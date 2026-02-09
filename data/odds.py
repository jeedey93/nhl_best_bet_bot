import requests
import os
import requests
import os
from dotenv import load_dotenv

# Load your .env file
load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")

def get_odds():
    """
    Fetch NHL odds using The Odds API.
    Returns a list of games with bookmakers and markets.
    """
    url = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds"

    params = {
        "apiKey": API_KEY,
        "regions": "us",          # which sportsbook regions to pull
        "markets": "h2h,totals",  # moneyline & totals
        "oddsFormat": "decimal"
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()  # raise error if API fails
    data = response.json()

    return data

# Example mapping (add all teams as needed)
TEAM_NAME_MAP = {
    "buffalo": "Buffalo Sabres",
    "newjersey": "New Jersey Devils",
    "philadelphia": "Philadelphia Flyers",
    "washington": "Washington Capitals",
    "toronto": "Toronto Maple Leafs",
    "tampabay": "Tampa Bay Lightning",
    "seattle": "Seattle Kraken",
    "dallas": "Dallas Stars",
    "colorado": "Colorado Avalanche",
    "utah": "Utah Mammoth",
    "winnipeg": "Winnipeg Jets",
    "vancouver": "Vancouver Canucks",
    "vegas": "Vegas Golden Knights",
    "losangeles": "Los Angeles Kings",
    "edmonton": "Edmonton Oilers",
    "anaheim": "Anaheim Ducks"
}

def normalize(name):
    return name.lower().replace('.', '').replace(' ', '')

def match_odds_to_games(games, odds_data):
    matched_games = []

    for game in games:
        home_city = normalize(game["home"])
        away_city = normalize(game["away"])
        home = TEAM_NAME_MAP.get(home_city, game["home"])
        away = TEAM_NAME_MAP.get(away_city, game["away"])
        start_time = game["start_time"]
        home_odds = None
        away_odds = None
        over_under = None

        for odds_game in odds_data:
            if (normalize(odds_game["home_team"]) == normalize(home) and
                normalize(odds_game["away_team"]) == normalize(away)):
                bookmaker = odds_game["bookmakers"][0]
                for market in bookmaker["markets"]:
                    if market["key"] == "h2h":
                        for outcome in market["outcomes"]:
                            if normalize(outcome["name"]) == normalize(home):
                                home_odds = outcome["price"]
                            elif normalize(outcome["name"]) == normalize(away):
                                away_odds = outcome["price"]
                    elif market["key"] == "totals":
                        over_under = market["outcomes"][0].get("point")
                break

        if home_odds is not None and away_odds is not None:
            matched_games.append({
                "game_id": game["game_id"],
                "home": home,
                "away": away,
                "start_time": start_time,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "over_under": over_under
            })

    return matched_games
