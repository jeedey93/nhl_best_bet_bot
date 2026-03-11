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

    # Fix Mc/Mac names (e.g., "Mc Avoy" -> "McAvoy", "Mac Kenzie" -> "MacKenzie")
    name = re.sub(r'\bMc ([A-Z])', r'Mc\1', name)
    name = re.sub(r'\bMac ([A-Z])', r'Mac\1', name)

    # Clean up multiple spaces
    name = ' '.join(name.split())

    return name

def scrape_nhl_daily_lines():
    """
    Scrape projected lineups for all teams from NHL.com.

    Only scrapes after 2pm Montreal time to ensure lineup information is available.

    Returns:
        dict: Mapping of team names to their projected lines structure
              {
                  'Team Name': {
                      'forward_lines': [
                          ['Player1', 'Player2', 'Player3'],  # Line 1
                          ['Player4', 'Player5', 'Player6'],  # Line 2
                          ...
                      ],
                      'defense_pairs': [
                          ['Player1', 'Player2'],  # Pair 1
                          ['Player3', 'Player4'],  # Pair 2
                          ...
                      ],
                      'goalies': ['Goalie1', 'Goalie2']
                  }
              }
    """
    # Check if it's after 2pm Montreal time
    montreal_tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(montreal_tz)

    if current_time.hour < 14:  # Before 2pm
        print(f"⚠️ Skipping daily lines scraping - before 2pm Montreal time (current: {current_time.strftime('%I:%M %p')})")
        return {}

    url = "https://www.nhl.com/news/nhl-lineup-projections-2025-26-season"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    lines_by_team = {}

    # Find all elements that could be a team section header
    for header in soup.find_all(['strong', 'b']):
        header_text = header.get_text(strip=True)

        # Look for team section headers with "projected lineup"
        if "projected lineup" in header_text.lower():
            team_name = header_text.replace("projected lineup", "").strip(" :")

            # Initialize team data structure
            forward_lines = []
            defense_pairs = []
            goalies = []

            # Track current position in parsing
            current_section = None
            current_line = []

            # Get all text between this header and the next team's header
            current_element = header.find_next()

            while current_element:
                # Stop if we hit the next team's lineup or end of content
                text = current_element.get_text(strip=True)

                if current_element.name in ['strong', 'b']:
                    next_header = text.lower()

                    # Check if this is the next team
                    if "projected lineup" in next_header and team_name.lower() not in next_header:
                        break

                    # Check for section markers (Scratched/Injured means we're done with lines)
                    if next_header in ["scratched:", "injured:"]:
                        break

                # Look for lines in text format (e.g., "Player1 -- Player2 -- Player3")
                # Note: NHL.com uses both "--" and "–" (en dash) in their HTML
                if ('--' in text or '–' in text or '\x80\x93' in text) and text.strip():
                    # Clean up the text first - handle various dash encodings and apostrophes
                    cleaned_text = text.replace("'", "")
                    # Handle UTF-8 encoded en dash (â\x80\x93)
                    cleaned_text = cleaned_text.replace('\u2013', '--')  # en dash
                    cleaned_text = cleaned_text.replace('\u2014', '--')  # em dash
                    cleaned_text = cleaned_text.replace('–', '--')  # another en dash variant
                    cleaned_text = cleaned_text.replace('—', '--')  # em dash variant
                    cleaned_text = cleaned_text.replace('â\x80\x93', '--')  # malformed UTF-8 en dash
                    cleaned_text = cleaned_text.replace('â', '')  # Remove remaining â characters
                    cleaned_text = cleaned_text.strip()

                    # Skip if the line doesn't look valid (has weird characters or too short)
                    if len(cleaned_text) < 10:
                        current_element = current_element.find_next()
                        continue

                    # Split by double dash and filter
                    parts = cleaned_text.split('--')
                    players = []
                    for part in parts:
                        # Clean each part and check if it looks like a valid player name
                        player = clean_player_name(part.strip())
                        if player and len(player) > 2 and ' ' in player:  # Must have first and last name
                            players.append(player)

                    # Determine if it's forwards (3 players) or defense (2 players)
                    if len(players) == 3:
                        forward_lines.append(players)
                    elif len(players) == 2:
                        defense_pairs.append(players)

                # Also check for individual goalie names (single names on their own line)
                elif text and not any(skip in text.lower() for skip in ['scratched', 'injured', 'projected', 'at', 'et;', 'p.m.', 'a.m.']):
                    # Check if this looks like a single player name (goalie)
                    if len(text.split()) <= 3 and not '--' in text:
                        # This might be a goalie
                        # Goalies typically come after defense pairs
                        if len(defense_pairs) > 0 and len(goalies) < 2:
                            cleaned_name = clean_player_name(text)
                            if cleaned_name and len(cleaned_name.split()) >= 2:  # First and last name
                                goalies.append(cleaned_name)

                current_element = current_element.find_next()

            # Only add team if we found at least some lines
            if forward_lines or defense_pairs or goalies:
                lines_by_team[team_name] = {
                    'forward_lines': forward_lines,
                    'defense_pairs': defense_pairs,
                    'goalies': goalies
                }

    return lines_by_team

def format_lines_for_display(team_lines):
    """
    Format team lines for HTML display.

    Args:
        team_lines: Dict with forward_lines, defense_pairs, and goalies

    Returns:
        str: HTML formatted string of the lines
    """
    if not team_lines:
        return "<p>No lineup information available</p>"

    html = ""

    # Forward Lines
    if team_lines.get('forward_lines'):
        for i, line in enumerate(team_lines['forward_lines'], 1):
            html += f"<div class='lineup-line'>{' — '.join(line)}</div>\n"

    # Defense Pairs
    if team_lines.get('defense_pairs'):
        html += "<div class='lineup-spacer'></div>\n"
        for pair in team_lines['defense_pairs']:
            html += f"<div class='lineup-line defense-line'>{' — '.join(pair)}</div>\n"

    # Goalies
    if team_lines.get('goalies'):
        html += "<div class='lineup-spacer'></div>\n"
        for goalie in team_lines['goalies']:
            html += f"<div class='lineup-line goalie-line'>{goalie}</div>\n"

    return html

if __name__ == "__main__":
    lines = scrape_nhl_daily_lines()
    print("NHL Daily Lines by Team:")
    for team, team_lines in lines.items():
        print(f"\n{team}:")
        print("Forward Lines:")
        for i, line in enumerate(team_lines['forward_lines'], 1):
            print(f"  Line {i}: {' -- '.join(line)}")
        print("Defense Pairs:")
        for i, pair in enumerate(team_lines['defense_pairs'], 1):
            print(f"  Pair {i}: {' -- '.join(pair)}")
        print("Goalies:")
        for goalie in team_lines['goalies']:
            print(f"  {goalie}")
