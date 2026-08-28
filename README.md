# nfl-beersheet

Custom fantasy football beer sheet for the ESPN league **"I'm so excited, I'm so scared!"** (10 teams, 0.5 PPR, snake draft).

Rescores projections under your league rules, runs VBD (VOLS + BEER), and compares against ESPN/Yahoo market boards. Subvertadown BeerSheet columns are included for reference.

Forked from the architecture of [cff-beersheet](../cff-beersheet) but stripped down for NFL: no college team pool, no Fantrax custom bonuses, public projection sources align much closer to ESPN scoring.

## Setup

```bash
cd nfl-beersheet
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Build

```bash
./scripts/refresh.sh
```

Drop exports into `data/manual/` for Subvertadown reference and (optionally) Yahoo if the article won't scrape. Live sources:

| Source | How |
|--------|-----|
| ESPN projections | Fetched automatically (`espn_projections` in `config/sources.yaml`) |
| Rotoballer top-400 | Fetched automatically from the URL in `sources.yaml` |
| Yahoo top-300 | Auto-fetch when the page renders; otherwise paste into `data/manual/yahoo_rankings.csv` |
| Subvertadown | `data/manual/subvertadown_beersheet.csv` (reference columns only) |

## League settings

Each league profile lives in `config/leagues/`:

| Profile | League | Scoring |
|---------|--------|---------|
| `espn-half-ppr` | I'm so excited, I'm so scared! (10-team ESPN) | 0.5 PPR, 1 FLEX |
| `yahoo-full-ppr` | Football for All of Us (12-team Yahoo) | Full PPR, 3 WR, no FLEX |

Build a specific league:

```bash
./scripts/refresh.sh --league yahoo-full-ppr
# or: NFL_LEAGUE=yahoo-full-ppr ./scripts/refresh.sh
```

Output lands in `output/<profile>/`.

## Output

| File | Description |
|------|-------------|
| `output/beersheet.csv` | Full value board |
| `output/beersheet_draftable.csv` | Top ~115 names (draft picks + cushion) |
| `output/beersheet.xlsx` | Multi-tab workbook |

Key columns: `value`, `vols`, `beer`, `edge_vs_board`, `subvertadown_val`, `subvertadown_adp`.

## Tests

```bash
PYTHONPATH=src pytest tests/ -q
```

## Google Sheet

Reuse the same service account as [cff-beersheet](../cff-beersheet):

```bash
cp ../cff-beersheet/config/service-account.json config/service-account.json
PYTHONPATH=src python -m nfl init-sheet   # creates sheet, writes config/sheet_id.txt
./scripts/refresh.sh                      # build + publish
```

Share the new sheet with your Google account (Editor) so it appears in Drive.

**Manual setup** (if `init-sheet` fails — Drive API not enabled on the GCP project):

1. Create a blank Google Sheet in your Drive (e.g. "NFL Beer Sheet — I'm so excited")
2. Share it with `beersheet-writer@cff-beersheet.iam.gserviceaccount.com` as **Editor**
3. Paste the sheet URL into `config/sheet_id.txt`
4. Run `./scripts/refresh.sh`

Or use an existing sheet: paste its URL into `config/sheet_id.txt` and share that sheet with the service account as Editor.

## Daily automation

Two layers:

| Layer | What it does |
|-------|----------------|
| **Local schedule (8 AM)** | `scripts/install-daily-launchd.sh` — fetches ESPN/Rotoballer, rebuilds, publishes **both** sheets |
| **News + injuries** | Cursor Automation or manual run using `.cursor/skills/update-nfl-beersheet/SKILL.md` — scans r/fantasyfootball, edits `adjustments.csv`, rebuilds |

Install the local daily job:

```bash
./scripts/install-daily-launchd.sh
```

Logs: `logs/daily-YYYY-MM-DD.log`

For the **full** daily pass (injuries + adjustments), create a Cursor Automation on a schedule that follows the update skill, or ask in chat: *"update the NFL beer sheet"*.
