import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz
from data.odds_cache import get_cached_odds, save_odds_to_cache

# Load your .env file
load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")

def get_nhl_odds(force_refresh=False):
    """
    Fetch NHL odds using The Odds API with caching.

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        List of odds data from The Odds API
    """
    # Try to get from cache first
    if not force_refresh:
        cached_data = get_cached_odds('nhl')
        if cached_data is not None:
            return cached_data

    # Cache miss or force refresh - fetch from API
    try:
        url = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds"

        eastern = pytz.timezone("America/Toronto")
        now = datetime.now(eastern)

        start_local = eastern.localize(datetime(now.year, now.month, now.day))
        end_local = start_local + timedelta(days=1)

        # Convert to UTC ISO strings with Z suffix
        start_utc = start_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
        end_utc = end_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")

        params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "commenceTimeFrom": start_utc,
            "commenceTimeTo": end_utc,
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        odds_data = response.json()

        # Save to cache
        save_odds_to_cache('nhl', odds_data)

        return odds_data
    except Exception as e:
        print(f"⚠️ Error fetching NHL odds: {e}")
        return []

def get_nba_odds(force_refresh=False):
    """
    Fetch NBA odds using The Odds API with caching.

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        List of odds data from The Odds API
    """
    # Try to get from cache first
    if not force_refresh:
        cached_data = get_cached_odds('nba')
        if cached_data is not None:
            return cached_data

    # Cache miss or force refresh - fetch from API
    try:
        url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"

        eastern = pytz.timezone("America/Toronto")
        now = datetime.now(eastern)

        start_local = eastern.localize(datetime(now.year, now.month, now.day))
        end_local = start_local + timedelta(days=1)

        # Convert to UTC ISO strings with Z suffix
        start_utc = start_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
        end_utc = end_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")

        params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "commenceTimeFrom": start_utc,
            "commenceTimeTo": end_utc,
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        odds_data = response.json()

        # Save to cache
        save_odds_to_cache('nba', odds_data)

        return odds_data
    except Exception as e:
        print(f"⚠️ Error fetching NBA odds: {e}")
        return []

def get_nfl_odds(force_refresh=False):
    """Fetch NFL week odds using The Odds API with caching (7-day window, Thu–Mon)."""
    if not force_refresh:
        cached_data = get_cached_odds('nfl')
        if cached_data is not None:
            return cached_data

    try:
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"

        eastern = pytz.timezone("America/Toronto")
        now = datetime.now(eastern)

        # Span today through 7 days out to capture the full NFL week
        start_local = eastern.localize(datetime(now.year, now.month, now.day))
        end_local = start_local + timedelta(days=7)

        start_utc = start_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
        end_utc = end_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")

        params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "commenceTimeFrom": start_utc,
            "commenceTimeTo": end_utc,
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        odds_data = response.json()

        save_odds_to_cache('nfl', odds_data)
        return odds_data
    except Exception as e:
        print(f"⚠️ Error fetching NFL odds: {e}")
        return []

NFL_TEAM_NAME_MAP = {
    "arizona": ["Arizona Cardinals"],
    "atlanta": ["Atlanta Falcons"],
    "baltimore": ["Baltimore Ravens"],
    "buffalo": ["Buffalo Bills"],
    "carolina": ["Carolina Panthers"],
    "chicago": ["Chicago Bears"],
    "cincinnati": ["Cincinnati Bengals"],
    "cleveland": ["Cleveland Browns"],
    "dallas": ["Dallas Cowboys"],
    "denver": ["Denver Broncos"],
    "detroit": ["Detroit Lions"],
    "greenbay": ["Green Bay Packers"],
    "houston": ["Houston Texans"],
    "indianapolis": ["Indianapolis Colts"],
    "jacksonville": ["Jacksonville Jaguars"],
    "kansascity": ["Kansas City Chiefs"],
    "lasvegas": ["Las Vegas Raiders"],
    "losangeles": ["Los Angeles Rams", "Los Angeles Chargers"],
    "lac": ["Los Angeles Chargers"],
    "lar": ["Los Angeles Rams"],
    "miami": ["Miami Dolphins"],
    "minnesota": ["Minnesota Vikings"],
    "newengland": ["New England Patriots"],
    "neworleans": ["New Orleans Saints"],
    "nygiants": ["New York Giants"],
    "nyjets": ["New York Jets"],
    "philadelphia": ["Philadelphia Eagles"],
    "pittsburgh": ["Pittsburgh Steelers"],
    "sanfrancisco": ["San Francisco 49ers"],
    "seattle": ["Seattle Seahawks"],
    "tampabay": ["Tampa Bay Buccaneers"],
    "tennessee": ["Tennessee Titans"],
    "washington": ["Washington Commanders"],
}

def match_nfl_odds_to_games(games, odds_data):
    """Match NFL games to odds data using NFL_TEAM_NAME_MAP."""
    return match_odds_to_games(games, odds_data, NFL_TEAM_NAME_MAP)


    "anaheim": ["Anaheim Ducks"],
    "arizona": ["Arizona Coyotes"],
    "boston": ["Boston Bruins"],
    "buffalo": ["Buffalo Sabres"],
    "calgary": ["Calgary Flames"],
    "carolina": ["Carolina Hurricanes"],
    "chicago": ["Chicago Blackhawks"],
    "colorado": ["Colorado Avalanche"],
    "columbus": ["Columbus Blue Jackets"],
    "dallas": ["Dallas Stars"],
    "detroit": ["Detroit Red Wings"],
    "edmonton": ["Edmonton Oilers"],
    "florida": ["Florida Panthers"],
    "losangeles": ["Los Angeles Kings"],
    "minnesota": ["Minnesota Wild"],
    "montreal": ["Montreal Canadiens"],
    "nashville": ["Nashville Predators"],
    "newjersey": ["New Jersey Devils"],
    "nyislanders": ["New York Islanders"],
    "nyrangers": ["New York Rangers"],
    "ottawa": ["Ottawa Senators"],
    "philadelphia": ["Philadelphia Flyers"],
    "pittsburgh": ["Pittsburgh Penguins"],
    "sanjose": ["San Jose Sharks"],
    "seattle": ["Seattle Kraken"],
    "stlouis": ["St. Louis Blues"],
    "tampabay": ["Tampa Bay Lightning"],
    "toronto": ["Toronto Maple Leafs"],
    "utah": ["Utah Hockey Club", "Utah Mammoth"],
    "vancouver": ["Vancouver Canucks"],
    "vegas": ["Vegas Golden Knights"],
    "washington": ["Washington Capitals"],
    "winnipeg": ["Winnipeg Jets"]
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
    """
    Matches games (with short team names) to odds_data (with full team names) using the team_name_map.
    Returns a list of dicts with odds and game info for matched games only.
    Logs unmatched games for debugging.
    Handles ambiguous city names like 'New York' by trying all possible teams.
    Now includes spread data for NHL games.
    """
    def normalize(name):
        if not name:
            return ""
        import unicodedata
        # Remove accents by decomposing and filtering out combining characters
        name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
        return name.lower().replace('.', '').replace(' ', '').replace('-', '').replace('club', '').replace('hockey', '')

    def _tally_spread(spread_records):
        # spread_records: list of dicts {point, price}
        if not spread_records:
            return None, None
        # Count points frequency
        from collections import Counter
        points = [r["point"] for r in spread_records if r.get("point") is not None]
        if not points:
            # fallback first
            first = spread_records[0]
            return first.get("point"), first.get("price")
        most_common_point, _ = Counter(points).most_common(1)[0]
        # pick best price among records with that point (highest decimal price)
        candidates = [r for r in spread_records if r.get("point") == most_common_point and r.get("price") is not None]
        if not candidates:
            return most_common_point, None
        best = max(candidates, key=lambda r: r.get("price", 0))
        return most_common_point, best.get("price")

    # Build a reverse map: short_name -> [full_names]
    short_to_full = {}
    for short, fulls in team_name_map.items():
        if isinstance(fulls, str):
            fulls = [fulls]
        short_to_full[short] = [normalize(f) for f in fulls]

    # Add ambiguous city fallback for New York
    ambiguous_city_map = {
        'newyork': ['nyislanders', 'nyrangers'],
        'stlouis': ['stlouis'],
        'losangeles': ['losangeles'],
        # Add more if needed
    }

    matched = []
    unmatched = []
    for game in games:
        home_short = normalize(game["home"])
        away_short = normalize(game["away"])
        # Try ambiguous fallback if not found
        home_fulls = short_to_full.get(home_short, [])
        away_fulls = short_to_full.get(away_short, [])
        if not home_fulls and home_short in ambiguous_city_map:
            # Try all possible teams for ambiguous city
            home_fulls = []
            for ambig in ambiguous_city_map[home_short]:
                home_fulls.extend(short_to_full.get(ambig, []))
        if not away_fulls and away_short in ambiguous_city_map:
            away_fulls = []
            for ambig in ambiguous_city_map[away_short]:
                away_fulls.extend(short_to_full.get(ambig, []))
        found = False
        for odds in odds_data:
            home_team = normalize(odds.get("home_team"))
            away_team = normalize(odds.get("away_team"))
            if (home_team in home_fulls and away_team in away_fulls):
                home_odds = away_odds = over_under = over_price = under_price = None
                spread_home_records = []
                spread_away_records = []

                for bm in odds.get("bookmakers", []):
                    for market in bm.get("markets", []):
                        if market["key"] == "h2h":
                            for outcome in market["outcomes"]:
                                if normalize(outcome["name"]) == home_team:
                                    home_odds = outcome["price"]
                                elif normalize(outcome["name"]) == away_team:
                                    away_odds = outcome["price"]
                        elif market["key"] == "totals":
                            for outcome in market["outcomes"]:
                                if outcome["name"].lower() == "over":
                                    over_under = outcome.get("point")
                                    over_price = outcome.get("price")
                                elif outcome["name"].lower() == "under":
                                    under_price = outcome.get("price")
                        elif market["key"] == "spreads":
                            for outcome in market["outcomes"]:
                                name = outcome.get("name", "")
                                price = outcome.get("price")
                                point = outcome.get("point")
                                if normalize(name) == home_team:
                                    spread_home_records.append({"point": point, "price": price})
                                elif normalize(name) == away_team:
                                    spread_away_records.append({"point": point, "price": price})

                spread_home_points, spread_home_price = _tally_spread(spread_home_records)
                spread_away_points, spread_away_price = _tally_spread(spread_away_records)

                matched.append({
                    **game,
                    "home": odds["home_team"],
                    "away": odds["away_team"],
                    "home_odds": home_odds,
                    "away_odds": away_odds,
                    "over_under": over_under,
                    "over_price": over_price,
                    "under_price": under_price,
                    "spread_home_points": spread_home_points,
                    "spread_home_price": spread_home_price,
                    "spread_away_points": spread_away_points,
                    "spread_away_price": spread_away_price,
                    "bookmakers_odds": odds.get("bookmakers", [])
                })
                found = True
                break
        if not found:
            print(f"[match_odds_to_games] Odds not found for game: {game}, home_full: {home_fulls}, away_full: {away_fulls}")
            unmatched.append(game)
    if unmatched:
        print("[match_odds_to_games] Unmatched games:")
        for g in unmatched:
            print(g)
    return matched

def match_nba_odds_to_games(games, odds_data, team_name_map=NBA_TEAM_NAME_MAP):
    """
    Match The Odds API NBA odds to your games list and summarize moneyline, totals, and spreads.
    - Scans all bookmakers to find moneyline (h2h), totals (point), and spreads (home/away points & prices).
    - For spreads, chooses the most common point per side; if tie or unavailable, picks the first seen.
    - Also returns a per-bookmaker snapshot in `bookmakers_odds` for downstream analysis.
    """
    def _tally_spread(spread_records):
        # spread_records: list of dicts {point, price}
        if not spread_records:
            return None, None
        # Count points frequency
        from collections import Counter
        points = [r["point"] for r in spread_records if r.get("point") is not None]
        if not points:
            # fallback first
            first = spread_records[0]
            return first.get("point"), first.get("price")
        most_common_point, _ = Counter(points).most_common(1)[0]
        # pick best price among records with that point (highest decimal price)
        candidates = [r for r in spread_records if r.get("point") == most_common_point and r.get("price") is not None]
        if not candidates:
            return most_common_point, None
        best = max(candidates, key=lambda r: r.get("price", 0))
        return most_common_point, best.get("price")

    matched_games = []

    for game in games:
        home_city = normalize(game["home"]) if isinstance(game.get("home"), str) else game.get("home")
        away_city = normalize(game["away"]) if isinstance(game.get("away"), str) else game.get("away")
        home = team_name_map.get(home_city, game.get("home"))
        away = team_name_map.get(away_city, game.get("away"))
        start_time = game.get("commence_time") or game.get("start_time")

        home_odds = None
        away_odds = None
        over_under = None
        over_price = None
        under_price = None

        # collect spreads across all bookmakers
        spread_home_records = []  # list of {point, price}
        spread_away_records = []

        bookmakers_odds = []

        for odds_game in odds_data:
            if (normalize(odds_game.get("home_team", "")) == normalize(home) and
                normalize(odds_game.get("away_team", "")) == normalize(away)):

                for bookmaker in odds_game.get("bookmakers", []):
                    bm_snapshot = {"title": bookmaker.get("title"), "markets": []}

                    for market in bookmaker.get("markets", []):
                        mkey = market.get("key")
                        outcomes = market.get("outcomes", []) or []
                        bm_snapshot["markets"].append({"key": mkey, "outcomes": outcomes})

                        if mkey == "h2h":
                            # moneyline summary (first seen)
                            if home_odds is None or away_odds is None:
                                for o in outcomes:
                                    name = o.get("name", "")
                                    price = o.get("price")
                                    if price is None:
                                        continue
                                    if normalize(name) == normalize(home):
                                        home_odds = price
                                    elif normalize(name) == normalize(away):
                                        away_odds = price

                        elif mkey == "totals":
                            if over_under is None and outcomes:
                                for o in outcomes:
                                    if o.get("name", "").lower() == "over":
                                        over_under = o.get("point")
                                        over_price = o.get("price")
                                    elif o.get("name", "").lower() == "under":
                                        under_price = o.get("price")

                        elif mkey == "spreads":
                            for o in outcomes:
                                name = o.get("name", "")
                                price = o.get("price")
                                point = o.get("point")
                                if normalize(name) == normalize(home):
                                    spread_home_records.append({"point": point, "price": price})
                                elif normalize(name) == normalize(away):
                                    spread_away_records.append({"point": point, "price": price})

                    bookmakers_odds.append(bm_snapshot)
                break

        spread_home_points, spread_home_price = _tally_spread(spread_home_records)
        spread_away_points, spread_away_price = _tally_spread(spread_away_records)

        if home_odds is not None and away_odds is not None:
            matched_games.append({
                "game_id": game.get("game_id") or odds_game.get("id"),
                "home": home,
                "away": away,
                "start_time": start_time,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "over_under": over_under,
                "over_price": over_price,
                "under_price": under_price,
                "spread_home_price": spread_home_price,
                "spread_away_points": spread_away_points,
                "spread_away_price": spread_away_price,
                "bookmakers_odds": bookmakers_odds,
            })

    return matched_games
