# Diagnostic Enhancements - Deployment Checklist

## Files Modified ✅

- ✅ `/docs/pool/trades.html` (1003 lines)
  - Enhanced `loadTrades()` with total count diagnostic
  - Enhanced `executeTradeRpc()` with parameter logging
  - Enhanced `createTradeRecord()` with payload logging
  - Enhanced `postWithFallback()` with attempt tracking

- ✅ `/docs/pool/TRADES_SCHEMA.sql` (283 lines)
  - Added `CREATE INDEX idx_trades_league_code` on line 24

- ✅ `/docs/pool/TRADE_HISTORY_DIAGNOSTIC.md` (NEW)
  - Complete diagnostic guide with all console log formats
  - SQL query examples for Supabase verification
  - Scenario-based troubleshooting

- ✅ `/docs/pool/DIAGNOSTIC_ENHANCEMENTS.md` (NEW)
  - Technical explanation of all enhancements
  - Before/after code comparisons
  - How to use the diagnostics

- ✅ `/docs/pool/NEXT_STEPS.md` (NEW)
  - Step-by-step instructions for testing
  - SQL queries to run for verification
  - Expected output examples

## What Each Enhancement Does

### 1. Load Trades Diagnostic (`loadTrades()` function)

**Problem it solves**: Determine if trades exist in DB but aren't being retrieved

**Code added**:
- Fetches total count from entire `player_trades` table
- Compares total count with league-filtered count
- If mismatch: warns user that league code is wrong
- Suggests checking Supabase directly

**Console output**:
```
[TRADES] Total trades in entire table: 5
[TRADES] Loaded for league GYN9
  Total: 0 trades for this league (5 total in DB)
  ⚠️  DIAGNOSTIC: 5 trades exist in database but none match league_code='GYN9'
```

### 2. RPC Execution Diagnostic (`executeTradeRpc()` function)

**Problem it solves**: Verify league code is being passed correctly to RPC

**Code added**:
- Logs all RPC parameters before calling
- Logs raw `_leagueCode` value with type inspection
- Logs full RPC response on success or error

**Console output**:
```
[RPC] Calling execute_pool_trade with: {league: "GYN9", team_id: "...", ...}
[RPC] Raw _leagueCode value: {"value":"GYN9","type":"string","length":4}
[RPC] ✓ RPC SUCCESS: {ok: true, ...}
```

### 3. Trade Record Creation Diagnostic (`createTradeRecord()` function)

**Problem it solves**: See exactly what data is being inserted into DB

**Code added**:
- Logs primary and fallback payloads before POST
- Logs insert result

**Console output**:
```
[TRADE RECORD] Creating with payloads: {
  primary: {league_code: "GYN9", team_id: "1040", ...},
  fallback: {league_code: "GYN9", team_id: "1040", ...}
}
[TRADE RECORD] Insert result: {id: "...", ...}
```

### 4. POST Fallback Diagnostic (`postWithFallback()` function)

**Problem it solves**: Track which POST attempt succeeds and why

**Code added**:
- Logs each POST attempt number
- Logs exact payload being sent
- Logs exact error from server
- Shows which payload worked

**Console output**:
```
[POST] Attempt 1/2: {league_code: "GYN9", ...full payload...}
[POST] ✗ Attempt 1 failed (400): column "xyz" not found
[POST] Schema mismatch on attempt 1, trying fallback...
[POST] Attempt 2/2: {league_code: "GYN9", ...minimal...}
[POST] ✓ Success on attempt 2
```

### 5. Database Index (`TRADES_SCHEMA.sql`)

**Problem it solves**: Ensure `WHERE league_code='...'` queries are efficient

**Code added**:
```sql
CREATE INDEX IF NOT EXISTS idx_trades_league_code ON player_trades(league_code);
```

**Status**: This index should already exist if the SQL migration has been applied.

## Testing Instructions

### Quick Test (5 minutes)

1. Go to: `your-domain/pool/trades.html?league=GYN9`
2. Press F12 → Console tab
3. Make one trade
4. Watch console for `[RPC]`, `[POST]`, `[TRADES]` logs
5. Record what you see

### Full Diagnostic Test (15 minutes)

1. Complete "Quick Test" above
2. Copy all console output
3. Open Supabase SQL Editor
4. Run the 4 diagnostic queries from `NEXT_STEPS.md`
5. Share console output + SQL results

## Debug Log Checklists

### After Making a Trade, You Should See:

**Stage 1 - Trade Initiation**
- [ ] `[Trade] Starting: ...` 
- [ ] `[Trade] RPC executed. Used RPC: true/false`

**Stage 2 - RPC or POST (depending on execution path)**
- [ ] `[RPC] Calling execute_pool_trade with: ...` 
- [ ] `[RPC] Raw _leagueCode value: ...`
- [ ] Either `[RPC] ✓ RPC SUCCESS` OR `[POST] Attempt ...`

**Stage 3 - Trade Record Wait**
- [ ] `[Wait attempt 1/12] Looking for trade: ... → ...`
- [ ] `[TRADES] Total trades in entire table: X`
- [ ] `[TRADES] Loaded for league GYN9`

**Stage 4 - Result**
- [ ] Either: `✓ Found trade!` → SUCCESS
- [ ] Or: `✗ Trade not found after 12 attempts` → INVESTIGATE

## Key Variables to Monitor

| Variable | What it shows | Expected | Problem if |
|----------|---------------|----------|------------|
| `league` (URL param) | Your league ID | GYN9 | Different from trades in DB |
| `team_id` (team object) | Your team UUID | Long string | Trades use team_name instead |
| `p_league_code` (RPC) | League sent to RPC | Matches URL | NULL or mismatched |
| RPC response | Success/error | `ok: true` | Error message shown |
| Total trades count | Trades in entire DB | > 0 | No trades created yet |
| League trades count | Trades matching your league | > 0 | League code mismatch |

## Success Indicators

✅ **Full Success** - You see in console:
```
[TRADES] Total: X trades for this league (X total in DB)
(table of trades shown)
```

⚠️ **Partial Success** - You see:
```
[RPC] ✓ RPC SUCCESS but [TRADES] shows 0 trades for this league
```
→ Suggests league code mismatch or team filtering issue

❌ **Failure** - You see:
```
[RPC] ✗ RPC response (400): Error message
```
→ RPC didn't execute, check error message

## Integration with Existing Code

The enhancements are **backwards compatible**:
- All logging is additive (doesn't change behavior)
- Fallback payload unchanged (still has team_id, team_name_snapshot)
- No changes to return values or error handling
- If console is quiet, logging just doesn't appear

## File Structure After Enhancements

```
/docs/pool/
├── trades.html                          ← UPDATED (diagnostic logging)
├── TRADES_SCHEMA.sql                    ← UPDATED (index added)
├── TRADES_SETUP.md                      ← Existing (no changes)
├── TRADE_HISTORY_DIAGNOSTIC.md          ← NEW (detailed guide)
├── DIAGNOSTIC_ENHANCEMENTS.md           ← NEW (technical info)
├── NEXT_STEPS.md                        ← NEW (action steps)
└── [other files unchanged]
```

## Deployment Status

| Item | Status | Next Step |
|------|--------|-----------|
| HTML logging | ✅ Ready | Deploy to production |
| SQL index | ✅ Ready | Run in Supabase SQL editor |
| Documentation | ✅ Ready | Share with user |
| Testing | ⏳ Pending | User makes test trade |

## What's NOT Changed

- ✅ RPC function logic (still works same way)
- ✅ Roster state storage (still uses pool_rosters)
- ✅ Fallback payload structure (still includes all required fields)
- ✅ Trade execution flow (still same 3 paths)
- ✅ UI components (still same buttons/forms)
- ✅ Error handling (still same error messages)

## Next Action

All code changes are complete. Ready for testing:

1. **Deploy updated `trades.html`** to your hosting
2. **Run the SQL index creation** in Supabase (or it will run automatically if using migration)
3. **Perform test trade** while watching console
4. **Share console output + SQL query results** for final diagnosis

See `NEXT_STEPS.md` for detailed testing instructions.

