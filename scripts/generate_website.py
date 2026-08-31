import argparse
import os
import re
import sys
from datetime import datetime, timedelta
from glob import glob
from zoneinfo import ZoneInfo

# Add the scripts directory to path to import calculate_bet_of_the_day_stats
sys.path.insert(0, os.path.dirname(__file__))
from calculate_bet_of_the_day_stats import calculate_botd_stats


def get_latest_file(folder, prefix, ext="txt"):
    files = glob(os.path.join(folder, f"{prefix}_*.{ext}"))
    if not files:
        return None
    latest = max(files, key=os.path.getctime)
    return latest


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_nav_html():
    """Read the navigation bar HTML from the shared nav file."""
    nav_path = os.path.join("docs", "nav.html")
    if os.path.exists(nav_path):
        return read_file(nav_path)
    return ""


def format_date_nice(date_str):
    """Convert 2026-03-03 to Friday, March 3, 2026"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%A, %B %d, %Y").replace(" 0", " ")
    except Exception:
        return date_str


def parse_record(summary_path):
    """Parse the total_results_summary.txt and return NBA/NHL records."""
    nba_record = {"wins": 0, "losses": 0}
    nhl_record = {"wins": 0, "losses": 0}
    if not os.path.exists(summary_path):
        return nba_record, nhl_record
    content = read_file(summary_path)
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
                record = nba_record if current_sport == "nba" else nhl_record
                record["wins"] = int(m.group(1))
                record["losses"] = int(m.group(2))
    return nba_record, nhl_record


def parse_calendar_data(summary_path):
    """Parse total_results_summary.txt and return {date: {wins, losses}} for all days."""
    daily = {}
    if not os.path.exists(summary_path):
        return daily
    content = read_file(summary_path)
    for line in content.splitlines():
        line = line.strip()
        m = re.match(r'(\d{4}-\d{2}-\d{2}):\s*(\d+)\s*wins?,\s*(\d+)\s*loss(?:es)?', line)
        if m:
            date, wins, losses = m.group(1), int(m.group(2)), int(m.group(3))
            if date not in daily:
                daily[date] = {"wins": 0, "losses": 0}
            daily[date]["wins"] += wins
            daily[date]["losses"] += losses
    return daily


def build_calendar_html(calendar_data):
    """Build a 2-month rolling calendar heatmap HTML block."""
    import json
    today = datetime.now()
    # Build list of months to display (current month + previous month, or 2 full months)
    months = []
    for delta in range(1, -1, -1):  # previous month first, then current
        year = today.year
        month = today.month - delta
        if month <= 0:
            month += 12
            year -= 1
        months.append((year, month))

    cal_json = json.dumps(calendar_data)

    html = f"""
<!-- Performance Calendar Heatmap -->
<div id='perf-calendar-section' style='max-width: 1600px; margin: 60px auto 0; padding: 0 20px;'>
  <div style='background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;'>
    <div style='text-align: center; margin-bottom: 30px;'>
      <h2 style='font-size: 2em; font-weight: 800; color: #111827; margin-bottom: 8px;'>📅 Performance Calendar</h2>
      <p style='color: #6b7280; font-size: 1.05em;'>Daily win/loss heatmap — hover a day to see the record</p>
      <div style='display: flex; justify-content: center; gap: 20px; margin-top: 14px; flex-wrap: wrap;'>
        <span style='display:flex;align-items:center;gap:6px;font-size:0.85em;color:#374151;font-weight:600;'><span style='width:14px;height:14px;border-radius:3px;background:#10b981;display:inline-block;'></span>Winning day</span>
        <span style='display:flex;align-items:center;gap:6px;font-size:0.85em;color:#374151;font-weight:600;'><span style='width:14px;height:14px;border-radius:3px;background:#ef4444;display:inline-block;'></span>Losing day</span>
        <span style='display:flex;align-items:center;gap:6px;font-size:0.85em;color:#374151;font-weight:600;'><span style='width:14px;height:14px;border-radius:3px;background:#f59e0b;display:inline-block;'></span>Split day</span>
        <span style='display:flex;align-items:center;gap:6px;font-size:0.85em;color:#374151;font-weight:600;'><span style='width:14px;height:14px;border-radius:3px;background:#e5e7eb;display:inline-block;'></span>No picks</span>
      </div>
    </div>
    <div id='calendar-grid' style='display:flex;gap:30px;justify-content:center;flex-wrap:wrap;'></div>
    <div id='cal-tooltip' style='position:fixed;background:#1f2937;color:white;padding:8px 14px;border-radius:8px;font-size:0.85em;font-weight:600;pointer-events:none;opacity:0;transition:opacity 0.15s;z-index:9999;white-space:nowrap;'></div>
  </div>
</div>
<style>
@media (max-width: 768px) {{
  #perf-calendar-section {{ margin: 40px auto 0; padding: 0 15px; }}
  #perf-calendar-section > div {{ padding: 25px 15px; border-radius: 12px; }}
  #perf-calendar-section h2 {{ font-size: 1.5em !important; }}
  #calendar-grid {{ gap: 20px !important; }}
  .cal-day {{ width: 30px !important; height: 30px !important; font-size: 0.65em !important; }}
}}
</style>
<script>
(function() {{
  var calData = {cal_json};
  var months = {json.dumps([(y, m) for y, m in months])};
  var monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  var dayLabels = ['Su','Mo','Tu','We','Th','Fr','Sa'];
  var grid = document.getElementById('calendar-grid');
  var tooltip = document.getElementById('cal-tooltip');

  months.forEach(function(ym) {{
    var year = ym[0], month = ym[1];
    var daysInMonth = new Date(year, month, 0).getDate();
    var firstDow = new Date(year, month - 1, 1).getDay(); // 0=Sun

    var wrap = document.createElement('div');
    wrap.style.cssText = 'min-width:280px;flex:1;max-width:420px;';

    var title = document.createElement('div');
    title.style.cssText = 'text-align:center;font-weight:800;font-size:1.1em;color:#111827;margin-bottom:12px;';
    title.textContent = monthNames[month-1] + ' ' + year;
    wrap.appendChild(title);

    var table = document.createElement('div');
    table.style.cssText = 'display:grid;grid-template-columns:repeat(7,1fr);gap:5px;';

    // Day-of-week headers
    dayLabels.forEach(function(d) {{
      var h = document.createElement('div');
      h.style.cssText = 'text-align:center;font-size:0.72em;font-weight:700;color:#9ca3af;padding-bottom:4px;';
      h.textContent = d;
      table.appendChild(h);
    }});

    // Empty cells before first day
    for (var i = 0; i < firstDow; i++) {{
      var blank = document.createElement('div');
      table.appendChild(blank);
    }}

    // Day cells
    for (var day = 1; day <= daysInMonth; day++) {{
      var dateStr = year + '-' + String(month).padStart(2,'0') + '-' + String(day).padStart(2,'0');
      var cell = document.createElement('div');
      cell.className = 'cal-day';
      cell.style.cssText = 'width:36px;height:36px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:0.75em;font-weight:700;cursor:default;transition:transform 0.1s,box-shadow 0.1s;margin:0 auto;';
      cell.textContent = day;

      var rec = calData[dateStr];
      if (rec) {{
        var wins = rec.wins, losses = rec.losses;
        var total = wins + losses;
        if (wins > losses) {{
          var intensity = Math.min(0.4 + (wins / total) * 0.6, 1.0);
          cell.style.background = 'rgba(16,185,129,' + intensity + ')';
          cell.style.color = 'white';
        }} else if (losses > wins) {{
          var intensity = Math.min(0.4 + (losses / total) * 0.6, 1.0);
          cell.style.background = 'rgba(239,68,68,' + intensity + ')';
          cell.style.color = 'white';
        }} else {{
          // Exact split
          cell.style.background = '#f59e0b';
          cell.style.color = 'white';
        }}
        cell.style.cursor = 'pointer';
        cell.title = dateStr + ': ' + wins + 'W - ' + losses + 'L';

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
    return html


def format_sport_content(raw_text, sport_emoji, sport_name):
    """Format the raw prediction text into clean markdown sections."""
    lines = raw_text.strip().splitlines()

    # Find the line where the actual picks/recommendations start.
    # We look for lines that START with BET OF THE DAY or a heading with
    # "Unified Final Recommendation" — but not inside a paragraph.
    i = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        upper = stripped.upper()

        # Match lines that are clearly the start of recommendations:
        # "🏆 **BET OF THE DAY**"
        # "### Unified Final Recommendation List"
        # "**Unified Final Recommendation List**"
        # But NOT a sentence like "Here's an analysis... unified final recommendation list:"
        is_bet_of_day = upper.startswith("BET OF THE DAY") or upper.startswith("🏆")
        is_unified_header = (
            (stripped.startswith("#") or stripped.startswith("**"))
            and "UNIFIED FINAL RECOMMENDATION" in upper
        )
        if is_bet_of_day or is_unified_header:
            i = idx
            break
    else:
        # No clear split found — treat everything as recommendations
        return "", raw_text.strip()

    # Build the analysis summary as a collapsible section
    analysis_text = "\n".join(lines[:i]).strip()

    # Build recommendations section
    recs_text = "\n".join(lines[i:]).strip()

    return analysis_text, recs_text


def ensure_line_breaks_after_plays(text):
    """Ensure there is a blank line after each play header line so the
    justification renders on a new line in markdown.

    A 'play header' is a bold line like **Team vs Opponent ...** that is
    immediately followed by a non-blank line (Confidence Level or justification).
    We also handle the BET OF THE DAY header + play combo.
    Additionally, ensure a blank line after the confidence/unit/win probability line.
    """
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        result.append(line)

        # Check if this line is a play header (bold play line)
        is_play_header = (
            stripped.startswith("**") and stripped.endswith("**")
            and ("vs" in stripped.lower() or "over" in stripped.lower() or "under" in stripped.lower() or "@" in stripped)
            and "BET OF THE DAY" not in stripped
            and "Other Recommended" not in stripped
            and "Unified Final" not in stripped
        )

        # Also handle numbered plays like "**1. Team vs Opponent ...**"
        if not is_play_header and stripped.startswith("**") and stripped.endswith("**"):
            inner = stripped.strip("*").strip()
            if re.match(r'^\d+\.?\\s+', inner) and ("vs" in inner.lower() or "@" in inner):
                is_play_header = True

        if is_play_header:
            # Check if next non-blank line exists and is NOT already separated
            if i + 1 < len(lines) and lines[i + 1].strip() != "":
                result.append("")  # Insert blank line

        # Insert a blank line after confidence/unit/win probability line
        if (
            re.match(r"^Confidence Level:\s*", stripped, re.IGNORECASE)
            or re.match(r"^Confidence:\s*", stripped, re.IGNORECASE)
        ):
            # Only insert if next line is not already blank
            if i + 1 < len(lines) and lines[i + 1].strip() != "":
                result.append("")

        i += 1

    return "\n".join(result)


def format_recommendations_as_cards(recs_text):
    """Format plain recommendation text into styled cards."""
    if not recs_text:
        return ""

    lines = recs_text.split('\n')
    formatted = []
    current_card = None
    in_bet_of_day = False
    in_other_plays = False

    for line in lines:
        stripped = line.strip()

        # Detect BET OF THE DAY section
        if '🏆' in stripped and 'BET OF THE DAY' in stripped.upper():
            if current_card:
                formatted.append(format_single_card(current_card, is_featured=in_bet_of_day))
            in_bet_of_day = True
            continue

        # Detect "Other Recommended Plays" section
        if 'Other Recommended' in stripped or 'Unified Final Recommendation' in stripped:
            if current_card:
                formatted.append(format_single_card(current_card, is_featured=in_bet_of_day))
                current_card = None
            in_bet_of_day = False
            in_other_plays = True
            formatted.append(f"\n<h3 style='margin: 30px 0 20px 0; color: #333;'>Other Recommended Plays</h3>\n\n")
            continue

        # Detect new play (starts with ** and contains vs or @)
        if stripped.startswith('**') and ('vs' in stripped or '@' in stripped) and not 'BET OF THE DAY' in stripped.upper():
            # Save previous card
            if current_card:
                formatted.append(format_single_card(current_card, is_featured=in_bet_of_day))

            # Extract play number if present
            play_num = None
            match = re.match(r'^\*\*(\d+)\.\s+(.+?)\*\*', stripped)
            if match:
                play_num = match.group(1)
                bet_line = match.group(2)
            else:
                bet_line = stripped.strip('*')

            current_card = {
                'number': play_num,
                'bet': bet_line,
                'details': [],
                'description': '',
                'changes': ''
            }
            continue

        # Collect card details
        if current_card:
            if 'Confidence Level:' in stripped or 'Confidence:' in stripped:
                current_card['details'].append(stripped)
            elif stripped.startswith('*Changes:') or stripped.startswith('*Change from'):
                current_card['changes'] = stripped.lstrip('*').strip()
            elif stripped and not stripped.startswith('---') and not stripped.startswith('Based on'):
                current_card['description'] += ' ' + stripped

    # Don't forget last card
    if current_card:
        formatted.append(format_single_card(current_card, is_featured=in_bet_of_day))

    return '\n'.join(formatted)


def format_single_card(card, is_featured=False):
    """Format a single recommendation card."""
    if is_featured:
        # Featured "Bet of the Day" card
        card_html = "<div style='background: linear-gradient(135deg, #FFD70015 0%, #FFA50005 100%); border: 2px solid #FFA500; border-radius: 8px; padding: 25px; margin: 20px 0; box-shadow: 0 4px 12px rgba(255,165,0,0.2);'>\n\n"
        card_html += "<div style='display: flex; align-items: center; margin-bottom: 15px;'>\n"
        card_html += "<span style='font-size: 2em; margin-right: 10px;'>🏆</span>\n"
        card_html += "<span style='font-size: 1.3em; font-weight: bold; color: #FF8C00;'>BET OF THE DAY</span>\n"
        card_html += "</div>\n\n"
    else:
        # Regular play card
        card_html = "<div style='background: white; border: 1px solid #e0e0e0; border-left: 4px solid #4a90e2; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>\n\n"
        if card['number']:
            card_html += f"<div style='font-size: 0.85em; color: #4a90e2; font-weight: bold; margin-bottom: 8px;'>PLAY #{card['number']}</div>\n\n"

    # Bet line
    card_html += f"<div style='font-size: 1.25em; font-weight: bold; color: #333; margin-bottom: 12px;'>{card['bet']}</div>\n\n"

    # Details (Confidence, Units, Win Prob)
    if card['details']:
        details_html = ' | '.join(card['details'])
        card_html += f"<div style='font-size: 0.9em; color: #4a90e2; font-weight: 600; margin-bottom: 12px; padding: 8px 0; border-top: 1px solid #f0f0f0; border-bottom: 1px solid #f0f0f0;'>{details_html}</div>\n\n"

    # Description
    if card['description']:
        card_html += f"<div style='color: #666; line-height: 1.6; margin-bottom: 10px;'>{card['description'].strip()}</div>\n\n"

    # Changes (if any)
    if card['changes']:
        card_html += f"<div style='font-size: 0.85em; color: #999; font-style: italic; padding-top: 10px; border-top: 1px dashed #e0e0e0;'>{card['changes']}</div>\n\n"

    card_html += "</div>\n\n"

    return card_html


def format_comparison_analysis(analysis_text):
    """Format the morning vs noon comparison analysis with enhanced visual styling."""
    if not analysis_text:
        return ""

    # Clean up the analysis text
    cleaned = analysis_text.strip()

    # Remove leading intro patterns
    intro_patterns = [
        r"^Here'?s an analysis.*?:\s*\n",
        r"^Here'?s a comparison.*?:\s*\n",
    ]
    for pat in intro_patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip().lstrip("-").strip()

    # Split into comparison section and final recommendations
    parts = re.split(r'═+\s*\n\s*🎯 FINAL UNIFIED RECOMMENDATIONS\s*\n\s*═+', cleaned, maxsplit=1)
    comparison_section = parts[0] if parts else cleaned

    # Start building the styled output
    html = "<details style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);'>\n"
    html += "<summary style='cursor:pointer; font-size:1.2em; font-weight: bold; color: white; padding: 18px 20px; border-radius: 10px;'>"
    html += "<span style='font-size:1.3em; margin-right: 8px;'>📊</span> Morning vs Noon Analysis "
    html += "<span style='color: rgba(255,255,255,0.7); font-weight: normal; font-size: 0.85em;'>(click to expand)</span>"
    html += "</summary>\n\n"

    html += "<div style='background: white; padding: 25px; border-radius: 10px; margin-top: 2px;'>\n"

    # Parse and format the comparison section
    sections = re.split(r'─{20,}', comparison_section)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Handle the header with double bars
        if section.startswith('═'):
            header_match = re.search(r'📊 MORNING vs NOON ANALYSIS', section)
            if header_match:
                html += "<div style='text-align: center; margin-bottom: 25px;'>\n"
                html += "<h2 style='color: #667eea; margin: 0; font-size: 1.8em;'>📊 Morning vs Noon Analysis</h2>\n"
                html += "</div>\n"
                continue

        # Handle Quick Stats section
        if '**📈 QUICK STATS**' in section:
            html += "<div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px; color: white;'>\n"
            html += "<h3 style='margin: 0 0 15px 0; font-size: 1.3em;'>📈 Quick Stats</h3>\n"
            html += "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;'>\n"

            stats = re.findall(r'• (.+?):\s*\[?(\d+|X)\]?\s*(✓|➕|➖|📉📈)?', section)
            for stat_name, stat_value, emoji in stats:
                html += f"<div style='background: rgba(255,255,255,0.2); padding: 12px; border-radius: 8px; text-align: center;'>\n"
                html += f"<div style='font-size: 2em; font-weight: bold;'>{stat_value}</div>\n"
                html += f"<div style='font-size: 0.9em; opacity: 0.9;'>{stat_name} {emoji}</div>\n"
                html += "</div>\n"

            html += "</div></div>\n"
            continue

        # Handle Consistent Plays section
        if '**✓ CONSISTENT PLAYS**' in section:
            html += "<div style='background: #f0fdf4; border-left: 4px solid #10b981; padding: 20px; border-radius: 8px; margin-bottom: 20px;'>\n"
            html += "<h3 style='color: #10b981; margin: 0 0 15px 0; font-size: 1.3em;'>✓ Consistent Plays</h3>\n"
            html += "<div style='color: #666; line-height: 1.8;'>\n"

            # Parse bullet points
            plays = re.findall(r'• \*\*(.+?)\*\* - (.+?)(?=\n  └─|\n• |\n\n|$)', section, re.DOTALL)
            for play, details in plays:
                html += f"<div style='margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px dashed #d1d5db;'>\n"
                html += f"<div style='font-weight: 600; color: #111827; margin-bottom: 8px;'>• {play}</div>\n"
                html += f"<div style='font-size: 0.9em; color: #6b7280; margin-left: 20px;'>{details.strip()}</div>\n"

                # Parse sub-details (└─ lines)
                sub_details = re.findall(r'└─ (.+?)(?=\n|$)', section)
                for sub in sub_details:
                    html += f"<div style='font-size: 0.85em; color: #9ca3af; margin-left: 30px; margin-top: 4px;'>└─ {sub}</div>\n"

                html += "</div>\n"

            html += "</div></div>\n"
            continue

        # Handle Added Plays section
        if '**➕ ADDED PLAYS**' in section:
            html += "<div style='background: #eff6ff; border-left: 4px solid #3b82f6; padding: 20px; border-radius: 8px; margin-bottom: 20px;'>\n"
            html += "<h3 style='color: #3b82f6; margin: 0 0 15px 0; font-size: 1.3em;'>➕ Added Plays</h3>\n"
            html += "<div style='color: #666; line-height: 1.8;'>\n"
            html += format_play_bullets(section)
            html += "</div></div>\n"
            continue

        # Handle Removed Plays section
        if '**➖ REMOVED PLAYS**' in section:
            html += "<div style='background: #fef2f2; border-left: 4px solid #ef4444; padding: 20px; border-radius: 8px; margin-bottom: 20px;'>\n"
            html += "<h3 style='color: #ef4444; margin: 0 0 15px 0; font-size: 1.3em;'>➖ Removed Plays</h3>\n"
            html += "<div style='color: #666; line-height: 1.8;'>\n"
            html += format_play_bullets(section)
            html += "</div></div>\n"
            continue

        # Handle Line Movement Analysis section
        if '**📉📈 LINE MOVEMENT ANALYSIS**' in section:
            html += "<div style='background: #fefce8; border-left: 4px solid #eab308; padding: 20px; border-radius: 8px; margin-bottom: 20px;'>\n"
            html += "<h3 style='color: #eab308; margin: 0 0 15px 0; font-size: 1.3em;'>📉📈 Line Movement Analysis</h3>\n"

            # Extract table content
            table_match = re.search(r'```\n(.*?)\n```', section, re.DOTALL)
            if table_match:
                table_text = table_match.group(1)
                html += format_line_movement_table(table_text)

            html += "</div>\n"
            continue

        # Handle Key Insights section
        if '**💡 KEY INSIGHTS**' in section:
            html += "<div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px; color: white;'>\n"
            html += "<h3 style='margin: 0 0 15px 0; font-size: 1.3em;'>💡 Key Insights</h3>\n"
            html += "<ul style='margin: 0; padding-left: 20px; line-height: 1.8;'>\n"

            insights = re.findall(r'• (.+?)(?=\n• |\n\n|$)', section, re.DOTALL)
            for insight in insights:
                html += f"<li style='margin-bottom: 10px;'>{insight.strip()}</li>\n"

            html += "</ul></div>\n"
            continue

        # Default: format as regular content
        if section:
            formatted = format_generic_section(section)
            if formatted:
                html += formatted

    html += "</div>\n"
    html += "</details>\n\n"

    return html


def format_play_bullets(section_text):
    """Format play bullets with consistent styling."""
    html = ""
    plays = re.findall(r'• \*\*(.+?)\*\*\s*(?:@\s*[\d.]+)?\s*(?:\((.+?)\))?\s*\n  └─ Reason: (.+?)(?=\n• |\n\n|$)', section_text, re.DOTALL)

    for play, extra_info, reason in plays:
        html += f"<div style='margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px dashed #d1d5db;'>\n"
        html += f"<div style='font-weight: 600; color: #111827; margin-bottom: 8px;'>• {play}"
        if extra_info:
            html += f" <span style='font-size: 0.9em; color: #6b7280;'>({extra_info})</span>"
        html += "</div>\n"
        html += f"<div style='font-size: 0.9em; color: #6b7280; margin-left: 20px; line-height: 1.6;'>└─ {reason.strip()}</div>\n"
        html += "</div>\n"

    return html


def format_line_movement_table(table_text):
    """Format the line movement table with nice styling."""
    lines = [line for line in table_text.split('\n') if line.strip() and not line.strip().startswith('─')]

    if len(lines) < 2:
        return "<div style='color: #666;'>No line movement data available</div>"

    html = "<div style='overflow-x: auto; margin-top: 15px;'>\n"
    html += "<table style='width: 100%; border-collapse: collapse; font-size: 0.9em;'>\n"

    # Header row
    headers = [h.strip() for h in lines[0].split('|') if h.strip()]
    html += "<thead style='background: #78350f; color: white;'>\n<tr>\n"
    for header in headers:
        html += f"<th style='padding: 12px 8px; text-align: left; font-weight: 600;'>{header}</th>\n"
    html += "</tr>\n</thead>\n"

    # Data rows
    html += "<tbody>\n"
    for i, line in enumerate(lines[1:]):
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if len(cells) < len(headers):
            continue

        bg_color = '#fefce8' if i % 2 == 0 else 'white'
        html += f"<tr style='background: {bg_color};'>\n"
        for cell in cells:
            html += f"<td style='padding: 10px 8px; border-bottom: 1px solid #e5e7eb;'>{cell}</td>\n"
        html += "</tr>\n"

    html += "</tbody>\n</table>\n</div>\n"
    return html


def format_generic_section(section_text):
    """Format generic sections with basic HTML conversion."""
    if not section_text.strip():
        return ""

    html = "<div style='margin-bottom: 15px; color: #374151; line-height: 1.6;'>\n"

    # Convert **bold** to <strong>
    section_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', section_text)

    # Convert *italic* to <em>
    section_text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', section_text)

    # Convert bullet points
    lines = section_text.split('\n')
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('• ') or stripped.startswith('- '):
            if not in_list:
                html += '<ul style="margin: 10px 0; padding-left: 25px;">\n'
                in_list = True
            item_text = stripped[2:]
            html += f'<li style="margin-bottom: 8px;">{item_text}</li>\n'
        else:
            if in_list:
                html += '</ul>\n'
                in_list = False
            if stripped:
                html += f'<p style="margin: 10px 0;">{stripped}</p>\n'

    if in_list:
        html += '</ul>\n'

    html += "</div>\n"
    return html


def build_sport_section(raw_text, sport_key, sport_name, sport_emoji, record):
    """Build a complete sport section with nice formatting."""
    if not raw_text:
        return f"\n> ℹ️ No {sport_name} predictions available today.\n\n"

    analysis_text, recs_text = format_sport_content(raw_text, sport_emoji, sport_name)

    md = ""

    # Analysis summary (collapsible)
    if analysis_text:
        formatted_analysis = format_comparison_analysis(analysis_text)
        md += formatted_analysis

    # Format recommendations as styled cards
    if recs_text:
        formatted_recs = format_recommendations_section(recs_text)
        md += formatted_recs + "\n\n"

    return md


def format_recommendations_section(recs_text):
    """Parse and format recommendation text into styled cards."""
    if not recs_text:
        return ""

    lines = recs_text.split('\n')
    output = []
    current_pick = None
    is_bet_of_day = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect BET OF THE DAY - skip it since it's already shown in featured picks section
        if '🏆' in line and 'BET OF THE DAY' in line.upper():
            if current_pick:
                output.append(format_pick_card(current_pick, is_bet_of_day))
                current_pick = None
            # Skip the entire Bet of the Day section until we hit "Other Recommended Plays"
            i += 1
            while i < len(lines):
                if 'Other Recommended' in lines[i]:
                    break
                i += 1
            is_bet_of_day = False
            continue

        # Detect "Other Recommended Plays" header - skip it since we're already in the sport section
        if 'Other Recommended' in line:
            if current_pick:
                output.append(format_pick_card(current_pick, is_bet_of_day))
                current_pick = None
            is_bet_of_day = False
            # Don't add the header, just continue parsing
            i += 1
            continue

        # Detect a bet line (starts with ** and looks like a bet)
        # Format: **Team vs Team** or **Team ML vs Team** or **Team +X.X vs Team @ odds**
        is_bet_line = (line.startswith('**') and line.endswith('**') and
                      'BET OF THE DAY' not in line and
                      'Unified Final' not in line and
                      'Other Recommended' not in line and
                      ('vs' in line.lower() or 'ML' in line or 'over' in line.lower() or 'under' in line.lower() or '+' in line or '-' in line))
        if is_bet_line:
            # Save previous pick
            if current_pick:
                output.append(format_pick_card(current_pick, is_bet_of_day))

            # Extract play number if it exists
            play_num = None
            bet_text = line.strip('*')
            if bet_text[0].isdigit() and '.' in bet_text[:3]:
                parts = bet_text.split('.', 1)
                play_num = parts[0].strip()
                bet_text = parts[1].strip() if len(parts) > 1 else bet_text

            current_pick = {
                'number': play_num,
                'bet': bet_text,
                'confidence': '',
                'description': '',
                'changes': ''
            }
            i += 1
            continue

        # Collect details for current pick
        if current_pick:
            if 'Confidence Level:' in line or 'Confidence:' in line:
                current_pick['confidence'] = line
            elif line.startswith('*Changes:') or line.startswith('*Change from'):
                current_pick['changes'] = line.lstrip('*').strip()
            elif line and not line.startswith('---') and not line.startswith('Based on'):
                if current_pick['description']:
                    current_pick['description'] += ' '
                current_pick['description'] += line

        i += 1

    # Don't forget the last pick
    if current_pick:
        output.append(format_pick_card(current_pick, is_bet_of_day))

    # If no picks were added (only Bet of the Day was present), show a message
    if not output:
        output.append("<div style='background: #f9fafb; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; color: #6b7280; font-style: italic;'>")
        output.append("No other recommended plays today.")
        output.append("</div>")

    return '\n'.join(output)


def format_pick_card(pick, is_featured=False):
    """Format a single pick as a styled card."""
    if is_featured:
        # Gold gradient for Bet of the Day
        html = "<div style='background: linear-gradient(135deg, #FFD70020 0%, #FFA50010 100%); border: 2px solid #FFA500; border-radius: 10px; padding: 25px; margin: 20px 0; box-shadow: 0 4px 12px rgba(255,165,0,0.15);'>\n\n"
        html += "<div style='display: inline-block; background: #FFA500; color: white; padding: 6px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; margin-bottom: 15px;'>🏆 BET OF THE DAY</div>\n\n"
    else:
        # Clean white card with blue accent
        html = "<div style='background: white; border: 1px solid #e0e0e0; border-left: 4px solid #4a90e2; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>\n\n"
        if pick['number']:
            html += f"<div style='display: inline-block; background: #4a90e2; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold; margin-bottom: 10px;'>#{pick['number']}</div>\n\n"

    # Extract odds from changes note if not in bet text
    bet_display = pick['bet']
    if '@' not in bet_display and pick['changes']:
        # Try to extract odds from changes note
        # Patterns: "from 1.74 (morning) to 1.77 (noon)" or "remained the same as morning (1.67)"
        odds_match = re.search(r'to (\d+\.\d+) \(noon\)|same as morning \((\d+\.\d+)\)', pick['changes'])
        if odds_match:
            odds = odds_match.group(1) or odds_match.group(2)
            bet_display = f"{bet_display} @ {odds}"

    # Bet line - large and bold
    html += f"<div style='font-size: 1.3em; font-weight: bold; color: #222; margin-bottom: 15px; line-height: 1.3;'>{bet_display}</div>\n\n"

    # Confidence details in a styled bar with colored badge
    if pick['confidence']:
        confidence_badge = get_confidence_badge(pick['confidence'])
        html += f"<div style='background: #f8f9fa; padding: 10px 15px; border-radius: 6px; font-size: 0.9em; color: #555; margin-bottom: 15px;'>{confidence_badge} {pick['confidence']}</div>\n\n"

    # Description
    if pick['description']:
        html += f"<div style='color: #666; line-height: 1.7; margin-bottom: 12px;'>{pick['description'].strip()}</div>\n\n"

    # Changes note in lighter style
    if pick['changes']:
        html += f"<div style='font-size: 0.85em; color: #999; font-style: italic; padding-top: 12px; border-top: 1px dashed #e0e0e0; margin-top: 10px;'>💡 {pick['changes']}</div>\n\n"

    html += "</div>\n\n"
    return html


def parse_last_n_days_results(sport_key, days=5):
    """Parse last N days of results for a sport and return combined record with units."""
    results_dir = os.path.join("data", "bot_results", sport_key)
    results_files = sorted(glob(os.path.join(results_dir, f"{sport_key}_daily_results_*.txt")))

    if not results_files:
        return {"wins": 0, "losses": 0, "units_won": 0, "units_lost": 0, "net_units": 0}

    # Get last N files
    recent_files = results_files[-days:] if len(results_files) >= days else results_files

    total_wins = 0
    total_losses = 0
    total_units_won = 0
    total_units_lost = 0

    for file_path in recent_files:
        try:
            content = read_file(file_path)

            # Parse wins and losses from the summary
            win_match = re.search(r'\*\*Total Wins:\s*(\d+)\*\*', content)
            loss_match = re.search(r'\*\*Total Losses:\s*(\d+)\*\*', content)

            if win_match:
                total_wins += int(win_match.group(1))
            if loss_match:
                total_losses += int(loss_match.group(1))

            # Parse individual picks to calculate units
            lines = content.strip().splitlines()
            current_pick = None

            for line in lines:
                stripped = line.strip()

                # Match numbered pick lines
                pick_match = re.match(r'^\d+\.\s+\*\*(.+?)\*\*', stripped)
                if pick_match:
                    if current_pick:
                        # Process previous pick
                        if current_pick["outcome"] == "WIN":
                            total_units_won += (current_pick["odds"] - 1) * current_pick["units"]
                        elif current_pick["outcome"] == "LOSS":
                            total_units_lost += current_pick["units"]

                    bet_text = pick_match.group(1)
                    odds_match = re.search(r'@\s*(\d+\.?\d*)', bet_text)
                    odds = float(odds_match.group(1)) if odds_match else 1.0

                    current_pick = {
                        "units": 1.0,
                        "odds": odds,
                        "outcome": None
                    }
                    continue

                # Extract confidence/units
                if current_pick and ('Confidence Level:' in stripped or 'Confidence:' in stripped):
                    if 'High' in stripped:
                        current_pick["units"] = 1.5
                    elif 'Medium' in stripped:
                        current_pick["units"] = 1.0
                    continue

                # Match outcome
                if current_pick and re.match(r'^\*\s+Outcome:', stripped):
                    outcome_text = re.sub(r'^\*\s+Outcome:\s*', '', stripped)
                    if "**WIN**" in outcome_text:
                        current_pick["outcome"] = "WIN"
                    elif "**LOSS**" in outcome_text:
                        current_pick["outcome"] = "LOSS"
                    elif "**PUSH**" in outcome_text:
                        current_pick["outcome"] = "PUSH"
                    elif "WIN" in outcome_text.upper() and "not a win" not in outcome_text.lower():
                        current_pick["outcome"] = "WIN"
                    elif "PUSH" in outcome_text.upper():
                        current_pick["outcome"] = "PUSH"
                    elif "LOSS" in outcome_text.upper():
                        current_pick["outcome"] = "LOSS"
                    continue

            # Don't forget last pick
            if current_pick and current_pick["outcome"]:
                if current_pick["outcome"] == "WIN":
                    total_units_won += (current_pick["odds"] - 1) * current_pick["units"]
                elif current_pick["outcome"] == "LOSS":
                    total_units_lost += current_pick["units"]

        except Exception:
            continue

    net_units = total_units_won - total_units_lost
    return {
        "wins": total_wins,
        "losses": total_losses,
        "units_won": total_units_won,
        "units_lost": total_units_lost,
        "net_units": net_units
    }


def parse_this_week_results(sport_key):
    """Parse this week's results (Monday to Sunday) for a sport and return combined record with units."""
    results_dir = os.path.join("data", "bot_results", sport_key)
    results_files = glob(os.path.join(results_dir, f"{sport_key}_daily_results_*.txt"))

    if not results_files:
        return {"wins": 0, "losses": 0, "units_won": 0, "units_lost": 0, "net_units": 0}

    # Get current date and calculate Monday of this week
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    # weekday() returns 0=Monday, 6=Sunday
    days_since_monday = today.weekday()
    monday_this_week = today - timedelta(days=days_since_monday)
    monday_date = monday_this_week.strftime("%Y-%m-%d")

    # Special case: If today is Monday, we also want to include today's file
    # because it contains yesterday's (Sunday's) results from the week that just ended
    is_monday = days_since_monday == 0

    total_wins = 0
    total_losses = 0
    total_units_won = 0
    total_units_lost = 0

    for file_path in results_files:
        # Extract date from filename: {sport}_daily_results_YYYY-MM-DD.txt
        filename = os.path.basename(file_path)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if not date_match:
            continue

        file_date = date_match.group(1)

        # Only include files from this week
        # NOTE: The 6am results workflow creates files with TODAY's date but contains YESTERDAY's games
        # So for "this week" (Mon-Sun games), we need files from Tuesday onwards (Tue-Mon files)
        #
        # Normal days: Include files where monday_date < file_date <= today
        # Monday: Also include today's file (which has last Sunday's results), so we show the complete week
        if is_monday:
            # On Monday: Include files from last Tuesday through today (has last week's Mon-Sun results)
            last_monday = monday_this_week - timedelta(days=7)
            last_monday_str = last_monday.strftime("%Y-%m-%d")
            if file_date <= last_monday_str or file_date > today_str:
                continue
        else:
            # Other days: Include files from this Tuesday onwards
            if file_date <= monday_date or file_date > today_str:
                continue

        try:
            content = read_file(file_path)

            # Parse wins and losses from the summary
            win_match = re.search(r'\*\*Total Wins:\s*(\d+)\*\*', content)
            loss_match = re.search(r'\*\*Total Losses:\s*(\d+)\*\*', content)

            if win_match:
                total_wins += int(win_match.group(1))
            if loss_match:
                total_losses += int(loss_match.group(1))

            # Parse individual picks to calculate units
            lines = content.strip().splitlines()
            current_pick = None

            for line in lines:
                stripped = line.strip()

                # Match numbered pick lines
                pick_match = re.match(r'^\d+\.\s+\*\*(.+?)\*\*', stripped)
                if pick_match:
                    if current_pick:
                        # Process previous pick
                        if current_pick["outcome"] == "WIN":
                            total_units_won += (current_pick["odds"] - 1) * current_pick["units"]
                        elif current_pick["outcome"] == "LOSS":
                            total_units_lost += current_pick["units"]

                    bet_text = pick_match.group(1)
                    odds_match = re.search(r'@\s*(\d+\.?\d*)', bet_text)
                    odds = float(odds_match.group(1)) if odds_match else 1.0

                    current_pick = {
                        "units": 1.0,
                        "odds": odds,
                        "outcome": None
                    }
                    continue

                # Extract confidence/units
                if current_pick and ('Confidence Level:' in stripped or 'Confidence:' in stripped):
                    if 'High' in stripped:
                        current_pick["units"] = 1.5
                    elif 'Medium' in stripped:
                        current_pick["units"] = 1.0
                    continue

                # Match outcome
                if current_pick and re.match(r'^\*\s+Outcome:', stripped):
                    outcome_text = re.sub(r'^\*\s+Outcome:\s*', '', stripped)
                    if "**WIN**" in outcome_text:
                        current_pick["outcome"] = "WIN"
                    elif "**LOSS**" in outcome_text:
                        current_pick["outcome"] = "LOSS"
                    elif "**PUSH**" in outcome_text:
                        current_pick["outcome"] = "PUSH"
                    elif "WIN" in outcome_text.upper() and "not a win" not in outcome_text.lower():
                        current_pick["outcome"] = "WIN"
                    elif "PUSH" in outcome_text.upper():
                        current_pick["outcome"] = "PUSH"
                    elif "LOSS" in outcome_text.upper():
                        current_pick["outcome"] = "LOSS"
                    continue

            # Don't forget last pick
            if current_pick and current_pick["outcome"]:
                if current_pick["outcome"] == "WIN":
                    total_units_won += (current_pick["odds"] - 1) * current_pick["units"]
                elif current_pick["outcome"] == "LOSS":
                    total_units_lost += current_pick["units"]

        except Exception:
            continue

    net_units = total_units_won - total_units_lost
    return {
        "wins": total_wins,
        "losses": total_losses,
        "units_won": total_units_won,
        "units_lost": total_units_lost,
        "net_units": net_units
    }


def parse_all_results(sport_key):
    """Parse all results files for a sport to get season totals with units.

    First tries to read wins/losses from total_results_summary.txt for accuracy,
    then parses individual files for units calculation.
    """
    # Read wins/losses from total_results_summary.txt
    summary_path = os.path.join("data", "bot_results", "total_results_summary.txt")
    total_wins = 0
    total_losses = 0

    if os.path.exists(summary_path):
        try:
            summary_content = read_file(summary_path)
            # Find the sport section
            sport_upper = sport_key.upper()
            sport_section_match = re.search(rf'{sport_upper}:.*?TOTAL:\s*(\d+)\s*wins?,\s*(\d+)\s*losses?',
                                           summary_content, re.DOTALL | re.IGNORECASE)
            if sport_section_match:
                total_wins = int(sport_section_match.group(1))
                total_losses = int(sport_section_match.group(2))
        except Exception:
            pass  # Fall back to parsing individual files

    # Parse individual results files for units calculation
    results_dir = os.path.join("data", "bot_results", sport_key)
    results_files = sorted(glob(os.path.join(results_dir, f"{sport_key}_daily_results_*.txt")))

    if not results_files:
        return {"wins": total_wins, "losses": total_losses, "units_won": 0, "units_lost": 0, "net_units": 0}

    total_units_won = 0
    total_units_lost = 0

    for file_path in results_files:
        try:
            content = read_file(file_path)

            # Parse individual picks to calculate units
            lines = content.strip().splitlines()
            current_pick = None

            for line in lines:
                stripped = line.strip()

                # Match numbered pick lines
                pick_match = re.match(r'^\d+\.\s+\*\*(.+?)\*\*', stripped)
                if pick_match:
                    if current_pick:
                        # Process previous pick
                        if current_pick["outcome"] == "WIN":
                            total_units_won += (current_pick["odds"] - 1) * current_pick["units"]
                        elif current_pick["outcome"] == "LOSS":
                            total_units_lost += current_pick["units"]

                    bet_text = pick_match.group(1)
                    odds_match = re.search(r'@\s*(\d+\.?\d*)', bet_text)
                    odds = float(odds_match.group(1)) if odds_match else 1.0

                    current_pick = {
                        "units": 1.0,
                        "odds": odds,
                        "outcome": None
                    }
                    continue

                # Extract confidence/units
                if current_pick and ('Confidence Level:' in stripped or 'Confidence:' in stripped):
                    if 'High' in stripped:
                        current_pick["units"] = 1.5
                    elif 'Medium' in stripped:
                        current_pick["units"] = 1.0
                    continue

                # Match outcome
                if current_pick and re.match(r'^\*\s+Outcome:', stripped):
                    outcome_text = re.sub(r'^\*\s+Outcome:\s*', '', stripped)
                    if "**WIN**" in outcome_text:
                        current_pick["outcome"] = "WIN"
                    elif "**LOSS**" in outcome_text:
                        current_pick["outcome"] = "LOSS"
                    elif "**PUSH**" in outcome_text:
                        current_pick["outcome"] = "PUSH"
                    elif "WIN" in outcome_text.upper() and "not a win" not in outcome_text.lower():
                        current_pick["outcome"] = "WIN"
                    elif "PUSH" in outcome_text.upper():
                        current_pick["outcome"] = "PUSH"
                    elif "LOSS" in outcome_text.upper():
                        current_pick["outcome"] = "LOSS"
                    continue

            # Don't forget last pick
            if current_pick and current_pick["outcome"]:
                if current_pick["outcome"] == "WIN":
                    total_units_won += (current_pick["odds"] - 1) * current_pick["units"]
                elif current_pick["outcome"] == "LOSS":
                    total_units_lost += current_pick["units"]

        except Exception:
            continue

    net_units = total_units_won - total_units_lost
    return {
        "wins": total_wins,
        "losses": total_losses,
        "units_won": total_units_won,
        "units_lost": total_units_lost,
        "net_units": net_units
    }


def parse_yesterday_results(sport_key):
    """Parse yesterday's results file for a sport and extract summary."""
    from datetime import datetime

    results_dir = os.path.join("data", "bot_results", sport_key)

    # The 6am results workflow creates files with TODAY's date but contains YESTERDAY's games
    # So we need to look for today's file
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # Look for today's results file (which contains yesterday's game results)
    today_file = os.path.join(results_dir, f"{sport_key}_daily_results_{today_str}.txt")

    if os.path.exists(today_file):
        latest_results_file = today_file
    else:
        # Fallback: Get the most recent results file
        results_files = sorted(glob(os.path.join(results_dir, f"{sport_key}_daily_results_*.txt")))
        if not results_files:
            return None
        latest_results_file = max(results_files, key=os.path.getctime)

    try:
        content = read_file(latest_results_file)

        # Extract date from content (first line mentions the actual game date)
        # e.g., "I have reviewed the AI's predictions against the actual game results for 2026-03-03."
        date_match_content = re.search(r'game results for (\d{4}-\d{2}-\d{2})', content)
        if date_match_content:
            results_date = date_match_content.group(1)
        else:
            # Fallback: Extract date from filename
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(latest_results_file))
            results_date = date_match.group(1) if date_match else "Unknown"

        # Find the corresponding prediction file to identify Bet of the Day
        bet_of_the_day_text = None
        predictions_dir = os.path.join("data", "predictions", sport_key)
        pred_file = os.path.join(predictions_dir, f"{sport_key}_daily_predictions_{results_date}.txt")
        if os.path.exists(pred_file):
            pred_content = read_file(pred_file)
            # Extract the bet line after "BET OF THE DAY"
            botd_match = re.search(r'BET OF THE DAY\*\*\s*\*\*(.+?)\*\*', pred_content, re.IGNORECASE)
            if botd_match:
                bet_of_the_day_text = botd_match.group(1).strip()

        # Parse wins and losses from the summary
        wins = 0
        losses = 0

        # Look for "Total Wins: X" and "Total Losses: Y"
        win_match = re.search(r'\*\*Total Wins:\s*(\d+)\*\*', content)
        loss_match = re.search(r'\*\*Total Losses:\s*(\d+)\*\*', content)

        if win_match:
            wins = int(win_match.group(1))
        if loss_match:
            losses = int(loss_match.group(1))

        # Extract individual picks with their outcomes, units, and odds
        picks = []
        lines = content.strip().splitlines()
        current_pick = None

        for line in lines:
            stripped = line.strip()

            # Match numbered pick lines like "1. **Washington Capitals ML vs Utah @ 1.83 - Confidence: High, Units: 1.5u**"
            pick_match = re.match(r'^\d+\.\s+\*\*(.+?)\*\*', stripped)
            if pick_match:
                if current_pick:
                    picks.append(current_pick)

                bet_text = pick_match.group(1)
                # Extract odds from bet text (e.g., "@ 1.83")
                odds_match = re.search(r'@\s*(\d+\.?\d*)', bet_text)
                odds = float(odds_match.group(1)) if odds_match else 1.0

                # Extract units from bet text (e.g., "Units: 1.5u")
                units_match = re.search(r'Units?:\s*(\d+\.?\d*)u', bet_text, re.IGNORECASE)
                units = float(units_match.group(1)) if units_match else 1.0

                # Extract confidence level
                confidence = None
                if 'High' in bet_text:
                    confidence = "High"
                elif 'Medium' in bet_text:
                    confidence = "Medium"

                # Check if this matches the Bet of the Day
                is_botd = False
                if bet_of_the_day_text:
                    # Compare the bet text (removing odds and confidence info for matching)
                    bet_clean = re.sub(r'\s*@\s*[\d.]+.*$', '', bet_text).strip()
                    botd_clean = re.sub(r'\s*@\s*[\d.]+.*$', '', bet_of_the_day_text).strip()
                    if bet_clean.lower() == botd_clean.lower():
                        is_botd = True

                current_pick = {
                    "bet": bet_text,
                    "result": None,
                    "outcome": None,
                    "units": units,
                    "confidence": confidence,
                    "odds": odds,
                    "is_botd": is_botd
                }
                continue

            # Extract confidence level and units from confidence line
            if current_pick and ('Confidence Level:' in stripped or 'Confidence:' in stripped):
                # Extract units (1u or 1.5u) - this takes priority
                units_match = re.search(r'Units?:\s*(\d+\.?\d*)u', stripped, re.IGNORECASE)
                if units_match:
                    current_pick["units"] = float(units_match.group(1))
                else:
                    # Fallback: Extract confidence level and set default units
                    if 'High' in stripped:
                        current_pick["confidence"] = "High"
                        current_pick["units"] = 1.5  # High confidence = 1.5 units
                    elif 'Medium' in stripped:
                        current_pick["confidence"] = "Medium"
                        current_pick["units"] = 1.0  # Medium confidence = 1 unit

                # Extract confidence level (even if units were explicitly set)
                if 'High' in stripped:
                    current_pick["confidence"] = "High"
                elif 'Medium' in stripped:
                    current_pick["confidence"] = "Medium"
                continue

            # Match actual result lines (with * bullet)
            if current_pick and re.match(r'^\*\s+Actual Result:', stripped):
                current_pick["result"] = re.sub(r'^\*\s+Actual Result:\s*', '', stripped)
                continue

            # Match outcome lines (WIN/LOSS/PUSH) (with * bullet)
            if current_pick and re.match(r'^\*\s+Outcome:', stripped):
                outcome_text = re.sub(r'^\*\s+Outcome:\s*', '', stripped)
                # Check for **WIN**, **LOSS**, or **PUSH** (bolded outcomes are the actual results)
                if "**WIN**" in outcome_text:
                    current_pick["outcome"] = "WIN"
                elif "**LOSS**" in outcome_text:
                    current_pick["outcome"] = "LOSS"
                elif "**PUSH**" in outcome_text:
                    current_pick["outcome"] = "PUSH"
                # Fallback to uppercase check only if bolded version not found
                elif "WIN" in outcome_text.upper() and "**LOSS**" not in outcome_text:
                    # Make sure it's actually indicating a win and not "not a win"
                    if "not a win" not in outcome_text.lower():
                        current_pick["outcome"] = "WIN"
                elif "PUSH" in outcome_text.upper():
                    current_pick["outcome"] = "PUSH"
                elif "LOSS" in outcome_text.upper():
                    current_pick["outcome"] = "LOSS"
                continue

        # Don't forget the last pick
        if current_pick:
            picks.append(current_pick)

        # Calculate total units won/lost based on odds
        # Win = profit only (odds - 1) * units
        # Loss = -units
        units_won = sum((pick["odds"] - 1) * pick["units"] for pick in picks if pick["outcome"] == "WIN")
        units_lost = sum(pick["units"] for pick in picks if pick["outcome"] == "LOSS")
        net_units = units_won - units_lost

        return {
            "date": results_date,
            "wins": wins,
            "losses": losses,
            "picks": picks,
            "units_won": units_won,
            "units_lost": units_lost,
            "net_units": net_units
        }
    except Exception as e:
        print(f"Error parsing results for {sport_key}: {e}")
        return None


def format_compact_stats_banner(nhl_results, nba_results, nba_record, nhl_record):
    """Format yesterday's results in a compact grid of square tiles."""
    md = ""

    # Add yesterday's results if available
    if (nhl_results and nhl_results.get("picks")) or (nba_results and nba_results.get("picks")):
        yesterday_date = None
        if nhl_results and nhl_results.get("date"):
            yesterday_date = nhl_results["date"]
        elif nba_results and nba_results.get("date"):
            yesterday_date = nba_results.get("date")

        nice_date = format_date_nice(yesterday_date) if yesterday_date else "Yesterday"

        md += "<div class='yesterday-section'>\n"

        if nhl_results and nhl_results.get("picks"):
            md += "<h3 style='color: #dc2626; margin-top: 0; margin-bottom: 15px; font-size: 1.2em; font-weight: 700;'>🏒 NHL Results</h3>\n\n"
            md += "<div class='results-grid'>\n"

            # Track if we've already marked a Bet of the Day for NHL
            nhl_botd_shown = False

            for i, pick in enumerate(nhl_results["picks"], 1):
                if pick["outcome"] == "WIN":
                    outcome_emoji = "✅"
                    tile_class = "result-tile result-tile-win"
                    # Calculate profit: (odds - 1) * units
                    units_display = f"+{(pick.get('odds', 1.0) - 1) * pick.get('units', 1.0):.2f}u"
                    units_color = "#10b981"
                elif pick["outcome"] == "PUSH":
                    outcome_emoji = "↔️"
                    tile_class = "result-tile result-tile-push"
                    units_display = "0.00u"
                    units_color = "#f59e0b"
                else:  # LOSS
                    outcome_emoji = "❌"
                    tile_class = "result-tile result-tile-loss"
                    # Loss: -units
                    units_display = f"-{pick.get('units', 1.0):.2f}u"
                    units_color = "#ef4444"

                # Check if this is the Bet of the Day (from prediction file)
                is_botd = pick.get('is_botd', False)
                if is_botd:
                    tile_class += " result-tile-featured"
                    nhl_botd_shown = True

                # Shorten bet text for compact display
                bet_short = pick['bet']
                # Remove odds from display to save space
                bet_short = re.sub(r'\s*@\s*\d+\.?\d*', '', bet_short)
                # Remove confidence and units from display
                bet_short = re.sub(r'\s*-\s*Confidence.*', '', bet_short)
                # Truncate long team names if needed
                if len(bet_short) > 50:
                    bet_short = bet_short[:47] + "..."

                md += f"<div class='{tile_class}'>\n"
                if is_botd:
                    md += "<div class='botd-badge'>🔥 BET OF THE DAY</div>\n"
                md += f"<div class='result-tile-emoji'>{outcome_emoji}</div>\n"
                md += f"<div class='result-tile-bet'>{bet_short}</div>\n"
                md += f"<div class='result-tile-units' style='color: {units_color};'>{units_display}</div>\n"
                md += "</div>\n"

            md += "</div>\n\n"

        if nba_results and nba_results.get("picks"):
            md += "<h3 style='color: #ea580c; margin-top: 25px; margin-bottom: 15px; font-size: 1.2em; font-weight: 700;'>🏀 NBA Results</h3>\n\n"
            md += "<div class='results-grid'>\n"

            # Track if we've already marked a Bet of the Day for NBA
            nba_botd_shown = False

            for i, pick in enumerate(nba_results["picks"], 1):
                if pick["outcome"] == "WIN":
                    outcome_emoji = "✅"
                    tile_class = "result-tile result-tile-win"
                    # Calculate profit: (odds - 1) * units
                    units_display = f"+{(pick.get('odds', 1.0) - 1) * pick.get('units', 1.0):.2f}u"
                    units_color = "#10b981"
                elif pick["outcome"] == "PUSH":
                    outcome_emoji = "↔️"
                    tile_class = "result-tile result-tile-push"
                    units_display = "0.00u"
                    units_color = "#f59e0b"
                else:  # LOSS
                    outcome_emoji = "❌"
                    tile_class = "result-tile result-tile-loss"
                    # Loss: -units
                    units_display = f"-{pick.get('units', 1.0):.2f}u"
                    units_color = "#ef4444"

                # Check if this is the Bet of the Day (from prediction file)
                is_botd = pick.get('is_botd', False)
                if is_botd:
                    tile_class += " result-tile-featured"
                    nba_botd_shown = True

                # Shorten bet text for compact display
                bet_short = pick['bet']
                # Remove odds from display to save space
                bet_short = re.sub(r'\s*@\s*\d+\.?\d*', '', bet_short)
                # Remove confidence and units from display
                bet_short = re.sub(r'\s*-\s*Confidence.*', '', bet_short)
                # Truncate long team names if needed
                if len(bet_short) > 50:
                    bet_short = bet_short[:47] + "..."

                md += f"<div class='{tile_class}'>\n"
                if is_botd:
                    md += "<div class='botd-badge'>🔥 BET OF THE DAY</div>\n"
                md += f"<div class='result-tile-emoji'>{outcome_emoji}</div>\n"
                md += f"<div class='result-tile-bet'>{bet_short}</div>\n"
                md += f"<div class='result-tile-units' style='color: {units_color};'>{units_display}</div>\n"
                md += "</div>\n"

            md += "</div>\n\n"

        md += "</div>\n\n"

    return md


def format_dual_bet(raw_text):
    """Format the dual bet of the day into a nicely styled markdown section."""
    lines = raw_text.strip().splitlines()

    md = ""

    # Parse picks from the raw text
    picks = []
    current_pick = None
    footer_lines = []
    in_footer = False

    for line in lines:
        stripped = line.strip()

        # Skip the header line and separator lines
        if stripped.startswith("🔥 DUAL BET OF THE DAY") or stripped.startswith("🔥 BET OF THE DAY"):
            continue
        if stripped == "⸻":
            if current_pick:
                picks.append(current_pick)
                current_pick = None
            continue

        # Detect pick headers (numbered "🎯 PICK #1" or unnumbered "🎯 PICK –")
        if stripped.startswith("🎯 PICK #") or stripped.startswith("🎯 PICK –") or stripped.startswith("🎯 PICK -"):
            current_pick = {"header": stripped, "body": []}
            continue

        # Detect footer (starts with "Two sports" or legacy French closing)
        if stripped.startswith("Two sports") or stripped.startswith("We follow the value") or stripped.startswith("Deux sports") or stripped.startswith("On suit la value"):
            in_footer = True

        if in_footer:
            if stripped:
                footer_lines.append(stripped)
            continue

        # Add body text to current pick
        if current_pick is not None and stripped:
            current_pick["body"].append(stripped)
        elif current_pick is None and stripped and not stripped.startswith("Two leagues") and not stripped.startswith("Deux ligues"):
            # Stray line before any pick – skip
            pass

    # Flush last pick if not yet added
    if current_pick:
        picks.append(current_pick)

    # Render picks as modern card-style layout
    md += "<div class='featured-grid'>\n\n"

    for pick in picks:
        header = pick["header"]
        body_lines = pick["body"]

        # Extract the sport emoji for the card accent
        if "NHL" in header:
            sport_badge_class = "badge-nhl"
            sport_label = "NHL"
        elif "NBA" in header:
            sport_badge_class = "badge-nba"
            sport_label = "NBA"
        else:
            sport_badge_class = "badge-featured"
            sport_label = "Featured"

        # Extract the bet line
        bet_line = header
        for tag in ["🎯 PICK #1 – NHL 🏒", "🎯 PICK #2 – NBA 🏀",
                     "🎯 PICK #1 – NBA 🏀", "🎯 PICK #2 – NHL 🏒",
                     "🎯 PICK – NHL 🏒", "🎯 PICK – NBA 🏀",
                     "🎯 PICK - NHL 🏒", "🎯 PICK - NBA 🏀",
                     "🎯 PICK #1 –", "🎯 PICK #2 –",
                     "🎯 PICK –", "🎯 PICK -"]:
            if bet_line.startswith(tag):
                bet_line = bet_line[len(tag):].strip()
                break

        # Determine pick number
        pick_num = "1" if "#1" in header else "2"

        # Parse confidence and description
        confidence_text = ""
        description_text = ""
        odds_value = None
        for line in body_lines:
            if "Confidence Level:" in line or "Confidence:" in line:
                # Extract only the short confidence summary: "Confidence Level: X, Units: Xu, Win Probability: XX%"
                # The line may be preceded by a long paragraph — find where "Confidence Level:" starts
                conf_start = line.find("Confidence Level:")
                if conf_start == -1:
                    conf_start = line.find("Confidence:")
                # Text before "Confidence Level:" is reasoning, goes to description
                before_conf = line[:conf_start].strip()
                if before_conf:
                    description_text += "\n" + before_conf
                # Extract confidence info up to Win Probability
                conf_portion = line[conf_start:]
                prob_match = re.search(r'(Win Probability:\s*[\d.]+%)\s*(.*)', conf_portion)
                if prob_match:
                    confidence_text = conf_portion[:prob_match.end(1)]
                    remaining = prob_match.group(2).strip()
                    if remaining:
                        description_text += "\n" + remaining
                else:
                    confidence_text = conf_portion
            else:
                description_text += "\n" + line
                # Try to extract odds from the description
                if not odds_value:
                    # Look for patterns like "@ 1.77" or "at 1.91"
                    odds_match = re.search(r'[@at]\s*(\d+\.\d+)', line)
                    if odds_match:
                        odds_value = odds_match.group(1)

        # Add odds to bet line if found and not already present
        if odds_value and '@' not in bet_line:
            bet_line = f"{bet_line} @ {odds_value}"

        # Create card
        md += "<div class='pick-card' style='position: relative;'>\n"
        md += f"<div class='pick-badge {sport_badge_class}'>PICK #{pick_num} — {sport_label}</div>\n"
        md += f"<div class='pick-title'>{bet_line}</div>\n"

        # Add confidence and meta info
        if confidence_text:
            # Extract confidence level
            conf_level = "MEDIUM"
            if "High" in confidence_text:
                conf_level = "HIGH"
            elif "Low" in confidence_text:
                conf_level = "LOW"

            confidence_badge_html = f"<span class='confidence-{conf_level.lower()}'>{conf_level}</span>"
            md += f"<div class='pick-meta'>{confidence_badge_html}<span class='pick-meta-text'>{confidence_text}</span></div>\n"

        if description_text:
            import html as html_module
            md += f"<div class='pick-description reasoning' data-raw='{html_module.escape(description_text.strip(), quote=True)}'></div>\n"

        # Add share button
        pick_id = f"featured-pick-{pick_num}"
        md += f"<button class='share-button' onclick='event.stopPropagation(); handleShare(\"{pick_id}\", \"{sport_label}\")' id='share-btn-{pick_id}'>\n"
        md += "<span style='font-size: 1.5em;'>📤</span>\n"
        md += "<span>Share</span>\n"
        md += "</button>\n"

        md += "</div>\n\n"

    md += "</div>\n\n"

    return md


def get_confidence_badge(text):
    """Return a colored badge for confidence level."""
    text_upper = text.upper()
    if "HIGH" in text_upper:
        return "<span style='display: inline-block; background: #28a745; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75em; font-weight: bold; margin-right: 8px;'>HIGH</span>"
    elif "MEDIUM" in text_upper:
        return "<span style='display: inline-block; background: #ffc107; color: #333; padding: 2px 8px; border-radius: 10px; font-size: 0.75em; font-weight: bold; margin-right: 8px;'>MEDIUM</span>"
    elif "LOW" in text_upper:
        return "<span style='display: inline-block; background: #6c757d; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75em; font-weight: bold; margin-right: 8px;'>LOW</span>"
    return ""


def extract_bet_of_day_from_prediction(content, sport_name, sport_emoji):
    """Extract the Bet of the Day section from a prediction file."""
    lines = content.strip().splitlines()

    # Find "BET OF THE DAY:" section
    bet_start = -1
    for i, line in enumerate(lines):
        if "BET OF THE DAY" in line.upper():
            bet_start = i
            break

    if bet_start == -1:
        return None

    # Extract bet details
    bet_line = ""
    confidence_line = ""
    description = ""

    for i in range(bet_start + 1, len(lines)):
        line = lines[i].strip()
        clean_line = line.strip('*').strip()

        # Stop immediately if we hit another section (like "**Other Recommended Plays**")
        # Use clean_line so bold-wrapped bet lines aren't mistaken for section headers
        if line.startswith("**") and clean_line and not clean_line.startswith("[") and bet_line:
            break

        if not clean_line:
            continue

        # First non-empty line after BET OF THE DAY is the bet
        if not bet_line and not clean_line.startswith("Confidence"):
            bet_line = clean_line
        # Confidence line
        elif clean_line.startswith("Confidence"):
            confidence_line = clean_line
            # Stop after getting confidence - we have everything we need
            break
        # Description (lines between bet and confidence)
        elif bet_line and not clean_line.startswith("Confidence"):
            if description:
                description += "\n"
            description += line

    if not bet_line:
        return None

    # Determine sport badge class
    sport_badge_class = "badge-nhl" if sport_name == "NHL" else "badge-nba"

    # Format as a card
    html = "<div class='pick-card'>\n"

    # Card content container (will grow to fill space)
    html += "<div style='flex-grow: 1;'>\n"
    html += f"<div class='pick-badge {sport_badge_class}'>{sport_emoji} {sport_name}</div>\n"
    html += f"<div class='pick-title'>{bet_line}</div>\n"

    if confidence_line:
        html += f"<div class='pick-meta'>{confidence_line}</div>\n"

    if description:
        import html as html_module
        html += f"<div class='pick-description reasoning' data-raw='{html_module.escape(description, quote=True)}'></div>\n"

    html += "</div>\n"  # Close content container

    # Add share button
    pick_id = f"featured-pick-{sport_name.lower()}"
    html += f"<button class='share-button' onclick='event.stopPropagation(); handleShare(\"{pick_id}\", \"{sport_name}\")' id='share-btn-{pick_id}'>\n"
    html += "<span style='font-size: 1.5em;'>📤</span>\n"
    html += "<span>Share</span>\n"
    html += "</button>\n"

    # Warning box (pushed to bottom with margin-top: auto)
    html += "<div style='margin-top: 15px; padding: 12px; background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 4px;'>\n"
    html += "<div style='font-size: 0.85em; color: #92400e; font-weight: 600;'>⚠️ Preliminary Pick</div>\n"
    html += "<div style='font-size: 0.8em; color: #78350f; margin-top: 4px;'>This pick may change after 3pm line movement analysis</div>\n"
    html += "</div>\n"

    html += "</div>\n"
    return html


def update_latest_predictions(preliminary=False):
    predictions_dir = "data/predictions"
    sports_config = [
        {"key": "nhl", "name": "NHL", "emoji": "🏒"},
        {"key": "nba", "name": "NBA", "emoji": "🏀"},
    ]
    output_html = "docs/index.html"
    summary_path = "data/bot_results/total_results_summary.txt"
    dual_bet_path = os.path.join(predictions_dir, "dual_bet_of_the_day.txt")

    # Parse records
    nba_record, nhl_record = parse_record(summary_path)
    records = {"nba": nba_record, "nhl": nhl_record}

    # Find the latest date among all sports
    latest_dates = []
    sport_files = {}
    for cfg in sports_config:
        sport = cfg["key"]
        folder = os.path.join(predictions_dir, sport)
        latest_text_file = get_latest_file(folder, f"{sport}_daily_predictions", ext="txt")
        sport_files[sport] = latest_text_file
        if latest_text_file:
            date_str = os.path.basename(latest_text_file).split("_")[-1].replace(".txt", "")
            latest_dates.append(date_str)
    overall_latest_date = max(latest_dates) if latest_dates else ""

    # ── Build the page ──
    from datetime import datetime
    nice_date = datetime.now().strftime("%A, %B %-d, %Y").replace(" 0", " ")
    content = ""

    # ── Add HTML head with title and meta tags ──
    content += "<!DOCTYPE html>\n"
    content += "<html lang='en'>\n"
    content += "<head>\n"
    content += "<meta charset='UTF-8'>\n"
    content += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
    content += "<title>Parieur Discipliné - AI Betting Predictions</title>\n"
    content += "<meta name='description' content='AI-powered sports betting predictions for NHL and NBA. Daily picks with analysis and edge calculation.'>\n"

    # Favicons for all devices
    content += "<link rel='icon' type='image/png' href='parieur_discipline_icon_1024.png'>\n"
    content += "<link rel='apple-touch-icon' href='parieur_discipline_icon_1024.png?v=2'>\n"
    content += "<link rel='shortcut icon' href='parieur_discipline_icon_1024.png'>\n"


    # Open Graph meta tags for social media sharing (Facebook, Messenger, WhatsApp, LinkedIn)
    content += "<meta property='og:title' content='Parieur Discipliné - AI Betting Predictions'>\n"
    content += "<meta property='og:description' content='AI-powered sports betting predictions for NHL and NBA. Daily picks with analysis and edge calculation.'>\n"
    content += "<meta property='og:image' content='https://parieurdiscipline.com/parieur_discipline_icon_1024.png'>\n"
    content += "<meta property='og:url' content='https://parieurdiscipline.com/'>\n"
    content += "<meta property='og:type' content='website'>\n"

    # Twitter Card meta tags
    content += "<meta name='twitter:card' content='summary_large_image'>\n"
    content += "<meta name='twitter:title' content='Parieur Discipliné - AI Betting Predictions'>\n"
    content += "<meta name='twitter:description' content='AI-powered sports betting predictions for NHL and NBA. Daily picks with analysis and edge calculation.'>\n"
    content += "<meta name='twitter:image' content='https://parieurdiscipline.com/parieur_discipline_icon_1024.png'>\n"

    content += "</head>\n"
    content += "<body>\n\n"

    # ── Fixed Navigation Bar ──
    content += get_nav_html()

    # ── Sports Blog CSS ──
    content += "<style>\n"
    content += "* { margin: 0; padding: 0; box-sizing: border-box; }\n"
    content += "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1a1a1a; background: #f5f7fa; padding-top: 88px; }\n"
    content += ".main-content { max-width: 100% !important; padding: 0 !important; }\n"
    content += ".blog-container { width: 100%; margin: 0; background: white; }\n"
    content += ".hero-section { background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%); color: white; padding: 50px 40px; text-align: center; position: relative; overflow: hidden; }\n"
    content += ".hero-section::before { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: url('data:image/svg+xml,%3Csvg width=\"60\" height=\"60\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cpath d=\"M0 0h60v60H0z\" fill=\"none\"/%3E%3Cpath d=\"M30 0l30 30-30 30L0 30z\" fill=\"%23ffffff\" fill-opacity=\".03\"/%3E%3C/svg%3E'); opacity: 0.3; }\n"
    content += ".hero-content { position: relative; z-index: 1; }\n"
    content += ".hero-logo { width: 170px; height: 170px; border-radius: 50%; margin: 0 auto 20px auto; display: block; border: 4px solid rgba(255,255,255,0.3); box-shadow: 0 4px 15px rgba(0,0,0,0.2); }\n"
    content += ".blog-title { font-size: 3em; font-weight: 800; margin-bottom: 15px; letter-spacing: -1px; text-shadow: 0 2px 10px rgba(0,0,0,0.2); }\n"
    content += ".blog-subtitle { font-size: 1.3em; opacity: 0.95; margin-bottom: 10px; font-weight: 300; }\n"
    content += ".blog-date { font-size: 1.1em; opacity: 0.85; font-weight: 500; }\n"
    content += ".blog-update-time { font-size: 0.9em; opacity: 0.75; margin-top: 10px; }\n"
    content += ".content-wrapper { padding: 0 60px 40px 60px; max-width: 1600px; margin: 0 auto; }\n"
    content += ".stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px; margin: -35px auto 35px auto; padding: 0 60px; max-width: 1600px; position: relative; z-index: 10; }\n"
    content += ".stat-card { background: white; border-radius: 10px; padding: 18px 15px; text-align: center; box-shadow: 0 3px 12px rgba(0,0,0,0.08); transition: transform 0.2s, box-shadow 0.2s; border: 1px solid #e8ecf1; }\n"
    content += ".stat-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.12); }\n"
    content += ".stat-label { font-size: 0.75em; color: #6b7280; text-transform: uppercase; font-weight: 700; letter-spacing: 0.8px; margin-bottom: 8px; }\n"
    content += ".stat-value { font-size: 2.2em; font-weight: 800; margin-bottom: 6px; background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }\n"
    content += ".stat-record { font-size: 0.9em; color: #4b5563; font-weight: 500; }\n"
    content += ".nav-tabs { display: flex; gap: 10px; margin: 30px 0; padding: 10px; background: #f9fafb; border-radius: 12px; flex-wrap: wrap; }\n"
    content += ".nav-tab { flex: 1; min-width: 120px; padding: 12px 20px; background: white; border: 2px solid #e5e7eb; border-radius: 8px; text-decoration: none; text-align: center; font-weight: 600; font-size: 0.95em; transition: all 0.2s; color: #374151; }\n"
    content += ".nav-tab:hover { border-color: #4a90e2; color: #4a90e2; transform: translateY(-2px); box-shadow: 0 4px 10px rgba(74,144,226,0.1); }\n"
    content += ".section-header { margin: 50px 0 30px 0; padding-bottom: 15px; border-bottom: 3px solid #e5e7eb; }\n"
    content += ".section-title { font-size: 2.2em; font-weight: 800; color: #111827; display: flex; align-items: center; gap: 12px; }\n"
    content += ".section-subtitle { font-size: 0.95em; color: #6b7280; margin-top: 8px; font-weight: 400; }\n"
    content += ".featured-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 40px; margin: 35px 0; }\n"
    content += ".pick-card { background: white; border-radius: 16px; padding: 28px; border: 2px solid #e5e7eb; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); transition: all 0.3s ease; position: relative; display: flex; flex-direction: column; }\n"
    content += ".share-button { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; border-radius: 12px; padding: 12px 20px; cursor: pointer; font-size: 0.9em; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25); margin-top: auto; padding-top: 12px; width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; }\n"
    content += ".share-button:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4); background: linear-gradient(135deg, #059669 0%, #047857 100%); }\n"
    content += ".share-button:disabled { background: #e5e7eb; color: #9ca3af; cursor: not-allowed; box-shadow: none; }\n"
    content += ".pick-card:hover { transform: translateY(-4px); box-shadow: 0 12px 35px rgba(37, 99, 235, 0.15); border-color: #3b82f6; }\n"
    content += ".pick-badge { display: block; text-align: center; padding: 10px 20px; border-radius: 25px; font-size: 0.85em; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 18px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15); animation: pulse 2s ease-in-out infinite; }\n"
    content += "@keyframes pulse { 0%, 100% { transform: scale(1); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15); } 50% { transform: scale(1.05); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25); } }\n"
    content += "@keyframes glow { 0%, 100% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.5), 0 0 30px rgba(255, 215, 0, 0.3); } 50% { box-shadow: 0 0 30px rgba(255, 215, 0, 0.8), 0 0 50px rgba(255, 215, 0, 0.5); } }\n"
    content += ".badge-nhl { background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); }\n"
    content += ".badge-nba { background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%); color: white; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); }\n"
    content += ".badge-featured { background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%); color: white; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); }\n"
    content += ".pick-title { font-size: 1.4em; font-weight: 700; color: #2563eb; margin-bottom: 18px; line-height: 1.4; text-align: center; }\n"
    content += ".pick-meta { display: flex; flex-wrap: wrap; align-items: center; padding: 14px 18px; background: #f9fafb; border-radius: 10px; font-size: 0.9em; margin-bottom: 18px; border: 1px solid #e5e7eb; gap: 8px; }\n"
    content += ".confidence-high { display: inline-flex; align-items: center; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 6px 14px; border-radius: 8px; font-size: 0.8em; font-weight: 800; margin-right: 10px; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3); }\n"
    content += ".confidence-high::before { content: '✓'; margin-right: 6px; font-weight: 900; }\n"
    content += ".confidence-medium { display: inline-flex; align-items: center; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 6px 14px; border-radius: 8px; font-size: 0.8em; font-weight: 800; margin-right: 10px; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3); }\n"
    content += ".confidence-medium::before { content: '→'; margin-right: 6px; font-weight: 900; }\n"
    content += ".pick-meta-text { display: inline; }\n"
    content += ".pick-description { color: #374151; line-height: 1.8; font-size: 1em; font-weight: 500; }\n"
    content += ".reasoning { font-size: 0.9em; color: #4b5563; line-height: 1.6; }\n"
    content += ".reasoning-point { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; padding-left: 4px; line-height: 1.6; }\n"
    content += ".reasoning-point:last-child { margin-bottom: 0; }\n"
    content += ".reasoning-emoji { font-size: 1.2em; flex-shrink: 0; margin-top: 2px; }\n"
    content += ".reasoning-content { flex: 1; display: block; }\n"
    content += ".reasoning-title { font-weight: 700; color: #1f2937; display: block; margin-bottom: 3px; font-size: 0.95em; }\n"
    content += ".reasoning-text { color: #6b7280; display: block; font-size: 0.95em; }\n"
    content += ".yesterday-section { background: #f9fafb; border-radius: 12px; padding: 30px; margin: 40px 0; border: 1px solid #e5e7eb; }\n"
    content += ".result-card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 15px; border-left: 5px solid #e5e7eb; transition: all 0.2s; }\n"
    content += ".result-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }\n"
    content += ".result-win { border-left-color: #10b981; background: linear-gradient(90deg, #ecfdf5 0%, #ffffff 100%); }\n"
    content += ".result-loss { border-left-color: #ef4444; background: linear-gradient(90deg, #fef2f2 0%, #ffffff 100%); }\n"
    content += ".result-push { border-left-color: #f59e0b; background: linear-gradient(90deg, #fffbeb 0%, #ffffff 100%); }\n"
    content += ".results-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px; }\n"
    content += ".result-tile { background: white; border-radius: 8px; padding: 15px; text-align: center; border: 2px solid #e5e7eb; transition: all 0.2s; min-height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; }\n"
    content += ".result-tile:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }\n"
    content += ".result-tile-win { border-color: #10b981; background: linear-gradient(135deg, #ecfdf5 0%, #ffffff 100%); }\n"
    content += ".result-tile-loss { border-color: #ef4444; background: linear-gradient(135deg, #fef2f2 0%, #ffffff 100%); }\n"
    content += ".result-tile-push { border-color: #f59e0b; background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%); }\n"
    content += ".result-tile-emoji { font-size: 2em; margin-bottom: 8px; }\n"
    content += ".result-tile-bet { font-size: 0.85em; color: #374151; font-weight: 500; line-height: 1.3; margin-bottom: 6px; }\n"
    content += ".result-tile-units { font-size: 0.9em; font-weight: 700; margin-top: 6px; }\n"
    content += ".result-tile-featured { border-width: 3px; box-shadow: 0 6px 20px rgba(234, 88, 12, 0.25); transform: scale(1.05); position: relative; }\n"
    content += ".result-tile-featured:hover { transform: scale(1.08) translateY(-2px); box-shadow: 0 8px 30px rgba(234, 88, 12, 0.35); }\n"
    content += ".botd-badge { position: absolute; top: -8px; left: 50%; transform: translateX(-50%); background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.7em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; box-shadow: 0 2px 8px rgba(234, 88, 12, 0.4); }\n"
    content += ".result-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }\n"
    content += ".result-badge { padding: 4px 10px; border-radius: 5px; font-size: 0.75em; font-weight: 700; text-transform: uppercase; }\n"
    content += ".badge-win { background: #10b981; color: white; }\n"
    content += ".badge-loss { background: #ef4444; color: white; }\n"
    content += ".badge-push { background: #f59e0b; color: white; }\n"
    content += ".result-title { font-weight: 600; color: #111827; font-size: 1.05em; }\n"
    content += ".result-score { color: #6b7280; font-size: 0.9em; padding-left: 50px; }\n"
    content += "#back-to-top { position: fixed; bottom: 30px; right: 30px; background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%); color: white; padding: 14px 18px; border-radius: 50%; box-shadow: 0 4px 20px rgba(74,144,226,0.4); cursor: pointer; font-size: 1.3em; display: none; z-index: 1000; border: none; transition: all 0.3s; }\n"
    content += "#back-to-top:hover { transform: translateY(-5px); box-shadow: 0 6px 30px rgba(74,144,226,0.6); }\n"
    content += "@media (max-width: 768px) { .content-wrapper { padding: 0 20px 30px 20px; } .stats-grid { margin: -25px 0px 25px 0px; grid-template-columns: repeat(5, 1fr); gap: 8px; max-width: 100%; padding: 0 15px; overflow-x: auto; -webkit-overflow-scrolling: touch; } .stat-card { padding: 12px 8px; min-width: 110px; } .stat-label { font-size: 0.65em; } .stat-value { font-size: 1.6em; } .stat-record { font-size: 0.75em; } .blog-title { font-size: 1.8em; } .blog-subtitle { font-size: 1em; } .blog-date { font-size: 0.95em; } .blog-update-time { font-size: 0.8em; } .hero-logo { width: 90px; height: 90px; margin-bottom: 15px; } .section-title { font-size: 1.5em; } .section-subtitle { font-size: 0.85em; } .featured-grid { grid-template-columns: 1fr; gap: 20px; margin: 20px 0; } .pick-card { padding: 18px 15px; border-radius: 12px; } .pick-title { font-size: 1.05em; line-height: 1.4; margin-bottom: 15px; } .pick-badge { font-size: 0.7em; padding: 8px 12px; margin-bottom: 12px; } .pick-meta { font-size: 0.8em; padding: 10px 14px; margin-bottom: 15px; flex-direction: column; align-items: flex-start; gap: 10px; } .pick-meta-text { display: block; width: 100%; } .confidence-high, .confidence-medium { display: flex; width: 100%; justify-content: center; margin: 0; padding: 8px 12px; font-size: 0.8em; } .confidence-high::before, .confidence-medium::before { margin-right: 8px; } .pick-description { font-size: 0.9em; line-height: 1.7; } .hero-section { padding: 30px 20px; } .nav-tabs { gap: 8px; padding: 8px; } .nav-tab { padding: 10px 12px; font-size: 0.85em; min-width: 100px; } .result-card { padding: 15px; } .result-title { font-size: 0.95em; } .result-score { font-size: 0.85em; padding-left: 40px; } .results-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; } .result-tile { min-height: 90px; padding: 12px; } .result-tile-featured { min-height: 100px; } .result-tile-emoji { font-size: 1.8em; } .result-tile-bet { font-size: 0.8em; } .result-tile-units { font-size: 0.85em; } .botd-badge { font-size: 0.65em; padding: 3px 10px; top: -6px; } .yesterday-section { padding: 20px; } #back-to-top { bottom: 20px; right: 20px; padding: 12px 16px; font-size: 1.1em; } }\n"
    content += "</style>\n\n"

    content += "<div class='blog-container'>\n\n"

    # ── Hero Section ──
    # Get time since last update from the most recent prediction file
    latest_file_for_timestamp = None
    for sport_file in sport_files.values():
        if sport_file:
            latest_file_for_timestamp = sport_file
            break
    time_since = get_time_since_update(latest_file_for_timestamp) if latest_file_for_timestamp else "Unknown"

    content += "<div class='hero-section'>\n"
    content += "<div class='hero-content'>\n"
    content += "<img src='parieur_discipline_icon_1024.png' alt='Parieur Discipliné' class='hero-logo'>\n"
    content += "<div class='blog-title'>🎯 Parieur Discipliné</div>\n"
    content += "<div class='blog-subtitle'>AI-Powered NHL & NBA Betting Predictions</div>\n"
    content += f"<div class='blog-date'>{nice_date}</div>\n"
    content += f"<div class='blog-update-time'>⏱️ {time_since}</div>\n"
    subscriber_count = os.getenv('SUBSCRIBER_LIST', '')
    # Count emails separated by commas
    if subscriber_count:
        subscriber_count = len([email.strip() for email in subscriber_count.split(',') if email.strip()])
    else:
        subscriber_count = 9  # Default count when SUBSCRIBER_LIST is not set

    # Combined subscriber count + subscribe banner (bold eye-catching style)
    content += "<div style='margin-top: 30px; text-align: center;'>\n"
    content += "<div style='display: inline-block; background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); border-radius: 50px; padding: 12px 28px; box-shadow: 0 6px 25px rgba(251, 191, 36, 0.5); animation: pulse 2s ease-in-out infinite; border: 2px solid #fbbf24;'>\n"
    content += "<span style='color: #78350f; font-size: 1em; margin-right: 10px; font-weight: 700;'>📬 Daily Picks</span>\n"
    content += "<span id='hero-subscribe-wrap' style='display:inline-flex;align-items:center;gap:6px;'>\n"
    content += "  <input id='hero-email' type='email' placeholder='your@email.com' style='padding:7px 14px;border-radius:25px;border:none;font-size:0.85em;outline:none;width:170px;' />\n"
    content += "  <button onclick='heroSubscribe()' style='display:inline-block;background:white;color:#f59e0b;padding:8px 18px;border-radius:25px;border:none;cursor:pointer;font-weight:800;font-size:0.9em;box-shadow:0 3px 12px rgba(0,0,0,0.2);transition:all 0.3s;text-transform:uppercase;letter-spacing:0.5px;' onmouseover=\"this.style.transform='scale(1.05)'\" onmouseout=\"this.style.transform='scale(1)'\">Subscribe</button>\n"
    content += "</span>\n"
    content += "<span id='hero-subscribe-msg' style='display:none;font-size:0.85em;font-weight:700;margin-left:6px;'></span>\n"
    content += "<script>\n"
    content += "function heroSubscribe() {\n"
    content += "  var email = document.getElementById('hero-email').value.trim();\n"
    content += "  var msg = document.getElementById('hero-subscribe-msg');\n"
    content += "  if (!email) { return; }\n"
    content += "  fetch('/api/subscribe', {\n"
    content += "    method: 'POST',\n"
    content += "    headers: { 'Content-Type': 'application/json' },\n"
    content += "    body: JSON.stringify({ email: email })\n"
    content += "  }).then(function(r) { return r.json(); }).then(function(d) {\n"
    content += "    msg.style.display = 'inline';\n"
    content += "    if (d.success) {\n"
    content += "      document.getElementById('hero-subscribe-wrap').style.display = 'none';\n"
    content += "      msg.style.color = '#78350f';\n"
    content += "      msg.textContent = '\\u2705 Subscribed!';\n"
    content += "    } else if (d.alreadySubscribed) {\n"
    content += "      msg.style.color = '#78350f';\n"
    content += "      msg.textContent = '\\u2705 Already subscribed!';\n"
    content += "    } else {\n"
    content += "      msg.style.color = '#ef4444';\n"
    content += "      msg.textContent = d.error || 'Error, try again.';\n"
    content += "    }\n"
    content += "  }).catch(function() {\n"
    content += "    msg.style.display = 'inline';\n"
    content += "    msg.style.color = '#ef4444';\n"
    content += "    msg.textContent = 'Error, try again.';\n"
    content += "  });\n"
    content += "}\n"
    content += "document.addEventListener('keydown', function(e) {\n"
    content += "  if (e.key === 'Enter' && document.activeElement === document.getElementById('hero-email')) heroSubscribe();\n"
    content += "});\n"
    content += "</script>\n"
    content += "</div>\n"
    content += "</div>\n"
    content += "<style>@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.02); } }</style>\n"

    content += "</div>\n"
    content += "</div>\n\n"

    # ── Quick Stats Row ──
    nhl_yesterday = parse_yesterday_results("nhl")
    nba_yesterday = parse_yesterday_results("nba")

    # Calculate yesterday's stats including units
    yesterday_total_w = (nhl_yesterday["wins"] if nhl_yesterday else 0) + (nba_yesterday["wins"] if nba_yesterday else 0)
    yesterday_total_l = (nhl_yesterday["losses"] if nhl_yesterday else 0) + (nba_yesterday["losses"] if nba_yesterday else 0)
    yesterday_wr = f"{(yesterday_total_w / (yesterday_total_w + yesterday_total_l) * 100):.0f}%" if (yesterday_total_w + yesterday_total_l) > 0 else "N/A"

    # Calculate yesterday's units
    yesterday_units_won = (nhl_yesterday.get("units_won", 0) if nhl_yesterday else 0) + (nba_yesterday.get("units_won", 0) if nba_yesterday else 0)
    yesterday_units_lost = (nhl_yesterday.get("units_lost", 0) if nhl_yesterday else 0) + (nba_yesterday.get("units_lost", 0) if nba_yesterday else 0)
    yesterday_net_units = yesterday_units_won - yesterday_units_lost
    yesterday_units_display = f"+{yesterday_net_units:.2f} units" if yesterday_net_units >= 0 else f"{yesterday_net_units:.2f} units"

    # Calculate this week's stats (Monday to Sunday) including units
    nhl_week = parse_this_week_results("nhl")
    nba_week = parse_this_week_results("nba")
    week_total_w = nhl_week["wins"] + nba_week["wins"]
    week_total_l = nhl_week["losses"] + nba_week["losses"]
    week_wr = f"{(week_total_w / (week_total_w + week_total_l) * 100):.0f}%" if (week_total_w + week_total_l) > 0 else "N/A"

    # Calculate this week's units
    week_net_units = nhl_week["net_units"] + nba_week["net_units"]
    week_units_display = f"+{week_net_units:.2f} units" if week_net_units >= 0 else f"{week_net_units:.2f} units"

    # Calculate season stats including units
    nhl_all = parse_all_results("nhl")
    nba_all = parse_all_results("nba")
    overall_total_w = nhl_all["wins"] + nba_all["wins"]
    overall_total_l = nhl_all["losses"] + nba_all["losses"]
    overall_wr = f"{(overall_total_w / (overall_total_w + overall_total_l) * 100):.0f}%" if (overall_total_w + overall_total_l) > 0 else "N/A"

    # Calculate season units
    season_net_units = nhl_all["net_units"] + nba_all["net_units"]
    season_units_display = f"+{season_net_units:.2f} units" if season_net_units >= 0 else f"{season_net_units:.2f} units"

    content += "<div class='stats-grid'>\n"

    # Yesterday's Win Rate Card with Units
    content += "<div class='stat-card'>\n"
    content += "<div class='stat-label'>Yesterday</div>\n"
    content += f"<div class='stat-value'>{yesterday_wr}</div>\n"
    content += f"<div class='stat-record'>{yesterday_total_w}W - {yesterday_total_l}L</div>\n"
    content += f"<div class='stat-record' style='margin-top: 5px; color: {'#10b981' if yesterday_net_units >= 0 else '#ef4444'}; font-weight: 600;'>{yesterday_units_display}</div>\n"
    content += "</div>\n"

    # This Week Win Rate Card with Units
    content += "<div class='stat-card'>\n"
    content += "<div class='stat-label'>This Week</div>\n"
    content += f"<div class='stat-value'>{week_wr}</div>\n"
    content += f"<div class='stat-record'>{week_total_w}W - {week_total_l}L</div>\n"
    content += f"<div class='stat-record' style='margin-top: 5px; color: {'#10b981' if week_net_units >= 0 else '#ef4444'}; font-weight: 600;'>{week_units_display}</div>\n"
    content += "</div>\n"

    # All Time Win Rate Card with Units
    content += "<div class='stat-card'>\n"
    content += "<div class='stat-label'>All Time</div>\n"
    content += f"<div class='stat-value'>{overall_wr}</div>\n"
    content += f"<div class='stat-record'>{overall_total_w}W - {overall_total_l}L</div>\n"
    content += f"<div class='stat-record' style='margin-top: 5px; color: {'#10b981' if season_net_units >= 0 else '#ef4444'}; font-weight: 600;'>{season_units_display}</div>\n"
    content += "</div>\n"

    # NHL Record Card with Units
    nhl_wr = f"{(nhl_all['wins'] / (nhl_all['wins'] + nhl_all['losses']) * 100):.0f}%" if (nhl_all['wins'] + nhl_all['losses']) > 0 else "N/A"
    nhl_units_display = f"+{nhl_all['net_units']:.2f} units" if nhl_all['net_units'] >= 0 else f"{nhl_all['net_units']:.2f} units"
    content += "<div class='stat-card'>\n"
    content += "<div class='stat-label'>🏒 NHL</div>\n"
    content += f"<div class='stat-value'>{nhl_wr}</div>\n"
    content += f"<div class='stat-record'>{nhl_all['wins']}W - {nhl_all['losses']}L</div>\n"
    content += f"<div class='stat-record' style='margin-top: 5px; color: {'#10b981' if nhl_all['net_units'] >= 0 else '#ef4444'}; font-weight: 600;'>{nhl_units_display}</div>\n"
    content += "</div>\n"

    # NBA Record Card with Units
    nba_wr = f"{(nba_all['wins'] / (nba_all['wins'] + nba_all['losses']) * 100):.0f}%" if (nba_all['wins'] + nba_all['losses']) > 0 else "N/A"
    nba_units_display = f"+{nba_all['net_units']:.2f} units" if nba_all['net_units'] >= 0 else f"{nba_all['net_units']:.2f} units"
    content += "<div class='stat-card'>\n"
    content += "<div class='stat-label'>🏀 NBA</div>\n"
    content += f"<div class='stat-value'>{nba_wr}</div>\n"
    content += f"<div class='stat-record'>{nba_all['wins']}W - {nba_all['losses']}L</div>\n"
    content += f"<div class='stat-record' style='margin-top: 5px; color: {'#10b981' if nba_all['net_units'] >= 0 else '#ef4444'}; font-weight: 600;'>{nba_units_display}</div>\n"
    content += "</div>\n"

    content += "</div>\n\n"

    # ── Content wrapper starts here ──
    content += "<div class='content-wrapper'>\n\n"

    # ── Featured Picks Section ──
    # Check preliminary flag to determine which picks to show
    show_preliminary = preliminary
    featured_content = ""

    if preliminary:
        # Show 7am preliminary picks from daily_runs folder - use TODAY's date
        from datetime import date as date_module
        today_str = date_module.today().isoformat()

        nhl_7am_path = os.path.join(predictions_dir, "nhl", "daily_runs", f"nhl_daily_predictions_{today_str}_7am.txt")
        nba_7am_path = os.path.join(predictions_dir, "nba", "daily_runs", f"nba_daily_predictions_{today_str}_7am.txt")

        # Extract bet of the day from each 7am file and show as featured picks
        featured_picks = []
        if os.path.exists(nhl_7am_path):
            nhl_7am_content = read_file(nhl_7am_path).strip()
            nhl_pick = extract_bet_of_day_from_prediction(nhl_7am_content, "NHL", "🏒")
            if nhl_pick:
                featured_picks.append(nhl_pick)

        if os.path.exists(nba_7am_path):
            nba_7am_content = read_file(nba_7am_path).strip()
            nba_pick = extract_bet_of_day_from_prediction(nba_7am_content, "NBA", "🏀")
            if nba_pick:
                featured_picks.append(nba_pick)

        if featured_picks:
            featured_content = "<div class='featured-grid'>\n"
            for pick in featured_picks:
                featured_content += pick
            featured_content += "</div>\n"
    else:
        # Show 3pm final featured picks from dual bet file (only if written today)
        if os.path.exists(dual_bet_path):
            file_date = datetime.fromtimestamp(os.path.getmtime(dual_bet_path)).date()
            today = datetime.now(tz=ZoneInfo('America/Toronto')).date()
            if file_date == today:
                dual_content = read_file(dual_bet_path).strip()
                if dual_content:
                    featured_content = format_dual_bet(dual_content)

    if featured_content:
        content += "<div id='featured-picks' style='position: relative; margin: 0 -15px;'>\n"

        if show_preliminary:
            # Preliminary picks banner (7am) - gold like final picks
            content += "<div class='premium-banner' style='background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #fbbf24 100%); padding: 8px; text-align: center; border-radius: 12px 12px 0 0; margin-bottom: -5px; box-shadow: 0 4px 20px rgba(245, 158, 11, 0.5); animation: shine 3s ease-in-out infinite;'>\n"
            content += "<div style='color: #78350f; font-weight: 900; font-size: 0.9em; letter-spacing: 2px; text-transform: uppercase; text-shadow: 0 1px 2px rgba(255, 255, 255, 0.5);'>⏰ Preliminary Picks (7am) - Final Picks Coming at 3pm ⏰</div>\n"
            content += "</div>\n"
        else:
            # Final picks banner (3pm)
            content += "<div class='premium-banner' style='background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #fbbf24 100%); padding: 8px; text-align: center; border-radius: 12px 12px 0 0; margin-bottom: -5px; box-shadow: 0 4px 20px rgba(245, 158, 11, 0.5); animation: shine 3s ease-in-out infinite;'>\n"
            content += "<div style='color: #78350f; font-weight: 900; font-size: 0.9em; letter-spacing: 2px; text-transform: uppercase; text-shadow: 0 1px 2px rgba(255, 255, 255, 0.5);'>⭐ Today's Premium Selections ⭐</div>\n"
            content += "</div>\n"

        content += "<style>@keyframes shine { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.1); } } @media (max-width: 768px) { #featured-picks { margin: 0 -10px; } .premium-banner { border-radius: 8px 8px 0 0; padding: 6px; } .premium-banner div { font-size: 0.75em; letter-spacing: 1px; } .section-title { font-size: 1.4em !important; line-height: 1.2; } .section-subtitle { font-size: 0.9em !important; } }</style>\n"
        content += "<div class='premium-content' style='background: linear-gradient(180deg, #fffbeb 0%, #ffffff 100%); padding: 25px 30px 30px 30px; border-radius: 0 0 16px 16px; box-shadow: 0 10px 40px rgba(245, 158, 11, 0.15); border: 3px solid #fbbf24; border-top: none;'>\n"
        content += "<style>@media (max-width: 768px) { .premium-content { padding: 15px; border-radius: 0 0 8px 8px; border-width: 2px; } }</style>\n"

        # Add section header for both preliminary and final picks
        content += "<div class='section-header' style='margin-bottom: 20px; text-align: center;'>\n"
        content += "<div class='section-title' style='font-size: 2em; background: linear-gradient(135deg, #f59e0b 0%, #dc2626 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 8px; display: block !important; text-align: center !important; justify-content: center;'>🔥 Featured Picks of the Day</div>\n"
        if show_preliminary:
            content += "<div class='section-subtitle' style='font-size: 1.05em; color: #78350f; font-weight: 600; margin-bottom: 12px;'>Early morning selections - Final picks with line movement analysis at 3pm</div>\n"
        else:
            content += "<div class='section-subtitle' style='font-size: 1.05em; color: #78350f; font-weight: 600; margin-bottom: 12px;'>Our top AI-selected plays with the highest edge</div>\n"

        # Add Bet of the Day stats in a prominent position below subtitle (for both 7am and 3pm)
        try:
            import io
            import contextlib
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                botd_data = calculate_botd_stats()

            botd_wins = botd_data['combined']['wins']
            botd_losses = botd_data['combined']['losses']
            botd_wr_value = botd_data['combined']['win_rate']

            # Format with appropriate color and styling
            if botd_wr_value >= 50:
                stats_color = "#15803d"  # Green
                bg_color = "#f0fdf4"  # Light green bg
                border_color = "#86efac"
            else:
                stats_color = "#b91c1c"  # Red
                bg_color = "#fef2f2"  # Light red bg
                border_color = "#fecaca"

            content += f"<div style='margin-top: 0px; padding: 10px 18px; background: {bg_color}; border: 2px solid {border_color}; border-radius: 8px; display: inline-block;'>\n"
            content += f"<div style='color: {stats_color}; font-weight: 700; font-size: 1em;'>📊 Track Record: <span style='font-size: 1.15em;'>{botd_wins}-{botd_losses}</span> ({botd_wr_value:.1f}%)</div>\n"
            content += "</div>\n"
        except Exception as e:
            # Silently skip if stats can't be calculated
            pass

        content += "</div>\n"

        content += featured_content

        # Add CTA button to Today's page (different text for 7am vs 3pm)
        content += "<!-- CTA Button to Today's Page -->\n"
        content += "<div style='text-align: center; margin-top: 30px;'>\n"

        if show_preliminary:
            # 7am: Inform users that full picks come at 3pm
            content += "<div style='padding: 20px; background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-radius: 12px; border: 2px solid #60a5fa; max-width: 600px; margin: 0 auto;'>\n"
            content += "<div style='font-size: 1.2em; font-weight: 700; color: #1e3a8a; margin-bottom: 8px;'>⏰ Full Picks Coming Soon</div>\n"
            content += "<div style='font-size: 1em; color: #1e40af; margin-bottom: 15px;'>Complete picks table with all games and detailed analysis will be available at <strong>3:00 PM ET</strong></div>\n"
            content += "<div style='margin-bottom: 15px;'><a href='early-picks.html' style='display: inline-block; padding: 10px 24px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 0.95em; box-shadow: 0 3px 10px rgba(59, 130, 246, 0.4); transition: all 0.3s ease;' onmouseover='this.style.transform=\"translateY(-2px)\"; this.style.boxShadow=\"0 5px 15px rgba(59, 130, 246, 0.5)\";' onmouseout='this.style.transform=\"translateY(0)\"; this.style.boxShadow=\"0 3px 10px rgba(59, 130, 246, 0.4)\";'>📋 View Early 7am Picks →</a></div>\n"
            content += "<div style='font-size: 0.9em; color: #3b82f6;'>Above are today's featured bets to get you started</div>\n"
            content += "</div>\n"
        else:
            # 3pm: Regular CTA to view all picks
            content += "<a href='daily-picks.html' style='display: inline-block; padding: 16px 40px; background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%); color: white; text-decoration: none; border-radius: 12px; font-weight: 700; font-size: 1.1em; box-shadow: 0 4px 15px rgba(74, 144, 226, 0.4); transition: all 0.3s ease; border: 2px solid transparent;' onmouseover='this.style.transform=\"translateY(-2px)\"; this.style.boxShadow=\"0 6px 20px rgba(74, 144, 226, 0.5)\";' onmouseout='this.style.transform=\"translateY(0)\"; this.style.boxShadow=\"0 4px 15px rgba(74, 144, 226, 0.4)\";'>\n"
            content += "🎯 View All Today's Picks →\n"
            content += "</a>\n"
            content += "<p style='margin-top: 12px; color: #6b7280; font-size: 0.95em;'>See all NHL and NBA predictions with detailed analysis</p>\n"
            # Pick card share/download button (only shown if image exists)
            content += "<div id='pick-card-share' style='margin-top: 20px; display: none;'>\n"
            content += "<a id='pick-card-dl-btn' href='picks/pick_card_latest.png' download style='display: inline-flex; align-items: center; gap: 8px; padding: 14px 32px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #1a1a1a; text-decoration: none; border-radius: 12px; font-weight: 700; font-size: 1em; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4); transition: all 0.3s ease;' onmouseover='this.style.transform=\"translateY(-2px)\"; this.style.boxShadow=\"0 6px 20px rgba(245, 158, 11, 0.5)\";' onmouseout='this.style.transform=\"translateY(0)\"; this.style.boxShadow=\"0 4px 15px rgba(245, 158, 11, 0.4)\";'>\n"
            content += "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><path d='M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8'/><polyline points='16 6 12 2 8 6'/><line x1='12' y1='2' x2='12' y2='15'/></svg>\n"
            content += "Share Pick Card\n"
            content += "</a>\n"
            content += "<p style='margin-top: 10px; color: #9ca3af; font-size: 0.85em;'>Download the image to share on Facebook, Instagram, or X</p>\n"
            content += "</div>\n"
            content += "<script>\n"
            content += "(function(){\n"
            content += "  var img = new Image();\n"
            content += "  img.onload = function() { document.getElementById('pick-card-share').style.display = 'block'; };\n"
            content += "  img.src = 'picks/pick_card_latest.png?' + Date.now();\n"
            content += "  var btn = document.getElementById('pick-card-dl-btn');\n"
            content += "  if (btn && navigator.share) {\n"
            content += "    btn.addEventListener('click', function(e) {\n"
            content += "      e.preventDefault();\n"
            content += "      fetch('picks/pick_card_latest.png')\n"
            content += "        .then(r => r.blob())\n"
            content += "        .then(blob => {\n"
            content += "          var file = new File([blob], 'parieur-discipline-pick.png', {type: 'image/png'});\n"
            content += "          if (navigator.canShare && navigator.canShare({files: [file]})) {\n"
            content += "            navigator.share({files: [file], title: \"Today's Pick - Parieur Discipliné\", url: 'https://www.parieurdiscipline.com'});\n"
            content += "          } else {\n"
            content += "            window.open('picks/pick_card_latest.png', '_blank');\n"
            content += "          }\n"
            content += "        }).catch(function() { window.open('picks/pick_card_latest.png', '_blank'); });\n"
            content += "    });\n"
            content += "  }\n"
            content += "})();\n"
            content += "</script>\n"

        content += "</div>\n\n"

        content += "</div>\n"
        content += "</div>\n\n"


    # ── Yesterday's Results ──
    content += "<div id='yesterday-results'>\n"
    content += "<div class='section-header'>\n"
    content += "<div class='section-title'>📋 Yesterday's Results</div>\n"
    # Get yesterday's actual date from the results
    yesterday_date = None
    if nhl_yesterday and nhl_yesterday.get("date"):
        yesterday_date = nhl_yesterday["date"]
    elif nba_yesterday and nba_yesterday.get("date"):
        yesterday_date = nba_yesterday["date"]
    yesterday_date_nice = format_date_nice(yesterday_date) if yesterday_date else "Yesterday"
    content += f"<div class='section-subtitle'>Performance breakdown for {yesterday_date_nice}</div>\n"
    content += "</div>\n"
    stats_banner = format_compact_stats_banner(nhl_yesterday, nba_yesterday, nba_record, nhl_record)
    content += stats_banner
    content += "</div>\n\n"

    # ── Close content wrapper ──
    content += "</div>\n\n"

    # ── Close blog container ──
    content += "</div>\n\n"

    # ── Performance Calendar ──
    calendar_data = parse_calendar_data(summary_path)
    content += build_calendar_html(calendar_data)

    # ── What's New Section ──
    content += "<!-- What's New Section -->\n"
    content += "<div id='whats-new-section' style='max-width: 1600px; margin: 60px auto 40px; padding: 0 20px;'>\n"
    content += "  <div style='background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); border: 1px solid #e5e7eb;'>\n"
    content += "    <div style='text-align: center; margin-bottom: 30px;'>\n"
    content += "      <h2 style='font-size: 2em; font-weight: 800; color: #111827; margin-bottom: 8px;'>🎉 What's New</h2>\n"
    content += "      <p style='color: #6b7280; font-size: 1.05em;'>Latest updates and improvements to the platform</p>\n"
    content += "    </div>\n"
    content += "    <table id='changelog-table' style='width: 100%; border-collapse: collapse;'>\n"
    content += "      <thead>\n"
    content += "        <tr style='border-bottom: 2px solid #e5e7eb;'>\n"
    content += "          <th style='text-align: left; padding: 12px 15px; font-weight: 700; color: #374151; font-size: 0.95em;'>Date</th>\n"
    content += "          <th style='text-align: left; padding: 12px 15px; font-weight: 700; color: #374151; font-size: 0.95em;'>Changes</th>\n"
    content += "        </tr>\n"
    content += "      </thead>\n"
    content += "      <tbody id='changelog-body'>\n"
    content += "        <!-- Changelog entries will be dynamically loaded here -->\n"
    content += "      </tbody>\n"
    content += "    </table>\n"
    content += "  </div>\n"
    content += "</div>\n"
    content += "<style>\n"
    content += "@media (max-width: 768px) {\n"
    content += "  #whats-new-section {\n"
    content += "    margin: 40px auto 30px;\n"
    content += "    padding: 0 15px;\n"
    content += "  }\n"
    content += "  #whats-new-section > div {\n"
    content += "    padding: 25px 20px;\n"
    content += "    border-radius: 12px;\n"
    content += "  }\n"
    content += "  #whats-new-section h2 {\n"
    content += "    font-size: 1.5em !important;\n"
    content += "  }\n"
    content += "  #whats-new-section p {\n"
    content += "    font-size: 0.9em !important;\n"
    content += "  }\n"
    content += "  #changelog-table {\n"
    content += "    display: block;\n"
    content += "  }\n"
    content += "  #changelog-table thead {\n"
    content += "    display: none;\n"
    content += "  }\n"
    content += "  #changelog-table tbody {\n"
    content += "    display: block;\n"
    content += "  }\n"
    content += "  #changelog-table tr {\n"
    content += "    display: block;\n"
    content += "    margin-bottom: 20px;\n"
    content += "    padding: 15px;\n"
    content += "    background: #f9fafb;\n"
    content += "    border-radius: 8px;\n"
    content += "    border: 1px solid #e5e7eb;\n"
    content += "  }\n"
    content += "  #changelog-table td {\n"
    content += "    display: block;\n"
    content += "    padding: 0 !important;\n"
    content += "    text-align: left !important;\n"
    content += "  }\n"
    content += "  #changelog-table td:first-child {\n"
    content += "    font-size: 0.8em !important;\n"
    content += "    color: #4a90e2 !important;\n"
    content += "    font-weight: 700 !important;\n"
    content += "    margin-bottom: 8px;\n"
    content += "    padding-bottom: 8px !important;\n"
    content += "    border-bottom: 1px solid #e5e7eb;\n"
    content += "  }\n"
    content += "  #changelog-table td:last-child {\n"
    content += "    font-size: 0.9em !important;\n"
    content += "    line-height: 1.6 !important;\n"
    content += "    padding-top: 8px !important;\n"
    content += "  }\n"
    content += "}\n"
    content += "</style>\n\n"

    # ── Back to Top Button with JavaScript ──
    content += "<button id='back-to-top' onclick='window.scrollTo({top: 0, behavior: \"smooth\"})'>↑</button>\n\n"

    content += "<script>\n"
    # Back to top functionality
    content += "window.addEventListener('scroll', function() {\n"
    content += "  var btn = document.getElementById('back-to-top');\n"
    content += "  if (window.pageYOffset > 300) { btn.style.display = 'block'; }\n"
    content += "  else { btn.style.display = 'none'; }\n"
    content += "});\n"
    content += "</script>\n\n"

    # Add changelog loading script
    content += "<script>\n"
    content += "// Load changelog data\n"
    content += "fetch('data/changelog.json')\n"
    content += "  .then(response => response.json())\n"
    content += "  .then(data => {\n"
    content += "    const tbody = document.getElementById('changelog-body');\n"
    content += "    data.forEach((entry, index) => {\n"
    content += "      const row = document.createElement('tr');\n"
    content += "      row.style.borderBottom = '1px solid #f3f4f6';\n"
    content += "\n"
    content += "      // Format date\n"
    content += "      const dateObj = new Date(entry.date);\n"
    content += "      const formattedDate = dateObj.toLocaleDateString('en-US', {\n"
    content += "        year: 'numeric',\n"
    content += "        month: 'short',\n"
    content += "        day: 'numeric'\n"
    content += "      });\n"
    content += "\n"
    content += "      row.innerHTML = `\n"
    content += "        <td style='padding: 15px; color: #6b7280; font-weight: 600; font-size: 0.9em; white-space: nowrap;'>${formattedDate}</td>\n"
    content += "        <td style='padding: 15px; color: #374151; line-height: 1.6; font-size: 0.95em;'>${entry.notes}</td>\n"
    content += "      `;\n"
    content += "\n"
    content += "      tbody.appendChild(row);\n"
    content += "    });\n"
    content += "  })\n"
    content += "  .catch(error => {\n"
    content += "    console.error('Error loading changelog:', error);\n"
    content += "    const tbody = document.getElementById('changelog-body');\n"
    content += "    tbody.innerHTML = '<tr><td colspan=\"2\" style=\"padding: 15px; text-align: center; color: #6b7280;\">Unable to load changelog</td></tr>';\n"
    content += "  });\n"
    content += "</script>\n\n"

    # Add Vercel Analytics and Speed Insights
    content += "<script defer src='/_vercel/insights/script.js'></script>\n"
    content += "<script defer src='/_vercel/speed-insights/script.js'></script>\n\n"

    # Add feature request CTA block before closing body
    content += "<div style='max-width: 1600px; margin: 60px auto 40px; padding: 0 20px;'>\n"
    content += "  <div style='background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%); border-radius: 16px; padding: 50px 40px; text-align: center; box-shadow: 0 4px 15px rgba(74, 144, 226, 0.3);'>\n"
    content += "    <h2 style='color: white; font-size: 2em; font-weight: 800; margin-bottom: 15px;'>💡 Have a Feature Request?</h2>\n"
    content += "    <p style='color: rgba(255,255,255,0.95); font-size: 1.2em; margin-bottom: 30px;'>We'd love to hear your ideas to improve Parieur Discipliné!</p>\n"
    content += "    <a href='contact.html' style='display: inline-block; background: white; color: #4a90e2; padding: 15px 40px; border-radius: 30px; text-decoration: none; font-weight: 800; font-size: 1.1em; box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: all 0.3s; text-transform: uppercase; letter-spacing: 1px;' onmouseover='this.style.transform=\"scale(1.05)\"; this.style.boxShadow=\"0 6px 25px rgba(0,0,0,0.3)\";' onmouseout='this.style.transform=\"scale(1)\"; this.style.boxShadow=\"0 4px 15px rgba(0,0,0,0.2)\";'>Submit Feature Request</a>\n"
    content += "  </div>\n"
    content += "</div>\n\n"

    # Add html2canvas library and sharing JavaScript
    content += "<!-- html2canvas for screenshot sharing -->\n"
    content += "<script src='https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js'></script>\n\n"

    content += "<script>\n"
    content += "/**\n"
    content += " * Parse emoji bullet points into structured HTML\n"
    content += " */\n"
    content += "function formatReasoning(reasoning) {\n"
    content += "  var lines = reasoning.split('\\n');\n"
    content += "  var formatted = '';\n"
    content += "  var i = 0;\n"
    content += "  while (i < lines.length) {\n"
    content += "    var line = lines[i].trim();\n"
    content += "    var match = line.match(/^([^\\s*\\w]+)\\s*\\*{0,2}(.+?)\\*{0,2}$/);\n"
    content += "    if (match && match[1].length <= 2) {\n"
    content += "      var emoji = match[1];\n"
    content += "      var title = match[2];\n"
    content += "      var description = '';\n"
    content += "      i++;\n"
    content += "      while (i < lines.length) {\n"
    content += "        var nextLine = lines[i].trim();\n"
    content += "        if (!nextLine) { i++; break; }\n"
    content += "        if (nextLine.match(/^([^\\s*\\w]+)\\s*\\*{0,2}/)) break;\n"
    content += "        description += nextLine + ' ';\n"
    content += "        i++;\n"
    content += "      }\n"
    content += "      formatted += \"<div class='reasoning-point'>\";\n"
    content += "      formatted += \"<span class='reasoning-emoji'>\" + emoji + \"</span>\";\n"
    content += "      formatted += \"<div class='reasoning-content'>\";\n"
    content += "      formatted += \"<span class='reasoning-title'>\" + title + \"</span>\";\n"
    content += "      if (description.trim()) formatted += \"<span class='reasoning-text'>\" + description.trim() + \"</span>\";\n"
    content += "      formatted += \"</div></div>\";\n"
    content += "    } else { i++; }\n"
    content += "  }\n"
    content += "  return formatted || '<p>' + reasoning + '</p>';\n"
    content += "}\n\n"
    content += "document.addEventListener('DOMContentLoaded', function() {\n"
    content += "  document.querySelectorAll('.reasoning[data-raw]').forEach(function(el) {\n"
    content += "    el.innerHTML = formatReasoning(el.getAttribute('data-raw'));\n"
    content += "  });\n"
    content += "});\n\n"
    content += "/**\n"
    content += " * Handle share button click for featured picks\n"
    content += " */\n"
    content += "function loadImageAsDataURL(src, size) {\n"
    content += "  size = size || 88;\n"
    content += "  return new Promise(function(resolve) {\n"
    content += "    var img = new Image();\n"
    content += "    img.crossOrigin = 'anonymous';\n"
    content += "    img.onload = function() {\n"
    content += "      var c = document.createElement('canvas');\n"
    content += "      c.width = size; c.height = size;\n"
    content += "      c.getContext('2d').drawImage(img, 0, 0, size, size);\n"
    content += "      resolve(c.toDataURL('image/png'));\n"
    content += "    };\n"
    content += "    img.onerror = function() { resolve(null); };\n"
    content += "    img.src = src;\n"
    content += "  });\n"
    content += "}\n\n"
    content += "async function handleShare(pickId, sport) {\n"
    content += "  var button = document.getElementById('share-btn-' + pickId);\n"
    content += "  if (button.disabled) return;\n"
    content += "  button.disabled = true;\n"
    content += "  button.innerHTML = '⏳ Building...';\n"
    content += "  try {\n"
    content += "    var card = button.closest('.pick-card');\n"
    content += "    var titleEl = card.querySelector('.pick-title');\n"
    content += "    var metaEl = card.querySelector('.pick-meta');\n"
    content += "    var descEl = card.querySelector('.pick-description');\n"
    content += "    var titleText = titleEl ? titleEl.textContent.trim() : '';\n"
    content += "    var metaText = metaEl ? metaEl.textContent.trim() : '';\n"
    content += "    var sportIcon = sport === 'NHL' ? '🏒' : '🏀';\n"
    content += "    var sportColor = sport === 'NHL' ? '#3b82f6' : '#f59e0b';\n"
    content += "    var date = new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });\n"
    content += "    var oddsMatch = titleText.match(/@\\s*([\\d.]+)$/);\n"
    content += "    var odds = oddsMatch ? oddsMatch[1] : '';\n"
    content += "    var game = titleText.replace(/@\\s*[\\d.]+$/, '').trim();\n"
    content += "    var pickLine = game.split(' vs ')[0].trim();\n"
    content += "    var confMatch = metaText.match(/Confidence Level:\\s*(\\w+)/i);\n"
    content += "    var probMatch = metaText.match(/Win Probability:\\s*(\\d+)%/i);\n"
    content += "    var confidence = confMatch ? confMatch[1] : '';\n"
    content += "    var winProb = probMatch ? parseInt(probMatch[1]) : null;\n"
    content += "    var desc = descEl ? descEl.getAttribute('data-raw') || descEl.textContent.trim() : '';\n"
    content += "    // Parse bullet points from raw text\n"
    content += "    var bulletLines = desc.split('\\n').filter(function(l) { return l.trim(); });\n"
    content += "    var bulletPoints = [];\n"
    content += "    var i = 0;\n"
    content += "    while (i < bulletLines.length) {\n"
    content += "      var line = bulletLines[i].trim();\n"
    content += "      var m = line.match(/^([^\\s*\\w]+)\\s*\\*{0,2}(.+?)\\*{0,2}$/);\n"
    content += "      if (m && m[1].length <= 2) {\n"
    content += "        var bulletDesc = (i + 1 < bulletLines.length && !bulletLines[i+1].trim().match(/^[^\\s*\\w]+\\s/)) ? bulletLines[i+1].trim() : '';\n"
    content += "        bulletPoints.push({ emoji: m[1], title: m[2], desc: bulletDesc });\n"
    content += "        i += bulletDesc ? 2 : 1;\n"
    content += "      } else { i++; }\n"
    content += "    }\n"
    content += "    var logoDataURL = await loadImageAsDataURL('/parieur_discipline_icon_1024.png', 88);\n"
    content += "    var logoSrc = logoDataURL || '/parieur_discipline_icon_1024.png';\n"
    content += "    var cardEl = document.createElement('div');\n"
    content += "    cardEl.style.cssText = 'position:absolute;left:-9999px;top:0;width:540px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;background:#0f172a;border-radius:20px;overflow:hidden;';\n"
    content += "    cardEl.innerHTML = `\n"
    content += "      <div style=\"background:linear-gradient(135deg,#1e3a8a 0%,#2c5aa0 50%,#1e40af 100%);padding:22px 28px 18px;position:relative;overflow:hidden;\">\n"
    content += "        <div style=\"position:absolute;top:0;left:0;right:0;bottom:0;opacity:0.07;background:repeating-linear-gradient(45deg,transparent,transparent 20px,rgba(255,255,255,0.3) 20px,rgba(255,255,255,0.3) 21px);\"></div>\n"
    content += "        <div style=\"display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;position:relative;\">\n"
    content += "          <div style=\"display:flex;align-items:center;gap:10px;\">\n"
    content += "            <img src=\"${logoSrc}\" style=\"width:44px;height:44px;border-radius:50%;border:2px solid rgba(255,255,255,0.3);\" />\n"
    content += "            <div>\n"
    content += "              <div style=\"color:white;font-weight:800;font-size:1em;\">Le Parieur Discipliné</div>\n"
    content += "              <div style=\"color:rgba(255,255,255,0.65);font-size:0.72em;font-weight:500;\">AI Betting Predictions</div>\n"
    content += "            </div>\n"
    content += "          </div>\n"
    content += "          <div style=\"background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:5px 12px;text-align:right;\">\n"
    content += "            <div style=\"color:rgba(255,255,255,0.7);font-size:0.65em;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;\">Date</div>\n"
    content += "            <div style=\"color:white;font-size:0.78em;font-weight:700;\">${date}</div>\n"
    content += "          </div>\n"
    content += "        </div>\n"
    content += "        <div style=\"margin-bottom:6px;\"><span style=\"background:${sportColor};color:white;font-size:0.7em;font-weight:800;text-transform:uppercase;letter-spacing:0.8px;padding:4px 10px;border-radius:6px;\">${sportIcon} ${sport}</span></div>\n"
    content += "        <div style=\"color:white;font-size:1.15em;font-weight:800;line-height:1.3;position:relative;\">${game}</div>\n"
    content += "      </div>\n"
    content += "      <div style=\"padding:16px 24px;background:#0f172a;\">\n"
    content += "        <div style=\"background:linear-gradient(135deg,#064e3b 0%,#065f46 100%);border:1px solid #10b981;border-radius:12px;padding:12px 16px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;\">\n"
    content += "          <div style=\"flex:1;min-width:0;\">\n"
    content += "            <div style=\"color:#6ee7b7;font-size:0.62em;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:3px;\">AI Pick</div>\n"
    content += "            <div style=\"color:white;font-size:1em;font-weight:800;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;\">${pickLine}</div>\n"
    content += "          </div>\n"
    content += "          <div style=\"display:flex;gap:10px;margin-left:12px;flex-shrink:0;\">\n"
    content += "            ${odds ? `<div style=\"text-align:center;background:rgba(255,255,255,0.08);border-radius:8px;padding:8px 14px;\"><div style=\"color:#6ee7b7;font-size:0.6em;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;\">Odds</div><div style=\"color:white;font-size:1.3em;font-weight:900;\">${odds}</div></div>` : ''}\n"
    content += "            ${winProb ? `<div style=\"text-align:center;background:rgba(255,255,255,0.08);border-radius:8px;padding:8px 14px;\"><div style=\"color:#6ee7b7;font-size:0.6em;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;\">Win %</div><div style=\"color:#10b981;font-size:1.3em;font-weight:900;\">${winProb}%</div></div>` : ''}\n"
    content += "          </div>\n"
    content += "        </div>\n"
    content += "        ${bulletPoints.length > 0 ? `\n"
    content += "        <div style=\"background:#1e293b;border-radius:12px;padding:14px 16px;margin-bottom:14px;border:1px solid #334155;\">\n"
    content += "          <div style=\"color:#94a3b8;font-size:0.62em;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px;\">Analysis</div>\n"
    content += "          ${bulletPoints.map(function(p) { return `\n"
    content += "            <div style=\"display:flex;align-items:flex-start;gap:8px;margin-bottom:9px;\">\n"
    content += "              <span style=\"font-size:1em;flex-shrink:0;margin-top:1px;\">${p.emoji}</span>\n"
    content += "              <div>\n"
    content += "                <div style=\"color:#e2e8f0;font-size:0.78em;font-weight:700;line-height:1.3;\">${p.title}</div>\n"
    content += "                ${p.desc ? `<div style=\"color:#94a3b8;font-size:0.72em;line-height:1.4;margin-top:2px;\">${p.desc}</div>` : ''}\n"
    content += "              </div>\n"
    content += "            </div>`;}).join('')}\n"
    content += "        </div>` : ''}\n"
    content += "        <div style=\"display:flex;align-items:center;justify-content:space-between;padding-top:4px;\">\n"
    content += "          <div style=\"color:#475569;font-size:0.68em;\">AI-generated for entertainment only. Gamble responsibly.</div>\n"
    content += "          <div style=\"color:#64748b;font-size:0.72em;font-weight:700;\">parieurdiscipline.com</div>\n"
    content += "        </div>\n"
    content += "      </div>\n"
    content += "    `;\n"
    content += "    document.body.appendChild(cardEl);\n"
    content += "    await new Promise(function(r) { setTimeout(r, 200); });\n"
    content += "    var canvas = await html2canvas(cardEl, { backgroundColor: '#0f172a', scale: 2, logging: false });\n"
    content += "    document.body.removeChild(cardEl);\n"
    content += "    var blob = await new Promise(function(resolve) { canvas.toBlob(resolve, 'image/png'); });\n"
    content += "    var file = new File([blob], 'pick-' + pickId + '.png', { type: 'image/png' });\n"
    content += "    if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {\n"
    content += "      try {\n"
    content += "        await navigator.share({ files: [file] });\n"
    content += "        button.innerHTML = '✓ Shared!';\n"
    content += "        setTimeout(function() { button.innerHTML = '<span style=\"font-size:1.5em\">📤</span> <span>Share</span>'; button.disabled = false; }, 2000);\n"
    content += "        return;\n"
    content += "      } catch(err) {\n"
    content += "        if (err.name === 'AbortError') {\n"
    content += "          button.innerHTML = '<span style=\"font-size:1.5em\">📤</span> <span>Share</span>';\n"
    content += "          button.disabled = false; return;\n"
    content += "        }\n"
    content += "      }\n"
    content += "    }\n"
    content += "    if (navigator.clipboard && navigator.clipboard.write) {\n"
    content += "      try {\n"
    content += "        await navigator.clipboard.write([new ClipboardItem({ 'image/png': Promise.resolve(blob) })]);\n"
    content += "        button.innerHTML = '📋 Copied!';\n"
    content += "        setTimeout(function() { button.innerHTML = '<span style=\"font-size:1.5em\">📤</span> <span>Share</span>'; button.disabled = false; }, 2500);\n"
    content += "        return;\n"
    content += "      } catch(err) {}\n"
    content += "    }\n"
    content += "    var url = URL.createObjectURL(blob);\n"
    content += "    var a = document.createElement('a');\n"
    content += "    a.href = url; a.download = 'parieur-discipline-' + pickId + '.png';\n"
    content += "    document.body.appendChild(a); a.click();\n"
    content += "    document.body.removeChild(a); URL.revokeObjectURL(url);\n"
    content += "    button.innerHTML = '✓ Saved!';\n"
    content += "    setTimeout(function() { button.innerHTML = '<span style=\"font-size:1.5em\">📤</span> <span>Share</span>'; button.disabled = false; }, 2000);\n"
    content += "  } catch(error) {\n"
    content += "    console.error('Share error:', error);\n"
    content += "    alert('Failed to generate card. Please try again.');\n"
    content += "    button.innerHTML = '<span style=\"font-size:1.5em\">📤</span> <span>Share</span>';\n"
    content += "    button.disabled = false;\n"
    content += "  }\n"
    content += "}\n"
    content += "</script>\n\n"

    # Close HTML tags
    content += "</body>\n"
    content += "</html>\n\n"

    # Write HTML file
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Updated {output_html}")


def get_time_since_update(file_path):
    """Get the current time in Montreal/Eastern timezone when website is generated."""
    # Use current time instead of file modification time
    montreal_tz = ZoneInfo('America/Toronto')
    current_time = datetime.now(montreal_tz)
    # Format as "Last Updated at H:MM PM"
    time_str = current_time.strftime('%I:%M %p').lstrip('0')  # Remove leading zero from hour
    return f"Last Updated at {time_str}"


def build_chart_data_for_last_30_days():
    """Build chart data for win rate trends over last 30 days."""
    nhl_dir = "data/bot_results/nhl"
    nba_dir = "data/bot_results/nba"

    # Get all result files from both sports
    nhl_files = sorted(glob(os.path.join(nhl_dir, "nhl_daily_results_*.txt")))
    nba_files = sorted(glob(os.path.join(nba_dir, "nba_daily_results_*.txt")))

    # Build daily stats for last 30 days
    dates = []
    nhl_wr_data = []
    nba_wr_data = []
    combined_wr_data = []

    # Get date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=29)

    for i in range(30):
        date = start_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        dates.append(date.strftime("%b %d"))

        # Find files for this date
        nhl_file = os.path.join(nhl_dir, f"nhl_daily_results_{date_str}.txt")
        nba_file = os.path.join(nba_dir, f"nba_daily_results_{date_str}.txt")

        nhl_w = nhl_l = nba_w = nba_l = 0

        # Parse NHL results
        if os.path.exists(nhl_file):
            content = read_file(nhl_file)
            win_match = re.search(r'\*\*Total Wins:\s*(\d+)\*\*', content)
            loss_match = re.search(r'\*\*Total Losses:\s*(\d+)\*\*', content)
            if win_match:
                nhl_w = int(win_match.group(1))
            if loss_match:
                nhl_l = int(loss_match.group(1))

        # Parse NBA results
        if os.path.exists(nba_file):
            content = read_file(nba_file)
            win_match = re.search(r'\*\*Total Wins:\s*(\d+)\*\*', content)
            loss_match = re.search(r'\*\*Total Losses:\s*(\d+)\*\*', content)
            if win_match:
                nba_w = int(win_match.group(1))
            if loss_match:
                nba_l = int(loss_match.group(1))

        # Calculate win rates (use None for days with no games)
        nhl_total = nhl_w + nhl_l
        nba_total = nba_w + nba_l
        combined_total = nhl_total + nba_total

        nhl_wr = (nhl_w / nhl_total * 100) if nhl_total > 0 else None
        nba_wr = (nba_w / nba_total * 100) if nba_total > 0 else None
        combined_wr = ((nhl_w + nba_w) / combined_total * 100) if combined_total > 0 else None

        nhl_wr_data.append(nhl_wr)
        nba_wr_data.append(nba_wr)
        combined_wr_data.append(combined_wr)

    return {
        "labels": dates,
        "nhl_data": nhl_wr_data,
        "nba_data": nba_wr_data,
        "combined_data": combined_wr_data
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update latest predictions website')
    parser.add_argument('--preliminary', action='store_true',
                        help='Show preliminary 7am picks instead of final 3pm picks')
    args = parser.parse_args()

    update_latest_predictions(preliminary=args.preliminary)
