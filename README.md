# Army Publications Scraper

Downloads PDFs from the [Army Publishing Directorate](https://armypubs.army.mil) and organizes them by publication type. Covers all 43 public-facing categories across Administrative, Technical & Equipment, Training and Doctrine, Engineering, Medical, and Miscellaneous sections.

Built for RAG testing and document research use cases — the corpus includes field manuals, technical manuals with hand drawings, administrative regulations, training circulars, and more.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Download everything (thousands of PDFs — will take several hours)
python scraper.py

# Single category
python scraper.py --category training_doctrine/FM

# Preview without downloading
python scraper.py --category training_doctrine/FM --dry-run

# Limit downloads per category (useful for testing)
python scraper.py --category administrative/AR --limit 10

# Filter by publication status
python scraper.py --status ACTIVE

# Adjust request delay (default: 1.5s between requests)
python scraper.py --delay 2.0

# Custom output directory
python scraper.py --output /path/to/my/docs
```

## Output Structure

```
downloads/
├── administrative/
│   ├── AR/             # Army Regulations
│   ├── ALARACT/        # Army ALARACT Messages
│   ├── ArmyDir/        # Army Directives
│   ├── AGO_active/     # Army General Orders (Active)
│   ├── AGO_inactive/   # Army General Orders (Inactive)
│   ├── DAMEMO/         # DA Memorandums
│   ├── HQDA_Policy/    # HQDA Policy Notices
│   ├── PAM/            # DA Pamphlets
│   ├── POG/            # Principal Officials' Guidance
│   ├── PPM/            # Proponent Policy Memorandums
│   └── Web_Series/     # Administrative Series Collection
├── technical_equipment/
│   ├── EM/             # Electronic Media
│   ├── FT/             # Firing Tables
│   ├── LO/             # Lubrication Orders
│   ├── MWO/            # Modification Work Orders
│   ├── SB/             # Supply Bulletins
│   ├── SC/             # Supply Catalogs
│   ├── TB/             # Technical Bulletins
│   ├── TM_1_8/         # Technical Manuals (Range 1–8)
│   ├── TM_9/           # Technical Manuals (Range 9)
│   ├── TM_10/          # Technical Manuals (Range 10)
│   ├── TM_11_4/        # Technical Manuals (Range 11-4)
│   ├── TM_11_5/        # Technical Manuals (Range 11-5)
│   ├── TM_11_6_7/      # Technical Manuals (Range 11-6 & 7)
│   └── TM_14_750/      # Technical Manuals (Range ≥14)
├── training_doctrine/
│   ├── ADP/            # Army Doctrine Publications
│   ├── ADRP/           # Army Doctrine Reference Publications
│   ├── ATP/            # Army Techniques Publications
│   ├── ATTP/           # Army Tactics, Techniques, and Procedures
│   ├── CTA/            # Common Tables of Allowance
│   ├── FM/             # Field Manuals
│   ├── GTA/            # Graphic Training Aids
│   ├── JTA/            # Joint Tables of Allowance
│   ├── PB/             # Professional Bulletins
│   ├── STP/            # Soldier Training Publications
│   └── TC/             # Training Circulars
├── engineering/
│   ├── TM/             # Technical Manuals
│   └── TB/             # Technical Bulletins
├── medical/
│   ├── TM/             # Technical Manuals
│   ├── TB/             # Technical Bulletins
│   ├── SB/             # Supply Bulletins
│   └── SC/             # Supply Catalogs
└── miscellaneous/
    └── MCM/            # Manuals for Courts-Martial
```

Files are named using the official filename from the publication URL (e.g., `ARN43687-FM_1-000-WEB-2.pdf`).

## Logging

Every publication attempt is appended to `downloads/download_log.jsonl`:

```json
{
  "pub_id": "1031029",
  "pub_number": "FM 1",
  "category": "training_doctrine/FM",
  "status": "ACTIVE",
  "pdf_url": "https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN43687-FM_1-000-WEB-2.pdf",
  "local_path": "downloads/training_doctrine/FM/ARN43687-FM_1-000-WEB-2.pdf",
  "result": "downloaded",
  "timestamp": "2026-05-14T18:13:58.486163"
}
```

Possible `result` values: `downloaded`, `skipped` (file already exists), `no_pdf` (publication has no downloadable PDF), `http_404`, `error:<message>`.

## Resume

The scraper skips any file that already exists with a non-zero size. Re-running after an interruption will pick up where it left off.

## Notes

- Only public/unclassified documents are available without a CAC (Common Access Card)
- Some publications are listed as ACTIVE but have no downloadable PDF (marked `no_pdf` in the log)
- Default delay is 1.5 seconds per request — increase with `--delay` if you see rate limiting
- The `downloads/` directory is excluded from git via `.gitignore`
