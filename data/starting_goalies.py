import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import pytz


# Mapping from NHL.com lineup page team nicknames to full team names (matching odds API format)
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


# Cache file for goalie stats to handle API failures
GOALIE_CACHE_FILE = "data/goalie_stats_cache.json"

# Load cache at startup
GOALIE_STATS_CACHE = {}
if os.path.exists(GOALIE_CACHE_FILE):
    try:
        with open(GOALIE_CACHE_FILE, 'r') as f:
            GOALIE_STATS_CACHE = json.load(f)
    except:
        GOALIE_STATS_CACHE = {}


def get_goalie_stats(goalie_name):
    """
    Get goalie statistics from NHL API.

    Returns dict with:
    - record: Season W-L-OTL
    - gaa: Season goals against average
    - sv_pct: Season save percentage
    - last_5_record: Last 5 starts W-L
    - last_5_gaa: Last 5 starts GAA
    - last_5_sv_pct: Last 5 starts SV%
    """
    try:
        # Split name and search by last name (more reliable)
        name_parts = goalie_name.split()
        if len(name_parts) < 2:
            return None

        last_name = name_parts[-1]
        first_name = name_parts[0]

        # Try multiple search strategies
        goalie_id = None

        # Strategy 1: Search by last name only (larger limit)
        search_url = f'https://search.d3.nhle.com/api/v1/search/player?culture=en-us&limit=50&q={last_name}'
        try:
            response = requests.get(search_url, timeout=3)
            response.raise_for_status()
            results = response.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            print(f"⚠️ API timeout/error searching for {goalie_name}: {e}")
            results = []

        if results:
            # First pass: look for active goalie with exact name match
            for result in results:
                if (result.get('positionCode') == 'G' and
                    result.get('name', '').lower() == goalie_name.lower()):
                    goalie_id = result['playerId']
                    break

            # Second pass: look for active goalie with matching first and last name
            if not goalie_id:
                for result in results:
                    if (result.get('positionCode') == 'G' and
                        result.get('active', False) and
                        result.get('name', '').split()[-1].lower() == last_name.lower() and
                        result.get('name', '').split()[0].lower() == first_name.lower()):
                        goalie_id = result['playerId']
                        break

            # Third pass: look for any goalie with matching first name (last name already matched in search)
            if not goalie_id:
                for result in results:
                    if (result.get('positionCode') == 'G' and
                        result.get('name', '').split()[0].lower() == first_name.lower()):
                        goalie_id = result['playerId']
                        break

            # Fourth pass: fallback to first active goalie
            if not goalie_id:
                for result in results:
                    if result.get('positionCode') == 'G' and result.get('active', False):
                        goalie_id = result['playerId']
                        break

            # Fifth pass: fallback to any goalie
            if not goalie_id:
                for result in results:
                    if result.get('positionCode') == 'G':
                        goalie_id = result['playerId']
                        break

        # Strategy 2: Try searching by full name if first strategy didn't work
        if not goalie_id:
            search_url = f'https://search.d3.nhle.com/api/v1/search/player?culture=en-us&limit=50&q={goalie_name}'
            try:
                response = requests.get(search_url, timeout=3)
                response.raise_for_status()
                results = response.json()

                if results:
                    for result in results:
                        if result.get('positionCode') == 'G' and result.get('active', False):
                            goalie_id = result['playerId']
                            break
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
                print(f"⚠️ API timeout/error in strategy 2 for {goalie_name}: {e}")

        if not goalie_id:
            print(f"⚠️ Could not find {goalie_name} in NHL API")
            return None

        # Get current season
        current_year = datetime.now(ZoneInfo('America/Toronto')).year
        current_month = datetime.now(ZoneInfo('America/Toronto')).month
        # NHL season spans two years, starts in October
        if current_month >= 10:
            season = f"{current_year}{current_year+1}"
        else:
            season = f"{current_year-1}{current_year}"

        # Check cache first
        if goalie_name in GOALIE_STATS_CACHE:
            cached_stats = GOALIE_STATS_CACHE[goalie_name]
            # Validate cache (check if playerId matches)
            if cached_stats.get('playerId') == goalie_id:
                print(f"✅ Using cached stats for {goalie_name}")
                return cached_stats

        # Get player stats
        stats_url = f'https://api-web.nhle.com/v1/player/{goalie_id}/landing'
        try:
            response = requests.get(stats_url, timeout=3)
            response.raise_for_status()
            data = response.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            print(f"⚠️ Could not fetch stats for {goalie_name}: {e}")
            return None

        # Get season stats from featuredStats
        season_stats = data.get('featuredStats', {}).get('regularSeason', {}).get('subSeason', {})

        if not season_stats:
            print(f"⚠️ No season stats available for {goalie_name}")
            return None

        wins = season_stats.get('wins', 0)
        losses = season_stats.get('losses', 0)
        ot_losses = season_stats.get('otLosses', 0)
        gaa = season_stats.get('goalsAgainstAvg', 0)
        sv_pct = season_stats.get('savePctg', 0)

        # Get last 5 game logs
        gamelog_url = f'https://api-web.nhle.com/v1/player/{goalie_id}/game-log/{season}/2'
        try:
            response = requests.get(gamelog_url, timeout=3)
            response.raise_for_status()
            gamelog_data = response.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            print(f"⚠️ Could not fetch game logs for {goalie_name}: {e}")
            gamelog_data = {}

        games = gamelog_data.get('gameLog', [])[:5]  # Last 5 games

        last_5_wins = 0
        last_5_losses = 0
        last_5_ot_losses = 0
        last_5_goals_against = []
        last_5_shots_against = []

        for game in games:
            # Only count games where goalie started
            if game.get('gamesStarted', 0) > 0:
                decision = game.get('decision', '')
                if decision == 'W':
                    last_5_wins += 1
                elif decision == 'O':
                    last_5_ot_losses += 1
                elif decision == 'L':
                    last_5_losses += 1

                # Calculate GAA and SV% for last 5
                goals_against = game.get('goalsAgainst', 0)
                shots_against = game.get('shotsAgainst', 0)

                last_5_goals_against.append(goals_against)
                last_5_shots_against.append(shots_against)

        # Calculate last 5 averages
        if last_5_goals_against:
            last_5_gaa = sum(last_5_goals_against) / len(last_5_goals_against)
        else:
            last_5_gaa = 0

        if sum(last_5_shots_against) > 0:
            total_saves = sum(last_5_shots_against) - sum(last_5_goals_against)
            last_5_sv_pct = total_saves / sum(last_5_shots_against)
        else:
            last_5_sv_pct = 0

        # Cache the stats
        cached_stats = {
            'playerId': goalie_id,
            'record': f"{wins}-{losses}-{ot_losses}",
            'gaa': round(gaa, 2),
            'sv_pct': round(sv_pct, 3),
            'last_5_record': f"{last_5_wins}-{last_5_losses}-{last_5_ot_losses}",
            'last_5_gaa': round(last_5_gaa, 2),
            'last_5_sv_pct': round(last_5_sv_pct, 3)
        }
        GOALIE_STATS_CACHE[goalie_name] = cached_stats

        # Save cache to file
        try:
            with open(GOALIE_CACHE_FILE, 'w') as f:
                json.dump(GOALIE_STATS_CACHE, f)
        except Exception as e:
            print(f"⚠️ Error saving goalie stats cache: {e}")

        return cached_stats

    except Exception as e:
        print(f"⚠️ Error fetching stats for {goalie_name}: {e}")
        return None


def scrape_nhl_starting_goalies():
    """
    Scrape starting goalies from NHL lineup projections page.
    The first goalie listed for each team is considered the starter.

    Only scrapes after 2pm Montreal time to ensure lineup information is available.

    Returns dict with team names as keys and goalie info as values.
    """
    # Check if it's after 2pm Montreal time
    montreal_tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(montreal_tz)

    if current_time.hour < 14:  # Before 2pm
        print(f"⚠️ Skipping goalie scraping - before 2pm Montreal time (current: {current_time.strftime('%I:%M %p')})")
        return {}

    url = "https://www.nhl.com/news/nhl-lineup-projections-2025-26-season"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        goalies = {}

        # Find all team section headers
        for header in soup.find_all(['strong', 'b']):
            header_text = header.get_text(strip=True)

            # Look for team section headers (e.g., "Wild projected lineup")
            if "projected lineup" in header_text.lower():
                team_nickname = header_text.replace("projected lineup", "").strip(" :")

                # Convert nickname to API team name
                team_name = NHL_TEAM_NICKNAME_MAP.get(team_nickname, team_nickname)

                # Find goalies: they come after all the forward/defense lines (which contain "--")
                # and before "Scratched:" or "Injured:"
                current = header
                found_last_defensive_line = False
                goalie_candidates = []

                # Search through subsequent elements
                for _ in range(60):  # Look ahead up to 60 elements
                    current = current.find_next()
                    if not current:
                        break

                    # Stop if we hit the next team's lineup
                    current_text = current.get_text(strip=True)
                    if "projected lineup" in current_text.lower():
                        break

                    # Look for paragraph elements
                    if current.name == 'p':
                        text = current_text.strip()

                        # Skip empty or very long paragraphs
                        if not text or len(text) > 100:
                            continue

                        # Stop when we hit scratched/injured section
                        if any(marker in text.lower() for marker in ['scratched:', 'injured:']):
                            break

                        # Check if this line contains "--" (forward or defense line)
                        if '--' in text:
                            # This is a forward or defense line, keep going
                            found_last_defensive_line = True
                            continue

                        # If we've passed all the lines with "--" and this is a single name
                        # (no dashes, no special markers), it's likely a goalie
                        if found_last_defensive_line and '--' not in text:
                            # Clean up the name (remove special chars)
                            clean_name = text.replace('\xa0', ' ').replace('Â', '').strip()

                            # Make sure it looks like a name (has space, not too long)
                            if ' ' in clean_name and len(clean_name.split()) <= 3:
                                # Skip if it has numbers or looks like metadata
                                if not any(char.isdigit() for char in clean_name):
                                    goalie_candidates.append(clean_name)

                    # Stop when we hit scratched/injured tags
                    if current.name in ['strong', 'b']:
                        next_text = current_text.lower()
                        if next_text in ['scratched:', 'injured:']:
                            break

                # The goalies are typically the LAST 2 names in the candidates list
                # (scratched defensemen may appear first)
                if goalie_candidates:
                    # Take last 2 names as goalies, first one is starter
                    actual_goalies = goalie_candidates[-2:] if len(goalie_candidates) >= 2 else goalie_candidates
                    starter = actual_goalies[0]

                    goalies[team_name] = {
                        'name': starter,
                        'status': 'Confirmed'  # NHL lineup projections are typically confirmed
                    }

        if goalies:
            print(f"✅ Scraped {len(goalies)} starting goalies from NHL.com")

        return goalies

    except Exception as e:
        print(f"⚠️ Error scraping NHL starting goalies: {e}")
        return {}


def get_starting_goalies():
    """
    Get starting goalies with their stats. First tries to scrape from NHL.com lineup projections,
    then falls back to manual file if scraping fails.

    Manual file format (starting_goalies_today.txt):
    Team Name|Goalie Name|Confirmed
    Colorado Avalanche|Alexandar Georgiev|Confirmed
    Minnesota Wild|Filip Gustavsson|Confirmed

    Returns dict with team names as keys and goalie info as values.
    """
    # Try to scrape from NHL.com first
    goalies = scrape_nhl_starting_goalies()

    if goalies:
        # Fetch stats for each goalie
        for team, info in goalies.items():
            goalie_name = info['name']
            stats = get_goalie_stats(goalie_name)
            if stats:
                info.update(stats)
        return goalies

    # Fall back to manual file
    manual_file = "data/starting_goalies_today.txt"
    if os.path.exists(manual_file):
        try:
            goalies = {}
            with open(manual_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split('|')
                    if len(parts) >= 3:
                        team = parts[0].strip()
                        goalie = parts[1].strip()
                        status = parts[2].strip()

                        goalies[team] = {
                            'name': goalie,
                            'status': status
                        }

                        # Fetch stats
                        stats = get_goalie_stats(goalie)
                        if stats:
                            goalies[team].update(stats)

            if goalies:
                print(f"✅ Read {len(goalies)} starting goalies from manual file")
            return goalies
        except Exception as e:
            print(f"⚠️ Error reading manual goalies file: {e}")

    return {}


if __name__ == "__main__":
    goalies = get_starting_goalies()
    print("Starting Goalies:")
    for team, info in goalies.items():
        print(f"{team}: {info['name']} ({info['status']})")
