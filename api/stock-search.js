/**
 * Serverless proxy for Yahoo Finance symbol search (autocomplete).
 * GET /api/stock-search?q=MFC
 * Returns [{ symbol, name, exchange, type }, ...]
 */

const CACHE_TTL = 60 * 1000; // 1 min
const _cache = new Map();

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const q = (req.query.q || '').trim();
  if (!q || q.length < 1) return res.status(200).json([]);

  const cached = _cache.get(q);
  if (cached && Date.now() - cached.ts < CACHE_TTL) return res.status(200).json(cached.data);

  try {
    const url = `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=8&newsCount=0&enableFuzzyQuery=false&enableCb=false`;
    const response = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (!response.ok) throw new Error(`Yahoo returned ${response.status}`);
    const json = await response.json();
    const quotes = json?.finance?.result?.[0]?.quotes || [];
    const data = quotes
      .filter(q => q.quoteType === 'EQUITY' || q.quoteType === 'ETF' || q.quoteType === 'MUTUALFUND')
      .map(q => ({
        symbol: q.symbol,
        name: q.longname || q.shortname || q.symbol,
        exchange: q.exchDisp || q.exchange || '',
        type: q.quoteType || '',
      }));
    _cache.set(q, { ts: Date.now(), data });
    return res.status(200).json(data);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
