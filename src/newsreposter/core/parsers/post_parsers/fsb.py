from collections import defaultdict
from typing import List

from bs4 import BeautifulSoup

from . import get_text

def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    post = defaultdict(list)

    article = soup.select_one("div._attr._attr_text.form-group.common.type1")
    if not article:
        return post

    description = ""
    for p in article.find_all("p", recursive=False):
        description += "\n" + get_text(p).strip()
    if description:
        post["description"].append(description.strip())

    return post
