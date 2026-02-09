import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

from data.nhl_games import get_games_today
from data.odds import get_odds, match_odds_to_games

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

# Pull your hardcoded date games
games = get_games_today()

if not games:
    print("No NHL Games today")
else:
    odds_data = get_odds()
    matched = match_odds_to_games(games, odds_data)

    results_text = ""
    for g in matched:
        line = (
            f"{g['away']} @ {g['home']}\n"
            f"Home odds: {g['home_odds']}, Away odds: {g['away_odds']}, O/U: {g['over_under']}\n"
            "------\n"
        )
        print(line, end="")
        results_text += line

    if results_text:
        summary = analyze_results(results_text)
        print("\nAI Analysis Summary:")
        print(summary)
