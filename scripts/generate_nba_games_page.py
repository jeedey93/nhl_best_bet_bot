import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.odds import get_nba_odds
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

        # Add retry logic for rate limiting
        max_retries = 3
        retry_delay = 1.5  # seconds

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                break  # Success, exit retry loop
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429 and attempt < max_retries - 1:
                    # Rate limited, wait and retry
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise  # Re-raise if not rate limit or final attempt

        data = response.json()

        # Get completed games (API returns chronologically, so take the last N games)
        all_completed_events = [e for e in data.get('events', [])
                           if e['competitions'][0]['status']['type']['completed']]
        completed_events = all_completed_events[-last_n_games:] if len(all_completed_events) >= last_n_games else all_completed_events

        if not completed_events:
            return None

        scores_for = []
        scores_against = []
        wins = 0
        losses = 0

        # Track streak (need to iterate backwards since most recent is last in the list)
        streak_type = None  # 'W' or 'L'
        streak_count = 0

        for event in completed_events:
            comp = event['competitions'][0]

            # Find home and away teams
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)

            if not home or not away:
                continue

            # Determine team's score by comparing team IDs instead of names
            if home['team']['id'] == team_id:
                team_score = int(home['score']['value'])
                opponent_score = int(away['score']['value'])
                is_win = home.get('winner', False)
            elif away['team']['id'] == team_id:
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

        # Calculate streak by iterating backwards from most recent game
        for event in reversed(completed_events):
            comp = event['competitions'][0]

            # Find home and away teams
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)

            if not home or not away:
                continue

            # Determine if this was a win by comparing team IDs
            if home['team']['id'] == team_id:
                is_win = home.get('winner', False)
            elif away['team']['id'] == team_id:
                is_win = away.get('winner', False)
            else:
                continue

            current_result = 'W' if is_win else 'L'

            if streak_type is None:
                # First game (most recent)
                streak_type = current_result
                streak_count = 1
            elif current_result == streak_type:
                # Continue the streak
                streak_count += 1
            else:
                # Streak broken
                break

        return {
            'avg_scored': round(sum(scores_for) / len(scores_for), 2) if scores_for else 0,
            'avg_allowed': round(sum(scores_against) / len(scores_against), 2) if scores_against else 0,
            'games_analyzed': len(completed_events),
            'wins': wins,
            'losses': losses,
            'ot_losses': 0,  # NBA doesn't have OT losses
            'streak_type': streak_type,  # 'W' or 'L'
            'streak_count': streak_count  # Number of consecutive wins or losses
        }

    except Exception as e:
        print(f"⚠️ Error fetching NBA team stats for {team_name}: {e}")
        return None



def format_time(iso_time):
    """Convert ISO time to Montreal time."""
    dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    montreal_time = dt.astimezone(ZoneInfo('America/Toronto'))
    return montreal_time.strftime("%I:%M %p")


def check_back_to_back(team_name):
    """
    Check if an NBA team is playing back-to-back (played yesterday).

    Returns True if team played yesterday, False otherwise.
    """
    try:
        team_id = NBA_TEAM_ID_MAP.get(team_name)
        if not team_id:
            return False

        # Get today and yesterday dates in Montreal timezone
        montreal_tz = ZoneInfo('America/Toronto')
        today = datetime.now(montreal_tz).date()
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.isoformat()

        # Get team schedule from ESPN
        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule'
        response = requests.get(url, timeout=10)
        data = response.json()

        # Check if they played yesterday
        events = data.get('events', [])
        for event in events:
            event_date = event.get('date', '')
            # Extract date from ISO timestamp
            if event_date:
                game_date = datetime.fromisoformat(event_date.replace('Z', '+00:00')).astimezone(montreal_tz).date()
                if game_date == yesterday:
                    # Check if game is completed
                    status = event.get('status', {}).get('type', {}).get('completed', False)
                    if status:
                        return True

        return False

    except Exception as e:
        print(f"⚠️ Error checking back-to-back for {team_name}: {e}")
        return False


def get_head_to_head_stats(team1_name, team2_name):
    """
    Get head-to-head stats between two NBA teams for the current season.

    Returns dict with:
    - team1_wins: Number of wins for team1
    - team2_wins: Number of wins for team2
    - games_played: Total games between teams
    - last_5_results: List of last 5 game results
    - avg_total_points: Average total points in H2H games
    """
    try:
        # Get team IDs
        team1_id = NBA_TEAM_ID_MAP.get(team1_name)
        team2_id = NBA_TEAM_ID_MAP.get(team2_name)

        if not team1_id or not team2_id:
            return None

        # Get team1's schedule
        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team1_id}/schedule'
        response = requests.get(url, timeout=10)
        data = response.json()

        # Find games between these two teams
        h2h_games = []
        for event in data.get('events', []):
            # Check if game is completed (check inside competitions)
            competition = event.get('competitions', [{}])[0]
            status = competition.get('status', {}).get('type', {}).get('completed', False)
            if not status:
                continue

            # Check if team2 was involved
            competitors = competition.get('competitors', [])

            team_ids = [c.get('team', {}).get('id') for c in competitors]
            if team2_id in team_ids:
                h2h_games.append(event)

        if not h2h_games:
            return None

        # Calculate stats
        team1_wins = 0
        team2_wins = 0
        last_5_results = []
        total_points = []

        # Sort by date (most recent first) - already sorted by API
        for event in h2h_games[:5]:  # Last 5 games
            competition = event.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])

            home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
            away = next((c for c in competitors if c.get('homeAway') == 'away'), {})

            home_id = home.get('team', {}).get('id')
            away_id = away.get('team', {}).get('id')
            home_score = int(float(home.get('score', {}).get('value', 0)))
            away_score = int(float(away.get('score', {}).get('value', 0)))

            # Track total points
            total_points.append(home_score + away_score)

            # Determine winner
            if home_score > away_score:
                winner_id = home_id
            else:
                winner_id = away_id

            # Get team abbreviations for display
            home_abbrev = home.get('team', {}).get('abbreviation', 'HOME')
            away_abbrev = away.get('team', {}).get('abbreviation', 'AWAY')

            # Determine which is team1
            if team1_id == home_id:
                team1_abbrev = home_abbrev
                team2_abbrev = away_abbrev
            else:
                team1_abbrev = away_abbrev
                team2_abbrev = home_abbrev

            # Track wins and format results
            if winner_id == team1_id:
                team1_wins += 1
                result = f"{team1_abbrev} {home_score}-{away_score}" if home_id == team1_id else f"{team1_abbrev} {away_score}-{home_score}"
            else:
                team2_wins += 1
                result = f"{team2_abbrev} {home_score}-{away_score}" if home_id == team2_id else f"{team2_abbrev} {away_score}-{home_score}"

            last_5_results.append({
                'result': result,
                'winner': winner_id,
                'team1_id': team1_id
            })

        # Calculate average total points in H2H
        avg_h2h_total = round(sum(total_points) / len(total_points), 1) if total_points else 0

        return {
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'games_played': len(h2h_games),
            'last_5_results': last_5_results,
            'avg_total_points': avg_h2h_total
        }

    except Exception as e:
        print(f"⚠️ Error fetching H2H stats for {team1_name} vs {team2_name}: {e}")
        return None


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


def generate_game_card(away_team, home_team, game_time, game_odds, away_record=None, home_record=None, sport='nhl', away_logo=None, home_logo=None, game_id=None, away_goalie=None, home_goalie=None, away_rank=None, home_rank=None):
    """Generate HTML for a single game card."""

    # Extract short team names (team name without city)
    # For example: "Los Angeles Lakers" -> "Lakers"
    away_team_short = away_team.split()[-1]  # Last word is usually the team name
    home_team_short = home_team.split()[-1]

    # Handle special cases
    if away_team == "LA Clippers":
        away_team_short = "Clippers"
    elif away_team == "Golden State Warriors":
        away_team_short = "Warriors"
    elif away_team == "Oklahoma City Thunder":
        away_team_short = "Thunder"
    elif away_team == "Portland Trail Blazers":
        away_team_short = "Blazers"

    if home_team == "LA Clippers":
        home_team_short = "Clippers"
    elif home_team == "Golden State Warriors":
        home_team_short = "Warriors"
    elif home_team == "Oklahoma City Thunder":
        home_team_short = "Thunder"
    elif home_team == "Portland Trail Blazers":
        home_team_short = "Blazers"
    # Create anchor ID for navigation
    anchor_id = f"game-{game_id}" if game_id else f"game-{away_team.replace(' ', '-')}-{home_team.replace(' ', '-')}"

    html = f"<div class='game-card' id='{anchor_id}'>\n"
    html += f"<div class='game-time'>{game_time}</div>\n"
    html += f"<div class='matchup'>{away_team} vs {home_team}</div>\n"

    # Get head-to-head stats
    h2h_stats = get_head_to_head_stats(away_team, home_team)
    if h2h_stats:
        html += "<div class='h2h-section'>\n"
        html += "<div class='h2h-title'>🏆 Season Series</div>\n"
        html += "<div class='h2h-record'>\n"
        html += f"<span class='h2h-team'>{away_team}</span>\n"
        html += f"<span class='h2h-score'>{h2h_stats['team1_wins']}-{h2h_stats['team2_wins']}</span>\n"
        html += f"<span class='h2h-team'>{home_team}</span>\n"
        html += "</div>\n"
        if h2h_stats['last_5_results']:
            html += "<div class='h2h-results'>\n"
            for result_data in h2h_stats['last_5_results']:
                result = result_data['result']
                winner = result_data['winner']
                team1_id = result_data['team1_id']
                # Apply green class if team1 won, red if team1 lost
                result_class = 'h2h-win' if winner == team1_id else 'h2h-loss'
                html += f"<span class='h2h-result {result_class}'>{result}</span>\n"
            html += "</div>\n"
        html += "</div>\n"

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
                prediction_html = f"<div class='prediction-indicator away-favored'>↗ Trending: {away_team_short}</div>\n"
            else:
                prediction_html = f"<div class='prediction-indicator home-favored'>↗ Trending: {home_team_short}</div>\n"

        # Check Over/Under signal
        if game_odds and 'totals' in game_odds.get('markets', {}):
            total_line = game_odds['markets']['totals']['point']
            combined_avg = away_stats['avg_scored'] + home_stats['avg_scored']

            # Need at least 0.5 difference to show signal
            if combined_avg > total_line + 0.5:
                over_under_signal = f"<div class='ou-signal over-signal'>📈 Over {total_line}</div>\n"
            elif combined_avg < total_line - 0.5:
                over_under_signal = f"<div class='ou-signal under-signal'>📉 Under {total_line}</div>\n"

    # Generate H2H totals insight badge
    h2h_totals_badge = ""
    if h2h_stats and game_odds and 'totals' in game_odds.get('markets', {}):
        h2h_avg = h2h_stats.get('avg_total_points', 0)
        total_line = game_odds['markets']['totals']['point']

        if h2h_avg > 0:
            # Compare H2H average to betting line
            if h2h_avg > total_line + 2:  # NBA has higher scores, use 2 point threshold
                h2h_totals_badge = f"<div class='h2h-totals-badge high-scoring'>⚡ H2H Avg: {h2h_avg} pts</div>\n"
            elif h2h_avg < total_line - 2:
                h2h_totals_badge = f"<div class='h2h-totals-badge low-scoring'>🛡️ H2H Avg: {h2h_avg} pts</div>\n"

    # Check for back-to-back games
    b2b_badge = ""
    if sport == 'nba':
        away_b2b = check_back_to_back(away_team)
        home_b2b = check_back_to_back(home_team)

        if away_b2b and home_b2b:
            b2b_badge = f"<div class='b2b-badge both-b2b'>⚠️ Both on Back-to-Back</div>\n"
        elif away_b2b:
            b2b_badge = f"<div class='b2b-badge'>⚠️ {away_team_short} on Back-to-Back</div>\n"
        elif home_b2b:
            b2b_badge = f"<div class='b2b-badge'>⚠️ {home_team_short} on Back-to-Back</div>\n"

    # Generate streak badges
    streak_badges = ""
    if away_stats and away_stats.get('streak_count', 0) >= 3:
        streak_type = away_stats.get('streak_type')
        streak_count = away_stats.get('streak_count')
        if streak_type == 'W':
            streak_badges += f"<div class='streak-badge win-streak'>🔥 {away_team_short} {streak_count}W Streak</div>\n"
        elif streak_type == 'L':
            streak_badges += f"<div class='streak-badge lose-streak'>❄️ {away_team_short} {streak_count}L Streak</div>\n"

    if home_stats and home_stats.get('streak_count', 0) >= 3:
        streak_type = home_stats.get('streak_type')
        streak_count = home_stats.get('streak_count')
        if streak_type == 'W':
            streak_badges += f"<div class='streak-badge win-streak'>🔥 {home_team_short} {streak_count}W Streak</div>\n"
        elif streak_type == 'L':
            streak_badges += f"<div class='streak-badge lose-streak'>❄️ {home_team_short} {streak_count}L Streak</div>\n"

    if prediction_html or over_under_signal or h2h_totals_badge or b2b_badge or streak_badges:
        html += "<div class='signals-row'>\n"
        if prediction_html:
            html += prediction_html
        if over_under_signal:
            html += over_under_signal
        if h2h_totals_badge:
            html += h2h_totals_badge
        if b2b_badge:
            html += b2b_badge
        if streak_badges:
            html += streak_badges
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
    # Display team name with rank if available
    away_team_display = away_team
    if away_rank:
        away_team_display = f"{away_team} <span class='team-rank'>({get_ordinal_suffix(away_rank)})</span>"
    html += f"<div class='team-name'>{away_team_display}</div>\n"
    if away_record:
        # Add recent form in parentheses if stats available
        if away_stats:
            if sport == 'nhl':
                recent_form = f"{away_stats['wins']}-{away_stats['losses']}-{away_stats['ot_losses']}"
            else:
                recent_form = f"{away_stats['wins']}-{away_stats['losses']}"

            # Determine color based on record (green if winning, red if losing)
            wins = away_stats['wins']
            losses = away_stats['losses']
            if wins > losses:
                form_class = 'positive-form'
            elif losses > wins:
                form_class = 'negative-form'
            else:
                form_class = 'neutral-form'

            html += f"<div class='team-record'>{away_record} <span class='{form_class}'>({recent_form})</span></div>\n"
        else:
            html += f"<div class='team-record'>{away_record}</div>\n"
    html += "<div class='team-label'>Away Team</div>\n"
    html += "</div>\n"

    # Always show stats tiles for consistency (even if empty)
    score_label = "Goals" if sport == 'nhl' else "Points"
    html += "<div class='stats-tiles'>\n"

    # Avg Scored tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} For</div>\n"
    if away_stats:
        html += f"<div class='stat-value'>{away_stats['avg_scored']:.2f}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Allowed tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Against</div>\n"
    if away_stats:
        html += f"<div class='stat-value'>{away_stats['avg_allowed']:.2f}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Totals tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Total</div>\n"
    if away_stats:
        avg_total = round(away_stats['avg_scored'] + away_stats['avg_allowed'], 2)
        html += f"<div class='stat-value'>{avg_total:.2f}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
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
    # Display team name with rank if available
    home_team_display = home_team
    if home_rank:
        home_team_display = f"{home_team} <span class='team-rank'>({get_ordinal_suffix(home_rank)})</span>"
    html += f"<div class='team-name'>{home_team_display}</div>\n"
    if home_record:
        # Add recent form in parentheses if stats available
        if home_stats:
            if sport == 'nhl':
                recent_form = f"{home_stats['wins']}-{home_stats['losses']}-{home_stats['ot_losses']}"
            else:
                recent_form = f"{home_stats['wins']}-{home_stats['losses']}"

            # Determine color based on record (green if winning, red if losing)
            wins = home_stats['wins']
            losses = home_stats['losses']
            if wins > losses:
                form_class = 'positive-form'
            elif losses > wins:
                form_class = 'negative-form'
            else:
                form_class = 'neutral-form'

            html += f"<div class='team-record'>{home_record} <span class='{form_class}'>({recent_form})</span></div>\n"
        else:
            html += f"<div class='team-record'>{home_record}</div>\n"
    html += "<div class='team-label'>Home Team</div>\n"
    html += "</div>\n"

    # Always show stats tiles for consistency (even if empty)
    score_label = "Goals" if sport == 'nhl' else "Points"
    html += "<div class='stats-tiles'>\n"

    # Avg Scored tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} For</div>\n"
    if home_stats:
        html += f"<div class='stat-value'>{home_stats['avg_scored']:.2f}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Allowed tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Against</div>\n"
    if home_stats:
        html += f"<div class='stat-value'>{home_stats['avg_allowed']:.2f}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Totals tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Total</div>\n"
    if home_stats:
        avg_total = round(home_stats['avg_scored'] + home_stats['avg_allowed'], 2)
        html += f"<div class='stat-value'>{avg_total:.2f}</div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
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
            html += f"<div class='odds-value'><span>{away_team}</span><span>{h2h['away']:.2f}</span></div>\n"
            html += f"<div class='odds-value'><span>{home_team}</span><span>{h2h['home']:.2f}</span></div>\n"
            html += "</div>\n"

        # Totals
        if 'totals' in game_odds['markets']:
            totals = game_odds['markets']['totals']
            html += "<div class='odds-card'>\n"
            html += "<div class='odds-label'>Total</div>\n"
            html += f"<div class='odds-value'><span>Over {totals['point']}</span><span>{totals['over']:.2f}</span></div>\n"
            html += f"<div class='odds-value'><span>Under {totals['point']}</span><span>{totals['under']:.2f}</span></div>\n"
            html += "</div>\n"

        # Spreads
        if 'spreads' in game_odds['markets']:
            spreads = game_odds['markets']['spreads']
            html += "<div class='odds-card'>\n"
            html += "<div class='odds-label'>Spread</div>\n"
            html += f"<div class='odds-value'><span>{away_team} {spreads['away_point']:+.1f}</span><span>{spreads['away']:.2f}</span></div>\n"
            html += f"<div class='odds-value'><span>{home_team} {spreads['home_point']:+.1f}</span><span>{spreads['home']:.2f}</span></div>\n"
            html += "</div>\n"

        html += "</div>\n"  # Close odds-grid
        html += "</div>\n"  # Close odds-content
        html += "</div>\n"  # Close odds-section

    html += "</div>\n"
    return html



def normalize_nba_team_name(team_name):
    """Normalize NBA team names to match between different APIs."""
    # Handle LA Clippers vs Los Angeles Clippers
    if team_name == "Los Angeles Clippers":
        return "LA Clippers"
    return team_name


def get_ordinal_suffix(n):
    """Return ordinal suffix for a number (1st, 2nd, 3rd, etc.)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def get_nba_standings():
    """
    Fetch current NBA standings to get team records and league ranks.
    Returns dict mapping team names to their data (record and league rank).
    """
    try:
        standings_url = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'
        response = requests.get(standings_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Collect all teams with their win percentage for league-wide ranking
        all_teams = []
        for conference in data.get('children', []):
            for entry in conference['standings']['entries']:
                team_name = entry['team']['displayName']

                # Find wins, losses, and win percentage in stats
                wins = None
                losses = None
                win_pct = None
                for stat in entry['stats']:
                    if stat['name'] == 'wins':
                        wins = int(stat['value'])
                    elif stat['name'] == 'losses':
                        losses = int(stat['value'])
                    elif stat['name'] == 'winPercent':
                        win_pct = float(stat['value'])

                if wins is not None and losses is not None:
                    all_teams.append({
                        'name': team_name,
                        'wins': wins,
                        'losses': losses,
                        'win_pct': win_pct if win_pct is not None else 0
                    })

        # Sort teams by win percentage (descending) to get league rank
        all_teams.sort(key=lambda x: x['win_pct'], reverse=True)

        # Build standings dict with rank
        standings = {}
        for rank, team in enumerate(all_teams, start=1):
            record = f"{team['wins']}-{team['losses']}"
            standings[team['name']] = {
                'record': record,
                'rank': rank
            }

        return standings
    except Exception as e:
        print(f"⚠️ Error fetching NBA standings: {e}")
        return {}


def generate_nba_games_page(fetch_odds=True):
    """Generate NBA games page from template.

    Args:
        fetch_odds: If False, skip fetching odds data to avoid API rate limits
    """

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
    last_updated_str = now.strftime("⏱️ Last Updated at %-I:%M %p")

    # Get NBA games from odds API
    # Import moved to top
    nba_games = get_nba_games_today()

    # Get NBA odds (optional)
    nba_odds_data = get_nba_odds() if fetch_odds else []

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

            # Get team records from standings (normalize team names for lookup)
            away_team_normalized = normalize_nba_team_name(away_team)
            home_team_normalized = normalize_nba_team_name(home_team)
            away_standing = nba_standings.get(away_team_normalized, {})
            home_standing = nba_standings.get(home_team_normalized, {})
            away_record = away_standing.get('record') if away_standing else None
            home_record = home_standing.get('record') if home_standing else None
            away_rank = away_standing.get('rank') if away_standing else None
            home_rank = home_standing.get('rank') if home_standing else None

            # Parse odds for this game
            game_odds = parse_odds(nba_odds_data, home_team, away_team)

            nba_html += generate_game_card(away_team, home_team, game_time, game_odds, away_record, home_record, sport='nba', away_logo=away_logo, home_logo=home_logo, game_id=game_id, away_rank=away_rank, home_rank=home_rank)
    else:
        nba_html = "<div class='no-games'>No NBA games scheduled for today</div>\n"

    # Fill template
    output = template.replace("{{NAV_HTML}}", nav_html)
    output = output.replace("{{DATE}}", today_str)
    output = output.replace("{{LAST_UPDATED}}", last_updated_str)
    output = output.replace("{{GAMES_SCROLLER}}", scroller_html)
    output = output.replace("{{NBA_GAMES}}", nba_html)

    # Write to file
    output_file = "docs/nba.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"✅ Generated {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate NBA games page')
    parser.add_argument('--no-odds', action='store_true',
                        help='Skip fetching odds to avoid API rate limits')
    args = parser.parse_args()

    generate_nba_games_page(fetch_odds=not args.no_odds)
