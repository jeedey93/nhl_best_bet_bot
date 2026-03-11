import requests
from bs4 import BeautifulSoup
import re
import pytz
from datetime import datetime

def clean_player_name(name):
    """Clean and format player names properly."""
    # Remove HTML entities and unicode issues
    name = name.replace('\xa0', '').replace('Â', '').strip()

    # Fix common HTML encoding issues for apostrophes
    name = name.replace('â', "'")  # â€™ becomes â in some cases
    name = name.replace('â€™', "'")
    name = name.replace('&#39;', "'")
    name = name.replace('&apos;', "'")

    # Handle names without spaces (e.g., "SidneyCrosby" -> "Sidney Crosby")
    # Look for pattern: lowercase letter followed by uppercase letter
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)

    # Clean up multiple spaces
    name = ' '.join(name.split())

    return name

def scrape_nhl_absences_by_team():
    """
    Scrape injured and scratched players by team from NHL.com.

    Only scrapes after 2pm Montreal time to ensure lineup information is available.

    Returns:
        dict: Mapping of team names to lists of absent players
    """
    # Check if it's after 2pm Montreal time
    montreal_tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(montreal_tz)

    if current_time.hour < 14:  # Before 2pm
        print(f"⚠️ Skipping absences scraping - before 2pm Montreal time (current: {current_time.strftime('%I:%M %p')})")
        return {}

    url = "https://www.nhl.com/news/nhl-lineup-projections-2025-26-season"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    absences_by_team = {}

    # Find all elements that could be a team section header
    for header in soup.find_all(['strong', 'b']):
        header_text = header.get_text(strip=True)
        # Look for team section headers
        if "projected lineup" in header_text.lower():
            team_name = header_text.replace("projected lineup", "").strip(" :")
            team_players = []

            # Search for both "Scratched:" and "Injured:" tags after this header
            next_tag = header.find_next(['strong', 'b'])

            # Look for scratched and injured players
            while next_tag:
                next_text = next_tag.get_text(strip=True).lower()

                if next_text == "scratched:":
                    # The player info is usually in the next sibling
                    next_node = next_tag.next_sibling
                    if next_node:
                        scratched_list = str(next_node).strip()
                        scratched_list = scratched_list.lstrip(":").strip()
                        for player in scratched_list.split(","):
                            player = clean_player_name(player)
                            if player and player.lower() != "none":
                                team_players.append(f"{player} (scratched)")

                elif next_text == "injured:":
                    # The player info is usually in the next sibling
                    next_node = next_tag.next_sibling
                    if next_node:
                        injured_list = str(next_node).strip()
                        injured_list = injured_list.lstrip(":").strip()
                        for player in injured_list.split(","):
                            player = clean_player_name(player)
                            if player and player.lower() != "none":
                                team_players.append(player)

                # Stop when we hit the next team's lineup
                elif "projected lineup" in next_text:
                    break

                next_tag = next_tag.find_next(['strong', 'b'])

            if team_players:
                absences_by_team[team_name] = team_players

    return absences_by_team

if __name__ == "__main__":
    absences_by_team = scrape_nhl_absences_by_team()
    print("NHL Player Absences by Team:")
    for team, players in absences_by_team.items():
        print(f"{team}:")
        for player in players:
            print(f"  {player}")
