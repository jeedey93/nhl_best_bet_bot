import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nhl_games import get_todays_nhl_games
from data.nba_games import get_todays_nba_games
from data.odds import get_odds


def format_time(iso_time):
    """Convert ISO time to Montreal time."""
    dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    montreal_time = dt.astimezone(ZoneInfo('America/Toronto'))
    return montreal_time.strftime("%I:%M %p ET")


def generate_games_page():
    """Generate today's games page."""

    # Get today's date
    now = datetime.now(ZoneInfo('America/Toronto'))
    today_str = now.strftime("%A, %B %d, %Y").replace(" 0", " ")

    content = "<!DOCTYPE html>\n"
    content += "<html lang='en'>\n"
    content += "<head>\n"
    content += "<meta charset='UTF-8'>\n"
    content += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
    content += "<title>Today's Games - Parieur Discipliné</title>\n"
    content += "<link rel='icon' type='image/png' href='parieur_discipline_icon_1024.png'>\n"
    content += "</head>\n"
    content += "<body>\n\n"

    # Fixed Navigation Bar (same as main page)
    content += "<nav style='position: fixed; top: 0; left: 0; right: 0; z-index: 1000; background: linear-gradient(135deg, #2c5aa0 0%, #1e3a8a 100%); box-shadow: 0 2px 10px rgba(0,0,0,0.1); backdrop-filter: blur(10px);'>\n"
    content += "<div style='max-width: 1600px; margin: 0 auto; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between;'>\n"
    content += "<div style='display: flex; align-items: center; gap: 15px;'>\n"
    content += "<img src='parieur_discipline_icon_1024.png' alt='Logo' style='width: 35px; height: 35px; border-radius: 50%;' />\n"
    content += "<span style='color: white; font-weight: 700; font-size: 1.1em;'>Parieur Discipliné</span>\n"
    content += "</div>\n"
    content += "<div style='display: flex; gap: 5px; flex-wrap: wrap;'>\n"
    content += "<a href='index.html' style='color: white; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 0.9em; transition: background 0.2s;' onmouseover='this.style.background=\"rgba(255,255,255,0.15)\"' onmouseout='this.style.background=\"transparent\"'>Home</a>\n"
    content += "<a href='games.html' style='color: white; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 0.9em; background: rgba(255,255,255,0.2);'>Today's Games</a>\n"
    content += "</div>\n"
    content += "</div>\n"
    content += "</nav>\n"
    content += "<div style='height: 60px;'></div>\n"

    # CSS
    content += "<style>\n"
    content += "* { margin: 0; padding: 0; box-sizing: border-box; }\n"
    content += "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #1a1a1a; }\n"
    content += ".container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }\n"
    content += ".header { text-align: center; margin-bottom: 40px; }\n"
    content += ".header h1 { font-size: 2.5em; color: #2c5aa0; margin-bottom: 10px; }\n"
    content += ".header p { color: #6b7280; font-size: 1.1em; }\n"
    content += ".sport-section { margin-bottom: 50px; }\n"
    content += ".sport-title { font-size: 2em; color: #1e3a8a; margin-bottom: 20px; border-bottom: 3px solid #4a90e2; padding-bottom: 10px; display: flex; align-items: center; gap: 10px; }\n"
    content += ".game-card { background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: transform 0.2s, box-shadow 0.2s; }\n"
    content += ".game-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.12); }\n"
    content += ".game-time { color: #6b7280; font-size: 0.9em; margin-bottom: 15px; }\n"
    content += ".matchup { font-size: 1.3em; font-weight: 700; color: #1e3a8a; margin-bottom: 20px; }\n"
    content += ".odds-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }\n"
    content += ".odds-card { background: #f8fafc; border-radius: 8px; padding: 15px; border: 1px solid #e5e7eb; }\n"
    content += ".odds-label { font-size: 0.85em; color: #6b7280; text-transform: uppercase; font-weight: 600; margin-bottom: 8px; }\n"
    content += ".odds-value { font-size: 1.2em; font-weight: 700; color: #2c5aa0; }\n"
    content += ".no-games { text-align: center; padding: 40px; color: #6b7280; font-size: 1.1em; }\n"
    content += "@media (max-width: 768px) { .header h1 { font-size: 1.8em; } .sport-title { font-size: 1.5em; } .matchup { font-size: 1.1em; } }\n"
    content += "</style>\n\n"

    content += "<div class='container'>\n"
    content += "<div class='header'>\n"
    content += "<h1>📅 Today's Games</h1>\n"
    content += f"<p>{today_str}</p>\n"
    content += "</div>\n"

    # NHL Games
    content += "<div class='sport-section'>\n"
    content += "<div class='sport-title'>🏒 NHL Games</div>\n"

    nhl_games = get_todays_nhl_games()
    nhl_odds = get_odds("icehockey_nhl")

    if nhl_games:
        for game in nhl_games:
            away_team = game['awayTeam']['name']['default']
            home_team = game['homeTeam']['name']['default']
            game_time = format_time(game['startTimeUTC'])

            content += "<div class='game-card'>\n"
            content += f"<div class='game-time'>🕐 {game_time}</div>\n"
            content += f"<div class='matchup'>{away_team} @ {home_team}</div>\n"

            # Find odds for this game
            game_odds = None
            for odds_game in nhl_odds:
                if home_team in odds_game['home_team'] or away_team in odds_game['away_team']:
                    game_odds = odds_game
                    break

            if game_odds:
                content += "<div class='odds-grid'>\n"

                # Moneyline
                if 'h2h' in game_odds['markets']:
                    h2h = game_odds['markets']['h2h']
                    content += "<div class='odds-card'>\n"
                    content += "<div class='odds-label'>Moneyline</div>\n"
                    content += f"<div class='odds-value'>{away_team[:15]}: {h2h['away']}</div>\n"
                    content += f"<div class='odds-value'>{home_team[:15]}: {h2h['home']}</div>\n"
                    content += "</div>\n"

                # Totals
                if 'totals' in game_odds['markets']:
                    totals = game_odds['markets']['totals']
                    content += "<div class='odds-card'>\n"
                    content += "<div class='odds-label'>Total</div>\n"
                    content += f"<div class='odds-value'>Over {totals['point']}: {totals['over']}</div>\n"
                    content += f"<div class='odds-value'>Under {totals['point']}: {totals['under']}</div>\n"
                    content += "</div>\n"

                # Spreads
                if 'spreads' in game_odds['markets']:
                    spreads = game_odds['markets']['spreads']
                    content += "<div class='odds-card'>\n"
                    content += "<div class='odds-label'>Spread</div>\n"
                    content += f"<div class='odds-value'>{away_team[:15]} {spreads['away_point']:+.1f}: {spreads['away']}</div>\n"
                    content += f"<div class='odds-value'>{home_team[:15]} {spreads['home_point']:+.1f}: {spreads['home']}</div>\n"
                    content += "</div>\n"

                content += "</div>\n"

            content += "</div>\n"
    else:
        content += "<div class='no-games'>No NHL games scheduled for today</div>\n"

    content += "</div>\n"

    # NBA Games
    content += "<div class='sport-section'>\n"
    content += "<div class='sport-title'>🏀 NBA Games</div>\n"

    nba_games = get_todays_nba_games()
    nba_odds = get_odds("basketball_nba")

    if nba_games:
        for game in nba_games:
            away_team = game['awayTeam']['teamName']
            home_team = game['homeTeam']['teamName']
            game_time = format_time(game['gameTimeUTC'])

            content += "<div class='game-card'>\n"
            content += f"<div class='game-time'>🕐 {game_time}</div>\n"
            content += f"<div class='matchup'>{away_team} @ {home_team}</div>\n"

            # Find odds for this game
            game_odds = None
            for odds_game in nba_odds:
                if home_team in odds_game['home_team'] or away_team in odds_game['away_team']:
                    game_odds = odds_game
                    break

            if game_odds:
                content += "<div class='odds-grid'>\n"

                # Moneyline
                if 'h2h' in game_odds['markets']:
                    h2h = game_odds['markets']['h2h']
                    content += "<div class='odds-card'>\n"
                    content += "<div class='odds-label'>Moneyline</div>\n"
                    content += f"<div class='odds-value'>{away_team[:15]}: {h2h['away']}</div>\n"
                    content += f"<div class='odds-value'>{home_team[:15]}: {h2h['home']}</div>\n"
                    content += "</div>\n"

                # Totals
                if 'totals' in game_odds['markets']:
                    totals = game_odds['markets']['totals']
                    content += "<div class='odds-card'>\n"
                    content += "<div class='odds-label'>Total</div>\n"
                    content += f"<div class='odds-value'>Over {totals['point']}: {totals['over']}</div>\n"
                    content += f"<div class='odds-value'>Under {totals['point']}: {totals['under']}</div>\n"
                    content += "</div>\n"

                # Spreads
                if 'spreads' in game_odds['markets']:
                    spreads = game_odds['markets']['spreads']
                    content += "<div class='odds-card'>\n"
                    content += "<div class='odds-label'>Spread</div>\n"
                    content += f"<div class='odds-value'>{away_team[:15]} {spreads['away_point']:+.1f}: {spreads['away']}</div>\n"
                    content += f"<div class='odds-value'>{home_team[:15]} {spreads['home_point']:+.1f}: {spreads['home']}</div>\n"
                    content += "</div>\n"

                content += "</div>\n"

            content += "</div>\n"
    else:
        content += "<div class='no-games'>No NBA games scheduled for today</div>\n"

    content += "</div>\n"
    content += "</div>\n"
    content += "</body>\n"
    content += "</html>\n"

    # Write to file
    output_file = "docs/games.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Generated {output_file}")


if __name__ == "__main__":
    generate_games_page()
