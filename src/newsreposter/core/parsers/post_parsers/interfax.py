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
        article = soup.find("section", class_="news-body")
    if not article:
        return post

    content = article.find("div", class_="editor-content")
    if content:
        description = ""
        for p in content.find_all("p", recursive=False):
            description += "\n" + get_text(p).strip()
        if description:
            post["description"].append(description.strip())

    for img_tag in article.find_all("img"):
        src = img_tag.get("src")
        if src:
            absolute_src = urljoin(link, str(src))
            post["photo"].append(absolute_src)

    for video_tag in article.find_all("video"):
        src = video_tag.get("src")
        if src:
            absolute_src = urljoin(link, str(src))
            post["video"].append(absolute_src)
        for source_tag in video_tag.find_all("source"):
            src = source_tag.get("src")
            if src:
                absolute_src = urljoin(link, str(src))
                post["video"].append(absolute_src)

    return post
