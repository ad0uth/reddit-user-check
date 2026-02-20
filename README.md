# TrueVoice for Reddit

A Chrome extension that spots bots, corporate shills, and astroturf accounts on Reddit. Trust badges show account age, karma, and behavioral signals at a glance.

## What It Shows

**Inline badge** next to every username:
- A colored indicator dot (gold star / green / red)
- Account age and karma in compact form (e.g., `2y · 8.3k`)

**Hover tooltip** with detailed breakdown:
- Account age (exact)
- Karma split (comment vs post)
- Subreddit diversity — how many unique subs they post in
- Comment variety — detects repetitive posting patterns
- Activity frequency indicators
- Top subreddits with post counts

## Indicators

Each account gets a trust score (shown as a percentage) based on:

| Metric | Points | What it measures |
|---|---|---|
| Account age | 0–3 | Older accounts score higher |
| Karma | 0–3 | Total karma across posts and comments |
| Verified email | 0–1 | Unverified accounts score lower |
| Subreddit diversity | 0–3 | Number of unique subs in recent comments |
| Comment variety | 0–2 | Low repetition in comment text |

**Gold (≥83%):** Top-scoring established account with excellent track record.
**Green (≥33%):** Active account with reasonable history and diversity.
**Red (<33%):** Very new, low karma, or repetitive posting patterns.

Flags (no points deducted, shown separately):
- High link-to-comment karma ratio — common shill/promoter pattern
- Generic username pattern — 4+ trailing digits
- Posts in very few subreddits
- Burst posting detected — 15+ comments in a 24h window

## Performance

- **Lazy loading:** Only fetches data for usernames visible in the viewport (IntersectionObserver)
- **Two-phase fetch:** Account info loads first (fast), comment analysis loads on hover
- **24h cache:** All data cached locally to minimize API calls
- **Rate limiting:** Serialized requests with polite delays to respect Reddit's API
- **Debounced DOM scanning:** Handles infinite scroll without performance impact

## Install

1. Clone or download this repo
2. Open `chrome://extensions/` in Chrome
3. Enable **Developer mode** (top right)
4. Click **Load unpacked** and select this folder
5. Navigate to Reddit — badges appear automatically

## Settings

Click the extension icon for options:
- Toggle badges on/off
- Toggle hover tooltips on/off
- Clear cached data

## Privacy

- Uses Reddit's **public** JSON API only
- All data cached **locally** in chrome.storage.local
- No data sent to any third party
- No tracking or analytics
- See [Privacy Policy](privacy-policy.html) for full details

## Files

```
manifest.json          Chrome extension manifest (Manifest V3)
background.js          Service worker — API calls, caching, scoring
content.js             Content script — username detection, badge injection
styles.css             All visual styles (badges, tooltips, dark mode)
popup.html/js          Extension popup with settings
privacy-policy.html    Privacy policy for Chrome Web Store
icons/                 Extension icons (16, 48, 128px)
store_assets/          Chrome Web Store promotional images
generate_icons.py      Script to regenerate icons
generate_promo.py      Script to regenerate promotional tile
STORE_LISTING.md       Chrome Web Store listing copy
```
