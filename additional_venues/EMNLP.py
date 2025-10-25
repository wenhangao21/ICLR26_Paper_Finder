#!/usr/bin/env python3
import argparse
import json
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://aclanthology.org"
UA = "emnlp-anthology-crawler/1.0 (respectful; rate-limited)"

# Matches paper detail pages like /2024.emnlp-main.123 (optionally with trailing slash)
PAPER_ID_RE = re.compile(r"^/\d{4}\.[a-z0-9\-]+\.\d+/?$", re.IGNORECASE)

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

def volume_url_for(year: int, paper_type: str) -> str:
    paper_type = paper_type.lower().strip()
    if paper_type == "main":
        return f"{BASE}/volumes/{year}.emnlp-main"
    elif paper_type == "findings":
        return f"{BASE}/volumes/{year}.findings-emnlp/"
    else:
        raise ValueError("paper_type must be 'main' or 'findings'.")

def get_paper_urls(volume_html: str) -> List[str]:
    soup = BeautifulSoup(volume_html, "html.parser")
    urls: Set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        path = href[len(BASE):] if href.startswith(BASE) else href
        if PAPER_ID_RE.match(path.strip()):
            urls.add(urljoin(BASE, path.strip()))
    return sorted(urls)

def parse_paper_detail(detail_html: str, detail_url: str) -> Tuple[Dict, str]:
    soup = BeautifulSoup(detail_html, "html.parser")

    # Title (meta preferred; fallback to visible heading)
    title = None
    mt = soup.find("meta", attrs={"name": "citation_title"})
    if mt and mt.get("content"):
        title = mt["content"].strip()
    if not title:
        h = soup.select_one("h1, h2, #title, h2.title")
        if h:
            title = h.get_text(" ", strip=True)

    # Keywords (meta first; allow semicolon/comma-delimited lists), fallback to badges
    keywords: List[str] = []
    for m in soup.find_all("meta", attrs={"name": "citation_keywords"}):
        val = (m.get("content") or "").strip()
        if val:
            parts = [p.strip() for p in re.split(r"[;,]", val) if p.strip()]
            keywords.extend(parts)
    if not keywords:
        kw = []
        for n in soup.select(".badge, .keyword, span.badge"):
            txt = n.get_text(" ", strip=True)
            if txt:
                kw.append(txt)
        keywords = list(dict.fromkeys(kw))

    # Abstract
    abstract = None
    ab = soup.select_one("#abstract, section#abstract, div#abstract")
    if ab:
        abstract = ab.get_text(" ", strip=True)
    if not abstract:
        for sel in ["div.acl-abstract", "div.card-body .acl-abstract", "div.card-body"]:
            node = soup.select_one(sel)
            if node:
                p = node.find("p")
                if p and p.get_text(strip=True):
                    abstract = p.get_text(" ", strip=True)
                    break
                text = node.get_text(" ", strip=True)
                if text and len(text.split()) > 5:
                    abstract = text
                    break
    if not abstract:
        mabs = soup.find("meta", attrs={"name": "description"})
        if mabs and mabs.get("content"):
            abstract = mabs["content"].strip()

    # Optionally strip a leading "Abstract:" label
    if abstract:
        abstract = abstract[9:]
    bibtex_url = detail_url.rstrip("/") + ".bib"

    rec = {
        "title": title or None,
        "keywords": list(dict.fromkeys(keywords)),
        "link": detail_url,
        "_bibtex": None,         # filled after fetching .bib
        "abstract": abstract
    }
    return rec, bibtex_url

def crawl_emnlp_volume(year: int,
                       paper_type: str,
                       sleep_s: float = 0.8,
                       retries: int = 3) -> List[Dict]:
    vol_url = volume_url_for(year, paper_type)
    results: List[Dict] = []
    seen: Set[str] = set()

    with requests.Session() as sess:
        vr = polite_get(vol_url, sess, retries=retries, sleep_s=sleep_s)
        paper_urls = get_paper_urls(vr.text)
        if not paper_urls:
            print(f"No papers found at {vol_url}", file=sys.stderr)
            return []

        for purl in paper_urls:
            if purl in seen:
                continue
            seen.add(purl)

            time.sleep(sleep_s)
            try:
                pr = polite_get(purl, sess, retries=retries, sleep_s=sleep_s)
                rec, biburl = parse_paper_detail(pr.text, purl)
            except Exception as e:
                print(f"[warn] skipping paper {purl}: {e}", file=sys.stderr)
                continue

            # Fetch BibTeX (prefer plain text; handle occasional HTML wrapper)
            time.sleep(sleep_s)
            try:
                br = sess.get(biburl, timeout=25, headers={"User-Agent": UA, "Accept": "text/plain, */*"})
                if br.status_code == 200:
                    txt = br.text or ""
                    if ("@" in txt) and ("{" in txt):
                        rec["_bibtex"] = txt.strip()
                    else:
                        sb = BeautifulSoup(txt, "html.parser")
                        pre = sb.find("pre")
                        rec["_bibtex"] = (pre.get_text().strip() if pre else txt.strip()) or None
            except Exception as e:
                print(f"[warn] bibtex fetch failed for {purl}: {e}", file=sys.stderr)

            results.append(rec)

            # Progress every 100 papers
            if len(results) % 100 == 0:
                print(f"Collected {len(results)} papers so far...", file=sys.stderr)

    return results

def main():
    parser = argparse.ArgumentParser(description="EMNLP Anthology crawler (EMNLP volumes)")
    parser.add_argument("--paper-type", choices=["main", "findings"], required=True,
                        help="Which EMNLP volume to crawl: 'main' or 'findings'")
    parser.add_argument("--year", type=int, required=True, help="Year, e.g., 2024")
    parser.add_argument("--sleep", type=float, default=0.1, help="Polite delay between requests")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retry attempts")
    parser.add_argument("--out", type=str, default=None, help="Optional explicit output path")
    args = parser.parse_args()

    # Timestamp format: %Y-%m-%d_%H-%M-%S
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    paper_type = args.paper_type.lower()
    year = args.year

    default_name = f"notes_EMNLP{year}_{paper_type}_{ts}.json"
    out_path = args.out or default_name

    records = crawl_emnlp_volume(year, paper_type, sleep_s=args.sleep, retries=args.retries)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(records)} records to {out_path}")

if __name__ == "__main__":
    main()
