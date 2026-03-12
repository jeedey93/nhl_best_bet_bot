# Daily Picks Table Generator

This script generates the daily picks table for the `daily-picks.html` page by parsing NHL and NBA prediction files.

## Usage

```bash
python3 scripts/generate_daily_picks_table.py
```

## What it does

1. **Finds the latest prediction files** for today's date from:
   - `data/predictions/nhl/daily_runs/nhl_daily_predictions_YYYY-MM-DD_12pm.txt`
   - `data/predictions/nba/daily_runs/nba_daily_predictions_YYYY-MM-DD_12pm.txt`
   - Falls back to 7am files or yesterday's 3pm if today's aren't found

2. **Parses the prediction files** and extracts:
   - Bet of the Day
   - Other Recommended Plays
   - For each pick: game matchup, pick type, odds, confidence, reasoning

3. **Updates `docs/daily-picks.html`** with JavaScript data containing all picks

## Pick Format

The script parses picks in these formats:

```
Boston Bruins ML vs Los Angeles Kings @ 1.69
Minnesota Timberwolves +2.5 vs Los Angeles Clippers @ 1.91
Toronto Maple Leafs vs Montréal Canadiens Over 6.5 @ 1.90
```

## Output

Generates JavaScript data structure:
```javascript
const picks = {
  nhl: [
    {
      game: 'Team A @ Team B',
      pick: 'Pick description',
      odds: '-145' or '+120',
      betType: 'moneyline' | 'spread' | 'total',
      confidence: 'High' | 'Medium' | 'Low' | 'Very High',
      stars: '⭐⭐⭐⭐',
      reasoning: 'Brief explanation...',
      time: 'TBD'
    }
  ],
  nba: [...]
};
```

## Integration with GitHub Actions

Add to your daily predictions workflow (after predictions are generated):

```yaml
- name: Generate daily picks table
  run: python3 scripts/generate_daily_picks_table.py

- name: Commit daily picks table
  run: |
    git add docs/daily-picks.html
    git commit -m "Update daily picks table for $(date +%Y-%m-%d)" || echo "No changes"
```

## Features

- Converts decimal odds to American odds format
- Determines bet type automatically (moneyline, spread, total)
- Extracts confidence levels and converts to star ratings
- Handles both NHL and NBA prediction file formats
- Truncates reasoning to 200 characters for table display
- Mobile-responsive design with color-coded sports

## Troubleshooting

If no picks appear:
1. Check if prediction files exist for today's date
2. Verify file format matches expected structure
3. Check console output for parsing errors

The script will create `docs/daily-picks-data.js` as a fallback if it can't update the HTML directly.
