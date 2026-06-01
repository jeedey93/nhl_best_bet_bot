-- ============================================================
-- 2026 NHL Draft Pool Schema
-- Run in Supabase SQL Editor
-- ============================================================

-- 1. Draft pools table
CREATE TABLE IF NOT EXISTS draft_pools (
  id           bigserial PRIMARY KEY,
  code         text NOT NULL UNIQUE,
  name         text,
  actual_picks jsonb,        -- {pick#: prospect_rank} — set after the real draft
  created_at   timestamptz DEFAULT now()
);

-- 2. Participant entries
CREATE TABLE IF NOT EXISTS draft_pool_entries (
  id               bigserial PRIMARY KEY,
  pool_code        text NOT NULL REFERENCES draft_pools(code) ON DELETE CASCADE,
  participant_name text NOT NULL,
  picks            jsonb NOT NULL DEFAULT '{}',  -- {pick#: prospect_rank}
  pick_count       int  NOT NULL DEFAULT 0,
  submitted_at     timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now(),
  UNIQUE (pool_code, participant_name)
);

CREATE INDEX IF NOT EXISTS idx_draft_pool_entries_pool ON draft_pool_entries(pool_code);

-- 3. Seed the single global pool
INSERT INTO draft_pools (code, name)
VALUES ('DRAFT2026', '2026 NHL Draft Pool')
ON CONFLICT (code) DO NOTHING;
