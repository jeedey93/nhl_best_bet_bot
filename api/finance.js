/**
 * Unified finance proxy.
 * action=price   &symbols=TSX:MFC,TSX:ENB   → TMX Money GraphQL (CAD, real-time TSX)
 * action=search  &q=manulife                → Finnhub search
 * action=details &symbol=TSX:MFC            → TMX Money GraphQL (dividends, sector)
 */

const FINNHUB_KEY = process.env.FINNHUB_API_KEY;

const TMX_URL = 'https://app-money.tmx.com/graphql';
const TMX_HEADERS = {
  'Content-Type': 'application/json',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Origin': 'https://money.tmx.com',
  'Referer': 'https://money.tmx.com/',
};

// Convert any ticker format to TMX symbol: "TSX:MFC" or "MFC.TO" → "MFC"
function toTmx(ticker) {
  if (!ticker) return ticker;
  const t = ticker.toUpperCase();
  if (t.includes(':')) return t.split(':')[1];       // TSX:MFC → MFC
  if (t.endsWith('.TO')) return t.replace('.TO', ''); // MFC.TO → MFC
  if (t.endsWith('.V'))  return t.replace('.V', '');  // SPB.V → SPB
  return t;
}

async function tmxQuote(symbol) {
  const tmxSym = toTmx(symbol);
  const body = JSON.stringify({
    query: `query { getQuoteBySymbol(symbol: "${tmxSym}", locale: "en") {
      symbol name price priceChange close
      exDividendDate dividendFrequency dividendYield dividendAmount dividendCurrency
    }}`,
  });
  const r = await fetch(TMX_URL, { method: 'POST', headers: TMX_HEADERS, body });
  if (!r.ok) throw new Error(`TMX ${r.status}`);
  const json = await r.json();
  const q = json?.data?.getQuoteBySymbol;
  if (!q || !q.price) throw new Error('no data');
  return q;
}

const _priceCache   = new Map();
const _searchCache  = new Map();
const _detailsCache = new Map();

// ── Price ─────────────────────────────────────────────────────────────────
async function handlePrice(req, res) {
  const raw = req.query.symbols || '';
  if (!raw) return res.status(400).json({ error: 'symbols param required' });
  const symbols = raw.split(',').map(s => s.trim()).filter(Boolean);
  const cacheKey = [...symbols].sort().join(',');
  const cached = _priceCache.get(cacheKey);
  if (cached && Date.now() - cached.ts < 5 * 60 * 1000) return res.status(200).json(cached.data);

  const data = {};
  await Promise.all(symbols.map(async symbol => {
    try {
      const q = await tmxQuote(symbol);
      const price = q.price;
      const previousClose = q.close;
      const change = price != null && previousClose != null ? +(price - previousClose).toFixed(4) : null;
      const changePct = previousClose ? +((change / previousClose) * 100).toFixed(4) : null;
      data[symbol] = { price, previousClose, change, changePct, name: q.name || symbol };
    } catch(e) {
      data[symbol] = { error: e.message };
    }
  }));

  _priceCache.set(cacheKey, { ts: Date.now(), data });
  return res.status(200).json(data);
}

// ── Search ────────────────────────────────────────────────────────────────
async function handleSearch(req, res) {
  const q = (req.query.q || '').trim();
  if (!q) return res.status(200).json([]);
  const cached = _searchCache.get(q);
  if (cached && Date.now() - cached.ts < 60 * 1000) return res.status(200).json(cached.data);

  if (!FINNHUB_KEY) return res.status(200).json([]);

  try {
    const url = `https://finnhub.io/api/v1/search?q=${encodeURIComponent(q)}&token=${FINNHUB_KEY}`;
    const r = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (!r.ok) return res.status(200).json([]);
    const json = await r.json();

    const data = (json.result || [])
      .filter(r => r.type === 'Common Stock' || r.type === 'ETP')
      // Prefer TSX (.TO) and common exchanges
      .slice(0, 10)
      .map(r => {
        // Convert Finnhub symbol to display format: MFC.TO → TSX:MFC
        let display = r.symbol;
        let exchange = '';
        if (r.symbol.endsWith('.TO'))  { display = 'TSX:' + r.symbol.replace('.TO', ''); exchange = 'TSX'; }
        else if (r.symbol.endsWith('.V')) { display = 'TSX-V:' + r.symbol.replace('.V', ''); exchange = 'TSX-V'; }
        else { exchange = 'NYSE/NASDAQ'; }
        return { symbol: display, yahooSymbol: r.symbol, name: r.description, exchange, type: r.type };
      });

    // Sort TSX results first
    data.sort((a, b) => {
      const aCA = a.exchange === 'TSX' || a.exchange === 'TSX-V';
      const bCA = b.exchange === 'TSX' || b.exchange === 'TSX-V';
      return aCA === bCA ? 0 : aCA ? -1 : 1;
    });

    _searchCache.set(q, { ts: Date.now(), data: data.slice(0, 8) });
    return res.status(200).json(data.slice(0, 8));
  } catch(e) {
    return res.status(200).json([]);
  }
}

// ── Details ───────────────────────────────────────────────────────────────
async function handleDetails(req, res) {
  const symbol = (req.query.symbol || '').trim();
  if (!symbol) return res.status(400).json({ error: 'symbol param required' });
  const cached = _detailsCache.get(symbol);
  if (cached && Date.now() - cached.ts < 60 * 60 * 1000) return res.status(200).json(cached.data);

  try {
    const q = await tmxQuote(symbol);
    const freqMap = { 'Monthly': 'monthly', 'Quarterly': 'quarterly', 'Semi-Annual': 'semi-annual', 'Annual': 'annual' };
    const data = {
      annualDividend: q.dividendAmount ? +(q.dividendAmount * (freqMap[q.dividendFrequency] === 'monthly' ? 12 : freqMap[q.dividendFrequency] === 'quarterly' ? 4 : freqMap[q.dividendFrequency] === 'semi-annual' ? 2 : 1)).toFixed(4) : null,
      dividendFrequency: freqMap[q.dividendFrequency] || 'quarterly',
      sector: '',
    };
    _detailsCache.set(symbol, { ts: Date.now(), data });
    return res.status(200).json(data);
  } catch(e) {
    return res.status(500).json({ error: e.message });
  }
}

// ── Router ────────────────────────────────────────────────────────────────
module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });
  try {
    const action = req.query.action;
    if (action === 'price')   return await handlePrice(req, res);
    if (action === 'search')  return await handleSearch(req, res);
    if (action === 'details') return await handleDetails(req, res);
    return res.status(400).json({ error: 'action required: price | search | details' });
  } catch(e) {
    return res.status(500).json({ error: e.message });
  }
};
