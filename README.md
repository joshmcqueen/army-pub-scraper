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

To deactivate the virtual environment when you're done:

```bash
deactivate
```

## Usage

```bash
# Activate the virtual environment
source .venv/bin/activate

# Download all categories (thousands of PDFs — will take several hours)
python scraper.py

# Single category
python scraper.py --category training_doctrine/FM

# Preview without downloading
python scraper.py --category training_doctrine/FM --dry-run

# Limit downloads per category (useful for testing)
python scraper.py --category administrative/AR --limit 10

# Filter by publication status (ACTIVE, INACTIVE, or RESCINDED)
python scraper.py --status ACTIVE

# Adjust request delay in seconds (default: 1.5)
python scraper.py --delay 2.0

# Custom output directory
python scraper.py --output /path/to/my/docs
```

Run `python scraper.py --help` for the full option list.

## Categories

| Path | Publications |
|------|-------------|
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
| `engineering/TM` | Technical Manuals |
| `engineering/TB` | Technical Bulletins |
| `medical/TM` | Technical Manuals |
| `medical/TB` | Technical Bulletins |
| `medical/SB` | Supply Bulletins |
| `medical/SC` | Supply Catalogs |
| `miscellaneous/MCM` | Manuals for Courts-Martial |

## Output

Files land in `downloads/{category}/` and are named using the official filename from the publication URL (e.g., `ARN43687-FM_1-000-WEB-2.pdf`).

Every attempt is logged to `downloads/download_log.jsonl`:

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

`result` values: `downloaded`, `skipped` (already exists), `no_pdf` (no downloadable file), `http_404`, `error:<message>`.

The scraper skips any file that already exists with a non-zero size, so re-running after an interruption resumes where it left off.

## Notes

- Only public/unclassified documents are available without a CAC (Common Access Card)
- Some publications are listed as ACTIVE but have no downloadable PDF — these are logged as `no_pdf`
- The `downloads/` and `.venv/` directories are excluded from git via `.gitignore`
