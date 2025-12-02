import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

from loguru import logger

logger.debug("Initializing news_queue module")

QUEUE_DIR = Path(__file__).parent.parent.parent.parent / "news_queue"
NEW_DIR = QUEUE_DIR / "new"
IN_PROGRESS_DIR = QUEUE_DIR / "in_progress"
FAILED_DIR = QUEUE_DIR / "failed"
MAX_PROCESS_PER_RUN = 1


class FileQueue:
    def __init__(self, base_dir: Path = QUEUE_DIR):
        self.base = Path(base_dir)
        self.new = self.base / "new"
        self.in_progress = self.base / "in_progress"
        self.failed = self.base / "failed"
        for d in (self.new, self.in_progress, self.failed):
            d.mkdir(parents=True, exist_ok=True)

    def _make_filename(self) -> str:
        ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        uid = uuid.uuid4().hex
        return f"{ts}-{uid}.json"

    def enqueue(self, obj: Dict[str, Any]) -> Path:
        logger.debug("Enqueueing item: {}", obj)
        fname = self._make_filename()
        tmp = self.new / (fname + ".tmp")
        final = self.new / fname
        data = json.dumps(obj, ensure_ascii=False, default=str)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, final)
            logger.debug("Enqueued news -> {}", final)
            return final
        except Exception:
            logger.exception("Failed to enqueue item")
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                logger.exception("Failed to cleanup tmp file {}", tmp)
            raise

    def _list_new_sorted(self) -> Iterable[Path]:
        files = [p for p in self.new.iterdir() if p.is_file() and p.suffix == ".json"]
        files.sort(key=lambda p: p.name)
        return files

    def claim_one(self) -> Optional[Path]:
        logger.debug("Claiming one item from queue")
        for p in self._list_new_sorted():
            target = self.in_progress / p.name
            try:
                os.replace(p, target)
                logger.debug("Claimed {} -> {}", p, target)
                return target
            except FileNotFoundError:
                continue
            except Exception:
                logger.exception("Failed to claim {}", p)
                continue
        logger.debug("No items to claim")
        return None

    def read(self, in_progress_path: Path) -> Dict[str, Any]:
        logger.debug("Reading item from {}", in_progress_path)
        with open(in_progress_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Item read successfully")
        return data

    def remove(self, in_progress_path: Path):
        try:
            in_progress_path.unlink()
            logger.debug("Removed processed file {}", in_progress_path)
        except Exception:
            logger.exception("Failed to remove {}", in_progress_path)

    def mark_failed(self, in_progress_path: Path):
        dest = self.failed / in_progress_path.name
        try:
            os.replace(in_progress_path, dest)
            logger.warning("Moved failed file to {}", dest)
        except Exception:
            logger.exception("Failed to move failed file {}", in_progress_path)


class QueuePoster:
    def __init__(
        self,
        queue: FileQueue,
        post_cb: Callable[[Dict[str, Any]], Any],
        interval_seconds: int = 60,
        max_per_run: int = MAX_PROCESS_PER_RUN,
    ):
        self.queue = queue
        self.post_cb = post_cb
        self.interval = interval_seconds
        self.max_per_run = max_per_run
        self._task: Optional[asyncio.Task] = None
        self._stopping = False

    async def start(self):
        logger.debug("Starting QueuePoster")
        if self._task:
            logger.debug("QueuePoster already running")
            return
        self._stopping = False
        self._task = asyncio.create_task(self._loop())
        logger.debug("QueuePoster started")

    async def stop(self):
        logger.debug("Stopping QueuePoster")
        self._stopping = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.debug("QueuePoster stopped")

    async def _process_once(self):
        logger.debug("Processing queue items")
        processed = 0
        while processed < self.max_per_run:
            claimed = self.queue.claim_one()
            if not claimed:
                break
            try:
                item = self.queue.read(claimed)
            except Exception:
                logger.exception("Failed to read claimed file {}", claimed)
                self.queue.mark_failed(claimed)
                continue

            try:
                logger.debug("Posting item: {}", item)
                res = self.post_cb(item)
                if asyncio.iscoroutine(res):
                    await res
                self.queue.remove(claimed)
                processed += 1
                logger.debug("Item posted successfully")
            except Exception:
                logger.exception("Posting failed for {}", claimed)
                self.queue.mark_failed(claimed)
        logger.debug("Processed {} items", processed)
        return processed

    async def _loop(self):
        logger.debug("QueuePoster loop started")
        while not self._stopping:
            try:
                n = await self._process_once()
                if n:
                    logger.info("QueuePoster: processed {} items this run", n)
            except Exception:
                logger.exception("QueuePoster run failed")
            await asyncio.sleep(self.interval)
        logger.debug("QueuePoster loop ended")
