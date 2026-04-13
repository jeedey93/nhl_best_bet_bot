import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.nba_games import get_nba_games_yesterday
from datetime import date, timedelta
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def analyze_results_with_actuals(results_text, actuals_text, date_str):
    api_key = os.environ["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)
    prompt = f"""
You are a disciplined NBA betting analyst. Your job is to review the AI's predictions against the actual game results for {date_str}.

CRITICAL: Understand the difference between PUSH, WIN, and LOSS:
- PUSH: When the result EXACTLY equals the line. The stake is returned. This is NOT a loss, NOT a win. It's neutral.
  Example: Over 232.0 with exactly 232 total points = PUSH
  Example: Team -3.0 and team wins by exactly 3 points = PUSH
- WIN: When the bet wins
- LOSS: When the bet loses (but NOT when it's a push!)

For each recommended play:
- Match the prediction to the actual game result.
- IMPORTANT: Always include the odds AND confidence/units in the bet header
  Example: **Los Angeles Lakers vs New Orleans Pelicans Under 243.0 @ 1.99 - Confidence: High, Units: 1.5u**
- For totals (over/under), compare the predicted total to the actual total points scored:
  - If the result exactly equals the line (e.g., Over 232.0 with exactly 232 points), it's a **PUSH** (not a loss!).
  - Otherwise, state if it is a WIN or LOSS (e.g., 'Outcome: WIN (234 is over 232.5)').
- For spreads, compare the predicted spread to the actual margin:
  - If the margin exactly equals the spread (e.g., -3.0 and team wins by exactly 3), it's a **PUSH** (not a loss!).
  - Otherwise, state if it is a WIN or LOSS (e.g., 'Outcome: WIN (Team covered -3.5)').
- For moneyline, state if the predicted team won or lost (e.g., 'Outcome: WIN (Team won)').
- For each play, output:
    * The bet header WITH ODDS AND CONFIDENCE (e.g., **Team vs Team @ odds - Confidence: High, Units: 1.5u**)
    * The actual result (e.g., 'TeamA 110 @ TeamB 105')
    * The outcome (WIN/LOSS/PUSH) with a short justification

IMPORTANT: In the summary section, you MUST always include Total Pushes, even if it's 0.

After all plays, output a summary section:
- Total Wins
- Total Losses
- Total Pushes

Format exactly as this example:

As a disciplined NBA betting analyst, I have reviewed the AI's predictions against the actual game results for {date_str}.

Here's the breakdown:

1.  **<BET HEADER WITH @ ODDS AND CONFIDENCE>**
    *   Actual Result: <AWAY> <AWAY_SCORE> @ <HOME> <HOME_SCORE>
    *   Outcome: **WIN/LOSS/PUSH** (<short justification>)

---

**Summary of AI Prediction Performance:**

*   **Total Wins: X**
*   **Total Losses: Y**
*   **Total Pushes: Z**

---

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
predictions_file = f"data/predictions/nba/nba_daily_predictions_{yesterday}.txt"
with open(predictions_file, "r") as f:
    results_text = f.read()

# Get and format actual results
games = get_nba_games_yesterday()
actuals_text = "\n".join(
    f"{g['away']} {g['away_score']} @ {g['home']} {g['home_score']}" for g in games
)

today_str = date.today().isoformat()
summary = analyze_results_with_actuals(results_text, actuals_text, yesterday)

results_folder = os.path.join("data", "bot_results", "nba")
os.makedirs(results_folder, exist_ok=True)
filename = os.path.join(results_folder, f"nba_daily_results_{today_str}.txt")

# Write summary to file
with open(filename, "w") as out_f:
    out_f.write(summary)

print(summary)
