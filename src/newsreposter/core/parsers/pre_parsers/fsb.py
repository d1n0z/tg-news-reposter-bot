import datetime
from typing import Dict, List, Union

from bs4 import BeautifulSoup
from loguru import logger

from .. import MOSCOW_TZ, clean_html, get_rendered_page

FSB_URL = "http://www.fsb.ru/fsb/press/message.htm"


def get_recent_items(
    milliseconds: int, url: str = FSB_URL
) -> List[Dict[str, Union[str, int]]]:
    logger.debug("Fetching recent items from FSB: {} ms", milliseconds)
    out: List[Dict[str, Union[str, int]]] = []

    content = get_rendered_page(url)
    if not content:
        logger.debug("Failed to fetch FSB page")
        return out
    logger.debug("Successfully fetched FSB page")

    soup = BeautifulSoup(content, "html.parser")
    news = soup.select_one("div.news")
    if news:
        news = news.find("ul", recursive=False)
    if not news:
        logger.error("news div not found at fsb.ru")
        raise RuntimeError("news div not found at fsb.ru")

    for row in news.find_all("li", recursive=False):
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
        elif link.startswith("fsb"):
            link = "http://www.fsb.ru/" + link

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
