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

                # Find the goalie section - look for paragraph elements after this header
                current = header
                goalie_names = []

                # Search through subsequent elements
                for _ in range(50):  # Look ahead up to 50 elements
                    current = current.find_next()
                    if not current:
                        break

                    # Stop if we hit the next team's lineup
                    current_text = current.get_text(strip=True)
                    if "projected lineup" in current_text.lower():
                        break

                    # Look for standalone goalie names (paragraphs with single names)
                    # Goalies are typically listed after defensive pairs and before scratched/injured
                    if current.name == 'p':
                        text = current_text.strip()
                        # Goalie names are simple: "FirstName LastName" with no special characters
                        # Skip if it contains special chars like dashes, "at", numbers
                        if text and ' ' in text and len(text.split()) <= 3:
                            # Skip lines that look like game info or other metadata
                            if any(skip in text.lower() for skip in ['at', 'et;', 'p.m.', 'a.m.', '--', 'scratched:', 'injured:']):
                                continue
                            # Skip if it starts with a number (time) or has parentheses
                            if text[0].isdigit() or '(' in text or ')' in text:
                                continue
                            # This might be a goalie
                            goalie_names.append(text)

                    # Stop when we hit scratched/injured section
                    if current.name in ['strong', 'b']:
                        next_text = current_text.lower()
                        if next_text in ['scratched:', 'injured:']:
                            break

                # The first goalie listed is the starter (last 2 in the list before scratched/injured)
                # Typically the roster format is: forwards, defense, then 2 goalies
                if len(goalie_names) >= 2:
                    # Take the last 2 names found (these are usually the goalies)
                    potential_goalies = goalie_names[-2:]
                    starter = potential_goalies[0]  # First of the two goalies is the starter

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
