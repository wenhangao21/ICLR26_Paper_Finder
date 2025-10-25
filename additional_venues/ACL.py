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
UA = "acl-anthology-crawler/1.2 (respectful; rate-limited)"

PAPER_ID_RE = re.compile(r"^/\d{4}\.[a-z0-9\-]+\.\d+/?$")

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
    if paper_type == "long":
        return f"{BASE}/volumes/{year}.acl-long"
    elif paper_type == "findings":
        return f"{BASE}/volumes/{year}.findings-acl/"
    else:
        raise ValueError("paper_type must be 'long' or 'findings'.")

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

    # Keywords (meta first; fallback to visible badges)
    keywords = [m["content"].strip()
                for m in soup.find_all("meta", attrs={"name": "citation_keywords"})
                if m.get("content")]
    if not keywords:
        kw = []
        for n in soup.select(".badge, .keyword, span.badge"):
            txt = n.get_text(" ", strip=True)
            if txt:
                kw.append(txt)
        keywords = list(dict.fromkeys(kw))

    # Abstract (try common Anthology structures)
    abstract = None
    # 1) section/div with id='abstract'
    ab = soup.select_one("#abstract, section#abstract, div#abstract")
    if ab:
        abstract = ab.get_text(" ", strip=True)
    # 2) card body with an 'Abstract' heading nearby
    if not abstract:
        # common pattern: <div class="card-body acl-abstract"> <p>...</p>
        for sel in ["div.acl-abstract", "div.card-body .acl-abstract", "div.card-body"]:
            node = soup.select_one(sel)
            if node:
                # prefer paragraph text
                p = node.find("p")
                if p and p.get_text(strip=True):
                    abstract = p.get_text(" ", strip=True)
                    break
                # fallback: any text in node
                text = node.get_text(" ", strip=True)
                if text and len(text.split()) > 5:
                    abstract = text
                    break
    # 3) meta (rare)
    if not abstract:
        mabs = soup.find("meta", attrs={"name": "description"})
        if mabs and mabs.get("content"):
            abstract = mabs["content"].strip()

    bibtex_url = detail_url.rstrip("/") + ".bib"
    if abstract:
        abstract = abstract[9:]
    rec = {
        "title": title or None,
        "keywords": keywords,
        "link": detail_url,
        "_bibtex": None,         # filled after fetching .bib
        "abstract": abstract
    }
    return rec, bibtex_url

def crawl_acl_volume(year: int,
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

            # Fetch BibTeX
            time.sleep(sleep_s)
            try:
                br = polite_get(biburl, sess, retries=retries, sleep_s=sleep_s)
                rec["_bibtex"] = br.text.strip() if br.text else None
            except Exception as e:
                print(f"[warn] bibtex fetch failed for {purl}: {e}", file=sys.stderr)

            results.append(rec)

            # Progress every 100 papers
            if len(results) % 100 == 0:
                print(f"Collected {len(results)} papers so far...", file=sys.stderr)

    return results

def main():
    parser = argparse.ArgumentParser(description="ACL Anthology crawler (ACL volumes)")
    parser.add_argument("--paper-type", choices=["long", "findings"], required=True,
                        help="Which ACL volume to crawl: 'long' or 'findings'")
    parser.add_argument("--year", type=int, required=True, help="Year, e.g., 2025")
    parser.add_argument("--sleep", type=float, default=0.1, help="Polite delay between requests")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retry attempts")
    parser.add_argument("--out", type=str, default=None, help="Optional explicit output path")
    args = parser.parse_args()

    # Timestamp format: %Y-%m-%d_%H-%M-%S
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    paper_type = args.paper_type.lower()
    year = args.year

    default_name = f"notes_ACL{year}_{paper_type}_{ts}.json"
    out_path = args.out or default_name

    records = crawl_acl_volume(year, paper_type, sleep_s=args.sleep, retries=args.retries)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(records)} records to {out_path}")

if __name__ == "__main__":
    main()
