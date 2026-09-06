import requests
from datetime import date, datetime, timedelta
import os
from dotenv import load_dotenv
from dateutil import parser
import pytz

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")

def get_nfl_week_window():
    """Return (start, end) spanning the current + upcoming NFL week (14-day window from most recent Tuesday).

    Using a 14-day window ensures we always capture the next week's games even
    when today falls in the gap between weeks (e.g., a Sunday before Thursday kickoff).
    """
    eastern = pytz.timezone("America/Toronto")
    now = datetime.now(eastern)
    # Find the most recent Tuesday
    days_since_tuesday = (now.weekday() - 1) % 7
    this_tuesday = (now - timedelta(days=days_since_tuesday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = this_tuesday + timedelta(days=14)
    return this_tuesday, week_end

def get_nfl_games_this_week():
    """Return all NFL games in the current NFL week (Tue–Mon) using the odds endpoint."""
    eastern = pytz.timezone("America/Toronto")
    week_start, week_end = get_nfl_week_window()
    start_utc = week_start.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
    end_utc = week_end.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")

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
