#!/usr/bin/env python3
"""Fetch 2025-2026 regular season stats from the NHL API and upsert into nhl_players.

Matches players by normalised full name (first + last, lowercase, no accents).
Run after scrape_nhl_players.py so rows already exist.

Also populates:
  injury_status  — from roster endpoint injuryStatus field
  last5_game_pts — last 5 games pool points (oldest→newest) from game-log endpoint
"""

import re
import sys
import time
import unicodedata
import argparse
import requests
import json
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
GAMETYPE = 3          # playoffs

# Teams still active in the 2026 playoffs. Players on all other teams get zeroed out
# so their regular-season stats don't pollute pool standings.
PLAYOFF_TEAMS = {
    "ANA", "BOS", "BUF", "CAR", "COL", "DAL", "EDM", "LAK",
    "MIN", "MTL", "OTT", "PHI", "PIT", "TBL", "UTA", "VGK",
}

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


def fetch_roster_injury_map(abbr: str) -> dict[int, str]:
    """Return {playerId: injuryStatus} for a team from the roster endpoint."""
    url = f"https://api-web.nhle.com/v1/roster/{abbr}/{SEASON}"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"    ⚠️  roster {abbr}: {e}")
        return {}
    result = {}
    for group in ("forwards", "defensemen", "goalies"):
        for p in data.get(group, []):
            pid = p.get("id")
            status = p.get("injuryStatus") or "Active"
            if pid:
                result[pid] = status
    return result


def fetch_last5_game_pts(player_id: int, position: str, scoring: dict) -> list[int]:
    """Return list of pool-points for the last ≤5 games (oldest→newest)."""
    url = f"https://api-web.nhle.com/v1/player/{player_id}/game-log/{SEASON}/3"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        games = r.json().get("gameLog", [])
    except Exception:
        return []

    pos = position.upper() if position else "F"
    is_goalie = pos == "G"
    pts_list = []
    for g in games[-5:]:
        if is_goalie:
            w = 1 if g.get("decision", "").upper() == "W" else 0
            so = g.get("shutouts", 0) or 0
            pts_list.append(w * scoring["g_wins"] + so * scoring["g_shutouts"])
        else:
            pts_list.append(g.get("points", 0) or 0)
    return pts_list


def build_stats_map(skaters: list[dict], goalies: list[dict]) -> dict[str, dict]:
    """Key: normalised full name → stats dict."""
    result = {}
    for s in skaters:
        name = normalize(f"{s['firstName']['default']} {s['lastName']['default']}")
        result[name] = {
            "nhl_player_id": s.get("playerId"),
            "games_played": s.get("gamesPlayed"),
            "goals":        s.get("goals"),
            "assists":      s.get("assists"),
            "points":       s.get("points"),
            "wins":         None,
            "ot_losses":    None,
            "shutouts":     None,
            "save_pct":     None,
            "gaa":          None,
            "_position":    "F",
        }
    for g in goalies:
        name = normalize(f"{g['firstName']['default']} {g['lastName']['default']}")
        result[name] = {
            "nhl_player_id": g.get("playerId"),
            "games_played": g.get("gamesPlayed"),
            "goals":        None,
            "assists":      None,
            "points":       None,
            "wins":         g.get("wins"),
            "ot_losses":    g.get("overtimeLosses"),
            "shutouts":     g.get("shutouts"),
            "save_pct":     g.get("savePercentage") if g.get("savePercentage") is not None else g.get("savePctg"),
            "gaa":          g.get("goalsAgainstAverage"),
            "_position":    "G",
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
    parser.add_argument("--no-extras", action="store_true", help="Skip injury/sparkline fetching (faster)")
    args = parser.parse_args()

    teams = [args.team] if args.team else list(NHL_TEAM_ABBR.keys())

    # Default scoring multipliers (matches pool defaults)
    scoring = {"g_wins": 2, "g_shutouts": 3}

    print(f"📊  NHL Stats Scraper — {SEASON} playoffs → Supabase")
    print("─" * 50)

    # Zero out all players on non-playoff teams so regular-season stats
    # don't appear in pool standings.
    non_playoff_slugs = [slug for slug, abbr in NHL_TEAM_ABBR.items() if abbr not in PLAYOFF_TEAMS]
    if non_playoff_slugs:
        print(f"  🧹  Zeroing stats for {len(non_playoff_slugs)} non-playoff teams…")
        zero = {
            "goals": 0, "assists": 0, "points": 0,
            "wins": 0, "shutouts": 0, "games_played": 0,
            "ot_losses": 0, "save_pct": None, "gaa": None,
            "last5_game_pts": None,
        }
        for slug in non_playoff_slugs:
            rows = supabase.table("nhl_players").select("puckpedia_slug").eq("team", slug).execute().data
            if rows:
                supabase.table("nhl_players").update(zero).eq("team", slug).execute()
                print(f"      ✅  Zeroed {len(rows)} players for {slug}")
        print()

    total_matched = 0
    total_missed  = 0

    for slug in teams:
        abbr = NHL_TEAM_ABBR.get(slug)
        if not abbr:
            print(f"  ⚠️  Unknown slug: {slug}")
            continue

        print(f"  🏒  {slug} ({abbr})")
        if abbr not in PLAYOFF_TEAMS:
            continue  # already zeroed above
        skaters, goalies = fetch_team_stats(abbr)
        stats_map = build_stats_map(skaters, goalies)

        # Injury status map: {playerId → status}
        injury_map = {} if args.no_extras else fetch_roster_injury_map(abbr)

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
                player_id = stats.get("nhl_player_id")
                position  = stats.get("_position", "F")

                # Injury status
                injury_status = injury_map.get(player_id, "Active") if player_id and not args.no_extras else "Active"

                # Last-5-game sparkline
                if player_id and not args.no_extras:
                    last5 = fetch_last5_game_pts(player_id, position, scoring)
                    time.sleep(0.05)   # be gentle per-player
                else:
                    last5 = None

                # Strip internal fields before upsert
                clean_stats = {k: v for k, v in stats.items() if not k.startswith("_")}

                updates.append({
                    "puckpedia_slug":  row["puckpedia_slug"],
                    "updated_at":      now,
                    "injury_status":   injury_status,
                    "last5_game_pts":  json.dumps(last5) if last5 is not None else None,
                    **clean_stats,
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
    try:
        main()
        print("\n✅ Script completed successfully")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)
