import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nhl_games import get_games_yesterday
from data.nba_games import get_nba_games_yesterday


def record_nhl_games_with_scores():
    """Record yesterday's NHL games with final scores."""
    # Get yesterday's date in Montreal timezone
    montreal_tz = ZoneInfo('America/Toronto')
    yesterday = (datetime.now(montreal_tz) - timedelta(days=1)).date()
    date_str = yesterday.isoformat()

    # Create directory if it doesn't exist
    output_dir = "data/results_with_scores/nhl"
    os.makedirs(output_dir, exist_ok=True)

    # Get yesterday's games with scores
    games = get_games_yesterday()

    if not games:
        print(f"No NHL games found for {date_str}")
        return

    # Format output
    output_file = os.path.join(output_dir, f"nhl_games_scores_{date_str}.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Date: {date_str}\n\n")

        for game in games:
            away_team = game['away']
            home_team = game['home']
            away_score = game.get('away_score', 'N/A')
            home_score = game.get('home_score', 'N/A')

            f.write(f"{away_team} {away_score} - {home_team} {home_score}\n")

    print(f"✅ Recorded NHL games with scores: {output_file}")


def record_nba_games_with_scores():
    """Record yesterday's NBA games with final scores."""
    # Get yesterday's date in Montreal timezone
    montreal_tz = ZoneInfo('America/Toronto')
    yesterday = (datetime.now(montreal_tz) - timedelta(days=1)).date()
    date_str = yesterday.isoformat()

    # Create directory if it doesn't exist
    output_dir = "data/results_with_scores/nba"
    os.makedirs(output_dir, exist_ok=True)

    # Get yesterday's games with scores
    games = get_nba_games_yesterday()

    if not games:
        print(f"No NBA games found for {date_str}")
        return

    # Format output
    output_file = os.path.join(output_dir, f"nba_games_scores_{date_str}.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Date: {date_str}\n\n")

        for game in games:
            away_team = game['away']
            home_team = game['home']
            away_score = game.get('away_score', 'N/A')
            home_score = game.get('home_score', 'N/A')

            f.write(f"{away_team} {away_score} - {home_team} {home_score}\n")

    print(f"✅ Recorded NBA games with scores: {output_file}")


if __name__ == "__main__":
    print("Recording yesterday's games with scores...")
    record_nhl_games_with_scores()
    record_nba_games_with_scores()
    print("Done!")
