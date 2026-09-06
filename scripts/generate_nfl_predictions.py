import os
import sys
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from google import genai
from data.odds import get_nfl_odds, match_nfl_odds_to_games
from datetime import date, timedelta, datetime
from data.nfl_games import get_nfl_games_this_week
import glob
import pytz
import requests

load_dotenv()

# ESPN NFL team ID mapping
NFL_TEAM_ID_MAP = {
    'Arizona Cardinals': '22',
    'Atlanta Falcons': '1',
    'Baltimore Ravens': '33',
    'Buffalo Bills': '2',
    'Carolina Panthers': '29',
    'Chicago Bears': '3',
    'Cincinnati Bengals': '4',
    'Cleveland Browns': '5',
    'Dallas Cowboys': '6',
    'Denver Broncos': '7',
    'Detroit Lions': '8',
    'Green Bay Packers': '9',
    'Houston Texans': '34',
    'Indianapolis Colts': '11',
    'Jacksonville Jaguars': '30',
    'Kansas City Chiefs': '12',
    'Las Vegas Raiders': '13',
    'Los Angeles Chargers': '24',
    'Los Angeles Rams': '14',
    'Miami Dolphins': '15',
    'Minnesota Vikings': '16',
    'New England Patriots': '17',
    'New Orleans Saints': '18',
    'New York Giants': '19',
    'New York Jets': '20',
    'Philadelphia Eagles': '21',
    'Pittsburgh Steelers': '23',
    'San Francisco 49ers': '25',
    'Seattle Seahawks': '26',
    'Tampa Bay Buccaneers': '27',
    'Tennessee Titans': '10',
    'Washington Commanders': '28',
}

MIN_ODDS = 1.60
MAX_ODDS = 2.20

def get_nfl_team_last_games(team_name, last_n_games=5):
    """Get last N games for an NFL team from ESPN API."""
    try:
        team_id = NFL_TEAM_ID_MAP.get(team_name)
        if not team_id:
            return None

        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/schedule'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        all_completed = [e for e in data.get('events', [])
                         if e['competitions'][0]['status']['type']['completed']]
        completed_events = all_completed[-last_n_games:] if len(all_completed) >= last_n_games else all_completed

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

        return {
            'avg_scored': round(sum(scores_for) / len(scores_for), 2) if scores_for else 0,
            'avg_allowed': round(sum(scores_against) / len(scores_against), 2) if scores_against else 0,
            'games_analyzed': len(completed_events),
            'wins': wins,
            'losses': losses,
            'record': f"{wins}-{losses}"
        }

    except Exception as e:
        print(f"⚠️ Error fetching NFL team stats for {team_name}: {e}")
        return None


def get_head_to_head_stats(team1_name, team2_name):
    """Get recent head-to-head stats between two NFL teams."""
    try:
        team1_id = NFL_TEAM_ID_MAP.get(team1_name)
        team2_id = NFL_TEAM_ID_MAP.get(team2_name)

        if not team1_id or not team2_id:
            return None

        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team1_id}/schedule'
        response = requests.get(url, timeout=10)
        data = response.json()

        h2h_games = []
        for event in data.get('events', []):
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

        for event in h2h_games[:5]:
            competition = event.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])
            home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
            away = next((c for c in competitors if c.get('homeAway') == 'away'), {})

            home_id = home.get('team', {}).get('id')
            home_score = int(float(home.get('score', {}).get('value', 0)))
            away_score = int(float(away.get('score', {}).get('value', 0)))

            winner_id = home_id if home_score > away_score else away.get('team', {}).get('id')
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


def get_nfl_team_home_away_splits(team_name):
    """Get home/away record splits for an NFL team."""
    try:
        team_id = NFL_TEAM_ID_MAP.get(team_name)
        if not team_id:
            return None

        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/schedule'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        home_wins = home_losses = away_wins = away_losses = 0

        for event in data.get('events', []):
            comp = event.get('competitions', [{}])[0]
            status = comp.get('status', {}).get('type', {}).get('completed', False)
            if not status:
                continue

            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), None)
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), None)

            if not home or not away:
                continue

            if home['team']['id'] == team_id:
                if home.get('winner', False):
                    home_wins += 1
                else:
                    home_losses += 1
            elif away['team']['id'] == team_id:
                if away.get('winner', False):
                    away_wins += 1
                else:
                    away_losses += 1

        return {
            'home_record': f"{home_wins}-{home_losses}",
            'away_record': f"{away_wins}-{away_losses}",
            'home_win_pct': round(home_wins / (home_wins + home_losses), 3) if (home_wins + home_losses) > 0 else 0,
            'away_win_pct': round(away_wins / (away_wins + away_losses), 3) if (away_wins + away_losses) > 0 else 0,
        }

    except Exception as e:
        print(f"⚠️ Error fetching home/away splits for {team_name}: {e}")
        return None


def get_nfl_standings():
    """Fetch current NFL standings."""
    try:
        url = 'https://site.api.espn.com/apis/v2/sports/football/nfl/standings'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        standings = {}
        for conference in data.get('children', []):
            for division in conference.get('children', []):
                for entry in division.get('standings', {}).get('entries', []):
                    team_name = entry['team']['displayName']
                    wins = losses = None
                    for stat in entry.get('stats', []):
                        if stat['name'] == 'wins':
                            wins = int(stat['value'])
                        elif stat['name'] == 'losses':
                            losses = int(stat['value'])
                    if wins is not None and losses is not None:
                        gp = wins + losses
                        standings[team_name] = {
                            'record': f"{wins}-{losses}",
                            'wins': wins,
                            'losses': losses,
                            'games_played': gp,
                            'win_pct': round(wins / gp, 3) if gp > 0 else 0,
                        }

        return standings
    except Exception as e:
        print(f"⚠️ Error fetching NFL standings: {e}")
        return {}


def filter_low_odds_picks(text):
    """Remove recommended play blocks with odds outside [1.60, 2.20]."""
    import re
    lines = text.splitlines()
    result = []
    skip_block = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('**') and ('@' in stripped) and 'BET OF THE WEEK' not in stripped.upper():
            odds_match = re.search(r'@\s*([\d.]+)', stripped)
            if odds_match:
                odds = float(odds_match.group(1))
                if odds < MIN_ODDS or odds > MAX_ODDS:
                    skip_block = True
                    continue
                else:
                    skip_block = False
            else:
                skip_block = False

        if skip_block:
            if stripped.startswith('**') and ('@' in stripped or stripped == '---'):
                skip_block = False
                result.append(line)
            continue

        result.append(line)

    return '\n'.join(result)


def analyze_results(results_text, team_stats_text, h2h_stats_text, home_away_splits_text, standings_text, recent_games):
    import time
    api_key = os.environ["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)

    hist_dir = os.path.join("data", "bot_results", "nfl")
    hist_files = sorted(glob.glob(os.path.join(hist_dir, "nfl_weekly_results_*.txt")))
    historical_results = ""
    for hf in hist_files:
        try:
            with open(hf, "r", encoding="utf-8") as hfile:
                historical_results += f"\n---\n{os.path.basename(hf)}\n" + hfile.read()
        except Exception:
            continue

    last_10_files = hist_files[-10:] if len(hist_files) >= 10 else hist_files
    recent_results = ""
    for rf in last_10_files:
        try:
            with open(rf, "r", encoding="utf-8") as rfile:
                recent_results += f"\n---\n{os.path.basename(rf)}\n" + rfile.read()
        except Exception:
            continue

    prompt_path = os.path.join("prompts", "nfl_prompt.txt")
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
            prompt_text = prompt_text.replace("{{PLAYOFF_SERIES_STATUS}}", "")
    except Exception as e:
        return "AI analysis skipped: prompt file not found or unreadable."

    models_to_try = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.5-flash-lite",
    ]
    retry_waits = [30, 60]

    for model in models_to_try:
        max_retries = len(retry_waits) + 1
        for attempt in range(max_retries):
            try:
                print(f"🤖 Trying {model}...")
                response = client.models.generate_content(model=model, contents=prompt_text)
                return response.text.strip()
            except genai.errors.ServerError as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = retry_waits[attempt]
                        print(f"⚠️ {model} 503 error. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                        import time as _time; _time.sleep(wait_time)
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

    print("❌ All Gemini models unavailable. Cancelling workflow.")
    sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

today_str = date.today().isoformat()
predictions_folder = os.path.join("data", "predictions", "nfl")
daily_runs_folder = os.path.join(predictions_folder, "daily_runs")
os.makedirs(predictions_folder, exist_ok=True)
os.makedirs(daily_runs_folder, exist_ok=True)

filename = os.path.join(predictions_folder, f"nfl_weekly_predictions_{today_str}.txt")

if os.path.exists(filename):
    print(f"⚠️  Predictions file already exists: {filename}")
    print("Skipping prediction generation to avoid overwriting existing file.")
    exit(0)

# Fetch games for the week
games = get_nfl_games_this_week()

# Save raw games data
games_data_folder = os.path.join("data", "games", "nfl")
os.makedirs(games_data_folder, exist_ok=True)
games_data_file = os.path.join(games_data_folder, f"nfl_games_{today_str}.txt")

with open(games_data_file, "w") as gf:
    gf.write(f"Date: {today_str}\n\n")
    if games:
        for game in games:
            gf.write(f"{game['away']} @ {game['home']}\n")
    else:
        gf.write("No NFL games this week\n")

print(f"✅ Saved raw games data to: {games_data_file}")

odds = get_nfl_odds()
extra_injury_notes = os.getenv("NFL_INJURY_NOTES")

# Read last 4 weeks of saved games files for schedule context
games_dir = os.path.join("data", "games", "nfl")
games_files = sorted(glob.glob(os.path.join(games_dir, "nfl_games_*.txt")))
last_4_files = games_files[-4:] if len(games_files) >= 4 else games_files
recent_games = ""
for gf_path in last_4_files:
    try:
        with open(gf_path, "r", encoding="utf-8") as gfile:
            recent_games += f"\n---\n{os.path.basename(gf_path)}\n" + gfile.read()
    except Exception:
        continue

if not recent_games:
    recent_games = "No recent games data available"

# Match odds to games (use full team names from odds data directly)
matched = match_nfl_odds_to_games(games, odds)
predictions_text = ""
team_stats_text = ""
h2h_stats_text = ""
home_away_splits_text = ""

print("🔍 Collecting team statistics...")
standings = get_nfl_standings()
standings_text = "CURRENT NFL STANDINGS:\n\n"
if standings:
    for team_name, data in standings.items():
        standings_text += f"{team_name}: {data['record']} (Win%: {data['win_pct']:.3f})\n"
else:
    standings_text += "No standings data available\n"

with open(filename, "w") as f:
    f.write(f"Date: {today_str}\n\n")
    if not matched:
        # If no matched games, use raw odds data directly (NFL odds don't need game matching)
        if odds:
            print("Using raw odds data (no game list to match against)...")
            for game in odds:
                home_team = game.get('home_team', '')
                away_team = game.get('away_team', '')
                if not home_team or not away_team:
                    continue

                home_odds = away_odds = over_under = over_price = under_price = None
                spread_home_points = spread_away_points = spread_home_price = spread_away_price = None

                for bm in game.get('bookmakers', []):
                    for market in bm.get('markets', []):
                        if market['key'] == 'h2h' and home_odds is None:
                            for outcome in market['outcomes']:
                                if outcome['name'] == home_team:
                                    home_odds = outcome['price']
                                elif outcome['name'] == away_team:
                                    away_odds = outcome['price']
                        elif market['key'] == 'totals' and over_under is None:
                            for outcome in market['outcomes']:
                                if outcome['name'] == 'Over':
                                    over_under = outcome.get('point')
                                    over_price = outcome['price']
                                elif outcome['name'] == 'Under':
                                    under_price = outcome['price']
                        elif market['key'] == 'spreads' and spread_home_points is None:
                            for outcome in market['outcomes']:
                                if outcome['name'] == home_team:
                                    spread_home_points = outcome.get('point')
                                    spread_home_price = outcome['price']
                                elif outcome['name'] == away_team:
                                    spread_away_points = outcome.get('point')
                                    spread_away_price = outcome['price']

                ou_str = f"{over_under} (Over: {over_price} / Under: {under_price})" if over_under and over_price else str(over_under)
                line = (
                    f"{home_team} vs {away_team}\n"
                    f"{home_team} ML (Home): {home_odds}, {away_team} ML (Away): {away_odds}, "
                    f"O/U: {ou_str}\n"
                    f"Spreads: Home {spread_home_points} ({spread_home_price}), "
                    f"Away {spread_away_points} ({spread_away_price})\n"
                    "------\n"
                )
                print(line, end="")
                f.write(line)
                predictions_text += line

                # Get stats for both teams
                home_stats = get_nfl_team_last_games(home_team)
                away_stats = get_nfl_team_last_games(away_team)
                if home_stats:
                    team_stats_text += f"\n{home_team} (Last 5 Games):\n"
                    team_stats_text += f"  Record: {home_stats['record']}\n"
                    team_stats_text += f"  Avg Scored: {home_stats['avg_scored']} pts\n"
                    team_stats_text += f"  Avg Allowed: {home_stats['avg_allowed']} pts\n"
                if away_stats:
                    team_stats_text += f"\n{away_team} (Last 5 Games):\n"
                    team_stats_text += f"  Record: {away_stats['record']}\n"
                    team_stats_text += f"  Avg Scored: {away_stats['avg_scored']} pts\n"
                    team_stats_text += f"  Avg Allowed: {away_stats['avg_allowed']} pts\n"

                h2h = get_head_to_head_stats(away_team, home_team)
                if h2h and h2h['games_played'] > 0:
                    h2h_stats_text += f"\n{away_team} vs {home_team} (H2H):\n"
                    h2h_stats_text += f"  Record: {away_team} {h2h['team1_wins']}-{h2h['team2_wins']} {home_team}\n"
                    h2h_stats_text += f"  Recent Results: {', '.join(h2h['last_results'])}\n"

                home_splits = get_nfl_team_home_away_splits(home_team)
                away_splits = get_nfl_team_home_away_splits(away_team)
                if home_splits:
                    home_away_splits_text += f"\n{home_team}:\n"
                    home_away_splits_text += f"  Home: {home_splits['home_record']} (Win%: {home_splits['home_win_pct']:.3f})\n"
                    home_away_splits_text += f"  Away: {home_splits['away_record']} (Win%: {home_splits['away_win_pct']:.3f})\n"
                if away_splits:
                    home_away_splits_text += f"\n{away_team}:\n"
                    home_away_splits_text += f"  Home: {away_splits['home_record']} (Win%: {away_splits['home_win_pct']:.3f})\n"
                    home_away_splits_text += f"  Away: {away_splits['away_record']} (Win%: {away_splits['away_win_pct']:.3f})\n"
        else:
            f.write("No NFL games this week or no odds available\n")
            print("No NFL games this week or no odds available")
    else:
        print("NFL Matchups and Odds:")
        for g in matched:
            home_team = g['home']
            away_team = g['away']

            home_stats = get_nfl_team_last_games(home_team)
            away_stats = get_nfl_team_last_games(away_team)

            if home_stats:
                team_stats_text += f"\n{home_team} (Last 5 Games):\n"
                team_stats_text += f"  Record: {home_stats['record']}\n"
                team_stats_text += f"  Avg Scored: {home_stats['avg_scored']} pts\n"
                team_stats_text += f"  Avg Allowed: {home_stats['avg_allowed']} pts\n"

            if away_stats:
                team_stats_text += f"\n{away_team} (Last 5 Games):\n"
                team_stats_text += f"  Record: {away_stats['record']}\n"
                team_stats_text += f"  Avg Scored: {away_stats['avg_scored']} pts\n"
                team_stats_text += f"  Avg Allowed: {away_stats['avg_allowed']} pts\n"

            h2h = get_head_to_head_stats(away_team, home_team)
            if h2h and h2h['games_played'] > 0:
                h2h_stats_text += f"\n{away_team} vs {home_team} (H2H):\n"
                h2h_stats_text += f"  Record: {away_team} {h2h['team1_wins']}-{h2h['team2_wins']} {home_team}\n"
                h2h_stats_text += f"  Recent Results: {', '.join(h2h['last_results'])}\n"

            home_splits = get_nfl_team_home_away_splits(home_team)
            away_splits = get_nfl_team_home_away_splits(away_team)

            if home_splits:
                home_away_splits_text += f"\n{home_team}:\n"
                home_away_splits_text += f"  Home: {home_splits['home_record']} (Win%: {home_splits['home_win_pct']:.3f})\n"
                home_away_splits_text += f"  Away: {home_splits['away_record']} (Win%: {home_splits['away_win_pct']:.3f})\n"
            if away_splits:
                home_away_splits_text += f"\n{away_team}:\n"
                home_away_splits_text += f"  Home: {away_splits['home_record']} (Win%: {away_splits['home_win_pct']:.3f})\n"
                home_away_splits_text += f"  Away: {away_splits['away_record']} (Win%: {away_splits['away_win_pct']:.3f})\n"

            ou = g.get('over_under')
            over_p = g.get('over_price')
            under_p = g.get('under_price')
            ou_str = f"{ou} (Over: {over_p} / Under: {under_p})" if ou and over_p else str(ou)

            line = (
                f"{g['home']} vs {g['away']}\n"
                f"{g['home']} ML (Home): {g.get('home_odds')}, {g['away']} ML (Away): {g.get('away_odds')}, "
                f"O/U: {ou_str}\n"
                f"Spreads: Home {g.get('spread_home_points')} ({g.get('spread_home_price')}), "
                f"Away {g.get('spread_away_points')} ({g.get('spread_away_price')})\n"
                "------\n"
            )
            print(line, end="")
            f.write(line)
            predictions_text += line

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

    if extra_injury_notes:
        predictions_text += "\nInjury Notes (user-supplied):\n" + extra_injury_notes + "\n"

    if predictions_text:
        print("\n--- SENDING TO AI ANALYSIS ---")
        print("results_text:\n", predictions_text)
        print("team_stats_text:\n", team_stats_text)
        print("standings_text:\n", standings_text)
        print("-----------------------------\n")

        summary = analyze_results(predictions_text, team_stats_text, h2h_stats_text,
                                  home_away_splits_text, standings_text, recent_games)
        summary = filter_low_odds_picks(summary)
        f.write("\nAI Analysis Summary:\n")
        f.write(summary + "\n")
        print("\nAI Analysis Summary:")
        print(summary)

print(f"✅ Saved NFL weekly predictions to {filename}")
