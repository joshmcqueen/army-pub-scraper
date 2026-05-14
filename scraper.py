"""
Army Publications Scraper
Downloads PDFs from https://armypubs.army.mil organized by publication type.

Usage:
  python scraper.py                                    # Download all categories
  python scraper.py --category training_doctrine/FM   # Single category
  python scraper.py --dry-run                          # List URLs without downloading
  python scraper.py --delay 2.0                        # Request delay in seconds (default: 1.5)
  python scraper.py --limit 10                         # Max downloads per category
  python scraper.py --status ACTIVE                    # Filter: ACTIVE, INACTIVE, RESCINDED
  python scraper.py --output ./my_downloads            # Custom output directory
"""

import argparse
import json
import os
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://armypubs.army.mil"
CATEGORY_BASE = f"{BASE_URL}/ProductMaps/PubForm"

CATEGORIES = {
    # Administrative
    "administrative/Web_Series":    "Web_Series.aspx",
    "administrative/ALARACT":       "ALARACT.aspx",
    "administrative/ArmyDir":       "ArmyDir.aspx",
    "administrative/AR":            "AR.aspx",
    "administrative/AGO_active":    "AGO.aspx",
    "administrative/AGO_inactive":  "AGO_Inactive.aspx",
    "administrative/DAMEMO":        "DAMEMO.aspx",
    "administrative/HQDA_Policy":   "HQDAPolicyNotice.aspx",
    "administrative/PAM":           "PAM.aspx",
    "administrative/POG":           "PogProponent.aspx",
    "administrative/PPM":           "PPM.aspx",

    # Technical & Equipment
    "technical_equipment/EM":           "EM.aspx",
    "technical_equipment/FT":           "FT.aspx",
    "technical_equipment/LO":           "LO.aspx",
    "technical_equipment/MWO":          "MWO.aspx",
    "technical_equipment/SB":           "SB.aspx",
    "technical_equipment/SC":           "SC.aspx",
    "technical_equipment/TB":           "TB.aspx",
    "technical_equipment/TM_1_8":       "TM_1_8.aspx",
    "technical_equipment/TM_9":         "TM_9.aspx",
    "technical_equipment/TM_10":        "TM_10.aspx",
    "technical_equipment/TM_11_4":      "TM_11_4.aspx",
    "technical_equipment/TM_11_5":      "TM_11_5.aspx",
    "technical_equipment/TM_11_6_7":    "TM_11_6_7.aspx",
    "technical_equipment/TM_14_750":    "TM_14_750.aspx",

    # Training and Doctrine
    "training_doctrine/ADP":   "ADP.aspx",
    "training_doctrine/ADRP":  "ADRP.aspx",
    "training_doctrine/ATP":   "ATP.aspx",
    "training_doctrine/ATTP":  "ATTP.aspx",
    "training_doctrine/CTA":   "CTA.aspx",
    "training_doctrine/FM":    "FM.aspx",
    "training_doctrine/GTA":   "GTA.aspx",
    "training_doctrine/JTA":   "JTA.aspx",
    "training_doctrine/PB":    "PB.aspx",
    "training_doctrine/STP":   "STP.aspx",
    "training_doctrine/TC":    "TC.aspx",

    # Engineering
    "engineering/TM": "TM_Admin.aspx",
    "engineering/TB": "TB_Admin.aspx",

    # Medical
    "medical/TM": "TM_Cal.aspx",
    "medical/TB": "TB_Cal.aspx",
    "medical/SB": "SB_Cal.aspx",
    "medical/SC": "SC_Cal.aspx",

    # Miscellaneous
    "miscellaneous/MCM": "MISC.aspx",
}


def make_session(delay: float) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    return session


def fetch_with_retry(session: requests.Session, url: str, delay: float, max_retries: int = 3) -> Optional[requests.Response]:
    for attempt in range(max_retries):
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 503):
                wait = delay * (2 ** attempt) + 5
                print(f"  Rate limited ({resp.status_code}), waiting {wait:.0f}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP {resp.status_code} for {url}")
                return None
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                print(f"  Request failed: {e}")
                return None
    return None


def fetch_category_page(session: requests.Session, aspx_slug: str, delay: float) -> List[dict]:
    url = f"{CATEGORY_BASE}/{aspx_slug}"
    resp = fetch_with_retry(session, url, delay)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", id="MainContent_GridView1")
    if not table:
        print(f"  No table found at {url}")
        return []

    publications = []
    rows = table.find_all("tr")
    for row in rows[1:]:  # skip header row
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        link = cells[0].find("a")
        if not link:
            continue

        href = link.get("href", "")
        pub_id = None
        if "PUB_ID=" in href:
            pub_id = href.split("PUB_ID=")[-1].strip()

        publications.append({
            "pub_id": pub_id,
            "pub_number": cells[0].get_text(strip=True),
            "status": cells[1].get_text(strip=True),
            "date": cells[2].get_text(strip=True),
            "title": cells[3].get_text(strip=True),
            "proponent": cells[4].get_text(strip=True) if len(cells) > 4 else "",
        })

    return publications


def fetch_pdf_urls(session: requests.Session, pub_id: str, delay: float) -> List[str]:
    url = f"{CATEGORY_BASE}/Details.aspx?PUB_ID={pub_id}"
    time.sleep(delay)
    resp = fetch_with_retry(session, url, delay)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    pdf_urls = []

    # Scope to the publication detail table only — the page nav has unrelated PDF links
    container = soup.find(id="MainContent_tblContainer1")
    search_root = container if container else soup

    for a in search_root.find_all("a", href=True):
        href = a["href"]
        if ".pdf" not in href.lower():
            continue
        if href.startswith("http"):
            pdf_urls.append(href)
        elif href.startswith("../../"):
            clean = href[6:]  # ../../epubs/... → /epubs/...
            pdf_urls.append(f"{BASE_URL}/{clean}")
        elif href.startswith("/"):
            pdf_urls.append(f"{BASE_URL}{href}")
        else:
            pdf_urls.append(urllib.parse.urljoin(f"{CATEGORY_BASE}/", href))

    return pdf_urls


def download_pdf(session: requests.Session, pdf_url: str, dest_path: Path, delay: float) -> str:
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return "skipped"

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    time.sleep(delay)

    try:
        resp = session.get(pdf_url, stream=True, timeout=60)
        if resp.status_code != 200:
            return f"http_{resp.status_code}"

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
            # Some publications are access-restricted or not available as PDF
            if "text/html" in content_type.lower():
                return "no_pdf"

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if dest_path.stat().st_size == 0:
            dest_path.unlink()
            return "empty"

        return "downloaded"
    except requests.RequestException as e:
        return f"error:{e}"


def log_result(log_path: Path, entry: dict) -> None:
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def scrape_category(
    session: requests.Session,
    category_path: str,
    aspx_slug: str,
    output_dir: Path,
    log_path: Path,
    args: argparse.Namespace,
) -> dict:
    print(f"\n[{category_path}] Fetching listing...")
    pubs = fetch_category_page(session, aspx_slug, args.delay)

    if not pubs:
        print(f"  No publications found.")
        return {"total": 0, "downloaded": 0, "skipped": 0, "no_pdf": 0, "errors": 0}

    # Filter by status if requested
    if args.status:
        pubs = [p for p in pubs if p["status"].upper() == args.status.upper()]

    print(f"  Found {len(pubs)} publications" + (f" (filtered to {args.status})" if args.status else ""))

    dest_dir = output_dir / category_path
    dest_dir.mkdir(parents=True, exist_ok=True)

    counts = {"total": len(pubs), "downloaded": 0, "skipped": 0, "no_pdf": 0, "errors": 0}
    limit = args.limit if args.limit else len(pubs)

    for i, pub in enumerate(tqdm(pubs[:limit], desc=category_path.split("/")[-1], unit="pub")):
        pub_id = pub["pub_id"]
        if not pub_id:
            continue

        if args.dry_run:
            print(f"  [DRY RUN] {pub['pub_number']} | {pub['status']} | {pub['title'][:60]}")
            continue

        pdf_urls = fetch_pdf_urls(session, pub_id, args.delay)

        if not pdf_urls:
            counts["no_pdf"] += 1
            log_result(log_path, {
                "pub_id": pub_id, "pub_number": pub["pub_number"],
                "category": category_path, "status": pub["status"],
                "pdf_url": None, "local_path": None,
                "result": "no_pdf", "timestamp": datetime.utcnow().isoformat(),
            })
            continue

        # Download all available PDFs for this publication
        for pdf_url in pdf_urls:
            filename = pdf_url.split("/")[-1]
            dest_path = dest_dir / filename

            result = download_pdf(session, pdf_url, dest_path, args.delay)

            if result == "downloaded":
                counts["downloaded"] += 1
            elif result == "skipped":
                counts["skipped"] += 1
            elif result == "no_pdf":
                counts["no_pdf"] += 1
            else:
                counts["errors"] += 1

            log_result(log_path, {
                "pub_id": pub_id, "pub_number": pub["pub_number"],
                "category": category_path, "status": pub["status"],
                "pdf_url": pdf_url, "local_path": str(dest_path),
                "result": result, "timestamp": datetime.utcnow().isoformat(),
            })

            # Only download first PDF per publication by default
            break

    return counts


def print_summary(all_counts: Dict[str, dict]) -> None:
    total = {"total": 0, "downloaded": 0, "skipped": 0, "no_pdf": 0, "errors": 0}
    print("\n" + "=" * 60)
    print(f"{'CATEGORY':<40} {'TOTAL':>6} {'DL':>6} {'SKIP':>6} {'NOPDF':>6} {'ERR':>6}")
    print("-" * 60)
    for cat, counts in all_counts.items():
        label = cat.split("/")[-1]
        print(f"{label:<40} {counts['total']:>6} {counts['downloaded']:>6} "
              f"{counts['skipped']:>6} {counts['no_pdf']:>6} {counts['errors']:>6}")
        for k in total:
            total[k] += counts[k]
    print("-" * 60)
    print(f"{'TOTAL':<40} {total['total']:>6} {total['downloaded']:>6} "
          f"{total['skipped']:>6} {total['no_pdf']:>6} {total['errors']:>6}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Army Publications PDF Scraper")
    parser.add_argument("--category", help="Single category to scrape (e.g. training_doctrine/FM)")
    parser.add_argument("--dry-run", action="store_true", help="List publications without downloading")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between requests (default: 1.5)")
    parser.add_argument("--limit", type=int, default=0, help="Max publications per category (0 = all)")
    parser.add_argument("--status", help="Filter by status: ACTIVE, INACTIVE, RESCINDED")
    parser.add_argument("--output", default="downloads", help="Output directory (default: downloads)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "download_log.jsonl"

    session = make_session(args.delay)

    if args.category:
        if args.category not in CATEGORIES:
            print(f"Unknown category: {args.category}")
            print("Available categories:")
            for cat in CATEGORIES:
                print(f"  {cat}")
            return
        categories = {args.category: CATEGORIES[args.category]}
    else:
        categories = CATEGORIES

    all_counts = {}
    for category_path, aspx_slug in categories.items():
        counts = scrape_category(session, category_path, aspx_slug, output_dir, log_path, args)
        all_counts[category_path] = counts

    if not args.dry_run:
        print_summary(all_counts)
        print(f"\nLog written to: {log_path}")


if __name__ == "__main__":
    main()
