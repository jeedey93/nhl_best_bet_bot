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
- `team_name` - Team name (text, e.g., "Team 1")
- `player_slug` - PuckPedia player slug (puckpedia_slug)
- `date_acquired` - When player was acquired
- `points_accumulated` - Points accumulated while held (updated manually or via cron)

**Unique Constraint**: One hold per player per (league_code, team_name)

#### `player_trades` Table
Historical record of all trades:
- `id` - UUID primary key
- `league_code` - League identifier
- `team_name` - Team name (text, e.g., "Team 1")
- `player_from_slug` - Player being traded out
- `player_to_slug` - Player being traded in
- `date_from_acquired` - When the "from" player was originally acquired
- `date_traded` - When the trade occurred
- `points_accumulated_at_trade` - Points saved from the "from" player

### File Structure

```
docs/pool/
├── trades.html              # Main trades/holds management page
│   ├── Current Holds section
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

This creates:
- `player_holds` table with indexes
- `player_trades` table with indexes

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

### Adding a Hold

**All main roster players (Forwards, Defensemen, Goalies) are automatically in holds by default.**

- When you visit the Trades page, any main roster player without an existing hold will be automatically added to a hold with today's date
- Bench players are excluded from holds
- Points start accumulating immediately on the next daily update

**Manual holds can also be added via direct Supabase insert:**
```json
{
  "league_code": "DEMO01",
  "team_id": "uuid-123",
  "player_slug": "connor-mcdavid",
  "date_acquired": "2026-04-27T00:00:00Z",
  "points_accumulated": 0
}
```

### Trading Between Roster and Bench

1. Go to Trades page → Select team
2. View Current Holds
3. Click "🔄 Trade" on a held player
4. Select a bench player to trade in
5. Confirm trade
6. System automatically:
   - Swaps players between active roster slot and bench slot
   - Persists updated roster composition to `pool_rosters` (visible in Draft/Standings)
   - Validates salary cap before confirming swap (bench excluded from cap)
   - Saves accumulated points to trade history
   - Creates new hold on player-to (bench player)
   - Clears old hold record

### Releasing a Hold

Click "↩ Release" on any held player to remove the hold without trading.

### Viewing Trade History

Trade History section shows all past trades with:
- From player name & acquisition date
- Trade execution date
- To player name
- Points accumulated and saved

## Data Flow

### On Trade Execution

```
1. Get current hold for player-from
2. Calculate points_accumulated from hold record
3. Insert record into player_trades with:
   - player_from_slug
   - player_to_slug
   - date_from_acquired
   - date_traded (now)
   - points_accumulated_at_trade
4. Delete hold for player-from
5. Create new hold for player-to with date_acquired = now
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
- Lists available bench players
- User selects target

**`confirmTrade()`** - Execute trade transaction
- Inserts trade record
- Deletes old hold
- Creates new hold on bench player

### UI Components

**Current Holds Card**
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
    <button onclick="releaseHold(...)">↩ Release</button>
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
| `/rest/v1/player_holds?id=eq.X` | DELETE | Release hold |
| `/rest/v1/player_trades` | GET | List trades |
| `/rest/v1/player_trades` | POST | Record trade |

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

### Bench-to-Main Swaps

Extend system to also track trades**from** bench to main roster (currently only main-to-bench supported).

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

1. **Add a hold**:
   - Navigate to Trades page
   - Add player with date
   - Verify in Current Holds

2. **Execute trade**:
   - Click 🔄 Trade on held player
   - Select bench player
   - Confirm
   - Verify trade appears in history

3. **Release hold**:
   - Click ↩ Release
   - Verify hold is removed

4. **View trade history**:
   - Scroll to Trade History
   - Verify all trades display correctly

### Database Verification

```sql
-- Check active holds
SELECT * FROM player_holds 
WHERE league_code = 'DEMO01' AND team_id = 'uuid-123';

-- Check trade history
SELECT * FROM player_trades 
WHERE league_code = 'DEMO01' AND team_id = 'uuid-123'
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
- Verify team_id is correct UUID format

### Trades failing
- Check both player_holds and player_trades tables exist
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
- **Cache**: Player list cached in sessionStorage, old key "hp_players" purged
- **Auto-Initialization**: Holds are auto-created on page load if table permissions allow

## Support

For issues with:
- **Schema**: Run TRADES_SCHEMA.sql again or check table structure
- **Navigation**: Verify all nav hrefs updated in join.html, standings.html, trades.html
- **Data**: Check Supabase dashboard for data integrity
- **Performance**: Add indexes if querying large datasets (already included in schema)
- **Permissions**: Check RLS policies and table grants in Supabase

