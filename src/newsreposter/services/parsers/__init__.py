import datetime
import email.utils
import html
import re
import xml.etree.ElementTree as ET
import zoneinfo
from typing import List, Optional

from bs4 import BeautifulSoup
from loguru import logger

MOSCOW_TZ = zoneinfo.ZoneInfo("Europe/Moscow")


def clean_html(text: str) -> str:
    if not text:
        logger.debug("Empty text provided to clean_html")
        return ""
    logger.debug("Cleaning HTML text: {} chars", len(text))
    text = html.unescape(text)

    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style", "iframe", "noscript"]):
        tag.decompose()
    clean_text = soup.get_text(separator=" ")
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    logger.debug("Cleaned text: {} chars", len(clean_text))

    return clean_text


def parse_rss_items(xml_bytes: bytes) -> List[ET.Element]:
    logger.debug("Parsing RSS items from {} bytes", len(xml_bytes))
    root = ET.fromstring(xml_bytes)
    items = root.findall(".//item")
    logger.debug("Found {} RSS items", len(items))
    return items


def parsed_pubdate(pubdate_str: str) -> Optional[datetime.datetime]:
    logger.debug("Parsing pubdate: {}", pubdate_str)
    try:
        try:
            dt = email.utils.parsedate_to_datetime(pubdate_str)
        except Exception:
            dt = datetime.datetime.fromisoformat(pubdate_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MOSCOW_TZ)
        else:
            dt = dt.astimezone(MOSCOW_TZ)
        logger.debug("Parsed pubdate: {}", dt)
        return dt
    except Exception as e:
        logger.debug("Failed to parse pubdate {}: {}", pubdate_str, e)


def find_by_localname(item: ET.Element, localname: str) -> str:
    logger.debug("Finding element by localname: {}", localname)
    for child in item:
        tag = child.tag
        if isinstance(tag, str) and tag.split("}")[-1] == localname:
            result = (child.text or "").strip()
            logger.debug("Found element: {} chars", len(result))
            return result
    logger.debug("Element not found: {}", localname)
    return ""
