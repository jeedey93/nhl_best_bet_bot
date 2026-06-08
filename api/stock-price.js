/**
 * Serverless proxy for Yahoo Finance stock prices.
 * Uses the chart API (v8/finance/chart) which works without auth.
 * GET /api/stock-price?symbols=MFC.TO,ENB.TO
 * Returns { "MFC.TO": { price, previousClose, change, changePct, name }, ... }
 */

const CACHE_TTL = 5 * 60 * 1000; // 5 min
const _cache = new Map();

async function fetchSymbol(symbol) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=1d`;
  const r = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'application/json',
    },
  });
  if (!r.ok) throw new Error(`${r.status}`);
  const json = await r.json();
  const meta = json?.chart?.result?.[0]?.meta;
  if (!meta) throw new Error('no meta');
  const price = meta.regularMarketPrice ?? null;
  const previousClose = meta.chartPreviousClose ?? meta.previousClose ?? null;
  const change = price != null && previousClose != null ? price - previousClose : null;
  const changePct = previousClose ? (change / previousClose) * 100 : null;
  return { price, previousClose, change, changePct, name: meta.longName || meta.shortName || symbol };
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const raw = req.query.symbols || '';
  if (!raw) return res.status(400).json({ error: 'symbols param required' });

  const symbols = raw.split(',').map(s => s.trim()).filter(Boolean);
  const cacheKey = [...symbols].sort().join(',');
  const cached = _cache.get(cacheKey);
  if (cached && Date.now() - cached.ts < CACHE_TTL) return res.status(200).json(cached.data);

  const data = {};
  await Promise.all(symbols.map(async symbol => {
    try {
      data[symbol] = await fetchSymbol(symbol);
    } catch (e) {
      data[symbol] = { error: e.message };
    }
  }));

  _cache.set(cacheKey, { ts: Date.now(), data });
  return res.status(200).json(data);
};
