#!/usr/bin/env python3
"""Scrape NHL player roster + contract data from PuckPedia → Supabase.

All data is extracted from the team page in a single request per team.
No individual player page visits needed.
"""

import argparse
import re
import sys
import time
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌  Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
    sys.exit(1)

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

NHL_TEAMS = [
    "anaheim-ducks", "boston-bruins", "buffalo-sabres",
    "calgary-flames", "carolina-hurricanes", "chicago-blackhawks",
    "colorado-avalanche", "columbus-blue-jackets", "dallas-stars",
    "detroit-red-wings", "edmonton-oilers", "florida-panthers",
    "los-angeles-kings", "minnesota-wild", "montreal-canadiens",
    "nashville-predators", "new-jersey-devils", "new-york-islanders",
    "new-york-rangers", "ottawa-senators", "philadelphia-flyers",
    "pittsburgh-penguins", "san-jose-sharks", "seattle-kraken",
    "st-louis-blues", "tampa-bay-lightning", "toronto-maple-leafs",
    "utah-hockey-club", "vancouver-canucks", "vegas-golden-knights",
    "washington-capitals", "winnipeg-jets",
]

BASE_URL   = "https://puckpedia.com"
DELAY_S    = 1.5
BATCH_SIZE = 50

# Only scrape active roster sections — skip everything after these
ACTIVE_SECTION_IDS = {"capby_forwards", "capby_defence", "capby_goaltenders"}


def parse_money(text: str | None) -> int | None:
    if not text:
        return None
    cleaned = re.sub(r"[$,\s]", "", text)
    try:
        return int(cleaned)
    except ValueError:
        return None


def fetch(pw_page, url: str) -> BeautifulSoup | None:
    try:
        pw_page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        pw_page.wait_for_selector("table.pp_table-roster", state="attached", timeout=15_000)
        html = pw_page.content()
        return BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(f"    ⚠️  Failed to load {url}: {e}")
        return None


def scrape_team(pw_page, team_slug: str) -> list[dict]:
    url = f"{BASE_URL}/team/{team_slug}"
    print(f"  📋  {team_slug}")
    soup = fetch(pw_page, url)
    if not soup:
        return []

    players = []

    for section_id in ACTIVE_SECTION_IDS:
        section_div = soup.find("div", id=section_id)
        if not section_div:
            continue

        # The roster table follows the section div (may be wrapped in a sibling div)
        table = None
        for sibling in section_div.find_next_siblings():
            table = sibling.find("table", class_="pp_table-roster") or (
                sibling if sibling.name == "table" and "pp_table-roster" in sibling.get("class", []) else None
            )
            if table:
                break

        if not table:
            continue

        for row in table.select("tr[role='row']"):
            first_td = row.find("td")
            if not first_td:
                continue

            # Player name + slug
            a = first_td.find("a", class_="pp_link")
            if not a:
                continue
            player_name = a.get_text(strip=True)
            puckpedia_slug = a.get("href", "")

            # Age and position from the sub-row spans
            age = None
            position = None
            for label_span in first_td.select("span.opacity-60"):
                label = label_span.get_text(strip=True).lower()
                value_span = label_span.find_next_sibling("span")
                if not value_span:
                    continue
                value = value_span.get_text(strip=True)
                if label == "age":
                    try:
                        age = int(value)
                    except ValueError:
                        pass
                elif label == "pos":
                    position = value.upper()

            # Cap hit columns: <td data-js="capcol">
            cap_tds = row.find_all("td", attrs={"data-js": "capcol"})

            # Current season cap hit = first capcol td with a non-zero value
            cap_hit = None
            aav = None
            base_salary = None
            signing_bonus = None
            expiry_year = None
            expiry_status = None

            for td in cap_tds:
                ch_raw = td.get("data-extract_ch", "").replace(",", "").strip()
                if ch_raw and ch_raw != "0":
                    if cap_hit is None:
                        cap_hit      = parse_money(td.get("data-ch"))
                        aav          = parse_money(td.get("data-aav"))
                        base_salary  = parse_money(td.get("data-sal"))
                        signing_bonus = parse_money(td.get("data-sb"))

                # Expiry status (UFA/RFA) and year appear in the last meaningful column
                ufa = td.find("span", class_="pp-ufa")
                rfa = td.find("span", class_="pp-rfa")
                if ufa or rfa:
                    expiry_status = "UFA" if ufa else "RFA"
                    year_div = td.find("div", class_=re.compile(r"text-right"))
                    if year_div:
                        expiry_year = year_div.get_text(strip=True)

            now = datetime.now(timezone.utc).isoformat()

            players.append({
                "puckpedia_slug": puckpedia_slug,
                "player_name":    player_name,
                "position":       position,
                "age":            age,
                "team":           team_slug,
                "cap_hit":        cap_hit,
                "aav":            aav,
                "total_value":    None,
                "contract_year":  None,
                "contract_years": None,
                "base_salary":    base_salary,
                "signing_bonus":  signing_bonus,
                "expiry_year":    expiry_year,
                "expiry_status":  expiry_status,
                "scraped_at":     now,
                "updated_at":     now,
            })

    return players


def upsert_batch(rows: list[dict]) -> None:
    result = supabase.table("nhl_players").upsert(rows, on_conflict="puckpedia_slug").execute()
    if hasattr(result, "error") and result.error:
        print(f"  ❌  Supabase upsert error: {result.error}")
    else:
        print(f"  ✅  Upserted {len(rows)} rows")


def main():
    parser = argparse.ArgumentParser(description="Scrape PuckPedia roster data into Supabase")
    parser.add_argument("--team", help="Single team slug to test (e.g. anaheim-ducks)")
    args = parser.parse_args()

    print("🏒  NHL Salary Scraper — PuckPedia → Supabase")
    print("─" * 50)

    teams = [args.team] if args.team else NHL_TEAMS
    if args.team:
        print(f"\n🔍  Single-team mode: {args.team}")

    batch: list[dict] = []
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pw_page = browser.new_page()
        pw_page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        })

        for team in teams:
            players = scrape_team(pw_page, team)
            print(f"    → {len(players)} players found")

            for p_data in players:
                cap = f"${p_data['cap_hit']:,}" if p_data["cap_hit"] else "?"
                print(f"      {p_data['player_name']} ({p_data['position']}, age {p_data['age']}) — cap: {cap}")

            batch.extend(players)

            if len(batch) >= BATCH_SIZE:
                upsert_batch(batch)
                total += len(batch)
                batch = []

            time.sleep(DELAY_S)

        browser.close()

    if batch:
        upsert_batch(batch)
        total += len(batch)

    print("\n" + "─" * 50)
    print(f"🎉  Done! {total} players saved to Supabase.")


if __name__ == "__main__":
    main()
