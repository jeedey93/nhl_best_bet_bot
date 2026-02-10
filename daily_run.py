import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from data.nhl_games import get_games_today
from data.odds import get_nhl_odds, match_odds_to_games
from datetime import date
from data.odds import NHL_TEAM_NAME_MAP

load_dotenv()

def analyze_results(results_text):
    api_key = os.environ["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)
    prompt = (
        "You are a disciplined NHL betting analyst.\n"
        "Your job is to:\n"
        "- Ignore coin-flip games\n"
        "- Highlight only +EV spots\n"
        "- Rank plays by confidence\n"
        "- Explain in 1–2 sentences per play\n"
        f"\nAnalyze the following NHL betting results:\n{results_text}"
    )
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=types.Part.from_text(text=prompt),
    )
    return response.candidates[0].content.parts[0].text

games = get_games_today()
today_str = date.today().isoformat()
results_folder = "results"
os.makedirs(results_folder, exist_ok=True)
filename = os.path.join(results_folder, f"nhl_daily_results_{today_str}.txt")

with open(filename, "w") as f:
    f.write(f"Date: {today_str}\n\n")

    if not games:
        f.write("No NHL games today\n")
        print("No NHL games today")
    else:
        odds_data = get_nhl_odds()
        matched = match_odds_to_games(games, odds_data, NHL_TEAM_NAME_MAP)

        results_text = ""
        for g in matched:
            line = (
                f"{g['away']} @ {g['home']}\n"
                f"Home odds: {g['home_odds']}, Away odds: {g['away_odds']}, O/U: {g['over_under']}\n"
                "------\n"
            )
            f.write(line)
            results_text += line

        if results_text:
            summary = analyze_results(results_text)
            f.write("\nAI Analysis Summary:\n")
            f.write(summary + "\n")

print(f"Saved daily results to {filename}")
