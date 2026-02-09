from data.nhl_games import get_games_today

games = get_games_today()

if not games:
    print("No NHL games today")
else:
    for g in games:
        print(f"{g['away']} @ {g['home']}")