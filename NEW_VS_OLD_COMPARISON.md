# New Prompt vs Old Prompt - Side-by-Side Comparison

## Test Date: March 15, 2026 (7am Run)

---

## NHL Predictions Comparison

### OLD PROMPT RESULTS
**Games Available**: 6 NHL games
**Picks Generated**: 5 plays (forced to fill quota)
**Confidence Distribution**: 4 High, 1 Medium
**Average Win Probability**: 60.6%

**Picks**:
1. **BET OF THE DAY**: Nashville vs Edmonton Over 6.5 @ 1.90 (High, 65%)
2. San Jose vs Ottawa Under 6.5 @ 1.90 (High, 60%)
3. Florida @ Seattle Under 6.0 @ 1.90 (High, 60%)
4. St. Louis @ Winnipeg Under 5.5 @ 1.87 (High, 60%)
5. Anaheim @ Montreal Over 6.5 @ 1.95 (Medium, 58%) - *Confidence reduced due to 3 consecutive losses on Montreal Overs*

**Issues Observed**:
- ❌ Forced 5 picks despite limited game slate
- ❌ 4 of 5 picks were totals (over-concentration)
- ❌ All goalies "unconfirmed" but still made high confidence picks
- ❌ Self-contradictory: Pick #5 mentions 3 consecutive losses but still recommends it
- ❌ Complex reasoning with many factors cited
- ❌ Montreal priority rule not triggered (no Montreal play recommended)

---

### NEW PROMPT RESULTS
**Games Available**: 6 NHL games
**Picks Generated**: 1 play (highly selective)
**Confidence Distribution**: 1 Medium
**Average Win Probability**: 55%

**Picks**:
1. **BET OF THE DAY**: Seattle Kraken ML vs Florida @ 2.05 (Medium, 55%)

**Improvements**:
- ✅ Selective approach - only 1 qualified play (no forced picks)
- ✅ Clear edge calculation: 55% estimated vs 48.78% implied = +6.22% edge
- ✅ Explicitly mentions goalie uncertainty and adjusts confidence accordingly
- ✅ Simple, systematic factor analysis (home ice, form, fatigue all listed)
- ✅ Honest about limitations ("goalies unconfirmed")
- ✅ Medium confidence appropriate given uncertainty
- ✅ Better odds value (2.05 vs mostly 1.87-1.95 in old picks)

**Key Difference**: 
Old prompt forced 5 picks by lowering standards. New prompt said "only 1 game has +5% edge" and stuck to discipline.

---

## NBA Predictions Comparison

### OLD PROMPT RESULTS
**Games Available**: 7 NBA games
**Picks Generated**: 5 plays
**Confidence Distribution**: Unknown (file was old prompt)

---

### NEW PROMPT RESULTS
**Games Available**: 7 NBA games
**Picks Generated**: 4 plays (selective, quality focused)
**Confidence Distribution**: 1 High, 3 Medium
**Average Win Probability**: 68%

**Picks**:
1. **BET OF THE DAY**: Cleveland Cavaliers -15.5 @ 1.98 (High, 78%)
   - Edge: Massive home/away gap (0.405), talent gap, motivation factor
   - Rationale: Elite home team (0.647) vs terrible road team (0.242)

2. New York Knicks -14.0 @ 1.94 (Medium, 68%)
   - Edge: 0.321 home/away gap, playoff team vs eliminated team
   - Note: Confidence reduced due to recent similar spread failure

3. Milwaukee Bucks -7.0 @ 1.95 (Medium, 64%)
   - Edge: Home advantage, 3-0 season series dominance, Pacers 0-10 streak
   - Note: Confidence reduced due to Bucks' poor recent form (2-8)

4. Oklahoma City Thunder -7.5 @ 1.95 (Medium, 62%)
   - Edge: Elite home team (0.800), exceptional recent form (9-1 last 10)
   - Note: Confidence reduced due to recent similar spread failure

**Improvements**:
- ✅ Clear edge identification (home/away gaps prominently featured)
- ✅ Explicit confidence adjustments with reasoning
- ✅ References specific stats (0.647 home%, 0.242 away%, etc.)
- ✅ Acknowledges historical pattern failures and adjusts accordingly
- ✅ Systematic factor breakdown (Factor 1, 2, 3, 4 applied)
- ✅ High confidence only on strongest play (78% vs rest at 62-68%)
- ✅ Target 2-4 plays achieved (made 4, not forced to 5)

---

## Key Differences Summary

### Selectivity
- **Old**: Forced 5 picks per day → marginal plays included
- **New**: Target 2-4 picks → only plays with +5% edge

### Edge Requirements
- **Old**: +3% minimum → allowed weak plays
- **New**: +5% minimum → higher bar for quality

### Analysis Complexity
- **Old**: 8-10 factors mentioned in justifications → confusing, hard to verify
- **New**: 4 core factors systematically applied → clear, verifiable

### Confidence Calibration
- **Old**: NHL had 4 High confidence picks despite goalie uncertainty
- **New**: NHL had 1 Medium confidence pick, honest about limitations

### Market Awareness
- **Old**: No mention of consensus lines or market efficiency
- **New**: Explicitly identifies home/away gaps the market may have mispriced

### Historical Learning
- **Old**: NHL Pick #5 mentioned 3 consecutive losses but still recommended it (contradictory)
- **New**: NBA Picks #2 and #4 reduced confidence due to recent spread failures (consistent)

---

## Expected Performance Difference

### Short-Term (Next 7 Days)
- **Fewer picks**: Old avg 5/day = 35 picks/week, New avg 2-3/day = 14-21 picks/week
- **Better edge**: Old avg edge ~4%, New avg edge ~7-8%
- **Win rate**: Should see improvement toward 52-55%

### Long-Term (Month 1+)
- **Old approach (48% win rate)**: -EV after juice
- **New approach (target 54%+)**: +EV, sustainable profit

---

## Conclusion

The new prompts demonstrate:
1. **Discipline**: Only betting when genuine edge exists
2. **Clarity**: Simple factor-based reasoning that's easy to verify
3. **Honesty**: Explicit about uncertainty and limitations
4. **Consistency**: Confidence adjustments aligned with stated concerns
5. **Market Respect**: Acknowledging that obvious edges are already priced in

The old prompts were trying too hard to find 5 picks per day, leading to forced, marginal plays. The new prompts prioritize quality over quantity, which is the foundation of profitable betting.
