# Hockey Pool Trade System - Implementation Guide

## Overview

The Trade & Hold System allows players to:
1. **Hold players** with acquisition dates to track when they joined the team
2. **Accumulate points** on held players while they remain in possession
3. **Execute trades** between main roster and bench
4. **Save accumulated points** on traded-out players for historical tracking
5. **View trade history** with full transaction details

## Architecture

### Data Model

#### `player_holds` Table
Tracks active player acquisitions:
- `id` - UUID primary key
- `league_code` - League identifier
- `team_id` - Stable team identifier from `pool_rosters.data.teams[].id`
- `team_name` - Current team name
- `team_name_snapshot` - Team name saved for history/safety
- `player_slug` - PuckPedia player slug (puckpedia_slug)
- `date_acquired` - When player was acquired
- `points_accumulated` - Points accumulated while held (updated manually or via cron)

**Unique Constraint**: One hold per player per `(league_code, team_name)` for backwards compatibility. `team_id` is now also stored for safer matching.

#### `player_trades` Table
Historical record of all trades:
- `id` - UUID primary key
- `league_code` - League identifier
- `team_id` - Stable team identifier
- `team_name` / `team_name_snapshot` - Team names for display/history
- `player_from_slug` - Player being traded out
- `player_to_slug` - Player being traded in
- `player_from_name`, `player_to_name` - Snapshot names stored at trade time
- `player_from_position`, `player_to_position` - Position snapshots
- `player_from_team`, `player_to_team` - NHL team snapshots
- `from_slot_group`, `from_slot_index` - Active roster slot that was vacated
- `to_slot_group`, `to_slot_index` - Bench slot that was activated
- `date_from_acquired` - When the "from" player was originally acquired
- `date_traded` - When the trade occurred
- `points_accumulated_at_trade` - Points saved from the "from" player

#### `execute_pool_trade()` RPC
Supabase SQL function that performs the trade atomically:
- validates outgoing player is on active roster
- validates incoming player is on bench
- validates position match (`F/D/G`)
- validates post-trade cap stays within `$95.5M`
- swaps the roster inside `pool_rosters`
- writes `player_trades`
- rolls hold from old player to new player

### File Structure

```
docs/pool/
├── trades.html              # Main trades/holds management page
│   ├── Active Roster section
│   ├── Team Bench section
│   ├── Trade History section
│   └── Team roster selector
├── join.html                # Updated with Trades nav link
├── standings.html           # Updated with Trades nav link
├── TRADES_SCHEMA.sql        # SQL migration for Supabase
└── TRADES_README.md         # This file
```

### Pages Integration

- **Draft Page** (`join.html`) - Added "Trades" nav link
- **Standings Page** (`standings.html`) - Added "Trades" nav link
- **Trades Page** (`trades.html`) - New dedicated page for:
  - Viewing current player holds per team
  - Executing trades (bench to main roster)
  - Viewing complete trade history

## Setup Instructions

### 1. Create Supabase Tables

Execute the SQL from `TRADES_SCHEMA.sql` in your Supabase SQL editor:

```sql
-- Copy entire contents of TRADES_SCHEMA.sql
-- Paste into Supabase → SQL Editor → Run
```

This creates / updates:
- `player_holds` table with indexes
- `player_trades` table with indexes
- `execute_pool_trade()` RPC function

If you previously created the trade tables, **run the updated SQL again** so the new columns and RPC are added.

### 2. Configure Access Policies (Optional)

If using RLS (Row Level Security), add policies:

```sql
-- Allow league members to view their own trades/holds
CREATE POLICY "Users can view their team's holds"
  ON player_holds
  FOR SELECT
  USING (true);  -- Or add auth-based check

CREATE POLICY "Users can view their team's trades"
  ON player_trades
  FOR SELECT
  USING (true);
```

### 3. Verify Files Are Deployed

Ensure these files are in `/docs/pool/`:
- ✅ `trades.html` - Main trades page
- ✅ `join.html` - Updated with nav link
- ✅ `standings.html` - Updated with nav link

## Usage Workflow

### Holds on Active Roster

**All main roster players (Forwards, Defensemen, Goalies) are treated as the active roster on the page.**

- The page will attempt to initialize missing hold rows for active players
- Bench players are excluded from holds
- Points accumulate only for held active-roster players
- If a hold cannot be initialized, the player still renders on the page and a warning is shown

**Manual holds can also be added via direct Supabase insert:**
```json
{
  "league_code": "DEMO01",
  "team_id": "team-1",
  "team_name": "Team 1",
  "team_name_snapshot": "Team 1",
  "player_slug": "connor-mcdavid",
  "date_acquired": "2026-04-27T00:00:00Z",
  "points_accumulated": 0
}
```

### Trading Between Roster and Bench

1. Go to Trades page → Select team
2. View Active Roster
3. Click "🔄 Trade" on a held player
4. Select an **eligible** bench player to trade in (same `F/D/G` slot type only)
5. Confirm trade
6. System automatically:
   - Swaps players between active roster slot and bench slot
   - Persists updated roster composition to `pool_rosters` (visible in Draft/Standings)
   - Shows current cap / cap-after preview before confirmation
   - Validates salary cap before confirming swap (bench excluded from cap)
   - Saves accumulated points to trade history
   - Creates new hold on player-to (bench player)
   - Clears old hold record

### Viewing Trade History

Trade History section shows all past trades with:
- From player name & acquisition date
- Trade execution date
- To player name
- Points accumulated and saved

## Data Flow

### On Trade Execution

```
1. Lock the league roster row
2. Validate active slot, bench slot, position match, and salary cap
3. Swap roster slots inside `pool_rosters`
4. Insert snapshot-rich `player_trades` history row
5. Delete old hold for player-from
6. Create new hold for player-to with `date_acquired = now`
```

### Updating Accumulated Points (Manual or Automated)

Points in holds are typically updated:
- **Manually**: Team admins periodically update `points_accumulated` in Supabase
- **Automated**: Daily cron job that:
  1. Gets all active holds
  2. Calculates player's current total points
  3. Updates `points_accumulated` in hold record

Example cron update query:
```sql
UPDATE player_holds
SET points_accumulated = (
  SELECT (p.points * s.f_points) + ...
  FROM nhl_players p
  JOIN pool_settings s ON s.league_code = player_holds.league_code
  WHERE p.puckpedia_slug = player_holds.player_slug
)
WHERE date_acquired < NOW();
```

## Frontend Implementation Details

### JavaScript Functions

**`load()`** - Initial load
- Loads players from cache or API
- Loads team rosters
- Loads holds and trades from Supabase

**`loadHolds()`** - Fetch active holds
```javascript
const res = await fetch(
  `${SUPABASE_URL}/rest/v1/player_holds?league_code=eq.${_leagueCode}`
);
currentHolds = await res.json();
```

**`loadTrades()`** - Fetch trade history
```javascript
const res = await fetch(
  `${SUPABASE_URL}/rest/v1/player_trades?league_code=eq.${_leagueCode}`
);
currentTrades = await res.json();
```

**`openTradeModal(playerSlug)`** - Show trade UI
- Displays player being traded from
- Lists only eligible bench players for that slot type
- Previews cap before/after trade

**`confirmTrade()`** - Execute trade transaction
- Uses `execute_pool_trade()` RPC when available for atomic updates
- Falls back to a best-effort rollback flow if RPC has not been deployed yet

### UI Components

**Active Roster Card**
```html
<div class="hold-card">
  <div class="hold-player">
    <img class="player-logo">
    <div class="hold-info">
      <div class="hold-name">Player Name</div>
      <div class="hold-since">Acquired: Date</div>
    </div>
  </div>
  <div class="hold-stats">
    <div class="hold-stat">
      <div class="hold-stat-label">Days Held</div>
      <div class="hold-stat-value">42</div>
    </div>
    <div class="hold-stat">
      <div class="hold-stat-label">Accumul. Points</div>
      <div class="hold-stat-value">15</div>
    </div>
  </div>
  <div class="hold-actions">
    <button onclick="openTradeModal(...)">🔄 Trade</button>
  </div>
</div>
```

**Trade History Row**
```html
<div class="trade-row">
  <div class="player-info">/* From Player */</div>
  <div class="date-box">Date Traded</div>
  <div class="player-info">/* To Player */</div>
  <div class="points-unit">Points Saved</div>
</div>
```

## API Endpoints Used

All endpoints are read/write to Supabase REST API:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/rest/v1/player_holds` | GET | List holds |
| `/rest/v1/player_holds` | POST | Create hold |
| `/rest/v1/player_trades` | GET | List trades |
| `/rest/v1/player_trades` | POST | Record trade |
| `/rest/v1/rpc/execute_pool_trade` | POST | Atomic roster swap + hold rollover |

## Future Enhancements

### Automated Point Accumulation

Create a daily GitHub Action to update `points_accumulated`:

```yaml
name: Update Player Hold Points
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
jobs:
  update-holds:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Update Hold Points
        run: python scripts/update_hold_points.py
```

Python script:
```python
from data.odds import get_nhl_odds
import supabase

client = supabase.create_client(url, key)

# Get all active holds
holds = client.table('player_holds').select('*').execute().data

for hold in holds:
    # Get player's current stats
    player = get_player_stats(hold['player_slug'])
    
    # Calculate points based on scoring settings
    points = calculate_pool_score(player, scoring)
    
    # Update hold
    client.table('player_holds')\
        .update({'points_accumulated': points})\
        .eq('id', hold['id'])\
        .execute()
```

### Future Enhancements

- Replace active-roster hold auto-init with a dedicated roster-finalization sync so acquisition dates are more exact.
- Add realtime updates to Standings / Draft after a completed trade.
- Add collapsible trade history for an even denser layout.

### Trade Validation

Add validation rules:
- Prevent trading same player twice simultaneously
- Check roster slot availability
- Verify bench player validity

### Notifications

Email/SMS notifications on:
- Trade executed by another team member
- Hold point milestones reached
- Trade history summaries

## Testing

### Manual Testing

1. **Execute trade**:
   - Click 🔄 Trade on held player
   - Select bench player
   - Confirm
   - Verify trade appears in history

2. **View trade history**:
   - Scroll to Trade History
   - Verify newest trades display first
   - Verify saved snapshot names still render even if live player metadata is missing

### Database Verification

```sql
-- Check active holds
SELECT * FROM player_holds 
WHERE league_code = 'DEMO01' AND team_name = 'Team 1';

-- Check trade history
SELECT * FROM player_trades 
WHERE league_code = 'DEMO01' AND team_name = 'Team 1'
ORDER BY date_traded DESC;
```

## Troubleshooting

### 400 Bad Request on Hold Creation

If you see `POST .../player_holds 400 (Bad Request)` error:

**Solution 1: Check RLS Policies**
- Go to Supabase Dashboard → Authentication → Policies
- Ensure `player_holds` table has public insert/update/delete policies
- If RLS is enabled, run these in SQL Editor:
  ```sql
  GRANT ALL ON player_holds TO anon;
  GRANT ALL ON player_trades TO anon;
  ```

**Solution 2: Check Table Permissions**
- Supabase Dashboard → SQL Editor
- Run: `SELECT * FROM player_holds LIMIT 1;` to verify table exists
- If error, re-run `TRADES_SCHEMA.sql`

**Solution 3: Disable Auto-Initialize**
- Edit `docs/pool/trades.html`
- Comment out this line (around line 300):
  ```javascript
  // initializeHoldsForRoster();
  ```
- Manually add holds via Supabase insert instead

### Holds not loading
- Verify player_holds table exists: `SELECT * FROM player_holds LIMIT 1;`
- Check league_code matches
- Verify `team_id` / `team_name` on the hold matches the selected roster team

### Trades failing
- Check both player_holds and player_trades tables exist
- Re-run `TRADES_SCHEMA.sql` so `execute_pool_trade()` exists
- Ensure player slugs are valid (must match nhl_players.puckpedia_slug)
- Verify no duplicate holds for same player+team

### Points not accumulating
- Run manual update via Supabase SQL or Python script
- Verify scoring settings loaded correctly
- Check nhl_players table has current stats

## Notes

- **Password Protection**: All pool pages require password "parieur2026"
- **Team Selection**: Trades page defaults to first team, use selector to switch
- **Date Format**: All dates stored as ISO 8601 timestamps in Supabase
- **Scoring**: Uses same pool_settings table as standings/draft pages
- **Cache**: Player list cached in sessionStorage, and missing roster/trade players are fetched on demand
- **Auto-Initialization**: Holds are auto-created on page load if table permissions allow

## Support

For issues with:
- **Schema**: Run TRADES_SCHEMA.sql again or check table structure
- **Navigation**: Verify all nav hrefs updated in join.html, standings.html, trades.html
- **Data**: Check Supabase dashboard for data integrity
- **Performance**: Add indexes if querying large datasets (already included in schema)
- **Permissions**: Check RLS policies and table grants in Supabase

