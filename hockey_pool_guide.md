# Hockey Pool — User Guide
*For league commissioners and participants — no technical knowledge required*

---

## What Is This?

The Hockey Pool is a custom fantasy-style hockey league built into the Parieur Discipliné website. One person (the **commissioner**) runs everything — creating the league, picking players for all teams, managing swaps and trades throughout the season, and watching the standings update automatically every day.

No app to download. No account to create. Everything lives at **parieurdiscipline.com/pool**.

---

## How It Works — The Big Picture

1. The commissioner **creates a league** and gets a 4-letter code (e.g. `MXQR`).
2. Using that code, the commissioner **builds each team's roster** by picking NHL players under a salary cap.
3. Once the season is underway, **NHL stats sync automatically every morning** — no manual entry needed.
4. The **standings update in real time** based on each player's performance since they were added to a team.
5. The commissioner can **make moves** (bench swaps, trades between teams) throughout the season.

---

## The Pages

### 🏠 Home — Pool Hub (`/pool`)

This is the starting point. From here the commissioner can:

- **Create a new league** — type in a league name (optional) and click Create. A password is required to prevent accidents.
- **Join an existing league** — enter a 4-letter code to navigate to any league.
- **See all leagues** — every league is listed with quick links to its draft page, standings, and roster manager.
- **Delete a league** — removes everything permanently (requires the password and a confirmation step).

Each league card now shows a **team count** so you can see at a glance how many teams have been drafted in a league without clicking into it.

---

### ✏️ Draft Builder (`/pool/join`)

This is where rosters are built. The commissioner fills out every team's roster before — and during — the season.

#### Roster Structure

Every team has exactly **26 player slots**:

| Group | Slots | Earns points? |
|---|---|---|
| Forwards (F) | 12 | Yes |
| Defencemen (D) | 6 | Yes |
| Goalies (G) | 2 | Yes |
| Bench (B) | 6 | No |
| **Total** | **26** | |

Bench players are on the team but **don't score points** until they're moved to an active slot.

#### The Salary Cap

Each team has a **$95.5 million salary cap**. Only the 20 active players (F/D/G) count toward the cap — bench players are free. If adding a player would push a team over the cap, the add is blocked.

The cap bar at the top of the screen shows how much cap space is left. If a team goes over, it pulses red.

#### Finding and Adding Players

The player pool on the right shows every NHL player, sorted by salary by default. You can:

- **Search by name** using the search bar
- **Filter by position** (F / D / G) using the position buttons
- **Filter by NHL team** using the team strip at the top
- **Sort by** salary, goals, assists, points, wins, shutouts, save %, or games played by clicking any column header
- **Click a player** to see their full stats, then add them to a roster slot

Players already claimed by another team show a badge so you know they're taken.

#### Managing Multiple Teams

The **team switcher** at the top lets you flip between all teams in the league. Each pill shows the team name, a fill bar, and how many of 26 slots are filled. When a team is complete, the bar turns green.

#### ⚡ Auto-Fill (Ultimate Team)

Don't want to pick every player manually? The **Ultimate Team** button automatically fills all empty slots with the best available players that fit within the remaining cap. It locks any players you've already chosen, so it only fills what's missing. A preview shows the suggested additions before anything is applied.

#### Other Tools

- **Undo** — reverses the last action
- **Clear team** — removes every player from a team and starts fresh
- **Compare** — pin up to two players side by side to compare their stats before deciding
- **Share** — copy a link to the current team's roster view

---

### 📊 Standings (`/pool/standings`)

The live leaderboard for the league. Updated every morning automatically, or instantly when the commissioner hits the **Sync** button.

#### What the Columns Mean

| Column | What it shows |
|---|---|
| Rank | Position in the league (👑 for 1st, medals for 2nd and 3rd) |
| Team | Pool team name |
| Pt/GP | Points per game played *since the player was acquired* |
| Eff. | Pool points earned per $1M of salary — measures value for money |
| Pts | Total pool points accumulated |
| Gap | How many points behind the leader |

#### Expanding a Team Row

Click any team row to expand it and see:
- Every active player, their pool points, and their position
- The team's top scorer highlighted

#### Pool Leaders Tab

Switches to a view of the **top individual performers by position** across the whole league — the best forwards, best defencemen, and best goalies regardless of which team owns them.

#### Insights

Below the standings, a quick summary shows:
- Who is in the lead
- Who has the best efficiency (most points per dollar)
- Who is closing the gap fastest on the current leader

#### Syncing Stats

Stats update automatically every morning. If you want the latest numbers mid-day, click **Sync Stats**. The last-synced time is shown at the top of the standings so you always know how fresh the data is.

---

### 🗂 Roster Manager (`/pool/roster`)

This is where the commissioner manages moves during the season — swapping players between active and bench, trading players between teams, and monitoring the health of every roster.

#### Viewing a Team

Use the team selector at the top to switch between teams. Each team shows:
- **Active players** (F, D, G) — these earn points
- **Bench players** — these don't earn points until activated

Each player row shows their NHL team logo, name, injury status, games played, goals, assists, points (or wins/shutouts for goalies), cap hit, and a **trend sparkline** showing recent performance. On mobile, the sparkline is replaced by a **▲ ▼ =** badge indicating whether the player is on a hot streak, cooling off, or holding steady.

#### How Points Work — The Key Concept

Points only count **while a player is in an active slot**. This is what makes swaps strategic:

- When you **move a player to bench**, their earned points are locked in ("frozen").
- When you **re-activate a player**, they start earning again from that moment forward — their frozen points are preserved and new points stack on top.
- This means benching a cold player and activating a hot one can change the standings.

#### Swapping Players (Active ↔ Bench)

Each team has a **swap limit** (default: 5 per team for the season). The swap counter at the top of each team's summary shows how many have been used, displayed as pips — the last one turns red as a warning.

To swap:
1. Click **⬇ Bench** on an active player to send them to the bench.
2. A modal appears to choose which bench player to activate in their place.
3. Both players must be the same position group (e.g. you can't swap a forward for a defenceman).

There's a **30-second undo window** after any swap in case you made a mistake.

**Bulk Swap Mode** lets you select one active and one bench player at the same time and execute the swap in one step, instead of navigating a modal.

#### Trading Between Teams

The roster page also supports **cross-team trades** — moving a player from one pool team to another. This counts as a swap for both teams involved.

A full **trade history** is shown for each team, including who was moved, when, and how many points they'd accumulated at the time.

#### Free Agents

The **Free Agents** tab shows every NHL player not currently on any pool roster. You can search and filter them the same way as in the draft builder.

#### Trading Block

Any player can be listed on the **Trading Block** using the 📤 List button. This signals to other managers (or the commissioner) that the team is open to moving that player.

---

## How Scoring Works

Points are calculated based on player performance **since they were added to a team's active roster**.

| Position | What earns points |
|---|---|
| Forward (C / LW / RW) | 1 pt per goal or assist |
| Defenceman | 1 pt per goal, 1 pt per assist (configurable) |
| Goalie | 2 pts per win, 3 pts per shutout (configurable) |

The commissioner can adjust these weights per league from the league settings page.

**Example:** If a forward joined your team having already scored 20 points that season, those 20 points don't count for your team — only what they score from the day you drafted them forward.

---

## What Happens Automatically

You don't need to do anything for the following — they happen on their own:

- **Stats update every morning** around 9am Montreal time via an automated process connected to the official NHL API.
- **Injury statuses** (Active / Day-to-Day / Injured Reserve / Non-Roster) update with the stats each morning.
- **Player trend data** (the sparkline graphs) update with the latest game-by-game results.

---

## Currently Implemented — Feature Summary

| Area | Feature | Available |
|---|---|---|
| League Hub | Create / delete leagues | ✅ |
| League Hub | View all leagues with team count | ✅ |
| Draft | Build rosters for multiple teams | ✅ |
| Draft | Salary cap enforcement | ✅ |
| Draft | Auto-fill (Ultimate Team) | ✅ |
| Draft | Player search, filter, sort | ✅ |
| Draft | Undo, clear team | ✅ |
| Draft | Player compare (pin two side by side) | ✅ |
| Standings | Live leaderboard with points, efficiency, gap | ✅ |
| Standings | Per-team player breakdown | ✅ |
| Standings | Pool Leaders by position | ✅ |
| Standings | Insights (leader, best efficiency, rising) | ✅ |
| Standings | Manual sync button + last-synced badge | ✅ |
| Roster | Active ↔ bench swaps with swap limit | ✅ |
| Roster | Bulk swap mode | ✅ |
| Roster | 30-second undo after swaps | ✅ |
| Roster | Cross-team trades | ✅ |
| Roster | Trade history per team | ✅ |
| Roster | Performance signal (▲ ▼ =) per player | ✅ |
| Roster | Injury badges | ✅ |
| Roster | Free agents tab | ✅ |
| Roster | Trading block listing | ✅ |
| Stats | Automatic daily sync from NHL API | ✅ |
| Stats | Active-window scoring (points only while active) | ✅ |
| Stats | Configurable scoring weights per league | ✅ |

---

## Suggested Future Features

These are improvements that would make the pool richer and easier to use:

### Quality of Life

| # | Feature | Why It Would Help |
|---|---|---|
| 1 | **Add players directly from the Roster page** | Right now you have to go back to the Draft Builder to add a free agent — it would be faster to do it from the same page where you manage swaps |
| 2 | **Drop a player back to free agents** | There's no way to fully release a player from a team — moving to bench is the closest option, but the player still occupies a bench slot |
| 3 | **Draft lock once all rosters are full** | Prevent accidental changes to rosters after the draft is complete |
| 4 | **Lock individual players** | Let the commissioner mark a player as untouchable so they can't be accidentally moved or traded |

### Standings & Analytics

| # | Feature | Why It Would Help |
|---|---|---|
| 5 | **Rank movement arrows (↑ ↓)** | Show whether each team moved up or down since the last sync — makes the standings more dynamic |
| 6 | **Week-by-week view** | Filter standings to see who performed best in a specific week, not just the full season |
| 7 | **Team scoring timeline chart** | A line graph showing how each team's point total has grown over the season |
| 8 | **Best and worst move of the week** | Auto-highlight the swap or trade that gained or cost the most points that week |
| 9 | **Projected final standings** | Based on current pace, estimate where each team will finish at season end |

### Roster Management

| # | Feature | Why It Would Help |
|---|---|---|
| 10 | **Waiver wire system** | An order of priority for claiming free agents, so the team in last place gets first pick |
| 11 | **Trade proposals between managers** | Let participants suggest trades to each other instead of the commissioner deciding everything |
| 12 | **Evening stats sync** | A second automatic update late at night to catch all games that finished that day (current sync is once per morning) |
| 13 | **Playoff-specific roster rules** | Optionally switch to a smaller active roster or different scoring rules for the playoffs |

### Commissioner Tools

| # | Feature | Why It Would Help |
|---|---|---|
| 14 | **League settings page improvements** | Currently max swaps and scoring weights are configurable — could add roster size options or custom tiebreaker rules |
| 15 | **Sync error log** | If the nightly stat sync fails, show a visible alert on the standings page instead of it going unnoticed |
| 16 | **Commissioner notes per team** | A small text field to leave notes on a team (e.g. "waiting on trade approval") visible only when managing |
| 17 | **Export standings to image or PDF** | Useful for sharing weekly results in a group chat |
