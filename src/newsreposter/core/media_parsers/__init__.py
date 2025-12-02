import importlib
import re
from typing import Dict, Optional

import requests
import urllib3
from loguru import logger
from playwright.sync_api import sync_playwright

from newsreposter.services.parsers import BeautifulSoup


def route(link: str) -> Optional[Dict]:
    match = re.search(r"https?://(?:www\.)?([^.]+)\.", link)
    if not match:
        return {}
    parser_module = importlib.import_module(
        f"newsreposter.core.media_parsers.{match.group(1)}"
    )
    html = get_rendered_html(link)
    if not html:
        return {}
    return parser_module.parse(BeautifulSoup(html, "html.parser"), link) or {}


def parse(url: str) -> Dict:
    try:
        return route(url) or {}
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
            logger.error(f"Error loading page {link}: {e}")
            logger.info(
                "Trying to load page with requests(verify=True then verify=False(some site has an issue with cert))..."
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
