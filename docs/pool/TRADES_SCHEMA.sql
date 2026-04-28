-- Hockey Pool Trade System - Supabase SQL Migration
-- This SQL creates the tables needed for the player hold/trade system

-- Active ownership comes from pool_rosters + player_trades.
-- Legacy holds table is no longer needed.
DROP TABLE IF EXISTS player_holds;

-- Player Trades Table
-- Historical record of trades between main roster and bench
CREATE TABLE IF NOT EXISTS player_trades (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamp DEFAULT now(),
  league_code text NOT NULL,
  team_name text NOT NULL,
  player_from_slug text NOT NULL,
  player_to_slug text NOT NULL,
  date_from_acquired timestamp NOT NULL,
  date_traded timestamp NOT NULL,
  points_accumulated_at_trade integer DEFAULT 0,

  CONSTRAINT valid_trade CHECK (player_from_slug != player_to_slug)
);

CREATE INDEX IF NOT EXISTS idx_trades_league_team ON player_trades(league_code, team_name);
CREATE INDEX IF NOT EXISTS idx_trades_from_player ON player_trades(player_from_slug);
CREATE INDEX IF NOT EXISTS idx_trades_to_player ON player_trades(player_to_slug);
CREATE INDEX IF NOT EXISTS idx_trades_date ON player_trades(date_traded);

ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS team_id text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS team_name_snapshot text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS player_from_name text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS player_to_name text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS player_from_position text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS player_to_position text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS player_from_team text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS player_to_team text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS from_slot_group text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS from_slot_index integer;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS to_slot_group text;
ALTER TABLE player_trades ADD COLUMN IF NOT EXISTS to_slot_index integer;
CREATE INDEX IF NOT EXISTS idx_trades_league_team_id ON player_trades(league_code, team_id);

CREATE OR REPLACE FUNCTION execute_pool_trade(
  p_league_code text,
  p_team_id text,
  p_team_name text,
  p_player_from_slug text,
  p_player_to_slug text,
  p_date_traded timestamp DEFAULT now()
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_roster_row record;
  v_teams jsonb;
  v_team jsonb;
  v_updated_team jsonb;
  v_updated_teams jsonb;
  v_team_idx integer := -1;
  v_group text;
  v_value text;
  v_idx integer;
  v_from_group text;
  v_from_index integer;
  v_to_index integer;
  v_hold_date timestamp;
  v_team_name text;
  v_team_id text;
  v_from_cap integer := 0;
  v_to_cap integer := 0;
  v_current_cap bigint := 0;
  v_cap_after bigint := 0;
  v_from_name text;
  v_to_name text;
  v_from_position text;
  v_to_position text;
  v_from_team text;
  v_to_team text;
  v_to_norm text;
BEGIN
  SELECT *
  INTO v_roster_row
  FROM pool_rosters
  WHERE league_code = p_league_code
  LIMIT 1
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'League roster not found';
  END IF;

  v_teams := COALESCE(v_roster_row.data->'teams', '[]'::jsonb);
  IF jsonb_typeof(v_teams) IS DISTINCT FROM 'array' OR jsonb_array_length(v_teams) = 0 THEN
    RAISE EXCEPTION 'No teams found in roster data';
  END IF;

  FOR v_idx IN 0 .. jsonb_array_length(v_teams) - 1 LOOP
    IF COALESCE(v_teams->v_idx->>'id', '') = COALESCE(p_team_id, '')
       OR COALESCE(v_teams->v_idx->>'name', '') = COALESCE(p_team_name, '') THEN
      v_team_idx := v_idx;
      EXIT;
    END IF;
  END LOOP;

  IF v_team_idx < 0 THEN
    RAISE EXCEPTION 'Team not found in league roster';
  END IF;

  v_team := v_teams->v_team_idx;
  v_team_name := COALESCE(v_team->>'name', p_team_name);
  v_team_id := COALESCE(v_team->>'id', p_team_id);

  FOR v_group IN SELECT unnest(ARRAY['F','D','G']) LOOP
    FOR v_value, v_idx IN
      SELECT value, ordinality::integer - 1
      FROM jsonb_array_elements_text(COALESCE(v_team->'roster'->v_group, '[]'::jsonb)) WITH ORDINALITY AS t(value, ordinality)
    LOOP
      IF v_value = p_player_from_slug THEN
        v_from_group := v_group;
        v_from_index := v_idx;
        EXIT;
      END IF;
    END LOOP;
    EXIT WHEN v_from_group IS NOT NULL;
  END LOOP;

  IF v_from_group IS NULL THEN
    RAISE EXCEPTION 'Outgoing player is not on the active roster';
  END IF;

  FOR v_value, v_idx IN
    SELECT value, ordinality::integer - 1
    FROM jsonb_array_elements_text(COALESCE(v_team->'roster'->'B', '[]'::jsonb)) WITH ORDINALITY AS t(value, ordinality)
  LOOP
    IF v_value = p_player_to_slug THEN
      v_to_index := v_idx;
      EXIT;
    END IF;
  END LOOP;

  IF v_to_index IS NULL THEN
    RAISE EXCEPTION 'Incoming player must be on the bench';
  END IF;

  SELECT player_name, team, position, cap_hit
  INTO v_from_name, v_from_team, v_from_position, v_from_cap
  FROM nhl_players
  WHERE puckpedia_slug = p_player_from_slug
  LIMIT 1;

  SELECT player_name, team, position, cap_hit
  INTO v_to_name, v_to_team, v_to_position, v_to_cap
  FROM nhl_players
  WHERE puckpedia_slug = p_player_to_slug
  LIMIT 1;

  IF v_from_name IS NULL OR v_to_name IS NULL THEN
    RAISE EXCEPTION 'Player metadata missing for trade';
  END IF;

  v_to_norm := CASE
    WHEN upper(COALESCE(v_to_position, 'F')) LIKE '%G%' THEN 'G'
    WHEN upper(COALESCE(v_to_position, 'F')) = 'D' OR upper(COALESCE(v_to_position, 'F')) LIKE '%LD%' OR upper(COALESCE(v_to_position, 'F')) LIKE '%RD%' THEN 'D'
    ELSE 'F'
  END;

  IF v_to_norm <> v_from_group THEN
    RAISE EXCEPTION 'Position mismatch: % cannot replace %', v_to_norm, v_from_group;
  END IF;

  FOR v_group IN SELECT unnest(ARRAY['F','D','G']) LOOP
    FOR v_value IN SELECT value FROM jsonb_array_elements_text(COALESCE(v_team->'roster'->v_group, '[]'::jsonb)) AS t(value) LOOP
      SELECT COALESCE(cap_hit, 0) INTO v_idx FROM nhl_players WHERE puckpedia_slug = v_value LIMIT 1;
      v_current_cap := v_current_cap + COALESCE(v_idx, 0);
    END LOOP;
  END LOOP;

  v_cap_after := v_current_cap - COALESCE(v_from_cap, 0) + COALESCE(v_to_cap, 0);
  IF v_cap_after > 95500000 THEN
    RAISE EXCEPTION 'Trade rejected: cap would be $%.2fM (max $95.50M)', (v_cap_after::numeric / 1000000.0);
  END IF;

  -- Derive the active tenure start from prior incoming trade history.
  -- If no incoming record exists (pre-trade roster), fallback to trade timestamp.
  SELECT date_traded
  INTO v_hold_date
  FROM player_trades
  WHERE league_code = p_league_code
    AND player_to_slug = p_player_from_slug
    AND (
      (v_team_id IS NOT NULL AND team_id = v_team_id)
      OR team_name = v_team_name
      OR team_name_snapshot = v_team_name
    )
  ORDER BY date_traded DESC
  LIMIT 1;

  v_updated_team := jsonb_set(v_team, ARRAY['roster', v_from_group, v_from_index::text], to_jsonb(p_player_to_slug::text), false);
  v_updated_team := jsonb_set(v_updated_team, ARRAY['roster', 'B', v_to_index::text], to_jsonb(p_player_from_slug::text), false);
  v_updated_teams := jsonb_set(v_teams, ARRAY[v_team_idx::text], v_updated_team, false);

  UPDATE pool_rosters
  SET data = jsonb_set(COALESCE(data, '{}'::jsonb), '{teams}', v_updated_teams, false),
      updated_at = p_date_traded
  WHERE league_code = p_league_code;

  INSERT INTO player_trades (
    league_code, team_id, team_name, team_name_snapshot,
    player_from_slug, player_to_slug,
    player_from_name, player_to_name,
    player_from_position, player_to_position,
    player_from_team, player_to_team,
    from_slot_group, from_slot_index, to_slot_group, to_slot_index,
    date_from_acquired, date_traded, points_accumulated_at_trade
  ) VALUES (
    p_league_code, v_team_id, v_team_name, v_team_name,
    p_player_from_slug, p_player_to_slug,
    v_from_name, v_to_name,
    CASE
      WHEN upper(COALESCE(v_from_position, 'F')) LIKE '%G%' THEN 'G'
      WHEN upper(COALESCE(v_from_position, 'F')) = 'D' OR upper(COALESCE(v_from_position, 'F')) LIKE '%LD%' OR upper(COALESCE(v_from_position, 'F')) LIKE '%RD%' THEN 'D'
      ELSE 'F'
    END,
    v_to_norm,
    v_from_team, v_to_team,
    v_from_group, v_from_index, 'B', v_to_index,
    COALESCE(v_hold_date, p_date_traded), p_date_traded, 0
  );

  RETURN jsonb_build_object(
    'ok', true,
    'team_id', v_team_id,
    'team_name', v_team_name,
    'cap_after', v_cap_after,
    'player_from_slug', p_player_from_slug,
    'player_to_slug', p_player_to_slug
  );
END;
$$;

-- ===== DISABLE RLS (Row Level Security) =====
-- CRITICAL: RLS must be disabled to allow public/anon access for trade operations
DROP POLICY IF EXISTS "Allow public read on player_trades" ON player_trades;
DROP POLICY IF EXISTS "Allow public insert on player_trades" ON player_trades;
DROP POLICY IF EXISTS "Allow public update on player_trades" ON player_trades;
DROP POLICY IF EXISTS "Allow public delete on player_trades" ON player_trades;

-- Disable RLS on trades table
ALTER TABLE player_trades DISABLE ROW LEVEL SECURITY;

-- CRITICAL: Grant ALL permissions to public and anon roles
-- This is necessary for browser-based access to work
GRANT ALL ON player_trades TO public;
GRANT ALL ON player_trades TO anon;

-- Grant function execution to both roles
GRANT EXECUTE ON FUNCTION execute_pool_trade(text, text, text, text, text, timestamp) TO public;
GRANT EXECUTE ON FUNCTION execute_pool_trade(text, text, text, text, text, timestamp) TO anon;

-- ===== OPTIONAL: Enable RLS with policies if needed =====
-- Uncomment the following if you want to enable RLS for security:

-- ALTER TABLE player_trades ENABLE ROW LEVEL SECURITY;


-- CREATE POLICY "Allow public read on player_trades"
--   ON player_trades
--   FOR SELECT
--   USING (true);

-- CREATE POLICY "Allow public insert on player_trades"
--   ON player_trades
--   FOR INSERT
--   WITH CHECK (true);





