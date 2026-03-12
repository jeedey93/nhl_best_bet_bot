#!/usr/bin/env python3
"""
Generate daily picks table for the Today's Picks page.
Parses NHL and NBA prediction files and creates JavaScript data for daily-picks.html
"""

import os
import re
from datetime import datetime
from pathlib import Path


def parse_decimal_odds(decimal_odds):
    """Convert decimal odds to American odds format."""
    decimal_odds = float(decimal_odds)
    if decimal_odds >= 2.0:
        american = int((decimal_odds - 1) * 100)
        return f"+{american}"
    else:
        american = int(-100 / (decimal_odds - 1))
        return str(american)


def determine_bet_type(pick_text):
    """Determine bet type from pick text."""
    pick_lower = pick_text.lower()
    if 'ml' in pick_lower or 'moneyline' in pick_lower or ('@' in pick_text and 'vs' not in pick_lower):
        return 'moneyline'
    elif 'over' in pick_lower or 'under' in pick_lower:
        return 'total'
    elif '+' in pick_text or '-' in pick_text:
        # Check if it's a spread (has +/- followed by a number that's not odds)
        if re.search(r'[+-]\d+\.?\d*\s', pick_text):
            return 'spread'
    return 'moneyline'


def extract_confidence_from_text(text):
    """Extract confidence level from recommendation text."""
    confidence_match = re.search(r'Confidence Level:\s*(\w+)', text, re.IGNORECASE)
    if confidence_match:
        level = confidence_match.group(1).lower()
        if level == 'high':
            return ('⭐⭐⭐⭐', 'High')
        elif level == 'medium':
            return ('⭐⭐⭐', 'Medium')
        elif level == 'low':
            return ('⭐⭐', 'Low')
    return ('⭐⭐⭐⭐⭐', 'Very High')  # Default to very high for bet of the day


def parse_pick_line(line, game_matchups):
    """
    Parse a pick line like:
    'Boston Bruins ML vs Los Angeles Kings @ 1.69'
    'Minnesota Timberwolves +2.5 vs Los Angeles Clippers @ 1.91'
    'Toronto Maple Leafs vs Montréal Canadiens Over 6.5 @ 1.90'
    """
    # Extract odds first
    odds_match = re.search(r'@\s*([\d.]+)', line)
    if not odds_match:
        return None

    decimal_odds = odds_match.group(1)

    # Remove odds from line for easier parsing
    line_without_odds = line.split('@')[0].strip()

    # Determine if it's over/under
    if 'over' in line_without_odds.lower():
        match = re.search(r'(.+?)\s+vs\s+(.+?)\s+over\s+([\d.]+)', line_without_odds, re.IGNORECASE)
        if match:
            away_team = match.group(1).strip()
            home_team = match.group(2).strip()
            total = match.group(3)
            return {
                'pick': f'Over {total}',
                'game': f'{away_team} @ {home_team}',
                'odds': decimal_odds,
                'bet_type': 'total'
            }
    elif 'under' in line_without_odds.lower():
        match = re.search(r'(.+?)\s+vs\s+(.+?)\s+under\s+([\d.]+)', line_without_odds, re.IGNORECASE)
        if match:
            away_team = match.group(1).strip()
            home_team = match.group(2).strip()
            total = match.group(3)
            return {
                'pick': f'Under {total}',
                'game': f'{away_team} @ {home_team}',
                'odds': decimal_odds,
                'bet_type': 'total'
            }

    # Check for spread
    spread_match = re.search(r'(.+?)\s+([+-][\d.]+)\s+vs\s+(.+)', line_without_odds)
    if spread_match:
        team = spread_match.group(1).strip()
        spread = spread_match.group(2)
        opponent = spread_match.group(3).strip()

        # Try to determine home/away from game matchups
        game_format_found = False
        for matchup in game_matchups:
            if team in matchup and opponent in matchup:
                # Check if matchup uses @ or vs
                if '@' in matchup:
                    try:
                        if matchup.index('@') < matchup.index(team):
                            # Team is home
                            game_format_found = True
                            return {
                                'pick': f'{team} {spread}',
                                'game': f'{opponent} @ {team}',
                                'odds': decimal_odds,
                                'bet_type': 'spread'
                            }
                        else:
                            # Team is away
                            game_format_found = True
                            return {
                                'pick': f'{team} {spread}',
                                'game': f'{team} @ {opponent}',
                                'odds': decimal_odds,
                                'bet_type': 'spread'
                            }
                    except ValueError:
                        continue
                elif 'vs' in matchup:
                    # vs format: Home team vs Away team
                    if matchup.index('vs') < matchup.index(team):
                        # Team is away
                        game_format_found = True
                        return {
                            'pick': f'{team} {spread}',
                            'game': f'{team} @ {opponent}',
                            'odds': decimal_odds,
                            'bet_type': 'spread'
                        }
                    else:
                        # Team is home
                        game_format_found = True
                        return {
                            'pick': f'{team} {spread}',
                            'game': f'{opponent} @ {team}',
                            'odds': decimal_odds,
                            'bet_type': 'spread'
                        }

        # If no matchup found, default to "Team vs Opponent" format
        if not game_format_found:
            return {
                'pick': f'{team} {spread}',
                'game': f'{team} vs {opponent}',
                'odds': decimal_odds,
                'bet_type': 'spread'
            }

    # Check for ML
    ml_match = re.search(r'(.+?)\s+ML\s+vs\s+(.+)', line_without_odds, re.IGNORECASE)
    if ml_match:
        team = ml_match.group(1).strip()
        opponent = ml_match.group(2).strip()

        # Try to determine home/away from game matchups
        game_format_found = False
        for matchup in game_matchups:
            if team in matchup and opponent in matchup:
                # Check if matchup uses @ or vs
                if '@' in matchup:
                    try:
                        if matchup.index('@') < matchup.index(team):
                            # Team is home
                            game_format_found = True
                            return {
                                'pick': f'{team} ML',
                                'game': f'{opponent} @ {team}',
                                'odds': decimal_odds,
                                'bet_type': 'moneyline'
                            }
                        else:
                            # Team is away
                            game_format_found = True
                            return {
                                'pick': f'{team} ML',
                                'game': f'{team} @ {opponent}',
                                'odds': decimal_odds,
                                'bet_type': 'moneyline'
                            }
                    except ValueError:
                        continue
                elif 'vs' in matchup:
                    # vs format: Home team vs Away team
                    if matchup.index('vs') < matchup.index(team):
                        # Team is away
                        game_format_found = True
                        return {
                            'pick': f'{team} ML',
                            'game': f'{team} @ {opponent}',
                            'odds': decimal_odds,
                            'bet_type': 'moneyline'
                        }
                    else:
                        # Team is home
                        game_format_found = True
                        return {
                            'pick': f'{team} ML',
                            'game': f'{opponent} @ {team}',
                            'odds': decimal_odds,
                            'bet_type': 'moneyline'
                        }

        # If no matchup found, default to "Team vs Opponent" format
        if not game_format_found:
            return {
                'pick': f'{team} ML',
                'game': f'{team} vs {opponent}',
                'odds': decimal_odds,
                'bet_type': 'moneyline'
            }

    return None


def parse_prediction_file(file_path, sport):
    """Parse a prediction file and extract picks."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    picks = []
    seen_picks = set()  # Track picks we've already added to avoid duplicates

    # Check if this is a comparison file (contains "Report Comparison")
    is_comparison_file = 'Report Comparison' in content or 'comparison of the morning' in content.lower()

    # Extract game matchups for reference (as strings, not tuples)
    if is_comparison_file:
        # For comparison files, games might be in different format
        matchup_section = content[:1000]  # Just check the beginning
    else:
        matchup_section = content[:content.find('AI Analysis Summary')] if 'AI Analysis Summary' in content else content[:500]

    game_matchups = []
    for line in matchup_section.split('\n'):
        if ' @ ' in line or ' vs ' in line:
            game_matchups.append(line.strip())

    # Find BET OF THE DAY section (works for both formats)
    # Look for patterns like "🏆 **BET OF THE DAY**" or "BET OF THE DAY:"
    # The pick might be on the same line or the next line
    bet_of_day_match = re.search(r'(?:🏆\s*)?(?:\*\*)?BET OF THE DAY(?:\*\*)?:?\s*\n\*\*(.+?@\s*[\d.]+)\*\*', content, re.DOTALL | re.IGNORECASE)

    if bet_of_day_match:
        pick_line = bet_of_day_match.group(1).strip()

        # Find the section after this pick for reasoning
        start_pos = bet_of_day_match.end()
        section_text = content[start_pos:start_pos + 1500]

        # Extract confidence and reasoning
        conf_match = re.search(r'Confidence Level:\s*(\w+(?:\s+\w+)?)', section_text, re.IGNORECASE)
        confidence_level = conf_match.group(1).strip() if conf_match else "High"

        # Get reasoning lines
        reasoning_lines = []
        for line in section_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('Confidence Level:') and not line.startswith('This play') and not line.startswith('Line moved') and not line.startswith('Odds remained') and not line.startswith('**Other'):
                reasoning_lines.append(line)
            if line.startswith('**Other'):
                break

        reasoning = ' '.join(reasoning_lines).strip()

        pick_data = parse_pick_line(pick_line, game_matchups)
        if pick_data:
            # Create unique key for this pick
            pick_key = f"{pick_data['game']}|{pick_data['pick']}"
            if pick_key not in seen_picks:
                seen_picks.add(pick_key)

                # Map confidence string to stars
                conf_map = {
                    'high': ('⭐⭐⭐⭐', 'High'),
                    'medium': ('⭐⭐⭐', 'Medium'),
                    'low': ('⭐⭐', 'Low'),
                    'very high': ('⭐⭐⭐⭐⭐', 'Very High')
                }
                confidence = conf_map.get(confidence_level.lower(), ('⭐⭐⭐⭐⭐', 'Very High'))

                picks.append({
                    'game': pick_data['game'],
                    'pick': pick_data['pick'],
                    'odds': pick_data['odds'],
                    'bet_type': pick_data['bet_type'],
                    'confidence': confidence[1],
                    'stars': confidence[0],
                    'reasoning': reasoning
                })

    # Find Other Recommended Plays (works for both formats)
    other_plays_section = re.search(r'(?:\*\*)?Other Recommended Plays(?:\*\*)?(.+?)(?:\n\n\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
    if other_plays_section:
        plays_text = other_plays_section.group(1)

        # Find all bold lines with team names and @ odds
        pick_lines = re.findall(r'\*\*([A-Z][^*]+@\s*[\d.]+)\*\*', plays_text)

        for pick_line in pick_lines:
            pick_line = pick_line.strip()

            # Find the section for this pick (from pick line to next pick or end)
            escaped_pick = re.escape(pick_line)  # Use full pick line
            # Try to match until next pick or end of text
            section_match = re.search(rf'\*\*{escaped_pick}\*\*\s*\n(.*?)(?=\n\*\*[A-Z])', plays_text, re.DOTALL)

            # If no match (likely the last pick), try matching till end
            if not section_match:
                section_match = re.search(rf'\*\*{escaped_pick}\*\*\s*\n(.*)', plays_text, re.DOTALL)

            reasoning = ""
            confidence_level = "High"

            if section_match:
                section_text = section_match.group(1)

                # Extract confidence level
                conf_match = re.search(r'Confidence Level:\s*(\w+(?:\s+\w+)?)', section_text, re.IGNORECASE)
                if conf_match:
                    confidence_level = conf_match.group(1).strip()

                # Extract reasoning (text before metadata lines)
                reasoning_lines = []
                for line in section_text.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('Confidence Level:') and not line.startswith('This play') and not line.startswith('Line moved') and not line.startswith('Odds remained') and not line.startswith('The morning report'):
                        reasoning_lines.append(line)

                reasoning = ' '.join(reasoning_lines).strip()

            pick_data = parse_pick_line(pick_line, game_matchups)
            if pick_data:
                # Create unique key for this pick
                pick_key = f"{pick_data['game']}|{pick_data['pick']}"
                if pick_key not in seen_picks:
                    seen_picks.add(pick_key)

                    # Map confidence string to stars
                    conf_map = {
                        'high': ('⭐⭐⭐⭐', 'High'),
                        'medium': ('⭐⭐⭐', 'Medium'),
                        'low': ('⭐⭐', 'Low'),
                        'very high': ('⭐⭐⭐⭐⭐', 'Very High')
                    }
                    confidence = conf_map.get(confidence_level.lower(), ('⭐⭐⭐⭐', 'High'))

                    picks.append({
                        'game': pick_data['game'],
                        'pick': pick_data['pick'],
                        'odds': pick_data['odds'],
                        'bet_type': pick_data['bet_type'],
                        'confidence': confidence[1],
                        'stars': confidence[0],
                        'reasoning': reasoning,
                        'time': 'TBD'
                    })

    return picks


def get_latest_prediction_file(sport):
    """Get the latest prediction file for a sport from main predictions directory."""
    predictions_dir = f'data/predictions/{sport}'

    if not os.path.exists(predictions_dir):
        return None

    # Get all prediction files matching the pattern
    pattern = f'{sport}_daily_predictions_*.txt'
    files = []

    for filename in os.listdir(predictions_dir):
        if filename.startswith(f'{sport}_daily_predictions_') and filename.endswith('.txt'):
            filepath = os.path.join(predictions_dir, filename)
            # Skip if it's a directory
            if os.path.isfile(filepath):
                files.append(filepath)

    if not files:
        return None

    # Sort by modification time, get the most recent
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    return files[0]


def generate_javascript_data(nhl_picks, nba_picks):
    """Generate JavaScript code with picks data."""

    def picks_to_js(picks):
        js_picks = []
        for pick in picks:
            js_picks.append(f"""  {{
    game: '{pick['game']}',
    pick: '{pick['pick']}',
    odds: '{pick['odds']}',
    betType: '{pick['bet_type']}',
    confidence: '{pick['confidence']}',
    stars: '{pick['stars']}',
    reasoning: `{pick['reasoning']}`
  }}""")
        return ',\n'.join(js_picks)

    js_code = f"""// Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
const picks = {{
  nhl: [
{picks_to_js(nhl_picks)}
  ],
  nba: [
{picks_to_js(nba_picks)}
  ]
}};

// Populate the page
renderPicks();
"""

    return js_code


def update_html_with_data(html_path, js_data):
    """Update the HTML file with the JavaScript data."""
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Find the script section and replace the picks data
    script_start = html_content.find('// TODO: This will be populated by your daily run scripts')
    if script_start == -1:
        print("Warning: Could not find TODO comment in HTML")
        return False

    # Find the end of the picks object
    picks_start = html_content.find('const picks = {', script_start)
    if picks_start == -1:
        print("Warning: Could not find picks object in HTML")
        return False

    # Find the closing of picks object
    picks_end = html_content.find('};', picks_start) + 2

    # Find renderPicks() call
    render_call = html_content.find('function renderPicks()', picks_end)
    if render_call == -1:
        render_call = html_content.find('renderPicks();', picks_end)

    # Replace the section
    new_html = (
        html_content[:picks_start] +
        js_data +
        html_content[render_call:]
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_html)

    return True


def main():
    """Main function to generate daily picks table."""
    print("Generating daily picks table...")

    # Get latest prediction files
    nhl_file = get_latest_prediction_file('nhl')
    nba_file = get_latest_prediction_file('nba')

    nhl_picks = []
    nba_picks = []

    if nhl_file:
        print(f"Found NHL predictions: {nhl_file}")
        nhl_picks = parse_prediction_file(nhl_file, 'nhl')
        print(f"Extracted {len(nhl_picks)} NHL picks")
    else:
        print("No NHL prediction file found for today")

    if nba_file:
        print(f"Found NBA predictions: {nba_file}")
        nba_picks = parse_prediction_file(nba_file, 'nba')
        print(f"Extracted {len(nba_picks)} NBA picks")
    else:
        print("No NBA prediction file found for today")

    # Generate JavaScript data
    js_data = generate_javascript_data(nhl_picks, nba_picks)

    # Update HTML file
    html_path = 'docs/daily-picks.html'
    if update_html_with_data(html_path, js_data):
        print(f"✅ Successfully updated {html_path}")
        print(f"Total picks: {len(nhl_picks) + len(nba_picks)} (NHL: {len(nhl_picks)}, NBA: {len(nba_picks)})")
    else:
        print("❌ Failed to update HTML file")

        # Write to separate JS file as fallback
        js_file = 'docs/daily-picks-data.js'
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(js_data)
        print(f"📝 Wrote data to {js_file} instead")


if __name__ == '__main__':
    main()
