#!/usr/bin/env python3
"""
Generate complete email body with picks and reasoning.
Single script that combines pick extraction and reasoning generation.
"""

import argparse
import hashlib
import hmac
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote


def extract_picks_from_html(html_path):
    """Extract picks data from the JavaScript in daily-picks.html"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the picks object in JavaScript
    picks_match = re.search(r'const picks = \{(.*?)\};', content, re.DOTALL)
    if not picks_match:
        return None, None

    picks_text = picks_match.group(1)

    # Extract NHL picks
    nhl_section = re.search(r'nhl: \[(.*?)\],', picks_text, re.DOTALL)
    nba_section = re.search(r'nba: \[(.*?)\]', picks_text, re.DOTALL)

    def parse_pick_objects(section_text):
        """Parse individual pick objects from JavaScript"""
        picks = []
        # Find all pick objects
        pick_pattern = r'\{(.*?)\}'
        for match in re.finditer(pick_pattern, section_text, re.DOTALL):
            pick_obj = match.group(1)

            # Extract fields
            pick_data = {}

            # Game
            game_match = re.search(r"game: '([^']+)'", pick_obj)
            if game_match:
                pick_data['game'] = game_match.group(1)

            # Pick
            pick_match = re.search(r"pick: '([^']+)'", pick_obj)
            if pick_match:
                pick_data['pick'] = pick_match.group(1)

            # Odds
            odds_match = re.search(r"odds: '([^']+)'", pick_obj)
            if odds_match:
                pick_data['odds'] = odds_match.group(1)

            # Win Probability
            prob_match = re.search(r"winProbability: '([^']*)'", pick_obj)
            if prob_match:
                pick_data['win_probability'] = prob_match.group(1)

            # Reasoning (handle backticks and newlines)
            reasoning_match = re.search(r"reasoning: `([^`]*)`", pick_obj, re.DOTALL)
            if reasoning_match:
                pick_data['reasoning'] = reasoning_match.group(1).strip()

            if pick_data:
                picks.append(pick_data)

        return picks

    nhl_picks = []
    nba_picks = []

    if nhl_section:
        nhl_picks = parse_pick_objects(nhl_section.group(1))

    if nba_section:
        nba_picks = parse_pick_objects(nba_section.group(1))

    return nhl_picks, nba_picks


def extract_picks_from_dual_bet(dual_bet_path):
    """Extract picks and inline reasoning from dual_bet_of_the_day.txt"""
    if not os.path.exists(dual_bet_path):
        return None, None

    with open(dual_bet_path, 'r', encoding='utf-8') as f:
        content = f.read()

    def _win_prob_from_prediction_file(sport, pick_text, odds):
        """Find today's prediction file and extract the win probability for this pick."""
        from datetime import date
        today = date.today().isoformat()
        pred_dir = Path(f'data/predictions/{sport}')
        candidate = pred_dir / f'{sport}_daily_predictions_{today}.txt'
        if not candidate.exists():
            files = sorted(pred_dir.glob(f'{sport}_daily_predictions_*.txt'))
            candidate = files[-1] if files else None
        if not candidate:
            return ''
        text = candidate.read_text(encoding='utf-8')
        lines = text.splitlines()
        # Find the line that has both a team name from pick_text AND the odds value
        pick_words = [w for w in pick_text.lower().split() if len(w) > 3][:3]
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if str(odds) in line and any(w in line_lower for w in pick_words):
                # Found the pick line — search forward for win probability
                for j in range(i, min(i + 8, len(lines))):
                    m = re.search(r'Win Probability[:\s]+(\d+(?:\.\d+)?)\s*%', lines[j], re.IGNORECASE)
                    if m:
                        return m.group(1)
        return ''

    def parse_section(header_pattern, accent_color, sport):
        m = re.search(header_pattern, content)
        if not m:
            return None

        pick_line = m.group(0)
        icon_m = re.search(r'🏒|🏀', pick_line)
        after_icon = pick_line[icon_m.end():].strip() if icon_m else pick_line
        odds_match = re.search(r'@\s*([\d.]+)', after_icon)
        if not odds_match:
            return None
        odds = odds_match.group(1)
        pick_text = after_icon[:odds_match.start()].strip().rstrip('vs').strip()

        # Collect reasoning lines between this header and the next ⸻
        header_end = m.end()
        separator = content.find('⸻', header_end)
        reasoning_block = content[header_end:separator if separator != -1 else len(content)]

        reasoning_lines = []
        for line in reasoning_block.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('Two sports') or line.startswith('We follow'):
                break
            if re.match(r'Confidence Level:', line):
                continue
            reasoning_lines.append(line)

        win_prob = _win_prob_from_prediction_file(sport, pick_text, odds)

        return {
            'text': pick_text,
            'odds': odds,
            'html': f"{pick_text}<br/><span style='font-size: 14px; color: {accent_color};'>@{odds}</span>",
            'reasoning_lines': reasoning_lines,
            'win_probability': win_prob,
        }

    nhl_pick = parse_section(r'PICK.*?NHL.*?🏒.+', '#93c5fd', 'nhl')
    nba_pick = parse_section(r'PICK.*?NBA.*?🏀.+', '#fed7aa', 'nba')

    return nhl_pick, nba_pick


def match_pick_to_reasoning(dual_pick, all_picks):
    """Find the matching pick in all_picks and return its reasoning data"""
    if not dual_pick:
        return None

    pick_text = dual_pick['text'].lower()

    for pick in all_picks:
        # Check if this pick matches
        pick_name = pick.get('pick', '').lower()
        game = pick.get('game', '').lower()

        team_match = any(team.strip().lower() in pick_text for team in game.split('@') if team.strip())
        name_match = pick_name in pick_text

        if not (name_match or team_match):
            continue

        # Prefer odds match, but fall back to any name/team match
        try:
            odds_diff = abs(float(pick.get('odds', '0')) - float(dual_pick['odds']))
            if odds_diff <= 0.05:
                return pick
        except ValueError:
            pass

        if name_match or team_match:
            return pick

    return None


def generate_reasoning_html(pick_data):
    """Generate HTML for reasoning section in email"""
    if not pick_data:
        return ""

    reasoning_lines = pick_data.get('reasoning_lines') or []
    win_prob = pick_data.get('win_probability', '')

    # Fall back to parsing the 'reasoning' string field (used when called with HTML-sourced pick)
    if not reasoning_lines:
        reasoning = pick_data.get('reasoning', '')
        if not reasoning:
            return ""
        reasoning_lines = [l.strip() for l in reasoning.strip().split('\n') if l.strip()]

    bullets_html = ""
    for line in reasoning_lines:
        if line.startswith('•') or line.startswith('-'):
            line = line[1:].strip()

        if '**' in line:
            parts = re.split(r'\*\*(.*?)\*\*', line)
            if len(parts) >= 2:
                emoji = parts[0].strip()
                title = parts[1].strip()
                description = parts[2].strip() if len(parts) > 2 else ""

                bullets_html += f"""
                                    <table border="0" cellpadding="0" cellspacing="0" style="margin: 0 auto 16px auto; width: 100%; max-width: 450px;">
                                      <tr>
                                        <td align="center" style="padding: 0 15px;">
                                          <p style="margin: 0 0 6px 0; color: #ffffff; font-size: 13px; font-weight: bold; font-family: Arial, sans-serif; line-height: 1.3; text-align: center;"><span style="font-size: 20px; vertical-align: middle; margin-right: 6px;">{emoji}</span>{title}</p>
                                          <p style="margin: 0; color: rgba(255,255,255,0.85); font-size: 12px; font-family: Arial, sans-serif; line-height: 1.5; text-align: center;">{description}</p>
                                        </td>
                                      </tr>
                                    </table>"""
        else:
            if line:
                bullets_html += f"""
                                    <p style="margin: 0 auto 12px auto; width: 100%; max-width: 450px; padding: 0 15px; color: rgba(255,255,255,0.85); font-size: 12px; font-family: Arial, sans-serif; line-height: 1.5; text-align: center; box-sizing: border-box;">{line}</p>"""

    if not bullets_html:
        return ""

    prob_html = ""
    if win_prob:
        prob_html = f"""
                                <table border="0" cellpadding="0" cellspacing="0" style="margin: 0 auto 15px auto; width: 100%; max-width: 450px; padding: 12px; background-color: rgba(255,255,255,0.1); border-radius: 8px; box-sizing: border-box;">
                                  <tr>
                                    <td align="center">
                                      <p style="margin: 0; color: #ffffff; font-size: 12px; font-weight: bold; font-family: Arial, sans-serif; text-align: center;">📊 Win Probability: <span style="font-size: 16px;">{win_prob}%</span></p>
                                    </td>
                                  </tr>
                                </table>"""

    html = f"""
                          <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-top: 18px; padding-top: 18px; border-top: 2px solid rgba(255,255,255,0.15);">
                            <tr>
                              <td align="center">
                                {prob_html}
                                <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                  <tr>
                                    <td align="center">
                                      <p style="margin: 0 0 12px 0; color: rgba(255,255,255,0.7); font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; font-family: Arial, sans-serif;">WHY THIS BET</p>
                                      {bullets_html}
                                    </td>
                                  </tr>
                                </table>
                              </td>
                            </tr>
                          </table>"""

    return html


def main():
    """Main function"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', default='')
    parser.add_argument('--token', default='')
    parser.add_argument('--generate-token', action='store_true')
    args = parser.parse_args()

    # Token generation mode: print HMAC token for a given email and exit
    if args.generate_token and args.email:
        secret = os.environ.get('UNSUBSCRIBE_SECRET', '')
        token = hmac.new(secret.encode(), args.email.lower().strip().encode(), hashlib.sha256).hexdigest()
        print(token)
        return 0

    # Paths
    html_path = 'docs/daily-picks.html'
    dual_bet_path = 'data/predictions/dual_bet_of_the_day.txt'
    email_template_path = '.github/workflows/email_body.html'
    output_path = '/tmp/email_body.html'

    print("🎯 Extracting picks and reasoning from dual_bet_of_the_day.txt...")
    nhl_pick_info, nba_pick_info = extract_picks_from_dual_bet(dual_bet_path)

    nhl_pick_html = nhl_pick_info['html'] if nhl_pick_info else "Check website for today's pick"
    nba_pick_html = nba_pick_info['html'] if nba_pick_info else "Check website for today's pick"

    print(f"NHL Pick: {nhl_pick_html[:80]}...")
    print(f"NBA Pick: {nba_pick_html[:80]}...")

    nhl_reasoning_html = generate_reasoning_html(nhl_pick_info) if nhl_pick_info else ""
    nba_reasoning_html = generate_reasoning_html(nba_pick_info) if nba_pick_info else ""

    if nhl_reasoning_html:
        print(f"✅ NHL reasoning generated ({len(nhl_pick_info.get('reasoning_lines', []))} bullet(s))")
    else:
        print("⚠️  No NHL reasoning found")

    if nba_reasoning_html:
        print(f"✅ NBA reasoning generated ({len(nba_pick_info.get('reasoning_lines', []))} bullet(s))")
    else:
        print("⚠️  No NBA reasoning found")

    # Read email template
    with open(email_template_path, 'r', encoding='utf-8') as f:
        email_html = f.read()

    # Replace placeholders
    email_html = email_html.replace('${NHL_PICK}', nhl_pick_html)
    email_html = email_html.replace('${NBA_PICK}', nba_pick_html)
    email_html = email_html.replace('${NHL_REASONING}', nhl_reasoning_html)
    email_html = email_html.replace('${NBA_REASONING}', nba_reasoning_html)

    # Remove card blocks for missing picks
    import re
    if not nhl_pick_info:
        email_html = re.sub(r'<!-- NHL_CARD_START -->.*?<!-- NHL_CARD_END -->', '', email_html, flags=re.DOTALL)
    else:
        email_html = email_html.replace('<!-- NHL_CARD_START -->', '').replace('<!-- NHL_CARD_END -->', '')
    if not nba_pick_info:
        email_html = re.sub(r'<!-- NBA_CARD_START -->.*?<!-- NBA_CARD_END -->', '', email_html, flags=re.DOTALL)
    else:
        email_html = email_html.replace('<!-- NBA_CARD_START -->', '').replace('<!-- NBA_CARD_END -->', '')

    if args.email and args.token:
        unsub_url = f"https://parieurdiscipline.com/api/unsubscribe?email={quote(args.email)}&token={args.token}"
        email_html = email_html.replace('${UNSUBSCRIBE_URL}', unsub_url)

    # Note: Yesterday banner will be replaced by bash script
    # We keep the placeholder for now

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(email_html)

    print(f"\n✅ Email body generated at {output_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
