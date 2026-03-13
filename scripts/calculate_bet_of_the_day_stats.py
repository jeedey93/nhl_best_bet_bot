#!/usr/bin/env python3
"""
Calculate Bet of the Day statistics by cross-referencing predictions with results.
"""

import os
import re
from datetime import datetime
from glob import glob

def extract_date_from_filename(filename):
    """Extract date from filename like 'nhl_daily_predictions_2026-02-26.txt'"""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    return match.group(1) if match else None

def extract_bet_of_the_day_from_prediction(filepath):
    """Extract BET OF THE DAY from prediction file.

    Handles two formats:
    1. Standard format: BET OF THE DAY: or BET OF THE DAY\n with bet on next line
    2. Comparison format: 🏆 **BET OF THE DAY** with **bet** on next line
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try format 1: Standard format
        match = re.search(r'BET OF THE DAY:?\s*\n(.+?)(?:\n.*?Confidence Level:|$)', content, re.DOTALL)
        if match:
            bet_line = match.group(1).strip()
            return bet_line

        # Try format 2: Comparison format with trophy emoji
        match = re.search(r'🏆\s*\*\*BET OF THE DAY\*\*\s*\n\*\*(.+?)\*\*', content, re.DOTALL)
        if match:
            bet_line = match.group(1).strip()
            return bet_line

        return None
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def extract_all_bets_from_results(filepath):
    """Extract all bets (with WIN/LOSS outcomes) from results file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        bets = []

        # Split into numbered sections (must start at beginning of line)
        sections = re.split(r'(?=^\d+\.\s+\*{0,2})', content, flags=re.MULTILINE)

        for section in sections:
            # Look for bet description and outcome
            bet_match = re.search(r'^\d+\.\s+\*{0,2}(?:BET OF THE DAY:?\s*)?(.*?)\*{0,2}(?:\s*@\s*[\d.]+)?$', section, re.MULTILINE)
            outcome_match = re.search(r'(?:Prediction Outcome|Result|Outcome):\s*\*{0,2}.*?\*{0,2}(WIN|LOSS)\*{0,2}', section, re.IGNORECASE)

            if bet_match and outcome_match:
                bet_desc = bet_match.group(1).strip()
                outcome = outcome_match.group(1).upper()

                # Clean up bet description
                bet_desc = re.sub(r'BET OF THE DAY:?\s*', '', bet_desc, flags=re.IGNORECASE)

                # Skip obviously wrong extractions
                if len(bet_desc) < 10 or 'breakdown' in bet_desc.lower():
                    continue

                bets.append({
                    'bet': bet_desc.strip(),
                    'outcome': outcome
                })

        return bets
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

def normalize_bet_string(bet):
    """Normalize bet string for comparison."""
    # Remove odds, markdown, extra spaces
    bet = re.sub(r'@\s*[\d.]+', '', bet)  # Remove odds
    bet = re.sub(r'\*+', '', bet)  # Remove asterisks
    bet = re.sub(r'\s+', ' ', bet)  # Normalize whitespace
    return bet.strip().lower()

def extract_teams_and_bet_type(bet_string):
    """Extract key components from a bet string for matching."""
    normalized = normalize_bet_string(bet_string)

    # Extract teams
    teams = []
    for word in normalized.split():
        # Skip common bet-related words
        if word not in ['ml', 'vs', '@', 'over', 'under', 'spread', '-', '+']:
            teams.append(word)

    # Determine bet type
    bet_type = None
    if 'over' in normalized:
        bet_type = 'over'
    elif 'under' in normalized:
        bet_type = 'under'
    elif 'ml' in normalized or 'moneyline' in normalized:
        bet_type = 'ml'
    elif any(c.isdigit() for c in normalized.split()[-1] if '.' in normalized.split()[-1]):
        bet_type = 'spread'

    return set(teams), bet_type

def find_bet_outcome(prediction_bet, results_bets, debug=False):
    """Find matching bet in results and return outcome."""
    normalized_pred = normalize_bet_string(prediction_bet)
    pred_teams, pred_type = extract_teams_and_bet_type(prediction_bet)

    if debug:
        print(f"\n  Searching for: {normalized_pred}")
        print(f"    Teams: {pred_teams}")
        print(f"    Type: {pred_type}")

    best_match = None
    best_score = 0

    for result_bet in results_bets:
        normalized_result = normalize_bet_string(result_bet['bet'])
        result_teams, result_type = extract_teams_and_bet_type(result_bet['bet'])

        # Calculate match score
        common_teams = pred_teams & result_teams
        score = len(common_teams)

        # Bonus for matching bet type
        if pred_type and result_type and pred_type == result_type:
            score += 2

        if debug:
            print(f"    Comparing to: {normalized_result}")
            print(f"      Teams: {result_teams}, Common: {common_teams}, Score: {score}")

        # Need at least 2 team words matching
        if score > best_score and len(common_teams) >= 2:
            best_score = score
            best_match = result_bet

    if best_match:
        if debug:
            print(f"    ✓ BEST MATCH: {best_match['bet']} => {best_match['outcome']}")
        return best_match['outcome']

    return None

def calculate_botd_stats():
    """Calculate bet of the day statistics and return data structure.

    Returns:
        dict: {
            'nhl': {'wins': int, 'losses': int, 'not_found': int, 'dates': list},
            'nba': {'wins': int, 'losses': int, 'not_found': int, 'dates': list},
            'combined': {'wins': int, 'losses': int, 'win_rate': float}
        }
    """
    # Directories
    nhl_predictions_dir = "data/predictions/nhl"
    nba_predictions_dir = "data/predictions/nba"
    nhl_results_dir = "data/bot_results/nhl"
    nba_results_dir = "data/bot_results/nba"

    # Track bet of the day results
    botd_results = {
        'nhl': {'wins': 0, 'losses': 0, 'not_found': 0, 'dates': []},
        'nba': {'wins': 0, 'losses': 0, 'not_found': 0, 'dates': []}
    }

    print("=" * 80)
    print("BET OF THE DAY STATISTICS CALCULATOR")
    print("=" * 80)
    print()

    # Process NHL predictions
    print("🏒 NHL BET OF THE DAY ANALYSIS")
    print("-" * 80)

    nhl_pred_files = sorted(glob(os.path.join(nhl_predictions_dir, "nhl_daily_predictions_*.txt")))

    for pred_file in nhl_pred_files:
        pred_date = extract_date_from_filename(pred_file)
        if not pred_date:
            continue

        # Results file is dated THE NEXT DAY (analyzes previous day's games)
        # So prediction for 2026-02-26 matches results for 2026-02-27
        from datetime import datetime, timedelta
        pred_dt = datetime.strptime(pred_date, '%Y-%m-%d')
        result_dt = pred_dt + timedelta(days=1)
        result_date = result_dt.strftime('%Y-%m-%d')

        # Find corresponding results file
        result_file = os.path.join(nhl_results_dir, f"nhl_daily_results_{result_date}.txt")
        if not os.path.exists(result_file):
            continue

        date = pred_date  # For display purposes

        # Extract bet of the day from prediction
        botd = extract_bet_of_the_day_from_prediction(pred_file)
        if not botd:
            continue

        # Extract all bets from results
        result_bets = extract_all_bets_from_results(result_file)
        if not result_bets:
            continue

        # Find outcome
        outcome = find_bet_outcome(botd, result_bets)

        if outcome == 'WIN':
            botd_results['nhl']['wins'] += 1
            print(f"✅ {date}: WIN - {botd[:60]}...")
            botd_results['nhl']['dates'].append((date, 'WIN', botd))
        elif outcome == 'LOSS':
            botd_results['nhl']['losses'] += 1
            print(f"❌ {date}: LOSS - {botd[:60]}...")
            botd_results['nhl']['dates'].append((date, 'LOSS', botd))
        else:
            botd_results['nhl']['not_found'] += 1
            print(f"⚠️  {date}: NOT FOUND - {botd[:60]}...")
            botd_results['nhl']['dates'].append((date, 'NOT FOUND', botd))

    print()
    print("🏀 NBA BET OF THE DAY ANALYSIS")
    print("-" * 80)

    # Process NBA predictions
    nba_pred_files = sorted(glob(os.path.join(nba_predictions_dir, "nba_daily_predictions_*.txt")))

    for pred_file in nba_pred_files:
        # Skip 7am and 3pm files, only use final comparison files
        if '_7am_' in pred_file or '_3pm_' in pred_file or '_12pm_' in pred_file:
            continue

        pred_date = extract_date_from_filename(pred_file)
        if not pred_date:
            continue

        # Results file is dated THE NEXT DAY (analyzes previous day's games)
        # So prediction for 2026-02-26 matches results for 2026-02-27
        from datetime import datetime, timedelta
        pred_dt = datetime.strptime(pred_date, '%Y-%m-%d')
        result_dt = pred_dt + timedelta(days=1)
        result_date = result_dt.strftime('%Y-%m-%d')

        # Find corresponding results file
        result_file = os.path.join(nba_results_dir, f"nba_daily_results_{result_date}.txt")
        if not os.path.exists(result_file):
            continue

        date = pred_date  # For display purposes

        # Extract bet of the day from prediction
        botd = extract_bet_of_the_day_from_prediction(pred_file)
        if not botd:
            continue

        # Extract all bets from results
        result_bets = extract_all_bets_from_results(result_file)
        if not result_bets:
            continue

        # Find outcome
        outcome = find_bet_outcome(botd, result_bets)

        if outcome == 'WIN':
            botd_results['nba']['wins'] += 1
            print(f"✅ {date}: WIN - {botd[:60]}...")
            botd_results['nba']['dates'].append((date, 'WIN', botd))
        elif outcome == 'LOSS':
            botd_results['nba']['losses'] += 1
            print(f"❌ {date}: LOSS - {botd[:60]}...")
            botd_results['nba']['dates'].append((date, 'LOSS', botd))
        else:
            botd_results['nba']['not_found'] += 1
            print(f"⚠️  {date}: NOT FOUND - {botd[:60]}...")
            botd_results['nba']['dates'].append((date, 'NOT FOUND', botd))

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    nhl_total = botd_results['nhl']['wins'] + botd_results['nhl']['losses']
    nba_total = botd_results['nba']['wins'] + botd_results['nba']['losses']
    total_wins = botd_results['nhl']['wins'] + botd_results['nba']['wins']
    total_losses = botd_results['nhl']['losses'] + botd_results['nba']['losses']
    grand_total = total_wins + total_losses

    print(f"🏒 NHL BET OF THE DAY:")
    print(f"   Record: {botd_results['nhl']['wins']}-{botd_results['nhl']['losses']}")
    if nhl_total > 0:
        win_pct = (botd_results['nhl']['wins'] / nhl_total) * 100
        print(f"   Win Rate: {win_pct:.1f}%")
    print(f"   Not Found: {botd_results['nhl']['not_found']}")
    print()

    print(f"🏀 NBA BET OF THE DAY:")
    print(f"   Record: {botd_results['nba']['wins']}-{botd_results['nba']['losses']}")
    if nba_total > 0:
        win_pct = (botd_results['nba']['wins'] / nba_total) * 100
        print(f"   Win Rate: {win_pct:.1f}%")
    print(f"   Not Found: {botd_results['nba']['not_found']}")
    print()

    print(f"📊 COMBINED BET OF THE DAY:")
    print(f"   Record: {total_wins}-{total_losses}")
    if grand_total > 0:
        win_pct = (total_wins / grand_total) * 100
        print(f"   Win Rate: {win_pct:.1f}%")
    print()

    print(f"📈 COMPARISON TO OVERALL:")
    print(f"   Your Overall Record: 68-70 (49.3%)")
    if grand_total > 0:
        botd_pct = (total_wins / grand_total) * 100
        diff = botd_pct - 49.3
        symbol = "📈" if diff > 0 else "📉"
        print(f"   Bet of the Day Record: {total_wins}-{total_losses} ({botd_pct:.1f}%)")
        print(f"   Difference: {symbol} {diff:+.1f}%")
    print()
    print("=" * 80)

    # Return the data structure
    combined_wins = total_wins
    combined_losses = total_losses
    combined_total = grand_total
    combined_win_rate = (total_wins / grand_total * 100) if grand_total > 0 else 0

    return {
        'nhl': botd_results['nhl'],
        'nba': botd_results['nba'],
        'combined': {
            'wins': combined_wins,
            'losses': combined_losses,
            'total': combined_total,
            'win_rate': combined_win_rate
        }
    }

def main():
    """Main function for CLI usage."""
    calculate_botd_stats()

if __name__ == "__main__":
    main()
