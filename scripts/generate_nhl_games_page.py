import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.odds import get_nhl_odds
from data.starting_goalies import get_starting_goalies
from scripts.scrape_nhl_absences import scrape_nhl_absences_by_team
from scripts.scrape_nhl_daily_lines import scrape_nhl_daily_lines, format_lines_for_display
import requests

# NHL team abbreviation mapping
NHL_TEAM_ABBREV_MAP = {
    'Anaheim': 'ANA',
    'Boston': 'BOS',
    'Buffalo': 'BUF',
    'Calgary': 'CGY',
    'Carolina': 'CAR',
    'Chicago': 'CHI',
    'Colorado': 'COL',
    'Columbus': 'CBJ',
    'Dallas': 'DAL',
    'Detroit': 'DET',
    'Edmonton': 'EDM',
    'Florida': 'FLA',
    'Los Angeles': 'LAK',
    'Minnesota': 'MIN',
    'Montréal': 'MTL',
    'Nashville': 'NSH',
    'New Jersey': 'NJD',
    'New York': 'NYI',  # Islanders
    'New York Rangers': 'NYR',  # Rangers
    'Ottawa': 'OTT',
    'Philadelphia': 'PHI',
    'Pittsburgh': 'PIT',
    'San Jose': 'SJS',
    'Seattle': 'SEA',
    'St. Louis': 'STL',
    'Tampa Bay': 'TBL',
    'Toronto': 'TOR',
    'Utah': 'UTA',
    'Vancouver': 'VAN',
    'Vegas': 'VGK',
    'Washington': 'WSH',
    'Winnipeg': 'WPG',
}

# Mapping from NHL.com lineup page team nicknames to standardized names
NHL_TEAM_NICKNAME_MAP = {
    'Ducks': 'Anaheim Ducks',
    'Bruins': 'Boston Bruins',
    'Sabres': 'Buffalo Sabres',
    'Flames': 'Calgary Flames',
    'Hurricanes': 'Carolina Hurricanes',
    'Blackhawks': 'Chicago Blackhawks',
    'Avalanche': 'Colorado Avalanche',
    'Blue Jackets': 'Columbus Blue Jackets',
    'Stars': 'Dallas Stars',
    'Red Wings': 'Detroit Red Wings',
    'Oilers': 'Edmonton Oilers',
    'Panthers': 'Florida Panthers',
    'Kings': 'Los Angeles Kings',
    'Wild': 'Minnesota Wild',
    'Canadiens': 'Montreal Canadiens',
    'Predators': 'Nashville Predators',
    'Devils': 'New Jersey Devils',
    'Islanders': 'New York Islanders',
    'Rangers': 'New York Rangers',
    'Senators': 'Ottawa Senators',
    'Flyers': 'Philadelphia Flyers',
    'Penguins': 'Pittsburgh Penguins',
    'Sharks': 'San Jose Sharks',
    'Kraken': 'Seattle Kraken',
    'Blues': 'St Louis Blues',
    'Lightning': 'Tampa Bay Lightning',
    'Maple Leafs': 'Toronto Maple Leafs',
    'Canucks': 'Vancouver Canucks',
    'Golden Knights': 'Vegas Golden Knights',
    'Capitals': 'Washington Capitals',
    'Jets': 'Winnipeg Jets',
    'Mammoth': 'Utah Mammoth',
}


def get_team_stats_from_api(team_name, sport='nhl', last_n_games=10):
    """
    Calculate team stats from API for last N games.

    Args:
        team_name: Name of the team
        sport: 'nhl' or 'nba'
        last_n_games: Number of recent games to analyze

    Returns:
        dict with avg_scored, avg_allowed, games_analyzed, wins, losses, ot_losses
    """
    if sport == 'nhl':
        return get_nhl_team_last_games(team_name, last_n_games)
    elif sport == 'nba':
        return get_nba_team_last_games(team_name, last_n_games)
    return None


def get_nhl_team_last_games(team_name, last_n_games=10):
    """
    Get last N games for an NHL team from the API.

    Returns:
        dict with avg_scored, avg_allowed, games_analyzed, wins, losses, ot_losses
    """
    try:
        # Check if team_name is already an abbreviation (3 letters) or needs lookup
        if len(team_name) == 3 and team_name.isupper():
            # Already an abbreviation like 'NYR'
            team_abbrev = team_name
        else:
            # Need to look up abbreviation
            team_abbrev = NHL_TEAM_ABBREV_MAP.get(team_name)
            if not team_abbrev:
                return None

        url = f'https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/now'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        time.sleep(0.6)  # Add delay to avoid 429 rate limits

        # Get completed games (API returns chronologically, so take the last N games)
        all_completed_games = [g for g in data.get('games', []) if g.get('gameState') in ['OFF', 'FINAL']]
        completed_games = all_completed_games[-last_n_games:] if len(all_completed_games) >= last_n_games else all_completed_games

        if not completed_games:
            return None

        scores_for = []
        scores_against = []
        wins = 0
        losses = 0
        ot_losses = 0

        # Track first 5 and last 5 for form trend
        first_5_goals = []
        last_5_goals = []

        # Track streak (need to iterate backwards since most recent is last in the list)
        streak_type = None  # 'W' or 'L'
        streak_count = 0

        for idx, game in enumerate(completed_games):
            away_abbrev = game['awayTeam']['abbrev']
            home_abbrev = game['homeTeam']['abbrev']
            away_score = game['awayTeam'].get('score', 0)
            home_score = game['homeTeam'].get('score', 0)

            # Determine team's score and result
            if away_abbrev == team_abbrev:
                team_score = away_score
                opponent_score = home_score
                is_win = away_score > home_score
            else:
                team_score = home_score
                opponent_score = away_score
                is_win = home_score > away_score

            scores_for.append(team_score)
            scores_against.append(opponent_score)

            # Track goals for form trend (first 5 are oldest, last 5 are newest in the 10-game window)
            if idx < 5:
                first_5_goals.append(team_score)
            else:
                last_5_goals.append(team_score)

            # Track wins/losses
            if is_win:
                wins += 1
            else:
                # Check if it was an OT/SO loss
                game_outcome = game.get('gameOutcome', {})
                last_period = game_outcome.get('lastPeriodType', 'REG')
                if last_period in ['OT', 'SO']:
                    ot_losses += 1
                else:
                    losses += 1

        # Calculate streak by iterating backwards from most recent game
        for game in reversed(completed_games):
            away_abbrev = game['awayTeam']['abbrev']
            home_abbrev = game['homeTeam']['abbrev']
            away_score = game['awayTeam'].get('score', 0)
            home_score = game['homeTeam'].get('score', 0)

            # Determine if this was a win
            if away_abbrev == team_abbrev:
                is_win = away_score > home_score
            else:
                is_win = home_score > away_score

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

        # Calculate form trend
        form_trend = None
        if len(completed_games) >= 10:
            avg_first_5 = sum(first_5_goals) / len(first_5_goals) if first_5_goals else 0
            avg_last_5 = sum(last_5_goals) / len(last_5_goals) if last_5_goals else 0
            form_trend = avg_last_5 - avg_first_5  # Positive = improving, negative = declining

        return {
            'avg_scored': round(sum(scores_for) / len(scores_for), 2) if scores_for else 0,
            'avg_allowed': round(sum(scores_against) / len(scores_against), 2) if scores_against else 0,
            'games_analyzed': len(completed_games),
            'wins': wins,
            'losses': losses,
            'ot_losses': ot_losses,
            'form_trend': round(form_trend, 2) if form_trend is not None else None,
            'streak_type': streak_type,  # 'W' or 'L'
            'streak_count': streak_count  # Number of consecutive wins or losses
        }

    except Exception as e:
        print(f"⚠️ Error fetching NHL team stats for {team_name}: {e}")
        return None


def get_nhl_team_season_stats(team_name):
    """
    Get full season stats for an NHL team from the API (all completed games).

    Returns:
        dict with avg_scored, avg_allowed, games_analyzed, wins, losses, ot_losses
    """
    try:
        # Check if team_name is already an abbreviation (3 letters) or needs lookup
        if len(team_name) == 3 and team_name.isupper():
            # Already an abbreviation like 'NYR'
            team_abbrev = team_name
        else:
            # Need to look up abbreviation
            team_abbrev = NHL_TEAM_ABBREV_MAP.get(team_name)
            if not team_abbrev:
                return None

        url = f'https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/now'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        time.sleep(0.6)  # Add delay to avoid 429 rate limits

        # Get all completed games for the season
        completed_games = [g for g in data.get('games', []) if g.get('gameState') in ['OFF', 'FINAL']]

        if not completed_games:
            return None

        scores_for = []
        scores_against = []
        wins = 0
        losses = 0
        ot_losses = 0

        for game in completed_games:
            away_abbrev = game['awayTeam']['abbrev']
            home_abbrev = game['homeTeam']['abbrev']
            away_score = game['awayTeam'].get('score', 0)
            home_score = game['homeTeam'].get('score', 0)

            # Determine team's score and result
            if away_abbrev == team_abbrev:
                team_score = away_score
                opponent_score = home_score
                is_win = away_score > home_score
            else:
                team_score = home_score
                opponent_score = away_score
                is_win = home_score > away_score

            scores_for.append(team_score)
            scores_against.append(opponent_score)

            # Track wins/losses
            if is_win:
                wins += 1
            else:
                # Check if it was an OT/SO loss
                game_outcome = game.get('gameOutcome', {})
                last_period = game_outcome.get('lastPeriodType', 'REG')
                if last_period in ['OT', 'SO']:
                    ot_losses += 1
                else:
                    losses += 1

        return {
            'avg_scored': round(sum(scores_for) / len(scores_for), 2) if scores_for else 0,
            'avg_allowed': round(sum(scores_against) / len(scores_against), 2) if scores_against else 0,
            'games_analyzed': len(completed_games),
            'wins': wins,
            'losses': losses,
            'ot_losses': ot_losses
        }

    except Exception as e:
        print(f"⚠️ Error fetching NHL season stats for {team_name}: {e}")
        return None


def get_head_to_head_stats(team1_name, team2_name, season='20252026'):
    """
    Get head-to-head stats between two teams for the current season.

    Returns dict with:
    - team1_wins: Number of wins for team1
    - team2_wins: Number of wins for team2
    - games_played: Total games between teams
    - last_5_results: List of last 5 game results
    """
    try:
        # Check if team names are already abbreviations or need lookup
        if len(team1_name) == 3 and team1_name.isupper():
            team1_abbrev = team1_name
        else:
            team1_abbrev = NHL_TEAM_ABBREV_MAP.get(team1_name)

        if len(team2_name) == 3 and team2_name.isupper():
            team2_abbrev = team2_name
        else:
            team2_abbrev = NHL_TEAM_ABBREV_MAP.get(team2_name)

        if not team1_abbrev or not team2_abbrev:
            return None

        # Get team1's schedule
        url = f'https://api-web.nhle.com/v1/club-schedule-season/{team1_abbrev}/now'
        response = requests.get(url, timeout=10)
        data = response.json()
        time.sleep(0.6)  # Add delay to avoid 429 rate limits

        # Find games between these two teams
        h2h_games = []
        for game in data.get('games', []):
            # Only look at completed games
            if game.get('gameState') not in ['FINAL', 'OFF']:
                continue

            # Check if this game was against team2
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})

            home_abbrev = home_team.get('abbrev')
            away_abbrev = away_team.get('abbrev')

            # Check if team2 was involved
            if team2_abbrev in [home_abbrev, away_abbrev]:
                h2h_games.append(game)

        if not h2h_games:
            return None

        # Calculate stats
        team1_wins = 0
        team2_wins = 0
        last_5_results = []
        total_goals = []  # Track total goals for H2H average

        # Sort by date (most recent first)
        h2h_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)

        for game in h2h_games[:5]:  # Last 5 games
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})

            home_abbrev = home_team.get('abbrev')
            away_abbrev = away_team.get('abbrev')
            home_score = home_team.get('score', 0)
            away_score = away_team.get('score', 0)

            # Track total goals
            total_goals.append(home_score + away_score)

            # Determine winner
            if home_score > away_score:
                winner_abbrev = home_abbrev
            else:
                winner_abbrev = away_abbrev

            # Track wins and format results with team abbreviations for clarity
            if winner_abbrev == team1_abbrev:
                team1_wins += 1
                # Format: Winner abbrev score - Loser abbrev score
                result = f"{team1_abbrev} {home_score}-{away_score}" if home_abbrev == team1_abbrev else f"{team1_abbrev} {away_score}-{home_score}"
            else:
                team2_wins += 1
                result = f"{team2_abbrev} {home_score}-{away_score}" if home_abbrev == team2_abbrev else f"{team2_abbrev} {away_score}-{home_score}"

            last_5_results.append({
                'result': result,
                'winner': winner_abbrev,
                'team1_abbrev': team1_abbrev
            })

        # Calculate average total goals in H2H
        avg_h2h_total = round(sum(total_goals) / len(total_goals), 1) if total_goals else 0

        return {
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'games_played': len(h2h_games),
            'last_5_results': last_5_results,
            'avg_total_goals': avg_h2h_total
        }

    except Exception as e:
        print(f"⚠️ Error fetching H2H stats for {team1_name} vs {team2_name}: {e}")
        return None


def format_time(iso_time):
    """Convert ISO time to Montreal time."""
    dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    montreal_time = dt.astimezone(ZoneInfo('America/Toronto'))
    return montreal_time.strftime("%I:%M %p")


def get_rest_days(team_name):
    """
    Get the number of rest days since team's last game.

    Returns the number of days since the last completed game, or None if error.
    """
    try:
        # Check if team_name is already an abbreviation or needs lookup
        if len(team_name) == 3 and team_name.isupper():
            team_abbrev = team_name
        else:
            team_abbrev = NHL_TEAM_ABBREV_MAP.get(team_name)
            if not team_abbrev:
                return None

        # Get today's date in Montreal timezone
        montreal_tz = ZoneInfo('America/Toronto')
        today = datetime.now(montreal_tz).date()

        # Get team schedule
        url = f'https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/now'
        response = requests.get(url, timeout=10)
        data = response.json()
        time.sleep(0.6)  # Add delay to avoid 429 rate limits

        # Find the most recent completed game
        completed_games = [
            g for g in data.get('games', [])
            if g.get('gameState') in ['FINAL', 'OFF']
        ]

        if not completed_games:
            return None

        # Get the most recent game date
        last_game = completed_games[-1]
        last_game_date_str = last_game.get('gameDate')
        if not last_game_date_str:
            return None

        # Parse the date and calculate rest days
        from datetime import date
        last_game_date = date.fromisoformat(last_game_date_str)
        # Subtract 1 because if they played yesterday (1 day ago), that's 0 rest days (back-to-back)
        rest_days = (today - last_game_date).days - 1

        return rest_days

    except Exception as e:
        print(f"⚠️ Error getting rest days for {team_name}: {e}")
        return None


def check_back_to_back(team_name):
    """
    Check if a team is playing back-to-back (played yesterday).

    Returns True if team played yesterday, False otherwise.
    """
    try:
        # Check if team_name is already an abbreviation or needs lookup
        if len(team_name) == 3 and team_name.isupper():
            team_abbrev = team_name
        else:
            team_abbrev = NHL_TEAM_ABBREV_MAP.get(team_name)
            if not team_abbrev:
                return False

        # Get today and yesterday dates in Montreal timezone
        montreal_tz = ZoneInfo('America/Toronto')
        today = datetime.now(montreal_tz).date()
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.isoformat()

        # Get team schedule
        url = f'https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/now'
        response = requests.get(url, timeout=10)
        data = response.json()
        time.sleep(0.6)  # Add delay to avoid 429 rate limits

        # Check if they played yesterday
        for game in data.get('games', []):
            game_date = game.get('gameDate')
            if game_date == yesterday_str and game.get('gameState') in ['FINAL', 'OFF']:
                return True

        return False

    except Exception as e:
        print(f"⚠️ Error checking back-to-back for {team_name}: {e}")
        return False


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


def generate_game_card(away_team, home_team, game_time, game_odds, away_record=None, home_record=None, sport='nhl', away_logo=None, home_logo=None, game_id=None, away_goalie=None, home_goalie=None, away_team_short=None, home_team_short=None, away_absences=None, home_absences=None, away_lines=None, home_lines=None, away_special_teams=None, home_special_teams=None, away_rest_days=None, home_rest_days=None, away_rank=None, home_rank=None):
    """Generate HTML for a single game card.

    Args:
        away_team: Full team name for display (e.g., "Minnesota Wild")
        home_team: Full team name for display (e.g., "Vegas Golden Knights")
        away_team_short: Short team name for API calls (e.g., "Minnesota", "Vegas")
        home_team_short: Short team name for API calls (e.g., "Minnesota", "Vegas")
        away_absences: List of injured/scratched players for away team
        home_absences: List of injured/scratched players for home team
        away_lines: Daily projected lines for away team
        home_lines: Daily projected lines for home team
        away_special_teams: Dict with pp_pct and pk_pct for away team
        home_special_teams: Dict with pp_pct and pk_pct for home team
        away_rest_days: Number of rest days since last game for away team
        home_rest_days: Number of rest days since last game for home team
    """
    # Use short names for API calls if provided, otherwise use full names
    away_api_name = away_team_short if away_team_short else away_team
    home_api_name = home_team_short if home_team_short else home_team

    # Create anchor ID for navigation
    anchor_id = f"game-{game_id}" if game_id else f"game-{away_team.replace(' ', '-')}-{home_team.replace(' ', '-')}"

    html = f"<div class='game-card' id='{anchor_id}'>\n"
    html += f"<div class='game-time'>{game_time}</div>\n"
    html += f"<div class='matchup'>{away_team} vs {home_team}</div>\n"

    # Get head-to-head stats (NHL only)
    if sport == 'nhl':
        h2h_stats = get_head_to_head_stats(away_api_name, home_api_name)
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
                    team1_abbrev = result_data['team1_abbrev']
                    # Apply green class if team1 won, red if team1 lost
                    result_class = 'h2h-win' if winner == team1_abbrev else 'h2h-loss'
                    html += f"<span class='h2h-result {result_class}'>{result}</span>\n"
                html += "</div>\n"
            html += "</div>\n"

    # Get team stats for prediction (using short names for API)
    away_stats = get_team_stats_from_api(away_api_name, sport=sport, last_n_games=10)
    home_stats = get_team_stats_from_api(home_api_name, sport=sport, last_n_games=10)

    # Get season stats for display (NHL only)
    away_season_stats = None
    home_season_stats = None
    if sport == 'nhl':
        away_season_stats = get_nhl_team_season_stats(away_api_name)
        home_season_stats = get_nhl_team_season_stats(home_api_name)

    # Calculate prediction if both teams have stats
    prediction_html = ""
    over_under_signal = ""

    if away_stats and home_stats:
        # Simple scoring: wins + (avg_scored - avg_allowed)
        away_score = away_stats['wins'] + (away_stats['avg_scored'] - away_stats['avg_allowed'])
        home_score = home_stats['wins'] + (home_stats['avg_scored'] - home_stats['avg_allowed'])

        if abs(away_score - home_score) > 0.5:  # Only show if there's a meaningful difference
            if away_score > home_score:
                prediction_html = f"<div class='prediction-indicator away-favored'>↗ Trending: {away_team_short or away_team}</div>\n"
            else:
                prediction_html = f"<div class='prediction-indicator home-favored'>↗ Trending: {home_team_short or home_team}</div>\n"

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
    if sport == 'nhl':
        h2h_stats = get_head_to_head_stats(away_api_name, home_api_name)
        if h2h_stats and game_odds and 'totals' in game_odds.get('markets', {}):
            h2h_avg = h2h_stats.get('avg_total_goals', 0)
            total_line = game_odds['markets']['totals']['point']

            if h2h_avg > 0:
                # Compare H2H average to betting line
                if h2h_avg > total_line + 0.5:
                    h2h_totals_badge = f"<div class='h2h-totals-badge high-scoring'>⚡ H2H Avg: {h2h_avg} goals</div>\n"
                elif h2h_avg < total_line - 0.5:
                    h2h_totals_badge = f"<div class='h2h-totals-badge low-scoring'>🛡️ H2H Avg: {h2h_avg} goals</div>\n"

    # Check for back-to-back games
    b2b_badge = ""
    if sport == 'nhl':
        away_b2b = check_back_to_back(away_api_name)
        home_b2b = check_back_to_back(home_api_name)

        if away_b2b and home_b2b:
            b2b_badge = f"<div class='b2b-badge both-b2b'>⚠️ Both on Back-to-Back</div>\n"
        elif away_b2b:
            b2b_badge = f"<div class='b2b-badge'>⚠️ {away_team_short or away_team} on Back-to-Back</div>\n"
        elif home_b2b:
            b2b_badge = f"<div class='b2b-badge'>⚠️ {home_team_short or home_team} on Back-to-Back</div>\n"

    # Generate streak badges
    streak_badges = ""
    if away_stats and away_stats.get('streak_count', 0) >= 3:
        streak_type = away_stats.get('streak_type')
        streak_count = away_stats.get('streak_count')
        if streak_type == 'W':
            streak_badges += f"<div class='streak-badge win-streak'>🔥 {away_team_short or away_team} {streak_count}W Streak</div>\n"
        elif streak_type == 'L':
            streak_badges += f"<div class='streak-badge lose-streak'>❄️ {away_team_short or away_team} {streak_count}L Streak</div>\n"

    if home_stats and home_stats.get('streak_count', 0) >= 3:
        streak_type = home_stats.get('streak_type')
        streak_count = home_stats.get('streak_count')
        if streak_type == 'W':
            streak_badges += f"<div class='streak-badge win-streak'>🔥 {home_team_short or home_team} {streak_count}W Streak</div>\n"
        elif streak_type == 'L':
            streak_badges += f"<div class='streak-badge lose-streak'>❄️ {home_team_short or home_team} {streak_count}L Streak</div>\n"

    # Generate goalie advantage badge (NHL only)
    goalie_advantage_badge = ""
    if sport == 'nhl' and away_goalie and home_goalie:
        # Check if both goalies have necessary stats
        try:
            # Calculate composite goalie score for away goalie
            away_score = 0.0
            away_valid = False

            if 'sv_pct' in away_goalie and 'gaa' in away_goalie and 'record' in away_goalie:
                # Season stats (40% weight)
                season_sv_pct = float(away_goalie['sv_pct'])
                season_gaa = float(away_goalie['gaa'])
                season_record = away_goalie['record']  # e.g., "15-8-3"

                # Parse season record
                record_parts = season_record.split('-')
                if len(record_parts) >= 2:
                    wins = int(record_parts[0])
                    losses = int(record_parts[1])
                    ot_losses = int(record_parts[2]) if len(record_parts) > 2 else 0
                    total_games = wins + losses + ot_losses
                    season_win_rate = wins / total_games if total_games > 0 else 0
                else:
                    season_win_rate = 0

                # Normalize: SV% is direct (higher is better), GAA inverse (lower is better, normalize to 0-1 scale)
                # Assume GAA range 1.5-4.0, normalize: (4.0 - GAA) / 2.5
                season_gaa_normalized = max(0, min(1, (4.0 - season_gaa) / 2.5))

                # Weight: 40% SV%, 40% GAA, 20% Win Rate
                season_score = (season_sv_pct * 0.4) + (season_gaa_normalized * 0.4) + (season_win_rate * 0.2)
                away_score += season_score * 0.4
                away_valid = True

            if 'last_5_sv_pct' in away_goalie and 'last_5_gaa' in away_goalie and 'last_5_record' in away_goalie:
                # Last 5 stats (60% weight - PRIORITY)
                last_5_sv_pct = float(away_goalie['last_5_sv_pct'])
                last_5_gaa = float(away_goalie['last_5_gaa'])
                last_5_record = away_goalie['last_5_record']  # e.g., "3-2-0"

                # Parse record
                record_parts = last_5_record.split('-')
                if len(record_parts) >= 2:
                    wins = int(record_parts[0])
                    losses = int(record_parts[1])
                    ot_losses = int(record_parts[2]) if len(record_parts) > 2 else 0
                    total_games = wins + losses + ot_losses
                    win_rate = wins / total_games if total_games > 0 else 0
                else:
                    win_rate = 0

                # Normalize GAA (same as season)
                last_5_gaa_normalized = max(0, min(1, (4.0 - last_5_gaa) / 2.5))

                # Weight: 40% SV%, 40% GAA, 20% Win Rate
                last_5_score = (last_5_sv_pct * 0.4) + (last_5_gaa_normalized * 0.4) + (win_rate * 0.2)
                away_score += last_5_score * 0.6
                away_valid = True

            # Calculate composite goalie score for home goalie
            home_score = 0.0
            home_valid = False

            if 'sv_pct' in home_goalie and 'gaa' in home_goalie and 'record' in home_goalie:
                # Season stats (40% weight)
                season_sv_pct = float(home_goalie['sv_pct'])
                season_gaa = float(home_goalie['gaa'])
                season_record = home_goalie['record']

                # Parse season record
                record_parts = season_record.split('-')
                if len(record_parts) >= 2:
                    wins = int(record_parts[0])
                    losses = int(record_parts[1])
                    ot_losses = int(record_parts[2]) if len(record_parts) > 2 else 0
                    total_games = wins + losses + ot_losses
                    season_win_rate = wins / total_games if total_games > 0 else 0
                else:
                    season_win_rate = 0

                season_gaa_normalized = max(0, min(1, (4.0 - season_gaa) / 2.5))

                # Weight: 40% SV%, 40% GAA, 20% Win Rate
                season_score = (season_sv_pct * 0.4) + (season_gaa_normalized * 0.4) + (season_win_rate * 0.2)
                home_score += season_score * 0.4
                home_valid = True

            if 'last_5_sv_pct' in home_goalie and 'last_5_gaa' in home_goalie and 'last_5_record' in home_goalie:
                # Last 5 stats (60% weight - PRIORITY)
                last_5_sv_pct = float(home_goalie['last_5_sv_pct'])
                last_5_gaa = float(home_goalie['last_5_gaa'])
                last_5_record = home_goalie['last_5_record']

                # Parse record
                record_parts = last_5_record.split('-')
                if len(record_parts) >= 2:
                    wins = int(record_parts[0])
                    losses = int(record_parts[1])
                    ot_losses = int(record_parts[2]) if len(record_parts) > 2 else 0
                    total_games = wins + losses + ot_losses
                    win_rate = wins / total_games if total_games > 0 else 0
                else:
                    win_rate = 0

                last_5_gaa_normalized = max(0, min(1, (4.0 - last_5_gaa) / 2.5))
                last_5_score = (last_5_sv_pct * 0.4) + (last_5_gaa_normalized * 0.4) + (win_rate * 0.2)
                home_score += last_5_score * 0.6
                home_valid = True

            # Compare scores and determine advantage
            if away_valid and home_valid:
                score_diff = abs(away_score - home_score)

                # Threshold: 0.03 difference in composite score indicates significant advantage
                if score_diff >= 0.03:
                    if away_score > home_score:
                        goalie_advantage_badge = f"<div class='goalie-advantage-badge away-advantage'>🥅 Goalie Edge: {away_team_short or away_team}</div>\n"
                    else:
                        goalie_advantage_badge = f"<div class='goalie-advantage-badge home-advantage'>🥅 Goalie Edge: {home_team_short or home_team}</div>\n"

        except (ValueError, TypeError, IndexError, ZeroDivisionError):
            # If calculation fails, skip the badge
            pass

    if prediction_html or over_under_signal or h2h_totals_badge or b2b_badge or streak_badges or goalie_advantage_badge:
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
        if goalie_advantage_badge:
            html += goalie_advantage_badge
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
    html += "<div class='team-name-container'>\n"
    # Display team name with rank if available
    away_team_display = away_team
    if away_rank:
        away_team_display = f"{away_team} <span class='team-rank'>({get_ordinal_suffix(away_rank)})</span>"
    html += f"<div class='team-name'>{away_team_display}</div>\n"
    # Add Daily Lines button (NHL only)
    if sport == 'nhl':
        if away_lines:
            lines_html = format_lines_for_display(away_lines)
            # Create unique ID for this team's lines
            away_lines_id = f"lines-{game_id}-away" if game_id else f"lines-away-{away_team.replace(' ', '-')}"
            # Store lines data in a data attribute (escape quotes)
            lines_html_escaped = lines_html.replace('"', '&quot;').replace("'", '&#39;').replace('\n', '')
            html += f"<button class='daily-lines-btn' data-lines-id='{away_lines_id}' data-team-name='{away_team}' data-lines-content='{lines_html_escaped}'>📋 Daily Lines</button>\n"
        else:
            # Show disabled button when no lines available
            html += f"<button class='daily-lines-btn' disabled title='Lines not available yet'>📋 Daily Lines</button>\n"
    html += "</div>\n"  # Close team-name-container
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
        if away_season_stats:
            html += f"<div style='font-size: 0.75em; color: #4b5563; margin-top: 6px; font-weight: 600;'><span style='color: #3b82f6;'>Last 10</span> | <span style='color: #10b981;'>Season: {away_season_stats['avg_scored']:.2f}</span></div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Allowed tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Against</div>\n"
    if away_stats:
        html += f"<div class='stat-value'>{away_stats['avg_allowed']:.2f}</div>\n"
        if away_season_stats:
            html += f"<div style='font-size: 0.75em; color: #4b5563; margin-top: 6px; font-weight: 600;'><span style='color: #3b82f6;'>Last 10</span> | <span style='color: #10b981;'>Season: {away_season_stats['avg_allowed']:.2f}</span></div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Totals tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Total</div>\n"
    if away_stats:
        avg_total = round(away_stats['avg_scored'] + away_stats['avg_allowed'], 2)
        html += f"<div class='stat-value'>{avg_total:.2f}</div>\n"
        if away_season_stats:
            season_total = round(away_season_stats['avg_scored'] + away_season_stats['avg_allowed'], 2)
            html += f"<div style='font-size: 0.75em; color: #4b5563; margin-top: 6px; font-weight: 600;'><span style='color: #3b82f6;'>Last 10</span> | <span style='color: #10b981;'>Season: {season_total:.2f}</span></div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    html += "</div>\n"  # Close stats-tiles

    # Special teams tiles (NHL only) - separate row
    if sport == 'nhl':
        html += "<div class='stats-tiles' style='margin-top: 15px;'>\n"

        # Power Play tile
        html += "<div class='stat-tile' style='border-color: #f59e0b; background: linear-gradient(135deg, #fef3c7 0%, #ffffff 100%);'>\n"
        html += "<div class='stat-label'>Power Play %</div>\n"
        if away_special_teams and 'pp_pct' in away_special_teams:
            html += f"<div class='stat-value'>{away_special_teams['pp_pct']:.1f}%</div>\n"
        else:
            html += "<div class='stat-value'>-</div>\n"
        html += "</div>\n"

        # Penalty Kill tile
        html += "<div class='stat-tile' style='border-color: #3b82f6; background: linear-gradient(135deg, #dbeafe 0%, #ffffff 100%);'>\n"
        html += "<div class='stat-label'>Penalty Kill %</div>\n"
        if away_special_teams and 'pk_pct' in away_special_teams:
            html += f"<div class='stat-value'>{away_special_teams['pk_pct']:.1f}%</div>\n"
        else:
            html += "<div class='stat-value'>-</div>\n"
        html += "</div>\n"

        # Rest Days tile
        html += "<div class='stat-tile' style='border-color: #10b981; background: linear-gradient(135deg, #d1fae5 0%, #ffffff 100%);'>\n"
        html += "<div class='stat-label'>Rest Days</div>\n"
        if away_rest_days is not None:
            # Color-code based on rest days
            if away_rest_days == 0:
                rest_color = '#ef4444'  # Red for back-to-back
                rest_display = 'B2B'
            elif away_rest_days == 1:
                rest_color = '#f59e0b'  # Orange for 1 day
                rest_display = '1'
            elif away_rest_days >= 3:
                rest_color = '#10b981'  # Green for well-rested
                rest_display = f'{away_rest_days}'
            else:
                rest_color = '#6b7280'  # Gray for normal
                rest_display = f'{away_rest_days}'
            html += f"<div class='stat-value' style='color: {rest_color} !important; background: none !important; -webkit-text-fill-color: {rest_color} !important;'>{rest_display}</div>\n"
        else:
            html += "<div class='stat-value'>-</div>\n"
        html += "</div>\n"

        html += "</div>\n"  # Close special-teams-tiles

    # Goalie row (NHL only) - separate row
    if sport == 'nhl':
        html += "<div class='goalie-row'>\n"
        html += "<div class='stat-tile goalie-tile'>\n"
        html += "<div class='stat-label'>Starting Goalie</div>\n"
        if away_goalie:
            status_class = 'confirmed' if 'confirm' in away_goalie['status'].lower() else 'unconfirmed'

            # Display goalie stats if available
            if 'record' in away_goalie:
                html += f"<div class='goalie-header'>\n"
                html += f"<div class='goalie-name'>{away_goalie['name']}</div>\n"
                html += f"<div class='goalie-status {status_class}'>{away_goalie['status']}</div>\n"
                html += "</div>\n"
                html += "<div class='goalie-stats-compact'>\n"
                html += "<div class='season-stats'>\n"
                html += f"<div class='stat-item'><span class='stat-label'>Record</span><span class='stat-value'>{away_goalie['record']}</span></div>\n"
                html += f"<div class='stat-item'><span class='stat-label'>GAA</span><span class='stat-value'>{away_goalie['gaa']:.2f}</span></div>\n"
                html += f"<div class='stat-item'><span class='stat-label'>SV%</span><span class='stat-value'>{away_goalie['sv_pct']:.3f}</span></div>\n"
                html += "</div>\n"
                html += "<div class='last5-divider'>Last 5 Starts</div>\n"
                html += "<div class='last5-stats'>\n"
                html += f"<div class='stat-compact'>{away_goalie['last_5_record']}</div>\n"
                html += f"<div class='stat-compact'>{away_goalie['last_5_gaa']:.2f} GAA</div>\n"
                html += f"<div class='stat-compact'>{away_goalie['last_5_sv_pct']:.3f} SV%</div>\n"
                html += "</div>\n"
                html += "</div>\n"
            else:
                html += f"<div class='goalie-header'>\n"
                html += f"<div class='goalie-name'>{away_goalie['name']}</div>\n"
                html += f"<div class='goalie-status {status_class}'>{away_goalie['status']}</div>\n"
                html += "</div>\n"
        else:
            html += "<div class='goalie-header'>\n"
            html += "<div class='goalie-name'>TBD</div>\n"
            html += "<div class='goalie-status unconfirmed'>Unconfirmed</div>\n"
            html += "</div>\n"
        html += "</div>\n"
        html += "</div>\n"  # Close goalie-row

    # Absences section (NHL only)
    if sport == 'nhl' and away_absences:
        html += "<div class='absences-section'>\n"
        html += "<div class='absences-title'>⚕️ Out</div>\n"
        for player in away_absences[:5]:  # Show max 5 players
            html += f"<div class='absence-item'>{player}</div>\n"
        html += "</div>\n"

    if away_stats:
        html += f"<div class='stat-games'>Last {away_stats['games_analyzed']} games</div>\n"

    html += "</div>\n"  # Close team-section

    # Home Team Section
    html += "<div class='team-section'>\n"
    html += f"<div class='team-header home-team'>\n"
    if home_logo:
        html += f"<img src='{home_logo}' alt='{home_team}' class='team-logo' />\n"
    html += "<div class='team-name-container'>\n"
    # Display team name with rank if available
    home_team_display = home_team
    if home_rank:
        home_team_display = f"{home_team} <span class='team-rank'>({get_ordinal_suffix(home_rank)})</span>"
    html += f"<div class='team-name'>{home_team_display}</div>\n"
    # Add Daily Lines button (NHL only)
    if sport == 'nhl':
        if home_lines:
            lines_html = format_lines_for_display(home_lines)
            # Create unique ID for this team's lines
            home_lines_id = f"lines-{game_id}-home" if game_id else f"lines-home-{home_team.replace(' ', '-')}"
            # Store lines data in a data attribute (escape quotes)
            lines_html_escaped = lines_html.replace('"', '&quot;').replace("'", '&#39;').replace('\n', '')
            html += f"<button class='daily-lines-btn' data-lines-id='{home_lines_id}' data-team-name='{home_team}' data-lines-content='{lines_html_escaped}'>📋 Daily Lines</button>\n"
        else:
            # Show disabled button when no lines available
            html += f"<button class='daily-lines-btn' disabled title='Lines not available yet'>📋 Daily Lines</button>\n"
    html += "</div>\n"  # Close team-name-container
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
        if home_season_stats:
            html += f"<div style='font-size: 0.75em; color: #4b5563; margin-top: 6px; font-weight: 600;'><span style='color: #3b82f6;'>Last 10</span> | <span style='color: #10b981;'>Season: {home_season_stats['avg_scored']:.2f}</span></div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Allowed tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Against</div>\n"
    if home_stats:
        html += f"<div class='stat-value'>{home_stats['avg_allowed']:.2f}</div>\n"
        if home_season_stats:
            html += f"<div style='font-size: 0.75em; color: #4b5563; margin-top: 6px; font-weight: 600;'><span style='color: #3b82f6;'>Last 10</span> | <span style='color: #10b981;'>Season: {home_season_stats['avg_allowed']:.2f}</span></div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    # Avg Totals tile
    html += "<div class='stat-tile'>\n"
    html += f"<div class='stat-label'>Avg {score_label} Total</div>\n"
    if home_stats:
        avg_total = round(home_stats['avg_scored'] + home_stats['avg_allowed'], 2)
        html += f"<div class='stat-value'>{avg_total:.2f}</div>\n"
        if home_season_stats:
            season_total = round(home_season_stats['avg_scored'] + home_season_stats['avg_allowed'], 2)
            html += f"<div style='font-size: 0.75em; color: #4b5563; margin-top: 6px; font-weight: 600;'><span style='color: #3b82f6;'>Last 10</span> | <span style='color: #10b981;'>Season: {season_total:.2f}</span></div>\n"
    else:
        html += "<div class='stat-value'>-</div>\n"
    html += "</div>\n"

    html += "</div>\n"  # Close stats-tiles

    # Special teams tiles (NHL only) - separate row
    if sport == 'nhl':
        html += "<div class='stats-tiles' style='margin-top: 15px;'>\n"

        # Power Play tile
        html += "<div class='stat-tile' style='border-color: #f59e0b; background: linear-gradient(135deg, #fef3c7 0%, #ffffff 100%);'>\n"
        html += "<div class='stat-label'>Power Play %</div>\n"
        if home_special_teams and 'pp_pct' in home_special_teams:
            html += f"<div class='stat-value'>{home_special_teams['pp_pct']:.1f}%</div>\n"
        else:
            html += "<div class='stat-value'>-</div>\n"
        html += "</div>\n"

        # Penalty Kill tile
        html += "<div class='stat-tile' style='border-color: #3b82f6; background: linear-gradient(135deg, #dbeafe 0%, #ffffff 100%);'>\n"
        html += "<div class='stat-label'>Penalty Kill %</div>\n"
        if home_special_teams and 'pk_pct' in home_special_teams:
            html += f"<div class='stat-value'>{home_special_teams['pk_pct']:.1f}%</div>\n"
        else:
            html += "<div class='stat-value'>-</div>\n"
        html += "</div>\n"

        # Rest Days tile
        html += "<div class='stat-tile' style='border-color: #10b981; background: linear-gradient(135deg, #d1fae5 0%, #ffffff 100%);'>\n"
        html += "<div class='stat-label'>Rest Days</div>\n"
        if home_rest_days is not None:
            # Color-code based on rest days
            if home_rest_days == 0:
                rest_color = '#ef4444'  # Red for back-to-back
                rest_display = 'B2B'
            elif home_rest_days == 1:
                rest_color = '#f59e0b'  # Orange for 1 day
                rest_display = '1'
            elif home_rest_days >= 3:
                rest_color = '#10b981'  # Green for well-rested
                rest_display = f'{home_rest_days}'
            else:
                rest_color = '#6b7280'  # Gray for normal
                rest_display = f'{home_rest_days}'
            html += f"<div class='stat-value' style='color: {rest_color} !important; background: none !important; -webkit-text-fill-color: {rest_color} !important;'>{rest_display}</div>\n"
        else:
            html += "<div class='stat-value'>-</div>\n"
        html += "</div>\n"

        html += "</div>\n"  # Close special-teams-tiles

    # Goalie row (NHL only) - separate row
    if sport == 'nhl':
        html += "<div class='goalie-row'>\n"
        html += "<div class='stat-tile goalie-tile'>\n"
        html += "<div class='stat-label'>Starting Goalie</div>\n"
        if home_goalie:
            status_class = 'confirmed' if 'confirm' in home_goalie['status'].lower() else 'unconfirmed'

            # Display goalie stats if available
            if 'record' in home_goalie:
                html += f"<div class='goalie-header'>\n"
                html += f"<div class='goalie-name'>{home_goalie['name']}</div>\n"
                html += f"<div class='goalie-status {status_class}'>{home_goalie['status']}</div>\n"
                html += "</div>\n"
                html += "<div class='goalie-stats-compact'>\n"
                html += "<div class='season-stats'>\n"
                html += f"<div class='stat-item'><span class='stat-label'>Record</span><span class='stat-value'>{home_goalie['record']}</span></div>\n"
                html += f"<div class='stat-item'><span class='stat-label'>GAA</span><span class='stat-value'>{home_goalie['gaa']:.2f}</span></div>\n"
                html += f"<div class='stat-item'><span class='stat-label'>SV%</span><span class='stat-value'>{home_goalie['sv_pct']:.3f}</span></div>\n"
                html += "</div>\n"
                html += "<div class='last5-divider'>Last 5 Starts</div>\n"
                html += "<div class='last5-stats'>\n"
                html += f"<div class='stat-compact'>{home_goalie['last_5_record']}</div>\n"
                html += f"<div class='stat-compact'>{home_goalie['last_5_gaa']:.2f} GAA</div>\n"
                html += f"<div class='stat-compact'>{home_goalie['last_5_sv_pct']:.3f} SV%</div>\n"
                html += "</div>\n"
                html += "</div>\n"
            else:
                html += f"<div class='goalie-header'>\n"
                html += f"<div class='goalie-name'>{home_goalie['name']}</div>\n"
                html += f"<div class='goalie-status {status_class}'>{home_goalie['status']}</div>\n"
                html += "</div>\n"
        else:
            html += "<div class='goalie-header'>\n"
            html += "<div class='goalie-name'>TBD</div>\n"
            html += "<div class='goalie-status unconfirmed'>Unconfirmed</div>\n"
            html += "</div>\n"
        html += "</div>\n"
        html += "</div>\n"  # Close goalie-row

    # Absences section (NHL only)
    if sport == 'nhl' and home_absences:
        html += "<div class='absences-section'>\n"
        html += "<div class='absences-title'>⚕️ Out</div>\n"
        for player in home_absences[:5]:  # Show max 5 players
            html += f"<div class='absence-item'>{player}</div>\n"
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



def get_nhl_special_teams_stats():
    """
    Fetch NHL special teams stats (Power Play % and Penalty Kill %).
    Returns dict mapping team abbreviations to their PP% and PK%.
    """
    try:
        stats_url = 'https://api.nhle.com/stats/rest/en/team/summary?cayenneExp=seasonId=20252026'
        response = requests.get(stats_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        time.sleep(0.6)  # Add delay to avoid 429 rate limits

        # Build mapping from team ID to team abbreviation first
        standings_url = 'https://api-web.nhle.com/v1/standings/now'
        standings_response = requests.get(standings_url, timeout=10)
        standings_response.raise_for_status()
        standings_data = standings_response.json()
        time.sleep(0.6)

        # Create team_id to abbrev map
        team_id_to_abbrev = {}
        for team in standings_data.get('standings', []):
            # The teamId is not in standings, we'll need to map by name
            team_name = team['teamName']['default']
            team_abbrev = team['teamAbbrev']['default']
            team_id_to_abbrev[team_name] = team_abbrev

        special_teams = {}
        for team_stat in data.get('data', []):
            team_name = team_stat.get('teamFullName')
            pp_pct = team_stat.get('powerPlayPct', 0) * 100  # Convert to percentage
            pk_pct = team_stat.get('penaltyKillPct', 0) * 100  # Convert to percentage

            # Find team abbreviation
            team_abbrev = team_id_to_abbrev.get(team_name)
            if team_abbrev:
                special_teams[team_abbrev] = {
                    'pp_pct': round(pp_pct, 1),
                    'pk_pct': round(pk_pct, 1)
                }

        return special_teams
    except Exception as e:
        print(f"⚠️ Error fetching NHL special teams stats: {e}")
        return {}


def get_ordinal_suffix(n):
    """Return ordinal suffix for a number (1st, 2nd, 3rd, etc.)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def get_nhl_standings():
    """
    Fetch current NHL standings to get team records and league ranks.
    Returns dict mapping team abbreviations to their data (record and league rank).
    """
    try:
        standings_url = 'https://api-web.nhle.com/v1/standings/now'
        response = requests.get(standings_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        time.sleep(0.6)  # Add delay to avoid 429 rate limits

        standings = {}
        for team in data.get('standings', []):
            team_abbrev = team['teamAbbrev']['default']
            wins = team['wins']
            losses = team['losses']
            ot_losses = team['otLosses']
            record = f"{wins}-{losses}-{ot_losses}"
            league_rank = team.get('leagueSequence', 0)  # League-wide rank
            standings[team_abbrev] = {
                'record': record,
                'rank': league_rank
            }

        return standings
    except Exception as e:
        print(f"⚠️ Error fetching NHL standings: {e}")
        return {}


def generate_nhl_games_page(fetch_odds=True):
    """Generate NHL games page from template.

    Args:
        fetch_odds: If False, skip fetching odds data to avoid API rate limits
    """

    # Read template
    template_path = "docs/nhl_games_template.html"
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

    # Get NHL games from the official API
    today = now.date().isoformat()
    nhl_api_url = f"https://api-web.nhle.com/v1/schedule/{today}"
    try:
        response = requests.get(nhl_api_url, timeout=10)
        response.raise_for_status()
        nhl_data = response.json()
        time.sleep(0.6)  # Add delay to avoid 429 rate limits
        nhl_games = nhl_data.get("gameWeek", [])[0].get("games", []) if nhl_data.get("gameWeek") else []
    except:
        nhl_games = []

    # Get NHL odds (optional)
    nhl_odds_data = get_nhl_odds() if fetch_odds else []

    # Generate scroller HTML for NHL games only
    scroller_html = "<div class='games-scroller'>\n"
    scroller_html += "<div class='scroller-title'>Quick Navigation</div>\n"
    scroller_html += "<div class='scroller-container'>\n"

    for game in nhl_games:
        away_team_short = game['awayTeam']['placeName']['default']
        home_team_short = game['homeTeam']['placeName']['default']
        away_team = f"{away_team_short} {game['awayTeam']['commonName']['default']}"
        home_team = f"{home_team_short} {game['homeTeam']['commonName']['default']}"
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
        scroller_html += f"<div class='mini-matchup'>{away_team[:15]} @ {home_team[:15]}</div>\n"
        scroller_html += "</a>\n"

    scroller_html += "</div>\n"  # Close scroller-container
    scroller_html += "</div>\n"  # Close games-scroller

    # Generate NHL games
    nhl_html = ""

    if nhl_games:
        # Get starting goalies
        starting_goalies = get_starting_goalies()

        # Get team standings for season records
        nhl_standings = get_nhl_standings()

        # Get special teams stats (Power Play % and Penalty Kill %)
        special_teams_stats = get_nhl_special_teams_stats()

        # Get player absences (injured/scratched)
        absences_by_team = scrape_nhl_absences_by_team()

        # Get daily projected lines for all teams
        daily_lines_by_team = scrape_nhl_daily_lines()

        for game in nhl_games:
            away_team_short = game['awayTeam']['placeName']['default']
            home_team_short = game['homeTeam']['placeName']['default']
            away_team = f"{away_team_short} {game['awayTeam']['commonName']['default']}"
            home_team = f"{home_team_short} {game['homeTeam']['commonName']['default']}"
            game_time = format_time(game['startTimeUTC'])
            game_id = game.get('id', '')

            # Get team abbreviations from API (more reliable than mapping)
            away_abbrev = game['awayTeam'].get('abbrev', '')
            home_abbrev = game['homeTeam'].get('abbrev', '')

            # Extract team logos
            away_logo = game['awayTeam'].get('logo')
            home_logo = game['homeTeam'].get('logo')

            # Get team records from standings (using abbreviations from API)
            away_standing = nhl_standings.get(away_abbrev, {})
            home_standing = nhl_standings.get(home_abbrev, {})
            away_record = away_standing.get('record') if away_standing else None
            home_record = home_standing.get('record') if home_standing else None
            away_rank = away_standing.get('rank') if away_standing else None
            home_rank = home_standing.get('rank') if home_standing else None

            # Get special teams stats (using abbreviations from API)
            away_special_teams = special_teams_stats.get(away_abbrev)
            home_special_teams = special_teams_stats.get(home_abbrev)

            # Get player absences and goalies (using team nicknames from API)
            away_nickname = game['awayTeam']['commonName']['default']
            home_nickname = game['homeTeam']['commonName']['default']

            # Convert nickname to standardized name for goalie lookup
            away_team_standard = NHL_TEAM_NICKNAME_MAP.get(away_nickname, away_nickname)
            home_team_standard = NHL_TEAM_NICKNAME_MAP.get(home_nickname, home_nickname)

            away_goalie = starting_goalies.get(away_team_standard)
            home_goalie = starting_goalies.get(home_team_standard)

            away_absences = absences_by_team.get(away_nickname, [])
            home_absences = absences_by_team.get(home_nickname, [])

            # Get daily projected lines (using team nicknames)
            away_lines = daily_lines_by_team.get(away_nickname)
            home_lines = daily_lines_by_team.get(home_nickname)

            # Get rest days for each team (using abbreviations)
            away_rest_days = get_rest_days(away_abbrev)
            home_rest_days = get_rest_days(home_abbrev)

            # Parse odds for this game (using short names for matching)
            game_odds = parse_odds(nhl_odds_data, home_team_short, away_team_short)

            nhl_html += generate_game_card(away_team, home_team, game_time, game_odds, away_record, home_record, sport='nhl', away_logo=away_logo, home_logo=home_logo, game_id=game_id, away_goalie=away_goalie, home_goalie=home_goalie, away_team_short=away_abbrev, home_team_short=home_abbrev, away_absences=away_absences, home_absences=home_absences, away_lines=away_lines, home_lines=home_lines, away_special_teams=away_special_teams, home_special_teams=home_special_teams, away_rest_days=away_rest_days, home_rest_days=home_rest_days, away_rank=away_rank, home_rank=home_rank)
    else:
        nhl_html = "<div class='no-games'>No NHL games scheduled for today</div>\n"

    # Fill template
    output = template.replace("{{NAV_HTML}}", nav_html)
    output = output.replace("{{DATE}}", today_str)
    output = output.replace("{{LAST_UPDATED}}", last_updated_str)
    output = output.replace("{{GAMES_SCROLLER}}", scroller_html)
    output = output.replace("{{NHL_GAMES}}", nhl_html)

    # Write to file
    output_file = "docs/nhl/games/index.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"✅ Generated {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate NHL games page')
    parser.add_argument('--no-odds', action='store_true',
                        help='Skip fetching odds to avoid API rate limits')
    args = parser.parse_args()

    generate_nhl_games_page(fetch_odds=not args.no_odds)
