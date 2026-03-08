import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
from zoneinfo import ZoneInfo


# Mapping from NHL.com lineup page team nicknames to NHL API team names
NHL_TEAM_NICKNAME_MAP = {
    'Ducks': 'Anaheim',
    'Bruins': 'Boston',
    'Sabres': 'Buffalo',
    'Flames': 'Calgary',
    'Hurricanes': 'Carolina',
    'Blackhawks': 'Chicago',
    'Avalanche': 'Colorado',
    'Blue Jackets': 'Columbus',
    'Stars': 'Dallas',
    'Red Wings': 'Detroit',
    'Oilers': 'Edmonton',
    'Panthers': 'Florida',
    'Kings': 'Los Angeles',
    'Wild': 'Minnesota',
    'Canadiens': 'Montréal',
    'Predators': 'Nashville',
    'Devils': 'New Jersey',
    'Islanders': 'New York',
    'Rangers': 'New York',
    'Senators': 'Ottawa',
    'Flyers': 'Philadelphia',
    'Penguins': 'Pittsburgh',
    'Sharks': 'San Jose',
    'Kraken': 'Seattle',
    'Blues': 'St. Louis',
    'Lightning': 'Tampa Bay',
    'Maple Leafs': 'Toronto',
    'Canucks': 'Vancouver',
    'Golden Knights': 'Vegas',
    'Capitals': 'Washington',
    'Jets': 'Winnipeg',
}


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

        # Search for goalie using NHL web API search with last name
        search_url = f'https://search.d3.nhle.com/api/v1/search/player?culture=en-us&limit=20&q={last_name}'
        response = requests.get(search_url, timeout=5)
        results = response.json()

        if not results:
            return None

        # Find the goalie with matching first name
        goalie_id = None

        # First pass: look for active goalie with matching first name
        for result in results:
            if (result.get('positionCode') == 'G' and
                result.get('active', False) and
                result.get('name', '').startswith(first_name)):
                goalie_id = result['playerId']
                break

        # Second pass: look for any goalie with matching first name
        if not goalie_id:
            for result in results:
                if result.get('positionCode') == 'G' and result.get('name', '').startswith(first_name):
                    goalie_id = result['playerId']
                    break

        # Third pass: fallback to first active goalie
        if not goalie_id:
            for result in results:
                if result.get('positionCode') == 'G' and result.get('active', False):
                    goalie_id = result['playerId']
                    break

        # Fourth pass: fallback to any goalie
        if not goalie_id:
            for result in results:
                if result.get('positionCode') == 'G':
                    goalie_id = result['playerId']
                    break

        if not goalie_id:
            return None

        # Get current season
        current_year = datetime.now(ZoneInfo('America/Toronto')).year
        current_month = datetime.now(ZoneInfo('America/Toronto')).month
        # NHL season spans two years, starts in October
        if current_month >= 10:
            season = f"{current_year}{current_year+1}"
        else:
            season = f"{current_year-1}{current_year}"

        # Get player stats
        stats_url = f'https://api-web.nhle.com/v1/player/{goalie_id}/landing'
        response = requests.get(stats_url, timeout=5)
        data = response.json()

        # Get season stats from featuredStats
        season_stats = data.get('featuredStats', {}).get('regularSeason', {}).get('subSeason', {})

        if not season_stats:
            return None

        wins = season_stats.get('wins', 0)
        losses = season_stats.get('losses', 0)
        ot_losses = season_stats.get('otLosses', 0)
        gaa = season_stats.get('goalsAgainstAvg', 0)
        sv_pct = season_stats.get('savePctg', 0)

        # Get last 5 game logs
        gamelog_url = f'https://api-web.nhle.com/v1/player/{goalie_id}/game-log/{season}/2'
        response = requests.get(gamelog_url, timeout=5)
        gamelog_data = response.json()

        games = gamelog_data.get('gameLog', [])[:5]  # Last 5 games

        last_5_wins = 0
        last_5_losses = 0
        last_5_goals_against = []
        last_5_shots_against = []

        for game in games:
            # Only count games where goalie started
            if game.get('gamesStarted', 0) > 0:
                decision = game.get('decision', '')
                if decision == 'W':
                    last_5_wins += 1
                elif decision in ['L', 'O']:
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

        return {
            'record': f"{wins}-{losses}-{ot_losses}",
            'gaa': round(gaa, 2),
            'sv_pct': round(sv_pct, 3),
            'last_5_record': f"{last_5_wins}-{last_5_losses}",
            'last_5_gaa': round(last_5_gaa, 2),
            'last_5_sv_pct': round(last_5_sv_pct, 3)
        }

    except Exception as e:
        print(f"⚠️ Error fetching stats for {goalie_name}: {e}")
        return None


def scrape_nhl_starting_goalies():
    """
    Scrape starting goalies from NHL lineup projections page.
    The first goalie listed for each team is considered the starter.

    Returns dict with team names as keys and goalie info as values.
    """
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

                # The first goalie candidate is the starter
                if goalie_candidates:
                    starter = goalie_candidates[0]

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
