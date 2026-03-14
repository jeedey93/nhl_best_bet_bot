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
    forward_html = ""
    for i, line in enumerate(lineup_data['forward_lines'], 1):
        players = [p.strip() for p in line.split('—')]
        forward_html += f"  <div class='line-card'>\n"
        forward_html += f"    <div class='line-number'>L{i}</div>\n"
        forward_html += f"    <div class='players'>\n"
        for player in players:
            forward_html += f"      <div class='player'>{player}</div>\n"
        forward_html += f"    </div>\n"
        forward_html += f"  </div>\n"

    # Build defense pairs HTML - more compact grid layout
    defense_html = ""
    for i, pair in enumerate(lineup_data['defense_pairs'], 1):
        players = [p.strip() for p in pair.split('—')]
        defense_html += f"  <div class='line-card'>\n"
        defense_html += f"    <div class='line-number'>D{i}</div>\n"
        defense_html += f"    <div class='players'>\n"
        for player in players:
            defense_html += f"      <div class='player'>{player}</div>\n"
        defense_html += f"    </div>\n"
        defense_html += f"  </div>\n"

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
  max-width: 1400px;
  margin: 0 auto;
  padding: 100px 20px 40px 20px;
}}
.lineup-container {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}}
.lineup-column {{
  display: flex;
  flex-direction: column;
  gap: 20px;
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
  font-size: 3.5em;
  font-weight: 800;
  margin-bottom: 10px;
  letter-spacing: -1px;
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
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}}
.section-title {{
  font-size: 1.4em;
  color: #2563eb;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.line-card {{
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  border-left: 3px solid #3b82f6;
}}
.line-number {{
  display: inline-block;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  font-weight: 800;
  font-size: 0.8em;
  padding: 3px 10px;
  border-radius: 20px;
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}}
.players {{
  display: flex;
  gap: 8px;
}}
.player {{
  flex: 1;
  background: white;
  padding: 6px 12px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 0.9em;
  color: #374151;
  border-left: 3px solid #3b82f6;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  text-align: center;
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
  font-size: 0.85em;
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
  .lineup-container {{
    grid-template-columns: 1fr;
    gap: 15px;
    display: flex;
    flex-direction: column;
  }}
  .lineup-column {{
    gap: 15px;
    display: contents;
  }}
  .lineup-column:first-child .section:first-child {{
    order: 1;  /* Forwards first */
  }}
  .lineup-column:last-child .section:first-child {{
    order: 2;  /* Defense second */
  }}
  .lineup-column:first-child .section:last-child {{
    order: 3;  /* Goalies third */
  }}
  .lineup-column:last-child .section:last-child {{
    order: 4;  /* Scratched/Injured fourth */
  }}
  .team-header {{
    padding: 30px 20px;
  }}
  .team-header h1 {{
    font-size: 2.2em;
    letter-spacing: -0.5px;
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
  .line-card {{
    padding: 10px;
    margin-bottom: 10px;
  }}
  .line-number {{
    font-size: 0.75em;
    padding: 2px 8px;
    margin-bottom: 6px;
  }}
  .players {{
    gap: 4px;
  }}
  .player {{
    padding: 6px 8px;
    font-size: 0.8em;
  }}
}}
</style>

<nav style='position: fixed; top: 0; left: 0; right: 0; z-index: 1000; background: linear-gradient(135deg, #2c5aa0 0%, #1e3a8a 100%); box-shadow: 0 2px 10px rgba(0,0,0,0.1); backdrop-filter: blur(10px);'>
<div style='max-width: 1600px; margin: 0 auto; padding: 10px 15px; display: flex; align-items: center; justify-content: space-between;'>
<div style='display: flex; align-items: center; gap: 10px;'>
<img src='../../../parieur_discipline_icon_1024.png' alt='Logo' style='width: 32px; height: 32px; border-radius: 50%;' />
<span style='color: white; font-weight: 700; font-size: 1em;'>Parieur Discipliné</span>
</div>
<button id='mobileMenuBtn' style='display: none; background: none; border: none; color: white; font-size: 1.5em; cursor: pointer; padding: 5px;' onclick='toggleMobileMenu()'>☰</button>
<div id='navLinks'>
<a href='../../../index.html' style='color: white; text-decoration: none; padding: 8px 12px; border-radius: 6px; font-weight: 600; font-size: 0.9em; transition: background 0.2s; white-space: nowrap;' onmouseover='this.style.background="rgba(255,255,255,0.15)"' onmouseout='this.style.background="transparent"'>Home</a>
<a href='../../../daily-picks.html' style='color: white; text-decoration: none; padding: 8px 12px; border-radius: 6px; font-weight: 600; font-size: 0.9em; transition: background 0.2s; white-space: nowrap;' onmouseover='this.style.background="rgba(255,255,255,0.15)"' onmouseout='this.style.background="transparent"'>🎯 Today</a>
<div class='nav-dropdown' style='position: relative;'>
  <a href='#' class='nav-dropdown-toggle' style='color: white; text-decoration: none; padding: 8px 12px; border-radius: 6px; font-weight: 600; font-size: 0.9em; transition: background 0.2s; white-space: nowrap; display: flex; align-items: center; gap: 4px;' onmouseover='this.style.background="rgba(255,255,255,0.15)"' onmouseout='this.style.background="transparent"'>🏒 NHL <span style='font-size: 0.7em;'>▼</span></a>
  <div class='nav-dropdown-menu' style='position: absolute; top: 100%; left: 0; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); min-width: 180px; opacity: 0; visibility: hidden; transform: translateY(-10px); transition: all 0.2s ease; margin-top: 5px; z-index: 1100;'>
    <a href='/nhl/games/index.html' style='display: block; color: #1e293b; text-decoration: none; padding: 10px 16px; font-weight: 600; font-size: 0.9em; transition: background 0.2s; border-bottom: 1px solid #e5e7eb;' onmouseover='this.style.background="#f1f5f9"' onmouseout='this.style.background="white"'>📅 Today's Games</a>
    <a href='/nhl/teams/index.html' style='display: block; color: #1e293b; text-decoration: none; padding: 10px 16px; font-weight: 600; font-size: 0.9em; transition: background 0.2s;' onmouseover='this.style.background="#f1f5f9"' onmouseout='this.style.background="white"'>🏒 All Teams</a>
  </div>
</div>
<a href='../../../nba.html' style='color: white; text-decoration: none; padding: 8px 12px; border-radius: 6px; font-weight: 600; font-size: 0.9em; transition: background 0.2s; white-space: nowrap;' onmouseover='this.style.background="rgba(255,255,255,0.15)"' onmouseout='this.style.background="transparent"'>🏀 NBA</a>
<a href='../../../performance.html' style='color: white; text-decoration: none; padding: 8px 12px; border-radius: 6px; font-weight: 600; font-size: 0.9em; transition: background 0.2s; white-space: nowrap;' onmouseover='this.style.background="rgba(255,255,255,0.15)"' onmouseout='this.style.background="transparent"'>📊 Performance</a>
<a href='../../../about.html' style='color: white; text-decoration: none; padding: 8px 12px; border-radius: 6px; font-weight: 600; font-size: 0.9em; transition: background 0.2s; white-space: nowrap;' onmouseover='this.style.background="rgba(255,255,255,0.15)"' onmouseout='this.style.background="transparent"'>ℹ️ About</a>
</div>
</div>
</nav>
<div style='position: fixed; top: 52px; left: 0; right: 0; z-index: 999; background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); padding: 8px 20px; text-align: center; box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3);'>
<span style='color: #78350f; font-weight: 600; font-size: 0.85em; letter-spacing: 0.3px;'>🎯 Our AI is learning and improving every day to bring you better predictions</span>
</div>
<style>
#navLinks {{ display: flex; gap: 8px; align-items: center; }}
.nav-dropdown:hover .nav-dropdown-menu {{
  opacity: 1 !important;
  visibility: visible !important;
  transform: translateY(0) !important;
}}
.nav-dropdown-menu.show {{
  opacity: 1 !important;
  visibility: visible !important;
  transform: translateY(0) !important;
}}
@media (max-width: 768px) {{
  nav div:first-child span {{ font-size: 0.85em; }}
  nav div:first-child img {{ width: 28px; height: 28px; }}
  #mobileMenuBtn {{ display: block !important; }}
  #navLinks {{
    display: none !important;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: linear-gradient(135deg, #2c5aa0 0%, #1e3a8a 100%);
    flex-direction: column;
    gap: 0;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    align-items: stretch;
    max-height: calc(100vh - 52px);
    overflow-y: auto;
  }}
  #navLinks.active {{ display: flex !important; }}
  #navLinks a {{
    padding: 14px 20px;
    font-size: 1em;
    border-radius: 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
  }}
  .nav-dropdown {{
    width: 100%;
  }}
  .nav-dropdown-toggle {{
    width: 100%;
    padding: 14px 20px !important;
    border-bottom: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 0 !important;
    justify-content: space-between !important;
  }}
  .nav-dropdown-menu {{
    position: static !important;
    opacity: 0 !important;
    visibility: hidden !important;
    max-height: 0;
    overflow: hidden;
    transform: none !important;
    box-shadow: none !important;
    background: rgba(255,255,255,0.1) !important;
    margin: 0 !important;
    transition: max-height 0.3s ease, opacity 0.2s ease !important;
  }}
  .nav-dropdown.mobile-open .nav-dropdown-menu {{
    opacity: 1 !important;
    visibility: visible !important;
    max-height: 200px;
  }}
  .nav-dropdown-menu a {{
    color: white !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    padding: 12px 20px 12px 40px !important;
    font-size: 0.95em !important;
  }}
  .nav-dropdown-menu a:hover {{
    background: rgba(255,255,255,0.1) !important;
  }}
  .nav-dropdown-menu a:last-child {{
    border-bottom: none !important;
  }}
}}
</style>
<script>
function toggleMobileMenu() {{
  const navLinks = document.getElementById('navLinks');
  navLinks.classList.toggle('active');
}}
// Close menu when clicking outside
document.addEventListener('click', function(event) {{
  const nav = document.querySelector('nav');
  const menuBtn = document.getElementById('mobileMenuBtn');
  const navLinks = document.getElementById('navLinks');
  const dropdown = document.querySelector('.nav-dropdown');
  const dropdownMenu = document.querySelector('.nav-dropdown-menu');

  // Close mobile menu when clicking outside
  if (!nav.contains(event.target) && navLinks.classList.contains('active')) {{
    navLinks.classList.remove('active');
  }}

  // Close dropdown when clicking outside
  if (dropdown && !dropdown.contains(event.target) && dropdownMenu) {{
    dropdownMenu.classList.remove('show');
  }}
}});
// Handle dropdown toggle
document.addEventListener('DOMContentLoaded', function() {{
  const dropdownToggle = document.querySelector('.nav-dropdown-toggle');
  const dropdown = document.querySelector('.nav-dropdown');
  const dropdownMenu = document.querySelector('.nav-dropdown-menu');

  if (dropdownToggle && dropdownMenu) {{
    dropdownToggle.addEventListener('click', function(e) {{
      e.preventDefault();

      // On mobile, toggle the mobile-open class
      if (window.innerWidth <= 768) {{
        dropdown.classList.toggle('mobile-open');
      }} else {{
        // On desktop, toggle the show class
        dropdownMenu.classList.toggle('show');
      }}
    }});
  }}
}});
</script>

<div class='container'>
  <div class='team-header'>
    <div class='team-logo'>
      <img src='{logo_url}' alt='{team_name}' onerror='this.style.display="none"'>
    </div>
    <h1>{team_name}</h1>
    <div class='last-updated'>⏱️ {lineup_data['last_updated']}</div>
    <a href='/nhl/teams/index.html' class='back-link'>← Back to All Teams</a>
  </div>

  <div class='lineup-container'>
    <div class='lineup-column'>
      <div class='section'>
        <div class='section-title'>🏒 Forward Lines</div>
{forward_html}
      </div>

      <div class='section'>
        <div class='section-title'>🥅 Goalies</div>
{goalies_html}
      </div>
    </div>

    <div class='lineup-column'>
      <div class='section'>
        <div class='section-title'>🛡️ Defense Pairs</div>
{defense_html}
      </div>

      <div class='section'>
        <div class='section-title'>⚠️ Scratched / Injured</div>
{scratched_html}
      </div>
    </div>
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
