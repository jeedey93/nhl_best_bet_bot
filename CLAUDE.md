# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NHL and NBA sports betting analysis bot. Fetches game schedules and odds, sends them to Google Gemini AI for predictions, compares morning vs afternoon lines for movement, and publishes results to a GitHub Pages site at parieurdiscipline.com. Runs via GitHub Actions twice daily (7am and 3pm Montreal time).

## Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Required environment variables in `.env`:
- `GOOGLE_API_KEY` — Google Gemini API key
- `ODDS_API_KEY` — The Odds API key
- `GH_API_TOKEN` — GitHub PAT (for voting system, Vercel only)

## Key Commands

```bash
# Generate predictions (run from repo root)
python scripts/generate_nhl_predictions.py
python scripts/generate_nba_predictions.py

# Force playoff prompt mode
PLAYOFF_MODE=true python scripts/generate_nhl_predictions.py

# Compare morning vs afternoon predictions (3pm only)
python scripts/compare_nhl_predictions.py
python scripts/compare_nba_predictions.py

# Generate featured picks (best plays)
python scripts/generate_featured_picks.py --run_time 3pm

# Fetch results and analyze accuracy
python scripts/analyze_nhl_results.py
python scripts/analyze_nba_results.py
python scripts/generate_combined_summary.py

# Rebuild website
python scripts/generate_website.py           # final (3pm)
python scripts/generate_website.py --preliminary  # early (7am)
python scripts/generate_daily_picks_table.py
python scripts/generate_early_picks_page.py

# Games pages
python scripts/generate_nhl_games_page.py
python scripts/generate_nba_games_page.py

# Cache management
python scripts/cleanup_cache.py
python -c "from data.odds import get_nhl_odds; get_nhl_odds(force_refresh=True)"

# Test API connections
python test_server.py
```

## Architecture

### Data Flow

```
Official NHL/NBA APIs → data/nhl_games.py, data/nba_games.py  (today's schedule)
The Odds API          → data/odds.py  (moneyline/totals/spreads, file-cached 2hr)
Web scrapers          → scripts/scrape_nhl_absences.py, data/starting_goalies.py
                     ↓
Google Gemini AI ← prompts/{sport}_prompt.txt + games + odds + history + injuries
                     ↓
data/predictions/nhl/  or  data/predictions/nba/  (timestamped .txt files)
                     ↓
compare_*.py  →  final unified prediction file  →  generate_website.py  →  docs/
                     ↓
analyze_*_results.py  →  data/bot_results/{sport}/  →  generate_combined_summary.py
```

### Dual-Run System

Both sports run twice daily to capture line movement. The 7am run saves early predictions; the 3pm run generates final predictions and compares against the morning.

Run time is detected via:
1. `NHL_RUN_TIME` / `NBA_RUN_TIME` env var (GitHub Actions sets this)
2. Current Montreal hour: 6am–12pm → 7am run; otherwise → 3pm run

Output naming: `nhl_daily_predictions_7am_YYYY-MM-DD.txt`, `..._3pm_...`, `..._{date}.txt` (final comparison).

### Playoff Mode

Set `PLAYOFF_MODE=true` (GitHub Actions repository variable) to switch prompts from regular-season (`nhl_prompt.txt` / `nba_prompt.txt`) to playoff variants (`nhl_playoff_prompt.txt` / `nba_playoff_prompt.txt`). The comparison scripts also use `prompts/compare_prompt.txt`.

### Prompt System

Prompts live in `prompts/` and use `{{PLACEHOLDER}}` substitution at runtime:
- `nhl_prompt.txt` / `nhl_prompt_7am.txt` / `nhl_playoff_prompt.txt`
- `nba_prompt.txt` / `nba_playoff_prompt.txt`
- `compare_prompt.txt` — used by compare scripts
- `bet_of_the_day.txt` / `summarize_bullet_points_prompt.txt`

### Caching

- **Odds** (`data/odds_cache.py`): `data/cache/{sport}_odds_{date}.json`, 2hr TTL
- **Standings** (`data/standings_cache.py`): `data/cache/{sport}_standings.json`, 4hr TTL
- Both follow: check cache → return if valid → else fetch and save

### Team Name Mapping

The Odds API uses different names than official APIs. Mappings are in `data/odds.py`:
- `NHL_TEAM_NAME_MAP` — e.g. `"Montréal" → "Montreal"`
- `NBA_TEAM_NAME_MAP` — e.g. `"LA Clippers" → "Los Angeles Clippers"`

Always update these when team names don't match.

### Website & Email Pipeline

`generate_website.py` reads the latest prediction files and bot_results to build `docs/index.html` and `docs/daily-picks.html`. At 3pm, `generate_complete_email.py` builds an HTML email that is sent to `SUBSCRIBER_LIST` (comma-separated env var). Unsubscribe tokens are generated per-recipient and embedded in each email.

### GitHub Actions

- **`daily_predictions.yml`** — runs at 10:15 and 18:15 UTC; detects 7am vs 3pm, runs predictions, compare (3pm), website rebuild, then sends emails (3pm)
- **`daily_results.yml`** — runs at 10:00 UTC; analyzes yesterday's results, rebuilds performance dashboard
- Other workflows: `generate_games_pages.yml`, `send_email_notification.yml`, `update_pool_stats.yml`, `update_playoff_index.yml`

All workflows push to `master` via `GH_PAT` secret.

### Voting System

Vercel Serverless Function at `api/vote.js` stores votes in GitHub Issues (titled `Votes: YYYY-MM-DD`). Uses `GH_API_TOKEN` secret in Vercel. See `VOTING_SETUP.md` for setup.

## File Layout

```
data/
├── nhl_games.py / nba_games.py   — official API schedule wrappers
├── odds.py                        — The Odds API wrapper + team name maps
├── odds_cache.py / standings_cache.py
├── starting_goalies.py
├── predictions/nhl/ , predictions/nba/   — AI output files
├── bot_results/nhl/ , bot_results/nba/  — results analysis files
├── bot_results/total_results_summary.txt
├── cache/                         — auto-managed cache files
└── teams/                         — scraped lineup files (after 2pm)

scripts/
├── generate_nhl_predictions.py / generate_nba_predictions.py
├── compare_nhl_predictions.py / compare_nba_predictions.py
├── analyze_nhl_results.py / analyze_nba_results.py
├── generate_website.py            — main site rebuild
├── generate_featured_picks.py     — bet of the day
├── generate_daily_picks_table.py / generate_early_picks_page.py
├── generate_combined_summary.py / generate_performance_dashboard.py
├── generate_complete_email.py / replace_unsub.py
├── scrape_nhl_absences.py / scrape_nhl_daily_lines.py / scrape_nhl_stats.py
└── cleanup_cache.py

prompts/                           — Gemini prompt templates
docs/                              — GitHub Pages static site
api/                               — Vercel serverless functions
```

## Important Notes

- **Timezone**: All date logic uses `America/Toronto` (Montreal time, UTC-4/5)
- **Branch**: Active development on `master`; `main` is the PR target listed in README
- **Historical context**: AI prompts include last 10 days of results for pattern recognition
- **Goalie stats**: Cached in `data/goalie_stats_cache.json`; lineup files in `data/teams/` are regenerated daily after 2pm
