#!/usr/bin/env python3
"""Build docs/nfl/index.html from the latest NFL weekly predictions file."""
import os
import sys
import glob
import re
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

OUTPUT = "docs/nfl/index.html"
PREDICTIONS_DIR = os.path.join("data", "predictions", "nfl")
NAV_PATH = os.path.join("docs", "nav.html")


def get_nav_html():
    if os.path.exists(NAV_PATH):
        with open(NAV_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def get_latest_predictions():
    files = sorted(glob.glob(os.path.join(PREDICTIONS_DIR, "nfl_weekly_predictions_*.txt")))
    if not files:
        return None, None
    latest = files[-1]
    date_str = os.path.basename(latest).replace("nfl_weekly_predictions_", "").replace(".txt", "")
    with open(latest, "r", encoding="utf-8") as f:
        content = f.read()
    return date_str, content


def format_predictions_html(raw_text):
    """Convert raw prediction text to readable HTML."""
    if not raw_text:
        return "<p>No predictions available.</p>"

    # Split into matchup blocks and AI summary
    ai_marker = "AI Analysis Summary:"
    if ai_marker in raw_text:
        matchups_raw, ai_raw = raw_text.split(ai_marker, 1)
    else:
        matchups_raw, ai_raw = raw_text, ""

    html = ""

    # Matchups table
    matchup_lines = [l for l in matchups_raw.splitlines() if l.strip() and not l.startswith("Date:")]
    if matchup_lines:
        html += "<div style='margin-bottom:24px;'>\n"
        html += "<h3 style='font-size:1.1em;font-weight:700;color:#374151;margin-bottom:12px;'>📋 This Week's Games & Odds</h3>\n"
        html += "<div style='display:grid;gap:10px;'>\n"
        current_game = []
        for line in matchup_lines:
            if line.startswith("------"):
                if current_game:
                    html += _render_game_card(current_game)
                    current_game = []
            else:
                current_game.append(line)
        if current_game:
            html += _render_game_card(current_game)
        html += "</div></div>\n"

    # AI Analysis
    if ai_raw.strip():
        html += "<div style='margin-top:30px;'>\n"
        html += "<h3 style='font-size:1.2em;font-weight:700;color:#2563eb;margin-bottom:16px;border-bottom:2px solid #dbeafe;padding-bottom:8px;'>🤖 AI Analysis</h3>\n"
        ai_html = _format_ai_text(ai_raw.strip())
        html += f"<div style='line-height:1.75;color:#374151;'>{ai_html}</div>\n"
        html += "</div>\n"

    return html or "<p>No data available.</p>"


def _render_game_card(lines):
    if not lines:
        return ""
    title = lines[0] if lines else ""
    details = " &nbsp;·&nbsp; ".join(l for l in lines[1:] if l.strip() and not l.startswith("Bookmakers"))
    return (
        f"<div style='background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:12px 16px;'>"
        f"<div style='font-weight:700;color:#1a1a1a;margin-bottom:4px;'>{title}</div>"
        f"<div style='font-size:0.85em;color:#6b7280;'>{details}</div>"
        f"</div>\n"
    )


def _format_ai_text(text):
    """Convert AI text output to readable HTML preserving structure."""
    # Escape HTML entities
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold headers: **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # BET OF THE WEEK block
    text = re.sub(
        r'(BET OF THE WEEK)',
        r'<div style="background:linear-gradient(135deg,#1e3a8a,#2563eb);color:white;padding:6px 14px;border-radius:8px;display:inline-block;font-weight:700;letter-spacing:1px;font-size:0.9em;margin-bottom:8px;">\1</div>',
        text
    )
    # Line breaks
    text = text.replace("\n", "<br>")
    return text


def build_page(date_str, predictions_html, last_updated_label, nav_html=""):
    return f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>NFL Weekly Picks - AI Predictions & Betting Odds | Parieur Discipliné</title>
<meta name='description' content='Weekly NFL predictions with AI-powered betting analysis. Spread, moneyline and over/under picks with team stats, home/away splits and historical context.'>
<link rel='canonical' href='https://parieurdiscipline.com/nfl/'>
<link rel='icon' type='image/png' href='../parieur_discipline_icon_1024.png'>
<meta name='theme-color' content='#1e3a8a'>
<meta property='og:type' content='website'>
<meta property='og:url' content='https://parieurdiscipline.com/nfl/'>
<meta property='og:title' content='NFL Weekly Picks - AI Predictions | Parieur Discipliné'>
<meta property='og:description' content='Weekly NFL predictions with AI-powered betting analysis.'>
<meta property='og:image' content='https://parieurdiscipline.com/parieur_discipline_icon_1024.png'>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #1a1a1a; min-height: 100vh; }}
.container {{ max-width: 1100px; margin: 0 auto; padding: 40px 20px; }}
.header {{ text-align: center; background: linear-gradient(135deg, #1e3a8a 0%, #2c5aa0 100%); padding: 60px 40px 40px; box-shadow: 0 4px 20px rgba(30,58,138,0.25); }}
.header h1 {{ font-size: 2.8em; color: white; margin-bottom: 12px; font-weight: 800; }}
.header p {{ color: rgba(255,255,255,0.9); font-size: 1.1em; font-weight: 500; }}
.header .badge {{ display: inline-block; background: rgba(255,255,255,0.15); color: white; padding: 4px 14px; border-radius: 20px; font-size: 0.85em; font-weight: 700; margin-top: 12px; letter-spacing: 1px; }}
.predictions-section {{ background: white; border-radius: 16px; padding: 30px; margin-top: 30px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
.meta-bar {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #dbeafe; }}
.meta-bar .title {{ font-size: 1.3em; font-weight: 700; color: #2563eb; }}
.meta-bar .date {{ background: #eff6ff; color: #2563eb; padding: 4px 12px; border-radius: 20px; border: 1px solid #bfdbfe; font-size: 0.85em; font-weight: 600; }}
</style>
</head>
<body>

{nav_html}

<div style='padding-top: 95px;'>
<div class='header'>
  <h1>🏈 NFL Weekly Picks</h1>
  <p>AI-powered spread, moneyline &amp; over/under analysis for every game</p>
  <div class='badge'>Updated every Sunday morning</div>
</div>

<div class='container'>
  <div class='predictions-section'>
    <div class='meta-bar'>
      <span class='title'>Week of {date_str}</span>
      <span class='date'>Updated {last_updated_label}</span>
    </div>
    {predictions_html}
  </div>
</div>
</div>

</body>
</html>"""


def main():
    os.makedirs("docs/nfl", exist_ok=True)
    date_str, raw_text = get_latest_predictions()

    if not date_str:
        print("No NFL predictions found — writing placeholder page.")
        # Keep the existing placeholder
        return

    predictions_html = format_predictions_html(raw_text)
    last_updated = datetime.now().strftime("%B %d, %Y at %H:%M")
    nav_html = get_nav_html()
    page = build_page(date_str, predictions_html, last_updated, nav_html)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"✅ NFL page written to {OUTPUT}")


if __name__ == "__main__":
    main()
