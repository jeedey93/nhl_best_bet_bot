"""
NHL and NBA odds cache to minimize API calls to The Odds API.

This module provides a file-based cache for betting odds that reduces redundant
API calls during the dual-run system (7am and 3pm NBA runs) and other scenarios.

The cache is stored in data/cache/ and expires after 2 hours. Since the bot runs
twice daily (7am and 3pm), this ensures:
- 7am run always fetches fresh odds (no cache from previous day)
- 3pm run may use 7am cache if still valid, or fetches fresh odds
- Cache expires before next day's runs

Cache keys include both sport and date to prevent stale cross-day data.
"""

import os
import json
import time
from datetime import datetime
import pytz


CACHE_DIR = "data/cache"
NHL_CACHE_FILE_TEMPLATE = os.path.join(CACHE_DIR, "nhl_odds_{date}.json")
NBA_CACHE_FILE_TEMPLATE = os.path.join(CACHE_DIR, "nba_odds_{date}.json")
CACHE_TTL = 2 * 60 * 60  # 2 hours in seconds


def ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def get_cache_filepath(sport, date_str):
    """
    Get cache file path for a specific sport and date.

    Args:
        sport: 'nhl' or 'nba'
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Full path to cache file
    """
    if sport.lower() == 'nhl':
        return NHL_CACHE_FILE_TEMPLATE.format(date=date_str)
    elif sport.lower() == 'nba':
        return NBA_CACHE_FILE_TEMPLATE.format(date=date_str)
    else:
        raise ValueError(f"Unsupported sport: {sport}")


def get_current_date_montreal():
    """Get current date in Montreal timezone as YYYY-MM-DD string."""
    eastern = pytz.timezone("America/Toronto")
    now = datetime.now(eastern)
    return now.strftime("%Y-%m-%d")


def is_cache_valid(cache_file):
    """Check if cache file exists and is not expired."""
    if not os.path.exists(cache_file):
        return False

    file_age = time.time() - os.path.getmtime(cache_file)
    return file_age < CACHE_TTL


def load_cache(cache_file):
    """Load odds data from cache file."""
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
            return data.get('odds', [])
    except (json.JSONDecodeError, IOError):
        return None


def save_cache(cache_file, odds_data):
    """Save odds data to cache file with timestamp."""
    ensure_cache_dir()
    data = {
        'timestamp': datetime.now().isoformat(),
        'odds': odds_data
    }
    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=2)


def get_cached_odds(sport, date_str=None, force_refresh=False):
    """
    Get cached odds data for a specific sport and date.

    Args:
        sport: 'nhl' or 'nba'
        date_str: Date string in YYYY-MM-DD format (defaults to today in Montreal time)
        force_refresh: If True, bypass cache and return None (caller should fetch fresh)

    Returns:
        List of odds data if cache is valid, None otherwise
    """
    if force_refresh:
        return None

    if date_str is None:
        date_str = get_current_date_montreal()

    cache_file = get_cache_filepath(sport, date_str)

    if is_cache_valid(cache_file):
        cached = load_cache(cache_file)
        if cached is not None:
            print(f"✓ Using cached {sport.upper()} odds from {cache_file}")
            return cached

    return None


def save_odds_to_cache(sport, odds_data, date_str=None):
    """
    Save odds data to cache.

    Args:
        sport: 'nhl' or 'nba'
        odds_data: List of odds data from The Odds API
        date_str: Date string in YYYY-MM-DD format (defaults to today in Montreal time)
    """
    if date_str is None:
        date_str = get_current_date_montreal()

    cache_file = get_cache_filepath(sport, date_str)
    save_cache(cache_file, odds_data)
    print(f"✓ Saved {sport.upper()} odds to cache: {cache_file}")


def clear_old_caches(days_to_keep=2):
    """
    Remove old cache files to prevent directory bloat.

    Args:
        days_to_keep: Number of days of cache files to keep (default 2)
    """
    ensure_cache_dir()

    cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)

    for filename in os.listdir(CACHE_DIR):
        if filename.startswith(('nhl_odds_', 'nba_odds_')) and filename.endswith('.json'):
            filepath = os.path.join(CACHE_DIR, filename)
            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    print(f"✓ Removed old cache file: {filename}")
                except Exception as e:
                    print(f"⚠️ Failed to remove {filename}: {e}")


if __name__ == "__main__":
    # Test the cache system
    print("Testing odds cache system...")

    # Test date handling
    today = get_current_date_montreal()
    print(f"Current date (Montreal): {today}")

    # Test cache file paths
    nhl_path = get_cache_filepath('nhl', today)
    nba_path = get_cache_filepath('nba', today)
    print(f"\nCache file paths:")
    print(f"  NHL: {nhl_path}")
    print(f"  NBA: {nba_path}")

    # Test save and load
    test_data = [
        {"home_team": "Test Team 1", "away_team": "Test Team 2", "odds": "test"}
    ]

    print("\nTesting save...")
    save_odds_to_cache('nhl', test_data, today)

    print("\nTesting load...")
    loaded = get_cached_odds('nhl', today)
    if loaded:
        print(f"✓ Successfully loaded cached data: {len(loaded)} games")
    else:
        print("✗ Failed to load cached data")

    print("\nTesting force_refresh...")
    loaded = get_cached_odds('nhl', today, force_refresh=True)
    if loaded is None:
        print("✓ force_refresh correctly bypassed cache")
    else:
        print("✗ force_refresh did not bypass cache")

    print("\nTesting old cache cleanup...")
    clear_old_caches(days_to_keep=2)

    print("\n✓ Cache system tests complete")
