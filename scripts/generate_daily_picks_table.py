#!/usr/bin/env python3
"""
Generate daily picks table for the Today's Picks page.
Parses NHL and NBA prediction files and creates JavaScript data for daily-picks.html
Also summarizes reasonings using Gemini in one batch call.
"""

import os
import sys
import re
import time
from datetime import datetime
from pathlib import Path
from google import genai
from dotenv import load_dotenv

def normalize_pick_line(line):
    """Clean up pick lines: remove junk tokens, fix all-caps team names."""
    line = re.sub(r'<[^>]+>', '', line)  # remove any <token> artifacts
    line = line.strip()
    # If the whole line before '@' is uppercase, title-case it
    parts = line.split('@')
    if len(parts) == 2 and parts[0] == parts[0].upper():
        line = parts[0].strip().title() + ' @ ' + parts[1].strip()
        # Fix common title-case issues: ML, OT, etc.
        line = re.sub(r'\bMl\b', 'ML', line)
        line = re.sub(r'\bNhl\b', 'NHL', line)
        line = re.sub(r'\bNba\b', 'NBA', line)
    return line

load_dotenv()


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

    # Normalize all-caps team names to title case
    def fix_case(s):
        alpha = [c for c in s if c.isalpha()]
        if alpha and sum(c.isupper() for c in alpha) / len(alpha) > 0.8:
            s = s.title()
            s = re.sub(r'\bMl\b', 'ML', s)
            s = re.sub(r'\bNhl\b', 'NHL', s)
            s = re.sub(r'\bNba\b', 'NBA', s)
            s = re.sub(r'\bVs\b', 'vs', s)
        return s
    line_without_odds = fix_case(line_without_odds)

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
    bet_of_day_match = re.search(r'(?:🏆\s*)?(?:\*\*)?BET OF THE DAY(?:\*\*)?:?\s*\n(?:\*\*)?(.+?@\s*[\d.]+)(?:\*\*)?', content, re.DOTALL | re.IGNORECASE)

    if bet_of_day_match:
        pick_line = normalize_pick_line(bet_of_day_match.group(1).strip())

        # Find the section after this pick for reasoning
        start_pos = bet_of_day_match.end()
        section_text = content[start_pos:start_pos + 1500]

        # Extract confidence and reasoning
        conf_match = re.search(r'Confidence Level:\s*(\w+(?:\s+\w+)?)', section_text, re.IGNORECASE)
        confidence_level = conf_match.group(1).strip() if conf_match else "High"

        # Get reasoning lines and extract win probability
        reasoning_lines = []
        win_probability = None
        for line in section_text.split('\n'):
            line = line.strip()
            # Extract win probability
            if 'Win Probability:' in line:
                prob_match = re.search(r'Win Probability:\s*([\d.]+)%', line)
                if prob_match:
                    win_probability = prob_match.group(1)
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
                    'win_probability': win_probability,
                    'reasoning': reasoning,
                    'is_bet_of_day': True
                })

    # Find Other Recommended Plays (works for both formats)
    other_plays_section = re.search(r'(?:\*\*)?Other Recommended Plays(?:\*\*)?(.+?)(?:\n\n\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
    if other_plays_section:
        plays_text = other_plays_section.group(1)

        # Find all pick lines with team names and @ odds (with or without bold markers)
        pick_lines = re.findall(r'(?:\*\*)?([A-Z][^*\n]+@\s*[\d.]+)(?:\*\*)?', plays_text)

        for raw_pick_line in pick_lines:
            raw_pick_line = raw_pick_line.strip()
            pick_line = normalize_pick_line(raw_pick_line)

            # Search using the raw line to match original text
            escaped_pick = re.escape(raw_pick_line)
            # Try to match until next pick or end of text
            section_match = re.search(rf'(?:\*\*)?{escaped_pick}(?:\*\*)?\s*\n(.*?)(?=\n(?:\*\*)?[A-Z][^\n]+@\s*[\d.]|\Z)', plays_text, re.DOTALL)

            # If no match (likely the last pick), try matching till end
            if not section_match:
                section_match = re.search(rf'(?:\*\*)?{escaped_pick}(?:\*\*)?\s*\n(.*)', plays_text, re.DOTALL)

            reasoning = ""
            confidence_level = "High"
            win_probability = None

            if section_match:
                section_text = section_match.group(1)

                # Extract confidence level
                conf_match = re.search(r'Confidence Level:\s*(\w+(?:\s+\w+)?)', section_text, re.IGNORECASE)
                if conf_match:
                    confidence_level = conf_match.group(1).strip()

                # Extract win probability
                prob_match = re.search(r'Win Probability:\s*([\d.]+)%', section_text)
                if prob_match:
                    win_probability = prob_match.group(1)

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
                        'win_probability': win_probability,
                        'reasoning': reasoning,
                        'time': 'TBD',
                        'is_bet_of_day': False
                    })

    return picks


def get_latest_prediction_file(sport):
    """Get the latest prediction file for a sport from main predictions directory."""
    from datetime import date
    today = date.today().isoformat()

    predictions_dir = f'data/predictions/{sport}'

    # Prefer today's merged file in main folder (written by compare scripts at 3pm)
    merged = os.path.join(predictions_dir, f'{sport}_daily_predictions_{today}.txt')
    if os.path.isfile(merged):
        return merged

    # Fall back to daily_runs: 3pm then 7am
    daily_runs_dir = os.path.join(predictions_dir, 'daily_runs')
    for suffix in ['_3pm', '_7am']:
        candidate = os.path.join(daily_runs_dir, f'{sport}_daily_predictions_{today}{suffix}.txt')
        if os.path.isfile(candidate):
            return candidate

    if not os.path.exists(predictions_dir):
        return None

    # Last resort: most recently modified file in main folder
    files = [
        os.path.join(predictions_dir, f)
        for f in os.listdir(predictions_dir)
        if f.startswith(f'{sport}_daily_predictions_') and f.endswith('.txt')
        and os.path.isfile(os.path.join(predictions_dir, f))
    ]
    if not files:
        return None
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return files[0]


def generate_javascript_data(nhl_picks, nba_picks):
    """Generate JavaScript code with picks data."""

    def picks_to_js(picks):
        js_picks = []
        for pick in picks:
            win_prob = pick.get('win_probability', '')
            is_bet_of_day = 'true' if pick.get('is_bet_of_day', False) else 'false'
            js_picks.append(f"""  {{
    game: '{pick['game']}',
    pick: '{pick['pick']}',
    odds: '{pick['odds']}',
    betType: '{pick['bet_type']}',
    confidence: '{pick['confidence']}',
    stars: '{pick['stars']}',
    winProbability: '{win_prob}',
    reasoning: `{pick['reasoning']}`,
    isBetOfDay: {is_bet_of_day}
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


def load_summarize_prompt():
    """Load the summarize bullet points prompt."""
    prompt_file = Path(__file__).parent.parent / 'prompts' / 'summarize_bullet_points_prompt.txt'
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def summarize_reasonings_batch(reasonings_dict):
    """
    Send all reasonings to Gemini in one call and get back summarized versions.

    Args:
        reasonings_dict: Dict with keys like "nhl_0", "nba_1" mapping to reasoning text

    Returns:
        Dict with same keys mapping to summarized bullet points
    """
    if not reasonings_dict:
        return {}

    # Configure Gemini
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("⚠️  Warning: GOOGLE_API_KEY not found, skipping reasoning summarization")
        return {}

    try:
        client = genai.Client(api_key=api_key)

        # Build the batch prompt
        base_prompt = load_summarize_prompt()

        # Create a batch request with all reasonings
        batch_request = "I have multiple NHL/NBA betting analyses to convert to bullet points. Please process each one and return them with the same identifiers.\n\n"

        for key, reasoning in reasonings_dict.items():
            batch_request += f"=== {key} ===\n{reasoning}\n\n"

        batch_request += "\n\nPlease return the summarized bullet points for each analysis using the EXACT same identifier (e.g., === nhl_0 ===) followed by the bullet points, then a blank line before the next one."

        # Combine base prompt with batch request
        full_prompt = f"{base_prompt}\n\n{batch_request}"

        print(f"📝 Summarizing {len(reasonings_dict)} reasonings with Gemini...")
        models_to_try = [
            "models/gemini-2.5-flash",
            "models/gemini-2.0-flash",
            "models/gemini-2.0-flash-lite",
            "models/gemini-2.5-flash-lite",
        ]
        response_text = None
        retry_waits = [30, 60]
        for model in models_to_try:
            max_retries = len(retry_waits) + 1
            for attempt in range(max_retries):
                try:
                    print(f"🤖 Trying {model}...")
                    response = client.models.generate_content(
                        model=model,
                        contents=full_prompt,
                    )
                    response_text = response.text
                    break
                except genai.errors.ServerError as e:
                    if "503" in str(e) or "UNAVAILABLE" in str(e):
                        if attempt < max_retries - 1:
                            wait_time = retry_waits[attempt]
                            print(f"⚠️ {model} 503 error. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            print(f"⚠️ {model} still unavailable, trying next model...")
                            break
                    else:
                        raise
                except genai.errors.ClientError as e:
                    if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e):
                        print(f"⚠️ {model} quota exceeded, trying next model...")
                        break
                    else:
                        raise
            if response_text:
                break
        if not response_text:
            print("⚠️ All models unavailable, skipping summarization.")
            return {}

        # Parse the response back into individual summaries
        summaries = {}
        current_key = None
        current_lines = []

        for line in response_text.split('\n'):
            # Check if this is a new section identifier
            if line.strip().startswith('===') and line.strip().endswith('==='):
                # Save previous section if exists
                if current_key and current_lines:
                    summaries[current_key] = '\n'.join(current_lines).strip()

                # Extract the key
                current_key = line.strip().replace('===', '').strip()
                current_lines = []
            else:
                if current_key is not None:
                    current_lines.append(line)

        # Save the last section
        if current_key and current_lines:
            summaries[current_key] = '\n'.join(current_lines).strip()

        print(f"✅ Received {len(summaries)} summaries from Gemini")
        return summaries

    except Exception as e:
        print(f"⚠️  Error summarizing reasonings: {e}")
        return {}


def apply_summaries_to_picks(nhl_picks, nba_picks, summaries):
    """
    Apply summarized reasonings to the picks.

    Args:
        nhl_picks: List of NHL pick dictionaries
        nba_picks: List of NBA pick dictionaries
        summaries: Dict of summarized reasonings with keys like "nhl_0", "nba_1"

    Returns:
        Tuple of (updated_nhl_picks, updated_nba_picks)
    """
    # Update NHL picks
    for i, pick in enumerate(nhl_picks):
        key = f"nhl_{i}"
        if key in summaries:
            pick['reasoning'] = summaries[key]

    # Update NBA picks
    for i, pick in enumerate(nba_picks):
        key = f"nba_{i}"
        if key in summaries:
            pick['reasoning'] = summaries[key]

    return nhl_picks, nba_picks


def main():
    """Main function to generate daily picks table."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate daily picks table')
    parser.add_argument('--results-only', action='store_true',
                       help='Generate empty picks page with "come back at 3pm" message')
    args = parser.parse_args()

    if args.results_only:
        print("Generating daily picks page with 'come back at 3pm' message...")
        # Generate empty picks
        nhl_picks = []
        nba_picks = []
    else:
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

        # Gather all reasonings for summarization
        reasonings_dict = {}
        for i, pick in enumerate(nhl_picks):
            reasonings_dict[f"nhl_{i}"] = pick['reasoning']
        for i, pick in enumerate(nba_picks):
            reasonings_dict[f"nba_{i}"] = pick['reasoning']

        # Summarize all reasonings in one Gemini call
        if reasonings_dict:
            summaries = summarize_reasonings_batch(reasonings_dict)
            if summaries:
                nhl_picks, nba_picks = apply_summaries_to_picks(nhl_picks, nba_picks, summaries)
        else:
            print("ℹ️  No picks found to summarize")

    # Generate JavaScript data
    js_data = generate_javascript_data(nhl_picks, nba_picks)

    # Update HTML file
    html_path = 'docs/daily-picks.html'
    if update_html_with_data(html_path, js_data):
        if args.results_only:
            print(f"✅ Successfully updated {html_path} with 'come back at 3pm' message")
        else:
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
