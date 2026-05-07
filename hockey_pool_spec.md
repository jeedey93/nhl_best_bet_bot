# Hockey Pool — Product Specification
**Single-Manager Pool · Auto NHL Stat Sync**
Version 2.0 · May 2026 · *Updated to reflect current implementation*

---

## 1. Overview

A hockey pool web application where one commissioner manages all teams from a single session. No authentication, no multi-user trade approvals, and no draft turn tracking are required.

**Live at:** parieurdiscipline.com (GitHub Pages + Vercel serverless functions)

### 1.1 Core Principles

- The commissioner manages all teams from a single browser session — no login required. A password gate (`parieur2026`) protects league creation.
- NHL stats are pulled automatically from the NHL public API daily at 9am Montreal time via GitHub Actions — no manual stat entry required.
- Scoring is position-based and **configurable per league** via `pool_settings`:
  - Forwards: 1 pt per point (goals + assists combined)
  - Defensemen: configurable pts per goal, configurable pts per assist
  - Goalies: configurable pts per win, configurable pts per shutout
- **Points only accumulate while a player is in an active slot.** Moving a player to bench freezes their earned total; re-activating them opens a new earning window on top of the frozen amount.
- The roster is managed via swaps (active ↔ bench), cross-team trades, and direct player adds throughout the season. A configurable swap limit per team is enforced.

### 1.2 Tech Stack

- **Frontend:** Static HTML/CSS/JS (no framework), hosted on GitHub Pages
- **Backend:** Vercel Serverless Functions (`/api/`)
- **Database:** Supabase (PostgreSQL) — roster data stored as JSONB in `pool_rosters`
- **NHL data source:** NHL public API at `https://api-web.nhle.com`
- **Stat sync:** Python script (`scripts/scrape_nhl_stats.py`) run via GitHub Actions daily

---

## 2. Pages & Features

### 2.1 `/pool` — Home / League Hub

Entry point. The commissioner creates leagues and navigates to existing ones.

| Feature | Status | Notes |
|---|---|---|
| Create a league with a name | ✅ Done | Optional name (max 32 chars), defaults to "League". Password-gated. |
| Auto-generate unique 4-char league code | ✅ Done | Chars A–Z, 2–9 (no 0, 1, I, O to avoid confusion) |
| View list of existing leagues | ✅ Done | Recent leagues stored in localStorage, displayed with links to draft/standings/roster/trades |
| Delete a league | ✅ Done | Cascades to pool_rosters, pool_settings, pool_locks |
| Multi-user invite / authentication | Not needed | Single-manager pool |
| Set number of teams or roster size at creation | Not needed | Roster structure is fixed: 12F / 6D / 2G / 6B |

### 2.2 `/pool/join` — Draft / Roster Builder

The commissioner assigns all players to all teams. All teams are managed in one view.

| Feature | Status | Notes |
|---|---|---|
| Create and name multiple teams | ✅ Done | Teams added via switcher bar; reorderable |
| Add players to roster slots by position | ✅ Done | Drag-and-drop or click-to-add from player pool |
| Player pool sourced from Supabase `nhl_players` | ✅ Done | Sorted by cap hit desc, limit 1000, cached 5 min |
| Filter players by position, NHL team, name search | ✅ Done | Strip + search bar above player table |
| Sort players by score, salary, goals, assists, wins, shutouts, save%, GP | ✅ Done | Column headers clickable |
| Show player stats when selecting | ✅ Done | G/A/PTS or W/SO, cap hit, efficiency score, injury badge |
| Salary cap enforcement ($95.5M per team) | ✅ Done | Cap bar shows remaining; blocks add if would exceed |
| Fixed roster structure: 12F / 6D / 2G / 6 Bench | ✅ Done | Bench players do not count toward cap |
| Bench players excluded from cap | ✅ Done | Only active (F/D/G) slots count toward cap |
| ⚡ Ultimate Team auto-fill | ✅ Done | Locks existing picks, fills empty slots with best-scoring players that fit the cap. Deterministic greedy pass + 200 randomised attempts for variety. Preview modal before applying. |
| Clear team | ✅ Done | Removes all players from active + bench |
| Undo last action | ✅ Done | Snapshot-based undo |
| Drag-and-drop reorder within roster | ✅ Done | |
| Lock draft once rosters full | Not implemented | No `draft_locked` mechanism |
| Enforce configurable roster size limits | Not implemented | Slot counts are hardcoded |

#### 2.2.1 Roster Structure

| Group | Slots | Cap counted? |
|---|---|---|
| Forwards (F) | 12 | Yes |
| Defence (D) | 6 | Yes |
| Goalies (G) | 2 | Yes |
| Bench (B) | 6 | No |
| **Total** | **26** | |

### 2.3 `/pool/standings` — Standings Page

Live pool leaderboard. Stats fetched from Supabase `nhl_players` table (updated daily by GitHub Actions).

| Feature | Status | Notes |
|---|---|---|
| Standings ranked by total pool points | ✅ Done | |
| Per-team point breakdown with top player | ✅ Done | Expandable rows |
| Top individual scorers by position (Pool Leaders tab) | ✅ Done | F / D / G sections |
| Efficiency metric (pts per $1M cap) | ✅ Done | Shown as "Eff." column |
| Pt/GP column (points per game since acquisition) | ✅ Done | Hidden on mobile |
| Gap column (points behind leader) | ✅ Done | |
| Manual sync button | ✅ Done | POST `/api/sync-pool-stats` → triggers GitHub Actions workflow |
| Last-synced timestamp displayed | Not implemented | Sync status only shows transient "✅ Stats updated!" message |
| Rank movement indicators (↑↓ vs previous sync) | Not implemented | No standings snapshots stored |
| Filter by week or custom date range | Not implemented | Full season only |

#### 2.3.1 Standings Table Columns

| Column | Description |
|---|---|
| Rank | 👑 / medal for top 3, number for rest |
| Team name | Pool team name |
| Pt/GP* | Points per game played since acquisition |
| Eff. | Pool pts per $1M cap (efficiency) |
| Pts | Total accumulated pool points |
| Gap | Points behind the leader |

### 2.4 `/pool/roster` — Roster Management

The commissioner manages all team rosters — swaps, cross-team trades, adds, and drops.

| Feature | Status | Notes |
|---|---|---|
| View full roster per team | ✅ Done | Active (F/D/G) and Bench sections |
| Swap active ↔ bench (single swap) | ✅ Done | Via "⚡ Swap" button, opens bench selection modal |
| Bulk Swap Mode | ✅ Done | Select one active + one bench player of same position, execute together |
| Undo swap (30-second window) | ✅ Done | Restores both players' acquisition states including frozen_points |
| Trade players between two pool teams | ✅ Done | Cross-team trade via `execute_pool_trade` RPC |
| Swap limit per team | ✅ Done | Configurable via `pool_settings.max_trades_per_team` (default 5); shown as pips |
| View free agents (undrafted players) | ✅ Done | "Free Agents" tab shows all players not on any roster, with stats |
| Injury / scratch badges | ✅ Done | DTD (day-to-day), IR, NRP, Active sourced from `injury_status` field |
| Performance signal (▲▼=) per player | ✅ Done | Compares pts/GP since acquisition vs career rate |
| Trade history per team | ✅ Done | Logged in `player_trades`, shown in roster page |
| Add player from free agent pool (from roster page) | Not implemented | Must use join.html (draft builder) to add players |
| Drop player back to free agent pool | Not implemented | Moving to bench is not the same as releasing |
| League feed view | ✅ Done | Aggregated trade activity across all teams |
| Trade proposals (multi-team) | ✅ Done | Separate `trade-proposal.html` |

#### 2.4.1 Active vs Bench — How Swaps Work

Every roster slot is either **Active** (F/D/G groups) or **Bench** (B group).

- Only active players accumulate pool points.
- When a player is moved to bench, their earned points are **frozen** at that moment into `acquisitions[slug].frozen_points`.
- When re-activated, a fresh stats snapshot is stored as the new earning baseline. Points earned in the new window are added on top of frozen_points.
- Formula: `pool_points = frozen_points + score_delta(current_stats − activation_snapshot)`
- This is computed client-side in `poolScoreOwned()` using data stored in `pool_rosters.data.teams[].acquisitions`.

---

## 3. Stat Sync Engine

### 3.1 NHL API Endpoints Used

| Endpoint | Purpose |
|---|---|
| `https://api-web.nhle.com/v1/club-stats/{team}/{season}/{gametype}` | Season stats per team (G, A, PTS, W, SO, GP, SV%) |
| `https://api-web.nhle.com/v1/roster/{team}/{season}` | Injury status per player |
| `https://api-web.nhle.com/v1/player/{id}/game-log/{season}/2` | Per-game log for last-5 trend visualization |

### 3.2 Sync Schedule

| Trigger | Schedule | Notes |
|---|---|---|
| Automatic (GitHub Actions) | Daily at 13:00 UTC (9am Montreal) | `update_pool_stats.yml` |
| Manual | POST `/api/sync-pool-stats` | Triggers workflow dispatch via GitHub API; also runs Python script directly in local dev |

### 3.3 Pool Points Calculation

Points are calculated **per active window**, not from raw cumulative season totals.

**Algorithm for each currently-active player:**
1. Look up `acquisitions[slug]` for this player on this team.
2. If no entry (original draft pick): baseline is zero — full season stats count.
3. If entry exists: `stats_snapshot` is the baseline at the start of the current active window.
4. `frozen_points` holds the sum of all previously completed active windows.
5. Compute delta: `current_stats − stats_snapshot` for goals/assists/points/wins/shutouts.
6. Apply position weights (see §3.4).
7. `total = frozen_points + score(delta)`

**On bench event:** `frozen_points += score(current_stats − stats_snapshot)`. New bench snapshot stored.

**On re-activate event:** `stats_snapshot` reset to current stats. `frozen_points` preserved. New window begins at zero delta.

**Data stored in `pool_rosters.data.teams[].acquisitions[slug]`:**
```json
{
  "date": "ISO timestamp — when first acquired",
  "stats_snapshot": { "points": 0, "goals": 0, "assists": 0, "wins": 0, "shutouts": 0, "games_played": 0 },
  "frozen_points": 0
}
```

### 3.4 Scoring Weights

Weights are stored per league in `pool_settings` and configurable. Defaults:

| Position | Stat | Default |
|---|---|---|
| Forward (C/LW/RW) | Points (G+A combined) | 1 pt each |
| Defence | Goals | 1 pt |
| Defence | Assists | 1 pt |
| Goalie | Wins | 2 pts |
| Goalie | Shutouts | 3 pts |

All other stats (GAA, SV%, +/-, etc.) are worth 0 pts.

### 3.5 Edge Cases

| Scenario | Handling |
|---|---|
| Player injured / scratched | Injury badge shown on roster; stats still accumulate from games played |
| Player traded to another NHL team | Pool assignment unchanged; stats follow player via `puckpedia_slug` |
| NHL API unreachable | `continue-on-error: true` in workflow; existing Supabase data preserved |
| Concurrent edits | `pool_locks` table with heartbeat prevents two sessions editing the same league simultaneously |

---

## 4. Data Model

All roster data is stored in Supabase. The primary roster structure uses JSONB for flexibility.

### `pool_leagues`
| Column | Type | Notes |
|---|---|---|
| code | VARCHAR(4) | Primary key, auto-generated |
| name | VARCHAR(32) | League name |
| created_at | TIMESTAMP | |

### `pool_settings`
| Column | Type | Notes |
|---|---|---|
| league_code | VARCHAR(4) | FK → pool_leagues |
| f_points | DECIMAL | Forward points weight (default 1) |
| d_goals | DECIMAL | Defence goals weight (default 1) |
| d_assists | DECIMAL | Defence assists weight (default 1) |
| g_wins | DECIMAL | Goalie wins weight (default 2) |
| g_shutouts | DECIMAL | Goalie shutouts weight (default 3) |
| max_trades_per_team | INTEGER | Swap limit per team (default 5) |

### `pool_rosters`
| Column | Type | Notes |
|---|---|---|
| league_code | VARCHAR(4) | FK → pool_leagues |
| data | JSONB | Full roster blob — see §3.3 for acquisitions structure |

**JSONB structure:**
```json
{
  "teams": [
    {
      "id": "uuid",
      "name": "Team Name",
      "acquisitions": { "<slug>": { "date": "...", "stats_snapshot": {}, "frozen_points": 0 } },
      "roster": {
        "F": ["slug", null, ...],
        "D": ["slug", null, ...],
        "G": ["slug", null],
        "B": ["slug", null, ...]
      }
    }
  ]
}
```

### `pool_locks`
| Column | Type | Notes |
|---|---|---|
| league_code | VARCHAR(4) | FK → pool_leagues |
| session_id | VARCHAR | Browser session UUID |
| heartbeat_at | TIMESTAMP | Updated periodically; stale locks auto-expire |

### `player_trades`
| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| league_code | VARCHAR(4) | FK → pool_leagues |
| team_id | VARCHAR | Team UUID |
| team_name | VARCHAR | |
| player_from_slug | VARCHAR | Outgoing player (null for straight adds) |
| player_to_slug | VARCHAR | Incoming player |
| player_from/to_name | VARCHAR | Cached for display |
| player_from/to_position | VARCHAR | |
| from/to_slot_group | VARCHAR | F / D / G / B |
| date_from_acquired | TIMESTAMP | When player joined team |
| date_traded | TIMESTAMP | When moved out (null if still owned) |
| points_accumulated_at_trade | DECIMAL | Points at time of swap (historical record) |
| swap_note | VARCHAR | Optional commissioner comment |

### `nhl_players`
| Column | Type | Notes |
|---|---|---|
| puckpedia_slug | VARCHAR | Primary key |
| nhl_player_id | INTEGER | NHL API player ID |
| player_name | VARCHAR | |
| position | VARCHAR | C / LW / RW / D / G |
| team | VARCHAR | NHL team abbreviation |
| cap_hit | INTEGER | Salary in dollars |
| goals | INTEGER | Season total |
| assists | INTEGER | Season total |
| points | INTEGER | Season total (goals + assists) |
| wins | INTEGER | Goalies only |
| shutouts | INTEGER | Goalies only |
| games_played | INTEGER | |
| save_pct | DECIMAL | Goalies only |
| injury_status | VARCHAR | Active / DTD / IR / NRP |
| last5_game_pts | JSONB | Array of per-game point totals for trend display |

---

## 5. Open Items

These features are in the spec but not yet implemented:

| # | Feature | Impact |
|---|---|---|
| 1 | Add player from free agent pool directly on roster page | Commissioner must use draft builder instead |
| 2 | Drop player back to free agent pool | No explicit release mechanic — bench ≠ free agent |
| 3 | Last-synced timestamp displayed on standings | No data freshness indicator |
| 4 | Rank movement indicators (↑↓ vs previous sync) | Requires standings snapshots to be stored |
| 5 | Filter standings by week / date range | Full season view only |
| 6 | Draft lock once rosters are full | No `draft_locked` enforcement |
| 7 | Game-day 11:59pm sync | Current: once daily at 9am only |
| 8 | sync_log table | Errors logged to GitHub Actions only, not Supabase |
