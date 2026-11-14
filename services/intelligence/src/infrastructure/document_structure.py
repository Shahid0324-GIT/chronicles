"""Document hierarchy uses offsets in the exact normalized evidence text."""

import json
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from src.application.research import FetchedDocument
from src.domain.research import digest, normalize


def html_document(body: bytes | str, url: str, *, rendered: bool = False) -> FetchedDocument:
    soup = BeautifulSoup(body, "html.parser")
    title = normalize(soup.title.get_text()) if soup.title else urlsplit(url).hostname or "Source"
    language = str(soup.html.get("lang", "und")) if soup.html else "und"
    for item in soup.select("script,style,nav,header,footer,aside,form,svg,noscript"):
        item.decompose()
    main = soup.select_one("main,article,#story,.story") or soup.body or soup
    text = normalize(main.get_text(" ", strip=True))
    headings: list[dict[str, Any]] = []
    cursor = 0
    for heading in main.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        label = normalize(heading.get_text(" ", strip=True))
        start = text.find(label, cursor) if label else -1
        if start >= 0:
            headings.append({"title": label, "level": int(heading.name[1]), "start": start})
            cursor = start + len(label)
    sections = []
    for index, section_heading in enumerate(headings):
        end = next(
            (h["start"] for h in headings[index + 1 :] if h["level"] <= section_heading["level"]),
            len(text),
        )
        sections.append({**section_heading, "end": end})
    links = []
    seen = set()
    for anchor in main.find_all("a", href=True):
        reference = urljoin(url, str(anchor["href"]))
        if urlsplit(reference).scheme not in {"http", "https"} or reference in seen:
            continue
        label = normalize(anchor.get_text(" ", strip=True))
        start = text.find(label) if label else -1
        section = next((h["title"] for h in reversed(headings) if h["start"] <= start), "")
        links.append({"url": reference, "text": label, "start": start, "section": section})
        seen.add(reference)
    return FetchedDocument(
        url=url,
        title=title[:300],
        publisher=urlsplit(url).hostname or "",
        text=text,
        truncated=False,
        metadata={
            "extraction_version": "structured-html-v3",
            "language": language,
            "rendered": str(rendered).lower(),
            "structure_text_hash": digest(text),
            "sections_json": json.dumps(sections, ensure_ascii=False),
            "links_json": json.dumps(links, ensure_ascii=False),
        },
    )
