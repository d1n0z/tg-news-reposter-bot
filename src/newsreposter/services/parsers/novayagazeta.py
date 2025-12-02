import datetime
from typing import Dict, List, Union

import requests
from loguru import logger

from newsreposter.services.parsers import (
    MOSCOW_TZ,
    clean_html,
    parse_rss_items,
    parsed_pubdate,
)

NOVAYA_RSS = "https://novayagazeta.ru/feed/rss"


def get_recent_items(
    milliseconds: int, url: str = NOVAYA_RSS
) -> List[Dict[str, Union[str, int]]]:
    logger.debug("Fetching recent items from Novaya Gazeta: {} ms", milliseconds)
    now_moscow = datetime.datetime.now(MOSCOW_TZ)
    cutoff = now_moscow - datetime.timedelta(milliseconds=milliseconds)
    logger.debug("Cutoff time: {}", cutoff)

    out = []
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        logger.debug("Successfully fetched Novaya Gazeta RSS")
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        # this service is known to be slow/refuse connection, just skip
        return out

    items = parse_rss_items(res.content)
    for it in items:
        pub = (
            it.findtext("pubDate")
            or it.findtext("{http://purl.org/dc/elements/1.1/}date")
            or ""
        )

        dt = parsed_pubdate(pub) if pub else None
        if dt is None or dt < cutoff:
            continue

        title = (it.findtext("title") or "").strip()
        description = (it.findtext("description") or "").strip()
        link = (it.findtext("link") or "").strip()

        logger.debug("Adding Novaya Gazeta item: {}", title)
        out.append(
            {
                "title": clean_html(title),
                "description": clean_html(description),
                "link": link,
                "timestamp_ms": int(
                    dt.astimezone(datetime.timezone.utc).timestamp() * 1000
                ),
            }
        )

    logger.debug("Novaya Gazeta: found {} items", len(out))
    return out
