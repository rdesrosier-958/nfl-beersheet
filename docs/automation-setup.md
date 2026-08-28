# Cursor Automation setup

Use this if the Automations editor opened empty or you are configuring by hand.

## Name

`Daily NFL beer sheet update`

## Description

Morning rebuild with r/fantasyfootball injury news; publishes the Google Sheet.

## Trigger

**On a schedule** → **Every day** at **8:00 AM** (or custom cron `0 8 * * *`).

## Repository

Cloud automations need a **GitHub remote**. Push this repo first, then select it in the editor:

- Repo: your `nfl-beersheet` GitHub repo
- Branch: `main`

Commit `.cursor/skills/update-nfl-beersheet/SKILL.md` before the first run.

## Instructions (paste into the prompt field)

```
Run the daily NFL beer sheet update. Follow `.cursor/skills/update-nfl-beersheet/SKILL.md` exactly.

Hard requirements:
1. Work on `main`. Pull latest before editing.
2. Read r/fantasyfootball and NFL injury news since `data/processed/last_build.txt`.
3. Edit `data/manual/adjustments.csv` when news should move a projection.
4. Run `./scripts/refresh.sh` — must publish every tab to Google Sheets (log must show sheet URL).
5. Report: players adjusted, top-20 changes, cache fallbacks, sheet URL.

If Yahoo rankings changed, note that `data/manual/yahoo_top300.pdf` needs a refresh.
```

## Google Sheets (cloud only)

The automation form does **not** hold secrets. On [Cursor → Cloud Agents → Secrets](https://cursor.com/dashboard?tab=cloud-agents):

| Secret name | Value |
|-------------|--------|
| `CFF_GOOGLE_CREDENTIALS_JSON` | Already set for cff-beersheet — **reuse this** (same service account) |
| `NFL_SHEET_ID` | NFL sheet URL or id (`1Fc0uZPtLXMWA2zG94ijur2_uaCLCVpVYDFaWS-smvb0`) |

`NFL_GOOGLE_CREDENTIALS_JSON` also works if you prefer a separate name. `config/sheet_id.txt` is gitignored, so cloud runs need `NFL_SHEET_ID`.

## Local alternative (already installed)

`launchd` runs `./scripts/daily_refresh.sh` at 8 AM for rankings + sheet publish **without** injury news. Logs: `logs/`.

Uninstall: `launchctl bootout gui/$(id -u)/com.nfl-beersheet.daily`
