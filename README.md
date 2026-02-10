<p align="center">
  <img src="images/parieur_discipline.png" alt="Project Logo" width="250"/>
</p>

<p align="center">
  <b>Meet le Parieur Discipliné:</b>  
  <i>Le Parieur Discipliné is the disciplined bettor—focused on smart, consistent, and value-driven bets. This project is inspired by Parieur Discipliné’s approach: using data, AI, and strict criteria to identify the best opportunities each day.</i>
</p>


# NHL & NBA Best Bet Bot

A Python tool for analyzing NHL and NBA games, matching odds, and generating disciplined betting analysis using Google Gemini AI. The bot highlights +EV spots, ranks plays by confidence, and explains each pick.

## Features

- Fetches daily NHL and NBA games and odds
- Analyzes results using Google Gemini API
- Skips AI analysis if API quota is exceeded
- Outputs ranked betting recommendations
- Writes daily predictions and results to organized folders

## Requirements

- Python 3.8+
- pip

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/nhl_best_bet_bot.git
   cd nhl_best_bet_bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   - Create a `.env` file in the project root:
     ```
     GOOGLE_API_KEY=your_google_api_key_here
     ODDS_API_KEY=your_odds_api_key_here
     ```

## Usage

Run the daily scripts:

```bash
python nhl_predictions_daily_run.py
python nba_predictions_daily_run.py
python nhl_result_daily_run.py
python nba_results_daily_run.py
```

- The scripts will fetch game data, match odds, and (if quota allows) analyze results using Gemini AI.
- If the Gemini API quota is exceeded, the analysis step is skipped and a message is shown.
- Results and predictions are saved in the `predictions/` and `bot_results/` folders, organized by sport and date.

## Example Output

```
NHL Matchups and Odds:
Buffalo Sabres @ New Jersey Devils
Home odds: 1.97, Away odds: 1.83, O/U: None
------
...

AI Analysis Summary:
1. Vancouver Canucks to Win @ 2.15 — High confidence: Home-ice advantage and value odds.
...
```

Or if quota is exceeded:
```
AI analysis skipped: Gemini API quota exceeded.
```

## Project Structure

- `data/` — Game and odds data modules
- `predictions/` — Daily predictions by sport and date
- `bot_results/` — Daily results by sport and date
- `nhl_predictions_daily_run.py` — NHL prediction script
- `nba_predictions_daily_run.py` — NBA prediction script
- `nhl_result_daily_run.py` — NHL results/summary script
- `nba_results_daily_run.py` — NBA results/summary script
- `requirements.txt` — Python dependencies

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License
