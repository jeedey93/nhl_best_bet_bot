# Trade History Diagnostic Guide

## Current Problem

Trades are executing (roster swaps work) but trade history shows 0 results when loading the trades page, even after making a trade.

## Updated Diagnostic Enhancements

The `/docs/pool/trades.html` file has been enhanced with detailed console logging to help diagnose where the breakdown is occurring.

### What to do:

1. **Make a test trade** (swap one player from active to bench)
2. **Open Browser Developer Tools** (F12 or Right-click → Inspect → Console tab)
3. **Look for the following log groups in order:**

---

## Expected Console Output (Success Scenario)

### Stage 1: RPC Execution
```
[RPC] Calling execute_pool_trade with: {
  league: "GYN9"
  team_id: "..." 
  team_name: "Your Team Name"
  from: "player-slug-1"
  to: "player-slug-2"
}

[RPC] ✓ RPC SUCCESS: {
  ok: true
  team_id: "..."
  team_name: "Your Team Name"
  ... (other data)
}
```

**What it means**: The RPC function ran on the server and inserted the trade record to `player_trades` table. If you see this, the database INSERT happened.

---

### Stage 2: Trade Record Creation (if RPC returned false or used legacy path)
```
[TRADE RECORD] Creating with payloads: {
  primary: { league_code: "GYN9", team_id: "...", team_name: "...", ... }
  fallback: { league_code: "GYN9", team_id: "...", ... }
}

[POST] Attempt 1/2: { league_code: "GYN9", ... }
[POST] ✓ Success on attempt 1
[TRADE RECORD] Insert result: { id: "...", ... }
```

**What it means**: Fallback legacy trade creation also succeeded.

---

### Stage 3: Trade History Loading
```
[TRADES] Total trades in entire table: 5
[TRADES] Fetching from: https://...?league_code=eq.GYN9&select=...

[TRADES] Loaded for league GYN9
  Total: 5 trades for this league (5 total in DB)
  (table shows recent trades)
```

**What it means**: Trades are visible! The issue is resolved.

---

## Failure Scenarios & Diagnostics

### Scenario 1: RPC Returns Error
```
[RPC] ✗ RPC response (400): ERROR: Outgoing player is not on the active roster
```

**What it means**: Player wasn't found on active roster. Check that you selected the correct player from active (F/D/G) roster, not bench.

---

### Scenario 2: POST Fails with 400 Column Error
```
[POST] Attempt 1/2: { league_code: "GYN9", team_id: "1040", ...full data... }
[POST] ✗ Attempt 1 failed (400): column "some_field" not found
[POST] Schema mismatch on attempt 1, trying fallback...
[POST] Attempt 2/2: { league_code: "GYN9", team_id: "1040", ...minimal data... }
[POST] ✓ Success on attempt 2
```

**What it means**: First payload had a field that doesn't exist in the table schema, but fallback with minimal fields worked OK. This is expected behavior.

---

### Scenario 3: Zero Trades After Execution
```
[TRADES] Total trades in entire table: 5
[TRADES] Loaded for league GYN9
  Total: 0 trades for this league (5 total in DB)
  ⚠️  DIAGNOSTIC: 5 trades exist in database but none match league_code='GYN9'
  This suggests: Trade was inserted with WRONG league_code or NULL league_code
```

**What it means**: 
- The database HAS trades, but they were inserted with a DIFFERENT `league_code` (or NULL)
- The RPC parameter `p_league_code` may not match what's in the URL
- Check that `_leagueCode` variable is correctly extracted from URL

**Fix**: Check Supabase directly to see what `league_code` values exist:
```sql
SELECT DISTINCT league_code FROM player_trades ORDER BY league_code;
```

Compare with your current league code in the URL.

---

### Scenario 4: RPC Succeeds but Trade Record Creation Fails
```
[RPC] ✓ RPC SUCCESS: { ok: true, ... }

[Trade] RPC executed. Used RPC: true. Now waiting for history...

[Wait attempt 1/12] Looking for trade: player-1 → player-2
[TRADES] Loaded for league GYN9
  Total: 0 trades for this league (total in DB)
  
[Wait attempt 2/12] Looking for trade: ...
... (repeats 12 times)

✗ Trade not found after 12 attempts
```

**What it means**:
- RPC executed successfully and should have inserted a row
- But 6 seconds later the row still isn't visible
- This could be a caching issue or the RPC INSERT failed silently

**Diagnostic**: Open Supabase SQL editor and run:
```sql
SELECT * FROM player_trades 
WHERE league_code='GYN9' 
ORDER BY created_at DESC 
LIMIT 5;
```

Check if the row exists. If it does, wait a few seconds and refresh the browser. If it doesn't, the RPC INSERT failed.

---

## How to Check Supabase Directly

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to **SQL Editor** (left sidebar)
4. Run one of these queries:

### Count total trades:
```sql
SELECT COUNT(*) as total FROM player_trades;
```

### List all distinct league codes:
```sql
SELECT DISTINCT league_code FROM player_trades ORDER BY league_code;
```

### Check trades for your league:
```sql
SELECT 
  id, created_at, league_code, team_id, team_name,
  player_from_slug, player_to_slug, date_traded
FROM player_trades
WHERE league_code='GYN9'
ORDER BY date_traded DESC
LIMIT 10;
```

### Check for NULL league_code (suspicious):
```sql
SELECT 
  id, created_at, league_code, team_id, team_name,
  player_from_slug, player_to_slug
FROM player_trades
WHERE league_code IS NULL OR league_code=''
ORDER BY created_at DESC
LIMIT 10;
```

---

## Key Checks Performed by New Diagnostics

### In `loadTrades()`:
✅ Fetches **total count** from entire `player_trades` table first  
✅ Then fetches trades filtered by `league_code`  
✅ **Compares the two counts** to identify mismatches  
✅ If 0 results but >0 total: suggests code/name mismatch  

### In `executeTradeRpc()`:
✅ Logs all RPC parameters before calling  
✅ Logs full RPC response (success or error)  

### In `createTradeRecord()`:
✅ Logs both primary and fallback payloads  
✅ Logs final insert result  

### In `postWithFallback()`:
✅ Logs each POST attempt number  
✅ Logs exact error message from server  
✅ Shows which payload succeeded (if any)  

---

## Summary: What to Look For

After making a test trade, check the console in **this order**:

1. ✅ **[RPC]** - Did RPC succeed or fail?
2. ✅ **[POST]** - If legacy path, did POST succeed?
3. ✅ **[TRADES]** - How many trades loaded for your league?
4. 🔢 **Total count** - Are there trades in DB but just not for your league?

If you see 0 trades but the total count > 0, the `league_code` in your trade record doesn't match the URL parameter.

---

## Next Steps

1. **Make a trade** while watching console
2. **Copy the full console output** and share it
3. **Run the SQL queries** above and share results
4. **We can then diagnose** exactly where the breakdown is occurring

