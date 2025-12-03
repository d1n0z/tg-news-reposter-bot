from collections import defaultdict
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import get_text


def parse(soup: BeautifulSoup, link: str) -> defaultdict[str, List[str]]:
    post = defaultdict(list)

    article = soup.find("div", class_="left-column")
    if not article:
        return post

    content = article.find("div", class_="article")
    if content:
        description = ""
        for p in content.find_all("p"):
            description += "\n" + get_text(p).strip()
        if description:
            post["description"].append(description.strip())

    for img_tag in article.find_all("img"):
        src = img_tag.get("data-src") or img_tag.get("src")
        if src and "ajax-loader.gif" not in src:
            absolute_src = urljoin(link, str(src))
            post["photo"].append(absolute_src)

    for video_tag in article.find_all("iframe"):
        src = video_tag.get("src")
        if src and "ajax-loader.gif" not in src:
            absolute_src = urljoin(
                link, str(src).replace("files/embed/", "files/video/")
            )
            post["video"].append(absolute_src)
        for source_tag in video_tag.find_all("source"):
            src = source_tag.get("src")
            if src and "ajax-loader.gif" not in src:
                absolute_src = urljoin(
                    link, str(src).replace("files/embed/", "files/video/")
                )
                post["video"].append(absolute_src)

    return post
