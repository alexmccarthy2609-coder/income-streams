"""Pull HTML tables or links from a web page into CSV.

Only scrape sites whose terms allow it, and respect robots.txt.
"""
import csv
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

UA = "officekit/1.0 (+https://example.com/officekit)"


def allowed_by_robots(url: str) -> bool:
    rp = RobotFileParser(urljoin(url, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        return True
    return rp.can_fetch(UA, url)


def parse_tables(html: str) -> list[list[list[str]]]:
    soup = BeautifulSoup(html, "html.parser")
    tables = []
    for t in soup.find_all("table"):
        rows = []
        for tr in t.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def parse_links(html: str, base_url: str) -> list[list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    return [["text", "url"]] + [
        [a.get_text(" ", strip=True), urljoin(base_url, a["href"])]
        for a in soup.find_all("a", href=True)
    ]


def fetch(url: str) -> str:
    if not allowed_by_robots(url):
        raise PermissionError(f"robots.txt disallows fetching {url}")
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    resp.raise_for_status()
    return resp.text


def write_csv(rows: list[list[str]], output: Path) -> None:
    with output.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def add_parser(sub):
    p = sub.add_parser("scrape", help="Save a page's tables (or links) as CSV")
    p.add_argument("url")
    p.add_argument("-o", "--output", type=Path, default=Path("table.csv"))
    p.add_argument("--table", type=int, default=1, help="Which table on the page (1 = first)")
    p.add_argument("--links", action="store_true", help="Export all links instead of a table")

    def _run(a):
        html = fetch(a.url)
        if a.links:
            rows = parse_links(html, a.url)
        else:
            tables = parse_tables(html)
            if not tables:
                raise SystemExit("No tables found on that page.")
            if not 1 <= a.table <= len(tables):
                raise SystemExit(f"Page has {len(tables)} tables; pick --table 1..{len(tables)}")
            rows = tables[a.table - 1]
        write_csv(rows, a.output)
        print(f"Wrote {len(rows)} rows to {a.output}")
    p.set_defaults(func=_run)
