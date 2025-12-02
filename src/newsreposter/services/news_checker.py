import asyncio
import importlib
import inspect
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import requests
from loguru import logger

from newsreposter.core import process_news
from newsreposter.services.news_queue import FileQueue

ROTATION_INTERVAL_SECONDS = 60
OVERLAP_MS = 1000
INITIAL_BACKFILL_MS = 60 * 60 * 1000
STATE_FILE = "state.json"
PARSERS_PACKAGE = str(
    Path(__file__).parent.relative_to(Path(__file__).parent.parent.parent) / "parsers"
).replace("\\", ".")


class NewsChecker:
    def __init__(self, q: FileQueue):
        self.lock = asyncio.Lock()
        self._task = None
        self.queue = q
        self.parsers = self._discover_parsers()
        self.site_names = list(self.parsers.keys())
        if not self.site_names:
            raise RuntimeError("No parsers found in parsers package")
        self.state = self._load_state()
        self.state.setdefault("index", 0)
        self.state.setdefault("sites", {})
        for s in self.site_names:
            self.state["sites"].setdefault(s, {"last_checked": None})
        self._save_state()

    def _discover_parsers(self) -> Dict[str, Any]:
        logger.debug("Discovering parsers from package: {}", PARSERS_PACKAGE)
        parsers = {}
        package = PARSERS_PACKAGE
        pkg = importlib.import_module(package)
        if not pkg.__file__:
            logger.error("Failed to find package {}", package)
            raise RuntimeError(f"Failed to find package {package}")
        pkg_path = os.path.dirname(pkg.__file__)
        for fname in os.listdir(pkg_path):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            name = fname[:-3]
            mod = importlib.import_module(f"{package}.{name}")
            if hasattr(mod, "get_recent_items"):
                parsers[name] = mod.get_recent_items
                logger.debug("Discovered parser: {}", name)
        logger.debug("Found {} parsers", len(parsers))
        return parsers

    def _load_state(self) -> Dict[str, Any]:
        logger.debug("Loading state from {}", STATE_FILE)
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.debug("State loaded successfully")
                return data
            except Exception:
                logger.exception("Failed to load state file, starting fresh")
        logger.debug("State file not found, starting with empty state")
        return {"index": 0, "sites": {}}

    def _save_state(self):
        logger.debug("Saving state to {}", STATE_FILE)
        tmp = STATE_FILE + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, STATE_FILE)
            logger.debug("State saved successfully")
        except Exception:
            logger.exception(
                "Failed to save state to {}; keeping state in-memory", STATE_FILE
            )
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                logger.exception("Failed to remove temp state file {}", tmp)

    async def start(self):
        logger.debug("Starting NewsChecker")
        self._task = asyncio.create_task(self.run())

    async def close(self):
        logger.debug("Closing NewsChecker")
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def run(self):
        while True:
            try:
                await self.check_news()
            except (asyncio.CancelledError, KeyboardInterrupt):
                logger.debug("NewsChecker stopped")
                return
            except Exception:
                logger.exception("check_news failed")
            await asyncio.sleep(ROTATION_INTERVAL_SECONDS)

    async def check_news(self):
        async with self.lock:
            site = self.site_names[self.state["index"]]
            get_recent = self.parsers[site]
            logger.debug("Checking news for site: {}", site)

            now_ms_val = int(datetime.now(timezone.utc).timestamp() * 1000)
            last_ms = self.state["sites"][site].get("last_checked") or (
                now_ms_val - INITIAL_BACKFILL_MS
            )
            last_ms = int(last_ms)
            ms_to_request = max(1, (now_ms_val - last_ms) + OVERLAP_MS)
            logger.debug("Requesting {} ms of news for {}", ms_to_request, site)

            items = None
            try:
                if inspect.iscoroutinefunction(get_recent):
                    items = await get_recent(milliseconds=ms_to_request)
                else:
                    items = await asyncio.to_thread(
                        get_recent, milliseconds=ms_to_request
                    )
                logger.debug("Got {} items from {}", len(items) if items else 0, site)
            except Exception as e:
                if not isinstance(e, requests.RequestException):
                    logger.exception(
                        "Parser failed for site {}; leaving last_checked unchanged",
                        site,
                    )
                else:
                    logger.error(
                        f"Parser failed for site {site}: {e}"
                    )
                self.state["index"] = (self.state["index"] + 1) % len(self.site_names)
                self._save_state()
                return

            items = items or []
            max_item_ms = None
            enqueued = 0
            for it in items:
                try:
                    if isinstance(it, dict):
                        allowed = await asyncio.to_thread(
                            process_news.process_news, text=it["title"]
                        )
                        if not allowed[0] and "description" in it and it["description"]:
                            allowed = await asyncio.to_thread(
                                process_news.process_news, text=it["description"]
                            )
                        if allowed[0]:
                            enqueued += 1
                            self.queue.enqueue(it)

                        if "timestamp_ms" in it and it["timestamp_ms"] is not None:
                            ts = int(it["timestamp_ms"])
                            if (max_item_ms is None) or (ts > max_item_ms):
                                max_item_ms = ts
                        else:
                            logger.error("No timestamp_ms in item: {}", it)
                    else:
                        logger.error("Bad item from parser {}: {}", site, it)
                except Exception:
                    logger.exception("Bad item from parser {}: {}", site, it)

            if enqueued:
                logger.info("Enqueued {} items from {}", enqueued, site)

            if max_item_ms:
                new_last = int(max_item_ms) + 1
            else:
                new_last = now_ms_val

            logger.debug("Updated last_checked for {} to {}", site, new_last)
            self.state["sites"][site]["last_checked"] = int(new_last)
            self.state["index"] = (self.state["index"] + 1) % len(self.site_names)
            self._save_state()
