/**
 * Serverless unsubscribe API
 * Verifies HMAC-signed token and removes email from SUBSCRIBER_LIST GitHub variable.
 *
 * Deployment: Vercel Serverless Function
 * GET /api/unsubscribe?email=...&token=... → verify, remove, return HTML confirmation
 */

const crypto = require('crypto');

const GITHUB_OWNER = 'jeedey93';
const GITHUB_REPO = 'parieur-discipline-bot';

function getGitHubToken() {
  const token = process.env.GH_API_TOKEN || process.env.GITHUB_TOKEN || process.env.GITHUB_PAT;
  if (!token) throw new Error('GitHub token environment variable is not set');
  return token.trim();
}

function generateToken(email) {
  const secret = process.env.UNSUBSCRIBE_SECRET;
  if (!secret) throw new Error('UNSUBSCRIBE_SECRET is not set');
  return crypto.createHmac('sha256', secret)
    .update(email.toLowerCase().trim())
    .digest('hex');
}

function verifyToken(email, token) {
  const expected = generateToken(email);
  const a = Buffer.from(token, 'hex');
  const b = Buffer.from(expected, 'hex');
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
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

async function removeEmail(email) {
  const current = await getSubscriberList();
  const filtered = current
    .split(',')
    .map(e => e.trim())
    .filter(e => e.toLowerCase() !== email.toLowerCase().trim())
    .join(',');
  await updateSubscriberList(filtered);
}

function successPage(email) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unsubscribed - Parieur Discipliné</title>
<link rel="icon" type="image/png" href="/parieur_discipline_icon_1024.png">
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:#0f172a;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center;">
  <div style="text-align:center;padding:40px 24px;max-width:480px;">
    <div style="font-size:56px;margin-bottom:24px;">✅</div>
    <h1 style="font-size:28px;font-weight:700;margin:0 0 12px 0;color:#f1f5f9;">You've been unsubscribed</h1>
    <p style="font-size:16px;color:#94a3b8;margin:0 0 8px 0;">${escapeHtml(email)}</p>
    <p style="font-size:15px;color:#64748b;margin:0 0 32px 0;">You won't receive any more daily picks emails from us.</p>
    <a href="https://parieurdiscipline.com" style="display:inline-block;background:linear-gradient(135deg,#4a90e2,#357abd);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;">← Back to site</a>
    <p style="font-size:12px;color:#475569;margin:24px 0 0 0;">Changed your mind? <a href="https://parieurdiscipline.com/#subscribe" style="color:#4a90e2;">Subscribe again</a></p>
  </div>
</body>
</html>`;
}

function errorPage(message) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Error - Parieur Discipliné</title>
<link rel="icon" type="image/png" href="/parieur_discipline_icon_1024.png">
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:#0f172a;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center;">
  <div style="text-align:center;padding:40px 24px;max-width:480px;">
    <div style="font-size:56px;margin-bottom:24px;">⚠️</div>
    <h1 style="font-size:28px;font-weight:700;margin:0 0 12px 0;color:#f1f5f9;">Unsubscribe failed</h1>
    <p style="font-size:15px;color:#94a3b8;margin:0 0 32px 0;">${escapeHtml(message)}</p>
    <p style="font-size:14px;color:#64748b;margin:0 0 24px 0;">Please use the link from your email, or contact us directly.</p>
    <a href="mailto:parieur.discipline@gmail.com?subject=Unsubscribe+request" style="display:inline-block;background:linear-gradient(135deg,#4a90e2,#357abd);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;">Contact us</a>
  </div>
</body>
</html>`;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email, token } = req.query;

  if (!email || !token) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(400).send(errorPage('Missing email or token. Please use the link from your email.'));
  }

  let valid = false;
  try {
    valid = verifyToken(email, token);
  } catch (e) {
    console.error('Token verification error:', e.message);
    valid = false;
  }

  if (!valid) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(400).send(errorPage('Invalid or expired unsubscribe link. Please use the link from your most recent email.'));
  }

  try {
    await removeEmail(email);
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(200).send(successPage(email));
  } catch (error) {
    console.error('Unsubscribe error:', error);
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(500).send(errorPage('Something went wrong on our end. Please try again later.'));
  }
};
