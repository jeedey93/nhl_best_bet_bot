import requests
from bs4 import BeautifulSoup
import os


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
    Get starting goalies. First tries to scrape from NHL.com lineup projections,
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
