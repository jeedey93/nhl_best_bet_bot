import requests
from datetime import date, datetime, timedelta
import os
from dotenv import load_dotenv
from dateutil import parser
import pytz

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")

def get_nfl_games_this_week():
    """Return all NFL games scheduled within the next 7 days using the odds endpoint."""
    eastern = pytz.timezone("America/Toronto")
    now = datetime.now(eastern)
    start_local = eastern.localize(datetime(now.year, now.month, now.day))
    end_local = start_local + timedelta(days=7)
    start_utc = start_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
    end_utc = end_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")

    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
        "commenceTimeFrom": start_utc,
        "commenceTimeTo": end_utc,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    games = []
    for game in data:
        games.append({
            "game_id": game.get("id"),
            "home": game.get("home_team"),
            "away": game.get("away_team"),
            "commence_time": game.get("commence_time"),
        })
    return games

def get_nfl_games_yesterday():
    """Return completed NFL games from the last 3 days (scores endpoint, max daysFrom=3)."""
    url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/scores/?daysFrom=3&apiKey={API_KEY}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    local_tz = pytz.timezone("America/Toronto")
    yesterday = date.today() - timedelta(days=1)
    games = []
    for game in data:
        ct = game.get("commence_time")
        if not ct:
            continue
        if parser.isoparse(ct).astimezone(local_tz).date() == yesterday:
            scores = game.get("scores") or []
            games.append({
                "game_id": game.get("id"),
                "home": game.get("home_team"),
                "away": game.get("away_team"),
                "commence_time": ct,
                "home_score": scores[0].get("score") if len(scores) > 0 else None,
                "away_score": scores[1].get("score") if len(scores) > 1 else None,
                "completed": game.get("completed"),
            })
    return games
