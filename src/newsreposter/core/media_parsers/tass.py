from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    media_links = defaultdict(list)

    article = soup.find("article")
    if not article:
        article = soup.select_one("div[class^='ContentPage_container']")
    if not article:
        return media_links

    for figure in article.find_all("figure"):
        video = figure.find("video")
        if video:
            src = video.get("src")
            if src:
                absolute = urljoin(link, str(src))
                media_links["video"].append(absolute)
            continue

        img = figure.find("img")
        if img:
            src = img.get("src")
            if src:
                absolute = urljoin(link, str(src))
                media_links["photo"].append(absolute)
    return media_links
