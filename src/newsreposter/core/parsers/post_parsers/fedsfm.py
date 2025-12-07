from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import get_text


def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    post = defaultdict(list)

    article = soup.find("div", class_="ibox")
    if not article:
        return post

    description = ""
    for p in article.find_all("p"):
        text = p.get_text(strip=True)
        if not text:
            continue
        if text.startswith("Дата публикации: ") or text.startswith(
            "Дата редактирования: "
        ):
            continue
        description += "\n" + get_text(p).strip()
    if description:
        post["description"].append(description.strip())

    for img in article.find_all("img"):
        parent = img.find_parent("div")
        if parent:
            parent_id = parent.get("id")
            if isinstance(parent_id, str) and parent_id.endswith("share-button"):
                continue
        src = img.get("src")
        if src:
            absolute_src = urljoin(link, str(src))
            post["photo"].append(absolute_src)

    for video in article.find_all("video"):
        src = video.get("src")
        if src:
            absolute_src = urljoin(link, str(src))
            post["video"].append(absolute_src)
        for source in video.find_all("source"):
            src = source.get("src")
            if src:
                absolute_src = urljoin(link, str(src))
                post["video"].append(absolute_src)

    return post
