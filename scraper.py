"""
Army Publications Scraper — two-step workflow:

  Step 1: Build a manifest of all publications and their PDF URLs
    python scraper.py build

  Step 2: Download only the PDFs listed in the manifest
    python scraper.py download

Each command accepts:
  --category training_doctrine/FM   # Scope to one category
  --status ACTIVE                   # Filter: ACTIVE, INACTIVE, RESCINDED
  --limit 10                        # Cap per category (useful for testing)
  --delay 2.0                       # Seconds between requests (default: 1.5)
  --output ./downloads              # Output directory (default: downloads)
  --manifest manifest.jsonl         # Manifest filename (default: manifest.jsonl)
"""

import argparse
import json
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


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def make_session() -> requests.Session:
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


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

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
    for row in table.find_all("tr")[1:]:  # skip header
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        link = cells[0].find("a")
        if not link:
            continue
        href = link.get("href", "")
        pub_id = href.split("PUB_ID=")[-1].strip() if "PUB_ID=" in href else None
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

    # Scope to the detail table only — the site nav contains unrelated PDF links
    container = soup.find(id="MainContent_tblContainer1")
    search_root = container if container else soup

    pdf_urls = []
    for a in search_root.find_all("a", href=True):
        href = a["href"]
        if ".pdf" not in href.lower():
            continue
        if href.startswith("http"):
            pdf_urls.append(href)
        elif href.startswith("../../"):
            pdf_urls.append(f"{BASE_URL}/{href[6:]}")
        elif href.startswith("/"):
            pdf_urls.append(f"{BASE_URL}{href}")
        else:
            pdf_urls.append(urllib.parse.urljoin(f"{CATEGORY_BASE}/", href))

    return pdf_urls


# ---------------------------------------------------------------------------
# Step 1: build
# ---------------------------------------------------------------------------

def cmd_build(args: argparse.Namespace) -> None:
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / args.manifest

    categories = _resolve_categories(args.category)
    session = make_session()

    total_found = 0
    total_with_pdf = 0
    total_no_pdf = 0

    # Load already-processed pub_ids so we can resume an interrupted build
    seen_ids: set = set()
    if manifest_path.exists():
        with open(manifest_path) as f:
            for line in f:
                try:
                    seen_ids.add(json.loads(line)["pub_id"])
                except (json.JSONDecodeError, KeyError):
                    pass
        print(f"Resuming — {len(seen_ids)} publications already in manifest.\n")

    for category_path, aspx_slug in categories.items():
        print(f"[{category_path}] Fetching listing...")
        pubs = fetch_category_page(session, aspx_slug, args.delay)

        if args.status:
            pubs = [p for p in pubs if p["status"].upper() == args.status.upper()]

        limit = args.limit or len(pubs)
        pubs = pubs[:limit]
        print(f"  {len(pubs)} publications")

        for pub in tqdm(pubs, desc=category_path.split("/")[-1], unit="pub"):
            pub_id = pub["pub_id"]
            if not pub_id or pub_id in seen_ids:
                continue

            pdf_urls = fetch_pdf_urls(session, pub_id, args.delay)
            pdf_url = pdf_urls[0] if pdf_urls else None

            entry = {
                "pub_id": pub_id,
                "pub_number": pub["pub_number"],
                "category": category_path,
                "status": pub["status"],
                "date": pub["date"],
                "title": pub["title"],
                "proponent": pub["proponent"],
                "pdf_url": pdf_url,
                "scanned_at": datetime.utcnow().isoformat(),
            }

            with open(manifest_path, "a") as f:
                f.write(json.dumps(entry) + "\n")

            seen_ids.add(pub_id)
            total_found += 1
            if pdf_url:
                total_with_pdf += 1
            else:
                total_no_pdf += 1

    print(f"\nManifest written to: {manifest_path}")
    print(f"  Total scanned : {total_found}")
    print(f"  With PDF      : {total_with_pdf}")
    print(f"  No PDF        : {total_no_pdf}")


# ---------------------------------------------------------------------------
# Step 2: download
# ---------------------------------------------------------------------------

def download_pdf(session: requests.Session, pdf_url: str, dest_path: Path, delay: float) -> str:
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return "skipped"

    # Only create the directory when we're actually about to write a file
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    time.sleep(delay)

    try:
        resp = session.get(pdf_url, stream=True, timeout=60)
        if resp.status_code != 200:
            return f"http_{resp.status_code}"

        content_type = resp.headers.get("Content-Type", "")
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


def cmd_download(args: argparse.Namespace) -> None:
    output_dir = Path(args.output)
    manifest_path = output_dir / args.manifest
    log_path = output_dir / "download_log.jsonl"

    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        print("Run 'python scraper.py build' first.")
        return

    # Load manifest entries that have a PDF URL
    entries = []
    with open(manifest_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not entry.get("pdf_url"):
                continue
            if args.category and entry["category"] != args.category:
                continue
            if args.status and entry["status"].upper() != args.status.upper():
                continue
            entries.append(entry)

    if not entries:
        print("No downloadable entries found in manifest matching your filters.")
        return

    # Apply per-category limit if requested
    if args.limit:
        from collections import defaultdict
        counts: Dict[str, int] = defaultdict(int)
        filtered = []
        for e in entries:
            if counts[e["category"]] < args.limit:
                filtered.append(e)
                counts[e["category"]] += 1
        entries = filtered

    print(f"Downloading {len(entries)} PDFs...\n")

    session = make_session()
    results: Dict[str, int] = {"downloaded": 0, "skipped": 0, "errors": 0}

    for entry in tqdm(entries, unit="pdf"):
        pdf_url = entry["pdf_url"]
        filename = pdf_url.split("/")[-1]
        dest_path = output_dir / entry["category"] / filename

        result = download_pdf(session, pdf_url, dest_path, args.delay)

        if result == "downloaded":
            results["downloaded"] += 1
        elif result == "skipped":
            results["skipped"] += 1
        else:
            results["errors"] += 1

        with open(log_path, "a") as f:
            f.write(json.dumps({
                "pub_id": entry["pub_id"],
                "pub_number": entry["pub_number"],
                "category": entry["category"],
                "status": entry["status"],
                "pdf_url": pdf_url,
                "local_path": str(dest_path),
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }) + "\n")

    print(f"\nDownloaded : {results['downloaded']}")
    print(f"Skipped    : {results['skipped']}  (already existed)")
    print(f"Errors     : {results['errors']}")
    print(f"\nLog written to: {log_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _resolve_categories(category_arg: Optional[str]) -> Dict[str, str]:
    if not category_arg:
        return CATEGORIES
    if category_arg not in CATEGORIES:
        print(f"Unknown category: {category_arg}")
        print("Available categories:")
        for cat in CATEGORIES:
            print(f"  {cat}")
        raise SystemExit(1)
    return {category_arg: CATEGORIES[category_arg]}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Army Publications scraper — two-step workflow: build then download.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--category", help="Scope to one category (e.g. training_doctrine/FM)")
    shared.add_argument("--status", help="Filter by status: ACTIVE, INACTIVE, RESCINDED")
    shared.add_argument("--limit", type=int, default=0, help="Max publications per category (0 = all)")
    shared.add_argument("--delay", type=float, default=1.5, help="Seconds between requests (default: 1.5)")
    shared.add_argument("--output", default="downloads", help="Output directory (default: downloads)")
    shared.add_argument("--manifest", default="manifest.jsonl", help="Manifest filename (default: manifest.jsonl)")

    subparsers.add_parser(
        "build",
        help="Crawl all categories and record PDF URLs into a manifest (no downloading).",
        parents=[shared],
    )
    subparsers.add_parser(
        "download",
        help="Download PDFs listed in the manifest.",
        parents=[shared],
    )

    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args)
    elif args.command == "download":
        cmd_download(args)


if __name__ == "__main__":
    main()
