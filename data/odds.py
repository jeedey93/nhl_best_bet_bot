import requests
import os
from dotenv import load_dotenv
from datetime import date

# Load your .env file
load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")

def get_nhl_odds():
    """Fetch NHL odds using The Odds API."""
    url = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds"
    today = date.today().isoformat()
    commence_from = f"{today}T00:00:00Z"
    commence_to = f"{today}T23:59:59Z"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
        #"commenceTimeFrom": commence_from,
        #"commenceTimeTo": commence_to
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def get_nba_odds():
    """Fetch NBA odds using The Odds API."""
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
    today = date.today().isoformat()
    commence_from = f"{today}T00:00:00Z"
    commence_to = f"{today}T23:59:59Z"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
        #"commenceTimeFrom": commence_from,
        #"commenceTimeTo": commence_to
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

NHL_TEAM_NAME_MAP = {
    "anaheim": "Anaheim Ducks",
    "arizona": "Arizona Coyotes",
    "boston": "Boston Bruins",
    "buffalo": "Buffalo Sabres",
    "calgary": "Calgary Flames",
    "carolina": "Carolina Hurricanes",
    "chicago": "Chicago Blackhawks",
    "colorado": "Colorado Avalanche",
    "columbus": "Columbus Blue Jackets",
    "dallas": "Dallas Stars",
    "detroit": "Detroit Red Wings",
    "edmonton": "Edmonton Oilers",
    "florida": "Florida Panthers",
    "losangeles": "Los Angeles Kings",
    "minnesota": "Minnesota Wild",
    "montreal": "Montreal Canadiens",
    "nashville": "Nashville Predators",
    "newjersey": "New Jersey Devils",
    "nyislanders": "New York Islanders",
    "nyrangers": "New York Rangers",
    "ottawa": "Ottawa Senators",
    "philadelphia": "Philadelphia Flyers",
    "pittsburgh": "Pittsburgh Penguins",
    "sanJose": "San Jose Sharks",
    "seattle": "Seattle Kraken",
    "stlouis": "St. Louis Blues",
    "tampabay": "Tampa Bay Lightning",
    "toronto": "Toronto Maple Leafs",
    "utah": "Utah Hockey Club",
    "vancouver": "Vancouver Canucks",
    "vegas": "Vegas Golden Knights",
    "washington": "Washington Capitals",
    "winnipeg": "Winnipeg Jets"
}

NBA_TEAM_NAME_MAP = {
    "atlanta": "Atlanta Hawks",
    "boston": "Boston Celtics",
    "brooklyn": "Brooklyn Nets",
    "charlotte": "Charlotte Hornets",
    "chicago": "Chicago Bulls",
    "cleveland": "Cleveland Cavaliers",
    "dallas": "Dallas Mavericks",
    "denver": "Denver Nuggets",
    "detroit": "Detroit Pistons",
    "goldenstate": "Golden State Warriors",
    "houston": "Houston Rockets",
    "indiana": "Indiana Pacers",
    "lac": "LA Clippers",
    "lal": "Los Angeles Lakers",
    "memphis": "Memphis Grizzlies",
    "miami": "Miami Heat",
    "milwaukee": "Milwaukee Bucks",
    "minnesota": "Minnesota Timberwolves",
    "neworleans": "New Orleans Pelicans",
    "newyork": "New York Knicks",
    "oklahomacity": "Oklahoma City Thunder",
    "orlando": "Orlando Magic",
    "philadelphia": "Philadelphia 76ers",
    "phoenix": "Phoenix Suns",
    "portland": "Portland Trail Blazers",
    "sacramento": "Sacramento Kings",
    "sanantonio": "San Antonio Spurs",
    "toronto": "Toronto Raptors",
    "utah": "Utah Jazz",
    "washington": "Washington Wizards"
}

def normalize(name):
    return name.lower().replace('.', '').replace(' ', '')

def match_odds_to_games(games, odds_data, team_name_map):
    matched_games = []
    for game in games:
        home_city = normalize(game["home"])
        away_city = normalize(game["away"])
        home = team_name_map.get(home_city, game["home"])
        away = team_name_map.get(away_city, game["away"])
        start_time = game["start_time"]
        home_odds = None
        away_odds = None
        over_under = None
        bookmakers_odds = []

        for odds_game in odds_data:
            if (normalize(odds_game["home_team"]) == normalize(home) and
                    normalize(odds_game["away_team"]) == normalize(away)):
                for bookmaker in odds_game["bookmakers"]:
                    bookmaker_entry = {
                        "title": bookmaker["title"],
                        "markets": []
                    }
                    for market in bookmaker["markets"]:
                        market_entry = {
                            "key": market["key"],
                            "outcomes": market["outcomes"]
                        }
                        bookmaker_entry["markets"].append(market_entry)
                        # For summary odds (first bookmaker only, for backward compatibility)
                        if home_odds is None and market["key"] == "h2h":
                            for outcome in market["outcomes"]:
                                if normalize(outcome["name"]) == normalize(home):
                                    home_odds = outcome["price"]
                                elif normalize(outcome["name"]) == normalize(away):
                                    away_odds = outcome["price"]
                        if over_under is None and market["key"] == "totals":
                            over_under = market["outcomes"][0].get("point")
                    bookmakers_odds.append(bookmaker_entry)
                break

        if home_odds is not None and away_odds is not None:
            matched_games.append({
                "game_id": game["game_id"],
                "home": home,
                "away": away,
                "start_time": start_time,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "over_under": over_under,
                "bookmakers_odds": bookmakers_odds
            })

    return matched_games

def match_nba_odds_to_games(games, odds_data, team_name_map=NBA_TEAM_NAME_MAP):
    matched_games = []
    for game in games:
        home_city = normalize(game["home"])
        away_city = normalize(game["away"])
        home = team_name_map.get(home_city, game["home"])
        away = team_name_map.get(away_city, game["away"])
        # NBA game objects use 'commence_time'
        start_time = game.get("commence_time")
        home_odds = None
        away_odds = None
        over_under = None
        bookmakers_odds = []

        for odds_game in odds_data:
            if (normalize(odds_game.get("home_team", "")) == normalize(home) and
                    normalize(odds_game.get("away_team", "")) == normalize(away)):
                for bookmaker in odds_game.get("bookmakers", []):
                    bookmaker_entry = {
                        "title": bookmaker.get("title"),
                        "markets": []
                    }
                    for market in bookmaker.get("markets", []):
                        market_entry = {
                            "key": market.get("key"),
                            "outcomes": market.get("outcomes", [])
                        }
                        bookmaker_entry["markets"].append(market_entry)
                        # Extract summary odds once (first seen h2h and totals)
                        if home_odds is None and market.get("key") == "h2h":
                            for outcome in market.get("outcomes", []):
                                name = outcome.get("name", "")
                                price = outcome.get("price")
                                if price is None:
                                    continue
                                if normalize(name) == normalize(home):
                                    home_odds = price
                                elif normalize(name) == normalize(away):
                                    away_odds = price
                        if over_under is None and market.get("key") == "totals":
                            outcomes = market.get("outcomes", [])
                            if outcomes:
                                over_under = outcomes[0].get("point")
                    bookmakers_odds.append(bookmaker_entry)
                break

        if home_odds is not None and away_odds is not None:
            matched_games.append({
                "game_id": game.get("game_id"),
                "home": home,
                "away": away,
                "start_time": start_time,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "over_under": over_under,
                "bookmakers_odds": bookmakers_odds
            })

    return matched_games
