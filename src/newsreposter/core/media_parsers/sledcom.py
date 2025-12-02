from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    media_links = defaultdict(list)

    article = soup.find("div", class_="news-card__img")
    if not article:
        article = soup.find("div", class_="news-card")
    if not article:
        return media_links

    for img in article.find_all("img"):
        src = img.get("src")
        if src:
            absolute = urljoin(link, str(src))
            media_links["photo"].append(absolute)
        break
    return media_links
