import requests
from datetime import date, timedelta
import pytz
from dateutil import parser

HEADERS = {"User-Agent": "Mozilla/5.0"}

def _get_scoreboard_games(target_date: date) -> list:
    """Fetch games for a specific date from the NBA CDN scoreboard API."""
    local_tz = pytz.timezone("America/New_York")

    if target_date == date.today():
        # Live scoreboard for today
        url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        response = requests.get(url, timeout=10, headers=HEADERS)
        response.raise_for_status()
        games_raw = response.json().get("scoreboard", {}).get("games", [])
    else:
        # Use the static schedule and filter by date
        url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
        response = requests.get(url, timeout=15, headers=HEADERS)
        response.raise_for_status()
        game_dates = response.json().get("leagueSchedule", {}).get("gameDates", [])
        games_raw = []
        target_str = target_date.strftime("%m/%d/%Y")  # NBA schedule uses MM/DD/YYYY
        for gd in game_dates:
            if gd.get("gameDate", "").startswith(target_str):
                games_raw = gd.get("games", [])
                break

        # If nothing found via static schedule, fall back to scoreboard
        # (handles yesterday when it was served as today at run time)
        if not games_raw:
            url2 = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
            r2 = requests.get(url2, timeout=10, headers=HEADERS)
            if r2.ok:
                all_games = r2.json().get("scoreboard", {}).get("games", [])
                for g in all_games:
                    ct = g.get("gameTimeUTC") or g.get("gameDateTimeUTC", "")
                    if ct:
                        dt = parser.isoparse(ct).astimezone(local_tz)
                        if dt.date() == target_date:
                            games_raw.append(g)

    games = []
    local_tz = pytz.timezone("America/New_York")
    for g in games_raw:
        home = g.get("homeTeam", {})
        away = g.get("awayTeam", {})
        home_name = f"{home.get('teamCity', '')} {home.get('teamName', '')}".strip()
        away_name = f"{away.get('teamCity', '')} {away.get('teamName', '')}".strip()
        commence = g.get("gameTimeUTC") or g.get("gameDateTimeUTC", "")
        status = g.get("gameStatus", 1)  # 1=scheduled, 2=live, 3=final
        completed = status == 3
        home_score = home.get("score") if completed else None
        away_score = away.get("score") if completed else None

        games.append({
            "game_id": g.get("gameId"),
            "home": home_name,
            "away": away_name,
            "commence_time": commence,
            "home_score": home_score,
            "away_score": away_score,
            "completed": completed,
        })
    return games


def get_nba_games_today() -> list:
    return _get_scoreboard_games(date.today())


def get_nba_games_yesterday() -> list:
    return _get_scoreboard_games(date.today() - timedelta(days=1))


# Legacy — kept for backwards compatibility
def get_nba_games_by_days_from(days_from: int) -> list:
    target = date.today() - timedelta(days=days_from - 1)
    return _get_scoreboard_games(target)
