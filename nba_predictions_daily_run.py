import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from data.odds import get_nba_odds, match_nba_odds_to_games
from datetime import date
from data.odds import NBA_TEAM_NAME_MAP
from data.nba_games import get_nba_games_today


load_dotenv()

def analyze_results(results_text):
    api_key = os.environ["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)
    prompt = (
        "### ROLE\n"
        "You are an elite NBA Betting Analyst and Strategic Consultant. Your goal is to identify \"mispriced\" opportunities by blending cross-bookmaker odds analysis with advanced basketball situational theory.\n"
        "### ANALYSIS FRAMEWORK\n"
        "For each game in the provided data, execute the following three-step process:\n"
        "1. MARKET DISCREPANCY: Identify the \"best price\" available for a Side, Total, or Moneyline. Highlight where one bookmaker is a significant outlier compared to the consensus.\n"
        "2. SITUATIONAL EDGE: Evaluate the game based on:\n"
        "   - Schedule Fatigue: (e.g., Back-to-backs, 3-in-4 nights, or the \"post-road trip home opener\").\n"
        "   - Matchup Efficiency: How team Offensive/Defensive ratings and Pace interact (e.g., a fast-paced offense against a tired defense).\n"
        "   - Expected Value (EV): Only recommend plays where your qualitative analysis aligns with a quantitative price advantage.\n"
        "3. CONTRARIAN CHECK: Note if the value lies with the \"Sharp\" side (moving lines despite low public betting volume) or \"Public\" side.\n"
        "### CONSTRAINTS & OUTPUT\n"
        "- IGNORE: Games with spreads < 2 or \"coin-flip\" moneylines unless there is a massive Total (O/U) discrepancy.\n"
        "- RANKING: List plays from \"High Confidence\" to \"Leans.\"\n"
        "- FORMAT: Provide 2 sentences per play:\n"
        "    - Sentence 1: The numerical edge (Odds/Line variance).\n"
        "    - Sentence 2: Your strategic \"read\" on why the market is wrong (Fatigue, Matchup, or Sentiment).\n"
        "### DATA TO ANALYZE\n"
        f"{results_text}"
    )
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=types.Part.from_text(text=prompt),
        )
        return response.candidates[0].content.parts[0].text
    except genai.errors.ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e):
            return "AI analysis skipped: Gemini API quota exceeded."
        else:
            raise

today_str = date.today().isoformat()
predictions_folder = os.path.join("predictions", "nba")
os.makedirs(predictions_folder, exist_ok=True)
filename = os.path.join(predictions_folder, f"nba_daily_predictions_{today_str}.txt")

games = get_nba_games_today()
odds = get_nba_odds()

# Match structured odds to games
matched = match_nba_odds_to_games(games, odds, NBA_TEAM_NAME_MAP)
predictions_text = ""

with open(filename, "w") as f:
    f.write(f"Date: {today_str}\n\n")
    if not matched:
        f.write("No NBA games today or no odds available\n")
        print("No NBA games today or no odds available")
    else:
        print("NBA Matchups and Odds:")
        for g in matched:
            # Headline summary per game
            line = (
                f"{g['home']} vs {g['away']}\n"
                f"Home odds: {g.get('home_odds')}, Away odds: {g.get('away_odds')}, "
                f"O/U: {g.get('over_under')}\n"
                "------\n"
            )
            print(line, end="")
            f.write(line)
            predictions_text += line

            # Verbose per-bookmaker markets for the same game
            bm_list = g.get('bookmakers_odds', [])
            if bm_list:
                f.write("Bookmakers snapshot:\n")
                predictions_text += "Bookmakers snapshot:\n"
                for bm in bm_list:
                    title = bm.get('title') or bm.get('key') or 'Unknown Bookmaker'
                    f.write(f"  {title}\n")
                    predictions_text += f"  {title}\n"
                    for m in bm.get('markets', []):
                        mkey = m.get('key', 'unknown')
                        outcomes = m.get('outcomes', [])
                        # Render outcomes compactly: Name: price [point]
                        out_strs = []
                        for o in outcomes:
                            if isinstance(o, dict):
                                name = o.get('name', 'N/A')
                                price = o.get('price', 'N/A')
                                point = o.get('point')
                                if point is not None:
                                    out_strs.append(f"{name} @ {price} (point {point})")
                                else:
                                    out_strs.append(f"{name} @ {price}")
                            else:
                                out_strs.append(str(o))
                        line_bm = f"    {mkey}: " + ", ".join(out_strs) + "\n"
                        f.write(line_bm)
                        predictions_text += line_bm
                f.write("------\n")
                predictions_text += "------\n"

        if predictions_text:
            summary = analyze_results(predictions_text)
            f.write("\nAI Analysis Summary:\n")
            f.write(summary + "\n")
            print("\nAI Analysis Summary:")
            print(summary)

print(f"Saved NBA daily predictions to {filename}")
