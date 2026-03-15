/**
 * Serverless voting API for GitHub Pages
 * Uses GitHub Issues API to store votes
 * Tracks by IP address to prevent duplicate votes
 *
 * Deployment: Vercel Serverless Function
 * Updated: 2026-03-15
 */

const GITHUB_OWNER = 'jeedey93';
const GITHUB_REPO = 'parieur-discipline-bot';

/**
 * Get GitHub token (with trimming)
 */
function getGitHubToken() {
  // Try new variable name first, fallback to old one
  const token = process.env.GITHUB_TOKEN || process.env.GITHUB_PAT;
  if (!token) {
    throw new Error('GITHUB_TOKEN environment variable is not set');
  }
  return token.trim();
}

/**
 * Hash IP address for privacy
 */
function hashIP(ip) {
  let hash = 0;
  for (let i = 0; i < ip.length; i++) {
    const char = ip.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(36);
}

/**
 * Get or create voting issue for today
 */
async function getOrCreateVotingIssue(date) {
  const GITHUB_TOKEN = getGitHubToken();
  const issueTitle = `Votes: ${date}`;

  // Search for existing issue
  const searchUrl = `https://api.github.com/search/issues?q=repo:${GITHUB_OWNER}/${GITHUB_REPO}+is:issue+in:title+"${issueTitle}"`;
  const searchResponse = await fetch(searchUrl, {
    headers: {
      'Authorization': `token ${GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'Parieur-Discipline-Bot',
    },
  });

  if (!searchResponse.ok) {
    const errorText = await searchResponse.text();
    throw new Error(`Failed to search issues: ${searchResponse.statusText} - ${errorText}`);
  }

  const searchData = await searchResponse.json();

  if (searchData.total_count > 0) {
    return searchData.items[0].number;
  }

  // Create new issue
  const createUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues`;
  const createResponse = await fetch(createUrl, {
    method: 'POST',
    headers: {
      'Authorization': `token ${GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json',
      'Content-Type': 'application/json',
      'User-Agent': 'Parieur-Discipline-Bot',
    },
    body: JSON.stringify({
      title: issueTitle,
      body: `## Voting data for ${date}\n\nThis issue stores votes for daily picks. Each comment represents one vote.\n\n**Format:**\n\`\`\`json\n{\n  "pickId": "nhl-game1-over",\n  "ipHash": "abc123",\n  "timestamp": "2026-03-15T10:30:00Z"\n}\n\`\`\``,
      labels: ['votes', 'automated'],
    }),
  });

  if (!createResponse.ok) {
    throw new Error(`Failed to create issue: ${createResponse.statusText}`);
  }

  const createData = await createResponse.json();
  return createData.number;
}

/**
 * Get all votes for a date
 */
async function getVotes(date) {
  try {
    const GITHUB_TOKEN = getGitHubToken();
    const issueNumber = await getOrCreateVotingIssue(date);

    // Fetch all comments on the issue
    const commentsUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues/${issueNumber}/comments`;
    const response = await fetch(commentsUrl, {
      headers: {
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Parieur-Discipline-Bot',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch comments: ${response.statusText}`);
    }

    const comments = await response.json();

    // Parse votes from comments
    const votes = {};
    const userVotes = {}; // Track what each IP voted for

    comments.forEach(comment => {
      try {
        const voteData = JSON.parse(comment.body);
        const { pickId, ipHash } = voteData;

        if (!votes[pickId]) {
          votes[pickId] = 0;
        }

        // Only count one vote per IP per pick
        const voteKey = `${ipHash}-${pickId}`;
        if (!userVotes[voteKey]) {
          votes[pickId]++;
          userVotes[voteKey] = true;
        }
      } catch (e) {
        // Ignore malformed comments
      }
    });

    return { votes, userVotes };
  } catch (error) {
    console.error('Error getting votes:', error);
    return { votes: {}, userVotes: {} };
  }
}

/**
 * Cast a vote
 */
async function castVote(date, pickId, ipHash) {
  try {
    const GITHUB_TOKEN = getGitHubToken();
    const issueNumber = await getOrCreateVotingIssue(date);

    // Check if user already voted for this pick
    const { userVotes } = await getVotes(date);
    const voteKey = `${ipHash}-${pickId}`;

    if (userVotes[voteKey]) {
      return { success: false, error: 'You have already voted for this pick' };
    }

    // Add comment with vote
    const commentsUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues/${issueNumber}/comments`;
    const response = await fetch(commentsUrl, {
      method: 'POST',
      headers: {
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'Parieur-Discipline-Bot',
      },
      body: JSON.stringify({
        body: JSON.stringify({
          pickId,
          ipHash,
          timestamp: new Date().toISOString(),
        }),
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to post comment: ${response.statusText}`);
    }

    return { success: true };
  } catch (error) {
    console.error('Error casting vote:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Vercel Serverless Function handler
 */
module.exports = async (req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    // Debug: Check if token is loaded
    if (!process.env.GITHUB_TOKEN && !process.env.GITHUB_PAT) {
      return res.status(500).json({
        success: false,
        error: 'GITHUB_TOKEN environment variable is not set in Vercel',
        debug: 'Token is undefined or empty'
      });
    }

    // Debug: Check token format
    const token = (process.env.GITHUB_TOKEN || process.env.GITHUB_PAT).trim();
    const tokenLength = token.length;
    const tokenStart = token.substring(0, 7);

    // Temporary debug endpoint
    if (req.query.debug === 'token') {
      return res.status(200).json({
        tokenLength,
        tokenStart,
        tokenEnd: token.substring(token.length - 4),
        usingVariable: process.env.GITHUB_TOKEN ? 'GITHUB_TOKEN' : 'GITHUB_PAT'
      });
    }

    const { date = new Date().toISOString().split('T')[0] } = req.query;

    // GET: Fetch vote counts
    if (req.method === 'GET') {
      const { votes } = await getVotes(date);
      return res.status(200).json({ success: true, votes });
    }

    // POST: Cast a vote
    if (req.method === 'POST') {
      const { pickId } = req.body;

      if (!pickId) {
        return res.status(400).json({ success: false, error: 'Missing pickId' });
      }

      // Get IP address from request
      const ip = req.headers['x-forwarded-for']?.split(',')[0] ||
                 req.headers['x-real-ip'] ||
                 req.connection.remoteAddress ||
                 'unknown';
      const ipHash = hashIP(ip);

      const result = await castVote(date, pickId, ipHash);

      if (result.success) {
        // Return updated vote counts
        const { votes } = await getVotes(date);
        return res.status(200).json({ success: true, votes });
      } else {
        return res.status(400).json(result);
      }
    }

    return res.status(405).json({ error: 'Method not allowed' });

  } catch (error) {
    console.error('Error in vote handler:', error);
    return res.status(500).json({ success: false, error: error.message });
  }
};
