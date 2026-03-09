import os
import sys
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from google import genai
from data.odds import get_nba_odds, match_nba_odds_to_games
from datetime import date, timedelta, datetime
from data.odds import NBA_TEAM_NAME_MAP
from data.nba_games import get_nba_games_today
import glob
import pytz
import requests

load_dotenv()

# ESPN NBA team ID mapping for API calls
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

def get_run_time_suffix():
    """Determine if this is 7am or 12pm run based on environment variable or current time in Montreal timezone."""
    run_time = os.getenv("NBA_RUN_TIME")
    if run_time:
        return run_time  # Should be "7am" or "12pm"

    # Use Montreal time (America/Toronto)
    tz = pytz.timezone("America/Toronto")
    now = datetime.now(tz)
    current_hour = now.hour
    # 7am run: 6:00–7:59
    if 6 <= current_hour < 8:
        return "7am"
    # 12pm run: 11:00–12:59
    elif 11 <= current_hour < 13:
        return "12pm"
    else:
        # Default based on which is closer
        if current_hour < 10:
            return "7am"
        else:
            return "12pm"

def get_nba_team_last_games(team_name, last_n_games=10):
    """
    Get last N games for an NBA team from ESPN API.

    Returns:
        dict with avg_scored, avg_allowed, games_analyzed, wins, losses, record
    """
    try:
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
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)

            if not home or not away:
                continue

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
            'record': f"{wins}-{losses}"
        }

    except Exception as e:
        print(f"⚠️ Error fetching NBA team stats for {team_name}: {e}")
        return None

def get_head_to_head_stats(team1_name, team2_name):
    """
    Get head-to-head stats between two NBA teams for the current season.

    Returns dict with:
    - team1_wins: Number of wins for team1
    - team2_wins: Number of wins for team2
    - games_played: Total games between teams
    - last_results: List of recent game results
    """
    try:
        team1_id = NBA_TEAM_ID_MAP.get(team1_name)
        team2_id = NBA_TEAM_ID_MAP.get(team2_name)

        if not team1_id or not team2_id:
            return None

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

            competitors = competition.get('competitors', [])
            team_ids = [c.get('team', {}).get('id') for c in competitors]

            if team2_id in team_ids:
                h2h_games.append(event)

        if not h2h_games:
            return None

        team1_wins = 0
        team2_wins = 0
        last_results = []

        for event in h2h_games[:5]:  # Last 5 games
            competition = event.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])

            home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
            away = next((c for c in competitors if c.get('homeAway') == 'away'), {})

            home_id = home.get('team', {}).get('id')
            home_score = int(float(home.get('score', {}).get('value', 0)))
            away_score = int(float(away.get('score', {}).get('value', 0)))

            if home_score > away_score:
                winner_id = home_id
            else:
                winner_id = away.get('team', {}).get('id')

            home_abbrev = home.get('team', {}).get('abbreviation', 'HOME')
            away_abbrev = away.get('team', {}).get('abbreviation', 'AWAY')

            if winner_id == team1_id:
                team1_wins += 1
            else:
                team2_wins += 1

            last_results.append(f"{away_abbrev} {away_score} @ {home_abbrev} {home_score}")

        return {
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'games_played': len(h2h_games),
            'last_results': last_results
        }

    except Exception as e:
        print(f"⚠️ Error fetching H2H stats for {team1_name} vs {team2_name}: {e}")
        return None

def get_nba_team_home_away_splits(team_name):
    """
    Get home/away record splits for an NBA team.

    Returns dict with home_record, away_record, home_win_pct, away_win_pct
    """
    try:
        team_id = NBA_TEAM_ID_MAP.get(team_name)
        if not team_id:
            return None

        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        home_wins = 0
        home_losses = 0
        away_wins = 0
        away_losses = 0

        for event in data.get('events', []):
            status = event.get('status', {}).get('type', {}).get('completed', False)
            if not status:
                continue

            comp = event['competitions'][0]
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)

            if not home or not away:
                continue

            is_home_game = home['team']['displayName'] == team_name
            is_away_game = away['team']['displayName'] == team_name

            if is_home_game:
                if home.get('winner', False):
                    home_wins += 1
                else:
                    home_losses += 1
            elif is_away_game:
                if away.get('winner', False):
                    away_wins += 1
                else:
                    away_losses += 1

        return {
            'home_record': f"{home_wins}-{home_losses}",
            'away_record': f"{away_wins}-{away_losses}",
            'home_win_pct': round(home_wins / (home_wins + home_losses), 3) if (home_wins + home_losses) > 0 else 0,
            'away_win_pct': round(away_wins / (away_wins + away_losses), 3) if (away_wins + away_losses) > 0 else 0
        }

    except Exception as e:
        print(f"⚠️ Error fetching home/away splits for {team_name}: {e}")
        return None

def get_nba_standings():
    """
    Fetch current NBA standings.

    Returns dict mapping team names to their record data (wins, losses, win_pct)
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

                wins = None
                losses = None
                for stat in entry['stats']:
                    if stat['name'] == 'wins':
                        wins = int(stat['value'])
                    elif stat['name'] == 'losses':
                        losses = int(stat['value'])

                if wins is not None and losses is not None:
                    games_played = wins + losses
                    win_pct = round(wins / games_played, 3) if games_played > 0 else 0

                    standings[team_name] = {
                        'record': f"{wins}-{losses}",
                        'wins': wins,
                        'losses': losses,
                        'games_played': games_played,
                        'win_pct': win_pct
                    }

        return standings
    except Exception as e:
        print(f"⚠️ Error fetching NBA standings: {e}")
        return {}

def analyze_results(results_text, team_stats_text, h2h_stats_text, home_away_splits_text, standings_text, recent_games):
    api_key = os.environ["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)

    # Read and concatenate all historical NBA results files (not predictions)
    hist_dir = os.path.join("data", "bot_results", "nba")
    hist_files = sorted(glob.glob(os.path.join(hist_dir, "nba_daily_results_*.txt")))
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

    # Strictly read external prompt; no fallback
    prompt_path = os.path.join("prompts", "nba_prompt.txt")
    today_str = date.today().isoformat()
    try:
        with open(prompt_path, "r", encoding="utf-8") as pf:
            prompt_text = pf.read()
            prompt_text = prompt_text.replace("{{RESULTS_TEXT}}", results_text)
            prompt_text = prompt_text.replace("{{TODAY_DATE}}", today_str)
            prompt_text = prompt_text.replace("{{HISTORICAL_RESULTS}}", historical_results)
            prompt_text = prompt_text.replace("{{RECENT_RESULTS}}", recent_results)
            prompt_text = prompt_text.replace("{{RECENT_GAMES}}", recent_games)
            prompt_text = prompt_text.replace("{{TEAM_STATS}}", team_stats_text)
            prompt_text = prompt_text.replace("{{H2H_STATS}}", h2h_stats_text)
            prompt_text = prompt_text.replace("{{HOME_AWAY_SPLITS}}", home_away_splits_text)
            prompt_text = prompt_text.replace("{{STANDINGS}}", standings_text)
    except Exception as e:
        # If prompt file is missing or unreadable, skip AI analysis
        return "AI analysis skipped: prompt file not found or unreadable."

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt_text,
        )
        return response.text.strip()
    except genai.errors.ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e):
            return "AI analysis skipped: Gemini API quota exceeded."
        else:
            raise

today_str = date.today().isoformat()
predictions_folder = os.path.join("data", "predictions", "nba")
daily_runs_folder = os.path.join(predictions_folder, "daily_runs")
os.makedirs(predictions_folder, exist_ok=True)
os.makedirs(daily_runs_folder, exist_ok=True)

# Determine which run this is
run_time = get_run_time_suffix()
# Write directly to daily_runs folder for 7am/12pm runs
if run_time == "7am":
    filename = os.path.join(daily_runs_folder, f"nba_daily_predictions_{today_str}_7am.txt")
elif run_time == "12pm":
    filename = os.path.join(daily_runs_folder, f"nba_daily_predictions_{today_str}_12pm.txt")
else:
    # Fallback goes to main folder
    filename = os.path.join(predictions_folder, f"nba_daily_predictions_{today_str}_{run_time}.txt")

# Check if file already exists - skip if it does
if os.path.exists(filename):
    print(f"⚠️  Predictions file already exists: {filename}")
    print("Skipping prediction generation to avoid overwriting existing file.")
    exit(0)

# Fetch and save games data
games = get_nba_games_today()

# Save raw games data to file
games_data_folder = os.path.join("data", "games", "nba")
os.makedirs(games_data_folder, exist_ok=True)
games_data_file = os.path.join(games_data_folder, f"nba_games_{today_str}.txt")

with open(games_data_file, "w") as gf:
    gf.write(f"Date: {today_str}\n\n")
    if games:
        for game in games:
            gf.write(f"{game['away']} @ {game['home']}\n")
    else:
        gf.write("No games today\n")

print(f"✅ Saved raw games data to: {games_data_file}")

odds = get_nba_odds()

# Optional: allow passing injury notes via environment or external pre-processing
extra_injury_notes = os.getenv("NBA_INJURY_NOTES")

# Read last 7 days of games from saved files
games_dir = os.path.join("data", "games", "nba")
games_files = sorted(glob.glob(os.path.join(games_dir, "nba_games_*.txt")))
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

# Match structured odds to games
matched = match_nba_odds_to_games(games, odds, NBA_TEAM_NAME_MAP)
predictions_text = ""

# Collect team stats, H2H stats, home/away splits, and standings
team_stats_text = ""
h2h_stats_text = ""
home_away_splits_text = ""

print("🔍 Collecting team statistics...")
standings = get_nba_standings()
standings_text = "CURRENT NBA STANDINGS:\n\n"

if standings:
    for team_name, data in standings.items():
        standings_text += f"{team_name}: {data['record']} (Win%: {data['win_pct']:.3f})\n"
else:
    standings_text += "No standings data available\n"

with open(filename, "w") as f:
    f.write(f"Date: {today_str}\n\n")
    if not matched:
        f.write("No NBA games today or no odds available\n")
        print("No NBA games today or no odds available")
    else:
        print("NBA Matchups and Odds:")
        for g in matched:
            home_team = g['home']
            away_team = g['away']

            # Get team stats (last 10 games)
            home_stats = get_nba_team_last_games(home_team)
            away_stats = get_nba_team_last_games(away_team)

            if home_stats:
                team_stats_text += f"\n{home_team} (Last 10 Games):\n"
                team_stats_text += f"  Record: {home_stats['record']}\n"
                team_stats_text += f"  Avg Scored: {home_stats['avg_scored']} pts\n"
                team_stats_text += f"  Avg Allowed: {home_stats['avg_allowed']} pts\n"

            if away_stats:
                team_stats_text += f"\n{away_team} (Last 10 Games):\n"
                team_stats_text += f"  Record: {away_stats['record']}\n"
                team_stats_text += f"  Avg Scored: {away_stats['avg_scored']} pts\n"
                team_stats_text += f"  Avg Allowed: {away_stats['avg_allowed']} pts\n"

            # Get H2H stats
            h2h = get_head_to_head_stats(away_team, home_team)
            if h2h and h2h['games_played'] > 0:
                h2h_stats_text += f"\n{away_team} vs {home_team} (Season Series):\n"
                h2h_stats_text += f"  Record: {away_team} {h2h['team1_wins']}-{h2h['team2_wins']} {home_team}\n"
                h2h_stats_text += f"  Recent Results: {', '.join(h2h['last_results'])}\n"

            # Get home/away splits
            home_splits = get_nba_team_home_away_splits(home_team)
            away_splits = get_nba_team_home_away_splits(away_team)

            if home_splits:
                home_away_splits_text += f"\n{home_team}:\n"
                home_away_splits_text += f"  Home Record: {home_splits['home_record']} (Win%: {home_splits['home_win_pct']:.3f})\n"
                home_away_splits_text += f"  Away Record: {home_splits['away_record']} (Win%: {home_splits['away_win_pct']:.3f})\n"

            if away_splits:
                home_away_splits_text += f"\n{away_team}:\n"
                home_away_splits_text += f"  Home Record: {away_splits['home_record']} (Win%: {away_splits['home_win_pct']:.3f})\n"
                home_away_splits_text += f"  Away Record: {away_splits['away_record']} (Win%: {away_splits['away_win_pct']:.3f})\n"

            # Headline summary per game (write to file + include in predictions_text)
            line = (
                f"{g['home']} vs {g['away']}\n"
                f"Home odds: {g.get('home_odds')}, Away odds: {g.get('away_odds')}, "
                f"O/U: {g.get('over_under')}\n"
                # Added spreads summary in the headline print
                f"Spreads: Home {g.get('spread_home_points')} ({g.get('spread_home_price')}), "
                f"Away {g.get('spread_away_points')} ({g.get('spread_away_price')})\n"
                "------\n"
            )
            print(line, end="")
            f.write(line)
            predictions_text += line

            # Verbose per-bookmaker markets ONLY for predictions_text (skip writing to file)
            bm_list = g.get('bookmakers_odds', [])
            if bm_list:
                predictions_text += "Bookmakers snapshot:\n"
                for bm in bm_list:
                    title = bm.get('title') or bm.get('key') or 'Unknown Bookmaker'
                    predictions_text += f"  {title}\n"
                    for m in bm.get('markets', []):
                        mkey = m.get('key', 'unknown')
                        outcomes = m.get('outcomes', [])
                        out_strs = []
                        for o in outcomes:
                            if isinstance(o, dict):
                                name = o.get('name', 'N/A')
                                price = o.get('price', 'N/A')
                                point = o.get('point')
                                if point is not None:
                                    out_strs.append(f"{name} @ {price} (point {point})")
                                else:
                                    out_strs.append(f"{name} @ {price}")
                            else:
                                out_strs.append(str(o))
                        predictions_text += f"    {mkey}: " + ", ".join(out_strs) + "\n"
                predictions_text += "------\n"

        # Append any external injury notes to give the model explicit names if provided
        if extra_injury_notes:
            predictions_text += "\nInjury Notes (user-supplied):\n" + extra_injury_notes + "\n"

        if predictions_text:
            summary = analyze_results(predictions_text, team_stats_text, h2h_stats_text,
                                     home_away_splits_text, standings_text, recent_games)
            f.write("\nAI Analysis Summary:\n")
            f.write(summary + "\n")
            print("\nAI Analysis Summary:")
            print(summary)

print(f"Saved NBA daily predictions to {filename}")
