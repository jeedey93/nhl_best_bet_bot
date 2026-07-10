#!/usr/bin/env python3
"""Copy AAV from nhl_players into poolers_players, matched by normalized player name.

nhl_players.aav is in dollars → converted to $M for poolers_players.
Uses a manual override map for nickname/transliteration mismatches, plus
a last-name fallback for unique matches.
"""
import re, sys, unicodedata
from dotenv import load_dotenv
import os

load_dotenv()
from supabase import create_client
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# poolers_players name (normalized) → nhl_players name (normalized)
OVERRIDES = {
    "tommy novak":        "thomas novak",
    "matt savoie":        "matthew savoie",
    "egor chinakhov":     "yegor chinakhov",
    "ben kindel":         "benjamin kindel",
    "josh norris":        "joshua norris",
    "zachary bolduc":     "zack bolduc",
    "artem zub":          "artyom zub",
    "j.j. moser":         "janis jerome moser",
    "cam york":           "cameron york",
    "maksim shabanov":    "maxim shabanov",
    "fedor svechkov":     "fyodor svechkov",
    "jake middleton":     "jacob middleton",
    "will borgen":        "william borgen",
    "nick perbix":        "nicklaus perbix",
    "alexey toropchenko": "alexei toropchenko",
    "max crozier":        "maxwell crozier",
    "joe veleno":         "joseph veleno",
}


def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_str).strip().lower()


print("Loading nhl_players…")
src_rows = sb.table("nhl_players").select("player_name,aav").execute().data
src_map = {}
for r in src_rows:
    raw = r.get("player_name", "")
    aav = r.get("aav")
    if not raw or not aav:
        continue
    if "," in raw:
        last, first = raw.split(",", 1)
        full = f"{first.strip()} {last.strip()}"
    else:
        full = raw
    src_map[normalize(full)] = round(aav / 1_000_000, 2)
print(f"  {len(src_map)} players with AAV in source\n")

print("Updating poolers_players…")
dest = sb.table("poolers_players").select("id,name,aav").execute().data
updated = missing = 0

for p in dest:
    key = normalize(p["name"])
    # 1. Direct match
    aav_m = src_map.get(key)
    # 2. Override map
    if not aav_m:
        aav_m = src_map.get(OVERRIDES.get(key, ""))
    # 3. Last-name fallback (only if unique)
    if not aav_m:
        last = key.split()[-1]
        candidates = [(k, v) for k, v in src_map.items() if k.split()[-1] == last]
        if len(candidates) == 1:
            aav_m = candidates[0][1]

    if aav_m:
        sb.table("poolers_players").update({"aav": aav_m}).eq("id", p["id"]).execute()
        updated += 1
    else:
        missing += 1

print(f"\n🎉  Done! {updated} updated, {missing} not found in nhl_players.")
print("     Run scrape_nhl_players.py then re-run this script to fill more.")
