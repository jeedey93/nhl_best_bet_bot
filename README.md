<p align="center">
  <img src="docs/parieur_discipline_icon_1024.png" alt="Project Logo" width="250"/>
</p>

<p align="center">
  <b>Meet le Parieur Discipliné:</b>  
  <i>Le Parieur Discipliné is the disciplined bettor—focused on smart, consistent, and value-driven bets. This project is inspired by Parieur Discipliné’s approach: using data, AI, and strict criteria to identify the best opportunities each day.</i>
</p>

# Parieur Discipliné Bot

A Python tool for analyzing NHL and NBA games, matching odds, and generating disciplined betting analysis using Google Gemini AI. The bot highlights +EV spots, ranks plays with confidence, and explains each pick.

---

## Table of Contents
- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Daily Automation (GitHub Actions)](#daily-automation-github-actions)
- [Example Output](#example-output)
- [Customization](#customization)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## Features

- **Dual-Run System**: NBA predictions run twice daily (7am & 12pm Montreal time) to capture line movement
- **Line Movement Analysis**: Compares morning vs noon predictions to identify consensus plays and odds changes
- **Multi-Sport Coverage**: Fetches daily NHL and NBA games with comprehensive odds data
- **Multi-Bookmaker Markets**: Supports moneyline (h2h), totals (over/under), and spreads across multiple bookmakers
- **AI-Powered Analysis**: Uses Google Gemini 2.5 for probabilistic edge calculation and play selection
- **Historical Self-Evaluation**: AI reviews past performance to avoid systematic errors and biased patterns
- **Confidence-Based Betting**: High confidence (1.5 units) and Medium confidence (1 unit) with strict edge requirements (+3% minimum)
- **Featured Picks**: Daily "Bet of the Day" extraction with detailed reasoning (3-4 sentences)
- **Injury Integration**: NHL predictions account for real-time injury reports and goalie status
- **Performance Tracking**: Comprehensive results tracking with unit profit/loss calculations
- **Weekly Stats**: Performance metrics organized by week (Monday-Sunday) with season totals
- **GitHub Pages Site**: Auto-updating website with clean, mobile-optimized UI
- **Automated Deployment**: GitHub Actions runs predictions twice daily and publishes results

## Project Structure

```
parieur-discipline-bot/
├── data/                # Odds, games, and market data modules
├── predictions/         # Daily predictions output
├── bot_results/         # Daily results and summaries
├── prompts/             # Prompt templates for AI analysis
├── docs/                # Documentation and GitHub Pages
├── images/              # Project images and logos
├── *.py                 # Main scripts
└── requirements.txt     # Python dependencies
```

## Requirements

- macOS or Linux (Windows works too)
- Python 3.10+ (3.13 supported)
- The Odds API key
- Google Gemini API key

## Quick Start

```bash
# from project root
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` in the repo root:

```bash
GOOGLE_API_KEY=your_google_api_key
ODDS_API_KEY=your_the_odds_api_key
```

These are read by scripts via `python-dotenv`.

## Usage

Run daily predictions (inside venv):

```bash
python nhl_predictions_daily_run.py
python nba_predictions_daily_run.py
```

Run daily results (scores) summary:

```bash
python nhl_results_daily_run.py
python nba_results_daily_run.py
```

## Daily Automation (GitHub Actions)

The bot runs automatically on a daily schedule via GitHub Actions:

### Daily Schedule (Montreal Time)

**6:00 AM** - Results Analysis (`daily_results.yml`)
- Fetches yesterday's game results from NHL/NBA APIs
- Analyzes prediction accuracy
- Calculates wins, losses, and unit profit/loss
- Commits results to repository

**7:00 AM** - Morning Predictions (`daily_predictions.yml`)
- Generates NHL and NBA predictions with early morning odds
- Updates website with yesterday's results + preliminary picks
- Commits predictions to repository

**12:00 PM** - Final Predictions (`daily_predictions.yml`)
- Generates updated NHL and NBA predictions with latest odds
- Compares 7am vs 12pm predictions to identify line movement
- Extracts featured picks (Bet of the Day)
- Updates website with full predictions
- Sends email notification to subscribers
- Commits final predictions to repository

### Workflow Details

- All workflows check out the repo, set up Python 3.13, install dependencies from `requirements.txt`
- API keys are loaded from repository secrets (`GOOGLE_API_KEY`, `ODDS_API_KEY`)
- Changes are automatically committed and pushed to the `master` branch
- Website is published via GitHub Pages at [parieurdiscipline.com](https://parieurdiscipline.com)

## Example Output

```
NBA Matchups and Odds:
New York Knicks vs Indiana Pacers
Home odds: 1.83, Away odds: 2.02, O/U: 223.5
Spreads: Home -2.5 (1.91), Away +2.5 (1.91)
------
...

AI Analysis Summary:
- Plays listed from High Confidence to Leans, with fan-friendly reasoning.
- Bet of the Day: <TEAM or MARKET> vs <OPPONENT> @ <ODDS>
```

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License

## Disclaimer

This project is for informational and entertainment purposes only. There are no guarantees of profit. Please bet responsibly and only wager what you can afford to lose. The authors are not responsible for any financial losses incurred.

---

For documentation, live predictions, and the daily Bets of the Day, visit the [project website](https://parieurdiscipline.com/).
