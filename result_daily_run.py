import os
from data.nhl_games import get_games_yesterday
from google import genai
from google.genai import types
from datetime import date
from dotenv import load_dotenv

load_dotenv()

def analyze_results_with_actuals(results_text, actuals_text):
    api_key = os.environ["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)
    prompt = (
        "You are a disciplined NHL betting analyst.\n"
        "You will:\n"
        "- Review the AI predictions and the actual game results\n"
        "- For each prediction, determine if it was a win or loss\n"
        "- Summarize the total number of wins and losses\n"
        "\nAI Predictions:\n"
        f"{results_text}\n"
        "\nActual Results:\n"
        f"{actuals_text}\n"
        "Return a summary of wins and losses."
    )
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=types.Part.from_text(text=prompt),
    )
    return response.candidates[0].content.parts[0].text

# Read the results file
yesterday = "2026-02-03"
result_file = f"results/nhl_daily_results_{yesterday}.txt"
with open(result_file, "r") as f:
    results_text = f.read()

# Get and format actual results
games = get_games_yesterday()
actuals_text = "\n".join(
    f"{g['away']} {g['away_score']} @ {g['home']} {g['home_score']}" for g in games
)

# Analyze
summary = analyze_results_with_actuals(results_text, actuals_text)

today_str = date.today().isoformat()
results_folder = "bot_results"
os.makedirs(results_folder, exist_ok=True)
filename = os.path.join(results_folder, f"nhl_daily_results_{today_str}.txt")

# Write summary to file
with open(filename, "w") as out_f:
    out_f.write(summary)
