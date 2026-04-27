-- Hockey Pool Trade System - Supabase SQL Migration
-- This SQL creates the tables needed for the player hold/trade system

-- Player Holds Table
-- Tracks when players are acquired and points accumulated while held
CREATE TABLE IF NOT EXISTS player_holds (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamp DEFAULT now(),
  league_code text NOT NULL,
  team_id uuid NOT NULL,
  player_slug text NOT NULL,
  date_acquired timestamp NOT NULL,
  points_accumulated integer DEFAULT 0,

  CONSTRAINT unique_hold UNIQUE (league_code, team_id, player_slug)
);

CREATE INDEX idx_holds_league_team ON player_holds(league_code, team_id);
CREATE INDEX idx_holds_player ON player_holds(player_slug);

-- Player Trades Table
-- Historical record of trades between main roster and bench
CREATE TABLE IF NOT EXISTS player_trades (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamp DEFAULT now(),
  league_code text NOT NULL,
  team_id uuid NOT NULL,
  player_from_slug text NOT NULL,
  player_to_slug text NOT NULL,
  date_from_acquired timestamp NOT NULL,
  date_traded timestamp NOT NULL,
  points_accumulated_at_trade integer DEFAULT 0,

  CONSTRAINT valid_trade CHECK (player_from_slug != player_to_slug)
);

CREATE INDEX idx_trades_league_team ON player_trades(league_code, team_id);
CREATE INDEX idx_trades_from_player ON player_trades(player_from_slug);
CREATE INDEX idx_trades_to_player ON player_trades(player_to_slug);
CREATE INDEX idx_trades_date ON player_trades(date_traded);

-- Enable Row Level Security (optional, for multi-user security)
-- ALTER TABLE player_holds ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE player_trades ENABLE ROW LEVEL SECURITY;

-- Allow anonymous access for pool functionality
-- (configure based on your app's auth model)

