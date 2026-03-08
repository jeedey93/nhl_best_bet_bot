import requests
from bs4 import BeautifulSoup
import os


def get_starting_goalies():
    """
    Get starting goalies. First tries to read from manual file,
    then falls back to empty dict if unavailable.

    Manual file format (starting_goalies_today.txt):
    Team Name|Goalie Name|Confirmed
    Colorado|Alexandar Georgiev|Confirmed
    Minnesota|Filip Gustavsson|Unconfirmed

    Returns dict with team names as keys and goalie info as values.
    """
    goalies = {}

    # Try to read from manual file first
    manual_file = "data/starting_goalies_today.txt"
    if os.path.exists(manual_file):
        try:
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
        except Exception as e:
            print(f"⚠️ Error reading manual goalies file: {e}")

    return goalies


if __name__ == "__main__":
    goalies = get_starting_goalies()
    print("Starting Goalies:")
    for team, info in goalies.items():
        print(f"{team}: {info['name']} ({info['status']})")
