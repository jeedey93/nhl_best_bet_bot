from data.nhl_games import get_games_today, get_games_yesterday

games = get_games_today()
games_yesterday = get_games_yesterday()

if not games_yesterday:
    print("No NHL games yesterday")
else:
    print("Yesterday's NHL games:")
    for g in games_yesterday:
        print(f"{g['away']} {g['away_score']} @ {g['home']} {g['home_score']}")

print()

if not games:
    print("No NHL games today")
else:
    print("Today's NHL games:")
    for g in games:
        print(f"{g['away']} @ {g['home']}")
