/**
 * Finance portfolio snapshot endpoint.
 * Called by GitHub Actions daily after market close.
 * POST /api/finance-snapshot
 * Body: { secret: "..." }  — must match SNAPSHOT_SECRET env var
 *
 * Fetches all portfolios → all holdings → current prices from TMX,
 * computes per-portfolio summary + per-holding breakdown,
 * upserts into finance_snapshots (unique on portfolio_id + snapshot_date).
 */

const SUPABASE_URL = process.env.SUPABASE_URL || 'https://fifurqlitkywtmhgtzeu.supabase.co';
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY; // service role key (bypasses RLS)
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZpZnVycWxpdGt5d3RtaGd0emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MDIyMjQsImV4cCI6MjA5MjI3ODIyNH0.KPVPj1qwbSJJMyLR_-AhDcRs0vi2sUU6qbFQ-kH53C0';
const SNAPSHOT_SECRET = process.env.SNAPSHOT_SECRET; // optional — if set, requests must include it

const TMX_URL = 'https://app-money.tmx.com/graphql';
const TMX_HEADERS = {
  'Content-Type': 'application/json',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
  'Origin': 'https://money.tmx.com',
  'Referer': 'https://money.tmx.com/',
};

function sbHeaders(useService = false) {
  const key = (useService && SUPABASE_SERVICE_KEY) ? SUPABASE_SERVICE_KEY : SUPABASE_ANON_KEY;
  return { 'apikey': key, 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json' };
}

function toTmx(ticker) {
  if (!ticker) return ticker;
  const u = ticker.toUpperCase();
  if (u.startsWith('TSX:')) return u.replace('TSX:', '');
  if (u.startsWith('TSX-V:')) return u.replace('TSX-V:', '');
  if (u.includes(':')) return u.split(':')[1];
  return u;
}

async function fetchPricesBatch(tickers) {
  const tmxSymbols = tickers.map(toTmx);
  const body = JSON.stringify({
    query: `query { getQuoteForSymbols(symbols: ${JSON.stringify(tmxSymbols)}) { symbol longname price priceChange prevClose } }`,
  });
  const r = await fetch(TMX_URL, { method: 'POST', headers: TMX_HEADERS, body });
  if (!r.ok) throw new Error(`TMX ${r.status}`);
  const json = await r.json();
  const quotes = json?.data?.getQuoteForSymbols || [];
  const map = {};
  tickers.forEach(t => {
    const q = quotes.find(q => q.symbol === toTmx(t));
    if (q?.price) map[t] = { price: q.price, prevClose: q.prevClose, change: q.priceChange, name: q.longname || t };
  });
  return map;
}

async function sbGet(path) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, { headers: sbHeaders(true) });
  if (!r.ok) throw new Error(`Supabase GET ${r.status}: ${await r.text()}`);
  return r.json();
}

async function sbUpsert(table, body) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: 'POST',
    headers: { ...sbHeaders(true), 'Prefer': 'resolution=merge-duplicates,return=minimal' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Supabase upsert ${r.status}: ${await r.text()}`);
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // Auth check — only enforced if SNAPSHOT_SECRET env var is set
  const { secret } = req.body || {};
  if (SNAPSHOT_SECRET && secret !== SNAPSHOT_SECRET) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD in UTC

    // Fetch all portfolios and holdings
    const [portfolios, allHoldings] = await Promise.all([
      sbGet('finance_portfolios?select=id,name'),
      sbGet('finance_holdings?select=portfolio_id,ticker,shares,avg_price,annual_dividend,company_name,sector'),
    ]);

    if (!allHoldings.length) return res.status(200).json({ message: 'No holdings found', date: today });

    // Fetch prices for all unique tickers
    const tickers = [...new Set(allHoldings.map(h => h.ticker).filter(Boolean))];
    const prices = await fetchPricesBatch(tickers);

    const snapshots = [];
    const results = {};

    for (const portfolio of portfolios) {
      const holdings = allHoldings.filter(h => h.portfolio_id === portfolio.id);
      if (!holdings.length) continue;

      let totalValue = 0, totalCost = 0, totalDayChange = 0;
      const holdingsSnapshot = holdings.map(h => {
        const cost = (h.shares || 0) * (h.avg_price || 0);
        const p = prices[h.ticker];
        const marketValue = p ? (h.shares || 0) * p.price : cost;
        const dayChange = p ? (h.shares || 0) * p.change : 0;
        const overallGain = marketValue - cost;
        totalCost += cost;
        totalValue += marketValue;
        totalDayChange += dayChange;
        return {
          ticker: h.ticker,
          company_name: h.company_name,
          sector: h.sector,
          shares: h.shares,
          avg_price: h.avg_price,
          price: p?.price || null,
          market_value: +marketValue.toFixed(2),
          day_change: +dayChange.toFixed(2),
          overall_gain: +overallGain.toFixed(2),
          overall_gain_pct: cost > 0 ? +((overallGain / cost) * 100).toFixed(2) : 0,
        };
      });

      const gain = totalValue - totalCost;
      const snapshot = {
        portfolio_id: portfolio.id,
        snapshot_date: today,
        total_value: +totalValue.toFixed(2),
        total_cost: +totalCost.toFixed(2),
        day_change: +totalDayChange.toFixed(2),
        day_change_pct: totalValue > 0 ? +((totalDayChange / (totalValue - totalDayChange)) * 100).toFixed(4) : 0,
        gain: +gain.toFixed(2),
        gain_pct: totalCost > 0 ? +((gain / totalCost) * 100).toFixed(4) : 0,
        holdings_json: holdingsSnapshot,
      };
      snapshots.push(snapshot);
      results[portfolio.name] = {
        value: snapshot.total_value,
        day_change: snapshot.day_change,
        gain_pct: snapshot.gain_pct,
        holdings: holdingsSnapshot.length,
      };
    }

    // Upsert all snapshots
    if (snapshots.length) await sbUpsert('finance_snapshots', snapshots);

    return res.status(200).json({
      success: true,
      date: today,
      portfolios_snapshotted: snapshots.length,
      results,
    });
  } catch (e) {
    console.error('Snapshot error:', e);
    return res.status(500).json({ error: e.message });
  }
};
