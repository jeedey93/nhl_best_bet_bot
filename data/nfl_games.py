import requests
from datetime import date, timedelta
import os
from dotenv import load_dotenv
from dateutil import parser
import pytz

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")

def get_nfl_games_by_days_from(days_from):
    url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/scores/?daysFrom={days_from}&apiKey={API_KEY}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    games = []
    for game in data:
        games.append({
            "game_id": game.get("id"),
            "home": game.get("home_team"),
            "away": game.get("away_team"),
            "commence_time": game.get("commence_time"),
            "home_score": game.get("scores", [{}])[0].get("score") if game.get("scores") else None,
            "away_score": game.get("scores", [{}])[1].get("score") if game.get("scores") and len(game.get("scores")) > 1 else None,
            "completed": game.get("completed")
        })
    return games

def get_nfl_games_yesterday():
    # NFL games span Thu-Mon so check last 7 days for completed games
    all_games = get_nfl_games_by_days_from(7)
    local_tz = pytz.timezone("America/Toronto")
    yesterday_local = date.today() - timedelta(days=1)
    return [
        g for g in all_games
        if g["commence_time"] and
        parser.isoparse(g["commence_time"]).astimezone(local_tz).date() == yesterday_local
    ]

def get_nfl_games_this_week():
    """Return all NFL games scheduled within the next 7 days (covers full Thu–Mon week)."""
    all_games = get_nfl_games_by_days_from(7)
    local_tz = pytz.timezone("America/Toronto")
    today = date.today()
    week_end = today + timedelta(days=7)
    return [
        g for g in all_games
        if g["commence_time"] and
        today <= parser.isoparse(g["commence_time"]).astimezone(local_tz).date() <= week_end
    ]
