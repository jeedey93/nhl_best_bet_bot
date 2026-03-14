import os
import re
from datetime import datetime

# Map team file names to full team names and abbreviations
TEAM_INFO = {
    'Avalanche': {'name': 'Colorado Avalanche', 'abbrev': 'COL'},
    'Blue_Jackets': {'name': 'Columbus Blue Jackets', 'abbrev': 'CBJ'},
    'Bruins': {'name': 'Boston Bruins', 'abbrev': 'BOS'},
    'Canadiens': {'name': 'Montréal Canadiens', 'abbrev': 'MTL'},
    'Capitals': {'name': 'Washington Capitals', 'abbrev': 'WSH'},
    'Blackhawks': {'name': 'Chicago Blackhawks', 'abbrev': 'CHI'},
    'Blues': {'name': 'St. Louis Blues', 'abbrev': 'STL'},
    'Canucks': {'name': 'Vancouver Canucks', 'abbrev': 'VAN'},
    'Coyotes': {'name': 'Arizona Coyotes', 'abbrev': 'ARI'},
    'Devils': {'name': 'New Jersey Devils', 'abbrev': 'NJD'},
    'Ducks': {'name': 'Anaheim Ducks', 'abbrev': 'ANA'},
    'Flames': {'name': 'Calgary Flames', 'abbrev': 'CGY'},
    'Flyers': {'name': 'Philadelphia Flyers', 'abbrev': 'PHI'},
    'Golden_Knights': {'name': 'Vegas Golden Knights', 'abbrev': 'VGK'},
    'Hurricanes': {'name': 'Carolina Hurricanes', 'abbrev': 'CAR'},
    'Islanders': {'name': 'New York Islanders', 'abbrev': 'NYI'},
    'Jets': {'name': 'Winnipeg Jets', 'abbrev': 'WPG'},
    'Kings': {'name': 'Los Angeles Kings', 'abbrev': 'LAK'},
    'Kraken': {'name': 'Seattle Kraken', 'abbrev': 'SEA'},
    'Lightning': {'name': 'Tampa Bay Lightning', 'abbrev': 'TBL'},
    'Maple_Leafs': {'name': 'Toronto Maple Leafs', 'abbrev': 'TOR'},
    'Oilers': {'name': 'Edmonton Oilers', 'abbrev': 'EDM'},
    'Panthers': {'name': 'Florida Panthers', 'abbrev': 'FLA'},
    'Penguins': {'name': 'Pittsburgh Penguins', 'abbrev': 'PIT'},
    'Predators': {'name': 'Nashville Predators', 'abbrev': 'NSH'},
    'Rangers': {'name': 'New York Rangers', 'abbrev': 'NYR'},
    'Red_Wings': {'name': 'Detroit Red Wings', 'abbrev': 'DET'},
    'Sabres': {'name': 'Buffalo Sabres', 'abbrev': 'BUF'},
    'Senators': {'name': 'Ottawa Senators', 'abbrev': 'OTT'},
    'Sharks': {'name': 'San Jose Sharks', 'abbrev': 'SJS'},
    'Stars': {'name': 'Dallas Stars', 'abbrev': 'DAL'},
    'Wild': {'name': 'Minnesota Wild', 'abbrev': 'MIN'},
    'Utah_Hockey_Club': {'name': 'Utah Hockey Club', 'abbrev': 'UTA'},
}

def parse_lineup_file(file_path):
    """Parse the lineup text file and extract structured data."""
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    data = {
        'forward_lines': [],
        'defense_pairs': [],
        'goalies': [],
        'scratched_injured': [],
        'last_updated': ''
    }

    # Extract last updated
    updated_match = re.search(r'Last Updated: (.+)', content)
    if updated_match:
        data['last_updated'] = updated_match.group(1)

    # Extract forward lines
    forward_section = re.search(r'FORWARD LINES:.*?(?=DEFENSE PAIRS:|$)', content, re.DOTALL)
    if forward_section:
        lines = re.findall(r'Line \d+: (.+)', forward_section.group())
        data['forward_lines'] = lines

    # Extract defense pairs
    defense_section = re.search(r'DEFENSE PAIRS:.*?(?=GOALIES:|$)', content, re.DOTALL)
    if defense_section:
        pairs = re.findall(r'Pair \d+: (.+)', defense_section.group())
        data['defense_pairs'] = pairs

    # Extract goalies
    goalie_section = re.search(r'GOALIES:.*?(?=SCRATCHED|$)', content, re.DOTALL)
    if goalie_section:
        goalies = re.findall(r'  (.+)', goalie_section.group())
        data['goalies'] = [g.strip() for g in goalies if g.strip() and '---' not in g]

    # Extract scratched/injured
    scratched_section = re.search(r'SCRATCHED / INJURED:.*?(?====|$)', content, re.DOTALL)
    if scratched_section:
        players = re.findall(r'  (.+)', scratched_section.group())
        data['scratched_injured'] = [p.strip() for p in players if p.strip() and '---' not in p]

    return data

def generate_team_page(team_file_name, team_name, team_abbrev, lineup_data):
    """Generate HTML page for a team."""

    logo_url = f"https://assets.nhle.com/logos/nhl/svg/{team_abbrev}_light.svg"

    # Build forward lines HTML - more compact grid layout
    forward_html = "<div class='lines-grid'>\n"
    for i, line in enumerate(lineup_data['forward_lines'], 1):
        players = [p.strip() for p in line.split('—')]
        forward_html += f"  <div class='line-card'>\n"
        forward_html += f"    <div class='line-number'>L{i}</div>\n"
        forward_html += f"    <div class='players'>\n"
        for player in players:
            forward_html += f"      <div class='player'>{player}</div>\n"
        forward_html += f"    </div>\n"
        forward_html += f"  </div>\n"
    forward_html += "</div>\n"

    # Build defense pairs HTML - more compact grid layout
    defense_html = "<div class='lines-grid'>\n"
    for i, pair in enumerate(lineup_data['defense_pairs'], 1):
        players = [p.strip() for p in pair.split('—')]
        defense_html += f"  <div class='line-card'>\n"
        defense_html += f"    <div class='line-number'>D{i}</div>\n"
        defense_html += f"    <div class='players'>\n"
        for player in players:
            defense_html += f"      <div class='player'>{player}</div>\n"
        defense_html += f"    </div>\n"
        defense_html += f"  </div>\n"
    defense_html += "</div>\n"

    # Build goalies HTML
    goalies_html = ""
    for goalie in lineup_data['goalies']:
        goalies_html += f"  <div class='goalie-name'>{goalie}</div>\n"

    # Build scratched/injured HTML
    scratched_html = ""
    for player in lineup_data['scratched_injured']:
        if 'injured' in player.lower():
            scratched_html += f"  <div class='injured-player'>🚑 {player}</div>\n"
        else:
            scratched_html += f"  <div class='scratched-player'>⊘ {player}</div>\n"

    html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>{team_name} - Lineup & Roster | Parieur Discipliné</title>
<meta name='description' content='Current lineup, forward lines, defense pairs, goalies, and injury report for the {team_name}.'>
<link rel='icon' type='image/png' href='../../../parieur_discipline_icon_1024.png'>
</head>
<body>

<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
  color: #1a1a1a;
  line-height: 1.6;
}}
.container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 100px 20px 40px 20px;
}}
.team-header {{
  background: linear-gradient(135deg, #2c5aa0 0%, #1e3a8a 100%);
  color: white;
  padding: 40px;
  border-radius: 16px;
  margin-bottom: 40px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}}
.team-logo {{
  width: 120px;
  height: 120px;
  margin: 0 auto 20px;
  background: white;
  border-radius: 50%;
  padding: 15px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}}
.team-logo img {{
  width: 100%;
  height: 100%;
  object-fit: contain;
}}
.team-header h1 {{
  font-size: 2.5em;
  font-weight: 800;
  margin-bottom: 10px;
}}
.last-updated {{
  font-size: 0.9em;
  opacity: 0.9;
  margin-top: 10px;
}}
.back-link {{
  display: inline-block;
  color: white;
  text-decoration: none;
  padding: 10px 20px;
  background: rgba(255,255,255,0.2);
  border-radius: 8px;
  margin-top: 20px;
  transition: background 0.3s;
}}
.back-link:hover {{
  background: rgba(255,255,255,0.3);
}}
.section {{
  background: white;
  border-radius: 12px;
  padding: 25px;
  margin-bottom: 25px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}}
.section-title {{
  font-size: 1.5em;
  color: #2563eb;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 10px;
}}
.lines-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 15px;
}}
.line-card {{
  background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
  border-radius: 10px;
  padding: 15px;
  border: 2px solid #e5e7eb;
  transition: all 0.3s;
}}
.line-card:hover {{
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}}
.line-number {{
  display: inline-block;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  font-weight: 800;
  font-size: 0.85em;
  padding: 4px 12px;
  border-radius: 20px;
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}}
.players {{
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
.player {{
  background: white;
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 0.9em;
  color: #374151;
  border-left: 3px solid #3b82f6;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
.goalie-name {{
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #78350f;
  padding: 10px 16px;
  border-radius: 8px;
  font-weight: 700;
  font-size: 1em;
  margin-bottom: 8px;
  box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3);
  text-align: center;
}}
.injured-player, .scratched-player {{
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 6px;
  font-weight: 600;
  font-size: 0.9em;
}}
.injured-player {{
  background: #fee2e2;
  color: #991b1b;
  border-left: 3px solid #dc2626;
}}
.scratched-player {{
  background: #f3f4f6;
  color: #6b7280;
  border-left: 3px solid #9ca3af;
}}
@media (max-width: 768px) {{
  .container {{
    padding: 80px 15px 30px 15px;
  }}
  .team-header {{
    padding: 30px 20px;
  }}
  .team-header h1 {{
    font-size: 1.8em;
  }}
  .team-logo {{
    width: 90px;
    height: 90px;
  }}
  .section {{
    padding: 20px;
  }}
  .section-title {{
    font-size: 1.3em;
  }}
  .lines-grid {{
    grid-template-columns: 1fr;
  }}
}}
</style>

<nav style='position: fixed; top: 0; left: 0; right: 0; z-index: 1000; background: linear-gradient(135deg, #2c5aa0 0%, #1e3a8a 100%); box-shadow: 0 2px 10px rgba(0,0,0,0.1); backdrop-filter: blur(10px);'>
<div style='max-width: 1600px; margin: 0 auto; padding: 10px 15px; display: flex; align-items: center; justify-content: space-between;'>
<div style='display: flex; align-items: center; gap: 10px;'>
<img src='../../../parieur_discipline_icon_1024.png' alt='Logo' style='width: 32px; height: 32px; border-radius: 50%;' />
<span style='color: white; font-weight: 700; font-size: 1em;'>Parieur Discipliné</span>
</div>
<a href='../index.html' style='color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 6px; font-weight: 600; font-size: 0.9em; transition: background 0.2s;' onmouseover='this.style.background="rgba(255,255,255,0.3)"' onmouseout='this.style.background="rgba(255,255,255,0.2)"'>← All Teams</a>
</div>
</nav>

<div class='container'>
  <div class='team-header'>
    <div class='team-logo'>
      <img src='{logo_url}' alt='{team_name}' onerror='this.style.display="none"'>
    </div>
    <h1>{team_name}</h1>
    <div class='last-updated'>⏱️ {lineup_data['last_updated']}</div>
    <a href='../index.html' class='back-link'>← Back to All Teams</a>
  </div>

  <div class='section'>
    <div class='section-title'>🏒 Forward Lines</div>
{forward_html}
  </div>

  <div class='section'>
    <div class='section-title'>🛡️ Defense Pairs</div>
{defense_html}
  </div>

  <div class='section'>
    <div class='section-title'>🥅 Goalies</div>
{goalies_html}
  </div>

  <div class='section'>
    <div class='section-title'>⚠️ Scratched / Injured</div>
{scratched_html}
  </div>
</div>

<script defer src='/_vercel/insights/script.js'></script>
<script defer src='/_vercel/speed-insights/script.js'></script>

</body>
</html>
"""

    return html

def main():
    # Create team pages directory
    teams_dir = "docs/nhl/teams"
    os.makedirs(teams_dir, exist_ok=True)

    data_dir = "data/teams"

    # Generate page for each team
    for team_file_name, info in TEAM_INFO.items():
        file_path = os.path.join(data_dir, f"{team_file_name}.txt")

        if not os.path.exists(file_path):
            print(f"Skipping {team_file_name} - no lineup file found")
            continue

        lineup_data = parse_lineup_file(file_path)
        if not lineup_data:
            print(f"Skipping {team_file_name} - could not parse lineup file")
            continue

        html = generate_team_page(
            team_file_name,
            info['name'],
            info['abbrev'],
            lineup_data
        )

        # Save to file
        output_path = os.path.join(teams_dir, f"{team_file_name}.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"Generated: {output_path}")

    print(f"\n✅ Team pages generated successfully!")

if __name__ == "__main__":
    main()
