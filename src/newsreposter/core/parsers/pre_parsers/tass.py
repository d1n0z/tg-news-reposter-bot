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

TASS_RSS = "https://tass.ru/rss/v2.xml"


def get_recent_items(
    milliseconds: int, url: str = TASS_RSS
) -> List[Dict[str, Union[str, int]]]:
    logger.debug("Fetching recent items from TASS: {} ms", milliseconds)
    now_utc = datetime.datetime.now(MOSCOW_TZ)
    cutoff = now_utc - datetime.timedelta(milliseconds=milliseconds)
    logger.debug("Cutoff time: {}", cutoff)

    out = []
    content = get_rendered_page(url, "text_content")
    if not content:
        logger.debug("Failed to fetch TASS RSS")
        return out
    logger.debug("Successfully fetched TASS RSS")

    items = parse_rss_items(content)
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

        logger.debug("Adding TASS item: {}", title)
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

    logger.debug("TASS: found {} items", len(out))
    return out
