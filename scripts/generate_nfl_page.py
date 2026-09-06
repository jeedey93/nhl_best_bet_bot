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


def parse_game_line(line):
    """Parse a game line into structured data."""
    game = {"title": "", "home": "", "away": "", "home_odds": None, "away_odds": None,
            "ou": None, "over_price": None, "under_price": None,
            "spread_home": None, "spread_away": None}

    # Title line: "Team A vs Team B"
    if " vs " in line and "ML" not in line and "Spread" not in line:
        game["title"] = line.strip()
        parts = line.strip().split(" vs ")
        if len(parts) == 2:
            game["home"] = parts[0].strip()
            game["away"] = parts[1].strip()

    # Moneyline + O/U line
    ml_match = re.search(r'(.+?) ML \(Home\): ([\d.]+),.+?ML \(Away\): ([\d.]+).*?O/U: ([\d.]+).*?Over: ([\d.]+).*?Under: ([\d.]+)', line)
    if ml_match:
        game["home_odds"] = float(ml_match.group(2))
        game["away_odds"] = float(ml_match.group(3))
        game["ou"] = float(ml_match.group(4))
        game["over_price"] = float(ml_match.group(5))
        game["under_price"] = float(ml_match.group(6))

    # Spreads line
    spread_match = re.search(r'Spreads?: Home ([+-]?[\d.]+) \(([\d.]+)\), Away ([+-]?[\d.]+) \(([\d.]+)\)', line)
    if spread_match:
        game["spread_home"] = {"points": spread_match.group(1), "price": spread_match.group(2)}
        game["spread_away"] = {"points": spread_match.group(3), "price": spread_match.group(4)}

    return game


def parse_matchups(raw):
    """Parse matchup blocks into list of game dicts."""
    games = []
    current = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("Date:"):
            continue
        if line.startswith("------"):
            if current.get("title"):
                games.append(current)
            current = {}
            continue
        if " vs " in line and "ML" not in line and "Spread" not in line and "@" not in line:
            current["title"] = line
            parts = line.split(" vs ", 1)
            current["home"] = parts[0].strip()
            current["away"] = parts[1].strip() if len(parts) > 1 else ""
        ml = re.search(r'ML \(Home\): ([\d.]+).*?ML \(Away\): ([\d.]+).*?O/U: ([\d.]+).*?Over: ([\d.]+).*?Under: ([\d.]+)', line)
        if ml:
            current["home_odds"] = float(ml.group(1))
            current["away_odds"] = float(ml.group(2))
            current["ou"] = float(ml.group(3))
            current["over_price"] = float(ml.group(4))
            current["under_price"] = float(ml.group(5))
        sp = re.search(r'Spreads?: Home ([+-]?[\d.]+) \(([\d.]+)\), Away ([+-]?[\d.]+) \(([\d.]+)\)', line)
        if sp:
            current["spread_home"] = {"points": sp.group(1), "price": sp.group(2)}
            current["spread_away"] = {"points": sp.group(3), "price": sp.group(4)}
    if current.get("title"):
        games.append(current)
    return games


def render_game_card(g):
    home = g.get("home", "")
    away = g.get("away", "")
    home_odds = g.get("home_odds")
    away_odds = g.get("away_odds")
    ou = g.get("ou")
    over_price = g.get("over_price")
    under_price = g.get("under_price")
    sh = g.get("spread_home", {})
    sa = g.get("spread_away", {})

    def chip(label, val, highlight=False):
        bg = "#1e3a8a" if highlight else "#f1f5f9"
        color = "white" if highlight else "#374151"
        return f"<span style='background:{bg};color:{color};padding:3px 10px;border-radius:20px;font-size:0.78em;font-weight:700;white-space:nowrap;'>{label}: {val}</span>"

    odds_chips = ""
    if home_odds:
        fav = home_odds < away_odds if away_odds else True
        odds_chips += chip(f"🏠 {home.split()[-1]}", home_odds, highlight=fav)
        odds_chips += " "
    if away_odds:
        fav = away_odds < home_odds if home_odds else True
        odds_chips += chip(f"✈ {away.split()[-1]}", away_odds, highlight=fav)
        odds_chips += " "
    if ou:
        odds_chips += chip(f"O/U", f"{ou}", highlight=False)

    spread_chips = ""
    if sh:
        spread_chips += chip(f"Home {sh['points']}", sh['price'])
        spread_chips += " "
    if sa:
        spread_chips += chip(f"Away {sa['points']}", sa['price'])

    return f"""<div style='background:white;border:1px solid #e5e7eb;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);transition:box-shadow 0.2s;' onmouseover='this.style.boxShadow="0 4px 16px rgba(37,99,235,0.12)"' onmouseout='this.style.boxShadow="0 2px 8px rgba(0,0,0,0.06)"'>
  <div style='font-size:1.05em;font-weight:700;color:#1e293b;margin-bottom:10px;'>🏈 {home} <span style='color:#94a3b8;font-weight:500;font-size:0.9em;'>vs</span> {away}</div>
  <div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;'>{odds_chips}</div>
  {"<div style='display:flex;flex-wrap:wrap;gap:6px;'>" + spread_chips + "</div>" if spread_chips else ""}
</div>"""


def parse_picks(ai_text):
    """Extract BET OF THE WEEK and other recommended plays from AI text."""
    picks = []

    # BET OF THE WEEK block
    botw_match = re.search(r'BET OF THE WEEK\s*\n+(.*?)(?=\*\*Other|Confidence Level.*?\n\n|\Z)', ai_text, re.DOTALL | re.IGNORECASE)
    if botw_match:
        block = botw_match.group(1).strip()
        conf_match = re.search(r'Confidence Level: (\w+).*?Units: ([\d.]+u).*?Win Probability: (\d+%)', block)
        conf = conf_match.group(1) if conf_match else None
        units = conf_match.group(2) if conf_match else None
        prob = conf_match.group(3) if conf_match else None
        # Remove confidence line from body
        body = re.sub(r'Confidence Level:.*', '', block).strip()
        first_line = body.split('\n')[0].strip()
        rest = '\n'.join(body.split('\n')[1:]).strip()
        picks.append({"type": "best", "pick": first_line, "detail": rest, "conf": conf, "units": units, "prob": prob})

    # Other recommended plays
    other_match = re.search(r'\*\*Other Recommended Plays\*\*\s*\n+(.*?)$', ai_text, re.DOTALL | re.IGNORECASE)
    if other_match:
        block = other_match.group(1).strip()
        # Split by blank lines — each play is a paragraph
        paragraphs = re.split(r'\n\n+', block)
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            conf_match = re.search(r'Confidence Level: (\w+).*?Units: ([\d.]+u).*?Win Probability: (\d+%)', para)
            conf = conf_match.group(1) if conf_match else None
            units = conf_match.group(2) if conf_match else None
            prob = conf_match.group(3) if conf_match else None
            body = re.sub(r'Confidence Level:.*', '', para).strip()
            first_line = body.split('\n')[0].strip()
            rest = '\n'.join(body.split('\n')[1:]).strip()
            if first_line:
                picks.append({"type": "other", "pick": first_line, "detail": rest, "conf": conf, "units": units, "prob": prob})

    return picks


def render_pick_card(pick):
    is_best = pick["type"] == "best"
    conf = pick.get("conf", "")
    units = pick.get("units", "")
    prob = pick.get("prob", "")
    detail = pick.get("detail", "").replace("\n", "<br>")

    conf_color = {"High": "#16a34a", "Medium": "#d97706", "Low": "#dc2626"}.get(conf, "#6b7280")

    if is_best:
        return f"""<div style='background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);border-radius:16px;padding:24px;margin-bottom:20px;color:white;box-shadow:0 6px 24px rgba(37,99,235,0.3);'>
  <div style='display:flex;align-items:center;gap:10px;margin-bottom:14px;'>
    <span style='background:rgba(255,255,255,0.2);padding:4px 14px;border-radius:20px;font-size:0.75em;font-weight:800;letter-spacing:2px;text-transform:uppercase;'>⭐ BET OF THE WEEK</span>
    {"<span style='background:rgba(255,255,255,0.15);padding:3px 10px;border-radius:20px;font-size:0.8em;font-weight:700;'>" + conf + " Confidence</span>" if conf else ""}
  </div>
  <div style='font-size:1.2em;font-weight:800;margin-bottom:12px;line-height:1.3;'>{pick["pick"]}</div>
  <div style='display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;'>
    {"<span style='background:rgba(255,255,255,0.15);padding:4px 12px;border-radius:20px;font-size:0.82em;font-weight:700;'>📊 " + units + "</span>" if units else ""}
    {"<span style='background:rgba(255,255,255,0.15);padding:4px 12px;border-radius:20px;font-size:0.82em;font-weight:700;'>🎯 " + prob + " win prob</span>" if prob else ""}
  </div>
  {"<div style='font-size:0.88em;opacity:0.9;line-height:1.7;'>" + detail + "</div>" if detail else ""}
</div>"""
    else:
        return f"""<div style='background:white;border:1px solid #e5e7eb;border-left:4px solid #2563eb;border-radius:12px;padding:20px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,0.05);'>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;'>
    {"<span style='background:" + conf_color + ";color:white;padding:3px 10px;border-radius:20px;font-size:0.75em;font-weight:700;'>" + conf + "</span>" if conf else ""}
    {"<span style='background:#eff6ff;color:#2563eb;padding:3px 10px;border-radius:20px;font-size:0.78em;font-weight:700;'>" + units + "</span>" if units else ""}
    {"<span style='background:#f0fdf4;color:#16a34a;padding:3px 10px;border-radius:20px;font-size:0.78em;font-weight:700;'>🎯 " + prob + "</span>" if prob else ""}
  </div>
  <div style='font-size:1em;font-weight:700;color:#1e293b;margin-bottom:8px;'>{pick["pick"]}</div>
  {"<div style='font-size:0.88em;color:#6b7280;line-height:1.7;'>" + detail + "</div>" if detail else ""}
</div>"""


def parse_intro(ai_text):
    """Get the intro/context paragraph before the picks."""
    # Everything before BET OF THE WEEK
    before_botw = re.split(r'BET OF THE WEEK', ai_text, flags=re.IGNORECASE)[0]
    # Remove the header line if present
    lines = [l for l in before_botw.strip().splitlines() if l.strip()]
    # Skip first line if it's a short header
    if lines and len(lines[0]) < 60:
        lines = lines[1:]
    return " ".join(lines).strip()


def format_predictions_html(raw_text):
    if not raw_text:
        return "<p>No predictions available.</p>"

    ai_marker = "AI Analysis Summary:"
    if ai_marker in raw_text:
        matchups_raw, ai_raw = raw_text.split(ai_marker, 1)
    else:
        matchups_raw, ai_raw = raw_text, ""

    html = ""

    # Game matchup cards
    games = parse_matchups(matchups_raw)
    if games:
        html += "<div style='margin-bottom:28px;'>\n"
        html += "<h3 style='font-size:1em;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:14px;'>📋 This Week's Matchups</h3>\n"
        html += "<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px;'>\n"
        for g in games:
            html += render_game_card(g) + "\n"
        html += "</div></div>\n"

    # AI section
    if ai_raw.strip():
        picks = parse_picks(ai_raw)
        intro = parse_intro(ai_raw)

        html += "<div style='margin-top:8px;'>\n"
        html += "<h3 style='font-size:1em;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:20px;'>🤖 AI Analysis & Picks</h3>\n"

        # BET OF THE WEEK first
        for p in picks:
            if p["type"] == "best":
                html += render_pick_card(p)
                break

        # Other picks
        others = [p for p in picks if p["type"] == "other"]
        if others:
            html += "<h4 style='font-size:0.9em;font-weight:700;color:#374151;margin:20px 0 12px;'>Other Recommended Plays</h4>\n"
            for p in others:
                html += render_pick_card(p)

        # Context/analysis text
        if intro:
            html += f"<div style='margin-top:20px;background:#f8fafc;border-radius:12px;padding:20px;border:1px solid #e2e8f0;'>\n"
            html += f"<div style='font-size:0.9em;font-weight:700;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;'>📝 Analysis Notes</div>\n"
            html += f"<div style='font-size:0.88em;color:#475569;line-height:1.75;'>{intro}</div>\n"
            html += "</div>\n"

        html += "</div>\n"

    return html or "<p>No data available.</p>"


def build_page(date_str, predictions_html, last_updated_label, nav_html=""):
    # Format date nicely
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        nice_date = dt.strftime("%B %d, %Y")
    except Exception:
        nice_date = date_str

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
<meta property='og:image' content='https://parieurdiscipline.com/nfl/og-nfl.png'>
<meta property='og:image:width' content='1200'>
<meta property='og:image:height' content='630'>
<meta property='og:image:alt' content='NFL Weekly Picks - AI-powered betting analysis'>
<meta name='twitter:card' content='summary_large_image'>
<meta name='twitter:site' content='@parieurdiscipl'>
<meta name='twitter:title' content='NFL Weekly Picks - AI Predictions | Parieur Discipliné'>
<meta name='twitter:description' content='Weekly NFL predictions with AI-powered betting analysis. Spread, moneyline and over/under picks.'>
<meta name='twitter:image' content='https://parieurdiscipline.com/nfl/og-nfl.png'>
<link rel='preconnect' href='https://fonts.googleapis.com'>
<link href='https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&display=swap' rel='stylesheet'>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f1f5f9; color: #1a1a1a; min-height: 100vh; }}
.page-wrap {{ padding-top: 95px; }}
.hero {{ background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 60%, #3b82f6 100%); padding: 52px 24px 44px; text-align: center; position: relative; overflow: hidden; }}
.hero::before {{ content: ''; position: absolute; inset: 0; background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E"); }}
.hero-emoji {{ font-size: 3.5em; margin-bottom: 12px; display: block; }}
.hero h1 {{ font-family: 'Barlow Condensed', sans-serif; font-size: 3em; font-weight: 800; color: white; margin-bottom: 10px; letter-spacing: 1px; text-transform: uppercase; }}
.hero p {{ color: rgba(255,255,255,0.85); font-size: 1.05em; font-weight: 500; max-width: 500px; margin: 0 auto 16px; }}
.hero-badges {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }}
.hero-badge {{ background: rgba(255,255,255,0.15); color: white; padding: 5px 16px; border-radius: 20px; font-size: 0.8em; font-weight: 700; letter-spacing: 0.5px; backdrop-filter: blur(4px); }}
.container {{ max-width: 900px; margin: 0 auto; padding: 32px 20px 60px; }}
.section-card {{ background: white; border-radius: 20px; padding: 28px; margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.07); }}
.week-bar {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 24px; padding-bottom: 18px; border-bottom: 2px solid #e2e8f0; }}
.week-label {{ font-family: 'Barlow Condensed', sans-serif; font-size: 1.5em; font-weight: 700; color: #1e3a8a; letter-spacing: 0.5px; }}
.updated-badge {{ background: #eff6ff; color: #2563eb; padding: 5px 14px; border-radius: 20px; border: 1px solid #bfdbfe; font-size: 0.8em; font-weight: 600; }}
.share-btn {{ display: inline-flex; align-items: center; gap: 6px; background: #1e3a8a; color: white; border: none; padding: 7px 16px; border-radius: 20px; font-size: 0.82em; font-weight: 700; cursor: pointer; transition: background 0.2s; }}
.share-btn:hover {{ background: #2563eb; }}
.share-toast {{ display: none; position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: #1e293b; color: white; padding: 10px 20px; border-radius: 30px; font-size: 0.88em; font-weight: 600; z-index: 9999; box-shadow: 0 4px 16px rgba(0,0,0,0.2); }}
</style>
<script>
function shareNFL() {{
  const url = 'https://parieurdiscipline.com/nfl/';
  const text = '🏈 Check out this week\\'s NFL AI picks on Parieur Discipliné!';
  if (navigator.share) {{
    navigator.share({{ title: 'NFL Weekly Picks', text: text, url: url }});
  }} else {{
    navigator.clipboard.writeText(url).then(function() {{
      const toast = document.getElementById('share-toast');
      toast.style.display = 'block';
      setTimeout(function() {{ toast.style.display = 'none'; }}, 2500);
    }});
  }}
}}
</script>
</head>
<body>

{nav_html}

<div class='page-wrap'>
  <div class='hero'>
    <span class='hero-emoji'>🏈</span>
    <h1>NFL Weekly Picks</h1>
    <p>AI-powered spread, moneyline &amp; over/under analysis for every game</p>
    <div class='hero-badges'>
      <span class='hero-badge'>📅 Updated Every Sunday</span>
      <span class='hero-badge'>🤖 Gemini AI Analysis</span>
      <span class='hero-badge'>📊 Spread + Moneyline + O/U</span>
    </div>
  </div>

  <div class='container'>
    <div class='section-card'>
      <div class='week-bar'>
        <span class='week-label'>Week of {nice_date}</span>
        <div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>
          <span class='updated-badge'>🕐 {last_updated_label}</span>
          <button class='share-btn' onclick='shareNFL()'>🔗 Share</button>
        </div>
      </div>
      {predictions_html}
    </div>
  </div>
</div>

<div id='share-toast' class='share-toast'>✅ Link copied to clipboard!</div>

</body>
</html>"""


def main():
    os.makedirs("docs/nfl", exist_ok=True)
    date_str, raw_text = get_latest_predictions()

    if not date_str:
        print("No NFL predictions found — writing placeholder page.")
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
