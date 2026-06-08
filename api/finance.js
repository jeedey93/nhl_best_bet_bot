/**
 * Unified Yahoo Finance proxy with cookie+crumb authentication.
 * Routes by ?action= param:
 *   action=price   &symbols=MFC.TO,ENB.TO
 *   action=search  &q=MFC
 *   action=details &symbol=MFC.TO
 */

const YF_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

// ── Crumb / cookie session (refreshed every 30 min) ───────────────────────
let _session = null; // { cookie, crumb, ts }

async function getSession() {
  if (_session && Date.now() - _session.ts < 30 * 60 * 1000) return _session;

  // Step 1: hit finance.yahoo.com to get consent cookie
  const consentRes = await fetch('https://finance.yahoo.com/', {
    headers: { 'User-Agent': YF_UA, 'Accept': 'text/html', 'Accept-Language': 'en-US,en;q=0.9' },
    redirect: 'follow',
  });
  const cookieHeader = consentRes.headers.get('set-cookie') || '';
  // Extract the A1 consent cookie
  const a1Match = cookieHeader.match(/A1=([^;]+)/);
  const cookie = a1Match ? `A1=${a1Match[1]}` : 'A1=d=AQABBBL';

  // Step 2: get crumb
  const crumbRes = await fetch('https://query1.finance.yahoo.com/v1/test/getcrumb', {
    headers: { 'User-Agent': YF_UA, 'Cookie': cookie, 'Accept': '*/*' },
  });
  const crumb = crumbRes.ok ? await crumbRes.text() : '';

  _session = { cookie, crumb, ts: Date.now() };
  return _session;
}

async function yfetch(url) {
  const { cookie, crumb } = await getSession();
  const sep = url.includes('?') ? '&' : '?';
  const fullUrl = crumb ? `${url}${sep}crumb=${encodeURIComponent(crumb)}` : url;
  const r = await fetch(fullUrl, {
    headers: {
      'User-Agent': YF_UA,
      'Accept': 'application/json',
      'Cookie': cookie,
      'Cache-Control': 'no-cache',
    },
  });
  if (r.status === 401 || r.status === 403) {
    // Session expired — force refresh on next call
    _session = null;
    throw new Error(`auth_${r.status}`);
  }
  return r;
}

const _priceCache   = new Map();
const _searchCache  = new Map();
const _detailsCache = new Map();

// ── Price ─────────────────────────────────────────────────────────────────
async function fetchSymbolPrice(symbol) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=1d`;
  const r = await yfetch(url);
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

async function handlePrice(req, res) {
  const raw = req.query.symbols || '';
  if (!raw) return res.status(400).json({ error: 'symbols param required' });
  const symbols = raw.split(',').map(s => s.trim()).filter(Boolean);
  const cacheKey = [...symbols].sort().join(',');
  const cached = _priceCache.get(cacheKey);
  if (cached && Date.now() - cached.ts < 5 * 60 * 1000) return res.status(200).json(cached.data);
  const data = {};
  await Promise.all(symbols.map(async s => {
    try { data[s] = await fetchSymbolPrice(s); } catch (e) { data[s] = { error: e.message }; }
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

  // Search both raw query and with .TO suffix for TSX stocks
  const queries = [q];
  if (!q.includes('.') && !q.includes(':')) queries.push(q + '.TO');

  const allQuotes = [];
  await Promise.all(queries.map(async term => {
    try {
      const url = `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(term)}&quotesCount=8&newsCount=0&enableFuzzyQuery=true`;
      const r = await yfetch(url);
      if (!r.ok) return;
      const json = await r.json();
      allQuotes.push(...(json?.quotes || []));
    } catch(_) {}
  }));

  const seen = new Set();
  const data = allQuotes
    .filter(r => r.isYahooFinance && ['EQUITY', 'ETF'].includes(r.quoteType))
    .filter(r => { if (seen.has(r.symbol)) return false; seen.add(r.symbol); return true; })
    .slice(0, 8)
    .map(r => ({ symbol: r.symbol, name: r.longname || r.shortname || r.symbol, exchange: r.exchDisp || r.exchange || '', type: r.quoteType || '', sector: r.sectorDisp || r.sector || '' }));

  _searchCache.set(q, { ts: Date.now(), data });
  return res.status(200).json(data);
}

// ── Details ───────────────────────────────────────────────────────────────
async function fetchDividendEvents(symbol) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=3mo&range=2y&events=dividends`;
  const r = await yfetch(url);
  if (!r.ok) throw new Error(`chart ${r.status}`);
  const json = await r.json();
  const divs = Object.values(json?.chart?.result?.[0]?.events?.dividends || {}).sort((a, b) => a.date - b.date);
  if (divs.length < 2) return { annualDividend: null, dividendFrequency: 'quarterly', sector: '' };
  const gaps = []; for (let i = 1; i < divs.length; i++) gaps.push((divs[i].date - divs[i-1].date) / 86400);
  const avgGap = gaps.reduce((a, b) => a + b, 0) / gaps.length;
  const freq = avgGap < 45 ? 'monthly' : avgGap < 120 ? 'quarterly' : avgGap < 270 ? 'semi-annual' : 'annual';
  const perYear = freq === 'monthly' ? 12 : freq === 'quarterly' ? 4 : freq === 'semi-annual' ? 2 : 1;
  return { annualDividend: Math.round(divs[divs.length - 1].amount * perYear * 100) / 100, dividendFrequency: freq };
}

async function fetchQuoteSummary(symbol) {
  const url = `https://query1.finance.yahoo.com/v11/finance/quoteSummary/${encodeURIComponent(symbol)}?modules=summaryDetail,assetProfile`;
  const r = await yfetch(url);
  if (!r.ok) throw new Error(`quoteSummary ${r.status}`);
  const json = await r.json();
  const result = json?.quoteSummary?.result?.[0] || {};
  const sd = result.summaryDetail || {}, ap = result.assetProfile || {};
  return { sector: ap.sector || '', industry: ap.industry || '', annualDividend: sd.dividendRate?.raw ?? sd.trailingAnnualDividendRate?.raw ?? null };
}

async function handleDetails(req, res) {
  const symbol = (req.query.symbol || '').trim();
  if (!symbol) return res.status(400).json({ error: 'symbol param required' });
  const cached = _detailsCache.get(symbol);
  if (cached && Date.now() - cached.ts < 60 * 60 * 1000) return res.status(200).json(cached.data);
  const [summaryResult, chartResult] = await Promise.allSettled([fetchQuoteSummary(symbol), fetchDividendEvents(symbol)]);
  const summary = summaryResult.status === 'fulfilled' ? summaryResult.value : {};
  const chart   = chartResult.status   === 'fulfilled' ? chartResult.value   : {};
  const data = { sector: summary.sector || '', industry: summary.industry || '', annualDividend: chart.annualDividend ?? summary.annualDividend ?? null, dividendFrequency: chart.dividendFrequency || 'quarterly' };
  _detailsCache.set(symbol, { ts: Date.now(), data });
  return res.status(200).json(data);
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
    return res.status(400).json({ error: 'action param required: price | search | details' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
