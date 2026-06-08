/**
 * Serverless proxy for Yahoo Finance quote data.
 * GET /api/stock-price?symbols=MFC.TO,ENB.TO,PZA.TO
 * Returns { "MFC.TO": { price, previousClose, change, changePct, name }, ... }
 * 5-minute in-memory cache per symbol set.
 */

const CACHE_TTL = 5 * 60 * 1000;
const _cache = new Map(); // key: sorted symbols string → { ts, data }

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
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return res.status(200).json(cached.data);
  }

  try {
    const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(symbols.join(','))}&fields=regularMarketPrice,regularMarketPreviousClose,regularMarketChange,regularMarketChangePercent,shortName`;
    const response = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });
    if (!response.ok) throw new Error(`Yahoo Finance returned ${response.status}`);
    const json = await response.json();
    const quotes = json?.quoteResponse?.result || [];

    const data = {};
    for (const q of quotes) {
      data[q.symbol] = {
        price: q.regularMarketPrice ?? null,
        previousClose: q.regularMarketPreviousClose ?? null,
        change: q.regularMarketChange ?? null,
        changePct: q.regularMarketChangePercent ?? null,
        name: q.shortName ?? q.symbol,
      };
    }

    _cache.set(cacheKey, { ts: Date.now(), data });
    return res.status(200).json(data);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
