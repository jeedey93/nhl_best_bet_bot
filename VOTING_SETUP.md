# Voting System Setup Guide

## Overview

This voting system allows visitors to vote on individual betting picks on your daily picks page. It uses:
- **GitHub Issues API** as a database (free, no extra services)
- **Vercel Serverless Functions** for the voting API
- **IP address hashing** to ensure 1 vote per person per pick
- **LocalStorage** for client-side vote tracking

## Setup Instructions

### 1. Update GitHub Configuration

The code is already configured with your GitHub username (`jeedey93`).

### 2. Create GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Name it: `Voting System API`
4. Select scopes:
   - ✅ `repo` (Full control of repositories)
5. Generate token and copy it (you won't see it again!)

### 3. Configure Vercel Environment Variable

In Vercel Dashboard:
1. Go to your project settings
2. Navigate to Settings → Environment Variables
3. Add new variable:
   - **Name**: `GH_API_TOKEN`
   - **Value**: [paste your GitHub token]
   - **Environments**: Production only (check only Production ✅)
4. Save

**Important:** Use `GH_API_TOKEN` as the variable name. The code also supports `GITHUB_TOKEN` or `GITHUB_PAT` as fallbacks.

### 4. Deploy

The voting system is already deployed. When you push to GitHub, Vercel automatically deploys.

### 5. Test the Voting System

Visit your daily picks page: `https://parieurdiscipline.com/daily-picks.html`

Test voting:
1. Click the 👍 button on any pick
2. Verify button shows ✓ and becomes disabled
3. Vote count should increment
4. Try voting again - should see "You have already voted"

## Environment Variable Notes

Due to Vercel caching issues, the final setup uses `GH_API_TOKEN`:
- Primary: `GH_API_TOKEN` (recommended)
- Fallback: `GITHUB_TOKEN`
- Fallback: `GITHUB_PAT`

The code checks for these in order and uses the first one found.

## How It Works

### Vote Storage (GitHub Issues)

When someone votes:
1. System creates/finds an issue titled `Votes: YYYY-MM-DD` (one per day)
2. Adds a comment with vote data:
   ```json
   {
     "pickId": "nhl-pick-0",
     "ipHash": "abc123xyz",
     "timestamp": "2026-03-15T10:30:00Z"
   }
   ```
3. IP address is hashed for privacy (original IP never stored)

### Vote Tracking (LocalStorage)

- Client-side uses localStorage to remember which picks you voted for
- Key format: `voted_picks_YYYY-MM-DD`
- Cleared automatically after 7 days
- Prevents accidental double-voting from same browser

### API Endpoints

**GET** `/api/vote?date=2026-03-15`
- Fetches all vote counts for a given date
- Returns: `{ success: true, votes: { "nhl-pick-0": 5, "nba-pick-1": 3 } }`

**POST** `/api/vote?date=2026-03-15`
- Casts a vote for a pick
- Body: `{ "pickId": "nhl-pick-0" }`
- Returns updated vote counts

## Pick ID Format

Each pick gets a unique ID based on its position:
- `nhl-pick-0`, `nhl-pick-1`, `nhl-pick-2`...
- `nba-pick-0`, `nba-pick-1`, `nba-pick-2`...

This ensures consistency across days even if games change.

## Security Features

1. **IP-based Limiting**: One vote per IP per pick (enforced server-side)
2. **LocalStorage Tracking**: Prevents accidental double-voting from same browser
3. **No Authentication**: Anonymous voting, minimal friction
4. **CORS Enabled**: API accessible from your domain
5. **Rate Limiting**: Vercel provides automatic rate limiting on Edge Functions

## Limitations

- **IP Changes**: If user changes IP (VPN, mobile network), they can vote again (expected behavior)
- **Browser Clearing**: Clearing localStorage allows re-voting from same browser (server still blocks duplicate IP)
- **GitHub API Limits**: Free tier has 5000 requests/hour (more than enough for voting)

## Troubleshooting

### Votes not saving

1. Check browser console for errors
2. Verify `GITHUB_PAT` environment variable is set in Vercel
3. Check GitHub token has `repo` or `public_repo` scope
4. Verify `GITHUB_OWNER` is correct in `api/vote.js`

### "Failed to vote" error

1. Check Vercel function logs: Vercel Dashboard → Functions → vote.js → Logs
2. Verify GitHub Issues are enabled on your repository
3. Test API manually: `curl https://parieurdiscipline.com/api/vote?date=2026-03-15`

### Votes reset every day

This is expected! Each day gets a new voting issue. Yesterday's votes are preserved in the old issue.

## Viewing Vote History

All votes are stored in GitHub Issues:
1. Go to your repository
2. Click "Issues"
3. Search for label `votes`
4. Each issue = one day's votes

Example issue: `Votes: 2026-03-15`

## Future Enhancements (Optional)

- **Vote Trends**: Show which pick is "trending" (most votes in last hour)
- **Leaderboard**: Display most-voted picks of the week
- **Vote Analytics**: Track correlation between votes and win rate
- **Social Sharing**: "X people voted for this pick"

## Cost

**$0** - Completely free!
- GitHub API: Free (5000 requests/hour)
- Vercel Edge Functions: Free tier (100k requests/day)
- No database costs
- No third-party services

## Support

If you encounter issues:
1. Check Vercel function logs
2. Review GitHub Issues for vote storage
3. Test API endpoints with curl/Postman
4. Check browser console for JavaScript errors
