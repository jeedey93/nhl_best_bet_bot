import requests
from datetime import date, timedelta
import os
from dotenv import load_dotenv
from dateutil import parser
import pytz

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")

def get_nba_games_by_days_from(days_from):
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/scores/?daysFrom={days_from}&apiKey={API_KEY}"
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

def get_nba_games_yesterday():
    all_games = get_nba_games_by_days_from(2)
    local_tz = pytz.timezone("America/New_York")  # Change if needed
    yesterday_local = date.today() - timedelta(days=1)
    games_yesterday = []
    for g in all_games:
        if g["commence_time"]:
            dt_utc = parser.isoparse(g["commence_time"])
            dt_local = dt_utc.astimezone(local_tz)
            if dt_local.date() == yesterday_local:
                games_yesterday.append(g)
    return games_yesterday

def get_nba_games_today():
    all_games = get_nba_games_by_days_from(2)
    today_local = date.today()
    local_tz = pytz.timezone("America/New_York")  # Change to your local timezone if needed
    games_today = []
    for g in all_games:
        if g["commence_time"]:
            dt_utc = parser.isoparse(g["commence_time"])
            dt_local = dt_utc.astimezone(local_tz)
            if dt_local.date() == today_local:
                games_today.append(g)
    return games_today
