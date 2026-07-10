#!/usr/bin/env python3
"""Fetch 2025-2026 regular season stats from the NHL API and upsert into poolers_players.

- Updates existing players: last_gp, last_g, last_a, last_pts, pp_pct
- Inserts missing players above a points threshold (default: 50 pts)

Usage:
    python scripts/scrape_poolers_stats.py              # update + add players >= 50 pts
    python scripts/scrape_poolers_stats.py --min-pts 40 # lower threshold
    python scripts/scrape_poolers_stats.py --update-only # skip adding new players
"""

import re
import sys
import time
import unicodedata
import argparse
import requests
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
GAMETYPE = 2   # regular season

NHL_TEAMS = [
    "ANA","BOS","BUF","CAR","CBJ","CGY","CHI","COL","DAL","DET",
    "EDM","FLA","LAK","MIN","MTL","NJD","NSH","NYI","NYR","OTT",
    "PHI","PIT","SEA","SJS","STL","TBL","TOR","UTA","VAN","VGK","WPG","WSH",
]

POS_MAP = {"C": "C", "L": "LW", "R": "RW", "D": "D", "G": "G"}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})


def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_str).strip().lower()


def fetch_team_stats(abbr: str) -> list[dict]:
    url = f"https://api-web.nhle.com/v1/club-stats/{abbr}/{SEASON}/{GAMETYPE}"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        skaters = data.get("skaters", [])
        for s in skaters:
            s["_team"] = abbr
        return skaters
    except Exception as e:
        print(f"    ⚠️  {abbr}: {e}")
        return []


def fetch_pp_stats(player_id: int) -> int:
    url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        for s in data.get("seasonTotals", []):
            if str(s.get("season", "")) == SEASON and s.get("gameTypeId") == GAMETYPE:
                return s.get("powerPlayPoints") or 0
        return 0
    except Exception:
        return 0


def fetch_player_age(player_id: int) -> int | None:
    url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        dob = r.json().get("birthDate", "")
        return 2026 - int(dob[:4]) if dob else None
    except Exception:
        return None


def build_stats_map(skaters: list[dict]) -> dict[str, dict]:
    result = {}
    for s in skaters:
        name = normalize(f"{s['firstName']['default']} {s['lastName']['default']}")
        result[name] = {
            "nhl_player_id": s.get("playerId"),
            "full_name":     f"{s['firstName']['default']} {s['lastName']['default']}",
            "team":          s.get("_team", ""),
            "pos":           POS_MAP.get(s.get("positionCode", "C"), "C"),
            "last_gp":       s.get("gamesPlayed") or 0,
            "last_g":        s.get("goals") or 0,
            "last_a":        s.get("assists") or 0,
            "last_pts":      s.get("points") or 0,
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-pts", type=int, default=50,
                        help="Min pts to auto-add missing players (default: 50)")
    parser.add_argument("--update-only", action="store_true",
                        help="Only update existing players, don't add new ones")
    args = parser.parse_args()

    print(f"📊  Poolers Guide Stats — {SEASON} regular season → poolers_players")
    print(f"    Mode: {'update only' if args.update_only else f'update + add players >= {args.min_pts} pts'}")
    print("─" * 55)

    # 1. Load existing players
    existing_rows = supabase.table("poolers_players").select("id,name,rank").execute().data
    poolers_map = {normalize(r["name"]): r["id"] for r in existing_rows if r.get("name")}
    max_rank = max((r.get("rank") or 0 for r in existing_rows), default=0)
    print(f"  Found {len(existing_rows)} existing players (max rank: {max_rank})\n")

    # 2. Fetch all NHL stats
    print("  Fetching NHL API stats for all 32 teams…")
    all_skaters: list[dict] = []
    for abbr in NHL_TEAMS:
        skaters = fetch_team_stats(abbr)
        all_skaters.extend(skaters)
        print(f"    ✓ {abbr}: {len(skaters)} skaters")
        time.sleep(0.2)

    all_stats = build_stats_map(all_skaters)
    print(f"\n  Total NHL skaters loaded: {len(all_stats)}")
    print("─" * 55)

    # 3. Update existing players
    matched = 0
    unmatched = []
    print("\n  Updating existing players…")

    for norm_name, player_id in poolers_map.items():
        stats = all_stats.get(norm_name)
        if not stats:
            last = norm_name.split()[-1] if norm_name else ""
            candidates = {k: v for k, v in all_stats.items() if k.endswith(" " + last)}
            if len(candidates) == 1:
                stats = list(candidates.values())[0]

        if not stats:
            unmatched.append(norm_name)
            continue

        nhl_id = stats.get("nhl_player_id")
        pp_pts = fetch_pp_stats(nhl_id) if nhl_id else 0
        time.sleep(0.05)

        total_pts = stats["last_pts"]
        pp_pct = round((pp_pts / total_pts) * 100) if total_pts else None

        supabase.table("poolers_players").update({
            "last_gp":  stats["last_gp"],
            "last_g":   stats["last_g"],
            "last_a":   stats["last_a"],
            "last_pts": stats["last_pts"],
            "pp_pct":   pp_pct,
        }).eq("id", player_id).execute()

        print(f"  ✅  {norm_name}: {stats['last_g']}G {stats['last_a']}A {stats['last_pts']}PTS  PP%={pp_pct}")
        matched += 1

    # 4. Add missing players above threshold
    added = 0
    if not args.update_only:
        print(f"\n  Looking for missing players with >= {args.min_pts} pts…")
        candidates = sorted(
            [(name, s) for name, s in all_stats.items()
             if s["last_pts"] >= args.min_pts and name not in poolers_map],
            key=lambda x: x[1]["last_pts"], reverse=True
        )
        print(f"  Found {len(candidates)} players above threshold not in guide\n")

        for norm_name, stats in candidates:
            nhl_id = stats.get("nhl_player_id")
            pp_pts = fetch_pp_stats(nhl_id) if nhl_id else 0
            time.sleep(0.05)
            age = fetch_player_age(nhl_id) if nhl_id else None
            time.sleep(0.05)

            total_pts = stats["last_pts"]
            pp_pct = round((pp_pts / total_pts) * 100) if total_pts else None
            max_rank += 1

            new_row = {
                "rank":     max_rank,
                "name":     stats["full_name"],
                "team":     stats["team"],
                "pos":      stats["pos"],
                "age":      age,
                "last_gp":  stats["last_gp"],
                "last_g":   stats["last_g"],
                "last_a":   stats["last_a"],
                "last_pts": stats["last_pts"],
                "pp_pct":   pp_pct,
                "proj_gp":  stats["last_gp"],
                "proj_g":   stats["last_g"],
                "proj_a":   stats["last_a"],
                "proj_pts": stats["last_pts"],
                "tier":     "Mid",
                "notes":    "",
            }
            supabase.table("poolers_players").insert(new_row).execute()
            print(f"  ➕  {stats['full_name']} ({stats['team']}) — {stats['last_pts']}PTS  PP%={pp_pct}")
            added += 1

    print("\n" + "─" * 55)
    print(f"🎉  Done! {matched} updated, {added} added, {len(unmatched)} unmatched.")
    if unmatched:
        print("\n  ⚠️  Unmatched (fix names manually):")
        for n in unmatched:
            print(f"    - {n}")


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
