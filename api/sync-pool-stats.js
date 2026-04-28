/**
 * Vercel Serverless Function: Sync NHL player stats
 *
 * Local: Runs scrape_nhl_stats.py directly
 * Vercel: Triggers GitHub Actions workflow
 * Usage: POST /api/sync-pool-stats
 */

export default async function handler(req, res) {
  // Only allow POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Check if we're in local environment or Vercel
    const isLocal = !process.env.VERCEL;

    if (isLocal) {
      // Local development: Run Python script directly
      try {
        const { execSync } = require('child_process');
        const output = execSync('python3 scripts/scrape_nhl_stats.py', {
          cwd: process.cwd(),
          encoding: 'utf-8',
          maxBuffer: 10 * 1024 * 1024,
          env: { ...process.env },
        });

        console.log('Script output:', output);

        return res.status(200).json({
          message: 'Sync completed',
          status: 'Player stats updated successfully',
          output: output.split('\n').slice(-3).join('\n'),
        });
      } catch (error) {
        console.error('Script execution failed:', error.message);
        return res.status(500).json({
          error: 'Script execution failed',
          details: error.message,
        });
      }
    } else {
      // Production (Vercel): Trigger GitHub Actions workflow
      const gitHubToken = process.env.GH_API_TOKEN;
      if (!gitHubToken) {
        return res.status(500).json({
          error: 'GitHub token not configured in Vercel environment variables'
        });
      }

      const response = await fetch(
        'https://api.github.com/repos/I854351/parieur-discipline-bot/actions/workflows/update_pool_stats.yml/dispatches',
        {
          method: 'POST',
          headers: {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': `token ${gitHubToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ref: 'master' }),
        }
      );

      if (!response.ok) {
        const error = await response.text();
        console.error('GitHub dispatch failed:', error);
        return res.status(response.status).json({
          error: `GitHub API error: ${response.statusText}`,
          details: error,
        });
      }

      return res.status(202).json({
        message: 'Sync triggered',
        status: 'GitHub Actions workflow dispatched (running in background)',
        eta: '~5 minutes',
      });
    }
  } catch (error) {
    console.error('Sync error:', error);
    return res.status(500).json({
      error: 'Failed to sync stats',
      details: error.message,
    });
  }
}

