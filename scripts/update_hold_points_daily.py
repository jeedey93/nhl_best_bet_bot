#!/usr/bin/env python3
"""
Daily update script to refresh accumulated points on active player holds.
Runs daily via GitHub Actions to keep hold points current with player stats.
"""

import os
import json
from datetime import datetime
from scripts.hockey_pool_trades import (
    get_all_holds,
    get_player_stats,
    get_scoring_settings,
    update_hold_points,
    calculate_pool_score,
    SUPABASE_URL,
    SUPABASE_KEY
)

def get_all_leagues():
    """Fetch list of all leagues from Supabase."""
    import requests
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    }
    try:
        resp = requests.get(
            f'{SUPABASE_URL}/rest/v1/pool_leagues?select=code',
            headers=headers
        )
        if resp.status_code == 200:
            return [row['code'] for row in resp.json()]
        return []
    except Exception as e:
        print(f"Error fetching leagues: {e}")
        return []

def update_league_holds(league_code: str) -> dict:
    """Update all holds for a specific league."""
    print(f"\n{'='*60}")
    print(f"Updating holds for league: {league_code}")
    print(f"{'='*60}")

    holds = get_all_holds(league_code)
    scoring = get_scoring_settings(league_code)

    stats = {
        'total': len(holds),
        'updated': 0,
        'failed': 0,
        'errors': []
    }

    if not holds:
        print(f"  No active holds found")
        return stats

    for hold in holds:
        player_slug = hold['player_slug']
        hold_id = hold['id']

        try:
            player = get_player_stats(player_slug)
            if not player:
                print(f"  ✗ {player_slug}: Player not found")
                stats['failed'] += 1
                stats['errors'].append(f"Player not found: {player_slug}")
                continue

            points = calculate_pool_score(player, scoring)

            if update_hold_points(hold_id, points):
                print(f"  ✓ {player['player_name']}: {points} pts")
                stats['updated'] += 1
            else:
                print(f"  ✗ {player['player_name']}: Update failed")
                stats['failed'] += 1
                stats['errors'].append(f"Failed to update: {player_slug}")

        except Exception as e:
            print(f"  ✗ {player_slug}: {str(e)}")
            stats['failed'] += 1
            stats['errors'].append(f"Exception: {player_slug} - {str(e)}")

    print(f"\nSummary: {stats['updated']} updated, {stats['failed']} failed")
    return stats

def main():
    """Main entry point."""
    print(f"Starting daily hold points update: {datetime.now().isoformat()}")

    leagues = get_all_leagues()
    print(f"Found {len(leagues)} leagues: {', '.join(leagues)}")

    if not leagues:
        print("No leagues to update.")
        return

    all_stats = {
        'timestamp': datetime.now().isoformat(),
        'leagues': {}
    }

    for league_code in leagues:
        try:
            stats = update_league_holds(league_code)
            all_stats['leagues'][league_code] = stats
        except Exception as e:
            print(f"\nError updating league {league_code}: {e}")
            all_stats['leagues'][league_code] = {
                'error': str(e),
                'updated': 0,
                'failed': 0
            }

    # Log summary
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print(f"{'='*60}")

    total_updated = sum(s.get('updated', 0) for s in all_stats['leagues'].values())
    total_failed = sum(s.get('failed', 0) for s in all_stats['leagues'].values())

    print(f"Total Updated: {total_updated}")
    print(f"Total Failed: {total_failed}")
    print(f"Timestamp: {all_stats['timestamp']}")

    # Save summary to file for reference
    summary_file = 'data/hold_updates_log.json'
    try:
        existing = []
        if os.path.exists(summary_file):
            with open(summary_file, 'r') as f:
                existing = json.load(f)

        existing.append(all_stats)
        with open(summary_file, 'w') as f:
            json.dump(existing[-30:], f, indent=2)  # Keep last 30 runs

        print(f"✓ Summary saved to {summary_file}")
    except Exception as e:
        print(f"Warning: Could not save summary: {e}")

if __name__ == '__main__':
    main()

