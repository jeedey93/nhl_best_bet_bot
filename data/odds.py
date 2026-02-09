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
        "oddsFormat": "american"
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()  # raise error if API fails
    data = response.json()

    return data

def match_odds_to_games(games, odds_data):
    """
    Match the NHL API games with The Odds API data by team names.
    
    Returns a list of dicts with:
    - game_id
    - home, away
    - start_time
    - home_odds, away_odds
    - over_under (point total)
    """
    matched_games = []

    for game in games:
        home = game["home"]
        away = game["away"]
        start_time = game["start_time"]
        home_odds = None
        away_odds = None
        over_under = None

        # Search the odds data for the same matchup
        for odds_game in odds_data:
            if (odds_game["home_team"] == home and odds_game["away_team"] == away):
                # Get first bookmaker
                bookmaker = odds_game["bookmakers"][0]
                for market in bookmaker["markets"]:
                    if market["key"] == "h2h":
                        for outcome in market["outcomes"]:
                            if outcome["name"] == home:
                                home_odds = outcome["price"]
                            elif outcome["name"] == away:
                                away_odds = outcome["price"]
                    elif market["key"] == "totals":
                        over_under = market["outcomes"][0]["point"]  # assumes same point for O/U
                break  # stop once we found the matching game

         # Convert American odds to decimal here
        home_odds = american_to_decimal(home_odds)
        away_odds = american_to_decimal(away_odds)

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

def american_to_decimal(american_odds):
    """
    Convert American odds (-150, +130) to decimal odds (1.x)
    """
    if american_odds is None:
        return None
    if american_odds > 0:
        return round(1 + (american_odds / 100), 2)
    else:
        return round(1 + (100 / abs(american_odds)), 2)