import datetime
from typing import Dict, List, Union

import requests
from loguru import logger

from newsreposter.services.parsers import (
    MOSCOW_TZ,
    find_by_localname,
    clean_html,
    parse_rss_items,
    parsed_pubdate,
)

SLEDCOM_RSS = "https://sledcom.ru/news/rss_verify/?main=1"


def get_recent_items(
    milliseconds: int, url: str = SLEDCOM_RSS
) -> List[Dict[str, Union[str, int]]]:
    logger.debug("Fetching recent items from Sledcom: {} ms", milliseconds)
    now_local = datetime.datetime.now(MOSCOW_TZ)
    cutoff = now_local - datetime.timedelta(milliseconds=milliseconds)
    logger.debug("Cutoff time: {}", cutoff)

    out: List[Dict[str, Union[str, int]]] = []
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    logger.debug("Successfully fetched Sledcom RSS")

    items = parse_rss_items(response.content)

    for item in items:
        pub = (
            item.findtext("pubDate")
            or item.findtext("{http://purl.org/dc/elements/1.1/}date")
            or item.findtext("{http://www.w3.org/2005/Atom}updated")
            or ""
        )
        dt = parsed_pubdate(pub)
        if not dt or dt < cutoff:
            continue

        title = (item.findtext("title") or "").strip()
        description = (
            find_by_localname(item, "full-text") or item.findtext("description") or ""
        )
        link = (item.findtext("link") or "").strip()
        if not link:
            for child in item:
                if child.tag.split("}")[-1] == "link":
                    link = child.get("href", "") or link
                    if link:
                        break

        logger.debug("Adding Sledcom item: {}", title)
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

    logger.debug("Sledcom: found {} items", len(out))
    return out
