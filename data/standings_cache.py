"""
NHL and NBA standings cache to avoid redundant API calls.

This module provides a simple file-based cache for team standings that can be
shared across multiple scripts (games page, predictions, team pages, etc.).

The cache is stored in data/cache/ and expires after 4 hours to ensure
standings stay relatively fresh while minimizing API calls.
"""

import os
import json
import time
import requests
from datetime import datetime


CACHE_DIR = "data/cache"
NHL_CACHE_FILE = os.path.join(CACHE_DIR, "nhl_standings.json")
NBA_CACHE_FILE = os.path.join(CACHE_DIR, "nba_standings.json")
CACHE_TTL = 4 * 60 * 60  # 4 hours in seconds


def ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def is_cache_valid(cache_file):
    """Check if cache file exists and is not expired."""
    if not os.path.exists(cache_file):
        return False

    file_age = time.time() - os.path.getmtime(cache_file)
    return file_age < CACHE_TTL


def load_cache(cache_file):
    """Load standings from cache file."""
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
            return data.get('standings', {})
    except (json.JSONDecodeError, IOError):
        return None


def save_cache(cache_file, standings):
    """Save standings to cache file with timestamp."""
    ensure_cache_dir()
    data = {
        'timestamp': datetime.now().isoformat(),
        'standings': standings
    }
    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=2)


def fetch_nhl_standings_from_api():
    """
    Fetch current NHL standings from API.
    Returns dict mapping team abbreviations to their data (record, points, etc.).
    """
    try:
        standings_url = 'https://api-web.nhle.com/v1/standings/now'
        response = requests.get(standings_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        time.sleep(0.6)  # Add delay to avoid 429 rate limits

        standings = {}
        for standing in data.get('standings', []):
            team_abbrev = standing.get('teamAbbrev', {}).get('default', '')
            team_name_full = standing.get('teamName', {}).get('default', '')
            team_name_place = standing.get('placeName', {}).get('default', '')

            wins = standing.get('wins', 0)
            losses = standing.get('losses', 0)
            otl = standing.get('otLosses', 0)
            points = standing.get('points', 0)
            games_played = standing.get('gamesPlayed', 0)
            points_pct = standing.get('pointPctg', 0.0)
            league_sequence = standing.get('leagueSequence', 99)

            record = f"{wins}-{losses}-{otl}"

            standings[team_abbrev] = {
                'abbrev': team_abbrev,
                'full_name': f"{team_name_place} {team_name_full}",
                'place_name': team_name_place,
                'team_name': team_name_full,
                'record': record,
                'wins': wins,
                'losses': losses,
                'otl': otl,
                'points': points,
                'games_played': games_played,
                'points_pct': points_pct,
                'league_rank': league_sequence
            }

        return standings
    except Exception as e:
        print(f"Error fetching NHL standings: {e}")
        return {}


def fetch_nba_standings_from_api():
    """
    Fetch current NBA standings from API.
    Returns dict mapping team names to their data (record, win %, etc.).
    """
    try:
        # ESPN API for NBA standings
        standings_url = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'
        response = requests.get(standings_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        standings = {}

        # Process both conferences (Eastern and Western)
        for entry in data.get('children', []):
            for standing_entry in entry.get('standings', {}).get('entries', []):
                team_data = standing_entry.get('team', {})
                team_name = team_data.get('displayName', '')
                team_abbrev = team_data.get('abbreviation', '')

                # Extract stats from the stats array
                stats = {stat['name']: stat['value']
                        for stat in standing_entry.get('stats', [])}

                wins = int(stats.get('wins', 0))
                losses = int(stats.get('losses', 0))
                win_pct = float(stats.get('winPercent', 0))
                games_played = int(stats.get('gamesPlayed', 0))
                rank = int(stats.get('rank', 99))

                record = f"{wins}-{losses}"

                standings[team_name] = {
                    'abbrev': team_abbrev,
                    'full_name': team_name,
                    'record': record,
                    'wins': wins,
                    'losses': losses,
                    'games_played': games_played,
                    'win_pct': win_pct,
                    'league_rank': rank
                }

        return standings
    except Exception as e:
        print(f"Error fetching NBA standings: {e}")
        return {}


def get_nhl_standings(force_refresh=False):
    """
    Get NHL standings with caching.

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        Dict mapping team abbreviations to their standings data
    """
    if not force_refresh and is_cache_valid(NHL_CACHE_FILE):
        cached = load_cache(NHL_CACHE_FILE)
        if cached:
            return cached

    # Fetch fresh data
    standings = fetch_nhl_standings_from_api()
    if standings:
        save_cache(NHL_CACHE_FILE, standings)

    return standings


def get_nba_standings(force_refresh=False):
    """
    Get NBA standings with caching.

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        Dict mapping team names to their standings data
    """
    if not force_refresh and is_cache_valid(NBA_CACHE_FILE):
        cached = load_cache(NBA_CACHE_FILE)
        if cached:
            return cached

    # Fetch fresh data
    standings = fetch_nba_standings_from_api()
    if standings:
        save_cache(NBA_CACHE_FILE, standings)

    return standings


def get_team_record_by_abbrev(team_abbrev, sport='nhl'):
    """
    Get a specific team's record by their abbreviation.

    Args:
        team_abbrev: Team abbreviation (e.g., 'MTL', 'BOS')
        sport: 'nhl' or 'nba'

    Returns:
        String like "44-12-9" for NHL or "44-12" for NBA, or None if not found
    """
    if sport.lower() == 'nhl':
        standings = get_nhl_standings()
        team_data = standings.get(team_abbrev)
        return team_data['record'] if team_data else None
    elif sport.lower() == 'nba':
        standings = get_nba_standings()
        # NBA uses full team names as keys, so we need to find by abbrev
        for team_name, team_data in standings.items():
            if team_data.get('abbrev') == team_abbrev:
                return team_data['record']
        return None
    else:
        return None


def get_team_data_by_abbrev(team_abbrev, sport='nhl'):
    """
    Get all standings data for a specific team by their abbreviation.

    Args:
        team_abbrev: Team abbreviation (e.g., 'MTL', 'BOS')
        sport: 'nhl' or 'nba'

    Returns:
        Dict with team standings data, or None if not found
    """
    if sport.lower() == 'nhl':
        standings = get_nhl_standings()
        return standings.get(team_abbrev)
    elif sport.lower() == 'nba':
        standings = get_nba_standings()
        # NBA uses full team names as keys, so we need to find by abbrev
        for team_name, team_data in standings.items():
            if team_data.get('abbrev') == team_abbrev:
                return team_data
        return None
    else:
        return None


if __name__ == "__main__":
    # Test the cache
    print("Testing NHL standings cache...")
    nhl = get_nhl_standings()
    print(f"Fetched {len(nhl)} NHL teams")
    if nhl:
        # Show first 3 teams as example
        for i, (abbrev, data) in enumerate(list(nhl.items())[:3]):
            print(f"  {abbrev}: {data['full_name']} - {data['record']}")

    print("\nTesting NBA standings cache...")
    nba = get_nba_standings()
    print(f"Fetched {len(nba)} NBA teams")
    if nba:
        # Show first 3 teams as example
        for i, (team_name, data) in enumerate(list(nba.items())[:3]):
            print(f"  {data['abbrev']}: {team_name} - {data['record']}")

    print("\nTesting specific team lookup...")
    mtl_record = get_team_record_by_abbrev('MTL', 'nhl')
    print(f"Montreal Canadiens record: {mtl_record}")

    mtl_data = get_team_data_by_abbrev('MTL', 'nhl')
    if mtl_data:
        print(f"Full data: Points={mtl_data['points']}, League Rank={mtl_data['league_rank']}")
