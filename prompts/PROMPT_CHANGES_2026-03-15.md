# Prompt Improvements - March 15, 2026

## Performance Context
- **Overall Win Rate**: 48.1% (74W-80L) - Below breakeven
- **NHL**: 45.2% (33-40) - Significantly underperforming
- **NBA**: 50.6% (41-40) - Marginally above 50%
- **Need**: 52-55%+ win rate to be profitable after juice/vig

## Key Changes Made

### 1. Increased Selectivity (Quality Over Quantity)
**Old**: Minimum +3% edge, target 5 plays per day
**New**: Minimum +5% edge, target 2-4 plays per day

**Rationale**: Forcing 5 picks per day leads to marginal plays with no real edge. Better to make fewer, higher-quality bets.

### 2. Simplified Analysis Framework
**Old**: 8-10 adjustment factors with complex sub-steps
**New**: 4 core factors with clear weights

**NHL Factors (by weight)**:
1. Goalie Matchup (35%) - Most important
2. Home Ice Advantage (30%)
3. Recent Form & Quality (20%)
4. Fatigue & Schedule (15%)

**NBA Factors (by weight)**:
1. Home Court Advantage (35%) - NBA home court is huge
2. Team Quality & Motivation (30%)
3. Recent Form & H2H (20%)
4. Fatigue & Schedule (15%)

**Rationale**: Too many factors compound errors. Focus on what actually matters.

### 3. Removed Forced Picks
**Old**: Montreal Canadiens priority rule forcing picks at +1% edge
**New**: No forced picks on any team

**Rationale**: Forcing picks on a mediocre team destroys expected value. Let the model pass when there's no edge.

### 4. Added Market Awareness
**New Features**:
- Detect consensus lines (4+ books within 0.02 odds)
- Flag market inefficiencies (books 0.08+ different from consensus)
- Avoid obvious narratives that market has already priced in

**Rationale**: You're competing against sharp bettors. The market knows about win streaks, star players, etc. Only bet when you have an edge the market missed.

### 5. Reduced Recency Bias
**Old**: Heavy weighting on last 5-10 games, multiple momentum adjustments
**New**: Balanced approach using goal/point differentials, cross-check with season stats

**Rationale**: Small sample sizes (5-10 games) are noisy. Hot/cold streaks often revert to mean.

### 6. Simplified Goalie Analysis (NHL)
**Old**: Complex multi-tier system, Last 5 weighted 60%, season 40%
**New**: Clear tier system based on Last 5 SV%, with season stats as sanity check

**Key Improvement**: Explicitly warn about variance - if Last 5 is hot but season is poor, reduce adjustment (regression coming).

### 7. Cleaner Probability Calculation
**Old**: Sum 6-8 adjustments with unclear priorities
**New**: Start at baseline (54% NHL home, 58% NBA home), apply 4 factors systematically

**Example (NHL)**:
```
Base: 54% (home team)
+ Factor 1 (Goalie): +7%
+ Factor 2 (Home Ice): +4%
+ Factor 3 (Form): +2%
+ Factor 4 (Fatigue): +4%
= 71% estimated probability
vs 58.8% implied (1.70 odds)
= 12.2% edge ✓
```

### 8. Streamlined Historical Self-Evaluation
**Old**: Multiple thresholds, complex conditions, separate paragraph in output
**New**: Simple pattern detection, only mention in specific play justification if relevant

**Rationale**: Historical review was adding noise. Simplified to focus on clear patterns (3+ consecutive losses, <45% win rate over 10+ plays).

## What Stayed The Same

- Output format (completely unchanged)
- BET OF THE DAY selection logic
- Confidence tiers and unit sizing
- Odds range (1.60-2.20)
- Data sources used
- Goalie name mention requirement (NHL)

## Expected Improvements

1. **Higher Win Rate**: More selective = fewer marginal picks = better results
2. **Better ROI**: Fewer plays but higher edge per play
3. **Less Overconfidence**: Simpler framework = fewer compounding errors
4. **Market-Aware**: Avoid betting into efficient consensus lines
5. **Regression Management**: Better handling of hot/cold streaks

## Backup Files Created

- `nhl_prompt_backup_20260315.txt` - Full backup of old NHL prompt
- `nba_prompt_backup_20260315.txt` - Full backup of old NBA prompt
- `nhl_prompt_old.txt` - Previous version before replacement
- `nba_prompt_old.txt` - Previous version before replacement

## Testing Recommendations

1. Run predictions for next 7 days with new prompts
2. Track number of plays per day (should be 2-4, not 5)
3. Monitor edge calculations (should average 7-10%, not 3-5%)
4. Compare win rate after 20+ picks to old prompt performance
5. Watch for "No qualified plays today" outputs (this is GOOD - means selectivity is working)

## Rollback Instructions

If new prompts perform worse after 20+ picks:

```bash
cd /Users/I854351/documents/parieur/parieur-discipline-bot/prompts
mv nhl_prompt.txt nhl_prompt_new_failed.txt
mv nhl_prompt_old.txt nhl_prompt.txt
mv nba_prompt.txt nba_prompt_new_failed.txt
mv nba_prompt_old.txt nba_prompt.txt
```
