import datetime
import email.utils
import html
import re
import xml.etree.ElementTree as ET
import zoneinfo
from typing import List, Literal, Optional

import requests
import urllib3
from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import sync_playwright

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


def parse_rss_items(xml_bytes: str | bytes) -> List[ET.Element]:
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


def get_rendered_page(url: str, return_type: Literal["text_content", "content"]="content"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            resp = page.goto(url, timeout=50000)
        except Exception:
            for verify in (True, False):
                if not verify:
                    urllib3.disable_warnings(
                        category=urllib3.exceptions.InsecureRequestWarning
                    )
                try:
                    alt_resp = requests.get(
                        url,
                        timeout=10,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        },
                        verify=verify,
                    )
                    alt_resp.raise_for_status()
                    return alt_resp.content
                except requests.RequestException as e:
                    if "novayagazeta.ru" not in url:  # this service is often unavailable
                        logger.error(f"Failed. Giving up with {url}. {e}")
                    return None

        try:
            page.wait_for_selector("article", timeout=1000)
        except Exception:
            pass

        if return_type == "text_content":
            if not resp:
                raise Exception("response is None")
            content = resp.text()
        else:
            content = getattr(page, return_type)()

        browser.close()
        return content
