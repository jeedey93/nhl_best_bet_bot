import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.odds import get_nhl_odds, get_nba_odds
import requests


def get_team_stats_from_results(team_name, sport='nhl', last_n_games=10):
    """
    Calculate average goals/points for a team from results_with_scores files.

    Args:
        team_name: Name of the team
        sport: 'nhl' or 'nba'
        last_n_games: Number of recent games to analyze

    Returns:
        dict with avg_scored, avg_allowed, games_analyzed
    """
    results_dir = f"data/results_with_scores/{sport}"

    if not os.path.exists(results_dir):
        return None

    # Get all score files sorted by date (newest first)
    files = sorted([f for f in os.listdir(results_dir) if f.endswith('.txt')], reverse=True)

    if not files:
        return None

    # Normalize team name for matching
    def normalize(name):
        return name.lower().replace('.', '').replace(' ', '').replace('-', '')

    team_norm = normalize(team_name)

    scores_for = []
    scores_against = []

    # Parse files until we have enough games
    for file in files:
        if len(scores_for) >= last_n_games:
            break

        file_path = os.path.join(results_dir, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('Date:'):
                        continue

                    # Parse line format: "Team1 Score1 - Team2 Score2"
                    if ' - ' in line:
                        parts = line.split(' - ')
                        if len(parts) == 2:
                            # Parse away team and score
                            away_parts = parts[0].rsplit(' ', 1)
                            if len(away_parts) == 2:
                                away_team, away_score = away_parts[0], away_parts[1]
                            else:
                                continue

                            # Parse home team and score
                            home_parts = parts[1].split(' ', 1)
                            if len(home_parts) == 2:
                                home_team, home_score = home_parts[0], home_parts[1]
                            else:
                                continue

                            # Check if this team played
                            if normalize(away_team) in team_norm or team_norm in normalize(away_team):
                                try:
                                    scores_for.append(int(away_score))
                                    scores_against.append(int(home_score))
                                except ValueError:
                                    pass
                            elif normalize(home_team) in team_norm or team_norm in normalize(home_team):
                                try:
                                    scores_for.append(int(home_score))
                                    scores_against.append(int(away_score))
                                except ValueError:
                                    pass

                            if len(scores_for) >= last_n_games:
                                break
        except Exception as e:
            continue

    if not scores_for:
        return None

    # Make sure we have matching data
    if len(scores_for) != len(scores_against):
        return None

    return {
        'avg_scored': round(sum(scores_for) / len(scores_for), 1),
        'avg_allowed': round(sum(scores_against) / len(scores_against), 1),
        'games_analyzed': len(scores_for)
    }


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


def generate_game_card(away_team, home_team, game_time, game_odds, away_record=None, home_record=None, sport='nhl'):
    """Generate HTML for a single game card."""
    html = "<div class='game-card'>\n"
    html += f"<div class='game-time'>🕐 {game_time}</div>\n"
    html += f"<div class='matchup'>{away_team} @ {home_team}</div>\n"

    # Key Insights Section
    html += "<div class='key-insights'>\n"
    html += "<div class='insights-title'>📊 Key Insights</div>\n"
    html += "<div class='insights-grid'>\n"

    # Away Team Section
    html += "<div class='team-section'>\n"
    html += f"<div class='team-header away-team'>\n"
    html += f"<div class='team-name'>{away_team}</div>\n"
    if away_record:
        html += f"<div class='team-record'>{away_record}</div>\n"
    html += "<div class='team-label'>Away Team</div>\n"
    html += "</div>\n"

    # Get team stats from results
    away_stats = get_team_stats_from_results(away_team, sport=sport, last_n_games=10)
    if away_stats:
        score_label = "Goals" if sport == 'nhl' else "Points"
        html += "<div class='stats-tiles'>\n"

        html += "<div class='stat-tile'>\n"
        html += f"<div class='stat-label'>Avg {score_label} Scored</div>\n"
        html += f"<div class='stat-value'>{away_stats['avg_scored']}</div>\n"
        html += "</div>\n"

        html += "<div class='stat-tile'>\n"
        html += f"<div class='stat-label'>Avg {score_label} Allowed</div>\n"
        html += f"<div class='stat-value'>{away_stats['avg_allowed']}</div>\n"
        html += "</div>\n"

        html += "</div>\n"
        html += f"<div class='stat-games'>Last {away_stats['games_analyzed']} games</div>\n"

    html += "</div>\n"  # Close team-section

    # Home Team Section
    html += "<div class='team-section'>\n"
    html += f"<div class='team-header home-team'>\n"
    html += f"<div class='team-name'>{home_team}</div>\n"
    if home_record:
        html += f"<div class='team-record'>{home_record}</div>\n"
    html += "<div class='team-label'>Home Team</div>\n"
    html += "</div>\n"

    # Get team stats from results
    home_stats = get_team_stats_from_results(home_team, sport=sport, last_n_games=10)
    if home_stats:
        score_label = "Goals" if sport == 'nhl' else "Points"
        html += "<div class='stats-tiles'>\n"

        html += "<div class='stat-tile'>\n"
        html += f"<div class='stat-label'>Avg {score_label} Scored</div>\n"
        html += f"<div class='stat-value'>{home_stats['avg_scored']}</div>\n"
        html += "</div>\n"

        html += "<div class='stat-tile'>\n"
        html += f"<div class='stat-label'>Avg {score_label} Allowed</div>\n"
        html += f"<div class='stat-value'>{home_stats['avg_allowed']}</div>\n"
        html += "</div>\n"

        html += "</div>\n"
        html += f"<div class='stat-games'>Last {home_stats['games_analyzed']} games</div>\n"

    html += "</div>\n"  # Close team-section

    html += "</div>\n"  # Close insights-grid
    html += "</div>\n"  # Close key-insights

    # Odds Section (smaller, less emphasis)
    if game_odds:
        html += "<div class='odds-section'>\n"
        html += "<div class='odds-toggle'>View Odds ▼</div>\n"
        html += "<div class='odds-content'>\n"
        html += "<div class='odds-grid'>\n"

        # Moneyline
        if 'h2h' in game_odds['markets']:
            h2h = game_odds['markets']['h2h']
            html += "<div class='odds-card'>\n"
            html += "<div class='odds-label'>Moneyline</div>\n"
            html += f"<div class='odds-value'><span>{away_team[:15]}</span><span>{h2h['away']}</span></div>\n"
            html += f"<div class='odds-value'><span>{home_team[:15]}</span><span>{h2h['home']}</span></div>\n"
            html += "</div>\n"

        # Totals
        if 'totals' in game_odds['markets']:
            totals = game_odds['markets']['totals']
            html += "<div class='odds-card'>\n"
            html += "<div class='odds-label'>Total</div>\n"
            html += f"<div class='odds-value'><span>Over {totals['point']}</span><span>{totals['over']}</span></div>\n"
            html += f"<div class='odds-value'><span>Under {totals['point']}</span><span>{totals['under']}</span></div>\n"
            html += "</div>\n"

        # Spreads
        if 'spreads' in game_odds['markets']:
            spreads = game_odds['markets']['spreads']
            html += "<div class='odds-card'>\n"
            html += "<div class='odds-label'>Spread</div>\n"
            html += f"<div class='odds-value'><span>{away_team[:15]} {spreads['away_point']:+.1f}</span><span>{spreads['away']}</span></div>\n"
            html += f"<div class='odds-value'><span>{home_team[:15]} {spreads['home_point']:+.1f}</span><span>{spreads['home']}</span></div>\n"
            html += "</div>\n"

        html += "</div>\n"  # Close odds-grid
        html += "</div>\n"  # Close odds-content
        html += "</div>\n"  # Close odds-section

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

            # Extract team records if available
            away_record = None
            home_record = None
            if 'awayTeam' in game and 'record' in game['awayTeam']:
                away_record = game['awayTeam']['record']
            if 'homeTeam' in game and 'record' in game['homeTeam']:
                home_record = game['homeTeam']['record']

            # Parse odds for this game
            game_odds = parse_odds(nhl_odds_data, home_team, away_team)

            nhl_html += generate_game_card(away_team, home_team, game_time, game_odds, away_record, home_record, sport='nhl')
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

            # For NBA, we don't have records readily available, pass None
            nba_html += generate_game_card(away_team, home_team, game_time, game_odds, None, None, sport='nba')
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

