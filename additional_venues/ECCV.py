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

INDEX_URL = "https://www.ecva.net/papers.php"
UA = "eccv-ecva-crawler/1.0 (respectful; rate-limited)"

# Matches ECCV detail pages like /papers/eccv_2024/papers_ECCV/html/4_ECCV_2024_paper.php
DETAIL_RE = re.compile(r"^/papers/eccv_(\d{4})/.+_paper\.php$", re.IGNORECASE)

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

def get_detail_urls_for_year(index_html: str, year: int) -> List[str]:
    soup = BeautifulSoup(index_html, "html.parser")
    urls: Set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(INDEX_URL, href)
        path = urlparse(full).path
        m = DETAIL_RE.match(path)
        if m and int(m.group(1)) == year:
            urls.add(full)
    return sorted(urls)

def extract_abstract_from_detail_soup(soup: BeautifulSoup) -> str:
    """
    The ECVA detail page shows a line 'Abstract' followed by the abstract text,
    then a 'Related Material' line. We capture the text between 'Abstract' and
    'Related Material' as robustly as possible.
    """
    # Strategy 1: find the marker text nodes and collect siblings until 'Related Material'
    label = soup.find(string=re.compile(r"^\s*Abstract\s*$", re.IGNORECASE))
    if label:
        texts = []
        # walk through subsequent siblings in the same container
        for sib in label.parent.next_siblings if getattr(label, "parent", None) else []:
            # stop at 'Related Material'
            if isinstance(sib, str):
                if re.search(r"^\s*Related Material\s*$", sib, re.IGNORECASE):
                    break
                t = sib.strip()
                if t:
                    texts.append(t)
            else:
                # element
                if sib.get_text(strip=True) and re.search(r"^\s*Related Material\s*$", sib.get_text(" ", strip=True), re.IGNORECASE):
                    break
                # prefer paragraph-like text
                t = sib.get_text(" ", strip=True)
                if t:
                    texts.append(t)
        abstract = " ".join(texts).strip() if texts else None
        if abstract:
            # if the captured block still includes 'Abstract' at start, remove it
            abstract = abstract[9:]
            # also strip wrapping quotes that ECVA sometimes includes
            abstract = abstract.strip().strip('"').strip()
            return abstract

    # Fallback: whole-page text, cut between markers
    full = soup.get_text("\n", strip=True)
    m = re.search(r"\bAbstract\b(.*?)(?:\bRelated Material\b|Contact\b|$)", full, flags=re.IGNORECASE | re.DOTALL)
    if m:
        abstract = m.group(1).strip()
        abstract = re.sub(r"^\s*abstract\s*[:—–-]?\s*", "", abstract, flags=re.IGNORECASE)
        abstract = abstract.strip().strip('"').strip()
        return abstract if abstract else None
    return None

def parse_detail(detail_html: str, detail_url: str) -> Dict:
    soup = BeautifulSoup(detail_html, "html.parser")

    # Title: the page prints the title as the main line near the top; try <h1>/<h2>, fallback to first strong text line
    title = None
    for sel in ["h1", "h2", "title"]:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            title = node.get_text(" ", strip=True)
            break
    if not title:
        # fallback: first bold/strong text with enough length
        cand = soup.find(["b", "strong"])
        if cand and len(cand.get_text(strip=True)) > 8:
            title = cand.get_text(" ", strip=True)
    # final fallback: first non-empty line of body text
    if not title:
        title = soup.get_text("\n", strip=True).splitlines()[0] if soup.get_text(strip=True) else None

    # Abstract
    abstract = extract_abstract_from_detail_soup(soup)

    rec = {
        "title": title or None,
        "keywords": [],        # ECVA pages don't list keywords
        "link": detail_url,    # canonical detail page
        "_bibtex": None,       # ECVA doesn't expose BibTeX here
        "abstract": abstract
    }
    return rec

def crawl_eccv_year(year: int,
                    sleep_s: float = 0.8,
                    retries: int = 3) -> List[Dict]:
    results: List[Dict] = []
    seen: Set[str] = set()

    with requests.Session() as sess:
        idx = polite_get(INDEX_URL, sess, retries=retries, sleep_s=sleep_s)
        detail_urls = get_detail_urls_for_year(idx.text, year)
        if not detail_urls:
            print(f"No ECCV {year} paper URLs found at {INDEX_URL}", file=sys.stderr)
            return []

        for url in detail_urls:
            if url in seen:
                continue
            seen.add(url)

            time.sleep(sleep_s)
            try:
                dr = polite_get(url, sess, retries=retries, sleep_s=sleep_s)
                rec = parse_detail(dr.text, url)
            except Exception as e:
                print(f"[warn] skipping {url}: {e}", file=sys.stderr)
                continue

            results.append(rec)

            # progress every 100
            if len(results) % 100 == 0:
                print(f"Collected {len(results)} papers so far...", file=sys.stderr)

    return results

def main():
    parser = argparse.ArgumentParser(description="ECCV (ECVA) papers crawler")
    parser.add_argument("--year", type=int, required=True, help="ECCV year, e.g., 2024")
    parser.add_argument("--sleep", type=float, default=0.8, help="Polite delay between requests")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retry attempts")
    parser.add_argument("--out", type=str, default=None, help="Optional explicit output path")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    default_name = f"notes_ECCV{args.year}_{ts}.json"
    out_path = args.out or default_name

    records = crawl_eccv_year(args.year, sleep_s=args.sleep, retries=args.retries)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(records)} records to {out_path}")

if __name__ == "__main__":
    main()
