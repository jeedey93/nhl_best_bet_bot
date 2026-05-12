const GITHUB_RAW = 'https://raw.githubusercontent.com/jeedey93/nhl_best_bet_bot/master';

function getTodayMontreal() {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'America/Toronto' });
}

async function loadPredictions(date) {
  const files = [
    `data/predictions/nhl/daily_runs/nhl_daily_predictions_${date}_7am.txt`,
    `data/predictions/nhl/daily_runs/nhl_daily_predictions_${date}_3pm.txt`,
    `data/predictions/nhl/nhl_daily_predictions_${date}.txt`,
    `data/predictions/nba/daily_runs/nba_daily_predictions_${date}_7am.txt`,
    `data/predictions/nba/daily_runs/nba_daily_predictions_${date}_3pm.txt`,
    `data/predictions/nba/nba_daily_predictions_${date}.txt`,
  ];

  const sections = [];
  await Promise.all(files.map(async (f) => {
    try {
      const res = await fetch(`${GITHUB_RAW}/${f}`);
      if (res.ok) {
        const content = (await res.text()).trim();
        if (content) {
          const label = f.split('/').pop().replace('.txt', '');
          sections.push(`=== ${label} ===\n${content}`);
        }
      }
    } catch (_) {}
  }));
  return sections.join('\n\n');
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const apiKey = process.env.GOOGLE_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'GOOGLE_API_KEY not configured' });

  const { message, history = [] } = req.body || {};
  if (!message || typeof message !== 'string') {
    return res.status(400).json({ error: 'message is required' });
  }

  const date = getTodayMontreal();
  const predictions = await loadPredictions(date);

  const systemPrompt = predictions
    ? `You are a sports betting assistant for parieurdiscipline.com, a site that uses AI to generate daily NHL and NBA betting picks. Answer questions about today's picks, odds, and predictions concisely and confidently. Use the context below to answer — do not make up picks that aren't in the context. Today is ${date}.\n\n${predictions}`
    : `You are a sports betting assistant for parieurdiscipline.com. No prediction files are available for today (${date}) yet — tell the user to check back after the 7am or 3pm run. You can still answer general questions about sports betting.`;

  // Keep last 6 messages (3 turns) to stay within token limits
  const recentHistory = (Array.isArray(history) ? history : []).slice(-6);

  const contents = [
    ...recentHistory.map(m => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }],
    })),
    { role: 'user', parts: [{ text: message }] },
  ];

  const body = {
    system_instruction: { parts: [{ text: systemPrompt }] },
    contents,
    generationConfig: { maxOutputTokens: 512, temperature: 0.7 },
  };

  const models = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
    'gemini-2.5-flash-lite',
    'gemini-1.5-flash',
  ];

  let lastError = null;
  for (const model of models) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
    try {
      const geminiRes = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (geminiRes.status === 429 || geminiRes.status === 503) {
        lastError = await geminiRes.text();
        continue; // try next model
      }

      if (!geminiRes.ok) {
        const err = await geminiRes.text();
        console.error(`Gemini error (${model}):`, err);
        return res.status(502).json({ error: 'Gemini API error', detail: err });
      }

      const data = await geminiRes.json();
      const reply = data?.candidates?.[0]?.content?.parts?.[0]?.text || 'No response from Gemini.';
      return res.status(200).json({ reply, model });
    } catch (e) {
      lastError = e.message;
      continue;
    }
  }

  console.error('All models exhausted:', lastError);
  return res.status(502).json({ error: 'All models quota exceeded. Please try again later.' });
};
