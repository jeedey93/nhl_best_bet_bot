/**
 * Page view counter API
 * Uses a single GitHub Issue to store the view count per page.
 * GET /api/page-views?page=standings — increments and returns count
 * GET /api/page-views?page=standings&count_only=true — returns count without incrementing
 */

const GITHUB_OWNER = 'jeedey93';
const GITHUB_REPO = 'parieur-discipline-bot';
const ISSUE_TITLE = 'Page Views Counter';

function getGitHubToken() {
  const token = process.env.GH_API_TOKEN || process.env.GITHUB_TOKEN || process.env.GITHUB_PAT;
  if (!token) throw new Error('GitHub token not configured');
  return token.trim();
}

async function getOrCreateIssue() {
  const token = getGitHubToken();
  const headers = {
    'Authorization': `token ${token}`,
    'Accept': 'application/vnd.github.v3+json',
    'Content-Type': 'application/json',
    'User-Agent': 'Parieur-Discipline-Bot',
  };

  // Search for existing issue
  const search = await fetch(
    `https://api.github.com/search/issues?q=repo:${GITHUB_OWNER}/${GITHUB_REPO}+is:issue+in:title+"${ISSUE_TITLE}"`,
    { headers }
  );
  const searchData = await search.json();
  if (searchData.total_count > 0) return searchData.items[0];

  // Create it
  const create = await fetch(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues`,
    { method: 'POST', headers, body: JSON.stringify({ title: ISSUE_TITLE, body: '{}', labels: ['analytics', 'automated'] }) }
  );
  return await create.json();
}

async function getViews(issue) {
  try { return JSON.parse(issue.body) || {}; }
  catch { return {}; }
}

async function incrementViews(issue, page) {
  const token = getGitHubToken();
  const views = await getViews(issue);
  views[page] = (views[page] || 0) + 1;

  await fetch(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues/${issue.number}`,
    {
      method: 'PATCH',
      headers: {
        'Authorization': `token ${token}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'Parieur-Discipline-Bot',
      },
      body: JSON.stringify({ body: JSON.stringify(views) }),
    }
  );
  return views[page];
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    const page = (req.query.page || 'standings').toLowerCase();
    const countOnly = req.query.count_only === 'true';

    const issue = await getOrCreateIssue();
    const views = await getViews(issue);

    if (countOnly) {
      return res.status(200).json({ success: true, page, count: views[page] || 0 });
    }

    const count = await incrementViews(issue, page);
    return res.status(200).json({ success: true, page, count });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ success: false, error: err.message });
  }
};
