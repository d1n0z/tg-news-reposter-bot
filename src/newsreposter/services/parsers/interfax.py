import datetime
from typing import Dict, List, Union

import requests
from bs4 import BeautifulSoup
from loguru import logger

from newsreposter.services.parsers import MOSCOW_TZ, clean_html

INTERFAX_URL = "https://www.interfax-russia.ru/news"


def get_recent_items(
    milliseconds: int = 0, url: str = INTERFAX_URL
) -> List[Dict[str, Union[str, int]]]:
    logger.debug("Fetching recent items from Interfax: {} ms", milliseconds)

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    logger.debug("Successfully fetched Interfax page")

    soup = BeautifulSoup(resp.content, "html.parser")

    out: List[Dict[str, Union[str, int]]] = []

    lista = soup.select_one("ul.lenta-all-news, ul.list-unstyled.lenta-all-news")
    if not lista:
        logger.debug("News list not found on Interfax")
        return out

    first_h2 = lista.find("h2")
    if not first_h2:
        logger.debug("First h2 not found on Interfax")
        return out

    date_text = first_h2.get_text(strip=True)
    try:
        day_str = date_text.split()[0]
        day = int(day_str)
    except Exception as e:
        logger.debug("Failed to parse day from {}: {}", date_text, e)
        return out

    ru_months = {
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
        "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12
    }
    parts = date_text.split()
    if len(parts) >= 2:
        month_name = parts[1].lower()
        month = ru_months.get(month_name)
        if month:
            now = datetime.datetime.now()
            local_tz = now.astimezone().tzinfo
            try:
                current_date = datetime.datetime(datetime.datetime.now(local_tz).year, month, day, tzinfo=local_tz)
            except Exception as e:
                logger.debug("Failed to create date: {}", e)
                return out

    now = datetime.datetime.now(MOSCOW_TZ)
    if current_date.date() != now.date():
        return out

    header_li = first_h2.find_parent("li")
    if not header_li:
        logger.debug("Header li not found")
        return out

    now_ms = int(now.astimezone(datetime.timezone.utc).timestamp() * 1000)
    threshold_ms = now_ms - int(milliseconds) if milliseconds and milliseconds > 0 else None

    for li in header_li.find_next_siblings("li"):
        if li.find("h2"):
            break

        time_span = li.find("span", class_="news-datetime")
        a_tag = li.find("a")
        if not a_tag or not time_span:
            continue

        time_text = time_span.get_text(strip=True)
        try:
            hour, minute = map(int, time_text.split(":"))
        except Exception as e:
            logger.debug("Failed to parse time {}: {}", time_text, e)
            continue

        try:
            dt_msk = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except Exception as e:
            logger.debug("Failed to create datetime: {}", e)
            continue

        timestamp_ms = int(dt_msk.astimezone(datetime.timezone.utc).timestamp() * 1000)

        if threshold_ms is not None and timestamp_ms < threshold_ms:
            logger.debug("Skipping old item: {}", timestamp_ms)
            continue

        title = a_tag.get_text(strip=True)
        link = str(a_tag.get("href", ""))
        if link.startswith("/"):
            link = "https://www.interfax-russia.ru" + link
        elif link and not link.startswith("http"):
            link = "https://www.interfax-russia.ru/" + link.lstrip("/")

        logger.debug("Adding Interfax item: {}", title)
        out.append(
            {
                "title": clean_html(title),
                "link": link,
                "timestamp_ms": timestamp_ms,
            }
        )

    logger.debug("Interfax: found {} items", len(out))
    return out


if __name__ == "__main__":
    items = get_recent_items(30 * 60 * 1000 * 480)
    print(len(items))
    for i in items:
        print(i)
