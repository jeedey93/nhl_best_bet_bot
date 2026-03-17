/**
 * Serverless proxy for NHL schedule API
 * Avoids CORS issues when fetching from browser
 *
 * Deployment: Vercel Serverless Function
 */

module.exports = async (req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { date } = req.query;

    if (!date) {
      return res.status(400).json({ error: 'Missing date parameter' });
    }

    // Validate date format (YYYY-MM-DD)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      return res.status(400).json({ error: 'Invalid date format. Use YYYY-MM-DD' });
    }

    // Fetch from NHL API
    const nhlUrl = `https://api-web.nhle.com/v1/schedule/${date}`;
    const nhlResponse = await fetch(nhlUrl);

    if (!nhlResponse.ok) {
      return res.status(nhlResponse.status).json({
        error: `NHL API returned ${nhlResponse.status}`
      });
    }

    const data = await nhlResponse.json();

    // Return the schedule data
    return res.status(200).json(data);

  } catch (error) {
    console.error('Error fetching NHL schedule:', error);
    return res.status(500).json({
      error: 'Failed to fetch NHL schedule',
      message: error.message
    });
  }
};
