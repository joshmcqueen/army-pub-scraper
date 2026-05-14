# Army Publications Scraper

Downloads PDFs from the [Army Publishing Directorate](https://armypubs.army.mil) and organizes them by publication type. Covers all 43 public-facing categories across Administrative, Technical & Equipment, Training and Doctrine, Engineering, Medical, and Miscellaneous sections.

Built for RAG testing and document research — the corpus is a diverse mix of field manuals, technical manuals with engineering drawings, administrative regulations, training circulars, legal documents, and more.

## Requirements

- Python 3.9+
- macOS / Linux

## Setup

```bash
git clone https://github.com/joshmcqueen/army-pub-scraper.git
cd army-pub-scraper

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

```bash
source .venv/bin/activate

# Step 1 — crawl all categories and write downloads/manifest.jsonl (no downloading yet)
python scraper.py build

# Step 2 — download every PDF listed in the manifest
python scraper.py download
```

The full build + download run covers thousands of publications and will take several hours. Use `--category` and `--limit` to test with a subset first (see below).

## Two-Step Workflow

Splitting into two steps lets you inspect what's available before committing to a long download, and avoids creating empty directories for categories that have no public PDFs.

### `build` — scan and record PDF URLs

```bash
# All categories
python scraper.py build

# One category only
python scraper.py build --category training_doctrine/FM

# Limit per category (useful for a quick smoke test)
python scraper.py build --category administrative/AR --limit 10

# Active publications only
python scraper.py build --status ACTIVE

# Resume an interrupted build (already-seen pub_ids are skipped automatically)
python scraper.py build
```

### `download` — pull PDFs from the manifest

```bash
# Download everything in the manifest
python scraper.py download

# One category only
python scraper.py download --category training_doctrine/FM

# Limit per category
python scraper.py download --limit 10

# Slow down requests if you're seeing rate limiting
python scraper.py download --delay 2.0

# Resume after interruption (existing files are skipped automatically)
python scraper.py download
```

Both commands accept `--output` to change the base directory (default: `downloads/`) and `--manifest` to change the manifest filename (default: `manifest.jsonl`).

Run `python scraper.py build --help` or `python scraper.py download --help` for the full option list.

## Categories

### Administrative
| `--category` | Publication Type |
|---|---|
| `administrative/AR` | Army Regulations |
| `administrative/ALARACT` | Army ALARACT Messages |
| `administrative/ArmyDir` | Army Directives |
| `administrative/AGO_active` | Army General Orders (Active) |
| `administrative/AGO_inactive` | Army General Orders (Inactive) |
| `administrative/DAMEMO` | DA Memorandums |
| `administrative/HQDA_Policy` | HQDA Policy Notices |
| `administrative/PAM` | DA Pamphlets |
| `administrative/POG` | Principal Officials' Guidance |
| `administrative/PPM` | Proponent Policy Memorandums |
| `administrative/Web_Series` | Administrative Series Collection |

### Technical & Equipment
| `--category` | Publication Type |
|---|---|
| `technical_equipment/EM` | Electronic Media |
| `technical_equipment/FT` | Firing Tables |
| `technical_equipment/LO` | Lubrication Orders |
| `technical_equipment/MWO` | Modification Work Orders |
| `technical_equipment/SB` | Supply Bulletins |
| `technical_equipment/SC` | Supply Catalogs |
| `technical_equipment/TB` | Technical Bulletins |
| `technical_equipment/TM_1_8` | Technical Manuals (Range 1–8) |
| `technical_equipment/TM_9` | Technical Manuals (Range 9) |
| `technical_equipment/TM_10` | Technical Manuals (Range 10) |
| `technical_equipment/TM_11_4` | Technical Manuals (Range 11-4) |
| `technical_equipment/TM_11_5` | Technical Manuals (Range 11-5) |
| `technical_equipment/TM_11_6_7` | Technical Manuals (Range 11-6 & 7) |
| `technical_equipment/TM_14_750` | Technical Manuals (Range ≥14) |

### Training & Doctrine
| `--category` | Publication Type |
|---|---|
| `training_doctrine/ADP` | Army Doctrine Publications |
| `training_doctrine/ADRP` | Army Doctrine Reference Publications |
| `training_doctrine/ATP` | Army Techniques Publications |
| `training_doctrine/ATTP` | Army Tactics, Techniques, and Procedures |
| `training_doctrine/CTA` | Common Tables of Allowance |
| `training_doctrine/FM` | Field Manuals |
| `training_doctrine/GTA` | Graphic Training Aids |
| `training_doctrine/JTA` | Joint Tables of Allowance |
| `training_doctrine/PB` | Professional Bulletins |
| `training_doctrine/STP` | Soldier Training Publications |
| `training_doctrine/TC` | Training Circulars |

### Engineering
| `--category` | Publication Type |
|---|---|
| `engineering/TM` | Technical Manuals |
| `engineering/TB` | Technical Bulletins |

### Medical
| `--category` | Publication Type |
|---|---|
| `medical/TM` | Technical Manuals |
| `medical/TB` | Technical Bulletins |
| `medical/SB` | Supply Bulletins |
| `medical/SC` | Supply Catalogs |

### Miscellaneous
| `--category` | Publication Type |
|---|---|
| `miscellaneous/MCM` | Manuals for Courts-Martial |

## Output Files

### `downloads/manifest.jsonl`
Written by `build`. One JSON object per publication, including those with no available PDF (`"pdf_url": null`). Safe to inspect or filter with `jq` before running `download`.

```json
{
  "pub_id": "1031029",
  "pub_number": "FM 1",
  "category": "training_doctrine/FM",
  "status": "ACTIVE",
  "date": "04/16/2025",
  "title": "THE ARMY: A PRIMER TO OUR PROFESSION OF ARMS",
  "proponent": "OCSA",
  "pdf_url": "https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN43687-FM_1-000-WEB-2.pdf",
  "scanned_at": "2026-05-14T18:13:45.123456"
}
```

### `downloads/{category}/{filename}.pdf`
Written by `download`. Named using the official filename from the source URL (e.g., `ARN43687-FM_1-000-WEB-2.pdf`). Directories are only created when a file is actually written — categories with no available PDFs leave no trace on disk.

### `downloads/download_log.jsonl`
Written by `download`. One entry per attempted download.

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

`result` values: `downloaded`, `skipped` (already exists), `no_pdf`, `http_404`, `error:<message>`.

## Notes

- Only public/unclassified documents are available without a CAC (Common Access Card)
- Some publications are listed as ACTIVE but have no downloadable PDF — these appear in the manifest with `"pdf_url": null` and are skipped by `download`
- The `downloads/` and `.venv/` directories are excluded from git via `.gitignore`
