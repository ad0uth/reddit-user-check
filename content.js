// TrueVoice for Reddit - Content Script
// Detects usernames on the page and injects trust badges + hover tooltips

(function () {
  'use strict';

  // Avoid running in iframes
  if (window.self !== window.top) return;

  // Track which usernames we've already processed (by element)
  const processedElements = new WeakSet();

  // Cache for fetched data to avoid re-requesting within a page session
  const userDataCache = new Map();

  // Currently visible tooltip
  let activeTooltip = null;
  let tooltipTimeout = null;
  let hideTimeout = null;

  // --- Settings ---
  let settings = {
    enabled: true,
    showBadge: true,
    showTooltip: true,
    compactMode: false
  };

  // Load settings
  chrome.runtime.sendMessage({ type: 'getSettings' }, (res) => {
    if (res?.ok && res.data) {
      settings = res.data;
      if (settings.enabled) {
        init();
      }
    } else {
      init();
    }
  });

  // Listen for setting changes
  chrome.storage.onChanged.addListener((changes) => {
    if (changes.tv_settings) {
      settings = changes.tv_settings.newValue || settings;
      if (!settings.enabled) {
        // Remove all badges
        document.querySelectorAll('.tv-badge').forEach(el => el.remove());
        document.querySelectorAll('.tv-tooltip').forEach(el => el.remove());
      }
    }
  });

  // --- Helpers ---

  function formatAge(createdUtc) {
    const seconds = Date.now() / 1000 - createdUtc;
    const days = Math.floor(seconds / 86400);
    if (days >= 365) return Math.floor(days / 365) + 'y';
    if (days >= 30) return Math.floor(days / 30) + 'mo';
    return days + 'd';
  }

  function formatKarma(karma) {
    if (karma >= 1000000) return (karma / 1000000).toFixed(1) + 'M';
    if (karma >= 1000) return (karma / 1000).toFixed(1) + 'k';
    return String(karma);
  }

  function extractUsername(element) {
    // Get username from the link href or text content
    const href = element.getAttribute('href') || '';
    const match = href.match(/\/u(?:ser)?\/([A-Za-z0-9_-]+)/);
    if (match) return match[1];

    // Fallback: text content
    const text = element.textContent.trim();
    const textMatch = text.match(/^u\/([A-Za-z0-9_-]+)$/);
    if (textMatch) return textMatch[1];

    return null;
  }

  // Track which containers already have a badge for a given username
  const badgedContainers = new WeakMap(); // container -> Set<username>

  // --- Username selectors for different Reddit versions ---

  function getUsernameElements() {
    const allLinks = document.querySelectorAll('a[href*="/user/"], a[href*="/u/"]');
    const usernameLinks = [];

    for (const link of allLinks) {
      // Skip if already processed
      if (processedElements.has(link)) continue;

      const href = link.getAttribute('href') || '';
      if (!href.match(/\/u(?:ser)?\/[A-Za-z0-9_-]+\/?$/)) continue;

      // Skip links inside our own badges/tooltips
      if (link.closest('.tv-badge, .tv-tooltip')) continue;

      // Must contain visible username text (not just an avatar/icon)
      const text = link.textContent.trim();
      if (!text || text.length < 2) continue;
      // Should look like a username — starts with "u/" or matches the username from href
      const username = extractUsername(link);
      if (!username) continue;
      if (!text.includes(username) && !text.startsWith('u/')) continue;

      if (['AutoModerator', '[deleted]', 'reddit'].includes(username)) continue;

      // Prevent duplicate badges in the same comment/post container
      const container = link.closest('shreddit-comment, shreddit-post, .comment, .thing, .Comment, [data-testid="comment"], [data-testid="post-container"], article') || link.parentElement;
      if (container) {
        if (!badgedContainers.has(container)) {
          badgedContainers.set(container, new Set());
        }
        const userSet = badgedContainers.get(container);
        if (userSet.has(username)) {
          processedElements.add(link);
          continue; // Already have a badge for this user in this container
        }
        userSet.add(username);
      }

      usernameLinks.push(link);
    }

    return usernameLinks;
  }

  // --- Badge creation ---

  function createBadge(username) {
    const badge = document.createElement('span');
    badge.className = 'tv-badge tv-badge--loading';
    badge.dataset.username = username;

    // Start with just a loading dot — no text until data arrives
    badge.innerHTML = `<span class="tv-dot tv-dot--pending"></span><span class="tv-badge-text"></span>`;

    return badge;
  }

  function updateBadge(badge, about, level) {
    badge.classList.remove('tv-badge--loading');

    const dot = badge.querySelector('.tv-dot');
    if (dot) {
      dot.classList.remove('tv-dot--pending');
      dot.classList.add(`tv-dot--${level}`);
    }

    const text = badge.querySelector('.tv-badge-text');
    if (text) {
      text.textContent = `${formatAge(about.created)} · ${formatKarma(about.totalKarma)}`;
    }
  }

  // --- Helpers ---

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // --- Tooltip ---

  function createTooltip(username, about, comments, trust) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tv-tooltip';

    const ageMonths = Math.floor((Date.now() / 1000 - about.created) / (30 * 86400));
    const ageText = ageMonths >= 12
      ? `${Math.floor(ageMonths / 12)} year${Math.floor(ageMonths / 12) !== 1 ? 's' : ''}, ${ageMonths % 12} month${ageMonths % 12 !== 1 ? 's' : ''}`
      : `${ageMonths} month${ageMonths !== 1 ? 's' : ''}`;

    // Trust level label
    const levelLabels = {
      green: 'Trusted',
      yellow: 'Moderate',
      red: 'Suspicious'
    };
    const levelLabel = levelLabels[trust.level] || 'Unknown';

    // Avatar — clean up Reddit's noisy icon URL query params
    const avatarUrl = about.iconUrl
      ? about.iconUrl.replace(/\?.*$/, '') // strip query string (size/format params)
      : null;

    const userBadgesHtml = [
      about.isMod  ? '<span class="tv-user-badge tv-user-badge--mod">MOD</span>'  : '',
      about.isGold ? '<span class="tv-user-badge tv-user-badge--gold">GOLD</span>' : ''
    ].join('');

    // Build metrics rows
    let metricsHtml = `
      <div class="tv-tooltip-header">
        ${avatarUrl ? `<img class="tv-avatar" src="${avatarUrl}" alt="">` : ''}
        <div class="tv-tooltip-user">
          <span class="tv-tooltip-username">u/${escapeHtml(about.name)}</span>
          ${userBadgesHtml ? `<div class="tv-user-badges">${userBadgesHtml}</div>` : ''}
        </div>
        <span class="tv-tooltip-trust tv-trust--${trust.level}">${levelLabel}</span>
      </div>
      <div class="tv-tooltip-divider"></div>
      <div class="tv-tooltip-metrics">
        <div class="tv-metric">
          <span class="tv-metric-label">Account Age</span>
          <span class="tv-metric-value">${ageText}</span>
        </div>
        <div class="tv-metric">
          <span class="tv-metric-label">Karma</span>
          <span class="tv-metric-value">${formatKarma(about.commentKarma)} comment · ${formatKarma(about.linkKarma)} post</span>
        </div>
    `;

    if (comments) {
      // Subreddit diversity bar
      const diversityPct = Math.min(100, Math.round((comments.uniqueSubreddits / 10) * 100));
      const diversityColor = comments.uniqueSubreddits >= 6 ? 'green' : comments.uniqueSubreddits >= 3 ? 'yellow' : 'red';

      metricsHtml += `
        <div class="tv-metric">
          <span class="tv-metric-label">Subreddit Diversity</span>
          <span class="tv-metric-value">${comments.uniqueSubreddits} unique subs in last ${comments.count} comments</span>
          <div class="tv-bar"><div class="tv-bar-fill tv-bar--${diversityColor}" style="width:${diversityPct}%"></div></div>
        </div>
      `;

      // Repetition bar
      const repColor = comments.repetitionScore < 20 ? 'green' : comments.repetitionScore < 40 ? 'yellow' : 'red';
      metricsHtml += `
        <div class="tv-metric">
          <span class="tv-metric-label">Comment Variety</span>
          <span class="tv-metric-value">${100 - comments.repetitionScore}% unique</span>
          <div class="tv-bar"><div class="tv-bar-fill tv-bar--${repColor}" style="width:${100 - comments.repetitionScore}%"></div></div>
        </div>
      `;

      // Top subreddits
      if (comments.topSubreddits && comments.topSubreddits.length > 0) {
        const subsHtml = comments.topSubreddits
          .map(s => `<span class="tv-sub-tag">r/${s.name} <span class="tv-sub-count">${s.count}</span></span>`)
          .join('');
        metricsHtml += `
          <div class="tv-metric">
            <span class="tv-metric-label">Top Subreddits</span>
            <div class="tv-sub-tags">${subsHtml}</div>
          </div>
        `;
      }

      // Burst warning
      if (comments.burstScore >= 10) {
        metricsHtml += `
          <div class="tv-metric tv-metric--warning">
            <span class="tv-metric-label">Activity Burst</span>
            <span class="tv-metric-value">${comments.burstScore} comments in 24h window</span>
          </div>
        `;
      }
    }

    // Flags
    if (trust.flags && trust.flags.length > 0) {
      const flagsHtml = trust.flags.map(f => `<span class="tv-flag">${f}</span>`).join('');
      metricsHtml += `
        <div class="tv-tooltip-divider"></div>
        <div class="tv-flags">${flagsHtml}</div>
      `;
    }

    // Sample recent comments
    if (comments && comments.sampleComments && comments.sampleComments.length > 0) {
      const samplesHtml = comments.sampleComments.map(c => `
        <div class="tv-sample-comment">
          <span class="tv-sample-sub">r/${escapeHtml(c.subreddit)}</span>
          <span class="tv-sample-text">${escapeHtml(c.text)}</span>
        </div>
      `).join('');
      metricsHtml += `
        <div class="tv-tooltip-divider"></div>
        <div class="tv-metric">
          <span class="tv-metric-label">Recent Comments</span>
          <div class="tv-sample-comments">${samplesHtml}</div>
        </div>
      `;
    }

    metricsHtml += `
      </div>
      <div class="tv-tooltip-footer">
        <span class="tv-tooltip-score">Trust Score: ${trust.percent}%</span>
      </div>
    `;

    tooltip.innerHTML = metricsHtml;
    return tooltip;
  }

  function showTooltip(badge, username) {
    clearTimeout(hideTimeout);

    // If already showing this tooltip, do nothing
    if (activeTooltip && activeTooltip.dataset.username === username) return;

    // Remove existing tooltip
    removeTooltip();

    const cached = userDataCache.get(username);
    if (!cached) return;

    const { about, comments, trust } = cached;
    if (!about || !trust) return;

    const tooltip = createTooltip(username, about, comments, trust);
    tooltip.dataset.username = username;

    // Position tooltip near the badge
    document.body.appendChild(tooltip);
    positionTooltip(tooltip, badge);

    // Keep tooltip visible when hovering over it
    tooltip.addEventListener('mouseenter', () => {
      clearTimeout(hideTimeout);
    });
    tooltip.addEventListener('mouseleave', () => {
      hideTimeout = setTimeout(removeTooltip, 200);
    });

    activeTooltip = tooltip;
  }

  function positionTooltip(tooltip, anchor) {
    const rect = anchor.getBoundingClientRect();
    const scrollY = window.scrollY;
    const scrollX = window.scrollX;

    // Position below the badge
    let top = rect.bottom + scrollY + 6;
    let left = rect.left + scrollX;

    // Make sure tooltip doesn't go off-screen right
    const tooltipWidth = 320;
    if (left + tooltipWidth > window.innerWidth + scrollX - 16) {
      left = window.innerWidth + scrollX - tooltipWidth - 16;
    }

    // If it would go below viewport, show above instead
    const tooltipHeight = 300; // estimate
    if (rect.bottom + tooltipHeight > window.innerHeight) {
      top = rect.top + scrollY - tooltipHeight - 6;
    }

    tooltip.style.top = top + 'px';
    tooltip.style.left = Math.max(8, left) + 'px';
  }

  function removeTooltip() {
    if (activeTooltip) {
      activeTooltip.remove();
      activeTooltip = null;
    }
  }

  // --- Data fetching pipeline ---

  // Phase 1: Fetch about data only (fast — one API call per user)
  async function fetchAboutAndScore(username, badge) {
    try {
      const aboutRes = await chrome.runtime.sendMessage({
        type: 'fetchUserAbout',
        username
      });

      if (!aboutRes?.ok) return;
      const about = aboutRes.data;

      // Preliminary trust score from about data alone
      const trustRes = await chrome.runtime.sendMessage({
        type: 'computeQuickTrust',
        about
      });
      const trust = trustRes?.ok ? trustRes.data : { score: 0, maxScore: 12, percent: 0, level: 'green', flags: [] };

      userDataCache.set(username, { about, comments: null, trust });
      updateBadge(badge, about, trust.level);
    } catch (err) {
      console.debug('[TrueVoice] Error fetching about for', username, err);
    }
  }

  // Phase 2: Fetch comments and refine trust score (on hover)
  async function fetchCommentsAndRefine(username, badge) {
    const cached = userDataCache.get(username);
    if (!cached?.about || cached.comments) return; // already done or no about data

    try {
      const commentsRes = await chrome.runtime.sendMessage({
        type: 'fetchUserComments',
        username
      });
      const comments = commentsRes?.ok ? commentsRes.data : null;

      const trustRes = await chrome.runtime.sendMessage({
        type: 'computeTrustScore',
        about: cached.about,
        comments
      });
      const trust = trustRes?.ok ? trustRes.data : cached.trust;

      userDataCache.set(username, { about: cached.about, comments, trust });
      updateBadge(badge, cached.about, trust.level);
    } catch (err) {
      console.debug('[TrueVoice] Error fetching comments for', username, err);
    }
  }

  // --- Main processing ---

  function processUsernames() {
    if (!settings.enabled || !settings.showBadge) return;

    const elements = getUsernameElements();

    for (const el of elements) {
      processedElements.add(el);

      const username = extractUsername(el);
      if (!username) continue;

      // Create and insert badge (loading state, no data yet)
      const badge = createBadge(username);

      // Insert badge after the username link
      el.after(badge);

      // Set up hover events for tooltip + lazy comment fetch
      if (settings.showTooltip) {
        const showHandler = () => {
          // Trigger Phase 2 (comments) on hover
          fetchCommentsAndRefine(username, badge);
          tooltipTimeout = setTimeout(() => showTooltip(badge, username), 300);
        };
        const hideHandler = () => {
          clearTimeout(tooltipTimeout);
          hideTimeout = setTimeout(removeTooltip, 200);
        };

        badge.addEventListener('mouseenter', showHandler);
        badge.addEventListener('mouseleave', hideHandler);
        el.addEventListener('mouseenter', showHandler);
        el.addEventListener('mouseleave', hideHandler);
      }

      // Phase 1: Fetch about data when badge enters viewport.
      // After Phase 1 completes, automatically kick off Phase 2 (comment
      // analysis) after a short delay so the full trust score is shown
      // without requiring the user to hover over every badge.
      const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            obs.unobserve(entry.target);
            fetchAboutAndScore(username, badge).then(() => {
              setTimeout(() => fetchCommentsAndRefine(username, badge), 1500);
            });
          }
        });
      }, { rootMargin: '200px' });

      observer.observe(badge);
    }
  }

  // --- Initialization ---

  function init() {
    // Initial scan
    processUsernames();

    // Watch for dynamically loaded content (infinite scroll, expanding comments)
    const observer = new MutationObserver((mutations) => {
      let shouldProcess = false;
      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          shouldProcess = true;
          break;
        }
      }
      if (shouldProcess) {
        // Debounce processing
        clearTimeout(init._debounceTimer);
        init._debounceTimer = setTimeout(processUsernames, 500);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  // Close tooltip on scroll or click elsewhere
  document.addEventListener('scroll', () => {
    clearTimeout(tooltipTimeout);
    removeTooltip();
  }, { passive: true });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.tv-tooltip, .tv-badge')) {
      removeTooltip();
    }
  });

})();
