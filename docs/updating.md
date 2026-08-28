# Updating the NFL beer sheet

League: **I'm so excited, I'm so scared!** (ESPN 487681) — 10 teams, 0.5 PPR, 13 rounds.

## Quick refresh

```bash
./scripts/refresh.sh
```

Outputs land in `output/beersheet.csv`, `output/beersheet_draftable.csv`, and `output/beersheet.xlsx`.

## Live sources (automatic)

| Source | Role |
|--------|------|
| ESPN projections API | Stat backbone → rescored to half-PPR |
| [Rotoballer top-400](https://www.rotoballer.com/top-400-updated-half-ppr-fantasy-football-rankings-2026/1910000) | Market board |
| [Yahoo top-300](https://sports.yahoo.com/fantasy/article/fantasy-football-rankings-consensus-top-300-players-160643696.html) | Second market board (see manual fallback below) |

Configured in `config/sources.yaml`. Run `./scripts/refresh.sh` to fetch and rebuild (~600 players).

## Manual data files

Only needed for Subvertadown reference, Yahoo fallback, and news nudges:

| File | Source | Role |
|------|--------|------|
| `yahoo_top300.pdf` | Yahoo article (Print/Save as PDF) | Market board — drop export in `data/manual/` |
| `subvertadown_beersheet.csv` | [Subvertadown BeerSheet](https://subvertadown.com) | Reference VAL/ADP columns only |
| `adjustments.csv` | You / r/fantasyfootball news | % nudges to projections |

```csv
rank,player,team,position,pos_rank
```

`pos_rank` is optional but improves edge-vs-board columns.

### Subvertadown format

Export or transcribe from the BeerSheet PDF:

```csv
player,team,position,val,adp,bye
```

Subvertadown is **not** blended into VBD (it is already VBD output for a similar league). It shows up as `subvertadown_val` and `subvertadown_adp` on the sheet for comparison.

## News adjustments

Edit `data/manual/adjustments.csv` when r/fantasyfootball or beat reporters move a player:

```csv
player,position,adjust_pct,status,note,expires
Player Name,RB,-10,,questionable hamstring,2026-09-15
```

- `adjust_pct`: scale stats (e.g. `-15` = 85% of projection)
- `status`: `OUT` / `IR` / `SEASON` zeroes the player
- `expires`: ISO date; row is ignored after that day

## Google Sheet (optional)

1. Create a Google Sheet and share it with your service account email.
2. Save the sheet ID or URL to `config/sheet_id.txt`.
3. Place credentials at `config/service-account.json`.
4. Run `./scripts/refresh.sh` (publishes by default) or `python -m nfl sheet` to re-push cached data.

## CLI

```bash
PYTHONPATH=src python -m nfl build          # full build
PYTHONPATH=src python -m nfl build --offline  # use cached projections
PYTHONPATH=src python -m nfl picks 3        # snake pick numbers for slot 3
```

## Reddit reference

Subvertadown thread (snake, 0.5 PPR):  
https://www.reddit.com/r/fantasyfootball/comments/1vi0t3r/holdmybeersheets_snake_draft_version_the_lean/
