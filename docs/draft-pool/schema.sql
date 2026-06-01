-- ============================================================
-- 2026 NHL Draft Pool Schema
-- Run in Supabase SQL Editor
-- ============================================================

-- 1. Draft pools (one per group of friends)
CREATE TABLE IF NOT EXISTS draft_pools (
  id           bigserial PRIMARY KEY,
  code         text NOT NULL UNIQUE,
  name         text,
  access_token text,
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

-- 3. Open read/write for now (add RLS later if needed)
-- Anyone with the pool code can read/write entries.
-- The actual_picks field on draft_pools is only updated by the organizer.
