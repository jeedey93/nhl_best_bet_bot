-- ============================================================
-- Pool RLS Migration
-- Run this once in Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- 1. Add access_token to pool_leagues
ALTER TABLE pool_leagues
  ADD COLUMN IF NOT EXISTS access_token TEXT;

-- 2. Backfill tokens for all existing leagues that don't have one yet
UPDATE pool_leagues
SET access_token = encode(gen_random_bytes(18), 'base64')
WHERE access_token IS NULL;

-- 3. Make access_token required going forward
ALTER TABLE pool_leagues
  ALTER COLUMN access_token SET NOT NULL;

-- ============================================================
-- Enable RLS on all pool tables
-- ============================================================
ALTER TABLE pool_leagues       ENABLE ROW LEVEL SECURITY;
ALTER TABLE pool_rosters       ENABLE ROW LEVEL SECURITY;
ALTER TABLE pool_settings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_trades      ENABLE ROW LEVEL SECURITY;
ALTER TABLE pool_draft_order   ENABLE ROW LEVEL SECURITY;
ALTER TABLE pool_draft_picks   ENABLE ROW LEVEL SECURITY;
ALTER TABLE pool_draft_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE pool_locks         ENABLE ROW LEVEL SECURITY;

-- nhl_players stays public (shared data, no league scope)
-- If RLS is already enabled on it, add a permissive read policy:
-- ALTER TABLE nhl_players ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "public read" ON nhl_players FOR SELECT USING (true);

-- ============================================================
-- Helper: extract x-pool-token from request headers
-- ============================================================
-- Supabase exposes headers as request.headers (JSON text).
-- We use a small helper to safely read it.
CREATE OR REPLACE FUNCTION pool_request_token()
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(
    current_setting('request.headers', true)::json->>'x-pool-token',
    ''
  );
$$;

-- ============================================================
-- pool_leagues policies
-- ============================================================
DROP POLICY IF EXISTS "league token read"   ON pool_leagues;
DROP POLICY IF EXISTS "league token write"  ON pool_leagues;
DROP POLICY IF EXISTS "league token delete" ON pool_leagues;
DROP POLICY IF EXISTS "league insert open"  ON pool_leagues;

-- Anyone can create a new league (no token needed yet — token is set on insert)
CREATE POLICY "league insert open" ON pool_leagues
  FOR INSERT WITH CHECK (true);

-- Read: token in header must match this row's access_token
CREATE POLICY "league token read" ON pool_leagues
  FOR SELECT USING (access_token = pool_request_token());

-- Update (rename league, etc.): same token check
CREATE POLICY "league token write" ON pool_leagues
  FOR UPDATE USING (access_token = pool_request_token());

-- Delete: same token check
CREATE POLICY "league token delete" ON pool_leagues
  FOR DELETE USING (access_token = pool_request_token());

-- ============================================================
-- Reusable sub-select: "does this league_code belong to the token?"
-- Used in all per-league tables below.
-- ============================================================

-- pool_rosters
DROP POLICY IF EXISTS "league token access" ON pool_rosters;
CREATE POLICY "league token access" ON pool_rosters
  USING (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  )
  WITH CHECK (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  );

-- pool_settings
DROP POLICY IF EXISTS "league token access" ON pool_settings;
CREATE POLICY "league token access" ON pool_settings
  USING (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  )
  WITH CHECK (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  );

-- player_trades
DROP POLICY IF EXISTS "league token access" ON player_trades;
CREATE POLICY "league token access" ON player_trades
  USING (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  )
  WITH CHECK (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  );

-- pool_draft_order
DROP POLICY IF EXISTS "league token access" ON pool_draft_order;
CREATE POLICY "league token access" ON pool_draft_order
  USING (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  )
  WITH CHECK (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  );

-- pool_draft_picks
DROP POLICY IF EXISTS "league token access" ON pool_draft_picks;
CREATE POLICY "league token access" ON pool_draft_picks
  USING (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  )
  WITH CHECK (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  );

-- pool_draft_settings
DROP POLICY IF EXISTS "league token access" ON pool_draft_settings;
CREATE POLICY "league token access" ON pool_draft_settings
  USING (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  )
  WITH CHECK (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  );

-- pool_locks
DROP POLICY IF EXISTS "league token access" ON pool_locks;
CREATE POLICY "league token access" ON pool_locks
  USING (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  )
  WITH CHECK (
    league_code IN (
      SELECT code FROM pool_leagues WHERE access_token = pool_request_token()
    )
  );

-- ============================================================
-- Verify: show all leagues with their tokens (copy these for existing leagues)
-- ============================================================
SELECT code, name, access_token FROM pool_leagues ORDER BY created_at;
