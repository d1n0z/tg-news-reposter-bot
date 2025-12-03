import importlib
import re
from functools import partial
from typing import Dict, List, Optional

import requests
import urllib3
from bs4 import Tag
from loguru import logger
from playwright.sync_api import sync_playwright

from newsreposter.services.parsers import BeautifulSoup

CUSTOM_PARSERS = {"мвд": "mia"}
ALLOWED_TAGS = {"b", "strong", "i", "em", "code", "a", "u", "s", "strike", "del", "pre"}


def route(link: str) -> Optional[partial[Optional[Dict[str, List[str]]]]]:
    match = re.search(r"https?://(?:www\.)?([^.]+)\.", link)
    if not match:
        return
    parser = match.group(1)
    parser_module = importlib.import_module(
        f"newsreposter.core.post_parsers.{CUSTOM_PARSERS.get(parser, parser)}"
    )
    html = get_rendered_html(link)
    if not html:
        return
    return partial(parser_module.parse, BeautifulSoup(html, "html.parser"), link)


def parse(url: str) -> Dict[str, List[str]]:
    try:
        _parse = route(url)
        if not _parse:
            return {}
        return _parse() or {}
    except Exception as e:
        logger.error(f'Error parsing url "{url}": {e}')
        return {}


def get_rendered_html(link: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(link, timeout=50000)
        except Exception as e:
            logger.error(f"Error loading page dynamically ({link}): {e}")
            logger.info(
                "Trying to load page with requests: verify=True and then verify=False(some site has an issue with cert))..."
            )
            for verify in (True, False):
                if not verify:
                    urllib3.disable_warnings(
                        category=urllib3.exceptions.InsecureRequestWarning
                    )
                try:
                    resp = requests.get(
                        link,
                        timeout=10,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        },
                        verify=verify,
                    )
                    resp.raise_for_status()
                    return resp.text
                except requests.RequestException as e:
                    logger.error(f"Failed. Giving up. {e}")
                    return None

        try:
            page.wait_for_selector("article", timeout=2000)
        except Exception:
            pass

        html = page.content()

        browser.close()
        return html


def get_text(input_tag: Tag):
    for img in input_tag.find_all({"img", "video"}):
        img.decompose()

    for tag in input_tag.find_all(ALLOWED_TAGS):
        if tag.name == "a":
            href = tag.get("href")
            tag.attrs = {"href": href} if href else {}
        elif tag.name == "pre":
            lang = tag.get("language", tag.get("lang"))
            tag.attrs = {"language": lang} if lang else {}
        else:
            tag.attrs = {}

    for tag in input_tag.find_all():
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()

    content = input_tag.decode_contents()
    content = content.replace("<br/>", "\n").replace("<br>", "\n")
    if input_tag.name.startswith("h") and len(input_tag.name) == 2:
        content = "\n\n<b>" + content + "</b>\n\n"

    return content
