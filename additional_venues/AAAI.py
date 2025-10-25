#!/usr/bin/env python3
import argparse
import json
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

UA = "aaai-technical-track-crawler/1.0 (respectful; rate-limited)"

def ts_now() -> str:
    # required format: %Y-%m-%d_%H-%M-%S
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def polite_get(url: str, sess: requests.Session, retries: int = 3, sleep_s: float = 0.8, timeout: int = 25) -> requests.Response:
    last_exc = None
    for k in range(retries):
        try:
            r = sess.get(url, timeout=timeout, headers={"User-Agent": UA})
            if r.status_code == 200:
                return r
        except Exception as e:
            last_exc = e
        time.sleep(sleep_s * (k + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Failed to GET {url} after {retries} retries")

def proceeding_url_for(year: int) -> str:
    """
    AAAI uses 'aaai-<number>-<year>/' in the path.
    For AAAI-39 (2025) the slug is 'aaai-39-2025'.
    We accept explicit --proceeding-url to avoid guessing; but generate a common default.
    """
    # Fallback guess: derive <number> as (year - 1980) + 1. AAAI-1 was 1980.
    num = (year - 2020) + 34
    return f"https://aaai.org/proceeding/aaai-{num}-{year}/"

def get_technical_track_urls(index_html: str, base_url: str) -> List[str]:
    """
    From the proceedings landing page, collect links that correspond to 'Technical Track'
    pages/sections. This matches link text/headings containing 'Technical Track'.
    """
    soup = BeautifulSoup(index_html, "html.parser")
    urls: Set[str] = set()

    # 1) Any anchor visibly labeled Technical Track
    for a in soup.select("a[href]"):
        text = (a.get_text(" ", strip=True) or "").lower()
        href = a.get("href")
        if not href:
            continue
        if "technical track" in text:
            urls.add(urljoin(base_url, href))

    # 2) Section headings then find links beneath them
    for heading in soup.find_all(re.compile(r"^h[1-4]$")):
        if "technical track" in heading.get_text(" ", strip=True).lower():
            # collect all links inside the same section/card or next sibling lists
            container = heading.find_parent() or heading
            for a in container.select("a[href]"):
                urls.add(urljoin(base_url, a.get("href")))

    # 3) Fallback: filter URLs with 'technical' in the slug
    for a in soup.select("a[href*='technical']"):
        urls.add(urljoin(base_url, a.get("href")))

    # Keep only plausible HTML pages (avoid PDFs etc.)
    urls = {u for u in urls if not u.lower().endswith((".pdf", ".zip", ".bib", ".ris"))}

    return sorted(urls)

def get_paper_urls_from_track_page(track_html: str, base_url: str) -> List[str]:
    """
    Collect only the detailed article pages (exclude /view/<id>/<fileid> download links).
    """
    soup = BeautifulSoup(track_html, "html.parser")
    urls: Set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        # normalize path and test
        parsed = urlparse(full)
        path = parsed.path
        m = re.match(r"^/index\.php/AAAI/article/view/(\d+)(?:/)?$", path, re.IGNORECASE)
        if m:
            urls.add(full)
    return sorted(urls)

def extract_bibtex_url(soup: BeautifulSoup, detail_url: str) -> str:
    """
    Try to find the official BibTeX download link from the OJS page.
    Common patterns:
      - anchor with 'BibTeX' text
      - URLs containing 'citationstylelanguage' with 'format=bibtex'
      - sometimes a 'Cite' button leading to a modal with these links
    """
    # direct anchors that mention bibtex
    for a in soup.select("a[href]"):
        txt = (a.get_text(" ", strip=True) or "").lower()
        href = a.get("href") or ""
        href_l = href.lower()
        if "bibtex" in txt or "bibtex" in href_l:
            return urljoin(detail_url, href)

    # CSL download param (OJS)
    for a in soup.select("a[href*='citationstylelanguage']"):
        href = a.get("href") or ""
        if "format=bibtex" in href.lower():
            return urljoin(detail_url, href)

    # Some OJS skins embed links in buttons
    for btn in soup.select("button, a.btn, a.button"):
        txt = (btn.get_text(" ", strip=True) or "").lower()
        href = btn.get("href")
        if href and "bibtex" in txt:
            return urljoin(detail_url, href)

    return None  # not found

def parse_paper_detail(detail_html: str, detail_url: str) -> Tuple[Dict, str]:
    """
    Extract {title, abstract, keywords, link, _bibtex[None initially]} from an OJS 'article/view' page.
    """
    soup = BeautifulSoup(detail_html, "html.parser")

    # Title (prefer meta if provided)
    title = None
    mt = soup.find("meta", attrs={"name": "citation_title"})
    if mt and mt.get("content"):
        title = mt["content"].strip()
    if not title:
        h = soup.select_one("h1, h2, .page_title, .obj_article_header .page_title")
        if h:
            title = h.get_text(" ", strip=True)

    # Abstract
    abstract = None
    # OJS often uses <section class="item abstract"> or <div class="abstract">, or meta citation_abstract
    mabs = soup.find("meta", attrs={"name": "citation_abstract"})
    if mabs and mabs.get("content"):
        abstract = mabs["content"].strip()
    if not abstract:
        node = soup.select_one("section.abstract, .obj_article_details .abstract, div.abstract, #abstract")
        if node:
            # Prefer paragraph if available
            p = node.find("p")
            if p and p.get_text(strip=True):
                abstract = p.get_text(" ", strip=True)
            else:
                abstract = node.get_text(" ", strip=True)

    # Keywords
    keywords: List[str] = []
    # meta citation_keywords (may appear multiple times)
    metas = soup.find_all("meta", attrs={"name": "citation_keywords"})
    for m in metas:
        if m.get("content"):
            keywords.append(m["content"].strip())
    # on-page keyword labels (fallback)
    if not keywords:
        for n in soup.select(".keywords, .item.keywords, .tagit-choice, .badge, span.badge"):
            txt = n.get_text(" ", strip=True)
            if txt and len(txt) < 100:
                keywords.append(txt)
        # de-dup & normalize
        keywords = list(dict.fromkeys([k for k in (kw.strip() for kw in keywords) if k]))

    # BibTeX URL (to be fetched next)
    bibtex_url = extract_bibtex_url(soup, detail_url)

    if abstract:
        abstract = abstract[9:]
    rec = {
        "title": title or None,
        "keywords": keywords,
        "link": detail_url,
        "_bibtex": None,
        "abstract": abstract
    }
    return rec, bibtex_url

def crawl_aaai_technical(year: int,
                         proceeding_url: str = None,
                         sleep_s: float = 0.8,
                         retries: int = 3) -> List[Dict]:
    """
    Crawl AAAI Technical Tracks from the proceedings landing page:
    Only preserves Technical Track papers.
    """
    base_url = (proceeding_url or proceeding_url_for(year)).rstrip("/") + "/"
    results: List[Dict] = []
    seen_papers: Set[str] = set()

    with requests.Session() as sess:
        # 1) proceedings page -> collect Technical Track pages
        pr = polite_get(base_url, sess, retries=retries, sleep_s=sleep_s)
        track_urls = get_technical_track_urls(pr.text, base_url)
        if not track_urls:
            print("No Technical Track URLs found on the proceedings page.", file=sys.stderr)
            return []

        # 2) each Technical Track page -> collect paper detail URLs (OJS)
        paper_urls: List[str] = []
        for turl in track_urls:
            time.sleep(sleep_s)
            try:
                tr = polite_get(turl, sess, retries=retries, sleep_s=sleep_s)
            except Exception as e:
                print(f"[warn] skipping track page {turl}: {e}", file=sys.stderr)
                continue
            urls = get_paper_urls_from_track_page(tr.text, turl)
            paper_urls.extend(urls)

        # de-dup
        paper_urls = sorted(set(paper_urls))
        if not paper_urls:
            print("No paper URLs found under Technical Tracks.", file=sys.stderr)
            return []

        # 3) visit each paper detail page
        for purl in paper_urls:
            if purl in seen_papers:
                continue
            seen_papers.add(purl)

            time.sleep(sleep_s)
            try:
                pr = polite_get(purl, sess, retries=retries, sleep_s=sleep_s)
                rec, biburl = parse_paper_detail(pr.text, purl)
            except Exception as e:
                print(f"[warn] skipping paper {purl}: {e}", file=sys.stderr)
                continue

            # 4) fetch BibTeX if link found
            if biburl:
                time.sleep(sleep_s)
                try:
                    br = polite_get(biburl, sess, retries=retries, sleep_s=sleep_s)
                    # Some endpoints return HTML; if so, try to extract pre/code text, else raw text
                    txt = br.text or ""
                    if ("@" in txt) and ("{" in txt):
                        rec["_bibtex"] = txt.strip()
                    else:
                        # try to locate <pre> bibtex
                        sb = BeautifulSoup(txt, "html.parser")
                        pre = sb.find("pre")
                        rec["_bibtex"] = (pre.get_text().strip() if pre else txt.strip()) or None
                except Exception as e:
                    print(f"[warn] bibtex fetch failed for {purl}: {e}", file=sys.stderr)
            results.append(rec)

            # progress every 100 papers
            if len(results) % 100 == 0:
                print(f"Collected {len(results)} papers so far...", file=sys.stderr)

    return results

def main():
    parser = argparse.ArgumentParser(description="AAAI Technical Track crawler")
    parser.add_argument("--year", type=int, required=True, help="Year, e.g., 2025")
    parser.add_argument("--sleep", type=float, default=0.1, help="Polite delay between requests")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retry attempts")
    parser.add_argument("--proceeding-url", type=str, default=None,
                        help="Override the proceedings URL (defaults to https://aaai.org/proceeding/aaai-<n>-<year>/)")
    parser.add_argument("--out", type=str, default=None, help="Optional explicit output path")
    args = parser.parse_args()

    records = crawl_aaai_technical(
        year=args.year,
        proceeding_url=args.proceeding_url,
        sleep_s=args.sleep,
        retries=args.retries
    )

    out_default = f"notes_AAAI{args.year}_technical_{ts_now()}.json"
    out_path = args.out or out_default

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(records)} records to {out_path}")

if __name__ == "__main__":
    main()
