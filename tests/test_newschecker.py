# tests/test_newschecker_full.py
import asyncio
import json
from datetime import datetime, timezone

import pytest

NEWS_MODULE_PATH = "newsreposter.services.news_checker"
news_mod = __import__(NEWS_MODULE_PATH, fromlist=["*"])
NewsChecker = news_mod.NewsChecker

# constants override for tests
news_mod.ROTATION_INTERVAL_SECONDS = 1
news_mod.OVERLAP_MS = 1000
news_mod.INITIAL_BACKFILL_MS = 60 * 60 * 1000


def now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


@pytest.mark.asyncio
async def test_sync_parser_updates_state(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(news_mod, "STATE_FILE", str(state_file))

    chk = NewsChecker()
    # sync parser
    base = now_ms()

    def sync_parser(ms: int):
        # returns one item with timestamp base - 5000
        return [{"timestamp_ms": base - 5000, "link": "http://a/1"}]

    chk.parsers = {"a": sync_parser}
    chk.site_names = ["a"]
    chk.state = {"index": 0, "sites": {"a": {"last_checked": None}}}

    await chk.check_news()

    data = json.loads(state_file.read_text(encoding="utf-8"))
    last = data["sites"]["a"]["last_checked"]
    assert last == (base - 5000) + 1


@pytest.mark.asyncio
async def test_async_parser_updates_state(tmp_path, monkeypatch):
    state_file = tmp_path / "state2.json"
    monkeypatch.setattr(news_mod, "STATE_FILE", str(state_file))

    chk = NewsChecker()
    base = now_ms()

    async def async_parser(ms: int):
        await asyncio.sleep(0)  # ensure it's coroutine
        return [{"timestamp_ms": base - 2000, "link": "http://b/1"}]

    chk.parsers = {"b": async_parser}
    chk.site_names = ["b"]
    chk.state = {"index": 0, "sites": {"b": {"last_checked": None}}}

    await chk.check_news()

    data = json.loads(state_file.read_text(encoding="utf-8"))
    last = data["sites"]["b"]["last_checked"]
    assert last == (base - 2000) + 1


@pytest.mark.asyncio
async def test_empty_items_sets_now(tmp_path, monkeypatch):
    state_file = tmp_path / "state3.json"
    monkeypatch.setattr(news_mod, "STATE_FILE", str(state_file))

    chk = NewsChecker()

    async def empty_parser(ms: int):
        return []

    chk.parsers = {"c": empty_parser}
    chk.site_names = ["c"]
    chk.state = {"index": 0, "sites": {"c": {"last_checked": None}}}

    before = now_ms()
    await chk.check_news()
    after = now_ms()

    data = json.loads(state_file.read_text(encoding="utf-8"))
    last = data["sites"]["c"]["last_checked"]
    assert before <= last <= after


@pytest.mark.asyncio
async def test_parser_exception_does_not_update_last_checked(tmp_path, monkeypatch):
    state_file = tmp_path / "state4.json"
    monkeypatch.setattr(news_mod, "STATE_FILE", str(state_file))

    chk = NewsChecker()
    # set previous last_checked
    initial_last = now_ms() - 10000

    async def bad_parser(ms: int):
        raise RuntimeError("boom")

    chk.parsers = {"d": bad_parser}
    chk.site_names = ["d"]
    chk.state = {"index": 0, "sites": {"d": {"last_checked": initial_last}}}

    # call check_news -> should catch exception and NOT change last_checked
    await chk.check_news()
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data["sites"]["d"]["last_checked"] == initial_last


@pytest.mark.asyncio
async def test_duplicate_timestamps_handle(tmp_path, monkeypatch):
    state_file = tmp_path / "state5.json"
    monkeypatch.setattr(news_mod, "STATE_FILE", str(state_file))

    chk = NewsChecker()
    base = now_ms()

    async def dup_parser(ms: int):
        # two items with identical timestamp
        return [
            {"timestamp_ms": base - 3000, "link": "http://dup/1"},
            {"timestamp_ms": base - 3000, "link": "http://dup/2"},
        ]

    chk.parsers = {"e": dup_parser}
    chk.site_names = ["e"]
    chk.state = {"index": 0, "sites": {"e": {"last_checked": None}}}

    await chk.check_news()
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data["sites"]["e"]["last_checked"] == (base - 3000) + 1


@pytest.mark.asyncio
async def test_rotation_over_multiple_sites(tmp_path, monkeypatch):
    state_file = tmp_path / "state6.json"
    monkeypatch.setattr(news_mod, "STATE_FILE", str(state_file))

    chk = NewsChecker()
    base = now_ms()

    async def p1(ms):
        return [{"timestamp_ms": base - 1000}]

    async def p2(ms):
        return [{"timestamp_ms": base - 2000}]

    chk.parsers = {"s1": p1, "s2": p2}
    chk.site_names = ["s1", "s2"]
    chk.state = {
        "index": 0,
        "sites": {"s1": {"last_checked": None}, "s2": {"last_checked": None}},
    }

    await chk.check_news()  # handles s1, index->1
    await chk.check_news()  # handles s2, index->0
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data["index"] == 0
    assert "s1" in data["sites"] and "s2" in data["sites"]


@pytest.mark.asyncio
async def test_concurrent_checks_are_serialized(tmp_path, monkeypatch):
    state_file = tmp_path / "state7.json"
    monkeypatch.setattr(news_mod, "STATE_FILE", str(state_file))

    chk = NewsChecker()
    base = now_ms()
    event = asyncio.Event()
    call_count = {"n": 0}

    async def slow_parser(ms: int):
        call_count["n"] += 1
        # wait so the second check_news() will attempt to acquire lock
        await event.wait()
        return [{"timestamp_ms": base - 500}]

    chk.parsers = {"slow": slow_parser}
    chk.site_names = ["slow"]
    chk.state = {"index": 0, "sites": {"slow": {"last_checked": None}}}

    # start two concurrent check_news()
    t1 = asyncio.create_task(chk.check_news())
    # give t1 a moment to start and acquire the lock
    await asyncio.sleep(0.05)
    t2 = asyncio.create_task(chk.check_news())

    # ensure parser called once so far
    await asyncio.sleep(0.05)
    assert call_count["n"] == 1

    # release parser
    event.set()
    await asyncio.gather(t1, t2)

    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_ignores_bad_item_entries(tmp_path, monkeypatch):
    state_file = tmp_path / "state8.json"
    monkeypatch.setattr(news_mod, "STATE_FILE", str(state_file))

    chk = NewsChecker()
    base = now_ms()

    async def mixed_parser(ms: int):
        # first item malformed (no timestamp), second valid
        return [
            {"link": "bad"},
            {"timestamp_ms": base - 700, "link": "ok"},
        ]

    chk.parsers = {"m": mixed_parser}
    chk.site_names = ["m"]
    chk.state = {"index": 0, "sites": {"m": {"last_checked": None}}}

    await chk.check_news()
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data["sites"]["m"]["last_checked"] == (base - 700) + 1
