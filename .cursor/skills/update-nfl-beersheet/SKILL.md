---
name: update-nfl-beersheet
description: Refresh the NFL fantasy beer sheet for "I'm so excited, I'm so scared!" from ESPN projections, Rotoballer, Yahoo PDF, r/fantasyfootball injury news, then rebuild VBD rankings and publish to Google Sheets. Use when asked to update the NFL beer sheet, refresh fantasy rankings, check NFL injury news, or when running the daily rankings update for this project.
---

# Updating the NFL beer sheet

The pipeline fetches ESPN projections and ranking boards automatically. Your job
in a daily pass is the part a script cannot do: read injury/news and decide
whether anything should move a player in `data/manual/adjustments.csv`.

League: **I'm so excited, I'm so scared!** (ESPN 487681) — 10 teams, 0.5 PPR,
snake draft **Sep 8, 2026**.

## Daily workflow

```
- [ ] 1. Rebuild from live sources
- [ ] 2. Read the news since the last run
- [ ] 3. Edit data/manual/adjustments.csv
- [ ] 4. Rebuild and publish to Google Sheets
- [ ] 5. Report what changed
```

### 1. Rebuild from sources

```bash
cd /Users/rdr/Developer/nfl-beersheet
./scripts/refresh.sh
```

This fetches ESPN + Rotoballer, reads `data/manual/yahoo_top300.pdf`, rescores
under half-PPR rules, and publishes to Google Sheets. If a source times out the
build falls back to cache and prints a warning.

Check `data/processed/last_build.txt` for the previous run time.

### 2. Read the news

Check these, newest first, for anything since the last build:

- **r/fantasyfootball (required):** https://www.reddit.com/r/fantasyfootball/
  - Newest: https://www.reddit.com/r/fantasyfootball/new/.rss?limit=50
  - Injury search: https://www.reddit.com/r/fantasyfootball/search.rss?q=injury+OR+out+OR+doubtful+OR+questionable+OR+cleared&restrict_sr=1&sort=new&limit=50
- Rotoballer NFL news: https://www.rotoballer.com/player-news?sport=nfl
- ESPN NFL injuries: https://www.espn.com/nfl/injuries

What matters, in order:

1. **Practice reports and game status** — OUT, doubtful, limited, cleared.
2. **Role changes** — starter lost/won, committee shifts, trades.
3. **Season-ending injuries** — use `status=OUT` or `SEASON` in adjustments.
4. **Ripple effects** — when one RB is out, bump the backup; do not only move
   the headline name.

Ignore college football and unrelated NFL team news with no fantasy impact.

### 3. Edit adjustments.csv

`data/manual/adjustments.csv` is the only place to encode news:

```csv
player,position,adjust_pct,status,note,expires
Christian McCaffrey,RB,-10,,limited in practice,2026-09-05
Some Player,WR,,OUT,torn ACL,2026-12-31
```

Sizing guidance:

- Minor news / limited practice: **±5–10%**
- Significant doubt or expected missed time: **±15–25%**
- Confirmed OUT / IR / season: **`status=OUT`** (zeroes projection)
- Always set **`expires`** so stale lines drop off automatically

Rules:

- Never edit projections in code to reflect news.
- One line per player — edit the existing line instead of stacking duplicates.
- Delete lines once the public rankings have fully absorbed the news.
- If build prints `! no match for ...`, fix spelling to match ESPN's full name.

### 4. Rebuild and publish

```bash
./scripts/refresh.sh
```

Confirm the log prints the Google Sheet URL. Requires
`config/service-account.json` and `config/sheet_id.txt`.

### 5. Report

- Players adjusted and why (one line each).
- Any change in the top 20 by value.
- Sources that fell back to cache.
- Whether the sheet published successfully.

If no news warranted changes, still rebuild when source data may have moved
(ESPN/Rotoballer update daily).

## Yahoo rankings PDF

Yahoo's article is client-rendered; save it as PDF when rankings change:

1. Open the [Yahoo top-300 article](https://sports.yahoo.com/fantasy/article/fantasy-football-rankings-consensus-top-300-players-160643696.html)
2. Print → Save as PDF
3. Overwrite `data/manual/yahoo_top300.pdf`
4. Rebuild

Roughly weekly until draft week, or when Yahoo publishes a new version.

## Subvertadown (optional)

Reference only — paste into `data/manual/subvertadown_beersheet.csv` when you
export from the BeerSheet PDF. Not blended into VBD.

## What not to change

- `config/league.yaml` — only if ESPN league rules actually change.
- Do not inflate K/DST projections to "fix" value; the model reflects a
  10-team 1-QB league correctly.
