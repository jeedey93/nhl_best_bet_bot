import requests
from datetime import date

def get_games_today():
    date_str = "2026-02-26"
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