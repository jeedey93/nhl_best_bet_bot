/**
 * Serverless proxy for Yahoo Finance stock details (sector + dividend info).
 * GET /api/stock-details?symbol=MFC.TO
 * Returns { sector, industry, annualDividend, dividendFrequency }
 */

const CACHE_TTL = 60 * 60 * 1000; // 1 hour — this data changes rarely
const _cache = new Map();

const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept': 'application/json',
  'Cache-Control': 'no-cache',
  'Pragma': 'no-cache',
};

async function fetchQuoteSummary(symbol) {
  const url = `https://query1.finance.yahoo.com/v11/finance/quoteSummary/${encodeURIComponent(symbol)}?modules=summaryDetail,assetProfile`;
  const r = await fetch(url, { headers: HEADERS });
  if (!r.ok) throw new Error(`quoteSummary ${r.status}`);
  const json = await r.json();
  const result = json?.quoteSummary?.result?.[0] || {};
  const sd = result.summaryDetail || {};
  const ap = result.assetProfile || {};

  const annualDividend = sd.dividendRate?.raw ?? sd.trailingAnnualDividendRate?.raw ?? null;

  // Infer frequency from dividend payment history
  // payFrequency: 1=annual, 2=semi, 4=quarterly, 12=monthly
  const payFreq = sd.payoutRatio ? null : null; // not directly available
  let dividendFrequency = 'quarterly'; // safe default for most stocks
  if (annualDividend && sd.dividendYield?.raw) {
    // try to guess from exDividendDate pattern — just default to quarterly
  }

  return {
    sector: ap.sector || '',
    industry: ap.industry || '',
    annualDividend,
    dividendFrequency,
  };
}

async function fetchDividendEvents(symbol) {
  // Use chart API with 2y range and dividends event to infer frequency
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=3mo&range=2y&events=dividends`;
  const r = await fetch(url, { headers: HEADERS });
  if (!r.ok) throw new Error(`chart ${r.status}`);
  const json = await r.json();
  const result = json?.chart?.result?.[0];
  const divEvents = result?.events?.dividends || {};
  const divs = Object.values(divEvents).sort((a, b) => a.date - b.date);

  let annualDividend = null;
  let dividendFrequency = 'quarterly';

  if (divs.length >= 2) {
    // Compute average gap in days between payments to infer frequency
    const gaps = [];
    for (let i = 1; i < divs.length; i++) {
      gaps.push((divs[i].date - divs[i-1].date) / 86400);
    }
    const avgGap = gaps.reduce((a, b) => a + b, 0) / gaps.length;
    if (avgGap < 45) dividendFrequency = 'monthly';
    else if (avgGap < 120) dividendFrequency = 'quarterly';
    else if (avgGap < 270) dividendFrequency = 'semi-annual';
    else dividendFrequency = 'annual';

    // Annual dividend = most recent payment × payments per year
    const paymentsPerYear = dividendFrequency === 'monthly' ? 12
      : dividendFrequency === 'quarterly' ? 4
      : dividendFrequency === 'semi-annual' ? 2 : 1;
    annualDividend = Math.round(divs[divs.length - 1].amount * paymentsPerYear * 100) / 100;
  }

  return { annualDividend, dividendFrequency };
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const symbol = (req.query.symbol || '').trim();
  if (!symbol) return res.status(400).json({ error: 'symbol param required' });

  const cached = _cache.get(symbol);
  if (cached && Date.now() - cached.ts < CACHE_TTL) return res.status(200).json(cached.data);

  try {
    // Run both in parallel, use whichever succeeds
    const [summaryResult, chartResult] = await Promise.allSettled([
      fetchQuoteSummary(symbol),
      fetchDividendEvents(symbol),
    ]);

    const summary = summaryResult.status === 'fulfilled' ? summaryResult.value : {};
    const chart = chartResult.status === 'fulfilled' ? chartResult.value : {};

    const data = {
      sector: summary.sector || '',
      industry: summary.industry || '',
      // Prefer chart-derived dividend (more accurate) over summary
      annualDividend: chart.annualDividend ?? summary.annualDividend ?? null,
      dividendFrequency: chart.dividendFrequency || summary.dividendFrequency || 'quarterly',
    };

    _cache.set(symbol, { ts: Date.now(), data });
    return res.status(200).json(data);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
