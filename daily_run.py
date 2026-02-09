from dotenv import load_dotenv
load_dotenv()

from data.nhl_games import get_games_today
from data.odds import get_odds, match_odds_to_games
from datetime import date

# 1️⃣ Pull today's games
games = get_games_today()

# 2️⃣ Pull today's odds
odds_data = get_odds()

# 3️⃣ Match them
matched_games = match_odds_to_games(games, odds_data)

# 4️⃣ Write results to a text file
today_str = date.today().isoformat()
filename = f"daily_results_{today_str}.txt"

with open(filename, "w") as f:
    f.write(f"Date: {today_str}\n\n")
    for g in matched_games:
        f.write(f"Game: {g['away']} @ {g['home']}\n")
        f.write(f"Home Odds: {g['home_odds']}, Away Odds: {g['away_odds']}, O/U: {g['over_under']}\n")
        f.write("------\n")

print(f"Saved daily results to {filename}")