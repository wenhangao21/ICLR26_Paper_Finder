import openreview
from openreview import tools
import json
import time
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import chromadb
import textwrap
from collections import Counter
from datetime import datetime
from tqdm import tqdm
import argparse

def get_submissions(conf_name: str,
                    year: int,
                    sleep_second: float = 0.1):
    """
    Fetch CVF Open Access papers (CVPR / ICCV / WACV).

    Args:
        conf_name: Conference short name, e.g. 'CVPR', 'ICCV', or 'WACV' (case-insensitive).
        year: Four-digit year, e.g. 2024.
        base_url: Root of the CVF Open Access site.
        sleep_second: polite delay between requests.

    Returns:
        List[dict] with keys:
            - title (str)
            - authors (List[str])
            - abstract (str | None)
            - bibtex (str | None)
            - bibtex_url (str | None)
            - detail_url (str)
            - conference (str)  # normalized, e.g., 'CVPR'
            - year (int)
    """
    base_url="https://openaccess.thecvf.com"
    ROOT = base_url.rstrip("/")
    conf = conf_name.upper().strip()

    # Primary & fallback list pages used by CVF across years/templates
    list_urls = [
        f"{ROOT}/{conf}{year}?day=all",        # e.g., /CVPR2024?day=all
        f"{ROOT}/content/{conf}{year}",        # e.g., /content/CVPR2023
    ]

    def polite_get(url, sess, retries=3, timeout=25):
        last_exc = None
        for k in range(retries):
            try:
                r = sess.get(
                    url,
                    timeout=timeout,
                    headers={"User-Agent": f"{conf.lower()}-metadata-fetcher/1.0 (respectful; rate-limited)"}
                )
                if r.status_code == 200:
                    return r
            except Exception as e:
                last_exc = e
            time.sleep(sleep_second * (k + 1))
        if last_exc:
            raise last_exc
        raise RuntimeError(f"Failed to GET {url} after {retries} retries")

    def parse_list_titles(html):
        soup = BeautifulSoup(html, "html.parser")
        items = []
        # Standard listing blocks across many CVF years:
        # dt/div/h4.ptitle > a[href]
        for node in soup.select("dt.ptitle a, div.ptitle a, h4.ptitle a"):
            href = node.get("href")
            title = node.get_text(strip=True)
            if not href or not title:
                continue
            items.append({"title": title, "detail_url": urljoin(ROOT, href)})

        # Fallback: some "content" pages link to /html/... entries directly
        if not items:
            for a in soup.select("a[href*='/html/']"):
                title = a.get_text(strip=True)
                href = a.get("href")
                if title and href:
                    items.append({"title": title, "detail_url": urljoin(ROOT, href)})
        return items

    def parse_detail(html, detail_url):
        soup = BeautifulSoup(html, "html.parser")

        # Title (prefer detail page if present)
        title = None
        tnode = soup.select_one("#papertitle")
        if tnode:
            title = tnode.get_text(" ", strip=True)

        # Authors: <div id="authors"><i>Author1, Author2, ...</i></div>
        authors = []
        anode = soup.select_one("#authors i")
        if anode:
            authors = [x.strip() for x in anode.get_text(" ", strip=True).split(",") if x.strip()]

        # Abstract: <div id="abstract"> ... </div>
        abstract = None
        abnode = soup.select_one("#abstract")
        if abnode:
            abstract = abnode.get_text(" ", strip=True)

        # BibTeX: typically <div class="bibref"><pre> ... </pre>
        bibtex = None
        pre = soup.select_one("div.bibref pre")
        if pre:
            bibtex = pre.get_text().strip()
        else:
            bib = soup.select_one("div.bibref")
            if bib:
                bibtex = bib.get_text().strip()

        # BibTeX URL (if a link references bibtex)
        bibtex_url = None
        for a in soup.find_all("a", href=True):
            href_l = a["href"].lower()
            txt_l = (a.get_text() or "").lower()
            if "bibtex" in href_l or "bibtex" in txt_l:
                bibtex_url = urljoin(detail_url, a["href"])
                break

        return {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "bibtex": bibtex,
            "bibtex_url": bibtex_url
        }

    results = []
    seen_detail_urls = set()

    with requests.Session() as sess:
        # Step 1: gather (title, detail_url) entries from a list page
        entries = []
        for u in list_urls:
            try:
                r = polite_get(u, sess)
                entries = parse_list_titles(r.text)
                if entries:
                    break
            except Exception:
                continue

        if not entries:
            return []

        # Step 2: visit each detail page for full metadata
        for e in entries:
            # Deduplicate if the list page has repeated links
            detail_url = e["detail_url"]
            if detail_url in seen_detail_urls:
                continue
            seen_detail_urls.add(detail_url)

            title_from_list = e["title"]
            try:
                time.sleep(sleep_second)
                rd = polite_get(detail_url, sess)
                rec = parse_detail(rd.text, detail_url)
            except Exception:
                rec = {"title": None, "authors": [], "abstract": None, "bibtex": None, "bibtex_url": None}

            # Prefer detail title; fallback to list title
            rec["title"] = rec["title"] or title_from_list
            rec["detail_url"] = detail_url
            rec["conference"] = conf
            rec["year"] = year
            results.append(rec)
            if len(results) % 100 == 0:
                print (f'Get {len(results)} papers from {conf_name} {year}')

    return results


def main(args):

    notes = get_submissions(args.conf_name, args.year)
    
    # Check how many submissions there are
    print(f"Total submissions: {len(notes)}")
    # Get all the possible atrributes

    key_counter = Counter(k for note in notes for k in note.keys())
    print("\nAttribute occurrence counts:")
    for key, count in key_counter.items():
        print(f"{key}: {count}")

    json_data = []
    for note in notes:
        # Extract title value safely
        title_val = note.get("title", "")
        if isinstance(title_val, dict) and "value" in title_val:
            title_val = title_val["value"]
        # Skip notes where title starts with 'Null' followed by any non-space chars (one word)
        if isinstance(title_val, str) and re.fullmatch(r"Null\S+", title_val):
            continue
        entry = {}
        for key, value in note.items():
            # Safely extract inner value if present
            if isinstance(value, dict) and "value" in value:
                val = str(value["value"])
            else:
                val = str(value)
            if key == 'bibtex':
                entry['_bibtex'] = val
            elif key == 'detail_url':
                entry['link'] = val
            else: entry[key] = val
        json_data.append(entry)

    # Save to JSON file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # They update the submission list, so timestamps are added
    filename = f"notes_{args.conf_name}{args.year}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Openreview-based')
    parser.add_argument('--conf_name', type=str, help='Conference Name: CVPR, ICCV')
    parser.add_argument('--year', type=str, help='corresponding year')
    args = parser.parse_args()

    main(args)
