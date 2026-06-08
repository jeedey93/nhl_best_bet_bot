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
  if (!q) return res.status(200).json([]);

  const cached = _cache.get(q);
  if (cached && Date.now() - cached.ts < CACHE_TTL) return res.status(200).json(cached.data);

  try {
    const url = `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=8&newsCount=0&enableFuzzyQuery=false&enableCb=false`;
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
      },
    });
    // 304 means Yahoo returned cached empty body — treat as no results
    if (response.status === 304) {
      _cache.set(q, { ts: Date.now(), data: [] });
      return res.status(200).json([]);
    }
    if (!response.ok) throw new Error(`Yahoo returned ${response.status}`);
    const json = await response.json();

    // Response shape: { quotes: [...] }  (top-level, not nested)
    const quotes = json?.quotes || json?.finance?.result?.[0]?.quotes || [];
    const data = quotes
      .filter(r => r.isYahooFinance && (r.quoteType === 'EQUITY' || r.quoteType === 'ETF' || r.quoteType === 'MUTUALFUND'))
      .slice(0, 8)
      .map(r => ({
        symbol: r.symbol,
        name: r.longname || r.shortname || r.symbol,
        exchange: r.exchDisp || r.exchange || '',
        type: r.quoteType || '',
        sector: r.sectorDisp || r.sector || '',
      }));

    _cache.set(q, { ts: Date.now(), data });
    return res.status(200).json(data);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
