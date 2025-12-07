from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import get_text

def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    post = defaultdict(list)

    article = soup.find("article")
    if not article:
        article = soup.select_one("div[class^='ContentPage_container']")
    if not article:
        return post

    description = ""
    for p in article.find_all({"p", "summary"}, recursive=False):
        description += "\n" + get_text(p).strip()
    if description:
        post["description"].append(description.strip())

    for figure in article.find_all("figure"):
        video = figure.find("video")
        if video:
            src = video.get("src")
            if src:
                absolute = urljoin(link, str(src))
                post["video"].append(absolute)
            continue

        img = figure.find("img")
        if img:
            src = img.get("src")
            if src:
                absolute = urljoin(link, str(src))
                post["photo"].append(absolute)
    return post
