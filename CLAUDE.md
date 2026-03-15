# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a sports betting analysis bot for NHL and NBA games. It uses The Odds API to fetch games and odds, then leverages Google Gemini AI to generate disciplined betting predictions. The bot runs twice daily (7am and 3pm Montreal time) via GitHub Actions, compares predictions across time periods to identify line movement opportunities, and publishes results to GitHub Pages.

## Environment Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Required environment variables in `.env`:
- `GOOGLE_API_KEY` - Google Gemini API key
- `ODDS_API_KEY` - The Odds API key

## Key Commands

### Run Daily Predictions
```bash
# NHL predictions (uses today's date automatically)
python scripts/nhl_predictions_daily_run.py

# NBA predictions (detects 7am vs 3pm run based on Montreal time)
python scripts/nba_predictions_daily_run.py

# Manual override for NBA run time
NBA_RUN_TIME=7am python scripts/nba_predictions_daily_run.py
NBA_RUN_TIME=3pm python scripts/nba_predictions_daily_run.py
```

### Run Daily Results
```bash
# Fetch yesterday's game results and analyze predictions
python scripts/nhl_results_daily_run.py
python scripts/nba_results_daily_run.py

# Generate combined results summary
python scripts/total_results_daily_run.py
```

### Compare Predictions (3pm only)
```bash
# Compare 7am vs 3pm predictions to identify line movement
python scripts/nhl_predictions_compare.py
python scripts/nba_predictions_compare.py
```

### Generate Bet of the Day
```bash
# Extract best plays from both sports
python scripts/dual_bet_of_the_day.py --run_time 3pm
```

### Update Latest Predictions (for GitHub Pages)
```bash
python scripts/update_latest_predictions.py
```

### Testing
```bash
# Test API connections
python test_nhl_odds.py
python test_nhl_games.py
python test_nba_odds.py
python test_nba_games.py
```

### Cache Management
```bash
# Clean up old cache files (keeps last 2 days)
python scripts/cleanup_cache.py

# Force refresh odds (bypass cache)
python -c "from data.odds import get_nhl_odds; get_nhl_odds(force_refresh=True)"
```

## Architecture

### Data Flow

1. **Fetch Games** → `data/nhl_games.py`, `data/nba_games.py`
   - Uses official NHL/NBA APIs to get today's schedule
   - Returns game IDs, teams, and start times

2. **Fetch Odds** → `data/odds.py`
   - Queries The Odds API for moneyline (h2h), totals (O/U), and spreads
   - Filters to current day using Montreal timezone (America/Toronto)
   - Maps team names between official APIs and odds providers
   - **Uses file-based caching** (see Caching System below) to minimize API calls

3. **Match Odds to Games** → `data/odds.py`
   - Uses fuzzy team name mapping (`NHL_TEAM_NAME_MAP`, `NBA_TEAM_NAME_MAP`)
   - Handles variations like "Montréal Canadiens" vs "Montreal Canadiens"

4. **Analyze with AI** → `*_daily_run.py` scripts
   - Reads sport-specific prompts from `prompts/` directory
   - Injects:
     - Today's games with odds
     - Historical results (last 10 days for context)
     - NHL: Current injury reports from scraper
   - Calls Google Gemini API for analysis
   - Saves predictions to `predictions/{sport}/`

5. **Compare Predictions** → `*_compare.py` scripts
   - Reads both 7am and 3pm predictions
   - Uses `prompts/compare_prompt.txt` to identify consensus plays
   - Highlights line movement opportunities
   - Generates final unified prediction file

6. **Results Analysis** → `*_results_daily_run.py`
   - Fetches final scores from official APIs
   - Compares against predictions
   - Calculates win/loss for each pick
   - Saves to `bot_results/{sport}/`

### Prompt System

All AI prompts are in `prompts/`:
- `nhl_prompt.txt` - NHL prediction template
- `nba_prompt.txt` - NBA prediction template
- `compare_prompt.txt` - Cross-time comparison template
- `bet_of_the_day.txt` - Best play extraction template

Prompts use placeholders like `{{RESULTS_TEXT}}`, `{{TODAY_DATE}}`, `{{HISTORICAL_RESULTS}}` which are replaced at runtime.

### Dual-Run System (NBA)

NBA predictions run twice daily to capture line movement:
- **7am Montreal time**: Early odds (overnight markets)
- **3pm Montreal time**: Updated odds (closer to game time)

Scripts detect run time via:
1. `NBA_RUN_TIME` or `NHL_RUN_TIME` environment variable (GitHub Actions)
2. Current Montreal timezone hour (local development):
   - **6am-12pm** → considered 7am run (versatile window for scheduling variations)
   - **1pm-5:59am** → considered 3pm run

Output files include run time suffix:
- `nba_daily_predictions_7am_2026-03-04.txt`
- `nba_daily_predictions_3pm_2026-03-04.txt`
- `nba_daily_predictions_2026-03-04.txt` (final comparison result)

### Team Name Mapping

The Odds API uses different team names than official NHL/NBA APIs. Critical mappings in `data/odds.py`:

```python
NHL_TEAM_NAME_MAP = {
    "Montréal": "Montreal",
    # ... more mappings
}

NBA_TEAM_NAME_MAP = {
    "LA Clippers": "Los Angeles Clippers",
    # ... more mappings
}
```

When adding new teams or fixing match issues, update these dictionaries.

### Caching System

The bot uses file-based caching to minimize API calls and reduce costs:

#### Odds Cache (`data/odds_cache.py`)
- **Purpose**: Cache odds data from The Odds API (which has usage limits/costs)
- **Location**: `data/cache/{sport}_odds_{date}.json`
- **TTL**: 2 hours (balances freshness with dual-run efficiency)
- **Behavior**:
  - 7am run: Usually fetches fresh odds (no cache from previous day)
  - 3pm run: May use 7am cache if still valid (< 2 hours old), saving API calls
  - Cache keys include date to prevent stale cross-day data
- **Usage**:
  ```python
  from data.odds import get_nhl_odds, get_nba_odds

  odds = get_nhl_odds()  # Uses cache if available
  odds = get_nhl_odds(force_refresh=True)  # Bypass cache
  ```
- **Maintenance**: Old cache files automatically cleaned up by `scripts/cleanup_cache.py` (runs daily at 7am)

#### Standings Cache (`data/standings_cache.py`)
- **Purpose**: Cache team standings (less volatile than odds)
- **Location**: `data/cache/{sport}_standings.json`
- **TTL**: 4 hours (standings change less frequently)
- **Usage**:
  ```python
  from data.standings_cache import get_nhl_standings, get_nba_standings

  standings = get_nhl_standings()  # Uses cache if available
  standings = get_nhl_standings(force_refresh=True)  # Bypass cache
  ```

Both caching systems follow the same pattern:
1. Check if cache file exists and is within TTL
2. Return cached data if valid
3. Otherwise, fetch from API and save to cache
4. Old cache files (> 2 days) cleaned up automatically

### GitHub Actions Automation

Three workflows in `.github/workflows/`:

1. **daily_predictions.yml** - Runs at 7am and 3pm Montreal time (11:00 and 19:00 UTC during daylight saving)
   - Executes NHL and NBA prediction scripts
   - Compares predictions (3pm only)
   - Generates dual bet of the day (3pm only)
   - Commits to `master` branch

2. **daily_results.yml** - Runs at 6am Montreal time (10:00 UTC during daylight saving)
   - Fetches yesterday's game results
   - Analyzes prediction accuracy
   - Commits to `master` branch

3. **update_predictions.yml** - Manual trigger or scheduled
   - Updates `LATEST_PREDICTIONS.md` for GitHub Pages

All workflows use repository secrets for API keys and push via `GH_PAT` token.

## File Structure

```
predictions/
├── nhl/                           # NHL prediction outputs
│   └── nhl_daily_predictions_YYYY-MM-DD.txt
└── nba/                           # NBA prediction outputs
    ├── nba_daily_predictions_7am_YYYY-MM-DD.txt
    ├── nba_daily_predictions_3pm_YYYY-MM-DD.txt
    └── nba_daily_predictions_YYYY-MM-DD.txt  # Final comparison

bot_results/
├── nhl/                           # NHL results analysis
│   └── nhl_daily_results_YYYY-MM-DD.txt
└── nba/                           # NBA results analysis
    └── nba_daily_results_YYYY-MM-DD.txt

data/
├── nhl_games.py                   # NHL schedule API wrapper
├── nba_games.py                   # NBA schedule API wrapper
├── odds.py                        # The Odds API wrapper (with caching)
├── odds_cache.py                  # Odds caching system
├── standings_cache.py             # Standings caching system
├── polymarket_odds.py             # Alternative odds source
├── cache/                         # Cache directory
│   ├── nhl_odds_YYYY-MM-DD.json   # NHL odds cache (2hr TTL)
│   ├── nba_odds_YYYY-MM-DD.json   # NBA odds cache (2hr TTL)
│   ├── nhl_standings.json         # NHL standings cache (4hr TTL)
│   └── nba_standings.json         # NBA standings cache (4hr TTL)
└── teams/                         # Team lineup files (auto-generated)
    ├── Team_Name.txt              # Individual team lineup files
    └── README.md                  # Documentation

prompts/                           # AI prompt templates

docs/                              # GitHub Pages site
└── index.md                       # Generated daily from predictions
```

## Team Lineup Files

Scraped lineup data is automatically saved to `data/teams/` when lineups are fetched (after 2pm Montreal time). Each team gets its own file containing:

- **Forward Lines**: All 4 forward line combinations
- **Defense Pairs**: All 3 defense pairings
- **Goalies**: Starting and backup goalies
- **Scratched/Injured**: Players who are out

Files are timestamped and regenerated daily. See `data/teams/README.md` for format details.

## Important Notes

- **Timezone**: All scripts use Montreal time (America/Toronto, UTC-5/4) for determining "today"
- **API Rate Limits**: The Odds API has usage limits; caching system reduces redundant calls
- **Caching**: Odds are cached for 2 hours, standings for 4 hours; use `force_refresh=True` to bypass
- **Cache Cleanup**: Old cache files (>2 days) are automatically cleaned at 7am daily via GitHub Actions
- **Historical Context**: AI analysis includes last 10 days of results for pattern recognition
- **Team Name Consistency**: Always verify team name mappings when adding new sports or leagues
- **Commit Messages**: GitHub Actions uses format "Add daily [dual] predictions for YYYY-MM-DD"
- **Branch**: Main development happens on `master` branch (note: README mentions `main` as PR target)

## Common Workflows

### Adding a New Sport

1. Create `data/{sport}_games.py` with schedule fetcher
2. Add team name mappings to `data/odds.py`
3. Create `prompts/{sport}_prompt.txt`
4. Create `{sport}_predictions_daily_run.py` (copy from NBA/NHL template)
5. Create `{sport}_results_daily_run.py`
6. Add workflow to `.github/workflows/`

### Debugging Prediction Issues

1. Check team name mapping: Run `test_{sport}_odds.py` and compare team names
2. Verify date filtering: Ensure timezone logic captures correct games
3. Review prompt: Check if `prompts/{sport}_prompt.txt` has correct placeholders
4. Test AI response: Run prediction script manually and inspect output

### Updating AI Prompts

1. Edit files in `prompts/` directory
2. Test locally with manual run: `python scripts/{sport}_predictions_daily_run.py`
3. Verify output format matches expected structure
4. Commit changes - GitHub Actions will use updated prompts next run
