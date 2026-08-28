# Updating the NFL beer sheet

League: **I'm so excited, I'm so scared!** (ESPN 487681) — 10 teams, 0.5 PPR, 13 rounds.

## Quick refresh

```bash
./scripts/refresh.sh
```

Outputs land in `output/beersheet.csv`, `output/beersheet_draftable.csv`, and `output/beersheet.xlsx`.

## Manual data files

All sources live under `data/manual/`. Re-export from each site and overwrite the CSV.

| File | Source | Role |
|------|--------|------|
| `fantasypros_projections.csv` | [FantasyPros](https://www.fantasypros.com/nfl/projections/) | Stat backbone → VBD |
| `espn_rankings.csv` | ESPN league rankings | Market board |
| `yahoo_rankings.csv` | Yahoo rankings | Second market board |
| `subvertadown_beersheet.csv` | [Subvertadown BeerSheet](https://subvertadown.com) | Reference VAL/ADP columns only |
| `adjustments.csv` | You / r/fantasyfootball news | % nudges to projections |

### FantasyPros projections format

```csv
player,team,position,games,bye,pass_yd,pass_td,pass_int,rush_yd,rush_td,rec,rec_yd,rec_td
```

### Ranking CSV format (ESPN / Yahoo)

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
