#!/usr/bin/env python3
"""
Generate Historical Performance Dashboard
Parses all bot results and creates a comprehensive performance HTML page
"""

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

    # Count wins and losses
    wins = len(re.findall(r'Outcome:\s*\*\*WIN\*\*', content, re.IGNORECASE))
    losses = len(re.findall(r'Outcome:\s*\*\*LOSS\*\*', content, re.IGNORECASE))
    pushes = len(re.findall(r'Outcome:\s*\*\*PUSH\*\*', content, re.IGNORECASE))

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
                m = re.match(r"TOTAL:\s*(\d+)\s*wins?,\s*(\d+)\s*losses?", line)
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

    # Calculate streaks
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
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #1a1a1a; line-height: 1.6; }}

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
  .hero h1 {{ font-size: 2em; }}
  .stat-value {{ font-size: 2em; }}
  .sport-title {{ font-size: 1.5em; }}
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
    </div>
  </div>

  <!-- Daily Timeline -->
  <div class='timeline'>
    <div class='timeline-title'>📅 Daily Results Timeline</div>
"""

    # Add timeline items (reverse chronological)
    for date in sorted(daily_stats.keys(), reverse=True):
        day = daily_stats[date]
        day_class = 'win-day' if day['wins'] > day['losses'] else ('loss-day' if day['losses'] > day['wins'] else '')
        sports_text = ' + '.join(sorted(day['sports']))

        html += f"""    <div class='timeline-item {day_class}'>
      <div class='timeline-date'>{date}</div>
      <div class='timeline-record'>
        <span class='timeline-wins'>{day['wins']}W</span>
        <span class='timeline-losses'>{day['losses']}L</span>
        <span class='timeline-sports'>{sports_text}</span>
      </div>
    </div>
"""

    html += """  </div>
</div>

<script>
// Prepare chart data
const dates = [DATES_PLACEHOLDER];
const dailyWins = [DAILY_WINS_PLACEHOLDER];
const dailyLosses = [DAILY_LOSSES_PLACEHOLDER];
const cumulativeProfit = [CUMULATIVE_PROFIT_PLACEHOLDER];
const rollingWinRate = [ROLLING_WIN_RATE_PLACEHOLDER];

// Chart.js default settings
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.color = '#4b5563';

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
      legend: { display: false },
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
          }
        },
        grid: { color: '#e5e7eb' }
      },
      x: {
        grid: { display: false }
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
        label: 'Wins',
        data: dailyWins,
        backgroundColor: '#10b981',
        borderRadius: 4
      },
      {
        label: 'Losses',
        data: dailyLosses,
        backgroundColor: '#ef4444',
        borderRadius: 4
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { position: 'bottom' }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { stepSize: 1 },
        grid: { color: '#e5e7eb' }
      },
      x: {
        grid: { display: false }
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
      legend: { display: false },
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
          }
        },
        grid: { color: '#e5e7eb' }
      },
      x: {
        grid: { display: false }
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
    html = html.replace('CUMULATIVE_PROFIT_PLACEHOLDER', ', '.join(map(str, cumulative_profit)))
    html = html.replace('ROLLING_WIN_RATE_PLACEHOLDER', ', '.join(map(str, rolling_win_rates)))
    html = html.replace('NHL_WINS_PLACEHOLDER', str(nhl_wins))
    html = html.replace('NHL_LOSSES_PLACEHOLDER', str(nhl_losses))
    html = html.replace('NBA_WINS_PLACEHOLDER', str(nba_wins))
    html = html.replace('NBA_LOSSES_PLACEHOLDER', str(nba_losses))
    html = html.replace('NHL_WIN_RATE_PLACEHOLDER', f'{nhl_win_rate:.1f}')
    html = html.replace('NBA_WIN_RATE_PLACEHOLDER', f'{nba_win_rate:.1f}')

    return html

def main():
    """Main execution"""
    print("🔍 Scanning for results files...")

    all_data = []

    # Parse NHL results
    nhl_dir = RESULTS_DIR / "nhl"
    if nhl_dir.exists():
        for file in nhl_dir.glob("*.txt"):
            data = parse_results_file(file)
            if data:
                all_data.append(data)
                print(f"  ✓ Parsed {file.name}")

    # Parse NBA results
    nba_dir = RESULTS_DIR / "nba"
    if nba_dir.exists():
        for file in nba_dir.glob("*.txt"):
            data = parse_results_file(file)
            if data:
                all_data.append(data)
                print(f"  ✓ Parsed {file.name}")

    if not all_data:
        print("❌ No results data found!")
        return

    print(f"\n📊 Generating dashboard from {len(all_data)} result files...")
    html = generate_dashboard_html(all_data)

    # Write HTML file
    OUTPUT_FILE.write_text(html)
    print(f"✅ Dashboard created: {OUTPUT_FILE}")
    print(f"🌐 View at: file://{OUTPUT_FILE.absolute()}")

if __name__ == "__main__":
    main()
