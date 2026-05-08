# Plan: NHL 2026-27 Pool Pages

## Context

Create two new pages for the 2026-27 NHL season pool:
1. `docs/pool-2027.html` — individual salary-cap draft page (no league code, one submission per person)
2. `docs/pool-2027-standings.html` — standings page showing all submitted teams

Unlike the existing `/pool` system (league-based, multiple teams per league, real-time locking), this is a simple one-person-one-submission model: anyone visits the page, drafts their team against the salary cap, enters name + email, and submits. Picks go to a new Supabase table `pool_2027_submissions`.

**Scoring rules:**
- Forwards: 1pt per goal, 1pt per assist (= 1pt per point)
- Defensemen: 2pts per goal, 1pt per assist
- Goalies: 2pts per win, 3pts per shutout

**Player data:** existing `nhl_players` Supabase table (2025-26 stats)

---

## Supabase Table to Create

Run this SQL in the Supabase dashboard before deploying:

```sql
CREATE TABLE pool_2027_submissions (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name         text NOT NULL,
  email        text NOT NULL,
  paid         boolean DEFAULT false,
  roster       jsonb NOT NULL,   -- { F: [...slugs], D: [...slugs], G: [...slugs] }
  cap_used     bigint,           -- total cap hit in dollars
  submitted_at timestamptz DEFAULT now()
);

-- Allow anon access (for the frontend)
ALTER TABLE pool_2027_submissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public read"   ON pool_2027_submissions FOR SELECT USING (true);
CREATE POLICY "public insert" ON pool_2027_submissions FOR INSERT WITH CHECK (true);
CREATE POLICY "public update" ON pool_2027_submissions FOR UPDATE USING (true);
```

---

## File 1: `docs/pool-2027.html` (Draft Page)

Adapts `docs/pool/join.html` with these key differences:

**Removed:**
- Password gate (`#pw-gate` block)
- League code / URL param logic
- Team switcher (multi-team)
- Edit bar / lock / heartbeat system
- Compare drawer
- Swap mode (simplify to direct add)
- Overview grid / live draft / trade references
- Bench slots — roster is 12F / 6D / 2G only
- `saveToSupabase()` / `loadFromSupabase()` — replaced with `submitRoster()`

**Added:**
- Submit button in the cap bar area (enabled only when roster is complete + under cap)
- Submit modal: name input, email input, paid/free toggle
- `submitRoster()` — validates, POSTs to `pool_2027_submissions`, shows success
- `checkExistingSubmission(email)` — checks for duplicate email before submit
- Duplicate guard: if email already exists, asks user to confirm overwrite (PATCH by id)
- localStorage draft persistence (auto-saves as user builds team)

**Reused from `docs/pool/join.html`:**
- All CSS variables and styles
- `SUPABASE_URL`, `SUPABASE_KEY`, `sbHeaders()`, `CAP_MAX`, `TEAM_ABBR` constants
- Player loading from `nhl_players` with same query + sessionStorage caching
- Pool table HTML + sorting + position filter + search + salary slider
- Roster slots rendering logic
- Cap bar calculation
- `toast()` function
- `renderPool()` / `debouncedRenderPool()` / `setFilter()` / `setSort()` patterns
- Team logo URL pattern

**Roster rules:** 12 Forwards / 6 Defencemen / 2 Goalies under $95.5M cap

**Nav links:** Draft (`/pool-2027.html`) · Standings (`/pool-2027-standings.html`)

**New JS functions:**

```js
async function submitRoster() {
  // validate roster completeness and cap compliance
  // open submit modal (name, email, paid/free)
  // POST to pool_2027_submissions
  // show success toast + disable submit button
}

async function checkExistingSubmission(email) {
  // GET pool_2027_submissions?email=eq.{email}&select=id
  // returns id if found, null otherwise
}
```

**Submit modal HTML:**

```html
<div id="submit-modal" class="modal-overlay hidden">
  <div class="modal-box">
    <div class="modal-title">Submit <span>Your Team</span></div>
    <input id="sub-name" class="modal-input" placeholder="Your name" />
    <input id="sub-email" class="modal-input" type="email" placeholder="Your email" />
    <!-- paid/free toggle (same as picks-2026 pool type bar) -->
    <div class="modal-btns">
      <button class="modal-btn modal-btn-cancel" onclick="closeSubmitModal()">Cancel</button>
      <button class="modal-btn modal-btn-confirm" onclick="confirmSubmit()">Submit</button>
    </div>
  </div>
</div>
```

**Submit button** (shown in cap bar area, disabled when cap exceeded or roster incomplete):

```html
<button id="btn-submit" class="btn-submit-roster" onclick="openSubmitModal()">
  Submit My Team
</button>
```

---

## File 2: `docs/pool-2027-standings.html` (Standings Page)

Adapts `docs/pool/standings.html` with these key differences:

**Removed:**
- League code requirement
- Trade / acquisition window scoring
- Live score polling

**Page sections:**
1. Header + participant count badge
2. Paid / Free pool toggle (filters by `paid` column)
3. Podium (top 3 with medals)
4. Full leaderboard table: Rank · Name · PTS · Cap Used · F pts · D pts · G pts

**Scoring logic:**
```
Forwards:   points × 1
Defencemen: goals × 2 + assists × 1
Goalies:    wins × 2 + shutouts × 3
```

**Data loading:**

```js
// 1. Load all submissions
GET pool_2027_submissions?select=id,name,paid,roster,cap_used,submitted_at

// 2. Load all players once
GET nhl_players?select=puckpedia_slug,player_name,position,cap_hit,goals,assists,points,wins,shutouts,games_played

// 3. Score each submission client-side
function scoreTeam(roster, playerMap) {
  let total = 0;
  for (const slug of (roster.F || [])) {
    const p = playerMap[slug];
    if (p) total += (p.points ?? 0) * 1;       // F: 1pt per point
  }
  for (const slug of (roster.D || [])) {
    const p = playerMap[slug];
    if (p) total += (p.goals ?? 0) * 2 + (p.assists ?? 0) * 1;  // D: g×2 + a×1
  }
  for (const slug of (roster.G || [])) {
    const p = playerMap[slug];
    if (p) total += (p.wins ?? 0) * 2 + (p.shutouts ?? 0) * 3; // G: w×2 + so×3
  }
  return total;
}
```

**Reused from `docs/pool/standings.html`:**
- All CSS variables and nav styles
- Supabase constants + `sbHeaders()`
- `formatName()` helper
- Podium rendering pattern
- Sorting + search logic

---

## Implementation Order

1. Write `docs/pool-2027.html` (draft page)
2. Write `docs/pool-2027-standings.html` (standings page)
3. Commit both files + this plan

---

## Verification Checklist

- [ ] Player table loads from Supabase `nhl_players`
- [ ] Cap bar updates in real time as players are added/removed
- [ ] Submit button disabled when cap is exceeded or roster incomplete
- [ ] Submit modal collects name + email + paid/free
- [ ] Row appears in `pool_2027_submissions` after submit
- [ ] Standings page shows correct points for each submission
- [ ] Duplicate email triggers overwrite confirmation
- [ ] Works on mobile (responsive layout)
