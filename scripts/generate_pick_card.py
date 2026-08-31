#!/usr/bin/env python3
"""
Generate a shareable PNG pick-of-the-day card from dual_bet_of_the_day.txt.
Canvas height is calculated to fit content exactly — no empty space.
Output: docs/pick_card_{sport}_YYYY-MM-DD.png + docs/pick_card_{sport}_latest.png
"""

import io
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cairosvg
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "data" / "predictions" / "dual_bet_of_the_day.txt"
LOGO_FILE  = ROOT / "docs" / "parieur_discipline_icon_1024.png"
LOGOS_DIR  = ROOT / "docs" / "logos"
DOCS_DIR      = ROOT / "docs" / "picks"
ARCHIVE_DIR   = DOCS_DIR / "archive"
TZ         = ZoneInfo("America/Toronto")

# ── Colours ───────────────────────────────────────────────────────────────────
RINK   = (7,   17,  31)
DEEP   = (4,   10,  22)
PANEL  = (14,  26,  50)
GOLD   = (255, 184, 28)
WHITE  = (255, 255, 255)
SILVER = (175, 188, 205)
DIM    = (80,  95,  115)

W = 1080  # fixed width; height calculated per card

# ── NHL / NBA abbreviation maps ───────────────────────────────────────────────
NHL_ABBR = {
    "Anaheim Ducks": "ANA", "Boston Bruins": "BOS", "Buffalo Sabres": "BUF",
    "Calgary Flames": "CGY", "Carolina Hurricanes": "CAR", "Chicago Blackhawks": "CHI",
    "Colorado Avalanche": "COL", "Columbus Blue Jackets": "CBJ", "Dallas Stars": "DAL",
    "Detroit Red Wings": "DET", "Edmonton Oilers": "EDM", "Florida Panthers": "FLA",
    "Los Angeles Kings": "LAK", "Minnesota Wild": "MIN", "Montreal Canadiens": "MTL",
    "Montreal": "MTL", "Nashville Predators": "NSH", "New Jersey Devils": "NJD",
    "New York Islanders": "NYI", "New York Rangers": "NYR", "Ottawa Senators": "OTT",
    "Philadelphia Flyers": "PHI", "Pittsburgh Penguins": "PIT", "San Jose Sharks": "SJS",
    "Seattle Kraken": "SEA", "St. Louis Blues": "STL", "Tampa Bay Lightning": "TBL",
    "Toronto Maple Leafs": "TOR", "Utah Mammoth": "UTA", "Vancouver Canucks": "VAN",
    "Vegas Golden Knights": "VGK", "Washington Capitals": "WSH", "Winnipeg Jets": "WPG",
}
NBA_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}

# ── Font loader ───────────────────────────────────────────────────────────────
def load_font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Impact.ttf" if bold else None,
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

# ── Text helpers ──────────────────────────────────────────────────────────────
def strip_emoji(text):
    return re.sub(r'[^\x00-\x7FÀ-ɏ‘-…]+', '', text).strip()

def strip_md(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^[\U0001F300-\U0001FFFF☀-➿•\-⸻]\s*', '', text.strip())
    return strip_emoji(text).strip()

def text_height(font, text="Ag"):
    b = font.getbbox(text)
    return b[3] - b[1]

def text_width(font, text):
    b = font.getbbox(text)
    return b[2] - b[0]

def wrapped_lines(font, text, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if text_width(font, test) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def draw_wrapped(draw, text, x, y, max_width, font, fill, line_gap=5, align="left"):
    lines = wrapped_lines(font, text, max_width)
    lh = text_height(font)
    for line in lines:
        lx = x + (max_width - text_width(font, line)) // 2 if align == "center" else x
        draw.text((lx, y), line, font=font, fill=fill)
        y += lh + line_gap
    return y

def measure_wrapped(font, text, max_width, line_gap=5):
    lines = wrapped_lines(font, text, max_width)
    lh = text_height(font)
    return len(lines) * (lh + line_gap)

# ── SVG / logo helpers ────────────────────────────────────────────────────────
def svg_to_pil(svg_path, size):
    png = cairosvg.svg2png(url=str(svg_path), output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")

def load_team_logo(team_name, sport, size):
    abbr_map = NHL_ABBR if sport == "NHL" else NBA_ABBR
    abbr = abbr_map.get(team_name)
    if not abbr:
        return None
    for fname in [f"{abbr}_dark.svg", f"{abbr}.svg"]:
        svg = LOGOS_DIR / sport.lower() / fname
        if svg.exists():
            try:
                return svg_to_pil(svg, size)
            except Exception:
                return None
    return None

def paste_with_glow(img, team_logo, cx, cy, size):
    logo = team_logo.resize((size, size), Image.LANCZOS)
    a = logo.split()[3]
    glow_canvas = Image.new("RGBA", (size + 80, size + 80), (0, 0, 0, 0))
    gold_fill = Image.new("RGBA", logo.size, (*GOLD, 0))
    tinted = Image.composite(gold_fill, logo, a)
    tinted.putalpha(a)
    blurred = tinted.filter(ImageFilter.GaussianBlur(22))
    glow_canvas.paste(blurred, (40, 40), blurred)
    img.paste(glow_canvas, (cx - size // 2 - 40, cy - size // 2 - 40), glow_canvas)
    img.paste(logo, (cx - size // 2, cy - size // 2), logo)

# ── Parse bet-of-the-day file ─────────────────────────────────────────────────
def parse_teams_full(pick_line):
    m = re.match(r'^(.+?)\s+vs\.?\s+(.+?)(?:\s+(Over|Under|ML|Moneyline).*)$', pick_line, re.IGNORECASE)
    if m:
        away = m.group(1).strip()
        rest = pick_line[m.start(2):]
        kw = re.search(r'\s+(Over|Under|ML|Moneyline|\+|-\d)', rest, re.IGNORECASE)
        home = rest[:kw.start()].strip() if kw else m.group(2).strip()
        bet = pick_line[m.start(2) + len(home):].strip()
        return away, home, bet
    return None, None, pick_line

def parse_pick_file(path):
    text = path.read_text(encoding="utf-8")
    picks = []
    for section in re.split(r'[⸻—]{2,}', text):
        lines = [l.strip() for l in section.strip().splitlines() if l.strip()]
        if not lines:
            continue
        pick_line, sport_label = None, "NHL"
        for line in lines:
            m = re.search(r'PICK\s*[–\-]?\s*(NHL|NBA)\s*[🏒🏀]?\s*(.+)', line, re.IGNORECASE)
            if m:
                sport_label = m.group(1).upper()
                pick_line = strip_md(m.group(2)).strip()
                break
        if not pick_line:
            continue
        raw, in_pick = [], False
        for line in lines:
            if re.search(r'PICK\s*[–\-]', line, re.IGNORECASE):
                in_pick = True
                continue
            if in_pick:
                c = strip_md(line)
                if c and len(c) > 3:
                    raw.append(c)
        bullets, i = [], 0
        while i < len(raw):
            head = raw[i]
            if i + 1 < len(raw) and len(head) < 55 and len(raw[i+1]) > len(head):
                bullets.append({"head": head, "body": raw[i+1]})
                i += 2
            else:
                bullets.append({"head": None, "body": head})
                i += 1
        picks.append({"sport": sport_label, "pick": pick_line, "bullets": bullets[:5]})
    return picks

# ── Draw card with exact-fit height ──────────────────────────────────────────
def draw_card(pick, date_str, brand_logo):
    PAD      = 56
    LOGO_SZ  = 180
    INNER_W  = W - PAD * 2

    # Fonts
    f_brand   = load_font(26, bold=True)
    f_sub     = load_font(17)
    f_date    = load_font(18)
    f_vs      = load_font(52, bold=True)
    f_sport   = load_font(18, bold=True)
    f_team    = load_font(22, bold=True)
    f_pick    = load_font(48, bold=True)
    f_odds    = load_font(28)
    f_bhead   = load_font(24, bold=True)
    f_bbody   = load_font(21)
    f_footer  = load_font(18)

    sport = pick["sport"]
    away_name, home_name, bet_part = parse_teams_full(pick["pick"])

    m_odds = re.search(r'(@\s*[\d.]+|[\d.]+\s*$)', bet_part.strip())
    bet_type  = bet_part[:m_odds.start()].strip().rstrip('@').strip() if m_odds else bet_part.strip()
    odds_str  = m_odds.group(0).strip() if m_odds else ""
    odds_disp = f"@ {odds_str.lstrip('@').strip()}" if odds_str else ""

    # ── Measure all sections ──────────────────────────────────────────────────
    TH = text_height  # shorthand

    sec_header  = 6 + 20 + max(72, TH(f_brand)) + 16 + 1 + 20   # bar + logo row + divider
    sec_logos   = LOGO_SZ + 16 + TH(f_team) + 10                 # logos + team names + gap
    sec_pick    = TH(f_vs) + 14 \
                + measure_wrapped(f_pick, bet_type.upper(), INNER_W) + 6 \
                + (TH(f_odds) + 14 + 8 + 18 if odds_disp else 12)     # vs + pick + odds
    sec_div     = 1 + 20                                           # divider line

    sec_bullets = 0
    for b in pick["bullets"]:
        if b.get("head"):
            sec_bullets += TH(f_bhead) + 3
        sec_bullets += measure_wrapped(f_bbody, b["body"], INNER_W - 14, line_gap=3)
        sec_bullets += 16

    sec_footer = 20 + TH(f_footer) + 20   # padding + url + padding

    H_card = sec_header + sec_logos + sec_pick + sec_div + sec_bullets + sec_footer + 20

    # ── Render ────────────────────────────────────────────────────────────────
    img = Image.new("RGB", (W, H_card))
    draw = ImageDraw.Draw(img)

    # Gradient background
    for row in range(H_card):
        t = row / H_card
        r = int(DEEP[0] + (PANEL[0] - DEEP[0]) * min(t * 1.6, 1))
        g = int(DEEP[1] + (PANEL[1] - DEEP[1]) * min(t * 1.6, 1))
        b = int(DEEP[2] + (PANEL[2] - DEEP[2]) * min(t * 1.6, 1))
        draw.line([(0, row), (W, row)], fill=(r, g, b))

    # Top bar
    draw.rectangle([(0, 0), (W, 6)], fill=GOLD)

    # Brand header
    y = 20
    logo_img = brand_logo.resize((72, 72), Image.LANCZOS)
    img.paste(logo_img, (PAD, y), logo_img.split()[3])
    draw.text((PAD + 72 + 14, y + 10), "PARIEUR DISCIPLINÉ", font=f_brand, fill=GOLD)
    draw.text((PAD + 72 + 16, y + 42), "www.parieurdiscipline.com", font=f_sub, fill=DIM)
    dw = text_width(f_date, date_str)
    draw.text((W - PAD - dw, y + 26), date_str, font=f_date, fill=DIM)
    y += 92

    # Divider
    draw.line([(PAD, y), (W - PAD, y)], fill=(255, 255, 255, 25), width=1)
    y += 20

    # Team logos
    cx_away, cx_home = W // 4, 3 * W // 4
    logo_away = load_team_logo(away_name, sport, LOGO_SZ) if away_name else None
    logo_home = load_team_logo(home_name, sport, LOGO_SZ) if home_name else None
    logo_cy = y + LOGO_SZ // 2
    if logo_away:
        paste_with_glow(img, logo_away, cx_away, logo_cy, LOGO_SZ)
    if logo_home:
        paste_with_glow(img, logo_home, cx_home, logo_cy, LOGO_SZ)

    # VS centered between logos
    vs_w = text_width(f_vs, "VS")
    draw.text(((W - vs_w) // 2, logo_cy - TH(f_vs) // 2), "VS", font=f_vs, fill=GOLD)
    y += LOGO_SZ + 10

    # Team names under logos
    if away_name:
        aw = text_width(f_team, away_name.upper())
        draw.text((cx_away - aw // 2, y), away_name.upper(), font=f_team, fill=WHITE)
    if home_name:
        hw = text_width(f_team, home_name.upper())
        draw.text((cx_home - hw // 2, y), home_name.upper(), font=f_team, fill=WHITE)
    y += TH(f_team) + 18

    # Pick type
    bt = bet_type.upper()
    bw = text_width(f_pick, bt)
    draw.text(((W - bw) // 2, y), bt, font=f_pick, fill=WHITE)
    y += TH(f_pick) + 8

    # Odds pill — solid gold background, dark text
    if odds_disp:
        ow = text_width(f_odds, odds_disp)
        ox = (W - ow - 32) // 2
        draw.rounded_rectangle([(ox, y), (ox + ow + 32, y + TH(f_odds) + 14)],
                                radius=10, fill=GOLD)
        draw.text((ox + 16, y + 7), odds_disp, font=f_odds, fill=RINK)
        y += TH(f_odds) + 14 + 18
    else:
        y += 12

    # Divider
    draw.line([(PAD, y), (W - PAD, y)], fill=(255, 184, 28, 60), width=1)
    y += 20

    # Bullets
    for bullet in pick["bullets"]:
        head = bullet.get("head")
        body = bullet.get("body", "")
        if head:
            draw.text((PAD, y), head.upper(), font=f_bhead, fill=GOLD)
            y += TH(f_bhead) + 3
        if body:
            y = draw_wrapped(draw, body, PAD + (14 if head else 0), y,
                             INNER_W - (14 if head else 0), f_bbody, fill=SILVER, line_gap=3)
        y += 16

    # Footer
    y += 10
    draw.line([(0, y), (W, y)], fill=GOLD, width=2)
    y += 12
    footer_text = "www.parieurdiscipline.com  |  AI-Powered Picks"
    fw = text_width(f_footer, footer_text)
    draw.text(((W - fw) // 2, y), footer_text, font=f_footer, fill=DIM)
    y += TH(f_footer) + 16

    return img.crop((0, 0, W, y))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not INPUT_FILE.exists():
        print(f"No input file: {INPUT_FILE}")
        sys.exit(1)
    picks = parse_pick_file(INPUT_FILE)
    if not picks:
        print("No picks parsed.")
        sys.exit(1)

    brand_logo = Image.open(LOGO_FILE).convert("RGBA")
    today      = datetime.now(TZ)
    date_str   = today.strftime("%B %d, %Y").upper()
    date_slug  = today.strftime("%Y-%m-%d")
    DOCS_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)

    cards = []
    for pick in picks:
        sport = pick["sport"].lower()
        card  = draw_card(pick, date_str, brand_logo)
        out_dated  = ARCHIVE_DIR / f"pick_card_{sport}_{date_slug}.png"
        out_latest = DOCS_DIR / f"pick_card_{sport}_latest.png"
        card.save(out_dated,  "PNG", optimize=True)
        card.save(out_latest, "PNG", optimize=True)
        print(f"✅ {sport.upper()} card → {out_dated.name}  ({card.width}×{card.height})")
        cards.append(card)

    if len(cards) == 1:
        cards[0].save(DOCS_DIR / "pick_card_latest.png", "PNG", optimize=True)
    else:
        total_h = sum(c.height for c in cards)
        combined = Image.new("RGB", (W, total_h))
        y = 0
        for c in cards:
            combined.paste(c, (0, y))
            y += c.height
        out_dual = ARCHIVE_DIR / f"pick_card_dual_{date_slug}.png"
        combined.save(out_dual, "PNG", optimize=True)
        combined.save(DOCS_DIR / "pick_card_latest.png", "PNG", optimize=True)
        print(f"✅ Dual card  → {out_dual.name}")


if __name__ == "__main__":
    main()
