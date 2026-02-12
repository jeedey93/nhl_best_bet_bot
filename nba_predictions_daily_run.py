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
        "You are an elite NBA Betting Analyst and Strategic Consultant. Blend cross-bookmaker odds analysis with situational basketball theory.\n"
        "\n"
        "### SELECTION PHILOSOPHY (Safety-First)\n"
        "- Only recommend plays where the decimal odds are at most 2.2 (reject any pick above 2.2).\n"
        "- Avoid extreme odd (long shots > 2.2) unless there is a compelling, cross-book consensus and clear EV rationale — but still do not recommend odds above 2.2.\n"
        "- If a game looks like a coin-flip, skip unless the price advantage is clear within the <= 2.2 constraint.\n"
        "\n"
        "### ANALYSIS FRAMEWORK\n"
        "For each game in the provided data, execute the following three-step process:\n"
        "1. MARKET DISCREPANCY: Identify the \"best price\" for Side/Total/Moneyline and highlight bookmaker outliers.\n"
        "2. SITUATIONAL EDGE: Evaluate schedule fatigue, momentum/player form, and matchup/points context.\n"
        "3. CONTRARIAN CHECK: Note if value aligns with sharp vs public dynamics.\n"
        "\n"
        "### CONSTRAINTS & OUTPUT\n"
        "- IGNORE: Games with spreads < 2 or coin-flip moneylines unless there is a massive Total (O/U) discrepancy.\n"
        "- RANKING: List plays from \"High Confidence\" to \"Leans.\"\n"
        "- EXPLANATION TONE: Short, plain-language, user-friendly.\n"
        "- FORMAT: Provide exactly 2 short sentences per play:\n"
        "    - Sentence 1: Summarize teams/players, fatigue, momentum, matchups, and points expectations.\n"
        "    - Sentence 2: A simple reason grounded in matchups and current player form.\n"
        "- Do not mention bookmakers, odds, price/line variance, EV, or market data in these two sentences.\n"
        "- NAMING: For ML plays, always use the format \"<TEAM> ML vs <OPPONENT>\" (e.g., \"New York Knicks ML vs Philadelphia 76ers\").\n"
        "- NAMING: For spreads/totals, always include the opponent using the format \"<TEAM> <MARKET> vs <OPPONENT> @ <ODDS>\" (e.g., \"Oklahoma City Thunder -6.5 vs Milwaukee Bucks @ 1.95\").\n"
        "\n"
        "### BET OF THE DAY\n"
        "After listing plays, choose the single highest-confidence pick that fits the <= 2.2 odds constraint and mark it clearly as: \n"
        "\n"
        "Bet of the Day: <TEAM or MARKET> vs <OPPONENT> @ <ODDS>\n"
        "Provide a reason in plain language focusing on form, matchup, and injuries; do not mention bookmakers, odds, price/line variance, EV, or market data.\n"
        "\n"
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
            # Headline summary per game (write to file + include in predictions_text)
            line = (
                f"{g['home']} vs {g['away']}\n"
                f"Home odds: {g.get('home_odds')}, Away odds: {g.get('away_odds')}, "
                f"O/U: {g.get('over_under')}\n"
                # Added spreads summary in the headline print
                f"Spreads: Home {g.get('spread_home_points')} ({g.get('spread_home_price')}), "
                f"Away {g.get('spread_away_points')} ({g.get('spread_away_price')})\n"
                "------\n"
            )
            print(line, end="")
            f.write(line)
            predictions_text += line

            # Verbose per-bookmaker markets ONLY for predictions_text (skip writing to file)
            bm_list = g.get('bookmakers_odds', [])
            if bm_list:
                predictions_text += "Bookmakers snapshot:\n"
                for bm in bm_list:
                    title = bm.get('title') or bm.get('key') or 'Unknown Bookmaker'
                    predictions_text += f"  {title}\n"
                    for m in bm.get('markets', []):
                        mkey = m.get('key', 'unknown')
                        outcomes = m.get('outcomes', [])
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
                        predictions_text += f"    {mkey}: " + ", ".join(out_strs) + "\n"
                predictions_text += "------\n"

        if predictions_text:
            summary = analyze_results(predictions_text)
            f.write("\nAI Analysis Summary:\n")
            f.write(summary + "\n")
            print("\nAI Analysis Summary:")
            print(summary)

print(f"Saved NBA daily predictions to {filename}")
