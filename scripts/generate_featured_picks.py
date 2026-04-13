import os
import sys
import time
from pathlib import Path
# Try to load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # If dotenv is not installed, skip loading .env

# Path to the index.md file
INDEX_MD_PATH = "docs/index.md"
PREDICTIONS_DIR = "data/predictions"

# New: Path to latest predictions markdown
LATEST_PREDICTIONS_MD = "docs/index.md"  # Adjust if needed

def extract_bet_of_the_day(section_lines):
    """Extracts the Bet of the Day bet and justification from a section.

    Handles format like:
        🏆 **BET OF THE DAY**
        **Washington Capitals ML vs Utah Mammoth @ 1.83**
        Confidence Level: Medium, Units: 1u, Win Probability: 60%
        The Capitals are well-rested and have shown strong form...
        *Changes: ...*
    """
    bet = None
    justification_lines = []
    odds_value = None
    for i, line in enumerate(section_lines):
        stripped = line.strip()
        # Find the BET OF THE DAY header
        if '🏆' in stripped and 'BET OF THE DAY' in stripped.upper():
            # Find the bet line (next non-empty line, usually bolded)
            for j in range(i+1, len(section_lines)):
                bet_line = section_lines[j].strip()
                if bet_line:
                    # Remove bold markdown if present
                    bet = bet_line.strip('*').strip()
                    # Collect justification: all meaningful lines after the bet
                    # until we hit "Other Recommended Plays", a section break (---),
                    # or another header
                    for k in range(j+1, len(section_lines)):
                        jline = section_lines[k].strip()
                        # Stop at section boundaries
                        if jline.startswith('**Other Recommended Plays') or \
                           jline == '---' or \
                           jline.startswith('## ') or \
                           jline.startswith('### ') or \
                           jline.startswith('🏆'):
                            break
                        if jline:
                            # Extract odds from change notes before skipping
                            if jline.startswith('*Change') or jline.startswith('*Changes'):
                                # Try to extract odds: "to 1.77 (noon)" or "same as morning (1.67)"
                                import re
                                odds_match = re.search(r'to (\d+\.\d+) \(noon\)|same as morning \((\d+\.\d+)\)', jline)
                                if odds_match and not odds_value:
                                    odds_value = odds_match.group(1) or odds_match.group(2)
                                continue
                            justification_lines.append(jline)
                    break
            break

    # Join all justification lines into one text
    justification = ' '.join(justification_lines).strip() if justification_lines else None

    # Add odds to bet if found and not already present
    if odds_value and bet and '@' not in bet:
        bet = f"{bet} @ {odds_value}"

    return bet, justification

def get_latest_file(folder, prefix, ext="txt"):
    """Find the latest prediction file by date in filename (YYYY-MM-DD suffix)."""
    from glob import glob
    import re
    files = glob(os.path.join(folder, f"{prefix}_*.{ext}"))
    if not files:
        return None
    def file_date(f):
        m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(f))
        return m.group(1) if m else ''
    dated = [f for f in files if file_date(f)]
    if not dated:
        return max(files, key=os.path.getctime)
    return max(dated, key=file_date)

def get_sections_from_index():
    # Read from latest prediction files instead of index.md (which is now HTML)
    nhl_file = get_latest_file("data/predictions/nhl", "nhl_daily_predictions")
    nba_file = get_latest_file("data/predictions/nba", "nba_daily_predictions")

    nhl_section = []
    nba_section = []

    if nhl_file:
        with open(nhl_file, 'r', encoding='utf-8') as f:
            nhl_section = f.readlines()

    if nba_file:
        with open(nba_file, 'r', encoding='utf-8') as f:
            nba_section = f.readlines()

    return nhl_section, nba_section

def summarize_justifications(nhl_just, nba_just):
    """Call Gemini to convert paragraph justifications to emoji bullet points."""
    try:
        from google import genai
    except ImportError:
        print("⚠️  google-genai not installed, skipping summarization")
        return nhl_just, nba_just

    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("⚠️  GOOGLE_API_KEY not found, skipping summarization")
        return nhl_just, nba_just

    prompt_file = Path(__file__).parent.parent / 'prompts' / 'summarize_bullet_points_prompt.txt'
    with open(prompt_file, 'r', encoding='utf-8') as f:
        base_prompt = f.read()

    reasonings = {}
    if nhl_just:
        reasonings['nhl_0'] = nhl_just
    if nba_just:
        reasonings['nba_0'] = nba_just

    if not reasonings:
        return nhl_just, nba_just

    batch_request = "I have multiple NHL/NBA betting analyses to convert to bullet points. Please process each one and return them with the same identifiers.\n\n"
    for key, reasoning in reasonings.items():
        batch_request += f"=== {key} ===\n{reasoning}\n\n"
    batch_request += "\n\nPlease return the summarized bullet points for each analysis using the EXACT same identifier (e.g., === nhl_0 ===) followed by the bullet points, then a blank line before the next one."
    full_prompt = f"{base_prompt}\n\n{batch_request}"

    models_to_try = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.5-flash-lite",
    ]

    print(f"📝 Summarizing {len(reasonings)} featured pick reasonings with Gemini...")
    client = genai.Client(api_key=api_key)
    response_text = None
    retry_waits = [30, 60]
    for model in models_to_try:
        max_retries = len(retry_waits) + 1
        for attempt in range(max_retries):
            try:
                print(f"🤖 Trying {model}...")
                response = client.models.generate_content(model=model, contents=full_prompt)
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
        print("⚠️ All models unavailable, using original paragraphs.")
        return nhl_just, nba_just

    # Parse response back into individual summaries
    summaries = {}
    current_key = None
    current_lines = []
    for line in response_text.split('\n'):
        if line.strip().startswith('===') and line.strip().endswith('==='):
            if current_key and current_lines:
                summaries[current_key] = '\n'.join(current_lines).strip()
            current_key = line.strip().replace('===', '').strip()
            current_lines = []
        else:
            if current_key is not None:
                current_lines.append(line)
    if current_key and current_lines:
        summaries[current_key] = '\n'.join(current_lines).strip()

    print(f"✅ Received {len(summaries)} summaries from Gemini")

    summarized_nhl = summaries.get('nhl_0', nhl_just)
    summarized_nba = summaries.get('nba_0', nba_just)
    return summarized_nhl, summarized_nba



def build_gemini_prompt(nhl_bet, nhl_just, nba_bet, nba_just):
    """Builds the dual bet of the day prompt from a template file."""
    prompt_path = os.path.join("prompts", "bet_of_the_day.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()
    return template.format(
        nhl_bet=nhl_bet,
        nhl_just=nhl_just,
        nba_bet=nba_bet,
        nba_just=nba_just
    ).strip()


def save_to_file(content):
    """Save the content to a txt file in the predictions folder."""
    if not os.path.exists(PREDICTIONS_DIR):
        os.makedirs(PREDICTIONS_DIR)

    filename = "dual_bet_of_the_day.txt"
    filepath = os.path.join(PREDICTIONS_DIR, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Saved to: {filepath}")

def build_single_pick_prompt(sport, emoji, bet, just):
    """Build output when only one sport has a pick."""
    return f"""🔥 BET OF THE DAY 🤖📊 One pick. Full discipline. Same standard.
⸻
🎯 PICK – {sport} {emoji} {bet}
{just}
⸻
We follow the value. We protect the bankroll. Discipline > emotion. 🎯
""".strip()

def main():
    nhl_section, nba_section = get_sections_from_index()
    nhl_bet, nhl_just = extract_bet_of_the_day(nhl_section)
    nba_bet, nba_just = extract_bet_of_the_day(nba_section)

    if not nhl_bet and not nba_bet:
        print("No Bet of the Day entries found for today.")
        return

    if nhl_bet and nba_bet:
        # Both picks available — dual format
        nhl_just, nba_just = summarize_justifications(nhl_just, nba_just)
        output = build_gemini_prompt(nhl_bet, nhl_just, nba_bet, nba_just)
    elif nba_bet:
        # Only NBA pick
        print("ℹ️  No NHL pick today — outputting NBA only.")
        _, nba_just = summarize_justifications(None, nba_just)
        output = build_single_pick_prompt("NBA", "🏀", nba_bet, nba_just)
    else:
        # Only NHL pick
        print("ℹ️  No NBA pick today — outputting NHL only.")
        nhl_just, _ = summarize_justifications(nhl_just, None)
        output = build_single_pick_prompt("NHL", "🏒", nhl_bet, nhl_just)

    print(output)
    save_to_file(output)

if __name__ == "__main__":
    main()
