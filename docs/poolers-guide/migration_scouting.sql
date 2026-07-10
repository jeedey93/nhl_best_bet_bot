-- Run this in the Supabase SQL editor to add the new scouting columns

alter table poolers_players
  add column if not exists risk        text,     -- 'Low' | 'Medium' | 'High'
  add column if not exists bust_alert  boolean default false,
  add column if not exists scouting    text,     -- extended 3-4 sentence analysis
  add column if not exists comp_player text,     -- e.g. "Plays like a young Backstrom"
  add column if not exists key_risks   text;     -- free text, e.g. "Injury history, linemate dependency"
