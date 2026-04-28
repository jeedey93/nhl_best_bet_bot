# Trade History Resolution - Diagnostic Enhancements

## Problem Summary
After executing a trade, the roster swaps correctly but trade history shows 0 results. The console message was: `NO TRADES FOUND in database! Checking league code...`

## Root Cause Analysis

The issue likely stems from one of the following:

1. **League code mismatch** - Trades are being inserted with a different `league_code` than what's in the URL
2. **NULL league_code** - Fallback payload may still have issues despite fixes
3. **RPC not executing** - The `execute_pool_trade()` function may not be running at all
4. **Database filtering** - The Supabase query filtering by `league_code` may not be working

## Changes Made to Diagnose

### 1. Enhanced `loadTrades()` Function
**File**: `/docs/pool/trades.html` (line ~449)

Added comprehensive diagnostics:
- **Total count query**: Fetches total trades in entire `player_trades` table
- **League-filtered query**: Fetches trades for current league only
- **Mismatch detection**: If total > 0 but league-filtered = 0, warns about code mismatch
- **Better error messages**: Tells user to check Supabase directly

**New output format**:
```
[TRADES] Total trades in entire table: 5
[TRADES] Loaded for league GYN9
  Total: 0 trades for this league (5 total in DB)
  ⚠️  DIAGNOSTIC: 5 trades exist in database but none match league_code='GYN9'
```

### 2. Enhanced `executeTradeRpc()` Function  
**File**: `/docs/pool/trades.html` (line ~805)

Added detailed logging:
- Logs all RPC parameters BEFORE calling
- Logs raw `_leagueCode` value with type checking
- Logs full RPC response (success or error text)
- Shows which execution path is taken

**New output format**:
```
[RPC] Raw _leagueCode value: {"value":"GYN9","type":"string","length":4}
[RPC] ✓ RPC SUCCESS: {ok: true, team_id: "...", ...}
```

### 3. Enhanced `createTradeRecord()` Function
**File**: `/docs/pool/trades.html` (line ~850)

Added payload logging:
- Logs both primary and fallback payloads with all fields
- Logs final insert result
- Shows which payload was used (if fallback)

**New output format**:
```
[TRADE RECORD] Creating with payloads: {
  primary: {league_code: "GYN9", team_id: "1040", ...},
  fallback: {league_code: "GYN9", team_id: "1040", ...}
}
[TRADE RECORD] Insert result: {id: "...", ...}
```

### 4. Enhanced `postWithFallback()` Function
**File**: `/docs/pool/trades.html` (line ~349)

Added granular POST tracing:
- Logs each POST attempt number
- Logs exact payload being sent
- Logs exact error message from server
- Shows which payload succeeded

**New output format**:
```
[POST] Attempt 1/2: {league_code: "GYN9", ...}
[POST] ✗ Attempt 1 failed (400): column "xyz" not found
[POST] Schema mismatch on attempt 1, trying fallback...
[POST] Attempt 2/2: {league_code: "GYN9", ...minimal...}
[POST] ✓ Success on attempt 2
```

### 5. Added Index on `league_code`
**File**: `/docs/pool/TRADES_SCHEMA.sql` (line ~24)

Added primary index:
```sql
CREATE INDEX IF NOT EXISTS idx_trades_league_code ON player_trades(league_code);
```

This ensures `WHERE league_code='GYN9'` queries are efficient.

### 6. Created Diagnostic Documentation
**File**: `/docs/pool/TRADE_HISTORY_DIAGNOSTIC.md`

Comprehensive guide explaining:
- What each console log means
- Success scenario full output
- Failure scenarios and what to check
- SQL queries to run in Supabase to verify data
- Step-by-step troubleshooting

## How to Use These Enhancements

### For Testing:
1. Navigate to your trades page
2. Open Browser Developer Tools (F12)
3. Go to **Console** tab
4. Make a test trade (swap active player with bench player)
5. **Watch the console output** - you'll see:
   - `[RPC]` logs for RPC execution
   - `[POST]` logs for fallback creation
   - `[TRADES]` logs for history loading with diagnostics

### For Troubleshooting:
1. Look for **mismatch detection** message:
   - If you see "trades exist in database but none match league_code", the issue is a league code mismatch
   - Check Supabase directly to see what league codes exist

2. Look for **RPC vs POST success**:
   - If RPC succeeds but history shows 0, check team filtering
   - If POST fails, note the exact error message

3. Check **Supabase directly** using SQL queries provided in `TRADE_HISTORY_DIAGNOSTIC.md`

## Expected Next Step

Once you make a trade with these enhancements:

1. **Share the full console output** captured after the trade
2. **Run the diagnostic SQL queries** and share results
3. **We'll identify exactly** where the breakdown occurs:
   - Is data being inserted? (check RPC/POST logs)
   - Is data in DB but not retrievable? (check league code in Supabase)
   - Is filtering failing? (check team matching logic)

## Files Modified

- ✅ `/docs/pool/trades.html` - Added diagnostic logging to 4 functions
- ✅ `/docs/pool/TRADES_SCHEMA.sql` - Added `league_code` index
- ✅ `/docs/pool/TRADE_HISTORY_DIAGNOSTIC.md` - New diagnostic guide

## Fallback Payload Status

The fallback payload now includes ALL required team identification fields:
```javascript
{
  league_code: _leagueCode,        // ✅ League identifier
  team_id: team.id,                // ✅ Team UUID
  team_name: team.name,            // ✅ Team name
  team_name_snapshot: team.name,   // ✅ Team name at trade time
  player_from_slug: ...,           // ✅ Outgoing player
  player_to_slug: ...,             // ✅ Incoming player
  date_from_acquired: ...,         // ✅ Acquisition date
  date_traded: now,                // ✅ Trade timestamp
  points_accumulated_at_trade: 0   // ✅ Points at trade
}
```

This ensures even if the primary payload fails, the fallback will insert with proper league/team context.

## Next Actions

1. **Deploy** these enhancements to production
2. **Test** by making a trade and watching console
3. **Share console output** + Supabase query results
4. **We'll identify the exact** bottleneck and fix it

