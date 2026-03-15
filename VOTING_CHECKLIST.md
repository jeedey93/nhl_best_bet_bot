# Voting System Deployment Checklist

Use this checklist to deploy the voting system step-by-step.

## ✅ Pre-Deployment

- [ ] Read `VOTING_SUMMARY.md` for overview
- [ ] Read `VOTING_SETUP.md` for detailed instructions

## 🔧 Configuration (5 minutes)

### Step 1: Update GitHub Username
- [ ] Open `api/vote.js`
- [ ] Line 9: Replace `YOUR_USERNAME` with your actual GitHub username
- [ ] Save file

### Step 2: Create GitHub Personal Access Token
- [ ] Go to https://github.com/settings/tokens
- [ ] Click "Generate new token (classic)"
- [ ] Name: `Voting System API`
- [ ] Scopes: Select `repo` (or `public_repo` if public repo)
- [ ] Click "Generate token"
- [ ] **Copy token immediately** (you won't see it again!)

### Step 3: Add Token to Vercel
- [ ] Go to https://vercel.com/dashboard
- [ ] Select your project (parieur-discipline-bot)
- [ ] Go to Settings → Environment Variables
- [ ] Click "Add New"
- [ ] Name: `GITHUB_PAT`
- [ ] Value: [paste your GitHub token]
- [ ] Environments: Check all (Production, Preview, Development)
- [ ] Click "Save"

## 🚀 Deployment

### Step 4: Commit and Push
```bash
git add .
git commit -m "Add voting system to daily picks"
git push origin master
```

- [ ] Run git commands above
- [ ] Wait for Vercel to deploy (auto-deployment from GitHub)
- [ ] Check Vercel dashboard for deployment status

## 🧪 Testing (10 minutes)

### Step 5: Test the Voting System

#### A. Test Page
- [ ] Visit: `https://parieurdiscipline.com/vote-test.html`
- [ ] Click "Test API Connection" - should show ✓ success
- [ ] Click "Vote" on Test Pick #1 - should increment count
- [ ] Click "Vote" on Test Pick #2 - should increment count
- [ ] Click "Load All Votes" - should show vote counts
- [ ] Try voting again - should see error "already voted"
- [ ] Click "Check LocalStorage" - should show your votes

#### B. Daily Picks Page
- [ ] Visit: `https://parieurdiscipline.com/daily-picks.html`
- [ ] Scroll to picks table
- [ ] Click 👍 button on any pick
- [ ] Verify:
  - [ ] Button shows ✓ after clicking
  - [ ] Vote count increments
  - [ ] Button becomes disabled
  - [ ] "✓ Voted" label appears
- [ ] Refresh page
- [ ] Verify:
  - [ ] Vote count persists
  - [ ] Button still disabled
  - [ ] "✓ Voted" still visible

#### C. GitHub Issues
- [ ] Go to: `https://github.com/YOUR_USERNAME/parieur-discipline-bot/issues`
- [ ] Find issue titled "Votes: [today's date]"
- [ ] Open the issue
- [ ] Verify:
  - [ ] Issue has labels: `votes`, `automated`
  - [ ] Comments contain vote data (JSON format)
  - [ ] IP addresses are hashed (not readable)

## 🐛 Troubleshooting

### If votes aren't saving:

1. **Check Vercel Function Logs**
   - [ ] Go to Vercel Dashboard → Functions → vote.js → Logs
   - [ ] Look for errors in the logs
   - [ ] Common issues:
     - `GITHUB_PAT` not set
     - GitHub token doesn't have `repo` scope
     - GitHub username incorrect in `api/vote.js`

2. **Check Browser Console**
   - [ ] Open browser DevTools (F12)
   - [ ] Go to Console tab
   - [ ] Look for errors when clicking vote button
   - [ ] Common issues:
     - 404 error: Edge function not deployed
     - CORS error: Domain mismatch
     - Network error: Vercel function not responding

3. **Test API Directly**
   ```bash
   # Get votes
   curl https://parieurdiscipline.com/api/vote?date=2026-03-15

   # Should return: {"success":true,"votes":{}}
   ```
   - [ ] Run curl command above
   - [ ] Verify response is valid JSON
   - [ ] If error, check Vercel deployment status

### If button doesn't work:

- [ ] Check JavaScript console for errors
- [ ] Verify `renderTable()` function includes vote column
- [ ] Clear browser cache and reload page
- [ ] Test in incognito/private window

## ✨ Post-Deployment

### Step 6: Monitor First Day
- [ ] Check vote counts throughout the day
- [ ] Monitor GitHub Issues for vote storage
- [ ] Check Vercel function logs for errors
- [ ] Test from mobile device
- [ ] Test from different browsers

### Step 7: Optional Enhancements
- [ ] Add vote trends ("trending" picks)
- [ ] Add weekly leaderboard
- [ ] Add vote-to-win correlation
- [ ] Add social sharing features

## 📊 Success Metrics

After 24 hours, verify:
- [ ] Multiple votes recorded in GitHub Issues
- [ ] No errors in Vercel function logs
- [ ] Vote counts display correctly on page
- [ ] LocalStorage tracking works (prevents double-votes)
- [ ] Mobile/desktop both work

## 🎉 You're Done!

Your voting system is now live! Users can vote on their favorite picks.

---

## Quick Reference

**Test Page:** https://parieurdiscipline.com/vote-test.html
**Daily Picks:** https://parieurdiscipline.com/daily-picks.html
**GitHub Issues:** https://github.com/YOUR_USERNAME/parieur-discipline-bot/issues?q=label%3Avotes
**Vercel Logs:** https://vercel.com/dashboard → Functions → vote.js → Logs

**Need help?** See `VOTING_SETUP.md` for detailed troubleshooting.
