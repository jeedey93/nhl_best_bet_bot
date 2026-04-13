/**
 * Submit Playoff Picks — Vercel Serverless Function
 * Receives the participant's name + picks image (base64 JPEG),
 * then forwards it as an email attachment to parieur.discipline@gmail.com
 * via the Resend API.
 *
 * Required env var (set in Vercel dashboard):
 *   RESEND_API_KEY  — your Resend API key (re_xxxxxxxx)
 *
 * POST /api/submit-picks
 * Body JSON: { name: string, imageBase64: string, lang: "en"|"fr" }
 */

const RECIPIENT = 'parieur.discipline@gmail.com';
const FROM_ADDRESS = 'onboarding@resend.dev'; // free Resend sandbox sender — swap for your verified domain
const RESEND_API = 'https://api.resend.com/emails';

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: 'RESEND_API_KEY not configured' });
  }

  const { name, imageBase64, lang = 'en', picksData } = req.body || {};

  if (!name || !name.trim()) {
    return res.status(400).json({ error: 'Missing participant name' });
  }
  if (!imageBase64) {
    return res.status(400).json({ error: 'Missing image data' });
  }

  // Strip data URI prefix if present (data:image/jpeg;base64,...)
  const base64Data = imageBase64.replace(/^data:image\/\w+;base64,/, '');

  const participantName = name.trim();
  const subject = lang === 'fr'
    ? `Choix Éliminatoires LNH 2026 — ${participantName}`
    : `NHL Playoff Picks 2026 — ${participantName}`;

  const htmlBody = lang === 'fr'
    ? `<p><strong>${participantName}</strong> a soumis ses choix pour les éliminatoires LNH 2026.</p><p>Voir l'image en pièce jointe.</p>`
    : `<p><strong>${participantName}</strong> submitted their NHL Playoff Picks 2026.</p><p>See the attached image.</p>`;

  const filename = `${participantName.replace(/\s+/g, '-')}-NHL-Playoffs-2026.jpg`;
  const jsonFilename = `${participantName.replace(/\s+/g, '_')}_NHL_Picks.json`;

  const attachments = [
    { filename, content: base64Data },
  ];
  if (picksData) {
    const jsonBase64 = Buffer.from(JSON.stringify(picksData, null, 2)).toString('base64');
    attachments.push({ filename: jsonFilename, content: jsonBase64 });
  }

  try {
    const response = await fetch(RESEND_API, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'ParieurDiscipline/1.0',
      },
      body: JSON.stringify({
        from: FROM_ADDRESS,
        to: RECIPIENT,
        subject,
        html: htmlBody,
        attachments,
      }),
    });

    const result = await response.json();

    if (!response.ok) {
      console.error('Resend error:', result);
      return res.status(502).json({ error: result.message || 'Failed to send email' });
    }

    return res.status(200).json({ success: true });
  } catch (err) {
    console.error('submit-picks error:', err);
    return res.status(500).json({ error: err.message });
  }
};
