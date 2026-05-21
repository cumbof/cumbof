#!/usr/bin/env python3
"""Fetch Google Scholar data and update the research section in README.md."""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from scholarly import scholarly
except ImportError:
    print("scholarly is not installed. Run: pip install scholarly", file=sys.stderr)
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
except ImportError:
    print("matplotlib is not installed. Run: pip install matplotlib", file=sys.stderr)
    sys.exit(1)

SCHOLAR_ID = "DJWJY7EAAAAJ"
README_PATH = "README.md"
CHARTS_DIR = Path("charts")
START_MARKER = "<!-- SCHOLAR-START -->"
END_MARKER = "<!-- SCHOLAR-END -->"
N_RECENT_PUBS = 5


def fetch_author():
    print(f"Fetching Google Scholar profile for ID: {SCHOLAR_ID} ...")
    author = scholarly.search_author_id(SCHOLAR_ID)
    return scholarly.fill(author)


def interest_url(name: str) -> str:
    slug = name.lower().replace(" ", "_")
    return (
        f"https://scholar.google.com/citations"
        f"?view_op=search_authors&hl=en&mauthors=label:{slug}"
    )


def make_citations_chart(cites_per_year: dict):
    years = [str(y) for y in cites_per_year]
    values = list(cites_per_year.values())

    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.bar(range(len(years)), values, color="#2196F3", width=0.6, zorder=3)

    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, rotation=45, ha="right", fontsize=8.5)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=5))
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_ylabel("Citations", fontsize=9.5)
    ax.set_title("Citations per Year", fontsize=11, fontweight="bold", pad=8)

    ax.yaxis.grid(True, linestyle="--", linewidth=0.6, alpha=0.6, color="#cccccc", zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#cccccc")
    ax.tick_params(axis="both", which="both", length=0)

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    CHARTS_DIR.mkdir(exist_ok=True)
    out = CHARTS_DIR / "citations_per_year.svg"
    plt.tight_layout()
    plt.savefig(out, format="svg", bbox_inches="tight")
    plt.close()
    print(f"  Saved {out}")


def extract_venue(citation: str) -> str:
    if not citation:
        return ""
    match = re.search(r"\s+\d", citation)
    venue = citation[: match.start()].strip() if match else citation.split(",")[0].strip()
    return venue.rstrip(",").strip()


def pub_url(pub: dict) -> str:
    author_pub_id = pub.get("author_pub_id", "")
    if not author_pub_id:
        return ""
    return (
        f"https://scholar.google.com/citations?view_op=view_citation"
        f"&hl=en&user={SCHOLAR_ID}&citation_for_view={author_pub_id}"
    )


def build_section(author):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    citations = author.get("citedby", "N/A")
    hindex = author.get("hindex", "N/A")
    i10index = author.get("i10index", "N/A")
    interests = author.get("interests", [])
    cites_per_year = dict(sorted(author.get("cites_per_year", {}).items()))

    # Research interests line
    interest_parts = [f"[{i}]({interest_url(i)})" for i in interests]
    interests_line = "**Research interests:** " + " · ".join(interest_parts)

    # Citations chart
    if cites_per_year:
        make_citations_chart(cites_per_year)
        chart_line = "![Citations per year](charts/citations_per_year.svg)"
    else:
        chart_line = ""

    # Recent publications (deduplicated, sorted by year desc)
    pubs = sorted(
        author.get("publications", []),
        key=lambda p: int(p.get("bib", {}).get("pub_year") or 0),
        reverse=True,
    )
    seen, unique_pubs = set(), []
    for p in pubs:
        title = p.get("bib", {}).get("title", "")
        if title and title not in seen:
            seen.add(title)
            unique_pubs.append(p)

    pub_lines = []
    for pub in unique_pubs[:N_RECENT_PUBS]:
        bib = pub.get("bib", {})
        title = bib.get("title", "Unknown title")
        venue = extract_venue(bib.get("citation", ""))
        year = bib.get("pub_year", "")
        url = pub_url(pub)
        title_cell = f"[{title}]({url})" if url else title
        venue_part = f" — *{venue}*" if venue else ""
        pub_lines.append(f"- **{year}** · {title_cell}{venue_part}")

    # Assemble
    lines = ["", "---", "", interests_line, ""]
    lines += [
        (
            f"![Citations](https://img.shields.io/badge/Citations-{citations}-blue?style=flat-square) "
            f"![h-index](https://img.shields.io/badge/h--index-{hindex}-green?style=flat-square) "
            f"![i10-index](https://img.shields.io/badge/i10--index-{i10index}-orange?style=flat-square)"
        ),
        "",
        f"_Updated on {today} · [Google Scholar](https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en)_",
        "",
    ]
    if chart_line:
        lines += [chart_line, ""]
    lines += ["#### Recent Publications", ""]
    lines += pub_lines
    lines.append("")

    return "\n".join(lines)


def update_readme(section):
    with open(README_PATH, encoding="utf-8") as f:
        content = f.read()

    replacement = f"{START_MARKER}\n{section}\n{END_MARKER}"

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
        sys.exit(1)

    section = build_section(author)
    update_readme(section)


if __name__ == "__main__":
    main()
