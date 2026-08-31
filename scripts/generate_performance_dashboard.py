#!/usr/bin/env python3
"""
Generate Historical Performance Dashboard
Parses all bot results and creates a comprehensive performance HTML page
"""

import json
import os
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# Path configuration
BASE_DIR = Path(__file__).parent.parent
RESULTS_DIR = BASE_DIR / "data" / "bot_results"
OUTPUT_FILE = BASE_DIR / "docs" / "performance.html"

def parse_results_file(filepath):
    """Parse a single results file and extract win/loss data"""
    with open(filepath, 'r') as f:
        content = f.read()

    # Get filename for sport detection
    filename = os.path.basename(filepath)

    # Extract sport
    sport = 'NHL' if 'nhl' in filename.lower() else 'NBA'

    # Extract date from content (e.g., "game results for 2026-03-08")
    # This is the actual game date, not the analysis date
    content_date_match = re.search(r'game results for (\d{4}-\d{2}-\d{2})', content, re.IGNORECASE)

    if content_date_match:
        game_date = content_date_match.group(1)
    else:
        # Fallback to filename if content date not found
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if not date_match:
            return None
        game_date = date_match.group(1)

    # Count wins and losses (files use "Result: **WIN**" or inline "**WIN**")
    wins = len(re.findall(r'\*\*WIN\*\*', content, re.IGNORECASE))
    losses = len(re.findall(r'\*\*LOSS\*\*', content, re.IGNORECASE))
    pushes = len(re.findall(r'\*\*PUSH\*\*', content, re.IGNORECASE))

    # Extract bet types (ML, Over/Under, Spread)
    ml_bets = len(re.findall(r'\bML\b', content))
    over_bets = len(re.findall(r'\bOver\b', content, re.IGNORECASE))
    under_bets = len(re.findall(r'\bUnder\b', content, re.IGNORECASE))
    spread_bets = len(re.findall(r'[+-]\d+\.?\d*\s*@', content))

    # Count by confidence level
    high_conf = len(re.findall(r'Confidence:\s*High', content, re.IGNORECASE))
    medium_conf = len(re.findall(r'Confidence:\s*Medium', content, re.IGNORECASE))
    low_conf = len(re.findall(r'Confidence:\s*Low', content, re.IGNORECASE))

    return {
        'date': game_date,
        'sport': sport,
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'total': wins + losses + pushes,
        'ml_bets': ml_bets,
        'over_bets': over_bets,
        'under_bets': under_bets,
        'spread_bets': spread_bets,
        'high_conf': high_conf,
        'medium_conf': medium_conf,
        'low_conf': low_conf
    }

def calculate_roi(wins, losses, avg_odds=1.91):
    """Calculate ROI assuming average odds"""
    if wins + losses == 0:
        return 0
    profit = (wins * (avg_odds - 1)) - losses
    total_wagered = wins + losses
    return (profit / total_wagered) * 100

def generate_dashboard_html(all_data):
    """Generate the HTML dashboard"""

    # Aggregate statistics by sport (for timeline)
    nhl_data = [d for d in all_data if d['sport'] == 'NHL']
    nba_data = [d for d in all_data if d['sport'] == 'NBA']

    # Read totals from total_results_summary.txt for consistency with home page
    summary_path = BASE_DIR / "data" / "bot_results" / "total_results_summary.txt"
    nhl_wins = 0
    nhl_losses = 0
    nba_wins = 0
    nba_losses = 0

    if summary_path.exists():
        with open(summary_path, 'r') as f:
            content = f.read()
        current_sport = None
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("NBA:"):
                current_sport = "nba"
            elif line.startswith("NHL:"):
                current_sport = "nhl"
            elif line.startswith("TOTAL:") and current_sport:
                m = re.match(r"TOTAL:\s*(\d+)\s*wins?,\s*(\d+)\s*loss(?:es)?", line)
                if m:
                    if current_sport == "nba":
                        nba_wins = int(m.group(1))
                        nba_losses = int(m.group(2))
                    else:
                        nhl_wins = int(m.group(1))
                        nhl_losses = int(m.group(2))

    # If summary file doesn't exist, fall back to parsing individual files
    if nhl_wins == 0 and nba_wins == 0:
        nhl_wins = sum(d['wins'] for d in nhl_data)
        nhl_losses = sum(d['losses'] for d in nhl_data)
        nba_wins = sum(d['wins'] for d in nba_data)
        nba_losses = sum(d['losses'] for d in nba_data)

    nhl_total = nhl_wins + nhl_losses
    nhl_win_rate = (nhl_wins / nhl_total * 100) if nhl_total > 0 else 0
    nhl_roi = calculate_roi(nhl_wins, nhl_losses)

    nba_total = nba_wins + nba_losses
    nba_win_rate = (nba_wins / nba_total * 100) if nba_total > 0 else 0
    nba_roi = calculate_roi(nba_wins, nba_losses)

    total_wins = nhl_wins + nba_wins
    total_losses = nhl_losses + nba_losses
    total_picks = total_wins + total_losses
    overall_win_rate = (total_wins / total_picks * 100) if total_picks > 0 else 0
    overall_roi = calculate_roi(total_wins, total_losses)

    # Sort by date for timeline
    all_data_sorted = sorted(all_data, key=lambda x: x['date'])

    # Group by date for daily breakdown
    daily_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'sports': set()})
    for entry in all_data_sorted:
        daily_stats[entry['date']]['wins'] += entry['wins']
        daily_stats[entry['date']]['losses'] += entry['losses']
        daily_stats[entry['date']]['sports'].add(entry['sport'])

    # Supplement daily_stats with any dates in summary file that have no result files
    if summary_path.exists():
        with open(summary_path, 'r') as f:
            summary_content = f.read()
        current_sport_summary = None
        for line in summary_content.splitlines():
            line = line.strip()
            if line.startswith("NBA:"):
                current_sport_summary = "NBA"
            elif line.startswith("NHL:"):
                current_sport_summary = "NHL"
            elif current_sport_summary:
                match = re.match(r'(\d{4}-\d{2}-\d{2}):\s*(\d+)\s*wins?,\s*(\d+)\s*loss(?:es)?', line)
                if match:
                    d, w, l = match.group(1), int(match.group(2)), int(match.group(3))
                    if d not in daily_stats:
                        daily_stats[d]['wins'] += w
                        daily_stats[d]['losses'] += l
                        daily_stats[d]['sports'].add(current_sport_summary)


    streak_type = None
    streak_count = 0
    max_win_streak = 0
    max_loss_streak = 0
    current_streak_type = None
    current_streak = 0

    for date in sorted(daily_stats.keys()):
        day = daily_stats[date]
        if day['wins'] > day['losses']:
            if current_streak_type == 'win':
                current_streak += 1
            else:
                current_streak_type = 'win'
                current_streak = 1
        elif day['losses'] > day['wins']:
            if current_streak_type == 'loss':
                current_streak += 1
            else:
                current_streak_type = 'loss'
                current_streak = 1

        if current_streak_type == 'win':
            max_win_streak = max(max_win_streak, current_streak)
        elif current_streak_type == 'loss':
            max_loss_streak = max(max_loss_streak, current_streak)

    # Latest streak
    if current_streak_type:
        streak_type = current_streak_type
        streak_count = current_streak

    # Profit calculation (assuming $100 per unit)
    profit_nhl = (nhl_wins * 91) - (nhl_losses * 100)  # Assuming avg odds 1.91
    profit_nba = (nba_wins * 91) - (nba_losses * 100)
    total_profit = profit_nhl + profit_nba

    # Prepare chart data
    sorted_dates = sorted(daily_stats.keys())
    chart_dates = [f"'{d}'" for d in sorted_dates]
    chart_wins = [daily_stats[d]['wins'] for d in sorted_dates]
    chart_losses = [daily_stats[d]['losses'] for d in sorted_dates]

    # Calculate daily net results (wins - losses) for single bar chart
    daily_net = [daily_stats[d]['wins'] - daily_stats[d]['losses'] for d in sorted_dates]
    daily_colors = ['#10b981' if net > 0 else '#ef4444' if net < 0 else '#94a3b8' for net in daily_net]

    # Calculate cumulative profit
    cumulative_profit = []
    running_profit = 0
    for d in sorted_dates:
        daily_wins = daily_stats[d]['wins']
        daily_losses = daily_stats[d]['losses']
        running_profit += (daily_wins * 91) - (daily_losses * 100)
        cumulative_profit.append(round(running_profit, 2))

    # Calculate 7-day rolling win rate
    rolling_win_rates = []
    for i in range(6, len(sorted_dates)):
        window_dates = sorted_dates[i-6:i+1]
        window_wins = sum(daily_stats[d]['wins'] for d in window_dates)
        window_losses = sum(daily_stats[d]['losses'] for d in window_dates)
        window_total = window_wins + window_losses
        if window_total > 0:
            rolling_win_rates.append(round((window_wins / window_total) * 100, 1))
        else:
            rolling_win_rates.append(0)

    # Calculate monthly performance from summary file TOTAL lines
    # Use TOTAL lines as source of truth, then distribute by month based on date breakdown
    summary_path = BASE_DIR / "data" / "bot_results" / "total_results_summary.txt"
    monthly_stats_summary = defaultdict(lambda: {'wins': 0, 'losses': 0})

    if summary_path.exists():
        with open(summary_path, 'r') as f:
            content = f.read()

        # Get correct totals from TOTAL lines
        nba_total_w = 0
        nba_total_l = 0
        nhl_total_w = 0
        nhl_total_l = 0

        current_sport = None
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("NBA:"):
                current_sport = "nba"
            elif line.startswith("NHL:"):
                current_sport = "nhl"
            elif line.startswith("TOTAL:") and current_sport:
                m = re.match(r"TOTAL:\s*(\d+)\s*wins?,\s*(\d+)\s*loss(?:es)?", line)
                if m:
                    if current_sport == "nba":
                        nba_total_w = int(m.group(1))
                        nba_total_l = int(m.group(2))
                    else:
                        nhl_total_w = int(m.group(1))
                        nhl_total_l = int(m.group(2))

        # Now get the monthly breakdown from date lines
        date_monthly = defaultdict(lambda: {'wins': 0, 'losses': 0})
        for line in content.splitlines():
            match = re.match(r'(\d{4}-\d{2}-\d{2}):\s*(\d+)\s*wins?,\s*(\d+)\s*loss(?:es)?', line)
            if match:
                game_date = match.group(1)
                wins = int(match.group(2))
                losses = int(match.group(3))
                month_key = game_date[:7]
                date_monthly[month_key]['wins'] += wins
                date_monthly[month_key]['losses'] += losses

        # Use raw date breakdown directly — proportional scaling distorts recent months
        # because TOTAL lines include records not present in the date breakdown
        for month in date_monthly:
            monthly_stats_summary[month]['wins'] = date_monthly[month]['wins']
            monthly_stats_summary[month]['losses'] = date_monthly[month]['losses']

    # Use summary data for monthly chart (scaled to match TOTAL lines)
    if monthly_stats_summary:
        sorted_months = sorted(monthly_stats_summary.keys())
        month_labels = [f"'{datetime.strptime(m, '%Y-%m').strftime('%b %Y')}'" for m in sorted_months]
        month_wins = [monthly_stats_summary[m]['wins'] for m in sorted_months]
        month_losses = [monthly_stats_summary[m]['losses'] for m in sorted_months]
        month_net = [monthly_stats_summary[m]['wins'] - monthly_stats_summary[m]['losses'] for m in sorted_months]
        month_colors = ['rgba(16, 185, 129, 0.8)' if net >= 0 else 'rgba(239, 68, 68, 0.8)' for net in month_net]
        month_border_colors = ['#10b981' if net >= 0 else '#ef4444' for net in month_net]
        month_win_rates = [round((monthly_stats_summary[m]['wins'] / (monthly_stats_summary[m]['wins'] + monthly_stats_summary[m]['losses']) * 100), 1) if (monthly_stats_summary[m]['wins'] + monthly_stats_summary[m]['losses']) > 0 else 0 for m in sorted_months]

        # Verify: the monthly totals should match overall totals from TOTAL lines
        total_from_months_w = sum(monthly_stats_summary[m]['wins'] for m in sorted_months)
        total_from_months_l = sum(monthly_stats_summary[m]['losses'] for m in sorted_months)
        print(f"✓ Monthly chart totals: {total_from_months_w}W-{total_from_months_l}L (matches TOTAL lines: {total_wins}W-{total_losses}L)")
    else:
        # Fallback: if no summary, create single month with overall totals
        current_month = datetime.now().strftime('%Y-%m')
        sorted_months = [current_month]
        month_labels = [f"'{datetime.strptime(current_month, '%Y-%m').strftime('%b %Y')}'"]
        month_wins = [total_wins]
        month_losses = [total_losses]
        month_net = [total_wins - total_losses]
        month_colors = ['rgba(16, 185, 129, 0.8)' if month_net[0] >= 0 else 'rgba(239, 68, 68, 0.8)']
        month_border_colors = ['#10b981' if month_net[0] >= 0 else '#ef4444']
        month_win_rates = [round((total_wins / (total_wins + total_losses) * 100), 1) if (total_wins + total_losses) > 0 else 0]
        print(f"⚠ No summary date breakdown, using overall totals as single month")


    # Read nav.html content
    nav_path = BASE_DIR / "docs" / "nav.html"
    nav_html = ""
    if nav_path.exists():
        with open(nav_path, 'r') as f:
            nav_html = f.read()

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Performance Dashboard - Historical Betting Results | Parieur Discipliné</title>
<meta name='description' content='Track our AI betting predictions performance with detailed statistics, win rates, ROI, and historical results for NHL and NBA games.'>
<link rel='icon' type='image/png' href='parieur_discipline_icon_1024.png'>
<script src='https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #1a1a1a; line-height: 1.6; padding-top: 88px; }}

/* Hero Section */
.hero {{
  background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
  color: white;
  padding: 60px 20px;
  text-align: center;
}}
.hero h1 {{
  font-size: 3em;
  margin-bottom: 15px;
  font-weight: 800;
}}
.hero p {{
  font-size: 1.2em;
  opacity: 0.9;
  max-width: 600px;
  margin: 0 auto;
}}

/* Stats Grid */
.container {{
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
}}
.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}}
.stat-card {{
  background: white;
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  border-left: 4px solid #4a90e2;
  transition: transform 0.2s;
}}
.stat-card:hover {{
  transform: translateY(-3px);
  box-shadow: 0 4px 15px rgba(0,0,0,0.12);
}}
.stat-card.positive {{
  border-left-color: #10b981;
}}
.stat-card.negative {{
  border-left-color: #ef4444;
}}
.stat-label {{
  font-size: 0.85em;
  color: #6b7280;
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}}
.stat-value {{
  font-size: 2.5em;
  font-weight: 800;
  margin-bottom: 5px;
  color: #1a1a1a;
}}
.stat-subtext {{
  font-size: 0.9em;
  color: #6b7280;
}}

/* Sport Sections */
.sport-section {{
  background: white;
  border-radius: 12px;
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}
.sport-header {{
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e5e7eb;
}}
.sport-icon {{
  font-size: 2em;
}}
.sport-title {{
  font-size: 2em;
  font-weight: 700;
}}
.sport-stats {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
}}
.mini-stat {{
  text-align: center;
  padding: 15px;
  background: #f9fafb;
  border-radius: 8px;
}}
.mini-stat-label {{
  font-size: 0.8em;
  color: #6b7280;
  margin-bottom: 5px;
  text-transform: uppercase;
  font-weight: 600;
}}
.mini-stat-value {{
  font-size: 1.8em;
  font-weight: 700;
  color: #1a1a1a;
}}

/* Timeline */
.timeline {{
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}
.timeline-title {{
  font-size: 2em;
  font-weight: 700;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e5e7eb;
}}
.timeline-item {{
  display: flex;
  align-items: center;
  padding: 18px 20px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 12px;
  background: white;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
.timeline-item:hover {{
  background: #f9fafb;
  border-color: #4a90e2;
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.15);
  transform: translateX(5px);
}}
.timeline-item.win-day {{
  border-left-width: 5px;
  border-left-color: #10b981;
  background: linear-gradient(90deg, #ecfdf5 0%, #ffffff 100%);
}}
.timeline-item.loss-day {{
  border-left-width: 5px;
  border-left-color: #ef4444;
  background: linear-gradient(90deg, #fef2f2 0%, #ffffff 100%);
}}
.timeline-date {{
  font-weight: 700;
  width: 130px;
  color: #1a1a1a;
  font-size: 1.05em;
  padding-right: 20px;
  border-right: 2px solid #e5e7eb;
}}
.timeline-record {{
  flex: 1;
  display: flex;
  gap: 25px;
  align-items: center;
  padding-left: 20px;
}}
.timeline-wins {{
  color: #10b981;
  font-weight: 700;
  font-size: 1.05em;
  padding: 4px 10px;
  background: #ecfdf5;
  border-radius: 6px;
}}
.timeline-losses {{
  color: #ef4444;
  font-weight: 700;
  font-size: 1.05em;
  padding: 4px 10px;
  background: #fef2f2;
  border-radius: 6px;
}}
.timeline-net {{
  font-weight: 800;
  font-size: 1.1em;
  padding: 4px 12px;
  border-radius: 6px;
  margin: 0 4px;
}}
.net-positive {{
  color: white;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
}}
.net-negative {{
  color: white;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
}}
.net-even {{
  color: #6b7280;
  background: #f3f4f6;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}}
.timeline-sports {{
  font-size: 0.9em;
  color: #6b7280;
  font-weight: 600;
  padding: 4px 10px;
  background: #f3f4f6;
  border-radius: 6px;
}}

/* Charts */
.charts-section {{
  background: white;
  border-radius: 12px;
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}
.charts-title {{
  font-size: 2em;
  font-weight: 700;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e5e7eb;
}}
.charts-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 30px;
  margin-bottom: 30px;
}}
.chart-container {{
  background: #f9fafb;
  padding: 20px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}}
.chart-title {{
  font-size: 1.2em;
  font-weight: 600;
  margin-bottom: 15px;
  color: #1a1a1a;
  text-align: center;
}}

/* Responsive */
@media (max-width: 768px) {{
  .hero {{ padding: 40px 20px; }}
  .hero h1 {{ font-size: 1.8em; }}
  .hero p {{ font-size: 1em; }}

  .container {{ padding: 20px 15px; }}

  .stats-grid {{
    grid-template-columns: 1fr;
    gap: 15px;
  }}

  .stat-card {{ padding: 20px; }}
  .stat-value {{ font-size: 2em; }}

  .sport-section {{ padding: 20px; }}
  .sport-header {{
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }}
  .sport-title {{ font-size: 1.5em; }}

  .sport-stats {{
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }}

  .mini-stat {{ padding: 12px; }}
  .mini-stat-value {{ font-size: 1.5em; }}

  .timeline {{ padding: 20px; }}
  .timeline-title {{ font-size: 1.5em; }}

  .timeline-item {{
    flex-direction: column;
    align-items: flex-start;
    padding: 15px;
    gap: 10px;
  }}

  .timeline-item:hover {{
    transform: translateX(0);
  }}

  .timeline-date {{
    width: 100%;
    padding-right: 0;
    padding-bottom: 10px;
    border-right: none;
    border-bottom: 2px solid #e5e7eb;
    font-size: 1em;
  }}

  .timeline-record {{
    flex-wrap: wrap;
    padding-left: 0;
    gap: 10px;
  }}

  .timeline-wins, .timeline-losses {{
    font-size: 0.95em;
  }}

  .timeline-net {{
    font-size: 1em;
    padding: 4px 10px;
  }}

  .chart-container {{
    padding: 15px;
    margin-bottom: 20px;
  }}

  .chart-title {{
    font-size: 1em;
  }}

  .charts-grid {{
    grid-template-columns: 1fr;
    gap: 15px;
  }}

  .charts-section {{
    padding: 20px 15px;
  }}

  .charts-title {{
    font-size: 1.5em;
  }}

  canvas {{
    max-height: 250px !important;
  }}
}}
</style>
</head>
<body>

<!-- Navigation from nav.html -->
{nav_html}

<!-- Hero -->
<div class='hero'>
  <h1>📊 Performance Dashboard</h1>
  <p>Track our AI prediction performance with detailed statistics and historical results</p>
</div>

<!-- Main Stats -->
<div class='container'>
  <div class='stats-grid'>
    <div class='stat-card positive'>
      <div class='stat-label'>Overall Win Rate</div>
      <div class='stat-value'>{overall_win_rate:.1f}%</div>
      <div class='stat-subtext'>{total_wins}W - {total_losses}L</div>
    </div>
    <div class='stat-card'>
      <div class='stat-label'>Total Picks</div>
      <div class='stat-value'>{total_picks}</div>
      <div class='stat-subtext'>NHL + NBA Combined</div>
    </div>
    <div class='stat-card'>
      <div class='stat-label'>Best Win Streak</div>
      <div class='stat-value'>{max_win_streak}</div>
      <div class='stat-subtext'>Consecutive winning days</div>
    </div>
    <div class='stat-card'>
      <div class='stat-label'>Current Streak</div>
      <div class='stat-value'>{streak_count} {"🔥" if streak_type == "win" else "❄️"}</div>
      <div class='stat-subtext'>{"Winning" if streak_type == "win" else "Losing"} days</div>
    </div>
  </div>

  <!-- NHL Stats -->
  <div class='sport-section'>
    <div class='sport-header'>
      <div class='sport-icon'>🏒</div>
      <div class='sport-title'>NHL Performance</div>
    </div>
    <div class='sport-stats'>
      <div class='mini-stat'>
        <div class='mini-stat-label'>Win Rate</div>
        <div class='mini-stat-value'>{nhl_win_rate:.1f}%</div>
      </div>
      <div class='mini-stat'>
        <div class='mini-stat-label'>Record</div>
        <div class='mini-stat-value'>{nhl_wins}-{nhl_losses}</div>
      </div>
    </div>
  </div>

  <!-- NBA Stats -->
  <div class='sport-section'>
    <div class='sport-header'>
      <div class='sport-icon'>🏀</div>
      <div class='sport-title'>NBA Performance</div>
    </div>
    <div class='sport-stats'>
      <div class='mini-stat'>
        <div class='mini-stat-label'>Win Rate</div>
        <div class='mini-stat-value'>{nba_win_rate:.1f}%</div>
      </div>
      <div class='mini-stat'>
        <div class='mini-stat-label'>Record</div>
        <div class='mini-stat-value'>{nba_wins}-{nba_losses}</div>
      </div>
    </div>
  </div>

  <!-- Charts Section -->
  <div class='charts-section'>
    <div class='charts-title'>📈 Performance Charts</div>
    <div class='charts-grid'>
      <div class='chart-container'>
        <div class='chart-title'>NHL vs NBA Win Rate Comparison</div>
        <canvas id='winRateChart'></canvas>
      </div>
      <div class='chart-container'>
        <div class='chart-title'>Daily Win/Loss Trend</div>
        <canvas id='dailyTrendChart'></canvas>
      </div>
    </div>
    <div class='charts-grid'>
      <div class='chart-container'>
        <div class='chart-title'>Win Rate Rolling Average (7 days)</div>
        <canvas id='rollingAvgChart'></canvas>
      </div>
      <div class='chart-container'>
        <div class='chart-title'>Monthly Performance Overview</div>
        <canvas id='monthlyChart'></canvas>
      </div>
    </div>
  </div>

"""

    html += """</div>

"""

    # ── Performance Calendar ──
    # Build calendar data from daily_stats (already has combined NHL+NBA per day)
    calendar_data = {date: {"wins": day["wins"], "losses": day["losses"]} for date, day in daily_stats.items()}
    cal_json = json.dumps(calendar_data)
    # Determine which months to show: all distinct year-months in the data
    all_months = sorted({d[:7] for d in daily_stats.keys()})
    months_list = [[int(m.split('-')[0]), int(m.split('-')[1])] for m in all_months]

    html += f"""<!-- Performance Calendar Heatmap -->
<div id='perf-calendar-section' style='max-width: 1400px; margin: 0 auto 40px; padding: 0 20px;'>
  <div style='background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);'>
    <div style='text-align: center; margin-bottom: 30px;'>
      <h2 style='font-size: 2em; font-weight: 700; color: #111827; margin-bottom: 8px;'>📅 Performance Calendar</h2>
      <p style='color: #6b7280; font-size: 1.05em;'>Daily win/loss heatmap — hover a day to see the record</p>
      <div style='display: flex; justify-content: center; gap: 20px; margin-top: 14px; flex-wrap: wrap;'>
        <span style='display:flex;align-items:center;gap:6px;font-size:0.85em;color:#374151;font-weight:600;'><span style='width:14px;height:14px;border-radius:3px;background:#10b981;display:inline-block;'></span>Winning day</span>
        <span style='display:flex;align-items:center;gap:6px;font-size:0.85em;color:#374151;font-weight:600;'><span style='width:14px;height:14px;border-radius:3px;background:#ef4444;display:inline-block;'></span>Losing day</span>
        <span style='display:flex;align-items:center;gap:6px;font-size:0.85em;color:#374151;font-weight:600;'><span style='width:14px;height:14px;border-radius:3px;background:#f59e0b;display:inline-block;'></span>Split day</span>
        <span style='display:flex;align-items:center;gap:6px;font-size:0.85em;color:#374151;font-weight:600;'><span style='width:14px;height:14px;border-radius:3px;background:#e5e7eb;display:inline-block;'></span>No picks</span>
      </div>
    </div>
    <div id='calendar-grid' style='display:flex;gap:24px;justify-content:center;flex-wrap:wrap;'></div>
    <div id='cal-tooltip' style='position:fixed;background:#1f2937;color:white;padding:8px 14px;border-radius:8px;font-size:0.85em;font-weight:600;pointer-events:none;opacity:0;transition:opacity 0.15s;z-index:9999;white-space:nowrap;'></div>
  </div>
</div>
<style>
@media (max-width: 768px) {{
  #perf-calendar-section {{ padding: 0 15px; }}
  #perf-calendar-section > div {{ padding: 20px 15px; }}
  #perf-calendar-section h2 {{ font-size: 1.5em !important; }}
  #calendar-grid {{ gap: 16px !important; }}
  .cal-day {{ width: 30px !important; height: 30px !important; font-size: 0.65em !important; }}
}}
</style>
<script>
(function() {{
  var calData = {cal_json};
  var months = {json.dumps(months_list)};
  var monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  var dayLabels = ['Su','Mo','Tu','We','Th','Fr','Sa'];
  var grid = document.getElementById('calendar-grid');
  var tooltip = document.getElementById('cal-tooltip');

  months.forEach(function(ym) {{
    var year = ym[0], month = ym[1];
    var daysInMonth = new Date(year, month, 0).getDate();
    var firstDow = new Date(year, month - 1, 1).getDay();

    var wrap = document.createElement('div');
    wrap.style.cssText = 'min-width:240px;flex:1;max-width:380px;';

    var title = document.createElement('div');
    title.style.cssText = 'text-align:center;font-weight:800;font-size:1.05em;color:#111827;margin-bottom:10px;';
    title.textContent = monthNames[month-1] + ' ' + year;
    wrap.appendChild(title);

    var table = document.createElement('div');
    table.style.cssText = 'display:grid;grid-template-columns:repeat(7,1fr);gap:4px;';

    dayLabels.forEach(function(d) {{
      var h = document.createElement('div');
      h.style.cssText = 'text-align:center;font-size:0.7em;font-weight:700;color:#9ca3af;padding-bottom:4px;';
      h.textContent = d;
      table.appendChild(h);
    }});

    for (var i = 0; i < firstDow; i++) {{
      table.appendChild(document.createElement('div'));
    }}

    for (var day = 1; day <= daysInMonth; day++) {{
      var dateStr = year + '-' + String(month).padStart(2,'0') + '-' + String(day).padStart(2,'0');
      var cell = document.createElement('div');
      cell.className = 'cal-day';
      cell.style.cssText = 'width:34px;height:34px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:0.75em;font-weight:700;cursor:default;transition:transform 0.1s,box-shadow 0.1s;margin:0 auto;';
      cell.textContent = day;

      var rec = calData[dateStr];
      if (rec) {{
        var wins = rec.wins, losses = rec.losses, total = wins + losses;
        if (wins > losses) {{
          var intensity = Math.min(0.4 + (wins / total) * 0.6, 1.0);
          cell.style.background = 'rgba(16,185,129,' + intensity + ')';
          cell.style.color = 'white';
        }} else if (losses > wins) {{
          var intensity = Math.min(0.4 + (losses / total) * 0.6, 1.0);
          cell.style.background = 'rgba(239,68,68,' + intensity + ')';
          cell.style.color = 'white';
        }} else {{
          cell.style.background = '#f59e0b';
          cell.style.color = 'white';
        }}
        cell.style.cursor = 'pointer';
        (function(c, ds, w, l) {{
          c.addEventListener('mouseenter', function(e) {{
            var pct = (w + l) > 0 ? Math.round(w / (w + l) * 100) : 0;
            tooltip.textContent = ds + ': ' + w + 'W \u2013 ' + l + 'L (' + pct + '%)';
            tooltip.style.opacity = '1';
            c.style.transform = 'scale(1.15)';
            c.style.boxShadow = '0 4px 12px rgba(0,0,0,0.25)';
          }});
          c.addEventListener('mousemove', function(e) {{
            var x = e.clientX + 14, y = e.clientY - 36;
            if (x + 180 > window.innerWidth) x = e.clientX - 190;
            tooltip.style.left = x + 'px';
            tooltip.style.top = y + 'px';
          }});
          c.addEventListener('mouseleave', function() {{
            tooltip.style.opacity = '0';
            c.style.transform = '';
            c.style.boxShadow = '';
          }});
        }})(cell, dateStr, wins, losses);
      }} else {{
        cell.style.background = '#f3f4f6';
        cell.style.color = '#9ca3af';
      }}

      table.appendChild(cell);
    }}

    wrap.appendChild(table);
    grid.appendChild(wrap);
  }});
}})();
</script>

"""

    # ── Collapsible Daily Timeline (after calendar) ──
    html += """<div class='container' style='padding-top: 0;'>
  <details class='timeline-details'>
    <summary class='timeline-summary'>📅 Daily Results Timeline <span class='timeline-toggle-hint'>click to expand</span></summary>
    <div class='timeline' style='margin-top: 15px;'>
"""

    for date in sorted(daily_stats.keys(), reverse=True):
        day = daily_stats[date]
        net_result = day['wins'] - day['losses']
        day_class = 'win-day' if day['wins'] > day['losses'] else ('loss-day' if day['losses'] > day['wins'] else '')
        sports_text = ' + '.join(sorted(day['sports']))

        if net_result > 0:
            net_display = f"<span class='timeline-net net-positive'>+{net_result}</span>"
        elif net_result < 0:
            net_display = f"<span class='timeline-net net-negative'>{net_result}</span>"
        else:
            net_display = f"<span class='timeline-net net-even'>0</span>"

        html += f"""      <div class='timeline-item {day_class}'>
        <div class='timeline-date'>{date}</div>
        <div class='timeline-record'>
          <span class='timeline-wins'>{day['wins']}W</span>
          <span class='timeline-losses'>{day['losses']}L</span>
          {net_display}
          <span class='timeline-sports'>{sports_text}</span>
        </div>
      </div>
"""

    html += """    </div>
  </details>
</div>
<style>
.timeline-details {{ margin-bottom: 40px; }}
.timeline-summary {{
  display: flex; align-items: center; gap: 12px;
  background: white; border-radius: 12px; padding: 18px 24px;
  font-size: 1.4em; font-weight: 700; color: #111827;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08); cursor: pointer;
  list-style: none; border: 2px solid #e5e7eb;
  transition: border-color 0.2s, box-shadow 0.2s;
}}
.timeline-summary::-webkit-details-marker {{ display: none; }}
.timeline-summary::before {{ content: '▶'; font-size: 0.6em; color: #6b7280; transition: transform 0.2s; }}
details[open] .timeline-summary::before {{ transform: rotate(90deg); }}
.timeline-summary:hover {{ border-color: #4a90e2; box-shadow: 0 4px 15px rgba(74,144,226,0.15); }}
details[open] .timeline-summary {{ border-color: #4a90e2; border-radius: 12px 12px 0 0; margin-bottom: 0; }}
.timeline-toggle-hint {{ font-size: 0.55em; color: #9ca3af; font-weight: 500; margin-left: auto; }}
details[open] .timeline-toggle-hint {{ display: none; }}
@media (max-width: 768px) {{
  .timeline-summary {{ font-size: 1.1em; padding: 14px 16px; }}
}}
</style>
"""

    html += """<script>
// Prepare chart data
const dates = [DATES_PLACEHOLDER];
const dailyWins = [DAILY_WINS_PLACEHOLDER];
const dailyLosses = [DAILY_LOSSES_PLACEHOLDER];
const dailyNet = [DAILY_NET_PLACEHOLDER];
const dailyColors = [DAILY_COLORS_PLACEHOLDER];
const cumulativeProfit = [CUMULATIVE_PROFIT_PLACEHOLDER];
const rollingWinRate = [ROLLING_WIN_RATE_PLACEHOLDER];

// Monthly chart data
const monthLabels = [MONTH_LABELS_PLACEHOLDER];
const monthWins = [MONTH_WINS_PLACEHOLDER];
const monthLosses = [MONTH_LOSSES_PLACEHOLDER];
const monthNet = [MONTH_NET_PLACEHOLDER];
const monthColors = [MONTH_COLORS_PLACEHOLDER];
const monthBorderColors = [MONTH_BORDER_COLORS_PLACEHOLDER];
const monthWinRates = [MONTH_WIN_RATES_PLACEHOLDER];

// Chart.js default settings
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.color = '#4b5563';

// Responsive font sizes for mobile
const isMobile = window.innerWidth <= 768;
if (isMobile) {
  Chart.defaults.font.size = 10;
}

// Common responsive options for mobile
const responsiveOptions = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: {
      labels: {
        padding: isMobile ? 10 : 15,
        font: {
          size: isMobile ? 10 : 12
        }
      }
    }
  },
  scales: {
    x: {
      ticks: {
        font: {
          size: isMobile ? 9 : 11
        },
        maxRotation: isMobile ? 45 : 0,
        minRotation: isMobile ? 45 : 0
      }
    },
    y: {
      ticks: {
        font: {
          size: isMobile ? 9 : 11
        }
      }
    }
  }
};

// 1. Win Rate Comparison Chart (NHL vs NBA)
const winRateCtx = document.getElementById('winRateChart').getContext('2d');
new Chart(winRateCtx, {
  type: 'bar',
  data: {
    labels: ['NHL', 'NBA'],
    datasets: [
      {
        label: 'Win Rate',
        data: [NHL_WIN_RATE_PLACEHOLDER, NBA_WIN_RATE_PLACEHOLDER],
        backgroundColor: ['#3b82f6', '#f59e0b'],
        borderRadius: 8,
        barThickness: 80
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return 'Win Rate: ' + context.parsed.y.toFixed(1) + '%';
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: function(value) {
            return value + '%';
          },
          font: {
            size: isMobile ? 9 : 11
          }
        },
        grid: { color: '#e5e7eb' }
      },
      x: {
        grid: { display: false },
        ticks: {
          font: {
            size: isMobile ? 10 : 12
          }
        }
      }
    }
  }
});

// 2. Daily Win/Loss Trend
const dailyTrendCtx = document.getElementById('dailyTrendChart').getContext('2d');
new Chart(dailyTrendCtx, {
  type: 'bar',
  data: {
    labels: dates,
    datasets: [
      {
        label: 'Net Result (W-L)',
        data: dailyNet,
        backgroundColor: dailyColors,
        borderRadius: 4,
        borderWidth: 0
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          padding: isMobile ? 8 : 12,
          font: {
            size: isMobile ? 10 : 12
          },
          generateLabels: function(chart) {
            return [
              {
                text: 'Net Win',
                fillStyle: '#10b981',
                strokeStyle: '#10b981',
                lineWidth: 0
              },
              {
                text: 'Net Loss',
                fillStyle: '#ef4444',
                strokeStyle: '#ef4444',
                lineWidth: 0
              }
            ];
          }
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const value = context.parsed.y;
            const dateIndex = context.dataIndex;
            const wins = dailyWins[dateIndex];
            const losses = dailyLosses[dateIndex];
            if (value > 0) {
              return `Net: +${value} (${wins}W - ${losses}L)`;
            } else if (value < 0) {
              return `Net: ${value} (${wins}W - ${losses}L)`;
            } else {
              return `Net: 0 (${wins}W - ${losses}L)`;
            }
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
          font: {
            size: isMobile ? 9 : 11
          },
          callback: function(value) {
            if (value > 0) return '+' + value;
            return value;
          }
        },
        grid: {
          color: function(context) {
            if (context.tick.value === 0) {
              return '#9ca3af';
            }
            return '#e5e7eb';
          },
          lineWidth: function(context) {
            if (context.tick.value === 0) {
              return 2;
            }
            return 1;
          }
        }
      },
      x: {
        grid: { display: false },
        ticks: {
          font: {
            size: isMobile ? 8 : 10
          },
          maxRotation: isMobile ? 90 : 45,
          minRotation: isMobile ? 90 : 45
        }
      }
    }
  }
});

// 3. Rolling Average Win Rate
const rollingAvgCtx = document.getElementById('rollingAvgChart').getContext('2d');
new Chart(rollingAvgCtx, {
  type: 'line',
  data: {
    labels: dates.slice(6), // Skip first 6 days (need 7 for rolling avg)
    datasets: [{
      label: 'Win Rate %',
      data: rollingWinRate,
      borderColor: '#f59e0b',
      backgroundColor: 'rgba(245, 158, 11, 0.1)',
      borderWidth: 3,
      fill: true,
      tension: 0.4,
      pointRadius: 3,
      pointHoverRadius: 6
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return 'Win Rate: ' + context.parsed.y.toFixed(1) + '%';
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: false,
        min: 0,
        max: 100,
        ticks: {
          callback: function(value) {
            return value + '%';
          },
          font: {
            size: isMobile ? 9 : 11
          }
        },
        grid: { color: '#e5e7eb' }
      },
      x: {
        grid: { display: false },
        ticks: {
          font: {
            size: isMobile ? 8 : 10
          },
          maxRotation: isMobile ? 90 : 45,
          minRotation: isMobile ? 90 : 45
        }
      }
    }
  }
});

// 4. Monthly Performance Chart
const monthlyCtx = document.getElementById('monthlyChart').getContext('2d');
new Chart(monthlyCtx, {
  type: 'bar',
  data: {
    labels: monthLabels,
    datasets: [{
      label: 'Net Result',
      data: monthNet,
      backgroundColor: monthColors,
      borderColor: monthBorderColors,
      borderWidth: 1,
      borderRadius: 4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const net = context.parsed.y;
            const prefix = net >= 0 ? '+' : '';
            return 'Net: ' + prefix + net;
          },
          footer: function(items) {
            const index = items[0].dataIndex;
            const winRate = monthWinRates[index];
            const wins = monthWins[index];
            const losses = monthLosses[index];
            return 'Record: ' + wins + 'W - ' + losses + 'L (' + winRate + '%)';
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: function(value) {
            return value >= 0 ? '+' + value : value;
          },
          font: {
            size: isMobile ? 9 : 11
          }
        },
        grid: {
          color: function(context) {
            if (context.tick.value === 0) {
              return '#6b7280';
            }
            return '#e5e7eb';
          },
          lineWidth: function(context) {
            if (context.tick.value === 0) {
              return 2;
            }
            return 1;
          }
        }
      },
      x: {
        grid: { display: false },
        ticks: {
          font: {
            size: isMobile ? 9 : 11
          }
        }
      }
    }
  }
});

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    document.querySelector(this.getAttribute('href')).scrollIntoView({
      behavior: 'smooth'
    });
  });
});
</script>

</body>
</html>"""

    # Replace chart data placeholders
    html = html.replace('DATES_PLACEHOLDER', ', '.join(chart_dates))
    html = html.replace('DAILY_WINS_PLACEHOLDER', ', '.join(map(str, chart_wins)))
    html = html.replace('DAILY_LOSSES_PLACEHOLDER', ', '.join(map(str, chart_losses)))
    html = html.replace('DAILY_NET_PLACEHOLDER', ', '.join(map(str, daily_net)))
    html = html.replace('DAILY_COLORS_PLACEHOLDER', ', '.join(f"'{c}'" for c in daily_colors))
    html = html.replace('CUMULATIVE_PROFIT_PLACEHOLDER', ', '.join(map(str, cumulative_profit)))
    html = html.replace('ROLLING_WIN_RATE_PLACEHOLDER', ', '.join(map(str, rolling_win_rates)))
    html = html.replace('MONTH_LABELS_PLACEHOLDER', ', '.join(month_labels))
    html = html.replace('MONTH_WINS_PLACEHOLDER', ', '.join(map(str, month_wins)))
    html = html.replace('MONTH_LOSSES_PLACEHOLDER', ', '.join(map(str, month_losses)))
    html = html.replace('MONTH_NET_PLACEHOLDER', ', '.join(map(str, month_net)))
    html = html.replace('MONTH_COLORS_PLACEHOLDER', ', '.join(f"'{c}'" for c in month_colors))
    html = html.replace('MONTH_BORDER_COLORS_PLACEHOLDER', ', '.join(f"'{c}'" for c in month_border_colors))
    html = html.replace('MONTH_WIN_RATES_PLACEHOLDER', ', '.join(map(str, month_win_rates)))
    html = html.replace('NHL_WINS_PLACEHOLDER', str(nhl_wins))
    html = html.replace('NHL_LOSSES_PLACEHOLDER', str(nhl_losses))
    html = html.replace('NBA_WINS_PLACEHOLDER', str(nba_wins))
    html = html.replace('NBA_LOSSES_PLACEHOLDER', str(nba_losses))
    html = html.replace('NHL_WIN_RATE_PLACEHOLDER', f'{nhl_win_rate:.1f}')
    html = html.replace('NBA_WIN_RATE_PLACEHOLDER', f'{nba_win_rate:.1f}')

    return html

def main():
    """Main execution"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", help="Archive season slug, e.g. 2025-26")
    args = parser.parse_args()

    season = args.season  # e.g. "2025-26" or None

    if season:
        nhl_dir = RESULTS_DIR / "nhl" / season
        nba_dir = RESULTS_DIR / "nba" / season
        summary_override = RESULTS_DIR / f"total_results_summary_{season}.txt"
        output_file = BASE_DIR / "docs" / f"performance-{season}.html"
        print(f"🔍 Scanning archive for season {season}...")
    else:
        nhl_dir = RESULTS_DIR / "nhl"
        nba_dir = RESULTS_DIR / "nba"
        summary_override = None
        output_file = OUTPUT_FILE
        print("🔍 Scanning for results files...")

    all_data = []

    if nhl_dir.exists():
        for file in nhl_dir.glob("*.txt"):
            data = parse_results_file(file)
            if data:
                all_data.append(data)
                print(f"  ✓ Parsed {file.name}")

    if nba_dir.exists():
        for file in nba_dir.glob("*.txt"):
            data = parse_results_file(file)
            if data:
                all_data.append(data)
                print(f"  ✓ Parsed {file.name}")

    if not all_data:
        print("❌ No results data found!")
        if not season:
            # Write a minimal placeholder page for the current season with archive link
            nav_path = BASE_DIR / "docs" / "nav.html"
            nav_html = nav_path.read_text(encoding="utf-8") if nav_path.exists() else ""
            placeholder = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Performance Dashboard | Parieur Discipliné</title>
<link rel='icon' type='image/png' href='parieur_discipline_icon_1024.png'>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; }}
.hero {{ background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%); color: white; padding: 60px 20px; text-align: center; }}
.hero h1 {{ font-size: 2.5em; font-weight: 800; margin-bottom: 12px; }}
.hero p {{ font-size: 1.1em; opacity: 0.85; }}
.container {{ max-width: 900px; margin: 60px auto; padding: 0 20px; text-align: center; }}
.card {{ background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
.archive-link {{ display: inline-block; margin-top: 24px; padding: 14px 32px; background: linear-gradient(135deg, #16a34a, #15803d); color: white; text-decoration: none; border-radius: 10px; font-weight: 700; font-size: 1em; }}
</style>
</head>
<body>
{nav_html}
<div style='background:#f0fdf4;border-bottom:2px solid #86efac;padding:10px 20px;text-align:center;font-size:0.95em;font-weight:600;color:#166534;'>
Showing 2026-27 season &nbsp;·&nbsp; <a href='performance-2025-26.html' style='color:#16a34a;text-decoration:underline;'>View 2025-26 Season Archive →</a>
</div>
<div class='hero'>
  <h1>📊 Performance Dashboard</h1>
  <p>2026-27 season results will appear here once games are tracked</p>
</div>
<div class='container'>
  <div class='card'>
    <div style='font-size:3em;margin-bottom:16px;'>🏒🏀</div>
    <h2 style='font-size:1.6em;font-weight:800;color:#1e293b;margin-bottom:12px;'>New Season Starting Soon</h2>
    <p style='color:#64748b;font-size:1.05em;line-height:1.7;'>The 2026-27 NHL and NBA seasons are just getting underway. Daily results will populate this dashboard as games are tracked.</p>
    <a class='archive-link' href='performance-2025-26.html'>📁 View 2025-26 Season Archive</a>
  </div>
</div>
</body>
</html>"""
            output_file.write_text(placeholder)
            print(f"✅ Placeholder dashboard created: {output_file}")
        return

    # Temporarily swap summary path if using an archive season
    global_summary = BASE_DIR / "data" / "bot_results" / "total_results_summary.txt"
    if summary_override and summary_override.exists():
        # Monkey-patch: generate_dashboard_html reads the global path; swap it
        import shutil, tempfile
        tmp = Path(tempfile.mktemp(suffix=".txt"))
        shutil.copy(summary_override, tmp)
        bak = None
        if global_summary.exists():
            bak = Path(tempfile.mktemp(suffix=".txt"))
            shutil.copy(global_summary, bak)
        shutil.copy(tmp, global_summary)

    print(f"\n📊 Generating dashboard from {len(all_data)} result files...")
    html = generate_dashboard_html(all_data)

    # Restore original summary if we swapped it
    if summary_override and summary_override.exists():
        if bak:
            shutil.copy(bak, global_summary)
            bak.unlink(missing_ok=True)
        else:
            global_summary.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)

    # Patch title and hero for archive pages
    if season:
        html = html.replace(
            "<title>Performance Dashboard - Historical Betting Results | Parieur Discipliné</title>",
            f"<title>Performance Dashboard {season} Season | Parieur Discipliné</title>"
        )
        html = html.replace(
            "<h1>📊 Performance Dashboard</h1>",
            f"<h1>📊 Performance Dashboard — {season} Season</h1>"
        )
        html = html.replace(
            "<p>Track our AI prediction performance with detailed statistics and historical results</p>",
            f"<p>Archived results for the {season} NHL &amp; NBA season</p>"
        )
        # Add back-link banner after the hero div
        back_banner = (
            "<div style='background:#fffbeb;border-bottom:2px solid #fbbf24;padding:10px 20px;"
            "text-align:center;font-size:0.95em;font-weight:600;color:#78350f;'>"
            f"Viewing archived {season} season &nbsp;·&nbsp; "
            "<a href='performance.html' style='color:#d97706;text-decoration:underline;'>"
            "← Current Season</a></div>"
        )
        html = html.replace("<div class='container'>", back_banner + "\n<div class='container'>", 1)
    else:
        # Add archive link to current season page
        archive_banner = (
            "<div style='background:#f0fdf4;border-bottom:2px solid #86efac;padding:10px 20px;"
            "text-align:center;font-size:0.95em;font-weight:600;color:#166534;'>"
            "Showing 2026-27 season &nbsp;·&nbsp; "
            "<a href='performance-2025-26.html' style='color:#16a34a;text-decoration:underline;'>"
            "View 2025-26 Season Archive →</a></div>"
        )
        html = html.replace("<div class='container'>", archive_banner + "\n<div class='container'>", 1)

    output_file.write_text(html)
    print(f"✅ Dashboard created: {output_file}")
    print(f"🌐 View at: file://{output_file.absolute()}")

if __name__ == "__main__":
    main()
