#!/usr/bin/env python3
"""
Hockey Pool - Hold & Trade Management Utilities
Provides functions to manage player holds and update accumulated points
"""

import json
import os
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://fifurqlitkywtmhgtzeu.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZpZnVycWxpdGt5d3RtaGd0emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MDIyMjQsImV4cCI6MjA5MjI3ODIyNH0.KPVPj1qwbSJJMyLR_-AhDcRs0vi2sUU6qbFQ-kH53C0')

HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

def get_all_holds(league_code: str) -> list:
    """Fetch all active holds for a league."""
    try:
        resp = requests.get(
            f'{SUPABASE_URL}/rest/v1/player_holds?league_code=eq.{league_code}',
            headers=HEADERS
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Error fetching holds: {resp.status_code}")
            return []
    except Exception as e:
        print(f"Exception fetching holds: {e}")
        return []

def get_hold(hold_id: str) -> dict:
    """Fetch a specific hold by ID."""
    try:
        resp = requests.get(
            f'{SUPABASE_URL}/rest/v1/player_holds?id=eq.{hold_id}',
            headers=HEADERS
        )
        if resp.status_code == 200:
            data = resp.json()
            return data[0] if data else None
        return None
    except Exception as e:
        print(f"Exception fetching hold: {e}")
        return None

def create_hold(league_code: str, team_id: str, player_slug: str, date_acquired: str) -> dict:
    """Create a new player hold."""
    payload = {
        'league_code': league_code,
        'team_id': team_id,
        'player_slug': player_slug,
        'date_acquired': date_acquired,
        'points_accumulated': 0
    }
    try:
        resp = requests.post(
            f'{SUPABASE_URL}/rest/v1/player_holds',
            headers=HEADERS,
            json=payload
        )
        if resp.status_code in [200, 201]:
            return resp.json()[0] if isinstance(resp.json(), list) else resp.json()
        else:
            print(f"Error creating hold: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Exception creating hold: {e}")
        return None

def update_hold_points(hold_id: str, points: int) -> bool:
    """Update accumulated points on a hold."""
    try:
        resp = requests.patch(
            f'{SUPABASE_URL}/rest/v1/player_holds?id=eq.{hold_id}',
            headers=HEADERS,
            json={'points_accumulated': points}
        )
        return resp.status_code in [200, 204]
    except Exception as e:
        print(f"Exception updating hold points: {e}")
        return False

def delete_hold(hold_id: str) -> bool:
    """Delete a hold (release player)."""
    try:
        resp = requests.delete(
            f'{SUPABASE_URL}/rest/v1/player_holds?id=eq.{hold_id}',
            headers=HEADERS
        )
        return resp.status_code in [200, 204]
    except Exception as e:
        print(f"Exception deleting hold: {e}")
        return False

def get_all_trades(league_code: str) -> list:
    """Fetch all trades for a league."""
    try:
        resp = requests.get(
            f'{SUPABASE_URL}/rest/v1/player_trades?league_code=eq.{league_code}',
            headers=HEADERS
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Error fetching trades: {resp.status_code}")
            return []
    except Exception as e:
        print(f"Exception fetching trades: {e}")
        return []

def record_trade(
    league_code: str,
    team_id: str,
    player_from_slug: str,
    player_to_slug: str,
    date_from_acquired: str,
    date_traded: str,
    points_accumulated_at_trade: int
) -> dict:
    """Record a completed trade."""
    payload = {
        'league_code': league_code,
        'team_id': team_id,
        'player_from_slug': player_from_slug,
        'player_to_slug': player_to_slug,
        'date_from_acquired': date_from_acquired,
        'date_traded': date_traded,
        'points_accumulated_at_trade': points_accumulated_at_trade
    }
    try:
        resp = requests.post(
            f'{SUPABASE_URL}/rest/v1/player_trades',
            headers=HEADERS,
            json=payload
        )
        if resp.status_code in [200, 201]:
            return resp.json()[0] if isinstance(resp.json(), list) else resp.json()
        else:
            print(f"Error recording trade: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Exception recording trade: {e}")
        return None

def get_player_stats(player_slug: str) -> dict:
    """Fetch current stats for a player."""
    try:
        resp = requests.get(
            f'{SUPABASE_URL}/rest/v1/nhl_players?puckpedia_slug=eq.{player_slug}&select=*',
            headers=HEADERS
        )
        if resp.status_code == 200:
            data = resp.json()
            return data[0] if data else None
        return None
    except Exception as e:
        print(f"Exception fetching player stats: {e}")
        return None

def get_scoring_settings(league_code: str) -> dict:
    """Fetch scoring settings for a league."""
    defaults = {
        'f_points': 1,
        'd_goals': 1,
        'd_assists': 1,
        'g_wins': 2,
        'g_shutouts': 3
    }
    try:
        resp = requests.get(
            f'{SUPABASE_URL}/rest/v1/pool_settings?league_code=eq.{league_code}',
            headers=HEADERS
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return {**defaults, **data[0]}
        return defaults
    except Exception as e:
        print(f"Exception fetching scoring settings: {e}")
        return defaults

def calculate_pool_score(player: dict, scoring: dict) -> int:
    """Calculate pool score for a player given scoring settings."""
    if not player:
        return 0

    position = player.get('position', 'F').upper()

    if 'G' in position or position == 'G':
        return (player.get('wins', 0) or 0) * scoring['g_wins'] + \
               (player.get('shutouts', 0) or 0) * scoring['g_shutouts']
    elif position == 'D' or 'D' in position:
        return (player.get('goals', 0) or 0) * scoring['d_goals'] + \
               (player.get('assists', 0) or 0) * scoring['d_assists']
    else:  # Forward
        return (player.get('points', 0) or 0) * scoring['f_points']

def update_all_hold_points(league_code: str):
    """Update accumulated points for all active holds in a league."""
    holds = get_all_holds(league_code)
    scoring = get_scoring_settings(league_code)

    updated = 0
    for hold in holds:
        player = get_player_stats(hold['player_slug'])
        if not player:
            print(f"Warning: Player not found for hold {hold['id']}")
            continue

        points = calculate_pool_score(player, scoring)
        if update_hold_points(hold['id'], points):
            updated += 1
            print(f"✓ Updated {player['player_name']}: {points} pts")
        else:
            print(f"✗ Failed to update hold {hold['id']}")

    print(f"\nUpdated {updated}/{len(holds)} holds")
    return updated

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python hockey_pool_trades.py <command> [args]")
        print("\nCommands:")
        print("  list-holds <league_code>           - List all active holds")
        print("  list-trades <league_code>          - List all trades")
        print("  update-points <league_code>        - Update all hold points")
        print("  player-stats <player_slug>         - Get player stats")
        print("  scoring-settings <league_code>     - Get scoring rules")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'list-holds' and len(sys.argv) > 2:
        league_code = sys.argv[2]
        holds = get_all_holds(league_code)
        print(f"\nActive Holds for {league_code}:")
        for hold in holds:
            print(f"\n  Player: {hold['player_slug']}")
            print(f"    Acquired: {hold['date_acquired']}")
            print(f"    Points: {hold['points_accumulated']}")

    elif command == 'list-trades' and len(sys.argv) > 2:
        league_code = sys.argv[2]
        trades = get_all_trades(league_code)
        print(f"\nTrade History for {league_code}:")
        for trade in trades:
            print(f"\n  {trade['player_from_slug']} → {trade['player_to_slug']}")
            print(f"    Traded: {trade['date_traded']}")
            print(f"    Pts Saved: {trade['points_accumulated_at_trade']}")

    elif command == 'update-points' and len(sys.argv) > 2:
        league_code = sys.argv[2]
        update_all_hold_points(league_code)

    elif command == 'player-stats' and len(sys.argv) > 2:
        player_slug = sys.argv[2]
        player = get_player_stats(player_slug)
        if player:
            print(f"\n{player['player_name']} ({player['team']}):")
            print(f"  Position: {player['position']}")
            print(f"  Goals: {player.get('goals', 0)}")
            print(f"  Assists: {player.get('assists', 0)}")
            print(f"  Points: {player.get('points', 0)}")
            print(f"  Wins: {player.get('wins', 0)}")
            print(f"  Shutouts: {player.get('shutouts', 0)}")
        else:
            print(f"Player not found: {player_slug}")

    elif command == 'scoring-settings' and len(sys.argv) > 2:
        league_code = sys.argv[2]
        scoring = get_scoring_settings(league_code)
        print(f"\nScoring Settings for {league_code}:")
        print(f"  Forward Points: {scoring['f_points']}")
        print(f"  Defenseman Goals: {scoring['d_goals']}")
        print(f"  Defenseman Assists: {scoring['d_assists']}")
        print(f"  Goalie Wins: {scoring['g_wins']}")
        print(f"  Goalie Shutouts: {scoring['g_shutouts']}")

    else:
        print(f"Unknown command or missing arguments: {command}")
        sys.exit(1)

