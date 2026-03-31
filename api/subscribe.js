/**
 * Serverless subscribe API
 * Validates email and adds it to the SUBSCRIBER_LIST GitHub variable.
 *
 * Deployment: Vercel Serverless Function
 * POST /api/subscribe  body: { email }
 *   → { success: true }              (subscribed)
 *   → { success: false, alreadySubscribed: true }
 *   → { success: false, error: "..." }
 */

const GITHUB_OWNER = 'jeedey93';
const GITHUB_REPO = 'parieur-discipline-bot';

function getGitHubToken() {
  const token = process.env.GH_API_TOKEN || process.env.GITHUB_TOKEN || process.env.GITHUB_PAT;
  if (!token) throw new Error('GitHub token environment variable is not set');
  return token.trim();
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

async function getSubscriberList() {
  const GITHUB_TOKEN = getGitHubToken();
  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/variables/SUBSCRIBER_LIST`;
  const res = await fetch(url, {
    headers: {
      'Authorization': `token ${GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'Parieur-Discipline-Bot',
    },
  });
  if (!res.ok) throw new Error(`Failed to fetch SUBSCRIBER_LIST: ${res.statusText}`);
  const data = await res.json();
  return data.value || '';
}

async function updateSubscriberList(csv) {
  const GITHUB_TOKEN = getGitHubToken();
  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/variables/SUBSCRIBER_LIST`;
  const res = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Authorization': `token ${GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json',
      'Content-Type': 'application/json',
      'User-Agent': 'Parieur-Discipline-Bot',
    },
    body: JSON.stringify({ name: 'SUBSCRIBER_LIST', value: csv }),
  });
  if (!res.ok) throw new Error(`Failed to update SUBSCRIBER_LIST: ${res.statusText}`);
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email } = req.body || {};

  if (!email || typeof email !== 'string') {
    return res.status(400).json({ success: false, error: 'Email is required' });
  }

  const normalized = email.toLowerCase().trim();

  if (!isValidEmail(normalized)) {
    return res.status(400).json({ success: false, error: 'Invalid email address' });
  }

  try {
    const current = await getSubscriberList();
    const existing = current.split(',').map(e => e.trim().toLowerCase()).filter(Boolean);

    if (existing.includes(normalized)) {
      return res.status(200).json({ success: false, alreadySubscribed: true });
    }

    const updated = [...existing.map(e => e), normalized].join(',');
    await updateSubscriberList(updated);

    return res.status(200).json({ success: true });
  } catch (error) {
    console.error('Subscribe error:', error);
    return res.status(500).json({ success: false, error: 'Something went wrong. Please try again.' });
  }
};
