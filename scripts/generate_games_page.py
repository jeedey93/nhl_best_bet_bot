import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nhl_games import get_todays_nhl_games
from data.nba_games import get_todays_nba_games
from data.odds import get_odds


def format_time(iso_time):
    """Convert ISO time to Montreal time."""
    dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    montreal_time = dt.astimezone(ZoneInfo('America/Toronto'))
    return montreal_time.strftime("%I:%M %p ET")


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
    nhl_games = get_todays_nhl_games()
    nhl_odds = get_odds("icehockey_nhl")

    if nhl_games:
        for game in nhl_games:
            away_team = game['awayTeam']['name']['default']
            home_team = game['homeTeam']['name']['default']
            game_time = format_time(game['startTimeUTC'])

            # Find odds for this game
            game_odds = None
            for odds_game in nhl_odds:
                if home_team in odds_game['home_team'] or away_team in odds_game['away_team']:
                    game_odds = odds_game
                    break

            nhl_html += generate_game_card(away_team, home_team, game_time, game_odds)
    else:
        nhl_html = "<div class='no-games'>No NHL games scheduled for today</div>\n"

    # Generate NBA games
    nba_html = ""
    nba_games = get_todays_nba_games()
    nba_odds = get_odds("basketball_nba")

    if nba_games:
        for game in nba_games:
            away_team = game['awayTeam']['teamName']
            home_team = game['homeTeam']['teamName']
            game_time = format_time(game['gameTimeUTC'])

            # Find odds for this game
            game_odds = None
            for odds_game in nba_odds:
                if home_team in odds_game['home_team'] or away_team in odds_game['away_team']:
                    game_odds = odds_game
                    break

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

