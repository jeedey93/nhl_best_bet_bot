import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from data.odds import get_nba_odds
from datetime import date

load_dotenv()

odds = get_nba_odds()
results_text = ""

if not odds:
    print("No NBA games today")
else:
    for game in odds:
        home_odds = None
        away_odds = None
        ou = None
        ou_over_odds = None
        ou_under_odds = None
        for market in game['bookmakers'][0]['markets']:
            if market['key'] == 'h2h':
                for outcome in market['outcomes']:
                    if outcome['name'] == game['home_team']:
                        home_odds = outcome['price']
                    elif outcome['name'] == game['away_team']:
                        away_odds = outcome['price']
            elif market['key'] == 'totals':
                for outcome in market['outcomes']:
                    if outcome['name'] == 'Over':
                        ou = outcome['point']
                        ou_over_odds = outcome['price']
                    elif outcome['name'] == 'Under':
                        ou_under_odds = outcome['price']
        line = (
            f"{game['home_team']} vs {game['away_team']}\n"
            f"Home odds: {home_odds}, Away odds: {away_odds}, "
            f"O/U: {ou} (Over odds: {ou_over_odds}, Under odds: {ou_under_odds})\n"
            "------\n"
        )
        results_text += line

    print("NBA Matchups and Odds:")
    print(results_text)
