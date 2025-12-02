import datetime
from typing import Dict, List, Union

import requests
import urllib3
from loguru import logger

from newsreposter.services.parsers import (
    MOSCOW_TZ,
    clean_html,
    parse_rss_items,
    parsed_pubdate,
)

FEDS_RSS = "https://fedsfm.ru/rss"


def get_recent_items(
    milliseconds: int, url: str = FEDS_RSS
) -> List[Dict[str, Union[str, int]]]:
    logger.debug("Fetching recent items from FEDS: {} ms", milliseconds)
    now_moscow = datetime.datetime.now(MOSCOW_TZ)
    cutoff = now_moscow - datetime.timedelta(milliseconds=milliseconds)
    logger.debug("Cutoff time: {}", cutoff)

    out: List[Dict[str, Union[str, int]]] = []

    urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)
    res = requests.get(
        url,
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        verify=False,
    )
    res.raise_for_status()
    logger.debug("Successfully fetched FEDS RSS")

    items = parse_rss_items(res.content)
    for it in items:
        pub = (
            it.findtext("pubDate")
            or it.findtext("{http://purl.org/dc/elements/1.1/}date")
            or it.findtext("{http://www.w3.org/2005/Atom}updated")
            or ""
        )
        dt = parsed_pubdate(pub) if pub else None
        if dt is None or dt < cutoff:
            continue

        title = (it.findtext("title") or "").strip()
        description_raw = (it.findtext("description") or "").strip()
        if not description_raw:
            description_raw = (
                it.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
            ).strip()

        link = (it.findtext("link") or "").strip()
        logger.debug("Adding FEDS item: {}", title)

        out.append(
            {
                "title": clean_html(title),
                "description": clean_html(description_raw),
                "link": link,
                "timestamp_ms": int(
                    dt.astimezone(datetime.timezone.utc).timestamp() * 1000
                ),
            }
        )

    logger.debug("FEDS: found {} items", len(out))
    return out
