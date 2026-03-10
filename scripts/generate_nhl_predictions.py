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

        for game in recent_games:
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})

            home_abbrev = home_team.get('abbrev')
            away_abbrev = away_team.get('abbrev')
            home_score = home_team.get('score', 0)
            away_score = away_team.get('score', 0)

            if team_abbrev == home_abbrev:
                scores_for.append(home_score)
                scores_against.append(away_score)
                if home_score > away_score:
                    wins += 1
                elif game.get('periodDescriptor', {}).get('periodType') in ['OT', 'SO']:
                    ot_losses += 1
                else:
                    losses += 1
            elif team_abbrev == away_abbrev:
                scores_for.append(away_score)
                scores_against.append(home_score)
                if away_score > home_score:
                    wins += 1
                elif game.get('periodDescriptor', {}).get('periodType') in ['OT', 'SO']:
                    ot_losses += 1
                else:
                    losses += 1

        return {
            'avg_scored': round(sum(scores_for) / len(scores_for), 1) if scores_for else 0,
            'avg_allowed': round(sum(scores_against) / len(scores_against), 1) if scores_against else 0,
            'games_analyzed': len(recent_games),
            'wins': wins,
            'losses': losses,
            'ot_losses': ot_losses,
            'record': f"{wins}-{losses}-{ot_losses}"
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
    """
    try:
        standings_url = 'https://api-web.nhle.com/v1/standings/now'
        response = requests.get(standings_url, timeout=15)
        response.raise_for_status()
        data = response.json()

        standings = {}
        for team in data.get('standings', []):
            team_name = team['placeName']['default']
            wins = team['wins']
            losses = team['losses']
            ot_losses = team['otLosses']
            points = team['points']
            games_played = team['gamesPlayed']
            record = f"{wins}-{losses}-{ot_losses}"
            standings[team_name] = {
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


def analyze_results(results_text, absences_text, recent_games, team_stats_text, h2h_stats_text, goalie_stats_text, home_away_splits_text, standings_text):
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
    except Exception:
        return "AI analysis skipped: prompt file not found or unreadable."

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=types.Part.from_text(text=prompt_text),
        )
        return response.candidates[0].content.parts[0].text
    except genai.errors.ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e):
            return "AI analysis skipped: Gemini API quota exceeded."
        else:
            raise

# --- New logic for 7am/12pm runs ---
def detect_run_time():
    env_run_time = os.environ.get("NHL_RUN_TIME")
    if env_run_time:
        return env_run_time.lower()
    # Default: auto-detect based on Montreal time
    tz = pytz.timezone("America/Toronto")
    now = datetime.now(tz)
    hour = now.hour
    if 6 <= hour < 12:
        return "7am"
    elif 12 <= hour < 17:
        return "12pm"
    else:
        return "7am"  # fallback

run_time = detect_run_time()
today_str = date.today().isoformat()
predictions_folder = os.path.join("data", "predictions", "nhl")
daily_runs_folder = os.path.join(predictions_folder, "daily_runs")
os.makedirs(predictions_folder, exist_ok=True)
os.makedirs(daily_runs_folder, exist_ok=True)

# Write directly to daily_runs folder for 7am/12pm runs
if run_time == "7am":
    filename = os.path.join(daily_runs_folder, f"nhl_daily_predictions_{today_str}_7am.txt")
elif run_time == "12pm":
    filename = os.path.join(daily_runs_folder, f"nhl_daily_predictions_{today_str}_12pm.txt")
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

        # Get starting goalies
        starting_goalies = get_starting_goalies()

        # Get NHL standings
        standings = get_nhl_standings()

        results_text = ""
        team_stats_text = ""
        h2h_stats_text = ""
        goalie_stats_text = ""
        home_away_splits_text = ""
        standings_text = ""

        for g in matched:
            away_team = g['away']
            home_team = g['home']

            line = (
                f"{away_team} @ {home_team}\n"
                f"Home odds: {g['home_odds']}, Away odds: {g['away_odds']}, O/U: {g['over_under']}\n"
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
                elif 'St.' in full_name and 'Louis' in full_name:
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
            else:
                team_stats_text += "  No stats available\n"

            team_stats_text += f"\n{home_team} (Last 10 Games):\n"
            if home_stats:
                team_stats_text += f"  Record: {home_stats['record']}\n"
                team_stats_text += f"  Avg Goals Scored: {home_stats['avg_scored']}\n"
                team_stats_text += f"  Avg Goals Allowed: {home_stats['avg_allowed']}\n"
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

            # Fetch goalie stats
            away_goalie_info = starting_goalies.get(away_short)
            home_goalie_info = starting_goalies.get(home_short)

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

            # Add standings info for both teams
            away_standing = standings.get(away_short)
            home_standing = standings.get(home_short)

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

        # Print all variables being sent to AI analysis
        print("NHL Matchups and Odds:")
        print(results_text)
        print(absences_text)
        print("\nTeam Stats:")
        print(team_stats_text)
        print("\nHome/Away Splits:")
        print(home_away_splits_text)
        print("\nStandings:")
        print(standings_text)
        print("\nHead-to-Head Stats:")
        print(h2h_stats_text)
        print("\nGoalie Stats:")
        print(goalie_stats_text)
        print("\nRecent Games:")
        print(recent_games)

        if results_text:
            summary = analyze_results(results_text, absences_text, recent_games, team_stats_text, h2h_stats_text, goalie_stats_text, home_away_splits_text, standings_text)
            f.write("\nAI Analysis Summary:\n")
            f.write(summary + "\n")
            print("\nAI Analysis Summary:")
            print(summary)

print(f"Saved daily results to {filename}")
