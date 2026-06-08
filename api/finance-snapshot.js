/**
 * Finance portfolio snapshot endpoint.
 * Called by GitHub Actions daily after market close.
 * POST /api/finance-snapshot
 * Body: { secret: "..." }  — must match SNAPSHOT_SECRET env var
 *
 * Fetches all portfolios → all holdings → current prices from TMX (TSX)
 * or Finnhub+FX (foreign/non-TSX), computes per-portfolio summary +
 * per-account breakdown + per-holding detail,
 * upserts into finance_snapshots (unique on portfolio_id + snapshot_date).
 */

const SUPABASE_URL = process.env.SUPABASE_URL || 'https://fifurqlitkywtmhgtzeu.supabase.co';
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZpZnVycWxpdGt5d3RtaGd0emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MDIyMjQsImV4cCI6MjA5MjI3ODIyNH0.KPVPj1qwbSJJMyLR_-AhDcRs0vi2sUU6qbFQ-kH53C0';
const SNAPSHOT_SECRET = process.env.SNAPSHOT_SECRET;
const FINNHUB_KEY = process.env.FINNHUB_API_KEY;

const TMX_URL = 'https://app-money.tmx.com/graphql';
const TMX_HEADERS = {
  'Content-Type': 'application/json',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
  'Origin': 'https://money.tmx.com',
  'Referer': 'https://money.tmx.com/',
};

const FOREIGN_SUFFIXES = ['.DE','.PA','.L','.AS','.MI','.SW','.BR','.MC','.HK','.AX','.T','.TYO'];

function isForeignTicker(ticker) {
  if (!ticker) return false;
  const u = ticker.toUpperCase();
  if (u.startsWith('TSX:') || u.startsWith('TSX-V:') || u.endsWith('.TO') || u.endsWith('.V')) return false;
  return FOREIGN_SUFFIXES.some(s => u.endsWith(s));
}

function toFinnhubBase(ticker) {
  const u = ticker.toUpperCase();
  for (const s of FOREIGN_SUFFIXES) { if (u.endsWith(s)) return u.slice(0, -s.length); }
  return u;
}

function toTmx(ticker) {
  if (!ticker) return ticker;
  const u = ticker.toUpperCase();
  if (u.startsWith('TSX:')) return u.replace('TSX:', '');
  if (u.startsWith('TSX-V:')) return u.replace('TSX-V:', '');
  if (u.includes(':')) return u.split(':')[1];
  return u;
}

async function getUsdCad() {
  try {
    const r = await fetch('https://open.er-api.com/v6/latest/USD', { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (r.ok) { const d = await r.json(); const rate = d?.rates?.CAD; if (rate) return rate; }
  } catch(_) {}
  return 1.38;
}

async function fetchFinnhubPrice(symbol, fxRate) {
  const base = toFinnhubBase(symbol);
  if (!FINNHUB_KEY) throw new Error('no finnhub key');
  const r = await fetch(`https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(base)}&token=${FINNHUB_KEY}`, {
    headers: { 'User-Agent': 'Mozilla/5.0' }
  });
  if (!r.ok) throw new Error(`finnhub ${r.status}`);
  const q = await r.json();
  if (!q.c) throw new Error('no data');
  const price = +(q.c * fxRate).toFixed(4);
  const prevClose = +(q.pc * fxRate).toFixed(4);
  const change = +(price - prevClose).toFixed(4);
  const changePct = prevClose ? +((change / prevClose) * 100).toFixed(4) : null;
  return { price, prevClose, change, changePct };
}

async function fetchPricesBatch(tickers) {
  const tmxTickers = tickers.filter(t => !isForeignTicker(t));
  const foreignTickers = tickers.filter(t => isForeignTicker(t));
  const map = {};

  // TMX batch for TSX tickers
  if (tmxTickers.length) {
    const tmxSymbols = tmxTickers.map(toTmx);
    const body = JSON.stringify({
      query: `query { getQuoteForSymbols(symbols: ${JSON.stringify(tmxSymbols)}) { symbol longname price priceChange prevClose } }`,
    });
    const r = await fetch(TMX_URL, { method: 'POST', headers: TMX_HEADERS, body });
    if (r.ok) {
      const json = await r.json();
      const quotes = json?.data?.getQuoteForSymbols || [];
      tmxTickers.forEach(t => {
        const q = quotes.find(q => q.symbol === toTmx(t));
        if (q?.price) map[t] = { price: q.price, prevClose: q.prevClose, change: q.priceChange, name: q.longname || t };
      });
    }
  }

  // Finnhub + FX for foreign tickers
  if (foreignTickers.length) {
    const fxRate = await getUsdCad();
    await Promise.all(foreignTickers.map(async t => {
      try {
        const p = await fetchFinnhubPrice(t, fxRate);
        map[t] = { price: p.price, prevClose: p.prevClose, change: p.change, name: toFinnhubBase(t) };
      } catch(e) {
        console.warn(`Finnhub failed for ${t}:`, e.message);
      }
    }));
  }

  return map;
}

function sbHeaders(useService = false) {
  const key = (useService && SUPABASE_SERVICE_KEY) ? SUPABASE_SERVICE_KEY : SUPABASE_ANON_KEY;
  return { 'apikey': key, 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json' };
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

  const { secret } = req.body || {};
  if (SNAPSHOT_SECRET && secret !== SNAPSHOT_SECRET) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    // Use Montreal time for the snapshot date
    const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Toronto' });

    // Fetch portfolios, accounts, and holdings (include account_id)
    const [portfolios, accounts, allHoldings] = await Promise.all([
      sbGet('finance_portfolios?select=id,name'),
      sbGet('finance_accounts?select=id,name,portfolio_id'),
      sbGet('finance_holdings?select=portfolio_id,account_id,ticker,shares,avg_price,annual_dividend,company_name,sector'),
    ]);

    if (!allHoldings.length) return res.status(200).json({ message: 'No holdings found', date: today });

    const tickers = [...new Set(allHoldings.map(h => h.ticker).filter(Boolean))];
    const prices = await fetchPricesBatch(tickers);

    const snapshots = [];
    const results = {};

    for (const portfolio of portfolios) {
      const holdings = allHoldings.filter(h => h.portfolio_id === portfolio.id);
      if (!holdings.length) continue;

      const portfolioAccounts = accounts.filter(a => a.portfolio_id === portfolio.id);
      const accountMap = Object.fromEntries(portfolioAccounts.map(a => [a.id, a.name]));

      let totalValue = 0, totalCost = 0, totalDayChange = 0;
      const accountSummaries = {};

      const holdingsSnapshot = holdings.map(h => {
        const cost = (h.shares || 0) * (h.avg_price || 0);
        const p = prices[h.ticker];
        const marketValue = p ? (h.shares || 0) * p.price : cost;
        const dayChange = p ? (h.shares || 0) * p.change : 0;
        const overallGain = marketValue - cost;
        totalCost += cost;
        totalValue += marketValue;
        totalDayChange += dayChange;

        // Per-account rollup
        const acctName = accountMap[h.account_id] || 'Other';
        if (!accountSummaries[acctName]) accountSummaries[acctName] = { value: 0, cost: 0, day_change: 0 };
        accountSummaries[acctName].value += marketValue;
        accountSummaries[acctName].cost += cost;
        accountSummaries[acctName].day_change += dayChange;

        return {
          ticker: h.ticker,
          company_name: h.company_name,
          sector: h.sector,
          account: acctName,
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
        day_change_pct: (totalValue - totalDayChange) > 0 ? +((totalDayChange / (totalValue - totalDayChange)) * 100).toFixed(4) : 0,
        gain: +gain.toFixed(2),
        gain_pct: totalCost > 0 ? +((gain / totalCost) * 100).toFixed(4) : 0,
        holdings_json: holdingsSnapshot,
        accounts_json: accountSummaries,
      };
      snapshots.push(snapshot);
      results[portfolio.name] = {
        total_value: snapshot.total_value,
        day_change: snapshot.day_change,
        day_change_pct: snapshot.day_change_pct,
        gain: snapshot.gain,
        gain_pct: snapshot.gain_pct,
        accounts: accountSummaries,
        holdings: holdingsSnapshot,
      };
    }

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
