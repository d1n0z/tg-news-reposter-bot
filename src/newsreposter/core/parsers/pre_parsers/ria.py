import datetime
from typing import Dict, List, Union

from loguru import logger

from .. import (
    MOSCOW_TZ,
    clean_html,
    get_rendered_page,
    parse_rss_items,
    parsed_pubdate,
)

RIA_RSS = "https://ria.ru/export/rss2/archive/index.xml"


def get_recent_items(
    milliseconds: int, url: str = RIA_RSS
) -> List[Dict[str, Union[str, int]]]:
    logger.debug("Fetching recent items from RIA: {} ms", milliseconds)
    now_local = datetime.datetime.now(MOSCOW_TZ)
    cutoff = now_local - datetime.timedelta(milliseconds=milliseconds)
    logger.debug("Cutoff time: {}", cutoff)

    out = []
    content = get_rendered_page(url, "text_content")
    if not content:
        logger.debug("Failed to fetch RIA RSS")
        return out
    logger.debug("Successfully fetched RIA RSS")

    items = parse_rss_items(content)
    for item in items:
        pub = (
            item.findtext("pubDate")
            or item.findtext("{http://purl.org/dc/elements/1.1/}date")
            or ""
        )
        dt = parsed_pubdate(pub)
        if not dt or dt < cutoff:
            continue

        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()

        logger.debug("Adding RIA item: {}", title)
        out.append(
            {
                "title": clean_html(title),
                "link": link,
                "timestamp_ms": int(
                    dt.astimezone(datetime.timezone.utc).timestamp() * 1000
                ),
            }
        )

    logger.debug("RIA: found {} items", len(out))
    return out
