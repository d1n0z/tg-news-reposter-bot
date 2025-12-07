import datetime
from typing import Dict, List, Union

from loguru import logger

from .. import (
    MOSCOW_TZ,
    clean_html,
    find_by_localname,
    get_rendered_page,
    parse_rss_items,
    parsed_pubdate,
)

FEED_URL = "https://xn--b1aew.xn--p1ai/news/rss"


def get_recent_items(
    milliseconds: int, url: str = FEED_URL
) -> List[Dict[str, Union[str, int]]]:
    logger.debug("Fetching recent items from MIA: {} ms", milliseconds)
    now_local = datetime.datetime.now(MOSCOW_TZ)
    cutoff = now_local - datetime.timedelta(milliseconds=milliseconds)
    logger.debug("Cutoff time: {}", cutoff)

    out: List[Dict[str, Union[str, int]]] = []

    content = get_rendered_page(url, "text_content")
    if not content:
        return out
    logger.debug("Successfully fetched MIA RSS")

    items = parse_rss_items(content)

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

        title = clean_html(item.findtext("title") or "")
        description_raw = find_by_localname(item, "full-text") or (
            item.findtext("description") or ""
        )
        description = clean_html(description_raw)

        link = (item.findtext("link") or "").strip()
        if not link:
            for child in item:
                if child.tag.split("}")[-1] == "link":
                    link = child.get("href", "") or link
                    if link:
                        break

        logger.debug("Adding MIA item: {}", title)
        record: Dict[str, Union[str, int]] = {
            "title": title,
            "link": link,
            "timestamp_ms": int(
                dt.astimezone(datetime.timezone.utc).timestamp() * 1000
            ),
        }
        if description:
            record["description"] = description

        out.append(record)

    logger.debug("MIA: found {} items", len(out))
    return out
