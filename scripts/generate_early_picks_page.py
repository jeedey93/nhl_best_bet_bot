#!/usr/bin/env python3
"""
Generate the early picks page (docs/early-picks.html) from today's 7am prediction files.
This is a hidden page — not linked in the nav — accessible only via direct URL.
"""

import os
import re
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDICTIONS_DIR = os.path.join(BASE_DIR, "data", "predictions")
OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "early-picks.html")


def read_prediction_file(sport: str, today: str) -> str:
    path = os.path.join(PREDICTIONS_DIR, sport, "daily_runs",
                        f"{sport}_daily_predictions_{today}_7am.txt")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def parse_picks(raw: str) -> list[dict]:
    """
    Parse all picks from a 7am prediction file.
    Returns a list of dicts with keys: bet, description, confidence, units, win_prob, is_featured.
    """
    if not raw:
        return []

    # Split at the AI Analysis line to get just the recommendations section
    marker_patterns = ["AI Analysis Summary:", "BET OF THE DAY"]
    recs_start = 0
    for marker in marker_patterns:
        idx = raw.find(marker)
        if idx != -1:
            # Prefer BET OF THE DAY as the actual start of picks
            botd_idx = raw.find("BET OF THE DAY")
            if botd_idx != -1:
                recs_start = botd_idx
            break

    recs_text = raw[recs_start:] if recs_start else raw

    picks = []
    current = None
    is_featured = False

    for line in recs_text.splitlines():
        stripped = line.strip()

        # BET OF THE DAY header
        if "BET OF THE DAY" in stripped.upper() and not re.search(r'@\s*[\d.]+', stripped):
            is_featured = True
            current = None
            continue

        # Other Recommended Plays header
        if re.search(r'Other Recommended', stripped, re.IGNORECASE):
            if current:
                picks.append(current)
                current = None
            is_featured = False
            continue

        # New pick line: contains @ with decimal odds, not a header
        clean_stripped = stripped.strip("*").strip()
        odds_match = re.search(r'@\s*([\d.]+)\s*$', clean_stripped)
        if odds_match and clean_stripped and not clean_stripped.startswith("#"):
            if current:
                picks.append(current)
            # Clean up bold markers
            bet_line = clean_stripped
            current = {
                "bet": bet_line,
                "description": "",
                "confidence": "Medium",
                "units": "1u",
                "win_prob": "",
                "is_featured": is_featured,
            }
            continue

        # Confidence / Units / Win Probability line
        if current and re.match(r'Confidence Level:', stripped, re.IGNORECASE):
            conf_m = re.search(r'Confidence Level:\s*(\w+)', stripped, re.IGNORECASE)
            units_m = re.search(r'Units:\s*([\d.]+u)', stripped, re.IGNORECASE)
            prob_m = re.search(r'Win Probability:\s*(\d+%)', stripped, re.IGNORECASE)
            if conf_m:
                current["confidence"] = conf_m.group(1)
            if units_m:
                current["units"] = units_m.group(1)
            if prob_m:
                current["win_prob"] = prob_m.group(1)
            continue

        # Description / reasoning text
        if current and stripped and not stripped.startswith("---") and not stripped.startswith("Date:"):
            current["description"] += (" " if current["description"] else "") + stripped.strip("*")

    if current:
        picks.append(current)

    return picks


def confidence_stars(level: str) -> str:
    return {"high": "⭐⭐⭐⭐", "medium": "⭐⭐⭐", "low": "⭐⭐"}.get(level.lower(), "⭐⭐⭐")


def confidence_color(level: str) -> str:
    return {"high": "#15803d", "medium": "#b45309", "low": "#dc2626"}.get(level.lower(), "#4a90e2")


def render_pick_card(pick: dict) -> str:
    stars = confidence_stars(pick["confidence"])
    color = confidence_color(pick["confidence"])

    if pick["is_featured"]:
        border = "#f59e0b"
        bg = "linear-gradient(135deg, #fffbeb 0%, #ffffff 100%)"
        badge = "<span style='background:#f59e0b;color:#78350f;padding:3px 10px;border-radius:12px;font-size:0.75em;font-weight:700;letter-spacing:1px;text-transform:uppercase;'>🏆 BET OF THE DAY</span>"
    else:
        border = "#4a90e2"
        bg = "#ffffff"
        badge = ""

    win_prob_html = ""
    if pick["win_prob"]:
        win_prob_html = f"<span style='background:#e0f2fe;color:#0369a1;padding:2px 8px;border-radius:10px;font-size:0.8em;font-weight:600;'>Win Prob: {pick['win_prob']}</span> "

    return f"""<div style='background:{bg};border:2px solid {border};border-radius:12px;padding:20px 24px;margin:16px 0;box-shadow:0 2px 8px rgba(0,0,0,0.07);'>
  {f"<div style='margin-bottom:10px;'>{badge}</div>" if badge else ""}
  <div style='font-size:1.05em;font-weight:700;color:#1a1a1a;margin-bottom:10px;line-height:1.4;'>{pick['bet']}</div>
  <div style='margin-bottom:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;'>
    <span style='color:{color};font-weight:600;font-size:0.9em;'>{stars} {pick['confidence']}</span>
    {win_prob_html}<span style='background:#f3f4f6;color:#374151;padding:2px 8px;border-radius:10px;font-size:0.8em;font-weight:600;'>Units: {pick['units']}</span>
  </div>
  <div style='color:#4b5563;font-size:0.88em;line-height:1.6;'>{pick['description']}</div>
</div>"""


def render_sport_section(sport_name: str, emoji: str, picks: list[dict]) -> str:
    if not picks:
        return f"""<div style='background:#f9fafb;border:1px dashed #d1d5db;border-radius:12px;padding:30px;text-align:center;color:#9ca3af;margin:16px 0;'>
  No {sport_name} games today or predictions not yet available.
</div>"""

    cards = "\n".join(render_pick_card(p) for p in picks)
    return f"""<div style='margin-bottom:40px;'>
  <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px;'>
    <span style='font-size:1.8em;'>{emoji}</span>
    <h2 style='font-size:1.5em;color:#1e3a8a;margin:0;'>{sport_name} Picks</h2>
    <span style='background:#e0f2fe;color:#0369a1;padding:2px 10px;border-radius:12px;font-size:0.8em;font-weight:600;'>{len(picks)} plays</span>
  </div>
  <div style='height:3px;background:linear-gradient(90deg,#1e3a8a,#60a5fa);border-radius:2px;margin-bottom:20px;'></div>
  {cards}
</div>"""


def build_page(today: str, nhl_picks: list[dict], nba_picks: list[dict]) -> str:
    total = len(nhl_picks) + len(nba_picks)
    nhl_section = render_sport_section("NHL", "🏒", nhl_picks)
    nba_section = render_sport_section("NBA", "🏀", nba_picks)

    formatted_date = date.fromisoformat(today).strftime("%A, %B %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Early Picks ({today}) - Parieur Discipliné</title>
<meta name="robots" content="noindex, nofollow">
<link rel="icon" type="image/png" href="parieur_discipline_icon_1024.png">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
  color: #1a1a1a;
  line-height: 1.6;
  padding: 30px 16px 60px;
}}
.container {{
  max-width: 800px;
  margin: 0 auto;
}}
.header {{
  text-align: center;
  margin-bottom: 32px;
}}
.logo {{
  width: 56px;
  height: 56px;
  border-radius: 50%;
  margin-bottom: 12px;
}}
.title {{
  font-size: 1.8em;
  font-weight: 800;
  color: #1e3a8a;
  margin-bottom: 4px;
}}
.subtitle {{
  color: #6b7280;
  font-size: 0.95em;
}}
.banner {{
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #78350f;
  padding: 10px 20px;
  border-radius: 10px;
  text-align: center;
  font-weight: 700;
  font-size: 0.88em;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 28px;
}}
.stats-row {{
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 32px;
  flex-wrap: wrap;
}}
.stat-pill {{
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  padding: 6px 16px;
  font-size: 0.85em;
  font-weight: 600;
  color: #374151;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
@media (max-width: 600px) {{
  .title {{ font-size: 1.4em; }}
}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <img src="parieur_discipline_icon_1024.png" alt="Parieur Discipliné" class="logo">
    <div class="title">Parieur Discipliné</div>
    <div class="subtitle">Early Morning Predictions &mdash; {formatted_date}</div>
  </div>

  <div class="banner">⏰ Preliminary 7am Picks &mdash; Final picks with line movement analysis at 3pm ⏰</div>

  <div class="stats-row">
    <span class="stat-pill">🏒 NHL: {len(nhl_picks)} plays</span>
    <span class="stat-pill">🏀 NBA: {len(nba_picks)} plays</span>
    <span class="stat-pill">📋 Total: {total} picks</span>
  </div>

  {nhl_section}
  {nba_section}

  <div style="text-align:center;color:#9ca3af;font-size:0.8em;margin-top:40px;">
    These are preliminary AI picks generated at 7am. Final picks with line movement analysis are published at 3pm.<br>
    <a href="/" style="color:#4a90e2;text-decoration:none;">← Back to main site</a>
  </div>
</div>
</body>
</html>"""


def generate_early_picks_page():
    today = date.today().isoformat()

    nhl_raw = read_prediction_file("nhl", today)
    nba_raw = read_prediction_file("nba", today)

    nhl_picks = parse_picks(nhl_raw)
    nba_picks = parse_picks(nba_raw)

    html = build_page(today, nhl_picks, nba_picks)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generated {OUTPUT_PATH}: {len(nhl_picks)} NHL + {len(nba_picks)} NBA picks")


if __name__ == "__main__":
    generate_early_picks_page()
