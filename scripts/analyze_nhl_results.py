import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.nhl_games import get_games_yesterday
from google import genai
from google.genai import types
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

def analyze_results_with_actuals(results_text, actuals_text, summary_date):
    api_key = os.environ["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)
    prompt = f"""
You are a disciplined NHL betting analyst. Review the AI's predictions against the actual game results for {summary_date}.

CRITICAL: Understand the difference between PUSH, WIN, and LOSS:
- PUSH: When the result EXACTLY equals the line. The stake is returned. This is NOT a loss, NOT a win. It's neutral.
  Example: Over 6.0 with exactly 6 total goals = PUSH
  Example: Team -1.5 and team wins by exactly 1.5 (not possible in hockey due to whole goals)
- WIN: When the bet wins
- LOSS: When the bet loses (but NOT when it's a push!)

For each recommended play:
- List the play header WITH ODDS AND CONFIDENCE (e.g., **Team ML vs Team @ odds - Confidence: High, Units: 1.5u**).
- IMPORTANT: Always include the odds AND confidence/units in the bet header
  Example: **Tampa Bay Lightning vs Minnesota Wild Over 6.0 @ 2.18 - Confidence: High, Units: 1.5u**
- Show the actual result in the format: Actual Result: <away> <away_score> @ <home> <home_score> (Total goals: <total>)
- State the outcome: WIN, LOSS, or PUSH, with a short reason.
  - If the result EXACTLY equals the line, you MUST mark it as **PUSH** (not LOSS).
  - For totals: If the line is 6.0 and total goals is exactly 6, it's a **PUSH** (stake returned, no profit/loss).
  - For spreads: If the margin exactly equals the spread.

IMPORTANT: In the summary section, you MUST always include Total Pushes, even if it's 0.

After all plays, output a summary section:
---
Summary of AI Prediction Performance:
- Total Wins: <number>
- Total Losses: <number>
- Total Pushes: <number>

Use this exact format:

As a disciplined NHL betting analyst, I have reviewed the AI's predictions against the actual game results for {summary_date}.

Here's the breakdown:

1.  **<PLAY HEADER WITH @ ODDS AND CONFIDENCE>**
    *   Actual Result: <away> <away_score> @ <home> <home_score> (Total goals: <total>)
    *   Outcome: **WIN**, **LOSS**, or **PUSH** (<short reason>)

---

**Summary of AI Prediction Performance:**

*   **Total Wins: <number>**
*   **Total Losses: <number>**
*   **Total Pushes: <number>**

AI Predictions:
{results_text}

Actual Results:
{actuals_text}
"""
    models_to_try = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.5-flash-lite",
    ]
    retry_waits = [30, 60]

    for model in models_to_try:
        max_retries = len(retry_waits) + 1
        for attempt in range(max_retries):
            try:
                print(f"🤖 Trying {model}...")
                response = client.models.generate_content(
                    model=model,
                    contents=types.Part.from_text(text=prompt),
                )
                return response.candidates[0].content.parts[0].text
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

    print("❌ All Gemini models unavailable. Cancelling workflow.")
    sys.exit(1)

# Read the predictions file
yesterday = (date.today() - timedelta(days=1)).isoformat()
predictions_file = f"data/predictions/nhl/nhl_daily_predictions_{yesterday}.txt"
with open(predictions_file, "r") as f:
    predictions_text = f.read()

# Get and format actual results
games = get_games_yesterday()
actuals_text = "\n".join(
    f"{g['away']} {g['away_score']} @ {g['home']} {g['home_score']} (Total goals: {g['away_score'] + g['home_score']})" for g in games
)

# Analyze
summary_date = yesterday
summary = analyze_results_with_actuals(predictions_text, actuals_text, summary_date)

today_str = date.today().isoformat()
results_folder = os.path.join("data", "bot_results", "nhl")
os.makedirs(results_folder, exist_ok=True)
filename = os.path.join(results_folder, f"nhl_daily_results_{today_str}.txt")

# Write summary to file
with open(filename, "w") as out_f:
    out_f.write(summary)

print(summary)
