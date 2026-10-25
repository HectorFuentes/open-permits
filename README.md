# open-permits

[![CI](https://github.com/HectorFuentes/open-permits/actions/workflows/ci.yml/badge.svg)](https://github.com/HectorFuentes/open-permits/actions/workflows/ci.yml)
![Python 3.10–3.12](https://img.shields.io/badge/python-3.10%E2%80%933.12-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Pull building permits from any [Socrata](https://dev.socrata.com/) open-data portal, filter them by
permit type and date window, dedupe them, and write a clean CSV (and optionally a Markdown table).

- **Zero runtime dependencies**: standard library only (`urllib`, `csv`, `argparse`).
- **Works out of the box** on the City of Orlando permits dataset
  ([`ryhf-m453`](https://data.cityoforlando.net/d/ryhf-m453)); point it at any other Socrata
  dataset with `--domain` / `--dataset` / `--date-field` / `--key`.
- **Cron-friendly**: prints a one-line JSON summary, exits `1` and writes nothing when the window
  is empty, retries transient HTTP errors (403/429/5xx) with backoff, follows `$offset` pagination.
- **Tested offline**: pytest suite runs against recorded API responses, no network needed.

## Quickstart

```bash
git clone https://github.com/HectorFuentes/open-permits.git
cd open-permits
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Orlando plumbing permits issued in the 7 days ending 2026-10-23
open-permits --preset plumbing --until 2026-10-23 -o plumbing.csv --markdown plumbing.md
```

Output on stdout (live run, 25 Oct 2026):

```json
{"source": "https://data.cityoforlando.net/resource/ryhf-m453.json", "window": ["2026-10-17", "2026-10-23"], "fetched": 69, "unique": 69, "duplicates_removed": 0, "written": 69, "csv": "plumbing.csv", "markdown": "plumbing.md"}
```

First rows of `plumbing.csv` (public City of Orlando records, see
[`examples/`](examples/)):

```csv
permit_number,application_type,worktype,permit_address,issue_permit_date,estimated_cost,application_status,neighborhood
PLM2026-13036,Plumbing,Alteration,20 N ORANGE AVE,2026-10-23,3850,Open,Central Business District
PLM2026-13025,Plumbing,New,16659 LONE OAK CIR,2026-10-23,2500,Open,Southeastern Oaks
PLM2026-13023,Plumbing,Alteration,5959 LAKE NONA BLVD,2026-10-23,35000,Open,Lake Nona South
PLM2026-12891,Plumbing,New,37 W HARDING ST,2026-10-23,14000,Open,South Orange
PLM2026-12535,Plumbing,New,13059 BARNACLE WAY,2026-10-23,2500,Open,Meridian Park
```

Markdown output (`--markdown`), here from `--preset roofing --until 2026-10-23 --limit 3`:

| permit_number | application_type | worktype | permit_address | issue_permit_date | estimated_cost | application_status | neighborhood |
|---|---|---|---|---|---|---|---|
| BLD2026-18916 | Building Permit | Roof | 1841 HORNE AVE | 2026-10-23 | 9100 | Open | Richmond Heights |
| BLD2026-18915 | Building Permit | Roof | 5078 LOBELIA DR | 2026-10-23 | 8500 | Open | Timberleaf |
| BLD2026-18892 | Building Permit | Roof | 3106 GOLDEN VIEW LN | 2026-10-23 | 9970 | Open | Bryn Mawr |

## Usage

```text
open-permits [--domain D] [--dataset ID] [--app-token T]
             [--preset {building,electrical,mechanical,plumbing,roofing}]
             [--type-field COL] [--type VALUE ...] [--where SOQL ...]
             [--date-field COL] [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--days N]
             [--fields a,b,c] [--key COL] [--limit N]
             [-o out.csv] [--markdown out.md] [--allow-empty]
```

| Option | Default | What it does |
|---|---|---|
| `--domain`, `--dataset` | `data.cityoforlando.net`, `ryhf-m453` | Which Socrata dataset to read. |
| `--preset` | none | Orlando shortcut: `plumbing`, `mechanical` (HVAC), `electrical`, `building`, `roofing`. |
| `--type` | none | Keep rows where `--type-field` equals this value. Repeat for several types. |
| `--where` | none | Extra flat SoQL condition, e.g. `"worktype='Roof'"`. Repeatable. |
| `--since` / `--until` / `--days` | last 7 days ending yesterday | Inclusive date window on `--date-field`. |
| `--fields` | Orlando: 8 permit columns; other datasets: all columns | Columns to select and write. |
| `--key` | `permit_number` | Column used to dedupe. Rows are sorted newest first, ties by higher key. |
| `--limit` | all | Keep only the N newest rows. |
| `--app-token` | `$SOCRATA_APP_TOKEN` | Optional [app token](https://dev.socrata.com/docs/app-tokens.html) for higher rate limits. |
| `--allow-empty` | off | Write a header-only CSV instead of exiting `1` when nothing matches. |

### Other cities

Any Socrata dataset works. Name the date and key columns of that dataset:

```bash
open-permits --domain data.example.gov --dataset abcd-1234 \
  --date-field issued_date --key permit_id \
  --type-field permit_type --type "Electrical" --type "Mechanical" \
  --since 2026-10-01 --until 2026-10-07 -o permits.csv
```

### Why one query per type?

Some city portals sit behind a web application firewall that rejects parenthesised
`(...) AND ...` SoQL filters. `open-permits` keeps every `$where` clause flat and, when you pass
several `--type` values, runs one query per type and merges the results before deduping.

### Use as a library

```python
from open_permits import SocrataClient, Window, build_where, dedupe, normalize, write_csv
from open_permits.presets import ORLANDO_FIELDS

client = SocrataClient("data.cityoforlando.net", "ryhf-m453")
where = build_where(
    date_field="issue_permit_date",
    window=Window.last_days(7),
    type_field="application_type",
    type_value="Plumbing",
)
rows = normalize(client.iter_rows(where=where, select=ORLANDO_FIELDS), date_fields=["issue_permit_date"])
write_csv(dedupe(rows, "permit_number"), "plumbing.csv")
```

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest -q
```

CI runs lint and tests on Python 3.10, 3.11 and 3.12 for every push and pull request.

## Data notes

Permit data comes from public government open-data portals and is passed through as published;
`open-permits` does not verify or correct it. The Orlando preset selects permit details only
(number, type, work type, address, issue date, estimated cost, status, neighborhood), not owner or
contractor contact fields.

## License

[MIT](LICENSE) © 2026 Hector Fuentes
