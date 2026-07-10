#!/usr/bin/env python3
"""Fetch 2025-2026 regular season stats from the NHL API and upsert into poolers_players.

- Updates existing players: last_gp, last_g, last_a, last_pts, pp_pct
- Inserts ALL missing skaters (or above --min-pts threshold)

Age and PP% are fetched from the roster + landing page — one call per team
for roster (age), one call per new/updated player for PP points.

Usage:
    python scripts/scrape_poolers_guide_stats.py            # all players
    python scripts/scrape_poolers_guide_stats.py --min-pts 20
    python scripts/scrape_poolers_guide_stats.py --update-only
"""

import re
import sys
import time
import unicodedata
import argparse
import requests
from datetime import date
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
GAMETYPE = 2

NHL_TEAMS = [
    "ANA","BOS","BUF","CAR","CBJ","CGY","CHI","COL","DAL","DET",
    "EDM","FLA","LAK","MIN","MTL","NJD","NSH","NYI","NYR","OTT",
    "PHI","PIT","SEA","SJS","STL","TBL","TOR","UTA","VAN","VGK","WPG","WSH",
]

POS_MAP = {"C": "C", "L": "LW", "R": "RW", "D": "D", "G": "G"}

# Team name corrections (NHL API may return old abbreviations)
TEAM_REMAP = {"ARI": "UTA"}
DRAFT_YEAR = 2026   # used to compute age from birth year

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})


def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_str).strip().lower()


def fetch_team_stats(abbr: str) -> list[dict]:
    """Fetch club-stats (has powerPlayGoals per skater)."""
    url = f"https://api-web.nhle.com/v1/club-stats/{abbr}/{SEASON}/{GAMETYPE}"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        skaters = r.json().get("skaters", [])
        for s in skaters:
            s["_team"] = abbr
        return skaters
    except Exception as e:
        print(f"    ⚠️  stats {abbr}: {e}")
        return []


def fetch_roster_age_map(abbr: str) -> dict[int, int]:
    """Return {playerId: age} from roster endpoint (one call per team)."""
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
            dob = p.get("birthDate", "")
            if pid and dob:
                result[pid] = DRAFT_YEAR - int(dob[:4])
    return result


def fetch_pp_points(player_id: int) -> int:
    """Return total PP points from the player landing page seasonTotals."""
    url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        for s in r.json().get("seasonTotals", []):
            if str(s.get("season", "")) == SEASON and s.get("gameTypeId") == GAMETYPE:
                return s.get("powerPlayPoints") or 0
        return 0
    except Exception:
        return 0


def build_stats_map(skaters: list[dict], age_map: dict[int, int]) -> dict[str, dict]:
    result = {}
    for s in skaters:
        pid  = s.get("playerId")
        name = normalize(f"{s['firstName']['default']} {s['lastName']['default']}")
        result[name] = {
            "nhl_player_id": pid,
            "full_name":     f"{s['firstName']['default']} {s['lastName']['default']}",
            "team":          s.get("_team", ""),
            "pos":           POS_MAP.get(s.get("positionCode", "C"), "C"),
            "age":           age_map.get(pid),
            "last_gp":       s.get("gamesPlayed") or 0,
            "last_g":        s.get("goals") or 0,
            "last_a":        s.get("assists") or 0,
            "last_pts":      s.get("points") or 0,
            "pp_goals":      s.get("powerPlayGoals") or 0,  # available directly
        }
    return result


def compute_pp_pct(stats: dict, pp_pts: int) -> int | None:
    total = stats["last_pts"]
    return round((pp_pts / total) * 100) if total else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-pts", type=int, default=0,
                        help="Min pts to add missing players (default: 0 = all)")
    parser.add_argument("--update-only", action="store_true",
                        help="Only update existing players")
    args = parser.parse_args()

    print(f"📊  Poolers Guide Stats — {SEASON} regular season → poolers_players")
    print(f"    Mode: {'update only' if args.update_only else f'update + add all players (>= {args.min_pts} pts)'}")
    print("─" * 60)

    # 1. Load existing players
    existing_rows = supabase.table("poolers_players").select("id,name,rank").execute().data
    poolers_map = {normalize(r["name"]): r["id"] for r in existing_rows if r.get("name")}
    max_rank = max((r.get("rank") or 0 for r in existing_rows), default=0)
    print(f"  Found {len(existing_rows)} existing players\n")

    # 2. Fetch stats + age for all teams
    print("  Fetching NHL API stats + roster (age) for all 32 teams…")
    all_stats: dict[str, dict] = {}
    for abbr in NHL_TEAMS:
        skaters  = fetch_team_stats(abbr)
        age_map  = fetch_roster_age_map(abbr)
        team_map = build_stats_map(skaters, age_map)
        all_stats.update(team_map)
        print(f"    ✓ {abbr}: {len(skaters)} skaters")
        time.sleep(0.25)

    print(f"\n  Total NHL skaters loaded: {len(all_stats)}")
    print("─" * 60)

    # 3. Update existing players
    matched = 0
    unmatched = []
    print("\n  Updating existing players…")

    for norm_name, player_id in poolers_map.items():
        stats = all_stats.get(norm_name)
        if not stats:
            last = norm_name.split()[-1]
            candidates = {k: v for k, v in all_stats.items() if k.endswith(" " + last)}
            if len(candidates) == 1:
                stats = list(candidates.values())[0]

        if not stats:
            unmatched.append(norm_name)
            continue

        nhl_id = stats.get("nhl_player_id")
        pp_pts = fetch_pp_points(nhl_id) if nhl_id else 0
        time.sleep(0.08)

        pp_pct = compute_pp_pct(stats, pp_pts)
        supabase.table("poolers_players").update({
            "last_gp":  stats["last_gp"],
            "last_g":   stats["last_g"],
            "last_a":   stats["last_a"],
            "last_pts": stats["last_pts"],
            "pp_pct":   pp_pct,
        }).eq("id", player_id).execute()

        print(f"  ✅  {stats['full_name']}: {stats['last_g']}G {stats['last_a']}A {stats['last_pts']}PTS  PP%={pp_pct}")
        matched += 1

    # 4. Insert missing players
    added = 0
    if not args.update_only:
        candidates = sorted(
            [(name, s) for name, s in all_stats.items()
             if s["last_pts"] >= args.min_pts and name not in poolers_map],
            key=lambda x: x[1]["last_pts"], reverse=True
        )
        print(f"\n  Adding {len(candidates)} missing players…\n")

        # Batch insert in chunks of 50 to avoid timeouts
        CHUNK = 50
        chunk_rows = []

        for norm_name, stats in candidates:
            nhl_id = stats.get("nhl_player_id")
            pp_pts = fetch_pp_points(nhl_id) if nhl_id else 0
            time.sleep(0.08)

            pp_pct = compute_pp_pct(stats, pp_pts)
            max_rank += 1

            chunk_rows.append({
                "rank":     max_rank,
                "name":     stats["full_name"],
                "team":     stats["team"],
                "pos":      stats["pos"],
                "age":      stats.get("age"),
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
            })
            print(f"  ➕  {stats['full_name']} ({stats['team']}) {stats['last_pts']}PTS  PP%={pp_pct}")
            added += 1

            # Flush chunk
            if len(chunk_rows) >= CHUNK:
                supabase.table("poolers_players").insert(chunk_rows).execute()
                print(f"      → Inserted batch of {len(chunk_rows)}")
                chunk_rows = []

        # Final chunk
        if chunk_rows:
            supabase.table("poolers_players").insert(chunk_rows).execute()
            print(f"      → Inserted batch of {len(chunk_rows)}")

    print("\n" + "─" * 60)
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
