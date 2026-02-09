from data.odds import get_odds

odds = get_odds()

# Just print the first 3 games to check
for game in odds[:3]:
    print(game["home_team"], "vs", game["away_team"])
    # Print the first bookmaker and its markets
    print(game["bookmakers"][0]["title"])
    for market in game["bookmakers"][0]["markets"]:
        print(market["key"], market["outcomes"])
    print("-----")