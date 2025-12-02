from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    media_links = defaultdict(list)

    article = soup.find("div", class_="ibox")
    if not article:
        return media_links

    for img in article.find_all("img"):
        parent = img.find_parent("div")
        if parent:
            parent_id = parent.get("id")
            if isinstance(parent_id, str) and parent_id.endswith("share-button"):
                continue
        src = img.get("src")
        if src:
            absolute_src = urljoin(link, str(src))
            media_links["photo"].append(absolute_src)

    for video in article.find_all("video"):
        src = video.get("src")
        if src:
            absolute_src = urljoin(link, str(src))
            media_links["video"].append(absolute_src)
        for source in video.find_all("source"):
            src = source.get("src")
            if src:
                absolute_src = urljoin(link, str(src))
                media_links["video"].append(absolute_src)

    return media_links
