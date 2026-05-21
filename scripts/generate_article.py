#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import pathlib
import re
import textwrap
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

RSS_SOURCES = [
    ("CBC News", "https://www.cbc.ca/webfeed/rss/rss-canada"),
    ("Government of Canada News", "https://www.canada.ca/en/news/web-feeds/newsroom.xml"),
]

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "articles"
README_PATH = ROOT / "README.md"
INDEX_PATH = ROOT / "index.html"


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def fetch_latest_item() -> dict:
    candidates = []
    for source_name, feed_url in RSS_SOURCES:
        try:
            with urllib.request.urlopen(feed_url, timeout=20) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
        except (urllib.error.URLError, TimeoutError, ET.ParseError):
            continue

        for item in root.findall(".//item")[:5]:
            title = clean_text(item.findtext("title", ""))
            link = clean_text(item.findtext("link", ""))
            description = clean_text(item.findtext("description", ""))
            pub_date = clean_text(item.findtext("pubDate", ""))
            if title and link:
                candidates.append(
                    {
                        "source": source_name,
                        "title": title,
                        "link": link,
                        "description": description,
                        "pub_date": pub_date,
                    }
                )

    if candidates:
        return candidates[0]

    now = dt.datetime.now(dt.timezone.utc)
    return {
        "source": "Canada Success Hub fallback",
        "title": "Weekly Canada Success Planning Update",
        "link": "https://www.canada.ca/en/news.html",
        "description": (
            "No live feed was reachable at generation time, so this article offers "
            "a practical weekly planning update based on trusted Canadian public resources"
        ),
        "pub_date": now.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    }


def build_article(item: dict) -> tuple[str, str]:
    now = dt.datetime.now(dt.timezone.utc)
    slug = now.strftime("%Y-%m-%d-%H%M")
    filename = f"{slug}-canada-update.md"

    summary = item["description"]
    if not summary:
        summary = (
            "A recent Canadian news development with possible impact on newcomers,"
            " workers, and families settling in Canada."
        )

    own_words = textwrap.fill(
        (
            f"This update highlights: {summary}. For Canada Success Hub readers, "
            "the key takeaway is to monitor how this issue could affect everyday "
            "decisions like housing, employment, education, and local services. "
            "Use the source article to verify details and then convert the news into "
            "a practical weekly action plan."
        ),
        width=100,
    )

    content = f"""# {item['title']}

- **Generated (UTC):** {now.strftime('%Y-%m-%d %H:%M')}
- **Source:** {item['source']}
- **Published (feed value):** {item['pub_date'] or 'Not provided'}
- **Original URL:** {item['link']}

## In Our Own Words

{own_words}

## Why It Matters for Success in Canada

- Stay informed and validate policy or program changes directly from trusted Canadian sources.
- Discuss the update with local newcomer-serving organizations and community groups.
- Turn this news into one small, measurable action this week.
"""
    return filename, content


def prepend_readme(filename: str, title: str) -> None:
    if not README_PATH.exists():
        return

    line = f"- [{title}](articles/{filename})"
    existing = README_PATH.read_text(encoding="utf-8")
    if line in existing:
        return

    if "## Auto-generated Articles" not in existing:
        existing = existing.strip() + "\n\n## Auto-generated Articles\n\n"

    updated = existing.replace(
        "## Auto-generated Articles\n\n",
        f"## Auto-generated Articles\n\n{line}\n",
        1,
    )
    README_PATH.write_text(updated, encoding="utf-8")


def update_index_notice(filename: str) -> None:
    if not INDEX_PATH.exists():
        return

    html = INDEX_PATH.read_text(encoding="utf-8")
    link = f"articles/{filename}"
    if link in html:
        return

    marker = '<section class="newsletter">'
    insert = (
        "<section class=\"latest-auto\">\n"
        "  <h2>Latest Auto-Generated Article</h2>\n"
        f"  <p><a href=\"{link}\">Read the newest update</a></p>\n"
        "</section>\n\n"
    )

    if "Latest Auto-Generated Article" in html:
        html = re.sub(
            r"<section class=\"latest-auto\">[\s\S]*?</section>",
            insert.strip(),
            html,
            count=1,
        )
    else:
        html = html.replace(marker, insert + marker)

    INDEX_PATH.write_text(html, encoding="utf-8")


def main() -> None:
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    item = fetch_latest_item()
    filename, content = build_article(item)
    article_path = ARTICLES_DIR / filename
    article_path.write_text(content, encoding="utf-8")

    prepend_readme(filename, item["title"])
    update_index_notice(filename)
    print(f"Created {article_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
