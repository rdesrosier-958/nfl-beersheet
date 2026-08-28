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

Drop exports into `data/manual/` first — see [docs/updating.md](docs/updating.md).

## League settings

Encoded in `config/league.yaml`:

- 10 teams, 13 rounds (9 starters + 4 bench)
- 1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX (RB/WR/TE), 1 D/ST, 1 K
- 0.5 PPR, ESPN-standard yardage and D/ST scoring

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

Share the new sheet with your Google account (Editor) so it appears in Drive. The service account email is in the JSON key (`client_email`).

Or use an existing sheet: paste its URL into `config/sheet_id.txt` and share that sheet with the service account as Editor.
