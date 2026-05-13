/**
 * Serverless API for NHL playoff results persistence
 * Stores results as JSON in the body of a dedicated GitHub Issue
 * GET  /api/playoff-results → returns current results
 * POST /api/playoff-results → saves new results (replaces entire body)
 */

const GITHUB_OWNER = 'jeedey93';
const GITHUB_REPO  = 'parieur-discipline-bot';
const ISSUE_TITLE  = 'NHL Playoff Results 2026';

function getToken() {
  const t = process.env.GH_API_TOKEN || process.env.GITHUB_TOKEN || process.env.GITHUB_PAT;
  if (!t) throw new Error('GitHub token not set');
  return t.trim();
}

const GH_HEADERS = () => ({
  'Authorization': `token ${getToken()}`,
  'Accept': 'application/vnd.github.v3+json',
  'Content-Type': 'application/json',
  'User-Agent': 'Parieur-Discipline-Bot',
});

async function getOrCreateIssue() {
  const search = await fetch(
    `https://api.github.com/search/issues?q=repo:${GITHUB_OWNER}/${GITHUB_REPO}+is:issue+in:title+"${encodeURIComponent(ISSUE_TITLE)}"`,
    { headers: GH_HEADERS() }
  );
  const data = await search.json();
  if (data.total_count > 0) return data.items[0];

  const create = await fetch(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues`,
    {
      method: 'POST',
      headers: GH_HEADERS(),
      body: JSON.stringify({ title: ISSUE_TITLE, body: '{}', labels: ['automated'] }),
    }
  );
  return create.json();
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    const issue = await getOrCreateIssue();

    if (req.method === 'GET') {
      try {
        const stored = JSON.parse(issue.body || '{}');
        // Support both old format (plain results object) and new format ({results, previousResults})
        const results = stored.results || stored;
        const previousResults = stored.previousResults || null;
        return res.status(200).json({ success: true, results, previousResults });
      } catch {
        return res.status(200).json({ success: true, results: {}, previousResults: null });
      }
    }

    if (req.method === 'POST') {
      const { results, previousResults: explicitPrev } = req.body;
      if (!results) return res.status(400).json({ success: false, error: 'Missing results' });

      // Use explicit previousResults if provided, otherwise snapshot current stored results
      let previousResults = explicitPrev || null;
      if (!previousResults) {
        try {
          const stored = JSON.parse(issue.body || '{}');
          previousResults = stored.results || stored;
        } catch {}
      }
      await fetch(
        `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues/${issue.number}`,
        {
          method: 'PATCH',
          headers: GH_HEADERS(),
          body: JSON.stringify({ body: JSON.stringify({ results, previousResults }) }),
        }
      );
      return res.status(200).json({ success: true });
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ success: false, error: err.message });
  }
};
