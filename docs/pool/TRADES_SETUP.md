# Hockey Pool Trade System - Implementation Guide

## Overview

The trades system now uses a simpler model:

1. `pool_rosters` is the single source of truth for who is on each team right now.
2. `player_trades` is the transaction history and tenure log.
3. `player_holds` remains in the schema only for backward compatibility (not used by the current trades page flow).

This eliminates hold-sync race conditions and keeps current ownership in one place.

## Architecture

### Data Model

#### `pool_rosters` (active state)

- Stores each team roster (`F`, `D`, `G`, `B`) in `data.teams[].roster`
- Is updated on every successful trade
- Drives Draft / Standings / Trades active ownership

#### `player_trades` (history + tenure)

Each row stores one swap event with snapshots:

- team identity: `league_code`, `team_id`, `team_name`, `team_name_snapshot`
- player snapshot: slug, name, position, NHL team
- slot snapshot: `from_slot_group/index`, `to_slot_group/index`
- tenure window anchor:
  - `date_from_acquired` = when outgoing player entered the active roster
  - `date_traded` = when outgoing player left active roster
- `points_accumulated_at_trade` currently stored as snapshot value (set to `0` by RPC in this version)

#### `player_holds` (legacy)

- Table still exists in `TRADES_SCHEMA.sql`
- Kept for backward compatibility with older scripts
- Not required by current `docs/pool/trades.html` runtime flow

### RPC: `execute_pool_trade()`

Performs atomic trade operations:

1. locks roster row
2. validates active player, bench player, position, salary cap
3. swaps players inside `pool_rosters`
4. inserts one `player_trades` history row

The RPC now derives `date_from_acquired` from the latest incoming trade for the outgoing player.
If no prior incoming trade exists, it falls back to `p_date_traded`.

## Setup Instructions

### 1. Apply migration

Run the full `docs/pool/TRADES_SCHEMA.sql` in Supabase SQL Editor.

This creates/updates:

- `player_trades` columns + indexes
- `execute_pool_trade()` RPC
- legacy `player_holds` compatibility objects

### 2. Verify grants/RLS

The provided SQL currently disables RLS and grants broad access for browser-based usage.
If you later switch to RLS-on, add explicit policies for `player_trades` and RPC execution.

### 3. Deploy page files

Ensure:

- `docs/pool/trades.html`
- `docs/pool/join.html`
- `docs/pool/standings.html`

## Usage Workflow

### Trading between active roster and bench

1. Open Trades page and select a team
2. Click `🔄 Trade` on an active roster player (`F`, `D`, `G` only)
3. Select an eligible bench replacement (same normalized slot type)
4. Confirm trade

System behavior:

- validates cap and position
- swaps slots in `pool_rosters`
- logs transaction in `player_trades`
- refreshes page from persisted roster

### Active roster "Acquired" date in UI

`trades.html` derives active player acquisition date from the latest `player_trades` incoming record (`player_to_slug`).

- if found: shows actual trade-in date
- if not found: shows legacy fallback text (pre-trade roster)

## Data Flow

### On trade execution

1. read and lock league roster
2. locate outgoing active slot and incoming bench slot
3. validate position + cap
4. update `pool_rosters`
5. insert `player_trades` row with snapshots

### Tenure derivation model

- tenure start (`date_from_acquired`) = latest incoming trade date for outgoing player on that team
- tenure end = current trade time (`date_traded`)

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/rest/v1/pool_rosters` | GET/POST | Load and persist active roster |
| `/rest/v1/player_trades` | GET/POST | Read and write trade history |
| `/rest/v1/rpc/execute_pool_trade` | POST | Atomic trade swap |

`player_holds` endpoints are no longer required for current page behavior.

## Testing

### Manual test checklist

1. execute valid trade and verify roster swap appears immediately
2. verify trade history row includes snapshots and slot labels
3. verify acquisition date on outgoing player in next trade comes from prior incoming history
4. verify cap rejection path by selecting an over-cap swap

### SQL verification

```sql
-- Latest trades for a team
SELECT *
FROM player_trades
WHERE league_code = 'DEMO01' AND team_name = 'Team 1'
ORDER BY date_traded DESC;

-- Optional: inspect current roster source of truth
SELECT data
FROM pool_rosters
WHERE league_code = 'DEMO01';
```

## Troubleshooting

### Trades fail with RPC missing

- Re-run `docs/pool/TRADES_SCHEMA.sql`
- Confirm function exists:

```sql
SELECT proname
FROM pg_proc
WHERE proname = 'execute_pool_trade';
```

### Trades fail with permissions errors

- Re-run `docs/pool/TRADES_SCHEMA.sql` grants section
- Verify `anon` can call RPC and write `player_trades`

### Acquisition dates look "legacy"

This happens for players that were already active before tenure logging started.
Dates become fully accurate after one complete cycle of trade-in/trade-out events for that player.

## Notes

- Password gate remains in place (`parieur2026`)
- Salary cap checks only apply to active roster (`F/D/G`), not bench
- Player cache + hydration behavior remains unchanged in `trades.html`
- `player_holds` can be removed in a later cleanup migration once old scripts are retired

