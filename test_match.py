from dotenv import load_dotenv
load_dotenv()

from data.nhl_games import get_games_today
from data.odds import get_odds, match_odds_to_games

# Pull your hardcoded date games
games = get_games_today()

# Fetch odds
odds_data = get_odds()

# Match them
matched = match_odds_to_games(games, odds_data)

# Print results
for g in matched:
    print(f"{g['away']} @ {g['home']}")
    print(f"Home odds: {g['home_odds']}, Away odds: {g['away_odds']}, O/U: {g['over_under']}")
    print("------")