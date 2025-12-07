from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import get_text


def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    post = defaultdict(list)

    content = soup.find("div", class_="article__body")
    if content:
        blocks = soup.find_all("div", class_="abc", attrs={"data-type": True})
        description = ""
        for block in blocks:
            if block.get("data-type") != "article":
                description += "\n" + get_text(block).strip()
        if description:
            post["description"].append(description.strip())

    article = soup.find("article")
    if not article:
        article = soup.find("div", class_="article__header")
    if not article:
        return post

    for img in article.find_all("img"):
        src = img.get("src")
        if src:
            absolute = urljoin(link, str(src))
            post["photo"].append(absolute)
        break
    return post
