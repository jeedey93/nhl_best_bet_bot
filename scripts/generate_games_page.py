import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.odds import get_nhl_odds, get_nba_odds
from data.starting_goalies import get_starting_goalies
import requests


# NBA team logos mapping (using ESPN CDN)
NBA_TEAM_LOGOS = {
    'Atlanta Hawks': 'https://cdn.nba.com/logos/nba/1610612737/global/L/logo.svg',
    'Boston Celtics': 'https://cdn.nba.com/logos/nba/1610612738/global/L/logo.svg',
    'Brooklyn Nets': 'https://cdn.nba.com/logos/nba/1610612751/global/L/logo.svg',
    'Charlotte Hornets': 'https://cdn.nba.com/logos/nba/1610612766/global/L/logo.svg',
    'Chicago Bulls': 'https://cdn.nba.com/logos/nba/1610612741/global/L/logo.svg',
    'Cleveland Cavaliers': 'https://cdn.nba.com/logos/nba/1610612739/global/L/logo.svg',
    'Dallas Mavericks': 'https://cdn.nba.com/logos/nba/1610612742/global/L/logo.svg',
    'Denver Nuggets': 'https://cdn.nba.com/logos/nba/1610612743/global/L/logo.svg',
    'Detroit Pistons': 'https://cdn.nba.com/logos/nba/1610612765/global/L/logo.svg',
    'Golden State Warriors': 'https://cdn.nba.com/logos/nba/1610612744/global/L/logo.svg',
    'Houston Rockets': 'https://cdn.nba.com/logos/nba/1610612745/global/L/logo.svg',
    'Indiana Pacers': 'https://cdn.nba.com/logos/nba/1610612754/global/L/logo.svg',
    'LA Clippers': 'https://cdn.nba.com/logos/nba/1610612746/global/L/logo.svg',
    'Los Angeles Clippers': 'https://cdn.nba.com/logos/nba/1610612746/global/L/logo.svg',
    'Los Angeles Lakers': 'https://cdn.nba.com/logos/nba/1610612747/global/L/logo.svg',
    'Memphis Grizzlies': 'https://cdn.nba.com/logos/nba/1610612763/global/L/logo.svg',
    'Miami Heat': 'https://cdn.nba.com/logos/nba/1610612748/global/L/logo.svg',
    'Milwaukee Bucks': 'https://cdn.nba.com/logos/nba/1610612749/global/L/logo.svg',
    'Minnesota Timberwolves': 'https://cdn.nba.com/logos/nba/1610612750/global/L/logo.svg',
    'New Orleans Pelicans': 'https://cdn.nba.com/logos/nba/1610612740/global/L/logo.svg',
    'New York Knicks': 'https://cdn.nba.com/logos/nba/1610612752/global/L/logo.svg',
    'Oklahoma City Thunder': 'https://cdn.nba.com/logos/nba/1610612760/global/L/logo.svg',
    'Orlando Magic': 'https://cdn.nba.com/logos/nba/1610612753/global/L/logo.svg',
    'Philadelphia 76ers': 'https://cdn.nba.com/logos/nba/1610612755/global/L/logo.svg',
    'Phoenix Suns': 'https://cdn.nba.com/logos/nba/1610612756/global/L/logo.svg',
    'Portland Trail Blazers': 'https://cdn.nba.com/logos/nba/1610612757/global/L/logo.svg',
    'Sacramento Kings': 'https://cdn.nba.com/logos/nba/1610612758/global/L/logo.svg',
    'San Antonio Spurs': 'https://cdn.nba.com/logos/nba/1610612759/global/L/logo.svg',
    'Toronto Raptors': 'https://cdn.nba.com/logos/nba/1610612761/global/L/logo.svg',
    'Utah Jazz': 'https://cdn.nba.com/logos/nba/1610612762/global/L/logo.svg',
    'Washington Wizards': 'https://cdn.nba.com/logos/nba/1610612764/global/L/logo.svg',
}


def get_team_stats_from_results(team_name, sport='nhl', last_n_games=10):
    """
    Calculate average goals/points for a team from results_with_scores files.

    Args:
        team_name: Name of the team
        sport: 'nhl' or 'nba'
        last_n_games: Number of recent games to analyze

    Returns:
        dict with avg_scored, avg_allowed, games_analyzed, wins, losses, ot_losses
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
    wins = 0
    losses = 0
    ot_losses = 0

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
                            team_score = None
                            opponent_score = None

                            if normalize(away_team) in team_norm or team_norm in normalize(away_team):
                                try:
                                    team_score = int(away_score)
                                    opponent_score = int(home_score)
                                    scores_for.append(team_score)
                                    scores_against.append(opponent_score)
                                except ValueError:
                                    continue
                            elif normalize(home_team) in team_norm or team_norm in normalize(home_team):
                                try:
                                    team_score = int(home_score)
                                    opponent_score = int(away_score)
                                    scores_for.append(team_score)
                                    scores_against.append(opponent_score)
                                except ValueError:
                                    continue

                            # Determine win/loss/OT loss
                            if team_score is not None and opponent_score is not None:
                                if team_score > opponent_score:
                                    wins += 1
                                elif team_score < opponent_score:
                                    # For NHL, check if it's a one-goal loss (could be OT/SO)
                                    if sport == 'nhl' and abs(team_score - opponent_score) == 1:
                                        ot_losses += 1
                                    else:
                                        losses += 1
                                # Ties shouldn't happen in modern NHL/NBA but handle edge case
                                elif team_score == opponent_score:
                                    ot_losses += 1

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
        'games_analyzed': len(scores_for),
        'wins': wins,
        'losses': losses,
        'ot_losses': ot_losses
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


def generate_game_card(away_team, home_team, game_time, game_odds, away_record=None, home_record=None, sport='nhl', away_logo=None, home_logo=None, game_id=None, away_goalie=None, home_goalie=None):
    """Generate HTML for a single game card."""
    # Create anchor ID for navigation
    anchor_id = f"game-{game_id}" if game_id else f"game-{away_team.replace(' ', '-')}-{home_team.replace(' ', '-')}"

    html = f"<div class='game-card' id='{anchor_id}'>\n"
    html += f"<div class='game-time'>🕐 {game_time}</div>\n"
    html += f"<div class='matchup'>{away_team} @ {home_team}</div>\n"

    # Get team stats for prediction
    away_stats = get_team_stats_from_results(away_team, sport=sport, last_n_games=10)
    home_stats = get_team_stats_from_results(home_team, sport=sport, last_n_games=10)

    # Calculate prediction if both teams have stats
    prediction_html = ""
    over_under_signal = ""

    if away_stats and home_stats:
        # Simple scoring: wins + (avg_scored - avg_allowed)
        away_score = away_stats['wins'] + (away_stats['avg_scored'] - away_stats['avg_allowed'])
        home_score = home_stats['wins'] + (home_stats['avg_scored'] - home_stats['avg_allowed'])

        if abs(away_score - home_score) > 0.5:  # Only show if there's a meaningful difference
            if away_score > home_score:
                prediction_html = f"<div class='prediction-indicator away-favored'>↗ Trending: {away_team}</div>\n"
            else:
                prediction_html = f"<div class='prediction-indicator home-favored'>↗ Trending: {home_team}</div>\n"

        # Check Over/Under signal
        if game_odds and 'totals' in game_odds.get('markets', {}):
            total_line = game_odds['markets']['totals']['point']
            combined_avg = away_stats['avg_scored'] + home_stats['avg_scored']

            # Need at least 0.5 difference to show signal
            if combined_avg > total_line + 0.5:
                over_under_signal = f"<div class='ou-signal over-signal'>📈 Over {total_line}</div>\n"
            elif combined_avg < total_line - 0.5:
                over_under_signal = f"<div class='ou-signal under-signal'>📉 Under {total_line}</div>\n"

    if prediction_html or over_under_signal:
        html += "<div class='signals-row'>\n"
        if prediction_html:
            html += prediction_html
        if over_under_signal:
            html += over_under_signal
        html += "</div>\n"

    # Key Insights Section
    html += "<div class='key-insights'>\n"
    html += "<div class='insights-title'>📊 Key Insights</div>\n"
    html += "<div class='insights-grid'>\n"

    # Away Team Section
    html += "<div class='team-section'>\n"
    html += f"<div class='team-header away-team'>\n"
    if away_logo:
        html += f"<img src='{away_logo}' alt='{away_team}' class='team-logo' />\n"
    html += f"<div class='team-name'>{away_team}</div>\n"
    if away_record:
        html += f"<div class='team-record'>{away_record}</div>\n"
    html += "<div class='team-label'>Away Team</div>\n"
    html += "</div>\n"

    # Always show stats tiles for consistency (even if empty)
    score_label = "Goals" if sport == 'nhl' else "Points"
    html += "<div class='stats-tiles'>\n"

    if away_stats:
        html += "<div class='stat-tile'>\n"
        html += f"<div class='stat-label'>Avg {score_label} Scored</div>\n"
        html += f"<div class='stat-value'>{away_stats['avg_scored']}</div>\n"
        html += "</div>\n"

        html += "<div class='stat-tile'>\n"
        html += f"<div class='stat-label'>Avg {score_label} Allowed</div>\n"
        html += f"<div class='stat-value'>{away_stats['avg_allowed']}</div>\n"
        html += "</div>\n"

        # Record tile
        html += "<div class='stat-tile record-tile'>\n"
        html += "<div class='stat-label'>Last 10 Record</div>\n"
        if sport == 'nhl':
            html += f"<div class='stat-record'>{away_stats['wins']}-{away_stats['losses']}-{away_stats['ot_losses']}</div>\n"
        else:
            html += f"<div class='stat-record'>{away_stats['wins']}-{away_stats['losses']}</div>\n"
        html += "</div>\n"

    # Goalie tile (NHL only) - always show, even if no stats available
    if sport == 'nhl':
        html += "<div class='stat-tile goalie-tile'>\n"
        html += "<div class='stat-label'>Starting Goalie</div>\n"
        if away_goalie:
            html += f"<div class='goalie-name'>{away_goalie['name']}</div>\n"
            status_class = 'confirmed' if 'confirm' in away_goalie['status'].lower() else 'unconfirmed'
            html += f"<div class='goalie-status {status_class}'>{away_goalie['status']}</div>\n"
        else:
            html += "<div class='goalie-name'>TBD</div>\n"
            html += "<div class='goalie-status unconfirmed'>Unconfirmed</div>\n"
        html += "</div>\n"

    html += "</div>\n"
    if away_stats:
        html += f"<div class='stat-games'>Last {away_stats['games_analyzed']} games</div>\n"

    html += "</div>\n"  # Close team-section

    # Home Team Section
    html += "<div class='team-section'>\n"
    html += f"<div class='team-header home-team'>\n"
    if home_logo:
        html += f"<img src='{home_logo}' alt='{home_team}' class='team-logo' />\n"
    html += f"<div class='team-name'>{home_team}</div>\n"
    if home_record:
        html += f"<div class='team-record'>{home_record}</div>\n"
    html += "<div class='team-label'>Home Team</div>\n"
    html += "</div>\n"

    # Always show stats tiles for consistency (even if empty)
    score_label = "Goals" if sport == 'nhl' else "Points"
    html += "<div class='stats-tiles'>\n"

    if home_stats:
        html += "<div class='stat-tile'>\n"
        html += f"<div class='stat-label'>Avg {score_label} Scored</div>\n"
        html += f"<div class='stat-value'>{home_stats['avg_scored']}</div>\n"
        html += "</div>\n"

        html += "<div class='stat-tile'>\n"
        html += f"<div class='stat-label'>Avg {score_label} Allowed</div>\n"
        html += f"<div class='stat-value'>{home_stats['avg_allowed']}</div>\n"
        html += "</div>\n"

        # Record tile
        html += "<div class='stat-tile record-tile'>\n"
        html += "<div class='stat-label'>Last 10 Record</div>\n"
        if sport == 'nhl':
            html += f"<div class='stat-record'>{home_stats['wins']}-{home_stats['losses']}-{home_stats['ot_losses']}</div>\n"
        else:
            html += f"<div class='stat-record'>{home_stats['wins']}-{home_stats['losses']}</div>\n"
        html += "</div>\n"

    # Goalie tile (NHL only) - always show, even if no stats available
    if sport == 'nhl':
        html += "<div class='stat-tile goalie-tile'>\n"
        html += "<div class='stat-label'>Starting Goalie</div>\n"
        if home_goalie:
            html += f"<div class='goalie-name'>{home_goalie['name']}</div>\n"
            status_class = 'confirmed' if 'confirm' in home_goalie['status'].lower() else 'unconfirmed'
            html += f"<div class='goalie-status {status_class}'>{home_goalie['status']}</div>\n"
        else:
            html += "<div class='goalie-name'>TBD</div>\n"
            html += "<div class='goalie-status unconfirmed'>Unconfirmed</div>\n"
        html += "</div>\n"

    html += "</div>\n"
    if home_stats:
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

    # Get NHL games from the official API
    today = now.date().isoformat()
    nhl_api_url = f"https://api-web.nhle.com/v1/schedule/{today}"
    try:
        response = requests.get(nhl_api_url, timeout=10)
        response.raise_for_status()
        nhl_data = response.json()
        nhl_games = nhl_data.get("gameWeek", [])[0].get("games", []) if nhl_data.get("gameWeek") else []
    except:
        nhl_games = []

    nhl_odds_data = get_nhl_odds()

    # Import get_nba_games_today dynamically
    from data.nba_games import get_nba_games_today
    nba_games = get_nba_games_today()
    nba_odds_data = get_nba_odds()

    # Generate game scroller
    scroller_html = "<div class='games-scroller'>\n"
    scroller_html += "<div class='scroller-title'>Today's Games</div>\n"
    scroller_html += "<div class='scroller-container'>\n"

    # Add NHL games to scroller
    for game in nhl_games:
        away_team = game['awayTeam']['placeName']['default']
        home_team = game['homeTeam']['placeName']['default']
        away_logo = game['awayTeam'].get('logo')
        home_logo = game['homeTeam'].get('logo')
        game_time = format_time(game['startTimeUTC'])
        game_id = game.get('id', '')

        # Create anchor link
        anchor_id = f"game-{game_id}" if game_id else f"game-{away_team.replace(' ', '-')}-{home_team.replace(' ', '-')}"

        scroller_html += f"<a href='#{anchor_id}' class='mini-game-tile'>\n"
        scroller_html += "<div class='mini-time'>🏒 " + game_time + "</div>\n"
        scroller_html += "<div class='mini-teams'>\n"
        if away_logo:
            scroller_html += f"<img src='{away_logo}' class='mini-logo' />\n"
        scroller_html += f"<span class='mini-at'>@</span>\n"
        if home_logo:
            scroller_html += f"<img src='{home_logo}' class='mini-logo' />\n"
        scroller_html += "</div>\n"
        scroller_html += f"<div class='mini-matchup'>{away_team[:3].upper()} @ {home_team[:3].upper()}</div>\n"
        scroller_html += "</a>\n"

    # Add NBA games to scroller
    for game in nba_games:
        away_team = game['away']
        home_team = game['home']
        away_logo = NBA_TEAM_LOGOS.get(away_team)
        home_logo = NBA_TEAM_LOGOS.get(home_team)
        game_time = format_time(game['commence_time'])
        game_id = game.get('game_id', '')

        # Create anchor link
        anchor_id = f"game-{game_id}" if game_id else f"game-{away_team.replace(' ', '-')}-{home_team.replace(' ', '-')}"

        scroller_html += f"<a href='#{anchor_id}' class='mini-game-tile'>\n"
        scroller_html += "<div class='mini-time'>🏀 " + game_time + "</div>\n"
        scroller_html += "<div class='mini-teams'>\n"
        if away_logo:
            scroller_html += f"<img src='{away_logo}' class='mini-logo' />\n"
        scroller_html += f"<span class='mini-at'>@</span>\n"
        if home_logo:
            scroller_html += f"<img src='{home_logo}' class='mini-logo' />\n"
        scroller_html += "</div>\n"
        scroller_html += f"<div class='mini-matchup'>{away_team[:15]} @ {home_team[:15]}</div>\n"
        scroller_html += "</a>\n"

    scroller_html += "</div>\n"  # Close scroller-container
    scroller_html += "</div>\n"  # Close games-scroller

    # Generate NHL games
    nhl_html = ""

    if nhl_games:
        # Get starting goalies
        starting_goalies = get_starting_goalies()

        for game in nhl_games:
            away_team = game['awayTeam']['placeName']['default']
            home_team = game['homeTeam']['placeName']['default']
            game_time = format_time(game['startTimeUTC'])
            game_id = game.get('id', '')

            # Extract team logos
            away_logo = game['awayTeam'].get('logo')
            home_logo = game['homeTeam'].get('logo')

            # Extract team records if available
            away_record = None
            home_record = None
            if 'awayTeam' in game and 'record' in game['awayTeam']:
                away_record = game['awayTeam']['record']
            if 'homeTeam' in game and 'record' in game['homeTeam']:
                home_record = game['homeTeam']['record']

            # Get starting goalies
            away_goalie = starting_goalies.get(away_team)
            home_goalie = starting_goalies.get(home_team)

            # Parse odds for this game
            game_odds = parse_odds(nhl_odds_data, home_team, away_team)

            nhl_html += generate_game_card(away_team, home_team, game_time, game_odds, away_record, home_record, sport='nhl', away_logo=away_logo, home_logo=home_logo, game_id=game_id, away_goalie=away_goalie, home_goalie=home_goalie)
    else:
        nhl_html = "<div class='no-games'>No NHL games scheduled for today</div>\n"

    # Generate NBA games
    nba_html = ""

    if nba_games:
        for game in nba_games:
            away_team = game['away']
            home_team = game['home']
            game_time = format_time(game['commence_time'])
            game_id = game.get('game_id', '')

            # Get NBA logos from mapping
            away_logo = NBA_TEAM_LOGOS.get(away_team)
            home_logo = NBA_TEAM_LOGOS.get(home_team)

            # Parse odds for this game
            game_odds = parse_odds(nba_odds_data, home_team, away_team)

            # For NBA, we don't have records readily available, pass None
            nba_html += generate_game_card(away_team, home_team, game_time, game_odds, None, None, sport='nba', away_logo=away_logo, home_logo=home_logo, game_id=game_id)
    else:
        nba_html = "<div class='no-games'>No NBA games scheduled for today</div>\n"

    # Fill template
    output = template.replace("{{NAV_HTML}}", nav_html)
    output = output.replace("{{DATE}}", today_str)
    output = output.replace("{{GAMES_SCROLLER}}", scroller_html)
    output = output.replace("{{NHL_GAMES}}", nhl_html)
    output = output.replace("{{NBA_GAMES}}", nba_html)

    # Write to file
    output_file = "docs/games.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"✅ Generated {output_file}")


if __name__ == "__main__":
    generate_games_page()

