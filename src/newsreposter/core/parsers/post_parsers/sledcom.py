from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import get_text


def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    post = defaultdict(list)

    content = soup.find("div", class_="news-card__text")
    if content:
        description = ""
        for p in content.find_all("p", recursive=False):
            description += "\n" + get_text(p).strip()
        if description:
            post["description"].append(description.strip())

    article = soup.find("div", class_="news-card__img")
    if not article:
        article = soup.find("div", class_="news-card")
    if not article:
        return post

    for img in article.find_all("img"):
        src = img.get("src")
        if src:
            absolute = urljoin(link, str(src))
            post["photo"].append(absolute)
        break
    return post
