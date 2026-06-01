#!/usr/bin/env python3
"""Fetch Google Scholar data and update the research section in README.md."""

import re
import sys

try:
    from scholarly import scholarly, ProxyGenerator
except ImportError:
    print("scholarly is not installed. Run: pip install scholarly", file=sys.stderr)
    sys.exit(1)

SCHOLAR_ID = "DJWJY7EAAAAJ"
README_PATH = "README.md"
START_MARKER = "<!-- SCHOLAR-START -->"
END_MARKER = "<!-- SCHOLAR-END -->"


def fetch_author():
    try:
        pg = ProxyGenerator()
        if pg.FreeProxies():
            scholarly.use_proxy(pg)
            print("Using free proxy to reach Google Scholar.")
    except Exception as proxy_exc:
        print(f"Proxy setup skipped: {proxy_exc}", file=sys.stderr)

    print(f"Fetching Google Scholar profile for ID: {SCHOLAR_ID} ...")
    author = scholarly.search_author_id(SCHOLAR_ID)
    return scholarly.fill(author, sections=["basics", "indices"])


def interest_url(name: str) -> str:
    slug = name.lower().replace(" ", "_")
    return (
        f"https://scholar.google.com/citations"
        f"?view_op=search_authors&hl=en&mauthors=label:{slug}"
    )


def build_section(author):
    citations = author.get("citedby", "N/A")
    hindex = author.get("hindex", "N/A")
    i10index = author.get("i10index", "N/A")
    interests = author.get("interests", [])

    interest_parts = [f"[{i}]({interest_url(i)})" for i in interests]
    interests_line = "**Research interests:** " + " · ".join(interest_parts)

    badges_line = (
        f"![Citations](https://img.shields.io/badge/Citations-{citations}-blue?style=flat-square) "
        f"![h-index](https://img.shields.io/badge/h--index-{hindex}-green?style=flat-square) "
        f"![i10-index](https://img.shields.io/badge/i10--index-{i10index}-orange?style=flat-square)"
    )

    return "\n\n" + interests_line + "\n\n" + badges_line + "\n\n"


def update_readme(section):
    with open(README_PATH, encoding="utf-8") as f:
        content = f.read()

    replacement = START_MARKER + section + END_MARKER

    if START_MARKER in content:
        pattern = re.compile(
            re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
            re.DOTALL,
        )
        updated = pattern.sub(replacement, content)
    else:
        updated = content.rstrip("\n") + "\n\n" + replacement + "\n"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print("README.md updated.")


def main():
    try:
        author = fetch_author()
    except Exception as exc:
        print(f"Failed to fetch Scholar data: {exc}", file=sys.stderr)
        print("Skipping README update — Scholar may be temporarily unavailable.", file=sys.stderr)
        sys.exit(0)

    update_readme(build_section(author))


if __name__ == "__main__":
    main()
