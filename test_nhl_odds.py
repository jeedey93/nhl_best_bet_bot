from data.odds import get_nhl_odds

odds = get_nhl_odds()

for game in odds:
    print(game["home_team"], "vs", game["away_team"])
    print(game["bookmakers"][0]["title"])
    for market in game["bookmakers"][0]["markets"]:
        print(market["key"], market["outcomes"])
    print("-----")
