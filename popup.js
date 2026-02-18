// Reddit User Insight - Popup Script

const defaults = {
  enabled: true,
  showBadge: true,
  showTooltip: true,
  compactMode: false
};

const settingEnabled = document.getElementById('setting-enabled');
const settingBadges = document.getElementById('setting-badges');
const settingTooltips = document.getElementById('setting-tooltips');
const clearCacheBtn = document.getElementById('clear-cache');

// Load current settings
chrome.runtime.sendMessage({ type: 'getSettings' }, (res) => {
  const s = res?.ok ? res.data : defaults;
  settingEnabled.checked = s.enabled;
  settingBadges.checked = s.showBadge;
  settingTooltips.checked = s.showTooltip;
});

// Save on change
function saveSettings() {
  const settings = {
    enabled: settingEnabled.checked,
    showBadge: settingBadges.checked,
    showTooltip: settingTooltips.checked,
    compactMode: false
  };
  chrome.runtime.sendMessage({ type: 'saveSettings', settings });
}

settingEnabled.addEventListener('change', saveSettings);
settingBadges.addEventListener('change', saveSettings);
settingTooltips.addEventListener('change', saveSettings);

// Clear cache
clearCacheBtn.addEventListener('click', () => {
  chrome.storage.local.get(null, (items) => {
    const keysToRemove = Object.keys(items).filter(
      k => k.startsWith('about_') || k.startsWith('comments_')
    );
    if (keysToRemove.length > 0) {
      chrome.storage.local.remove(keysToRemove, () => {
        clearCacheBtn.textContent = `Cleared ${keysToRemove.length} entries`;
        setTimeout(() => {
          clearCacheBtn.textContent = 'Clear Cached Data';
        }, 2000);
      });
    } else {
      clearCacheBtn.textContent = 'Cache is empty';
      setTimeout(() => {
        clearCacheBtn.textContent = 'Clear Cached Data';
      }, 2000);
    }
  });
});
