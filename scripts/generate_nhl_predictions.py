import os
import sys
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
import google.genai as genai
from google.genai import types
from data.nhl_games import get_games_today
from data.odds import get_nhl_odds, match_odds_to_games
from datetime import date, timedelta
from data.odds import NHL_TEAM_NAME_MAP
import glob
from scripts.scrape_nhl_absences import scrape_nhl_absences_by_team
from data.starting_goalies import get_starting_goalies
import pytz
from datetime import datetime
import requests
import time

load_dotenv()


# Helper function for API calls with retry logic
def api_call_with_retry(url, max_retries=3, initial_wait=1):
    """
    Make API call with retry logic for rate limiting (429 errors).
    Implements exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                wait_time = initial_wait * (2 ** attempt)
                if attempt < max_retries - 1:
                    print(f"⚠️ Rate limited (429). Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"⚠️ Rate limit exceeded after {max_retries} retries")
                    return None
            else:
                raise
        except Exception as e:
            print(f"⚠️ API error: {e}")
            return None
    return None


# Import helper functions from generate_nhl_games_page
def get_nhl_team_home_away_splits(team_name):
    """
    Fetch home and away record splits for an NHL team from the NHL API.
    Returns separate records for home and away games.
    """
    try:
        # NHL API team abbreviation mapping
        NHL_TEAM_ABBREV_MAP = {
            'Anaheim': 'ANA', 'Boston': 'BOS', 'Buffalo': 'BUF', 'Calgary': 'CGY',
            'Carolina': 'CAR', 'Chicago': 'CHI', 'Colorado': 'COL', 'Columbus': 'CBJ',
            'Dallas': 'DAL', 'Detroit': 'DET', 'Edmonton': 'EDM', 'Florida': 'FLA',
            'Los Angeles': 'LAK', 'Minnesota': 'MIN', 'Montréal': 'MTL', 'Nashville': 'NSH',
            'New Jersey': 'NJD', 'New York': 'NYI', 'Rangers': 'NYR', 'Ottawa': 'OTT',
            'Philadelphia': 'PHI', 'Pittsburgh': 'PIT', 'San Jose': 'SJS', 'Seattle': 'SEA',
            'St. Louis': 'STL', 'Tampa Bay': 'TBL', 'Toronto': 'TOR', 'Vancouver': 'VAN',
            'Vegas': 'VGK', 'Washington': 'WSH', 'Winnipeg': 'WPG', 'Utah': 'UTA'
        }

        team_abbrev = NHL_TEAM_ABBREV_MAP.get(team_name)
        if not team_abbrev:
            return None

        url = f'https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/now'
        response = api_call_with_retry(url)
        if not response:
            return None

        data = response.json()

        completed_games = [
            g for g in data.get('games', [])
            if g.get('gameState') in ['FINAL', 'OFF']
        ]

        # Track home and away separately
        home_wins = home_losses = home_ot_losses = 0
        away_wins = away_losses = away_ot_losses = 0

        for game in completed_games:
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})

            home_abbrev = home_team.get('abbrev')
            away_abbrev = away_team.get('abbrev')
            home_score = home_team.get('score', 0)
            away_score = away_team.get('score', 0)

            is_ot_so = game.get('periodDescriptor', {}).get('periodType') in ['OT', 'SO']

            if team_abbrev == home_abbrev:
                # This team was home
                if home_score > away_score:
                    home_wins += 1
                elif is_ot_so:
                    home_ot_losses += 1
                else:
                    home_losses += 1
            elif team_abbrev == away_abbrev:
                # This team was away
                if away_score > home_score:
                    away_wins += 1
                elif is_ot_so:
                    away_ot_losses += 1
                else:
                    away_losses += 1

        return {
            'home_record': f"{home_wins}-{home_losses}-{home_ot_losses}",
            'away_record': f"{away_wins}-{away_losses}-{away_ot_losses}",
            'home_win_pct': round(home_wins / (home_wins + home_losses + home_ot_losses), 3) if (home_wins + home_losses + home_ot_losses) > 0 else 0,
            'away_win_pct': round(away_wins / (away_wins + away_losses + away_ot_losses), 3) if (away_wins + away_losses + away_ot_losses) > 0 else 0
        }

    except Exception as e:
        print(f"⚠️ Error fetching home/away splits for {team_name}: {e}")
        return None


def get_nhl_team_last_games(team_name, last_n_games=10):
    """
    Fetch last N games for an NHL team from the NHL API.
    Returns stats including avg goals scored/allowed, record, etc.
    """
    try:
        # NHL API team abbreviation mapping
        NHL_TEAM_ABBREV_MAP = {
            'Anaheim': 'ANA', 'Boston': 'BOS', 'Buffalo': 'BUF', 'Calgary': 'CGY',
            'Carolina': 'CAR', 'Chicago': 'CHI', 'Colorado': 'COL', 'Columbus': 'CBJ',
            'Dallas': 'DAL', 'Detroit': 'DET', 'Edmonton': 'EDM', 'Florida': 'FLA',
            'Los Angeles': 'LAK', 'Minnesota': 'MIN', 'Montréal': 'MTL', 'Nashville': 'NSH',
            'New Jersey': 'NJD', 'New York': 'NYI', 'Rangers': 'NYR', 'Ottawa': 'OTT',
            'Philadelphia': 'PHI', 'Pittsburgh': 'PIT', 'San Jose': 'SJS', 'Seattle': 'SEA',
            'St. Louis': 'STL', 'Tampa Bay': 'TBL', 'Toronto': 'TOR', 'Vancouver': 'VAN',
            'Vegas': 'VGK', 'Washington': 'WSH', 'Winnipeg': 'WPG', 'Utah': 'UTA'
        }

        team_abbrev = NHL_TEAM_ABBREV_MAP.get(team_name)
        if not team_abbrev:
            return None

        url = f'https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/now'
        response = api_call_with_retry(url)
        if not response:
            return None

        data = response.json()

        completed_games = [
            g for g in data.get('games', [])
            if g.get('gameState') in ['FINAL', 'OFF']
        ]

        # Get last N games
        completed_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = completed_games[:last_n_games]

        if not recent_games:
            return None

        scores_for = []
        scores_against = []
        wins = 0
        losses = 0
        ot_losses = 0
        first_5_goals = []
        last_5_goals = []

        for idx, game in enumerate(recent_games):
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})

            home_abbrev = home_team.get('abbrev')
            away_abbrev = away_team.get('abbrev')
            home_score = home_team.get('score', 0)
            away_score = away_team.get('score', 0)

            if team_abbrev == home_abbrev:
                gf = home_score
                ga = away_score
                if gf > ga:
                    wins += 1
                elif game.get('periodDescriptor', {}).get('periodType') in ['OT', 'SO']:
                    ot_losses += 1
                else:
                    losses += 1
            elif team_abbrev == away_abbrev:
                gf = away_score
                ga = home_score
                if gf > ga:
                    wins += 1
                elif game.get('periodDescriptor', {}).get('periodType') in ['OT', 'SO']:
                    ot_losses += 1
                else:
                    losses += 1
            else:
                continue

            scores_for.append(gf)
            scores_against.append(ga)
            # first 5 = oldest games (end of list), last 5 = most recent (start of list)
            if idx < 5:
                last_5_goals.append(gf + ga)
            if idx >= last_n_games - 5:
                first_5_goals.append(gf + ga)

        # Calculate streak (recent_games is sorted newest-first)
        streak_type = None
        streak_count = 0
        for game in recent_games:
            home_abbrev = game.get('homeTeam', {}).get('abbrev')
            away_abbrev = game.get('awayTeam', {}).get('abbrev')
            home_score = game.get('homeTeam', {}).get('score', 0)
            away_score = game.get('awayTeam', {}).get('score', 0)

            if team_abbrev == home_abbrev:
                is_win = home_score > away_score
            elif team_abbrev == away_abbrev:
                is_win = away_score > home_score
            else:
                continue

            result = 'W' if is_win else 'L'
            if streak_type is None:
                streak_type = result
                streak_count = 1
            elif result == streak_type:
                streak_count += 1
            else:
                break

        # Form trend: positive = improving (scoring more recently), negative = declining
        form_trend = None
        if len(last_5_goals) >= 3 and len(first_5_goals) >= 3:
            avg_last_5 = sum(last_5_goals) / len(last_5_goals)
            avg_first_5 = sum(first_5_goals) / len(first_5_goals)
            form_trend = round(avg_last_5 - avg_first_5, 2)

        return {
            'avg_scored': round(sum(scores_for) / len(scores_for), 1) if scores_for else 0,
            'avg_allowed': round(sum(scores_against) / len(scores_against), 1) if scores_against else 0,
            'games_analyzed': len(recent_games),
            'wins': wins,
            'losses': losses,
            'ot_losses': ot_losses,
            'record': f"{wins}-{losses}-{ot_losses}",
            'streak_type': streak_type,
            'streak_count': streak_count,
            'form_trend': form_trend,
        }

    except Exception as e:
        print(f"⚠️ Error fetching NHL team stats for {team_name}: {e}")
        return None


def get_head_to_head_stats(team1_name, team2_name, season='20252026'):
    """
    Get head-to-head stats between two teams for the current season.
    """
    try:
        NHL_TEAM_ABBREV_MAP = {
            'Anaheim': 'ANA', 'Boston': 'BOS', 'Buffalo': 'BUF', 'Calgary': 'CGY',
            'Carolina': 'CAR', 'Chicago': 'CHI', 'Colorado': 'COL', 'Columbus': 'CBJ',
            'Dallas': 'DAL', 'Detroit': 'DET', 'Edmonton': 'EDM', 'Florida': 'FLA',
            'Los Angeles': 'LAK', 'Minnesota': 'MIN', 'Montréal': 'MTL', 'Nashville': 'NSH',
            'New Jersey': 'NJD', 'New York': 'NYI', 'Rangers': 'NYR', 'Ottawa': 'OTT',
            'Philadelphia': 'PHI', 'Pittsburgh': 'PIT', 'San Jose': 'SJS', 'Seattle': 'SEA',
            'St. Louis': 'STL', 'Tampa Bay': 'TBL', 'Toronto': 'TOR', 'Vancouver': 'VAN',
            'Vegas': 'VGK', 'Washington': 'WSH', 'Winnipeg': 'WPG', 'Utah': 'UTA'
        }

        team1_abbrev = NHL_TEAM_ABBREV_MAP.get(team1_name)
        team2_abbrev = NHL_TEAM_ABBREV_MAP.get(team2_name)

        if not team1_abbrev or not team2_abbrev:
            return None

        # Add delay to avoid rate limiting
        time.sleep(0.5)

        url = f'https://api-web.nhle.com/v1/club-schedule-season/{team1_abbrev}/now'
        response = api_call_with_retry(url)
        if not response:
            return None

        data = response.json()

        h2h_games = []
        for game in data.get('games', []):
            if game.get('gameState') not in ['FINAL', 'OFF']:
                continue

            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})
            home_abbrev = home_team.get('abbrev')
            away_abbrev = away_team.get('abbrev')

            if team2_abbrev in [home_abbrev, away_abbrev]:
                h2h_games.append(game)

        if not h2h_games:
            return None

        team1_wins = 0
        team2_wins = 0
        last_5_results = []
        total_goals = []

        h2h_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)

        for game in h2h_games[:5]:
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})
            home_abbrev = home_team.get('abbrev')
            away_abbrev = away_team.get('abbrev')
            home_score = home_team.get('score', 0)
            away_score = away_team.get('score', 0)

            total_goals.append(home_score + away_score)

            if home_score > away_score:
                winner_abbrev = home_abbrev
            else:
                winner_abbrev = away_abbrev

            if winner_abbrev == team1_abbrev:
                team1_wins += 1
                result = f"{team1_abbrev} {home_score}-{away_score}" if home_abbrev == team1_abbrev else f"{team1_abbrev} {away_score}-{home_score}"
            else:
                team2_wins += 1
                result = f"{team2_abbrev} {home_score}-{away_score}" if home_abbrev == team2_abbrev else f"{team2_abbrev} {away_score}-{home_score}"

            last_5_results.append(result)

        avg_total_goals = round(sum(total_goals) / len(total_goals), 1) if total_goals else 0

        for game in h2h_games:
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})
            home_score = home_team.get('score', 0)
            away_score = away_team.get('score', 0)

            if home_score > away_score:
                winner_abbrev = home_team.get('abbrev')
            else:
                winner_abbrev = away_team.get('abbrev')

            if winner_abbrev == team1_abbrev:
                team1_wins += 1
            else:
                team2_wins += 1

        return {
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'games_played': len(h2h_games),
            'last_5_results': last_5_results,
            'avg_total_goals': avg_total_goals
        }

    except Exception as e:
        print(f"⚠️ Error fetching H2H stats: {e}")
        return None


def get_nhl_standings():
    """
    Fetch current NHL standings to get team records.
    Returns dict mapping team names to their records (W-L-OTL format).
    Keys use odds API format (e.g., "New York Rangers") for easy lookup.
    """
    try:
        standings_url = 'https://api-web.nhle.com/v1/standings/now'
        response = requests.get(standings_url, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Mapping from standings API names to odds API names (full team names with nicknames)
        STANDINGS_TO_ODDS_MAP = {
            'Anaheim': 'Anaheim Ducks',
            'Boston': 'Boston Bruins',
            'Buffalo': 'Buffalo Sabres',
            'Calgary': 'Calgary Flames',
            'Carolina': 'Carolina Hurricanes',
            'Chicago': 'Chicago Blackhawks',
            'Colorado': 'Colorado Avalanche',
            'Columbus': 'Columbus Blue Jackets',
            'Dallas': 'Dallas Stars',
            'Detroit': 'Detroit Red Wings',
            'Edmonton': 'Edmonton Oilers',
            'Florida': 'Florida Panthers',
            'Los Angeles': 'Los Angeles Kings',
            'Minnesota': 'Minnesota Wild',
            'Montréal': 'Montreal Canadiens',
            'NY Islanders': 'New York Islanders',
            'NY Rangers': 'New York Rangers',
            'Nashville': 'Nashville Predators',
            'New Jersey': 'New Jersey Devils',
            'Ottawa': 'Ottawa Senators',
            'Philadelphia': 'Philadelphia Flyers',
            'Pittsburgh': 'Pittsburgh Penguins',
            'San Jose': 'San Jose Sharks',
            'Seattle': 'Seattle Kraken',
            'St. Louis': 'St Louis Blues',
            'Tampa Bay': 'Tampa Bay Lightning',
            'Toronto': 'Toronto Maple Leafs',
            'Utah': 'Utah Mammoth',
            'Vancouver': 'Vancouver Canucks',
            'Vegas': 'Vegas Golden Knights',
            'Washington': 'Washington Capitals',
            'Winnipeg': 'Winnipeg Jets'
        }

        standings = {}
        for team in data.get('standings', []):
            team_name = team['placeName']['default']
            wins = team['wins']
            losses = team['losses']
            ot_losses = team['otLosses']
            points = team['points']
            games_played = team['gamesPlayed']
            record = f"{wins}-{losses}-{ot_losses}"

            # Map to odds API format if needed
            mapped_name = STANDINGS_TO_ODDS_MAP.get(team_name, team_name)

            standings[mapped_name] = {
                'record': record,
                'wins': wins,
                'losses': losses,
                'ot_losses': ot_losses,
                'points': points,
                'games_played': games_played,
                'points_pct': round(points / (games_played * 2), 3) if games_played > 0 else 0
            }

        return standings
    except Exception as e:
        print(f"⚠️ Error fetching NHL standings: {e}")
        return {}


def get_nhl_special_teams_stats():
    """
    Fetch NHL special teams stats (Power Play % and Penalty Kill %).
    Returns dict mapping full team names (odds API format) to their PP% and PK%.
    """
    try:
        stats_url = 'https://api.nhle.com/stats/rest/en/team/summary?cayenneExp=seasonId=20252026'
        response = requests.get(stats_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        time.sleep(0.6)

        special_teams = {}
        STANDINGS_TO_ODDS_MAP = {
            'Anaheim Ducks': 'Anaheim Ducks',
            'Boston Bruins': 'Boston Bruins',
            'Buffalo Sabres': 'Buffalo Sabres',
            'Calgary Flames': 'Calgary Flames',
            'Carolina Hurricanes': 'Carolina Hurricanes',
            'Chicago Blackhawks': 'Chicago Blackhawks',
            'Colorado Avalanche': 'Colorado Avalanche',
            'Columbus Blue Jackets': 'Columbus Blue Jackets',
            'Dallas Stars': 'Dallas Stars',
            'Detroit Red Wings': 'Detroit Red Wings',
            'Edmonton Oilers': 'Edmonton Oilers',
            'Florida Panthers': 'Florida Panthers',
            'Los Angeles Kings': 'Los Angeles Kings',
            'Minnesota Wild': 'Minnesota Wild',
            'Montréal Canadiens': 'Montreal Canadiens',
            'Montreal Canadiens': 'Montreal Canadiens',
            'Nashville Predators': 'Nashville Predators',
            'New Jersey Devils': 'New Jersey Devils',
            'New York Islanders': 'New York Islanders',
            'New York Rangers': 'New York Rangers',
            'Ottawa Senators': 'Ottawa Senators',
            'Philadelphia Flyers': 'Philadelphia Flyers',
            'Pittsburgh Penguins': 'Pittsburgh Penguins',
            'San Jose Sharks': 'San Jose Sharks',
            'Seattle Kraken': 'Seattle Kraken',
            'St. Louis Blues': 'St Louis Blues',
            'Tampa Bay Lightning': 'Tampa Bay Lightning',
            'Toronto Maple Leafs': 'Toronto Maple Leafs',
            'Utah Mammoth': 'Utah Mammoth',
            'Vancouver Canucks': 'Vancouver Canucks',
            'Vegas Golden Knights': 'Vegas Golden Knights',
            'Washington Capitals': 'Washington Capitals',
            'Winnipeg Jets': 'Winnipeg Jets',
        }

        for team_stat in data.get('data', []):
            team_full_name = team_stat.get('teamFullName', '')
            pp_pct = round(team_stat.get('powerPlayPct', 0) * 100, 1)
            pk_pct = round(team_stat.get('penaltyKillPct', 0) * 100, 1)
            odds_name = STANDINGS_TO_ODDS_MAP.get(team_full_name)
            if odds_name:
                special_teams[odds_name] = {'pp_pct': pp_pct, 'pk_pct': pk_pct}

        return special_teams
    except Exception as e:
        print(f"⚠️ Error fetching NHL special teams stats: {e}")
        return {}


def get_rest_days_for_team(team_name):
    """
    Get the number of rest days since team's last game.
    Returns int (0 = back-to-back, 1 = one day rest, etc.) or None on error.
    """
    try:
        NHL_TEAM_ABBREV_MAP = {
            'Anaheim': 'ANA', 'Boston': 'BOS', 'Buffalo': 'BUF', 'Calgary': 'CGY',
            'Carolina': 'CAR', 'Chicago': 'CHI', 'Colorado': 'COL', 'Columbus': 'CBJ',
            'Dallas': 'DAL', 'Detroit': 'DET', 'Edmonton': 'EDM', 'Florida': 'FLA',
            'Los Angeles': 'LAK', 'Minnesota': 'MIN', 'Montréal': 'MTL', 'Nashville': 'NSH',
            'New Jersey': 'NJD', 'New York': 'NYI', 'Rangers': 'NYR', 'Ottawa': 'OTT',
            'Philadelphia': 'PHI', 'Pittsburgh': 'PIT', 'San Jose': 'SJS', 'Seattle': 'SEA',
            'St. Louis': 'STL', 'Tampa Bay': 'TBL', 'Toronto': 'TOR', 'Vancouver': 'VAN',
            'Vegas': 'VGK', 'Washington': 'WSH', 'Winnipeg': 'WPG', 'Utah': 'UTA'
        }

        team_abbrev = NHL_TEAM_ABBREV_MAP.get(team_name)
        if not team_abbrev:
            return None

        url = f'https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/now'
        response = api_call_with_retry(url)
        if not response:
            return None

        data = response.json()
        completed_games = [
            g for g in data.get('games', [])
            if g.get('gameState') in ['FINAL', 'OFF']
        ]
        if not completed_games:
            return None

        completed_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        last_game_date_str = completed_games[0].get('gameDate', '')
        if not last_game_date_str:
            return None

        today = date.today()
        last_game_date = date.fromisoformat(last_game_date_str[:10])
        rest_days = (today - last_game_date).days - 1
        return rest_days

    except Exception as e:
        print(f"⚠️ Error getting rest days for {team_name}: {e}")
        return None


def get_playoff_series_status(season='20252026'):
    """
    Fetch current NHL playoff series status using today's schedule endpoint
    which includes seriesStatus on each game.
    """
    try:
        from datetime import date as date_mod
        today_str = date_mod.today().isoformat()
        url = f'https://api-web.nhle.com/v1/schedule/{today_str}'
        response = api_call_with_retry(url)
        if not response:
            return "Playoff series status: Unavailable"

        data = response.json()
        games = data.get('gameWeek', [{}])[0].get('games', [])

        output = "PLAYOFF SERIES STATUS:\n"
        output += "=" * 40 + "\n"

        series_found = False

        for game in games:
            ss = game.get('seriesStatus')
            if not ss:
                continue

            top_abbrev = ss.get('topSeedTeamAbbrev', '')
            bot_abbrev = ss.get('bottomSeedTeamAbbrev', '')
            top_wins = ss.get('topSeedWins', 0)
            bot_wins = ss.get('bottomSeedWins', 0)
            next_game_num = top_wins + bot_wins + 1
            round_name = {1: 'Round 1', 2: 'Round 2', 3: 'Conference Finals', 4: 'Stanley Cup Final'}.get(ss.get('round', 1), 'Round 1')

            home = game.get('homeTeam', {})
            away = game.get('awayTeam', {})
            home_abbrev = home.get('abbrev', '')
            away_abbrev = away.get('abbrev', '')
            home_name = home.get('commonName', {}).get('default', home_abbrev)
            away_name = away.get('commonName', {}).get('default', away_abbrev)

            top_name = home_name if home_abbrev == top_abbrev else away_name
            bot_name = home_name if home_abbrev == bot_abbrev else away_name

            if top_wins > bot_wins:
                leader, leader_wins, trailer_wins = top_name, top_wins, bot_wins
            elif bot_wins > top_wins:
                leader, leader_wins, trailer_wins = bot_name, bot_wins, top_wins
            else:
                leader = None

            if top_wins == 4:
                status = f"{top_name} WON SERIES 4-{bot_wins}"
            elif bot_wins == 4:
                status = f"{bot_name} WON SERIES 4-{top_wins}"
            elif leader:
                status = f"{leader} leads {leader_wins}-{trailer_wins} (Game {next_game_num} next)"
            else:
                status = f"Series tied {top_wins}-{bot_wins} (Game {next_game_num} next)"

            home_games = {1: 'top', 2: 'top', 3: 'bottom', 4: 'bottom', 5: 'top', 6: 'bottom', 7: 'top'}
            next_home_seed = home_games.get(next_game_num, 'top')
            next_home_team = top_name if next_home_seed == 'top' else bot_name
            next_away_team = bot_name if next_home_seed == 'top' else top_name

            output += f"\n{round_name}: {away_name} @ {home_name}\n"
            output += f"  Series Status: {status}\n"
            output += f"  Next Game: Game {next_game_num} — {next_away_team} @ {next_home_team}\n"

            if top_wins == 3 and bot_wins < 3:
                output += f"  ELIMINATION GAME: {bot_name} must win or season ends\n"
            elif bot_wins == 3 and top_wins < 3:
                output += f"  ELIMINATION GAME: {top_name} must win or season ends\n"
            elif top_wins == 3 and bot_wins == 3:
                output += f"  GAME 7 — WINNER TAKE ALL\n"

            series_found = True

        if not series_found:
            return "Playoff series status: No active series found"

        return output

    except Exception as e:
        print(f"Warning: Error fetching playoff series status: {e}")
        return f"Playoff series status: Error fetching data ({e})"


def get_playoff_goalie_stats(home_team, away_team, starting_goalies, season='20252026'):
    """
    For both teams' confirmed starting goalies, fetch their playoff-specific stats.
    Returns a formatted string ready to inject into {{PLAYOFF_GOALIE_STATS}}.
    """

    def fetch_goalie_playoff_stats(goalie_name):
        try:
            search_url = f'https://api-web.nhle.com/v1/player-search?q={goalie_name.replace(" ", "%20")}&culture=en'
            search_resp = api_call_with_retry(search_url)
            if not search_resp:
                return None

            players = search_resp.json().get('players', [])
            if not players:
                return None

            goalie_id = None
            for p in players:
                if p.get('positionCode') == 'G':
                    goalie_id = p.get('playerId')
                    break

            if not goalie_id:
                return None

            time.sleep(0.3)

            gamelog_url = f'https://api-web.nhle.com/v1/player/{goalie_id}/game-log/{season}/3'
            gamelog_resp = api_call_with_retry(gamelog_url)
            if not gamelog_resp:
                return None

            games = gamelog_resp.json().get('gameLog', [])
            if not games:
                return None

            games.sort(key=lambda x: x.get('gameDate', ''))

            total_shots_against = 0
            total_saves = 0
            total_goals_against = 0
            total_toi_seconds = 0
            total_starts = 0
            shutouts = 0

            for g in games:
                toi = g.get('toi', '0:00')
                try:
                    parts = toi.split(':')
                    toi_seconds = int(parts[0]) * 60 + int(parts[1])
                except Exception:
                    toi_seconds = 0

                if toi_seconds < 600:
                    continue

                sa = g.get('shotsAgainst', 0)
                ga = g.get('goalsAgainst', 0)
                saves = sa - ga

                total_shots_against += sa
                total_saves += saves
                total_goals_against += ga
                total_toi_seconds += toi_seconds
                total_starts += 1

                if ga == 0 and toi_seconds > 3000:
                    shutouts += 1

            if total_starts == 0:
                return None

            overall_sv_pct = round(total_saves / total_shots_against, 3) if total_shots_against > 0 else 0
            overall_gaa = round((total_goals_against / total_toi_seconds) * 3600, 2) if total_toi_seconds > 0 else 0

            last_3_games = games[-3:] if len(games) >= 3 else games
            l3_shots = 0
            l3_saves_count = 0
            l3_ga = 0
            l3_toi = 0

            for g in last_3_games:
                toi = g.get('toi', '0:00')
                try:
                    parts = toi.split(':')
                    toi_seconds = int(parts[0]) * 60 + int(parts[1])
                except Exception:
                    toi_seconds = 0

                if toi_seconds < 600:
                    continue

                sa = g.get('shotsAgainst', 0)
                ga = g.get('goalsAgainst', 0)
                l3_shots += sa
                l3_saves_count += (sa - ga)
                l3_ga += ga
                l3_toi += toi_seconds

            l3_sv_pct = round(l3_saves_count / l3_shots, 3) if l3_shots > 0 else 0
            l3_gaa = round((l3_ga / l3_toi) * 3600, 2) if l3_toi > 0 else 0

            return {
                'playoff_starts': total_starts,
                'overall_sv_pct': overall_sv_pct,
                'overall_gaa': overall_gaa,
                'shutouts': shutouts,
                'last_3_sv_pct': l3_sv_pct,
                'last_3_gaa': l3_gaa,
            }

        except Exception as e:
            print(f"Warning: Error fetching playoff goalie stats for {goalie_name}: {e}")
            return None

    output = "PLAYOFF GOALIE STATS:\n"
    output += "=" * 40 + "\n"

    for team_full in [away_team, home_team]:
        team_normalized = team_full.replace('Montréal', 'Montreal')
        goalie_info = starting_goalies.get(team_normalized)

        output += f"\n{team_full} Starting Goalie:\n"

        if not goalie_info:
            output += "  Name: Unconfirmed\n"
            output += "  Playoff Stats: Not available\n"
            continue

        goalie_name = goalie_info.get('name', 'Unknown')
        goalie_status = goalie_info.get('status', '')
        output += f"  Name: {goalie_name} ({goalie_status})\n"

        if 'sv_pct' in goalie_info:
            output += f"  Regular Season SV%: {goalie_info['sv_pct']}\n"
            output += f"  Regular Season GAA: {goalie_info['gaa']}\n"

        playoff_stats = fetch_goalie_playoff_stats(goalie_name)
        time.sleep(0.4)

        if playoff_stats and playoff_stats['playoff_starts'] > 0:
            output += f"  Playoff Starts (this run): {playoff_stats['playoff_starts']}\n"
            output += f"  Playoff Overall SV%: {playoff_stats['overall_sv_pct']:.3f}\n"
            output += f"  Playoff Overall GAA: {playoff_stats['overall_gaa']:.2f}\n"
            output += f"  Playoff Shutouts: {playoff_stats['shutouts']}\n"
            output += f"  Last 3 Playoff Starts SV%: {playoff_stats['last_3_sv_pct']:.3f}\n"
            output += f"  Last 3 Playoff Starts GAA: {playoff_stats['last_3_gaa']:.2f}\n"

            l3_sv = playoff_stats['last_3_sv_pct']
            if l3_sv >= 0.930:
                tier = "PLAYOFF ELITE (Stealing games)"
            elif l3_sv >= 0.915:
                tier = "PLAYOFF HOT (Strong form)"
            elif l3_sv >= 0.900:
                tier = "PLAYOFF AVERAGE"
            elif l3_sv >= 0.885:
                tier = "PLAYOFF STRUGGLING"
            else:
                tier = "PLAYOFF COLD (Major liability)"
            output += f"  Current Form Tier: {tier}\n"
        else:
            output += "  Playoff Stats: No playoff starts yet this run\n"
            output += "  NOTE: Use regular season Last 5 SV% as proxy (see {{GOALIE_STATS}})\n"

    return output


def analyze_results(results_text, absences_text, recent_games, team_stats_text, h2h_stats_text, goalie_stats_text, home_away_splits_text, standings_text, special_teams_text, playoff_series_text="", playoff_goalie_stats_text=""):
    api_key = os.environ["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)

    # Read and concatenate all historical NHL results files
    hist_dir = os.path.join("data", "bot_results", "nhl")
    hist_files = sorted(glob.glob(os.path.join(hist_dir, "nhl_daily_results_*.txt")))
    historical_results = ""
    for hf in hist_files:
        try:
            with open(hf, "r", encoding="utf-8") as hfile:
                historical_results += f"\n---\n{os.path.basename(hf)}\n" + hfile.read()
        except Exception:
            continue

    # Read last 10 days' result files
    last_10_files = hist_files[-10:] if len(hist_files) >= 10 else hist_files
    recent_results = ""
    for rf in last_10_files:
        try:
            with open(rf, "r", encoding="utf-8") as rfile:
                recent_results += f"\n---\n{os.path.basename(rf)}\n" + rfile.read()
        except Exception:
            continue

    # Strictly read external prompt file; no fallback
    # Use the 7am-specific prompt (no goalie data) for early run, standard prompt for 3pm
    # In playoff mode, use the playoff-specific prompt
    is_playoffs = os.environ.get("PLAYOFF_MODE", "").lower() in ("1", "true", "yes")
    if is_playoffs and run_time == "7am":
        prompt_path = os.path.join("prompts", "nhl_prompt_playoffs_7am.txt")
    elif is_playoffs:
        prompt_path = os.path.join("prompts", "nhl_playoff_prompt.txt")
    elif run_time == "7am":
        prompt_path = os.path.join("prompts", "nhl_prompt_7am.txt")
    else:
        prompt_path = os.path.join("prompts", "nhl_prompt.txt")
    today_str = date.today().isoformat()
    try:
        with open(prompt_path, "r", encoding="utf-8") as pf:
            prompt_text = pf.read()
            prompt_text = prompt_text.replace("{{RESULTS_TEXT}}", results_text)
            prompt_text = prompt_text.replace("{{TODAY_DATE}}", today_str)
            prompt_text = prompt_text.replace("{{HISTORICAL_RESULTS}}", historical_results)
            prompt_text = prompt_text.replace("{{RECENT_RESULTS}}", recent_results)
            prompt_text = prompt_text.replace("{{ABSENCES}}", absences_text)
            prompt_text = prompt_text.replace("{{RECENT_GAMES}}", recent_games)
            prompt_text = prompt_text.replace("{{TEAM_STATS}}", team_stats_text)
            prompt_text = prompt_text.replace("{{H2H_STATS}}", h2h_stats_text)
            prompt_text = prompt_text.replace("{{GOALIE_STATS}}", goalie_stats_text)
            prompt_text = prompt_text.replace("{{HOME_AWAY_SPLITS}}", home_away_splits_text)
            prompt_text = prompt_text.replace("{{STANDINGS}}", standings_text)
            prompt_text = prompt_text.replace("{{SPECIAL_TEAMS}}", special_teams_text)
            prompt_text = prompt_text.replace("{{PLAYOFF_SERIES_STATUS}}", playoff_series_text)
            prompt_text = prompt_text.replace("{{PLAYOFF_GOALIE_STATS}}", playoff_goalie_stats_text)
    except Exception:
        return "AI analysis skipped: prompt file not found or unreadable."

    # Model fallback order — try each on 503, then give up
    models_to_try = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.5-flash-lite",
    ]
    retry_waits = [30, 60]  # seconds between retries on same model

    for model in models_to_try:
        max_retries = len(retry_waits) + 1
        for attempt in range(max_retries):
            try:
                print(f"🤖 Trying {model}...")
                response = client.models.generate_content(
                    model=model,
                    contents=types.Part.from_text(text=prompt_text),
                )
                return response.candidates[0].content.parts[0].text
            except genai.errors.ServerError as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = retry_waits[attempt]
                        print(f"⚠️ {model} 503 error. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"⚠️ {model} still unavailable, trying next model...")
                        break
                else:
                    raise
            except genai.errors.ClientError as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e):
                    print(f"⚠️ {model} quota exceeded, trying next model...")
                    break
                else:
                    raise

    print(f"❌ All Gemini models unavailable. Cancelling workflow.")
    sys.exit(1)

# --- New logic for 7am/3pm runs ---
def detect_run_time():
    env_run_time = os.environ.get("NHL_RUN_TIME")
    if env_run_time:
        return env_run_time.lower()
    # Default: auto-detect based on Montreal time
    # 7am run: 6:00am–12:59pm (6-12 inclusive)
    # More versatile window to account for any scheduling variations
    tz = pytz.timezone("America/Toronto")
    now = datetime.now(tz)
    hour = now.hour
    if 6 <= hour <= 12:
        return "7am"
    else:
        # Everything else is 3pm run
        return "3pm"

run_time = detect_run_time()
today_str = date.today().isoformat()
predictions_folder = os.path.join("data", "predictions", "nhl")
daily_runs_folder = os.path.join(predictions_folder, "daily_runs")
os.makedirs(predictions_folder, exist_ok=True)
os.makedirs(daily_runs_folder, exist_ok=True)

# Write directly to daily_runs folder for 7am/3pm runs
if run_time == "7am":
    filename = os.path.join(daily_runs_folder, f"nhl_daily_predictions_{today_str}_7am.txt")
elif run_time == "3pm":
    filename = os.path.join(daily_runs_folder, f"nhl_daily_predictions_{today_str}_3pm.txt")
else:
    # Fallback goes to main folder
    filename = os.path.join(predictions_folder, f"nhl_daily_predictions_{today_str}.txt")

# Check if file already exists - skip if it does
if os.path.exists(filename):
    print(f"⚠️  Predictions file already exists: {filename}")
    print("Skipping prediction generation to avoid overwriting existing file.")
    exit(0)

# Fetch and save games data
games = get_games_today()

# Save raw games data to file
games_data_folder = os.path.join("data", "games", "nhl")
os.makedirs(games_data_folder, exist_ok=True)
games_data_file = os.path.join(games_data_folder, f"nhl_games_{today_str}.txt")

with open(games_data_file, "w") as gf:
    gf.write(f"Date: {today_str}\n\n")
    if games:
        for game in games:
            gf.write(f"{game['away']} @ {game['home']}\n")
    else:
        gf.write("No games today\n")

print(f"✅ Saved raw games data to: {games_data_file}")

# Get player absences (injuries and scratches) as a formatted string
absences_list = scrape_nhl_absences_by_team()
if absences_list:
    # Format absences by team, one team per line, indented players
    absences_text = "NHL Player Absences by Team:\n"
    for team, players in absences_list.items():
        if players:
            absences_text += f"{team}:\n"
            for player in players:
                absences_text += f"  - {player}\n"
else:
    absences_text = "NHL Player Absences by Team: None"

# Read last 7 days of games from saved files
games_dir = os.path.join("data", "games", "nhl")
games_files = sorted(glob.glob(os.path.join(games_dir, "nhl_games_*.txt")))
last_7_files = games_files[-7:] if len(games_files) >= 7 else games_files
recent_games = ""
for gf in last_7_files:
    try:
        with open(gf, "r", encoding="utf-8") as gfile:
            recent_games += f"\n---\n{os.path.basename(gf)}\n" + gfile.read()
    except Exception:
        continue

if not recent_games:
    recent_games = "No recent games data available"

with open(filename, "w") as f:
    f.write(f"Date: {today_str}\n\n")

    if not games:
        f.write("No NHL games today\n")
        print("No NHL games today")
    else:
        odds_data = get_nhl_odds()
        matched = match_odds_to_games(games, odds_data, NHL_TEAM_NAME_MAP)

        # Get starting goalies (only for 3pm run)
        if run_time == "3pm":
            starting_goalies = get_starting_goalies()
        else:
            starting_goalies = {}

        # Get NHL standings
        standings = get_nhl_standings()

        results_text = ""
        team_stats_text = ""
        h2h_stats_text = ""
        goalie_stats_text = ""
        home_away_splits_text = ""
        standings_text = ""
        special_teams_text = ""
        playoff_goalie_stats_text = ""

        # Fetch playoff series status once (only in playoff mode)
        is_playoffs = os.environ.get("PLAYOFF_MODE", "").lower() in ("1", "true", "yes")
        if is_playoffs:
            print("Fetching playoff series status...")
            playoff_series_text = get_playoff_series_status()
            print(playoff_series_text)
        else:
            playoff_series_text = ""

        # Fetch special teams stats once (not per-game)
        print("Fetching NHL special teams stats (PP%/PK%)...")
        special_teams_data = get_nhl_special_teams_stats()

        for g in matched:
            away_team = g['away']
            home_team = g['home']

            line = (
                f"{away_team} @ {home_team}\n"
                f"{home_team} ML (Home): {g['home_odds']}, {away_team} ML (Away): {g['away_odds']}, O/U: {g['over_under']}\n"
                "------\n"
            )
            f.write(line)
            results_text += line

            # Extract proper team names for API calls
            # Map full team names to searchable names used in NHL_TEAM_ABBREV_MAP
            def get_team_name_for_api(full_name):
                """Convert full team name to name used in NHL API mapping"""
                if 'Montréal' in full_name or 'Montreal' in full_name:
                    return 'Montréal'
                elif 'Islanders' in full_name:
                    return 'New York'
                elif 'Rangers' in full_name:
                    return 'Rangers'
                elif 'Golden Knights' in full_name:
                    return 'Vegas'
                elif ('St.' in full_name or 'St ' in full_name) and 'Louis' in full_name:
                    return 'St. Louis'
                elif 'Los Angeles' in full_name:
                    return 'Los Angeles'
                elif 'New Jersey' in full_name:
                    return 'New Jersey'
                elif 'San Jose' in full_name:
                    return 'San Jose'
                elif 'Tampa Bay' in full_name:
                    return 'Tampa Bay'
                elif ' ' in full_name:
                    # For two-word names, try to find the first part
                    first_word = full_name.split()[0]
                    return first_word
                else:
                    return full_name

            away_short = get_team_name_for_api(away_team)
            home_short = get_team_name_for_api(home_team)

            # Fetch team stats (last 10 games)
            away_stats = get_nhl_team_last_games(away_short, last_n_games=10)
            time.sleep(0.5)  # Add delay to avoid rate limiting
            home_stats = get_nhl_team_last_games(home_short, last_n_games=10)
            time.sleep(0.5)  # Add delay to avoid rate limiting

            if not away_stats:
                print(f"⚠️  No stats found for {away_team} (searched as: {away_short})")
            if not home_stats:
                print(f"⚠️  No stats found for {home_team} (searched as: {home_short})")

            team_stats_text += f"\n{away_team} (Last 10 Games):\n"
            if away_stats:
                team_stats_text += f"  Record: {away_stats['record']}\n"
                team_stats_text += f"  Avg Goals Scored: {away_stats['avg_scored']}\n"
                team_stats_text += f"  Avg Goals Allowed: {away_stats['avg_allowed']}\n"
                if away_stats.get('streak_type') and away_stats.get('streak_count', 0) >= 2:
                    team_stats_text += f"  Current Streak: {away_stats['streak_count']}{away_stats['streak_type']}\n"
                if away_stats.get('form_trend') is not None:
                    trend = away_stats['form_trend']
                    trend_label = "Improving" if trend > 0.3 else ("Declining" if trend < -0.3 else "Stable")
                    team_stats_text += f"  Form Trend (last5 vs first5 avg total goals): {trend:+.2f} ({trend_label})\n"
            else:
                team_stats_text += "  No stats available\n"

            team_stats_text += f"\n{home_team} (Last 10 Games):\n"
            if home_stats:
                team_stats_text += f"  Record: {home_stats['record']}\n"
                team_stats_text += f"  Avg Goals Scored: {home_stats['avg_scored']}\n"
                team_stats_text += f"  Avg Goals Allowed: {home_stats['avg_allowed']}\n"
                if home_stats.get('streak_type') and home_stats.get('streak_count', 0) >= 2:
                    team_stats_text += f"  Current Streak: {home_stats['streak_count']}{home_stats['streak_type']}\n"
                if home_stats.get('form_trend') is not None:
                    trend = home_stats['form_trend']
                    trend_label = "Improving" if trend > 0.3 else ("Declining" if trend < -0.3 else "Stable")
                    team_stats_text += f"  Form Trend (last5 vs first5 avg total goals): {trend:+.2f} ({trend_label})\n"
            else:
                team_stats_text += "  No stats available\n"

            # Fetch home/away splits
            away_splits = get_nhl_team_home_away_splits(away_short)
            home_splits = get_nhl_team_home_away_splits(home_short)

            home_away_splits_text += f"\n{away_team} (Home/Away Splits):\n"
            if away_splits:
                home_away_splits_text += f"  Home Record: {away_splits['home_record']} (Win %: {away_splits['home_win_pct']:.3f})\n"
                home_away_splits_text += f"  Away Record: {away_splits['away_record']} (Win %: {away_splits['away_win_pct']:.3f})\n"
            else:
                home_away_splits_text += "  No splits available\n"

            home_away_splits_text += f"\n{home_team} (Home/Away Splits):\n"
            if home_splits:
                home_away_splits_text += f"  Home Record: {home_splits['home_record']} (Win %: {home_splits['home_win_pct']:.3f})\n"
                home_away_splits_text += f"  Away Record: {home_splits['away_record']} (Win %: {home_splits['away_win_pct']:.3f})\n"
            else:
                home_away_splits_text += "  No splits available\n"

            # Fetch head-to-head stats
            h2h_stats = get_head_to_head_stats(away_short, home_short)
            h2h_stats_text += f"\n{away_team} vs {home_team} (Head-to-Head This Season):\n"
            if h2h_stats:
                h2h_stats_text += f"  Series: {away_team} {h2h_stats['team1_wins']} - {h2h_stats['team2_wins']} {home_team}\n"
                h2h_stats_text += f"  Games Played: {h2h_stats['games_played']}\n"
                h2h_stats_text += f"  Avg Total Goals: {h2h_stats['avg_total_goals']}\n"
                if h2h_stats['last_5_results']:
                    h2h_stats_text += f"  Last 5 Results: {', '.join(h2h_stats['last_5_results'])}\n"
            else:
                h2h_stats_text += "  No head-to-head games this season\n"

            # Fetch goalie stats (only for 3pm run)
            if run_time == "3pm":
                # Use full team name from odds API (away_team, home_team) to match starting_goalies keys
                # Normalize Montréal to Montreal (accent issue)
                away_team_normalized = away_team.replace('Montréal', 'Montreal')
                home_team_normalized = home_team.replace('Montréal', 'Montreal')

                away_goalie_info = starting_goalies.get(away_team_normalized)
                home_goalie_info = starting_goalies.get(home_team_normalized)

                goalie_stats_text += f"\n{away_team} Starting Goalie:\n"
                if away_goalie_info:
                    goalie_stats_text += f"  Name: {away_goalie_info['name']} ({away_goalie_info['status']})\n"
                    if 'record' in away_goalie_info:
                        goalie_stats_text += f"  Season Record: {away_goalie_info['record']}\n"
                        goalie_stats_text += f"  Season GAA: {away_goalie_info['gaa']}\n"
                        goalie_stats_text += f"  Season SV%: {away_goalie_info['sv_pct']}\n"
                        goalie_stats_text += f"  Last 5 Starts: {away_goalie_info['last_5_record']}\n"
                        goalie_stats_text += f"  Last 5 GAA: {away_goalie_info['last_5_gaa']}\n"
                        goalie_stats_text += f"  Last 5 SV%: {away_goalie_info['last_5_sv_pct']}\n"
                else:
                    goalie_stats_text += "  No goalie confirmed\n"

                goalie_stats_text += f"\n{home_team} Starting Goalie:\n"
                if home_goalie_info:
                    goalie_stats_text += f"  Name: {home_goalie_info['name']} ({home_goalie_info['status']})\n"
                    if 'record' in home_goalie_info:
                        goalie_stats_text += f"  Season Record: {home_goalie_info['record']}\n"
                        goalie_stats_text += f"  Season GAA: {home_goalie_info['gaa']}\n"
                        goalie_stats_text += f"  Season SV%: {home_goalie_info['sv_pct']}\n"
                        goalie_stats_text += f"  Last 5 Starts: {home_goalie_info['last_5_record']}\n"
                        goalie_stats_text += f"  Last 5 GAA: {home_goalie_info['last_5_gaa']}\n"
                        goalie_stats_text += f"  Last 5 SV%: {home_goalie_info['last_5_sv_pct']}\n"
                else:
                    goalie_stats_text += "  No goalie confirmed\n"

                goalie_stats_text += "\n"

                # Fetch playoff goalie stats (only in playoff mode)
                if is_playoffs:
                    playoff_goalie_stats_text += get_playoff_goalie_stats(
                        home_team, away_team, starting_goalies
                    )
            # Standings dict is keyed by full team names (e.g., 'Montreal Canadiens', 'Boston Bruins')
            # from get_nhl_standings() which uses STANDINGS_TO_ODDS_MAP
            # Normalize Montréal to Montreal for consistent lookup
            away_team_lookup = away_team.replace('Montréal', 'Montreal')
            home_team_lookup = home_team.replace('Montréal', 'Montreal')

            away_standing = standings.get(away_team_lookup)
            home_standing = standings.get(home_team_lookup)

            standings_text += f"\n{away_team} (Season Standings):\n"
            if away_standing:
                standings_text += f"  Record: {away_standing['record']}\n"
                standings_text += f"  Points: {away_standing['points']}\n"
                standings_text += f"  Points %: {away_standing['points_pct']:.3f}\n"
                standings_text += f"  Games Played: {away_standing['games_played']}\n"
            else:
                standings_text += "  No standings data\n"

            standings_text += f"\n{home_team} (Season Standings):\n"
            if home_standing:
                standings_text += f"  Record: {home_standing['record']}\n"
                standings_text += f"  Points: {home_standing['points']}\n"
                standings_text += f"  Points %: {home_standing['points_pct']:.3f}\n"
                standings_text += f"  Games Played: {home_standing['games_played']}\n"
            else:
                standings_text += "  No standings data\n"

            # Build special teams text for this game
            away_st = special_teams_data.get(away_team.replace('Montréal', 'Montreal'))
            home_st = special_teams_data.get(home_team.replace('Montréal', 'Montreal'))

            special_teams_text += f"\n{away_team} (Special Teams):\n"
            if away_st:
                special_teams_text += f"  Power Play %: {away_st['pp_pct']}%\n"
                special_teams_text += f"  Penalty Kill %: {away_st['pk_pct']}%\n"
            else:
                special_teams_text += "  No special teams data\n"

            special_teams_text += f"\n{home_team} (Special Teams):\n"
            if home_st:
                special_teams_text += f"  Power Play %: {home_st['pp_pct']}%\n"
                special_teams_text += f"  Penalty Kill %: {home_st['pk_pct']}%\n"
            else:
                special_teams_text += "  No special teams data\n"

            # Fetch rest days for each team
            away_rest = get_rest_days_for_team(away_short)
            time.sleep(0.5)
            home_rest = get_rest_days_for_team(home_short)
            time.sleep(0.5)

            def rest_label(rest_days):
                if rest_days is None:
                    return "Unknown"
                if rest_days <= 0:
                    return "Back-to-Back (0 rest days)"
                return f"{rest_days} rest day(s)"

            special_teams_text += f"\n{away_team} Rest: {rest_label(away_rest)}\n"
            special_teams_text += f"{home_team} Rest: {rest_label(home_rest)}\n"


        print("NHL Matchups and Odds:")
        print(results_text)
        print(absences_text)
        print("\nTeam Stats:")
        print(team_stats_text)
        print("\nHome/Away Splits:")
        print(home_away_splits_text)
        print("\nSpecial Teams (PP%/PK%) & Rest Days:")
        print(special_teams_text)
        print("\nStandings:")
        print(standings_text)
        print("\nHead-to-Head Stats:")
        print(h2h_stats_text)
        if run_time == "3pm":
            print("\nGoalie Stats:")
            print(goalie_stats_text)
            if is_playoffs:
                print("\nPlayoff Goalie Stats:")
                print(playoff_goalie_stats_text)
        print("\nRecent Games:")
        print(recent_games)

        if results_text:
            summary = analyze_results(results_text, absences_text, recent_games, team_stats_text, h2h_stats_text, goalie_stats_text, home_away_splits_text, standings_text, special_teams_text, playoff_series_text, playoff_goalie_stats_text)
            f.write("\nAI Analysis Summary:\n")
            f.write(summary + "\n")
            print("\nAI Analysis Summary:")
            print(summary)

print(f"Saved daily results to {filename}")
