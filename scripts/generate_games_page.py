import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.odds import get_nhl_odds, get_nba_odds
import requests


def format_time(iso_time):
    """Convert ISO time to Montreal time."""
    dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    montreal_time = dt.astimezone(ZoneInfo('America/Toronto'))
    return montreal_time.strftime("%I:%M %p ET")


def parse_odds(odds_data, home_team, away_team):
    """Parse odds from The Odds API response."""
    # Normalize team names for matching
    def normalize(name):
        return name.lower().replace('.', '').replace(' ', '').replace('-', '')

    home_norm = normalize(home_team)
    away_norm = normalize(away_team)

    for odds_game in odds_data:
        odds_home = normalize(odds_game.get('home_team', ''))
        odds_away = normalize(odds_game.get('away_team', ''))

        # Check if this odds entry matches our game
        if home_norm in odds_home or odds_home in home_norm or away_norm in odds_away or odds_away in away_norm:
            markets = {}

            # Extract odds from bookmakers
            for bookmaker in odds_game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    market_key = market['key']

                    if market_key == 'h2h' and 'h2h' not in markets:
                        # Moneyline
                        for outcome in market['outcomes']:
                            if normalize(outcome['name']) in odds_home or odds_home in normalize(outcome['name']):
                                if 'h2h' not in markets:
                                    markets['h2h'] = {}
                                markets['h2h']['home'] = outcome['price']
                            elif normalize(outcome['name']) in odds_away or odds_away in normalize(outcome['name']):
                                if 'h2h' not in markets:
                                    markets['h2h'] = {}
                                markets['h2h']['away'] = outcome['price']

                    elif market_key == 'totals' and 'totals' not in markets:
                        # Totals
                        markets['totals'] = {}
                        for outcome in market['outcomes']:
                            if outcome['name'].lower() == 'over':
                                markets['totals']['over'] = outcome['price']
                                markets['totals']['point'] = outcome['point']
                            elif outcome['name'].lower() == 'under':
                                markets['totals']['under'] = outcome['price']

                    elif market_key == 'spreads' and 'spreads' not in markets:
                        # Spreads
                        markets['spreads'] = {}
                        for outcome in market['outcomes']:
                            if normalize(outcome['name']) in odds_home or odds_home in normalize(outcome['name']):
                                markets['spreads']['home'] = outcome['price']
                                markets['spreads']['home_point'] = outcome['point']
                            elif normalize(outcome['name']) in odds_away or odds_away in normalize(outcome['name']):
                                markets['spreads']['away'] = outcome['price']
                                markets['spreads']['away_point'] = outcome['point']

            if markets:
                return {
                    'home_team': odds_game['home_team'],
                    'away_team': odds_game['away_team'],
                    'markets': markets
                }

    return None


def generate_game_card(away_team, home_team, game_time, game_odds):
    """Generate HTML for a single game card."""
    html = "<div class='game-card'>\n"
    html += f"<div class='game-time'>🕐 {game_time}</div>\n"
    html += f"<div class='matchup'>{away_team} @ {home_team}</div>\n"

    if game_odds:
        html += "<div class='odds-grid'>\n"

        # Moneyline
        if 'h2h' in game_odds['markets']:
            h2h = game_odds['markets']['h2h']
            html += "<div class='odds-card'>\n"
            html += "<div class='odds-label'>Moneyline</div>\n"
            html += f"<div class='odds-value'>{away_team[:15]}: {h2h['away']}</div>\n"
            html += f"<div class='odds-value'>{home_team[:15]}: {h2h['home']}</div>\n"
            html += "</div>\n"

        # Totals
        if 'totals' in game_odds['markets']:
            totals = game_odds['markets']['totals']
            html += "<div class='odds-card'>\n"
            html += "<div class='odds-label'>Total</div>\n"
            html += f"<div class='odds-value'>Over {totals['point']}: {totals['over']}</div>\n"
            html += f"<div class='odds-value'>Under {totals['point']}: {totals['under']}</div>\n"
            html += "</div>\n"

        # Spreads
        if 'spreads' in game_odds['markets']:
            spreads = game_odds['markets']['spreads']
            html += "<div class='odds-card'>\n"
            html += "<div class='odds-label'>Spread</div>\n"
            html += f"<div class='odds-value'>{away_team[:15]} {spreads['away_point']:+.1f}: {spreads['away']}</div>\n"
            html += f"<div class='odds-value'>{home_team[:15]} {spreads['home_point']:+.1f}: {spreads['home']}</div>\n"
            html += "</div>\n"

        html += "</div>\n"

    html += "</div>\n"
    return html


def generate_games_page():
    """Generate today's games page from template."""

    # Read template
    template_path = "docs/games_template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Read navigation HTML
    nav_path = "docs/nav.html"
    with open(nav_path, "r", encoding="utf-8") as f:
        nav_html = f.read()

    # Get today's date
    now = datetime.now(ZoneInfo('America/Toronto'))
    today_str = now.strftime("%A, %B %d, %Y").replace(" 0", " ")

    # Generate NHL games
    nhl_html = ""

    # Get NHL games from the official API
    today = datetime.now(ZoneInfo('America/Toronto')).date().isoformat()
    nhl_api_url = f"https://api-web.nhle.com/v1/schedule/{today}"
    try:
        response = requests.get(nhl_api_url, timeout=10)
        response.raise_for_status()
        nhl_data = response.json()
        nhl_games = nhl_data.get("gameWeek", [])[0].get("games", []) if nhl_data.get("gameWeek") else []
    except:
        nhl_games = []

    nhl_odds_data = get_nhl_odds()

    if nhl_games:
        for game in nhl_games:
            away_team = game['awayTeam']['placeName']['default']
            home_team = game['homeTeam']['placeName']['default']
            game_time = format_time(game['startTimeUTC'])

            # Parse odds for this game
            game_odds = parse_odds(nhl_odds_data, home_team, away_team)

            nhl_html += generate_game_card(away_team, home_team, game_time, game_odds)
    else:
        nhl_html = "<div class='no-games'>No NHL games scheduled for today</div>\n"

    # Generate NBA games
    nba_html = ""

    # Import get_nba_games_today dynamically
    from data.nba_games import get_nba_games_today
    nba_games = get_nba_games_today()
    nba_odds_data = get_nba_odds()

    if nba_games:
        for game in nba_games:
            away_team = game['away']
            home_team = game['home']
            game_time = format_time(game['commence_time'])

            # Parse odds for this game
            game_odds = parse_odds(nba_odds_data, home_team, away_team)

            nba_html += generate_game_card(away_team, home_team, game_time, game_odds)
    else:
        nba_html = "<div class='no-games'>No NBA games scheduled for today</div>\n"

    # Fill template
    output = template.replace("{{NAV_HTML}}", nav_html)
    output = output.replace("{{DATE}}", today_str)
    output = output.replace("{{NHL_GAMES}}", nhl_html)
    output = output.replace("{{NBA_GAMES}}", nba_html)

    # Write to file
    output_file = "docs/games.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"✅ Generated {output_file}")


if __name__ == "__main__":
    generate_games_page()

