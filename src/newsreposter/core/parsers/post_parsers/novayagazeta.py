import re
from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import get_text


def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    post = defaultdict(list)

    article = soup.find("article", id="article")
    if not article:
        article = soup.find("div", class_="article-page")
    if not article:
        return post

    content = article.find_all(id=re.compile(r"^MaterialBlock_"))
    if content:
        description = ""
        for block in content:
            for tag in block.find_all({"p", "h2"}):
                description += "\n" + get_text(tag).strip()
        if description:
            post["description"].append(description.strip())

    for img in article.find_all("img"):
        src = img.get("src")
        if src and not str(src).startswith("ic_") and not str(src).endswith(".svg"):
            parent = img.find_parent("div", class_="pg_2y")
            if parent:
                continue
            absolute = urljoin(link, str(src))
            post["photo"].append(absolute)

    for video in article.find_all("video"):
        src = video.get("src")
        if src:
            post["video"].append(urljoin(link, str(src)))
        for source in video.find_all("source"):
            src = source.get("src")
            if src:
                post["video"].append(urljoin(link, str(src)))

    return post
