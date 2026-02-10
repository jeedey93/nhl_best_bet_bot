import requests
from datetime import date, timedelta

def get_games_today():
    date_str = "2026-02-25"
    today = date.today().isoformat()
    url = f"https://api-web.nhle.com/v1/schedule/{date_str}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    games = []

    for game in data.get("gameWeek", [])[0].get("games", []):
        games.append({
            "game_id": game["id"],
            "away": game["awayTeam"]["placeName"]["default"],
            "home": game["homeTeam"]["placeName"]["default"],
            "start_time": game["startTimeUTC"]
        })

    return games

def get_games_yesterday():
    yesterday = date.today() - timedelta(days=1)
    date_str = yesterday.isoformat()

    date_str = "2026-02-03"
    url = f"https://api-web.nhle.com/v1/schedule/{date_str}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    games = []
    for game in data.get("gameWeek", [])[0].get("games", []):
        games.append({
            "game_id": game["id"],
            "away": game["awayTeam"]["placeName"]["default"],
            "home": game["homeTeam"]["placeName"]["default"],
            "start_time": game["startTimeUTC"],
            "away_score": game["awayTeam"].get("score"),
            "home_score": game["homeTeam"].get("score")
        })

    return games
