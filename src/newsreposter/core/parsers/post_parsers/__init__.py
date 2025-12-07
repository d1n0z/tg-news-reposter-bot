import importlib
import re
from functools import partial
from typing import Dict, List, Optional

from bs4 import BeautifulSoup, Tag
from loguru import logger

from .. import get_rendered_page

CUSTOM_PARSERS = {"мвд": "mia"}
ALLOWED_TAGS = {"b", "strong", "i", "em", "code", "a", "u", "s", "strike", "del", "pre"}


def route(link: str) -> Optional[partial[Optional[Dict[str, List[str]]]]]:
    match = re.search(r"https?://(?:www\.)?([^.]+)\.", link)
    if not match:
        return
    parser = match.group(1)
    parser_module = importlib.import_module(
        f"newsreposter.core.parsers.post_parsers.{CUSTOM_PARSERS.get(parser, parser)}"
    )
    html = get_rendered_page(link)
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
