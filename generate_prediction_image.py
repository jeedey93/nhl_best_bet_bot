import os
import re
from datetime import date
from glob import glob
from dotenv import load_dotenv

# Optional fallback image generation
from PIL import Image, ImageDraw, ImageFont

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except Exception:
    HAS_GENAI = False

PREDICTIONS_DIR = "predictions"
OUTPUT_DIR = "images/generated"
os.makedirs(OUTPUT_DIR, exist_ok=True)

load_dotenv()

# New: explicit regex for "Bet of the Day" block
BET_OF_DAY_REGEX = re.compile(
    r"""
    ^\s*\#{0,6}\s*Bet\s+of\s+the\s+Day\s*$      # header line
    (?:\s*\n)+                                  # one or more newlines
    \s*\**\s*                                   # optional bold start (**)
    (?P<betline>.+?)                            # full bet line (e.g., "Team ML vs Opponent")
    \s*@\s*(?P<odds>[\d\.]+)\s*                 # odds after '@'
    \**\s*$                                     # optional bold end
    """,
    re.IGNORECASE | re.VERBOSE | re.MULTILINE,
)

FIRST_PLAY_REGEX = re.compile(
    r"""
    \**\s*                                   # optional bold start
    (?P<teams>.+?(?:\s+vs\s+|\s+@\s+).+?)    # "Team A vs Team B" or "Team A @ Team B"
    \s*:\s*                                  # colon separator
    (?P<bet>.+?)                              # bet description
    (?:                                       # odds as @ price OR (Odds: price)
        \s*@\s*(?P<price1>[\d\.]+)           # "@ 1.95"
        |
        \s*\(\s*Odds:\s*(?P<price2>[\d\.]+)\s*\)  # "(Odds: 1.95)"
    )
    \s*\**                                   # optional bold end
    """,
    re.IGNORECASE | re.VERBOSE
)


def get_latest_predictions_file(sport_prefix: str) -> str | None:
    # Look for files like predictions/{sport}/nba_daily_predictions_YYYY-MM-DD.txt
    folder = os.path.join(PREDICTIONS_DIR, sport_prefix)
    pattern = os.path.join(folder, f"{sport_prefix}_daily_predictions_*.txt")
    files = glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)


def _split_teams_from_betline(betline: str) -> tuple[str, str, str]:
    """Try to derive home/away from a betline string.
    Returns (home, away, bet_desc). bet_desc is the original betline if teams are not derivable.
    """
    line = betline.strip()
    # Common formats we may see:
    # "Minnesota Timberwolves vs Atlanta Hawks: Over 246.5"
    # "Toronto Maple Leafs @ Edmonton Oilers: Maple Leafs ML"
    # "Vancouver Canucks to Win" (no explicit opponent)
    if " vs " in line:
        teams_part, _, bet_desc = line.partition(":")
        home, away = teams_part.split(" vs ", 1)
        return home.strip(), away.strip(), (bet_desc or "").strip() or line
    if " @ " in line:
        teams_part, _, bet_desc = line.partition(":")
        away, home = teams_part.split(" @ ", 1)
        return home.strip(), away.strip(), (bet_desc or "").strip() or line
    # No teams in line; return empty away, use line as bet_desc
    return line, "", line


def extract_first_play(predictions_text: str) -> dict | None:
    """Extract the highest-confidence play to render an image.
    Priority: "Bet of the Day: <betline> @ <odds>" if present; otherwise fallback to the first bold play line.
    """
    # 1) Look for explicit Bet of the Day block
    bod_match = BET_OF_DAY_REGEX.search(predictions_text)
    if bod_match:
        betline = bod_match.group("betline").strip()
        odds = bod_match.group("odds").strip()
        home, away, bet_desc = _split_teams_from_betline(betline)
        return {
            "home": home,
            "away": away,
            "bet": bet_desc if bet_desc else betline,
            "odds": odds,
            "game": f"{home} vs {away}" if home and away else betline,
        }

    print(bod_match)

    # 2) Fallback: first bold play line in the AI Analysis Summary
    match = FIRST_PLAY_REGEX.search(predictions_text)
    if not match:
        # Fallback: scan line by line
        for line in predictions_text.splitlines():
            line = line.strip()
            if not line:
                continue
            match = FIRST_PLAY_REGEX.search(line)
            if match:
                break
    if not match:
        return None

    # Use named groups for robustness
    game = match.group("teams").strip()
    bet_desc = match.group("bet").strip()
    price1 = match.group("price1")
    price2 = match.group("price2")
    odds = (price1 or price2 or "").strip()

    # Split teams for either 'vs' or '@'
    if " vs " in game:
        home_team, away_team = game.split(" vs ", 1)
    elif " @ " in game:
        away_team, home_team = game.split(" @ ", 1)
    else:
        home_team = game
        away_team = ""

    return {
        "home": home_team.strip(),
        "away": away_team.strip(),
        "bet": bet_desc,
        "odds": odds,
        "game": game,
    }


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_bytes_to_png(image_bytes: bytes, out_path: str):
    with open(out_path, "wb") as f:
        f.write(image_bytes)


def generate_image_with_gemini(play: dict, api_key: str) -> bytes | None:
    """
    Ask Gemini to generate a matchup image with the bet text rendered.
    Returns PNG bytes or None.
    """
    if not HAS_GENAI:
        return None
    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            "Create a clean, broadcast-style matchup graphic for an NBA game. "
            "Show both teams visually (logos or styled text), center the matchup, "
            "and include a clear banner with the betting recommendation. "
            "Design tips: modern, high contrast, readable, no gore or real logos if unavailable; "
            "use team names and colors if logos aren't accessible.\n\n"
            f"Matchup: {play['home']} vs {play['away']}\n"
            f"Bet: {play['bet']} @ {play['odds']}\n"
            "Layout request: Place the matchup on three centered lines — Home (line 1), 'vs' (line 2), Away (line 3).\n"
            "Include: Date and sport (NBA), and a subtle footer 'Generated by Best Bet Bot'."
        )
        print("[debug] Prompt length:", len(prompt))
        # Use the image-capable model from your list
        try:
            response = client.models.generate_content(
                model="models/gemini-2.5-flash-image",
                contents=types.Part.from_text(text=prompt),
                # Some image generation endpoints return binary; google-genai returns parts
            )
        except Exception as e:
            print("[error] Gemini generation failed:", str(e))
            return None

        # Try to extract an image part from the response
        for cand in getattr(response, "candidates", []):
            parts = getattr(cand.content, "parts", [])
            for p in parts:
                if getattr(p, "inline_data", None) and getattr(p.inline_data, "mime_type", "").startswith("image/"):
                    return p.inline_data.data
        return None
    except Exception:
        return None


def generate_image_with_pillow(play: dict, out_path: str):
    # Simple 1200x675 banner image with team names and bet text
    width, height = 1200, 675
    img = Image.new("RGB", (width, height), color=(20, 24, 28))
    draw = ImageDraw.Draw(img)

    # Try to load a system font; fallback to default
    try:
        font_title = ImageFont.truetype("Arial.ttf", 64)
        font_vs = ImageFont.truetype("Arial.ttf", 54)
        font_sub = ImageFont.truetype("Arial.ttf", 40)
    except Exception:
        font_title = ImageFont.load_default()
        font_vs = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    bet_line = f"Odds @ {play['odds']}"
    footer = "Generated by le Parieur Discipliné"

    # Centered text helper
    def center_text(text, y, font, fill=(240, 240, 240)):
        w, h = draw.textbbox((0, 0), text, font=font)[2:]
        x = (width - w) // 2
        draw.text((x, y), text, font=font, fill=fill)
        return h

    # Header
    center_text("NBA Matchup", 40, font_sub, (180, 220, 255))

    # Three-line title: Home \n vs \n Away
    home_h = draw.textbbox((0, 0), play['home'], font=font_title)[3]
    vs_h = draw.textbbox((0, 0), "vs", font=font_vs)[3]
    away_h = draw.textbbox((0, 0), play['away'], font=font_title)[3]

    base_y = 140  # top of the block
    center_text(play['home'], base_y, font_title, (255, 255, 255))
    center_text("vs", base_y + home_h + 10, font_vs, (200, 200, 200))
    center_text(play['away'], base_y + home_h + 10 + vs_h + 10, font_title, (255, 255, 255))

    # Bet line below the title block
    center_text(bet_line, 330, font_sub, (255, 215, 0))

    # Simple halves background accent
    draw.rectangle([0, 370, width//2, height], fill=(35, 45, 60))
    draw.rectangle([width//2, 370, width, height], fill=(60, 45, 35))

    # Footer
    center_text(footer, 620, font_sub, (180, 180, 180))

    img.save(out_path, format="PNG")


def main():
    # Prefer NBA; fallback to NHL if NBA not found
    sport_order = ["nba", "nhl"]
    latest_path = None
    sport_found = None
    for sp in sport_order:
        p = get_latest_predictions_file(sp)
        if p:
            latest_path = p
            sport_found = sp
            break
    if not latest_path:
        print("No predictions file found.")
        return

    text = read_file(latest_path)
    play = extract_first_play(text)
    if not play:
        print("No betting play found in predictions.")
        return

    today_str = date.today().isoformat()
    out_path = os.path.join(OUTPUT_DIR, f"{sport_found}_{today_str}.png")

    # Try Gemini image generation first
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    image_bytes = None
    if api_key:
        image_bytes = generate_image_with_gemini(play, api_key)

    print(f"Generating image for {play['bet']} @ {play['odds']}")
    if image_bytes:
        save_bytes_to_png(image_bytes, out_path)
        print(f"Saved Gemini-generated image to {out_path}")
    else:
        # Fallback to Pillow
        generate_image_with_pillow(play, out_path)
        print(f"Saved fallback image to {out_path}")


if __name__ == "__main__":
    main()

