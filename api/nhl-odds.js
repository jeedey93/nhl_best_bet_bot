/**
 * Serverless proxy for NHL odds (The Odds API)
 * Caches odds for 12 hours to minimize API calls
 *
 * Deployment: Vercel Serverless Function
 */

const ODDS_API_KEY = process.env.ODDS_API_KEY;
const CACHE_DURATION = 12 * 60 * 60 * 1000; // 12 hours in milliseconds

// In-memory cache (resets on cold start, but that's fine for serverless)
let cachedOdds = null;
let cacheTimestamp = null;

module.exports = async (req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Check API key
    if (!ODDS_API_KEY) {
      console.error('ODDS_API_KEY environment variable not set');
      return res.status(500).json({
        error: 'Odds API key not configured',
        hint: 'Set ODDS_API_KEY in Vercel environment variables'
      });
    }

    // Check cache
    const now = Date.now();
    if (cachedOdds && cacheTimestamp && (now - cacheTimestamp < CACHE_DURATION)) {
      console.log('Returning cached odds (age: ' + Math.round((now - cacheTimestamp) / 1000 / 60) + ' minutes)');
      return res.status(200).json(cachedOdds);
    }

    console.log('Fetching fresh odds from The Odds API...');

    // Fetch from The Odds API
    const oddsUrl = `https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds/?apiKey=${ODDS_API_KEY}&regions=us&markets=h2h,totals&oddsFormat=decimal`;

    const oddsResponse = await fetch(oddsUrl);

    if (!oddsResponse.ok) {
      console.error('Odds API error:', oddsResponse.status, oddsResponse.statusText);
      return res.status(oddsResponse.status).json({
        error: `Odds API returned ${oddsResponse.status}`,
        details: oddsResponse.statusText
      });
    }

    const data = await oddsResponse.json();
    console.log(`Received ${data.length} games from Odds API`);

    // Process and simplify the data
    const processedOdds = data.map(game => {
      const bookmaker = game.bookmakers?.[0]; // Take first bookmaker

      if (!bookmaker) {
        return {
          home_team: game.home_team,
          away_team: game.away_team,
          commence_time: game.commence_time,
          home_odds: null,
          away_odds: null,
          totals: null
        };
      }

      const h2hMarket = bookmaker.markets?.find(m => m.key === 'h2h');
      const totalsMarket = bookmaker.markets?.find(m => m.key === 'totals');

      const homeOdds = h2hMarket?.outcomes?.find(o => o.name === game.home_team)?.price;
      const awayOdds = h2hMarket?.outcomes?.find(o => o.name === game.away_team)?.price;

      // Get the O/U point from the first outcome (Over or Under, both have the same point)
      const overUnder = totalsMarket?.outcomes?.[0]?.point;

      return {
        home_team: game.home_team,
        away_team: game.away_team,
        commence_time: game.commence_time,
        home_odds: homeOdds,
        away_odds: awayOdds,
        totals: overUnder
      };
    });

    // Cache the results
    cachedOdds = processedOdds;
    cacheTimestamp = now;

    console.log(`Fetched and cached ${processedOdds.length} games from Odds API`);

    return res.status(200).json(processedOdds);

  } catch (error) {
    console.error('Error fetching NHL odds:', error);
    return res.status(500).json({
      error: 'Failed to fetch NHL odds',
      message: error.message
    });
  }
};
