/**
 * Unified finance proxy.
 * action=price   &symbols=TSX:MFC,SAP.DE  → TMX (CAD) or Finnhub+FX (non-TSX)
 * action=search  &q=manulife              → Finnhub search
 * action=details &symbol=TSX:MFC         → TMX GraphQL (dividends, sector)
 * action=profile &symbol=TSX:MFC         → Finnhub profile2
 * action=description &name=Manulife      → Wikipedia summary
 */

const FINNHUB_KEY = process.env.FINNHUB_API_KEY;

const TMX_URL = 'https://app-money.tmx.com/graphql';
const TMX_HEADERS = {
  'Content-Type': 'application/json',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Origin': 'https://money.tmx.com',
  'Referer': 'https://money.tmx.com/',
};

// European/other exchange suffixes that need Finnhub + FX conversion
const FOREIGN_SUFFIXES = ['.DE','.PA','.L','.AS','.MI','.SW','.BR','.MC','.HK','.AX','.T','.TYO'];

function isForeignTicker(ticker) {
  if (!ticker) return false;
  const u = ticker.toUpperCase();
  // TSX, TSX-V, or plain symbol → TMX
  if (u.startsWith('TSX:') || u.startsWith('TSX-V:') || u.endsWith('.TO') || u.endsWith('.V')) return false;
  // Has a known foreign exchange suffix
  return FOREIGN_SUFFIXES.some(s => u.endsWith(s));
}

// Strip exchange suffix to get base symbol for Finnhub (SAP.DE → SAP)
function toFinnhubBase(ticker) {
  const u = ticker.toUpperCase();
  for (const s of FOREIGN_SUFFIXES) {
    if (u.endsWith(s)) return u.slice(0, -s.length);
  }
  return u;
}

// Convert any ticker format to TMX symbol
function toTmx(ticker) {
  if (!ticker) return ticker;
  const t = ticker.toUpperCase();
  if (t.includes(':')) return t.split(':')[1];
  if (t.endsWith('.TO')) return t.replace('.TO', '');
  if (t.endsWith('.V'))  return t.replace('.V', '');
  return t;
}

// ── FX rate cache (USD→CAD) ───────────────────────────────────────────────
let _fxCache = null;
async function getUsdCad() {
  if (_fxCache && Date.now() - _fxCache.ts < 60 * 60 * 1000) return _fxCache.rate;
  try {
    const r = await fetch('https://open.er-api.com/v6/latest/USD', { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (r.ok) {
      const d = await r.json();
      const rate = d?.rates?.CAD;
      if (rate) { _fxCache = { rate, ts: Date.now() }; return rate; }
    }
  } catch(_) {}
  return _fxCache?.rate || 1.38; // fallback to approximate rate
}

async function tmxQuote(symbol) {
  const tmxSym = toTmx(symbol);
  const body = JSON.stringify({
    query: `query { getQuoteBySymbol(symbol: "${tmxSym}", locale: "en") {
      symbol name price priceChange close
      exDividendDate dividendPayDate dividendFrequency dividendYield dividendAmount dividendCurrency
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
async function fetchFinnhubPrice(symbol) {
  // For foreign tickers (SAP.DE → SAP), fetch from Finnhub and convert to CAD
  const base = toFinnhubBase(symbol);
  if (!FINNHUB_KEY) throw new Error('no finnhub key');
  const r = await fetch(`https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(base)}&token=${FINNHUB_KEY}`, {
    headers: { 'User-Agent': 'Mozilla/5.0' }
  });
  if (!r.ok) throw new Error(`finnhub ${r.status}`);
  const q = await r.json();
  if (!q.c) throw new Error('no data');
  const fxRate = await getUsdCad();
  const price = +(q.c * fxRate).toFixed(4);
  const prevClose = +(q.pc * fxRate).toFixed(4);
  const change = +(price - prevClose).toFixed(4);
  const changePct = prevClose ? +((change / prevClose) * 100).toFixed(4) : null;
  return { price, previousClose: prevClose, change, changePct, name: base, currency: 'CAD', source: 'NYSE+FX' };
}

async function handlePrice(req, res) {
  const raw = req.query.symbols || '';
  if (!raw) return res.status(400).json({ error: 'symbols param required' });
  const symbols = raw.split(',').map(s => s.trim()).filter(Boolean);
  const cacheKey = [...symbols].sort().join(',');
  const cached = _priceCache.get(cacheKey);
  if (cached && Date.now() - cached.ts < 5 * 60 * 1000) return res.status(200).json(cached.data);

  // Split: TMX symbols vs foreign symbols needing Finnhub
  const tmxSymbols = symbols.filter(s => !isForeignTicker(s));
  const foreignSymbols = symbols.filter(s => isForeignTicker(s));

  const data = {};

  // Fetch TMX prices in batch
  if (tmxSymbols.length) {
    const tmxKeys = tmxSymbols.map(toTmx);
    const body = JSON.stringify({
      query: `query { getQuoteForSymbols(symbols: ${JSON.stringify(tmxKeys)}) { symbol longname price priceChange prevClose } }`,
    });
    const r = await fetch(TMX_URL, { method: 'POST', headers: TMX_HEADERS, body });
    if (r.ok) {
      const json = await r.json();
      const quotes = json?.data?.getQuoteForSymbols || [];
      tmxSymbols.forEach(symbol => {
        const q = quotes.find(q => q.symbol === toTmx(symbol));
        if (!q || !q.price) { data[symbol] = { error: 'not found' }; return; }
        const change = q.price != null && q.prevClose != null ? +(q.price - q.prevClose).toFixed(4) : null;
        const changePct = q.prevClose ? +((change / q.prevClose) * 100).toFixed(4) : null;
        data[symbol] = { price: q.price, previousClose: q.prevClose, change, changePct, name: q.longname || symbol };
      });
    } else {
      tmxSymbols.forEach(s => { data[s] = { error: `TMX ${r.status}` }; });
    }
  }

  // Fetch foreign prices via Finnhub + FX
  await Promise.all(foreignSymbols.map(async symbol => {
    try {
      data[symbol] = await fetchFinnhubPrice(symbol);
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

  // Use Finnhub for search (free, reliable, TSX-aware)
  if (FINNHUB_KEY) {
    try {
      const url = `https://finnhub.io/api/v1/search?q=${encodeURIComponent(q)}&token=${FINNHUB_KEY}`;
      const r = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
      if (r.ok) {
        const json = await r.json();
        const data = (json.result || [])
          .filter(r => r.type === 'Common Stock' || r.type === 'ETP')
          .slice(0, 10)
          .map(r => {
            let symbol = r.symbol, exchange = 'NYSE/NASDAQ';
            if (r.symbol.endsWith('.TO'))  { symbol = 'TSX:' + r.symbol.replace('.TO', ''); exchange = 'TSX'; }
            else if (r.symbol.endsWith('.V')) { symbol = 'TSX-V:' + r.symbol.replace('.V', ''); exchange = 'TSX-V'; }
            return { symbol, name: r.description, exchange };
          })
          .sort((a, b) => {
            const aCA = a.exchange === 'TSX' || a.exchange === 'TSX-V';
            const bCA = b.exchange === 'TSX' || b.exchange === 'TSX-V';
            return aCA === bCA ? 0 : aCA ? -1 : 1;
          })
          .slice(0, 8);
        _searchCache.set(q, { ts: Date.now(), data });
        return res.status(200).json(data);
      }
    } catch(_) {}
  }

  // Fallback: try TMX direct symbol lookup
  try {
    const tmxSym = q.toUpperCase().replace(/^TSX:/, '').replace(/\.TO$/, '');
    const body = JSON.stringify({ query: `query { getQuoteBySymbol(symbol: "${tmxSym}", locale: "en") { symbol name } }` });
    const r = await fetch(TMX_URL, { method: 'POST', headers: TMX_HEADERS, body });
    const json = await r.json();
    const sym = json?.data?.getQuoteBySymbol;
    const data = sym?.symbol ? [{ symbol: `TSX:${sym.symbol}`, name: sym.name, exchange: 'TSX' }] : [];
    _searchCache.set(q, { ts: Date.now(), data });
    return res.status(200).json(data);
  } catch(_) {}

  return res.status(200).json([]);
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

    // Fetch sector from Finnhub profile2 in parallel
    let sector = '';
    if (FINNHUB_KEY) {
      try {
        const finnhubSym = toTmx(symbol); // MFC, ENB — TMX symbol works for Finnhub profile
        const fr = await fetch(`https://finnhub.io/api/v1/stock/profile2?symbol=${encodeURIComponent(finnhubSym)}&token=${FINNHUB_KEY}`, { headers: { 'User-Agent': 'Mozilla/5.0' } });
        if (fr.ok) { const fj = await fr.json(); sector = fj.finnhubIndustry || ''; }
      } catch(_) {}
    }

    const data = {
      annualDividend: q.dividendAmount ? +(q.dividendAmount * (freqMap[q.dividendFrequency] === 'monthly' ? 12 : freqMap[q.dividendFrequency] === 'quarterly' ? 4 : freqMap[q.dividendFrequency] === 'semi-annual' ? 2 : 1)).toFixed(4) : null,
      dividendFrequency: freqMap[q.dividendFrequency] || 'quarterly',
      dividendPayDate: q.dividendPayDate || null,  // e.g. "2026-06-19"
      exDividendDate: q.exDividendDate ? q.exDividendDate.slice(0, 10) : null,
      sector,
    };
    _detailsCache.set(symbol, { ts: Date.now(), data });
    return res.status(200).json(data);
  } catch(e) {
    return res.status(500).json({ error: e.message });
  }
}

// ── Description (Wikipedia) ───────────────────────────────────────────────
const _descCache = new Map();

async function fetchWikiSummary(name) {
  // Try direct title first, then search
  const slug = name.replace(/ /g, '_');
  const urls = [
    `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(slug)}`,
    `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(slug.replace(/_Inc\.?$|_Corp\.?$|_Ltd\.?$|_Limited$/, ''))}`,
  ];
  for (const url of urls) {
    const r = await fetch(url, { headers: { 'User-Agent': 'parieur-discipline-bot/1.0 (finance tracker)' } });
    if (r.ok) {
      const d = await r.json();
      if (d.extract && d.type !== 'disambiguation') {
        return { extract: d.extract, url: d.content_urls?.desktop?.page || null, thumbnail: d.thumbnail?.source || null };
      }
    }
  }
  // Fall back to Wikipedia search
  const searchUrl = `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(name + ' company')}&srlimit=1&format=json&origin=*`;
  const sr = await fetch(searchUrl, { headers: { 'User-Agent': 'parieur-discipline-bot/1.0' } });
  if (sr.ok) {
    const sj = await sr.json();
    const hit = sj?.query?.search?.[0];
    if (hit) {
      const r2 = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(hit.title)}`, { headers: { 'User-Agent': 'parieur-discipline-bot/1.0' } });
      if (r2.ok) {
        const d2 = await r2.json();
        if (d2.extract && d2.type !== 'disambiguation') return { extract: d2.extract, url: d2.content_urls?.desktop?.page || null, thumbnail: d2.thumbnail?.source || null };
      }
    }
  }
  return null;
}

async function handleDescription(req, res) {
  const name = (req.query.name || '').trim();
  if (!name) return res.status(400).json({ error: 'name param required' });
  const cached = _descCache.get(name);
  if (cached && Date.now() - cached.ts < 24 * 60 * 60 * 1000) return res.status(200).json(cached.data);
  try {
    const data = await fetchWikiSummary(name) || { extract: null };
    _descCache.set(name, { ts: Date.now(), data });
    return res.status(200).json(data);
  } catch(e) {
    return res.status(200).json({ extract: null });
  }
}

// ── Profile ───────────────────────────────────────────────────────────────
const _profileCache = new Map();

async function handleProfile(req, res) {
  const symbol = (req.query.symbol || '').trim();
  if (!symbol) return res.status(400).json({ error: 'symbol param required' });
  const cached = _profileCache.get(symbol);
  if (cached && Date.now() - cached.ts < 60 * 60 * 1000) return res.status(200).json(cached.data);

  if (!FINNHUB_KEY) return res.status(200).json({ error: 'no api key' });

  const tmxSym = toTmx(symbol);
  try {
    const [profileRes, metricsRes, quoteRes] = await Promise.allSettled([
      fetch(`https://finnhub.io/api/v1/stock/profile2?symbol=${encodeURIComponent(tmxSym)}&token=${FINNHUB_KEY}`, { headers: { 'User-Agent': 'Mozilla/5.0' } }),
      fetch(`https://finnhub.io/api/v1/stock/metric?symbol=${encodeURIComponent(tmxSym)}&metric=all&token=${FINNHUB_KEY}`, { headers: { 'User-Agent': 'Mozilla/5.0' } }),
      fetch(`https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(tmxSym)}&token=${FINNHUB_KEY}`, { headers: { 'User-Agent': 'Mozilla/5.0' } }),
    ]);

    const profile = profileRes.status === 'fulfilled' && profileRes.value.ok ? await profileRes.value.json() : {};
    const metricsData = metricsRes.status === 'fulfilled' && metricsRes.value.ok ? await metricsRes.value.json() : {};
    const quote = quoteRes.status === 'fulfilled' && quoteRes.value.ok ? await quoteRes.value.json() : {};
    const m = metricsData.metric || {};

    const data = {
      name: profile.name || tmxSym,
      ticker: profile.ticker || tmxSym,
      logo: profile.logo || null,
      exchange: profile.exchange || '',
      country: profile.country || '',
      currency: profile.currency || 'CAD',
      industry: profile.finnhubIndustry || '',
      website: profile.weburl || null,
      ipo: profile.ipo || null,
      marketCap: profile.marketCapitalization ? +(profile.marketCapitalization).toFixed(2) : null,
      sharesOutstanding: profile.shareOutstanding || null,
      // Quote
      price: quote.c || null,
      high52: m['52WeekHigh'] || null,
      low52: m['52WeekLow'] || null,
      // Valuation
      pe: m.peBasicExclExtraTTM ? +m.peBasicExclExtraTTM.toFixed(2) : null,
      pb: m.pbAnnual ? +m.pbAnnual.toFixed(2) : null,
      eps: m.epsBasicExclExtraItemsAnnual ? +m.epsBasicExclExtraItemsAnnual.toFixed(2) : null,
      beta: m.beta ? +m.beta.toFixed(2) : null,
      dividendYield: m.dividendYieldIndicatedAnnual ? +m.dividendYieldIndicatedAnnual.toFixed(2) : null,
      dividendPerShare: m.dividendPerShareAnnual ? +m.dividendPerShareAnnual.toFixed(2) : null,
    };

    _profileCache.set(symbol, { ts: Date.now(), data });
    return res.status(200).json(data);
  } catch(e) {
    return res.status(500).json({ error: e.message });
  }
}

// ── Router ────────────────────────────────────────────────────────────────
const _sparklineCache = new Map();

async function handleSparkline(req, res) {
  const raw = req.query.symbols || '';
  if (!raw) return res.status(400).json({ error: 'symbols param required' });
  const symbols = raw.split(',').map(s => s.trim()).filter(Boolean);
  const cacheKey = [...symbols].sort().join(',');
  const cached = _sparklineCache.get(cacheKey);
  if (cached && Date.now() - cached.ts < 60 * 60 * 1000) return res.status(200).json(cached.data);

  const data = {};
  const tmxSymbols = symbols.filter(s => !isForeignTicker(s));
  const foreignSymbols = symbols.filter(s => isForeignTicker(s));

  // TMX: getTimeSeriesData for last 10 trading days (gives ~7 data points after weekends)
  if (tmxSymbols.length) {
    await Promise.all(tmxSymbols.map(async symbol => {
      try {
        const tmxSym = toTmx(symbol);
        const body = JSON.stringify({
          query: `query { getTimeSeriesData(symbol: "${tmxSym}", dateSince: "", dateUntil: "", range: "1M", interval: "day") { dateTime open high low close volume } }`,
        });
        const r = await fetch(TMX_URL, { method: 'POST', headers: TMX_HEADERS, body });
        if (!r.ok) return;
        const json = await r.json();
        const series = json?.data?.getTimeSeriesData || [];
        const closes = series.slice(-10).map(d => d.close).filter(v => v != null);
        if (closes.length >= 2) data[symbol] = closes;
      } catch(_) {}
    }));
  }

  // Finnhub candle for foreign tickers
  if (foreignSymbols.length && FINNHUB_KEY) {
    const fxRate = await getUsdCad();
    const to = Math.floor(Date.now() / 1000);
    const from = to - 14 * 24 * 3600; // 14 days back
    await Promise.all(foreignSymbols.map(async symbol => {
      try {
        const base = toFinnhubBase(symbol);
        const r = await fetch(`https://finnhub.io/api/v1/stock/candle?symbol=${base}&resolution=D&from=${from}&to=${to}&token=${FINNHUB_KEY}`, {
          headers: { 'User-Agent': 'Mozilla/5.0' }
        });
        if (!r.ok) return;
        const json = await r.json();
        if (json.s !== 'ok' || !json.c?.length) return;
        const closes = json.c.slice(-10).map(v => +(v * fxRate).toFixed(2));
        if (closes.length >= 2) data[symbol] = closes;
      } catch(_) {}
    }));
  }

  _sparklineCache.set(cacheKey, { data, ts: Date.now() });
  return res.status(200).json(data);
}


  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });
  try {
    const action = req.query.action;
    if (action === 'price')       return await handlePrice(req, res);
    if (action === 'search')      return await handleSearch(req, res);
    if (action === 'details')     return await handleDetails(req, res);
    if (action === 'profile')     return await handleProfile(req, res);
    if (action === 'sparkline')   return await handleSparkline(req, res);
    if (action === 'description') return await handleDescription(req, res);
    return res.status(400).json({ error: 'action required: price | search | details' });
  } catch(e) {
    return res.status(500).json({ error: e.message });
  }
};
