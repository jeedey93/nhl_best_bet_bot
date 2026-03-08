import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.odds import get_nhl_odds, get_nba_odds
from data.starting_goalies import get_starting_goalies
from data.nba_games import get_nba_games_today
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


# ESPN NBA team ID mapping
NBA_TEAM_ID_MAP = {
    'Atlanta Hawks': '1',
    'Boston Celtics': '2',
    'Brooklyn Nets': '17',
    'Charlotte Hornets': '30',
    'Chicago Bulls': '4',
    'Cleveland Cavaliers': '5',
    'Dallas Mavericks': '6',
    'Denver Nuggets': '7',
    'Detroit Pistons': '8',
    'Golden State Warriors': '9',
    'Houston Rockets': '10',
    'Indiana Pacers': '11',
    'LA Clippers': '12',
    'Los Angeles Clippers': '12',
    'Los Angeles Lakers': '13',
    'Memphis Grizzlies': '29',
    'Miami Heat': '14',
    'Milwaukee Bucks': '15',
    'Minnesota Timberwolves': '16',
    'New Orleans Pelicans': '3',
    'New York Knicks': '18',
    'Oklahoma City Thunder': '25',
    'Orlando Magic': '19',
    'Philadelphia 76ers': '20',
    'Phoenix Suns': '21',
    'Portland Trail Blazers': '22',
    'Sacramento Kings': '23',
    'San Antonio Spurs': '24',
    'Toronto Raptors': '28',
    'Utah Jazz': '26',
    'Washington Wizards': '27',
}


def get_team_stats_from_api(team_name, sport='nhl', last_n_games=10):
    """
    Calculate team stats from API for last N games.

    Args:
        team_name: Name of the team
        sport: 'nhl' or 'nba'
        last_n_games: Number of recent games to analyze

    Returns:
        dict with avg_scored, avg_allowed, games_analyzed, wins, losses, ot_losses (NHL only)
    """
    if sport == 'nhl':
        return get_nhl_team_last_games(team_name, last_n_games)
    elif sport == 'nba':
        return get_nba_team_last_games(team_name, last_n_games)
    return None


def get_nba_team_last_games(team_name, last_n_games=10):
    """
    Get last N games for an NBA team from ESPN API.

    Returns:
        dict with avg_scored, avg_allowed, games_analyzed, wins, losses
    """
    try:
        # Get team ID
        team_id = NBA_TEAM_ID_MAP.get(team_name)
        if not team_id:
            return None

        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Get completed games
        completed_events = [e for e in data.get('events', [])
                           if e['competitions'][0]['status']['type']['completed']][:last_n_games]

        if not completed_events:
            return None

        scores_for = []
        scores_against = []
        wins = 0
        losses = 0

        for event in completed_events:
            comp = event['competitions'][0]

            # Find home and away teams
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)

            if not home or not away:
                continue

            # Determine team's score
            if home['team']['displayName'] == team_name:
                team_score = int(home['score']['value'])
                opponent_score = int(away['score']['value'])
                is_win = home.get('winner', False)
            elif away['team']['displayName'] == team_name:
                team_score = int(away['score']['value'])
                opponent_score = int(home['score']['value'])
                is_win = away.get('winner', False)
            else:
                continue

            scores_for.append(team_score)
            scores_against.append(opponent_score)

            if is_win:
                wins += 1
            else:
                losses += 1

        return {
            'avg_scored': round(sum(scores_for) / len(scores_for), 1) if scores_for else 0,
            'avg_allowed': round(sum(scores_against) / len(scores_against), 1) if scores_against else 0,
            'games_analyzed': len(completed_events),
            'wins': wins,
            'losses': losses,
            'ot_losses': 0  # NBA doesn't have OT losses
        }

    except Exception as e:
        print(f"⚠️ Error fetching NBA team stats for {team_name}: {e}")
        return None



def format_time(iso_time):
    """Convert ISO time to Montreal time."""
    dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    montreal_time = dt.astimezone(ZoneInfo('America/Toronto'))
    return montreal_time.strftime("%I:%M %p")


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
    html += f"<div class='game-time'>{game_time}</div>\n"
    html += f"<div class='matchup'>{away_team} vs {home_team}</div>\n"

    # Get team stats for prediction
    away_stats = get_team_stats_from_api(away_team, sport=sport, last_n_games=10)
    home_stats = get_team_stats_from_api(home_team, sport=sport, last_n_games=10)

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

    # Avg Scored tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Scored</div>\n"
    if away_stats:
        html += f"<div class='stat-value'>{away_stats['avg_scored']}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Allowed tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Allowed</div>\n"
    if away_stats:
        html += f"<div class='stat-value'>{away_stats['avg_allowed']}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Record tile
    html += "<div class='stat-tile record-tile'>\n"
    html += "<div class='stat-label'>Recent Form</div>\n"
    if away_stats:
        if sport == 'nhl':
            html += f"<div class='stat-record'>{away_stats['wins']}-{away_stats['losses']}-{away_stats['ot_losses']}</div>\n"
        else:
            html += f"<div class='stat-record'>{away_stats['wins']}-{away_stats['losses']}</div>\n"
    else:
        html += "<div class='stat-record'>-</div>\n"
    html += "</div>\n"

    html += "</div>\n"  # Close stats-tiles

    # Goalie row (NHL only) - separate row
    if sport == 'nhl':
        html += "<div class='goalie-row'>\n"
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
        html += "</div>\n"  # Close goalie-row

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

    # Avg Scored tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Scored</div>\n"
    if home_stats:
        html += f"<div class='stat-value'>{home_stats['avg_scored']}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Allowed tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Allowed</div>\n"
    if home_stats:
        html += f"<div class='stat-value'>{home_stats['avg_allowed']}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Record tile
    html += "<div class='stat-tile record-tile'>\n"
    html += "<div class='stat-label'>Recent Form</div>\n"
    if home_stats:
        if sport == 'nhl':
            html += f"<div class='stat-record'>{home_stats['wins']}-{home_stats['losses']}-{home_stats['ot_losses']}</div>\n"
        else:
            html += f"<div class='stat-record'>{home_stats['wins']}-{home_stats['losses']}</div>\n"
    else:
        html += "<div class='stat-record'>-</div>\n"
    html += "</div>\n"

    html += "</div>\n"  # Close stats-tiles

    # Goalie row (NHL only) - separate row
    if sport == 'nhl':
        html += "<div class='goalie-row'>\n"
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
        html += "</div>\n"  # Close goalie-row

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



def get_nba_standings():
    """
    Fetch current NBA standings to get team records.
    Returns dict mapping team names to their records (W-L format).
    """
    try:
        standings_url = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'
        response = requests.get(standings_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        standings = {}
        for conference in data.get('children', []):
            for entry in conference['standings']['entries']:
                team_name = entry['team']['displayName']

                # Find wins and losses in stats
                wins = None
                losses = None
                for stat in entry['stats']:
                    if stat['name'] == 'wins':
                        wins = int(stat['value'])
                    elif stat['name'] == 'losses':
                        losses = int(stat['value'])

                if wins is not None and losses is not None:
                    record = f"{wins}-{losses}"
                    standings[team_name] = record

        return standings
    except Exception as e:
        print(f"⚠️ Error fetching NBA standings: {e}")
        return {}


def generate_nba_games_page():
    """Generate NBA games page from template."""

    # Read template
    template_path = "docs/nba_games_template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Read navigation HTML
    nav_path = "docs/nav.html"
    with open(nav_path, "r", encoding="utf-8") as f:
        nav_html = f.read()

    # Get today's date
    now = datetime.now(ZoneInfo('America/Toronto'))
    today_str = now.strftime("%A, %B %d, %Y").replace(" 0", " ")

    # Get NBA games from odds API
    # Import moved to top
    nba_games = get_nba_games_today()

    # Get NBA odds
    nba_odds_data = get_nba_odds()

    # Generate scroller HTML for NBA games only
    scroller_html = "<div class='games-scroller'>\n"
    scroller_html += "<div class='scroller-title'>Quick Navigation</div>\n"
    scroller_html += "<div class='scroller-container'>\n"

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

    # Generate NBA games
    nba_html = ""

    if nba_games:
        # Get team standings for season records
        nba_standings = get_nba_standings()

        for game in nba_games:
            away_team = game['away']
            home_team = game['home']
            game_time = format_time(game['commence_time'])
            game_id = game.get('game_id', '')

            # Get NBA logos from mapping
            away_logo = NBA_TEAM_LOGOS.get(away_team)
            home_logo = NBA_TEAM_LOGOS.get(home_team)

            # Get team records from standings
            away_record = nba_standings.get(away_team)
            home_record = nba_standings.get(home_team)

            # Parse odds for this game
            game_odds = parse_odds(nba_odds_data, home_team, away_team)

            nba_html += generate_game_card(away_team, home_team, game_time, game_odds, away_record, home_record, sport='nba', away_logo=away_logo, home_logo=home_logo, game_id=game_id)
    else:
        nba_html = "<div class='no-games'>No NBA games scheduled for today</div>\n"

    # Fill template
    output = template.replace("{{NAV_HTML}}", nav_html)
    output = output.replace("{{DATE}}", today_str)
    output = output.replace("{{GAMES_SCROLLER}}", scroller_html)
    output = output.replace("{{NBA_GAMES}}", nba_html)

    # Write to file
    output_file = "docs/nba_games.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"✅ Generated {output_file}")


if __name__ == "__main__":
    generate_nba_games_page()
