-- Hockey Pool Trade System - Supabase SQL Migration
-- This SQL creates the tables needed for the player hold/trade system

-- Player Holds Table
-- Tracks when players are acquired and points accumulated while held
CREATE TABLE IF NOT EXISTS player_holds (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamp DEFAULT now(),
  league_code text NOT NULL,
  team_name text NOT NULL,
  player_slug text NOT NULL,
  date_acquired timestamp NOT NULL,
  points_accumulated integer DEFAULT 0,

  CONSTRAINT unique_hold UNIQUE (league_code, team_name, player_slug)
);

CREATE INDEX idx_holds_league_team ON player_holds(league_code, team_name);
CREATE INDEX idx_holds_player ON player_holds(player_slug);

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

CREATE INDEX idx_trades_league_team ON player_trades(league_code, team_name);
CREATE INDEX idx_trades_from_player ON player_trades(player_from_slug);
CREATE INDEX idx_trades_to_player ON player_trades(player_to_slug);
CREATE INDEX idx_trades_date ON player_trades(date_traded);

-- ===== RLS POLICIES (Optional - only enable if using Row Level Security) =====
-- Uncomment the lines below if you want to enable RLS for security

-- ALTER TABLE player_holds ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE player_trades ENABLE ROW LEVEL SECURITY;

-- Create policies that allow anonymous public access (for your pool use case)
-- Note: Only uncomment these if you've enabled RLS above

-- CREATE POLICY "Allow public read on player_holds"
--   ON player_holds
--   FOR SELECT
--   USING (true);

-- CREATE POLICY "Allow public insert on player_holds"
--   ON player_holds
--   FOR INSERT
--   WITH CHECK (true);

-- CREATE POLICY "Allow public update on player_holds"
--   ON player_holds
--   FOR UPDATE
--   USING (true)
--   WITH CHECK (true);

-- CREATE POLICY "Allow public delete on player_holds"
--   ON player_holds
--   FOR DELETE
--   USING (true);

-- CREATE POLICY "Allow public read on player_trades"
--   ON player_trades
--   FOR SELECT
--   USING (true);

-- CREATE POLICY "Allow public insert on player_trades"
--   ON player_trades
--   FOR INSERT
--   WITH CHECK (true);

-- ===== END RLS POLICIES =====

-- If RLS is preventing inserts, you can also grant permissions directly:
-- GRANT ALL ON player_holds TO anon;
-- GRANT ALL ON player_trades TO anon;




