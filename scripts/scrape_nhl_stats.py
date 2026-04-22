#!/usr/bin/env python3
"""Fetch 2025-2026 regular season stats from the NHL API and upsert into nhl_players.

Matches players by normalised full name (first + last, lowercase, no accents).
Run after scrape_nhl_players.py so rows already exist.
"""

import re
import sys
import time
import unicodedata
import argparse
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌  Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
    sys.exit(1)

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

SEASON   = "20252026"
GAMETYPE = 2          # regular season

NHL_TEAM_ABBR = {
    "anaheim-ducks":        "ANA",
    "boston-bruins":        "BOS",
    "buffalo-sabres":       "BUF",
    "calgary-flames":       "CGY",
    "carolina-hurricanes":  "CAR",
    "chicago-blackhawks":   "CHI",
    "colorado-avalanche":   "COL",
    "columbus-blue-jackets":"CBJ",
    "dallas-stars":         "DAL",
    "detroit-red-wings":    "DET",
    "edmonton-oilers":      "EDM",
    "florida-panthers":     "FLA",
    "los-angeles-kings":    "LAK",
    "minnesota-wild":       "MIN",
    "montreal-canadiens":   "MTL",
    "nashville-predators":  "NSH",
    "new-jersey-devils":    "NJD",
    "new-york-islanders":   "NYI",
    "new-york-rangers":     "NYR",
    "ottawa-senators":      "OTT",
    "philadelphia-flyers":  "PHI",
    "pittsburgh-penguins":  "PIT",
    "san-jose-sharks":      "SJS",
    "seattle-kraken":       "SEA",
    "st-louis-blues":       "STL",
    "tampa-bay-lightning":  "TBL",
    "toronto-maple-leafs":  "TOR",
    "utah-hockey-club":     "UTA",
    "vancouver-canucks":    "VAN",
    "vegas-golden-knights": "VGK",
    "washington-capitals":  "WSH",
    "winnipeg-jets":        "WPG",
}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})


def normalize(name: str) -> str:
    """Lowercase, strip accents, collapse spaces."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_str).strip().lower()


def fetch_team_stats(abbr: str) -> tuple[list[dict], list[dict]]:
    """Return (skaters, goalies) from the NHL API for one team."""
    url = f"https://api-web.nhle.com/v1/club-stats/{abbr}/{SEASON}/{GAMETYPE}"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("skaters", []), data.get("goalies", [])
    except Exception as e:
        print(f"    ⚠️  {abbr}: {e}")
        return [], []


def build_stats_map(skaters: list[dict], goalies: list[dict]) -> dict[str, dict]:
    """Key: normalised full name → stats dict."""
    result = {}
    for s in skaters:
        name = normalize(f"{s['firstName']['default']} {s['lastName']['default']}")
        result[name] = {
            "games_played": s.get("gamesPlayed"),
            "goals":        s.get("goals"),
            "assists":      s.get("assists"),
            "points":       s.get("points"),
            "wins":         None,
            "shutouts":     None,
        }
    for g in goalies:
        name = normalize(f"{g['firstName']['default']} {g['lastName']['default']}")
        result[name] = {
            "games_played": g.get("gamesPlayed"),
            "goals":        None,
            "assists":      None,
            "points":       None,
            "wins":         g.get("wins"),
            "shutouts":     g.get("shutouts"),
        }
    return result


def upsert_stats(rows: list[dict]) -> None:
    for row in rows:
        slug = row.pop("puckpedia_slug")
        result = supabase.table("nhl_players").update(row).eq("puckpedia_slug", slug).execute()
        if hasattr(result, "error") and result.error:
            print(f"  ❌  {slug}: {result.error}")
    print(f"  ✅  Updated {len(rows)} rows")


def main():
    parser = argparse.ArgumentParser(description="Fetch NHL season stats → Supabase")
    parser.add_argument("--team", help="Single team slug (e.g. boston-bruins)")
    args = parser.parse_args()

    teams = [args.team] if args.team else list(NHL_TEAM_ABBR.keys())

    print(f"📊  NHL Stats Scraper — {SEASON} regular season → Supabase")
    print("─" * 50)

    total_matched = 0
    total_missed  = 0

    for slug in teams:
        abbr = NHL_TEAM_ABBR.get(slug)
        if not abbr:
            print(f"  ⚠️  Unknown slug: {slug}")
            continue

        print(f"  🏒  {slug} ({abbr})")
        skaters, goalies = fetch_team_stats(abbr)
        stats_map = build_stats_map(skaters, goalies)

        # Fetch existing DB rows for this team
        db_rows = supabase.table("nhl_players").select(
            "puckpedia_slug,player_name"
        ).eq("team", slug).execute().data

        updates = []
        now = datetime.now(timezone.utc).isoformat()

        for row in db_rows:
            raw_name = row["player_name"] or ""
            # PuckPedia names may be "Last, First" — normalise either way
            if "," in raw_name:
                last, first = raw_name.split(",", 1)
                full = f"{first.strip()} {last.strip()}"
            else:
                full = raw_name
            key = normalize(full)
            stats = stats_map.get(key)
            if not stats:
                # Try last-name-only fallback for common mismatches
                last_key = normalize(full.split()[-1]) if full else ""
                stats = next((v for k, v in stats_map.items() if k.endswith(last_key) and last_key), None)

            if stats:
                updates.append({
                    "puckpedia_slug": row["puckpedia_slug"],
                    "updated_at":     now,
                    **stats,
                })
                total_matched += 1
            else:
                print(f"      ⚠️  No stats match: {full!r}")
                total_missed += 1

        if updates:
            upsert_stats(updates)
        else:
            print("      (no updates)")

        time.sleep(0.3)

    print("\n" + "─" * 50)
    print(f"🎉  Done! {total_matched} matched, {total_missed} unmatched.")


if __name__ == "__main__":
    main()
