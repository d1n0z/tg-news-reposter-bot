import datetime
from typing import Dict, List, Union

import requests
from bs4 import BeautifulSoup
from loguru import logger

from newsreposter.services.parsers import MOSCOW_TZ, clean_html

FSB_URL = "http://www.fsb.ru/fsb/press/message.htm"


def get_recent_items(
    milliseconds: int, url: str = FSB_URL
) -> List[Dict[str, Union[str, int]]]:
    logger.debug("Fetching recent items from FSB: {} ms", milliseconds)

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    logger.debug("Successfully fetched FSB page")

    soup = BeautifulSoup(response.content, "html.parser")

    out: List[Dict[str, Union[str, int]]] = []

    news = soup.select_one("div.news")
    if not news:
        logger.error("news div not found at fsb.ru")
        raise RuntimeError("news div not found at fsb.ru")

    for row in news.find_all("li"):
        date_tag = row.find("h5", class_="date")
        if not date_tag:
            continue
        date_text = date_tag.get_text(strip=True)

        a_tag = row.find("a")
        if not a_tag or not date_text:
            continue

        try:
            day, month, year = map(int, date_text.split("."))
            dt = datetime.datetime(year, month, day, 0, 0, 0, tzinfo=MOSCOW_TZ)
        except Exception as e:
            logger.debug("Failed to parse date {}: {}", date_text, e)
            continue
        if dt.day != datetime.datetime.now(MOSCOW_TZ).day:
            continue

        title = a_tag.get_text(strip=True)
        link = str(a_tag.get("href", ""))
        if link.startswith("/"):
            link = "http://www.fsb.ru" + link

        logger.debug("Adding FSB item: {}", title)
        out.append(
            {
                "title": clean_html(title),
                "link": link,
                "timestamp_ms": int(
                    dt.astimezone(datetime.timezone.utc).timestamp() * 1000
                ),
            }
        )

    logger.debug("FSB: found {} items", len(out))
    return out
