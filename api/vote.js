/**
 * Serverless voting API for GitHub Pages
 * Uses GitHub Issues API to store votes
 * Tracks by IP address to prevent duplicate votes
 *
 * Deployment: Vercel Edge Function or Cloudflare Worker
 */

const GITHUB_OWNER = 'jeedey93';
const GITHUB_REPO = 'parieur-discipline-bot';
const GITHUB_TOKEN = process.env.GITHUB_PAT; // Set in Vercel environment variables

/**
 * Hash IP address for privacy
 */
function hashIP(ip) {
  // Simple hash (use crypto.subtle.digest in production for better security)
  let hash = 0;
  for (let i = 0; i < ip.length; i++) {
    const char = ip.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Get or create voting issue for today
 */
async function getOrCreateVotingIssue(date) {
  const issueTitle = `Votes: ${date}`;

  // Search for existing issue
  const searchUrl = `https://api.github.com/search/issues?q=repo:${GITHUB_OWNER}/${GITHUB_REPO}+is:issue+in:title+"${issueTitle}"`;
  const searchResponse = await fetch(searchUrl, {
    headers: {
      'Authorization': `token ${GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json',
    },
  });

  if (!searchResponse.ok) {
    throw new Error(`Failed to search issues: ${searchResponse.statusText}`);
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
    const issueNumber = await getOrCreateVotingIssue(date);

    // Fetch all comments on the issue
    const commentsUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues/${issueNumber}/comments`;
    const response = await fetch(commentsUrl, {
      headers: {
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
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
        console.error('Failed to parse comment:', e);
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
 * Main handler
 */
export default async function handler(req) {
  // Enable CORS
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    const date = url.searchParams.get('date') || new Date().toISOString().split('T')[0];

    // GET: Fetch vote counts
    if (req.method === 'GET') {
      const { votes } = await getVotes(date);
      return new Response(JSON.stringify({ success: true, votes }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // POST: Cast a vote
    if (req.method === 'POST') {
      const body = await req.json();
      const { pickId } = body;

      if (!pickId) {
        return new Response(JSON.stringify({ success: false, error: 'Missing pickId' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      // Get IP address from request
      const ip = req.headers.get('x-forwarded-for')?.split(',')[0] ||
                 req.headers.get('x-real-ip') ||
                 'unknown';
      const ipHash = hashIP(ip);

      const result = await castVote(date, pickId, ipHash);

      if (result.success) {
        // Return updated vote counts
        const { votes } = await getVotes(date);
        return new Response(JSON.stringify({ success: true, votes }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      } else {
        return new Response(JSON.stringify(result), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    }

    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error in vote handler:', error);
    return new Response(JSON.stringify({ success: false, error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
}
