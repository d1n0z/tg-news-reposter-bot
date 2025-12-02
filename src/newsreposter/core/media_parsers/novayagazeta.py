from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    media_links = defaultdict(list)

    article = soup.find("article", id="article")
    if not article:
        article = soup.find("div", class_="article-page")
    if not article:
        return media_links

    for img in article.find_all("img"):
        src = img.get("src")
        if src and not str(src).startswith("ic_") and not str(src).endswith(".svg"):
            parent = img.find_parent("div", class_="pg_2y")
            if parent:
                continue
            absolute = urljoin(link, str(src))
            media_links["photo"].append(absolute)

    for video in article.find_all("video"):
        src = video.get("src")
        if src:
            media_links["video"].append(urljoin(link, str(src)))
        for source in video.find_all("source"):
            src = source.get("src")
            if src:
                media_links["video"].append(urljoin(link, str(src)))

    return media_links
