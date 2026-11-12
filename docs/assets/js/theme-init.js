/* Apply the theme before CSS paints; storage may be unavailable in private browsing. */
(() => {
  'use strict';
  const key = 'insta-g.theme';
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  const valid = value => ['system', 'light', 'dark'].includes(value);
  let preference = 'system';
  try { const saved = localStorage.getItem(key); if (valid(saved)) preference = saved; } catch {}
  const apply = () => {
    const theme = preference === 'system' ? (media.matches ? 'dark' : 'light') : preference;
    document.documentElement.dataset.bsTheme = theme;
    document.documentElement.style.colorScheme = theme;
  };
  window.siteTheme = {
    get: () => preference,
    set(value) {
      preference = valid(value) ? value : 'system';
      try { localStorage.setItem(key, preference); } catch {}
      apply();
    },
  };
  media.addEventListener('change', () => { if (preference === 'system') apply(); });
  apply();
})();
