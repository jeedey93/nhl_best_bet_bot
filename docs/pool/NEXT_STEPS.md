# Trade History - Next Steps for Resolution

## Summary of Enhancements Deployed

All diagnostic enhancements have been deployed to help identify why trade history shows 0 results. The code now provides granular visibility into every step of the trade execution and retrieval process.

**Files Updated:**
- ✅ `/docs/pool/trades.html` - Enhanced logging in 4 critical functions
- ✅ `/docs/pool/TRADES_SCHEMA.sql` - Added `league_code` index for query optimization
- ✅ `/docs/pool/TRADE_HISTORY_DIAGNOSTIC.md` - Comprehensive diagnostic guide
- ✅ `/docs/pool/DIAGNOSTIC_ENHANCEMENTS.md` - Technical explanation of changes

## What You Need to Do

### Phase 1: Make a Test Trade & Capture Logs

1. **Navigate to the trades page**
   - URL should be: `your-domain/pool/trades.html?league=GYN9`

2. **Open Developer Tools**
   - Press `F12` on Windows/Linux or `⌘+Option+I` on Mac
   - Go to the **Console** tab

3. **Make a test trade**
   - Select an active roster player (from F/D/G slots)
   - Select a bench player to receive
   - Click "Execute Trade"

4. **Capture all console output**
   - Look for logs starting with `[RPC]`, `[POST]`, `[TRADES]`
   - Copy/screenshot the entire console output
   - **Share it with the diagnostic guide in hand**

### Phase 2: Check Database Directly

While the trade is being tested, also verify what's in Supabase:

1. **Go to Supabase Dashboard**
   - Navigate to: https://app.supabase.com
   - Select your project
   - Click **SQL Editor** on left sidebar

2. **Run diagnostic queries**

   **Query 1: Total trades count**
   ```sql
   SELECT COUNT(*) as total FROM player_trades;
   ```

   **Query 2: All league codes in database**
   ```sql
   SELECT DISTINCT league_code FROM player_trades ORDER BY league_code;
   ```

   **Query 3: Trades for your league**
   ```sql
   SELECT 
     id, created_at, league_code, team_id, team_name,
     player_from_slug, player_to_slug, date_traded
   FROM player_trades
   WHERE league_code='GYN9'
   ORDER BY date_traded DESC
   LIMIT 10;
   ```

   **Query 4: Check for NULL league codes**
   ```sql
   SELECT 
     id, created_at, league_code, team_id, team_name,
     player_from_slug, player_to_slug
   FROM player_trades
   WHERE league_code IS NULL OR league_code=''
   ORDER BY created_at DESC
   LIMIT 10;
   ```

3. **Share the query results**
   - Screenshot or copy/paste results

### Phase 3: Interpret Diagnostic Output

#### If you see in console:
```
[TRADES] Total: 5 trades for this league (5 total in DB)
```
✅ **SUCCESS** - Trades are appearing! Issue is resolved.

#### If you see in console:
```
[TRADES] Total: 0 trades for this league (5 total in DB)
⚠️  DIAGNOSTIC: 5 trades exist in database but none match league_code='GYN9'
```
❌ **Mismatch detected** - Your league code in the URL doesn't match the one stored. Run Query 2 above to see what league codes exist.

#### If you see in console:
```
[RPC] ✗ RPC response (400): Outgoing player is not on the active roster
```
❌ **Player selection error** - Make sure you're selecting from ACTIVE roster (F/D/G), not bench.

#### If you see in console:
```
[POST] Attempt 1/2: {...primary payload...}
[POST] ✗ Attempt 1 failed (400): column "xyz" not found
[POST] Schema mismatch on attempt 1, trying fallback...
[POST] Attempt 2/2: {...fallback payload...}
[POST] ✓ Success on attempt 2
```
⚠️ **Fallback worked** - First payload schema issue but fallback succeeded. This is expected. Check if trades appear in Query 3 above.

## Expected Console Output (Success Case)

You should see something like this in the console:

```javascript
[RPC] Calling execute_pool_trade with: {league: "GYN9", team_id: "1040", team_name: "My Team", from: "player-slug-1", to: "player-slug-2", timestamp: "2026-04-28T..."}
[RPC] Raw _leagueCode value: {"value":"GYN9","type":"string","length":4}
[RPC] ✓ RPC SUCCESS: {ok: true, team_id: "1040", team_name: "My Team", ...}

[Trade] RPC executed. Used RPC: true. Now waiting for history...

[Wait attempt 1/12] Looking for trade: player-slug-1 → player-slug-2
[TRADES] Total trades in entire table: 5
[TRADES] Loaded for league GYN9
  Total: 5 trades for this league (5 total in DB)
  (table of recent trades shown)

✓ Found trade! {...trade record...}
[Trade] Trade history found after execution
```

## If Things Are Still Not Working

Please provide:

1. **Full console output** (F12 → Console → copy all logs after making trade)
2. **Results from all 4 SQL queries** above
3. **Browser URL** at time of trade test
4. **Team ID and team name** you're testing with

This information will pinpoint exactly where the breakdown is occurring.

## Summary of Diagnostic Enhancements

| Component | Enhancement | Purpose |
|-----------|-------------|---------|
| `loadTrades()` | Total count query | Detect if trades exist but don't match league code |
| `loadTrades()` | Mismatch detection | Warn if DB has data but league filter fails |
| `executeTradeRpc()` | Parameter logging | Verify league code being sent to RPC |
| `executeTradeRpc()` | Raw value inspection | Check type/length of league code |
| `createTradeRecord()` | Payload logging | Show exact data being inserted |
| `postWithFallback()` | Attempt tracking | Show which payload succeeded |
| `TRADES_SCHEMA.sql` | League code index | Optimize query performance |

## What We're Testing

1. **Is `league_code` being passed correctly to RPC?** → See RPC logs
2. **Is the RPC inserting data?** → See RPC SUCCESS log
3. **Is fallback working if RPC fails?** → See POST logs
4. **Does data match the league filter?** → See TRADES total count comparison
5. **Are there rows in DB with wrong league code?** → Run Query 4

## Immediate Action

**Do this right now to get us the data we need:**

1. Make a trade
2. Right-click → Inspect → Console tab
3. Copy ALL console output (select all, Ctrl+C)
4. Paste it in your response along with the SQL query results

This will give us everything we need to identify the exact issue and fix it.

---

**Questions?** Check `/docs/pool/TRADE_HISTORY_DIAGNOSTIC.md` for more detailed explanations of each console log format.

