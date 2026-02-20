// TrueVoice for Reddit - Background Service Worker
// Handles Reddit API calls and caching

const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const REQUEST_DELAY_MS = 100; // Delay between requests per worker
const MAX_CONCURRENT = 3; // Parallel request workers

// Queue with concurrent workers for Reddit API requests
const requestQueue = [];
let activeWorkers = 0;

async function processQueue() {
  if (activeWorkers >= MAX_CONCURRENT || requestQueue.length === 0) return;
  activeWorkers++;

  while (requestQueue.length > 0) {
    const { url, resolve, reject } = requestQueue.shift();
    try {
      const response = await fetch(url, {
        headers: { 'Accept': 'application/json' }
      });
      if (response.status === 429) {
        // Rate limited - wait and retry
        await sleep(2000);
        requestQueue.unshift({ url, resolve, reject });
        continue;
      }
      if (!response.ok) {
        reject(new Error(`HTTP ${response.status}`));
      } else {
        const data = await response.json();
        resolve(data);
      }
    } catch (err) {
      reject(err);
    }
    await sleep(REQUEST_DELAY_MS);
  }

  activeWorkers--;
}

function queuedFetch(url) {
  return new Promise((resolve, reject) => {
    requestQueue.push({ url, resolve, reject });
    // Spin up workers up to MAX_CONCURRENT
    for (let i = activeWorkers; i < MAX_CONCURRENT; i++) {
      processQueue();
    }
  });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// --- Cache helpers ---

async function getCached(key) {
  const result = await chrome.storage.local.get(key);
  if (!result[key]) return null;
  const entry = result[key];
  if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
    chrome.storage.local.remove(key);
    return null;
  }
  return entry.data;
}

async function setCache(key, data) {
  await chrome.storage.local.set({
    [key]: { data, timestamp: Date.now() }
  });
}

// --- Reddit API ---

async function fetchUserAbout(username) {
  const cacheKey = `about_${username}`;
  const cached = await getCached(cacheKey);
  if (cached) return cached;

  const data = await queuedFetch(
    `https://www.reddit.com/user/${encodeURIComponent(username)}/about.json`
  );

  const info = data?.data;
  if (!info) throw new Error('No user data');

  const result = {
    name: info.name,
    created: info.created_utc,
    linkKarma: info.link_karma || 0,
    commentKarma: info.comment_karma || 0,
    totalKarma: (info.link_karma || 0) + (info.comment_karma || 0),
    isGold: info.is_gold || false,
    isMod: info.is_mod || false,
    hasVerifiedEmail: info.has_verified_email || false,
    iconUrl: info.icon_img || info.snoovatar_img || null
  };

  await setCache(cacheKey, result);
  return result;
}

async function fetchUserComments(username) {
  const cacheKey = `comments_${username}`;
  const cached = await getCached(cacheKey);
  if (cached) return cached;

  const data = await queuedFetch(
    `https://www.reddit.com/user/${encodeURIComponent(username)}/comments.json?limit=30&sort=new`
  );

  const comments = (data?.data?.children || []).map(c => ({
    body: c.data.body,
    subreddit: c.data.subreddit,
    created: c.data.created_utc,
    score: c.data.score
  }));

  const analysis = analyzeComments(comments);
  await setCache(cacheKey, analysis);
  return analysis;
}

// --- Comment analysis ---

function analyzeComments(comments) {
  if (comments.length === 0) {
    return {
      count: 0,
      uniqueSubreddits: 0,
      subreddits: [],
      repetitionScore: 0,
      avgLength: 0,
      burstScore: 0,
      topSubreddits: [],
      sampleComments: []
    };
  }

  // Subreddit diversity
  const subCounts = {};
  comments.forEach(c => {
    subCounts[c.subreddit] = (subCounts[c.subreddit] || 0) + 1;
  });
  const uniqueSubreddits = Object.keys(subCounts).length;
  const topSubreddits = Object.entries(subCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, count]) => ({ name, count }));

  // Comment repetition detection using trigram similarity
  const repetitionScore = computeRepetition(comments.map(c => c.body));

  // Average comment length
  const avgLength = Math.round(
    comments.reduce((sum, c) => sum + c.body.length, 0) / comments.length
  );

  // Burst detection: how many comments in a 24h window
  const burstScore = computeBurstScore(comments.map(c => c.created));

  // Sample comments for tooltip (first 50 chars each)
  const sampleComments = comments.slice(0, 3).map(c => ({
    text: c.body.length > 80 ? c.body.substring(0, 80) + '…' : c.body,
    subreddit: c.subreddit,
    score: c.score
  }));

  return {
    count: comments.length,
    uniqueSubreddits,
    subreddits: Object.keys(subCounts),
    repetitionScore,
    avgLength,
    burstScore,
    topSubreddits,
    sampleComments
  };
}

function computeRepetition(texts) {
  if (texts.length < 2) return 0;

  // Normalize texts
  const normalized = texts.map(t =>
    t.toLowerCase().replace(/[^a-z0-9\s]/g, '').trim()
  );

  // Compare each pair using simple Jaccard similarity on word sets
  let totalSimilarity = 0;
  let comparisons = 0;

  for (let i = 0; i < normalized.length; i++) {
    const wordsA = new Set(normalized[i].split(/\s+/).filter(w => w.length > 2));
    for (let j = i + 1; j < normalized.length; j++) {
      const wordsB = new Set(normalized[j].split(/\s+/).filter(w => w.length > 2));
      const intersection = [...wordsA].filter(w => wordsB.has(w)).length;
      const union = new Set([...wordsA, ...wordsB]).size;
      if (union > 0) {
        totalSimilarity += intersection / union;
        comparisons++;
      }
    }
  }

  // Return 0-100 score (100 = all comments identical)
  return comparisons > 0 ? Math.round((totalSimilarity / comparisons) * 100) : 0;
}

function computeBurstScore(timestamps) {
  if (timestamps.length < 2) return 0;
  const sorted = [...timestamps].sort((a, b) => a - b);
  const DAY = 86400;

  // Sliding window: max comments within any 24h period
  let maxInWindow = 0;
  for (let i = 0; i < sorted.length; i++) {
    let count = 0;
    for (let j = i; j < sorted.length; j++) {
      if (sorted[j] - sorted[i] <= DAY) {
        count++;
      } else {
        break;
      }
    }
    maxInWindow = Math.max(maxInWindow, count);
  }

  return maxInWindow;
}

// --- Trust scoring ---

function computeTrustScore(about, comments) {
  let score = 0;
  const flags = [];

  // Account age scoring (0-3 points)
  const ageMonths = (Date.now() / 1000 - about.created) / (30 * 86400);
  if (ageMonths >= 24) { score += 3; }
  else if (ageMonths >= 12) { score += 2; }
  else if (ageMonths >= 6) { score += 1; }
  else { flags.push('New account'); }

  // Karma scoring (0-3 points)
  if (about.totalKarma >= 10000) { score += 3; }
  else if (about.totalKarma >= 1000) { score += 2; }
  else if (about.totalKarma >= 100) { score += 1; }
  else { flags.push('Very low karma'); }

  // Verified email (+1 point — unverified is a mild red flag)
  if (about.hasVerifiedEmail) { score += 1; }

  // Link-to-comment karma ratio: high link karma vs near-zero comment karma
  // is a classic pattern for accounts that submit promotional links but don't discuss
  if (about.linkKarma > about.commentKarma * 5 && about.linkKarma > 1000) {
    flags.push('High link-to-comment ratio');
  }

  // Username pattern: 4+ trailing digits is a common bot/sock-puppet pattern
  if (/\d{4,}$/.test(about.name)) {
    flags.push('Generic username pattern');
  }

  // Subreddit diversity (0-3 points)
  if (comments) {
    if (comments.uniqueSubreddits >= 8) { score += 3; }
    else if (comments.uniqueSubreddits >= 4) { score += 2; }
    else if (comments.uniqueSubreddits >= 2) { score += 1; }
    else { flags.push('Posts in very few subreddits'); }

    // Repetition penalty (0-2 points)
    if (comments.repetitionScore < 20) { score += 2; }
    else if (comments.repetitionScore < 40) { score += 1; }
    else { flags.push('Repetitive comments'); }

    // Burst penalty
    if (comments.burstScore >= 15) {
      flags.push('Burst posting detected');
    }
  }

  let level;
  if (comments) {
    // Full scoring with all data — max 12 points
    if (score >= 11) level = 'gold';
    else if (score >= 8) level = 'green';
    else if (score >= 5) level = 'yellow';
    else level = 'red';
  } else {
    // Quick scoring from about data only — max 7 points
    // Use scaled thresholds so normal accounts don't show red
    if (score >= 6) level = 'green';
    else if (score >= 4) level = 'yellow';
    else level = 'red';
  }

  const percent = Math.round((score / 12) * 100);
  return { score, maxScore: 12, percent, level, flags };
}

// --- Message handling ---

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'fetchUserAbout') {
    fetchUserAbout(msg.username)
      .then(data => sendResponse({ ok: true, data }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true; // async response
  }

  if (msg.type === 'fetchUserComments') {
    fetchUserComments(msg.username)
      .then(data => sendResponse({ ok: true, data }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (msg.type === 'computeTrustScore') {
    const trust = computeTrustScore(msg.about, msg.comments);
    sendResponse({ ok: true, data: trust });
    return false;
  }

  if (msg.type === 'computeQuickTrust') {
    // Preliminary score from about data only (no comment analysis)
    const trust = computeTrustScore(msg.about, null);
    sendResponse({ ok: true, data: trust });
    return false;
  }

  if (msg.type === 'getSettings') {
    chrome.storage.local.get('tv_settings', (result) => {
      sendResponse({
        ok: true,
        data: result.tv_settings || {
          enabled: true,
          showBadge: true,
          showTooltip: true,
          compactMode: false
        }
      });
    });
    return true;
  }

  if (msg.type === 'saveSettings') {
    chrome.storage.local.set({ tv_settings: msg.settings }, () => {
      sendResponse({ ok: true });
    });
    return true;
  }
});
