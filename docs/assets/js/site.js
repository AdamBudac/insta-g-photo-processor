(() => {
  'use strict';
  const languages = ['en', 'sk', 'cs'];
  const guides = {en: 'README-user.md', sk: 'README-user-sk.md', cs: 'README-user-cz.md'};
  const config = window.SITE_CONFIG;
  const guideCache = new Map();
  let languageRevision = 0;
  let currentLanguage = 'en';
  const storage = {
    get(key, fallback) { try { return localStorage.getItem(key) || fallback; } catch { return fallback; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch {} },
  };
  const t = key => i18next.t(key);

  function repositoryUrl() {
    if (config.repositoryUrl) {
      try {
        const url = new URL(config.repositoryUrl);
        if (url.protocol === 'https:' && url.hostname === 'github.com' &&
            /^\/[\w.-]+\/[\w.-]+\/?$/.test(url.pathname)) {
          return url.origin + url.pathname.replace(/\/$/, '').replace(/\.git$/, '');
        }
      } catch {}
    }
    if (location.hostname.endsWith('.github.io')) {
      const owner = location.hostname.slice(0, -'.github.io'.length);
      const project = location.pathname.split('/').filter(Boolean)[0] || `${owner}.github.io`;
      if (/^[\w.-]+$/.test(owner) && /^[\w.-]+$/.test(project)) {
        return `https://github.com/${owner}/${project}`;
      }
    }
    return null;
  }

  function updateLinks() {
    const repository = repositoryUrl();
    const destinations = repository ? {
      repository, issues: `${repository}/issues`, releases: `${repository}/releases`,
      download: `${repository}/releases/latest/download/${encodeURIComponent(config.downloadAsset)}`,
    } : {};
    document.querySelectorAll('[data-repo-link]').forEach(link => {
      const href = destinations[link.dataset.repoLink];
      link.classList.toggle('disabled', !href);
      if (href) {
        link.href = href;
        link.removeAttribute('aria-disabled');
        link.removeAttribute('tabindex');
        link.removeAttribute('title');
      } else {
        link.removeAttribute('href');
        link.setAttribute('aria-disabled', 'true');
        link.setAttribute('tabindex', '-1');
        link.title = t('links.pending');
      }
    });
    const source = document.getElementById('guide-source-link');
    source.href = repository
      ? `${repository}/blob/${encodeURIComponent(config.branch)}/${guides[currentLanguage]}`
      : guides[currentLanguage];
  }

  function translateDocument() {
    document.documentElement.lang = currentLanguage;
    document.title = t('meta.title');
    document.querySelector('meta[name="description"]').content = t('meta.description');
    document.querySelectorAll('[data-i18n]').forEach(element => {
      element.textContent = t(element.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-attr]').forEach(element => {
      element.dataset.i18nAttr.split(';').forEach(rule => {
        const separator = rule.indexOf(':');
        if (separator > 0) element.setAttribute(rule.slice(0, separator).trim(), t(rule.slice(separator + 1).trim()));
      });
    });
    document.getElementById('language-select').value = currentLanguage;
    document.querySelectorAll('[data-version]').forEach(element => { element.textContent = `v${config.version}`; });
    updateLinks();
  }

  function loadGuide(language) {
    if (!guideCache.has(language)) {
      guideCache.set(language, fetch(guides[language], {credentials: 'same-origin'})
        .then(response => {
          if (!response.ok) throw new Error(`Guide HTTP ${response.status}`);
          return response.text();
        })
        .then(markdown => DOMPurify.sanitize(marked.parse(markdown.replace(/^\uFEFF/, '')),
          {USE_PROFILES: {html: true}}))
        .catch(error => { guideCache.delete(language); throw error; }));
    }
    return guideCache.get(language);
  }

  function guidePosition() {
    const article = document.getElementById('guide-content');
    const bounds = article.getBoundingClientRect();
    if (bounds.top > 150 || bounds.bottom < 150) return null;
    const chapters = [...article.querySelectorAll('h2')];
    const visible = chapters.filter(heading => heading.getBoundingClientRect().top <= 170);
    return visible.length ? visible[visible.length - 1].id : null;
  }

  async function renderGuide(language, revision, chapter) {
    const status = document.getElementById('guide-status');
    const article = document.getElementById('guide-content');
    status.textContent = t('guide.loading');
    try {
      const html = await loadGuide(language);
      if (revision !== languageRevision) return;
      article.innerHTML = html;
      const toc = document.getElementById('guide-toc');
      toc.replaceChildren();
      article.querySelectorAll('h2').forEach((heading, index) => {
        heading.id = `guide-chapter-${index}`;
        const link = document.createElement('a');
        link.href = `#${heading.id}`;
        link.textContent = heading.textContent;
        toc.append(link);
      });
      article.querySelectorAll('a[href]').forEach(link => {
        if (link.origin !== location.origin) { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
      });
      status.textContent = '';
      article.setAttribute('lang', language);
      if (chapter) document.getElementById(chapter)?.scrollIntoView({behavior: 'instant', block: 'start'});
      if (location.hash.startsWith('#guide-chapter-') && !chapter) {
        document.getElementById(location.hash.slice(1))?.scrollIntoView({behavior: 'instant'});
      }
    } catch {
      if (revision !== languageRevision) return;
      article.replaceChildren();
      document.getElementById('guide-toc').replaceChildren();
      status.textContent = t('guide.error');
    }
  }

  async function changeLanguage(language) {
    if (!languages.includes(language)) return;
    const revision = ++languageRevision;
    const chapter = guidePosition();
    await i18next.changeLanguage(language);
    if (revision !== languageRevision) return;
    currentLanguage = language;
    storage.set('insta-g.language', language);
    translateDocument();
    updateSplit();
    await renderGuide(language, revision, chapter);
  }

  function updateSplit() {
    const input = document.getElementById('split-count');
    const count = Number(input.value);
    const preview = document.getElementById('split-preview');
    preview.style.setProperty('--split-count', count);
    document.getElementById('split-count-label').textContent = i18next.t('examples.tileCount', {count});
    const lines = preview.querySelector('.split-lines');
    const labels = preview.querySelector('.split-labels');
    lines.replaceChildren();
    labels.replaceChildren();
    for (let index = 0; index < count; index++) {
      const label = document.createElement('span');
      label.textContent = String(index + 1).padStart(2, '0');
      label.style.left = `${(index + .5) / count * 100}%`;
      labels.append(label);
      if (index > 0) {
        const line = document.createElement('span');
        line.style.left = `${index / count * 100}%`;
        lines.append(line);
      }
    }
  }

  function interactions() {
    document.getElementById('language-select').addEventListener('change', event => changeLanguage(event.target.value));
    const theme = document.getElementById('theme-select');
    theme.value = window.siteTheme.get();
    theme.addEventListener('change', event => window.siteTheme.set(event.target.value));
    document.getElementById('split-count').addEventListener('input', updateSplit);
    document.querySelectorAll('[data-expand]').forEach(button => button.addEventListener('click', () => {
      document.getElementById('expand-demo').classList.toggle('bg-blur', button.dataset.expand === 'blur');
      document.getElementById('expand-demo').classList.toggle('bg-solid', button.dataset.expand === 'solid');
      document.querySelectorAll('[data-expand]').forEach(item => {
        item.setAttribute('aria-pressed', String(item === button));
        item.classList.toggle('active', item === button);
      });
    }));
    const dialog = document.getElementById('image-lightbox');
    let trigger = null;
    document.querySelectorAll('[data-lightbox]').forEach(button => button.addEventListener('click', () => {
      trigger = button;
      const picture = document.getElementById('lightbox-image');
      picture.src = button.dataset.lightbox;
      picture.alt = t(button.dataset.lightboxAltKey || 'gui.imageAlt');
      document.getElementById('lightbox-caption').textContent = picture.alt;
      dialog.showModal();
      document.getElementById('lightbox-close').focus();
    }));
    document.getElementById('lightbox-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener('close', () => trigger?.focus());
    document.querySelectorAll('#main-nav a[href^="#"]').forEach(link => link.addEventListener('click', () => {
      const menu = document.getElementById('main-nav');
      if (menu.classList.contains('show')) bootstrap.Collapse.getOrCreateInstance(menu).hide();
    }));
    document.getElementById('guide-content').addEventListener('click', event => {
      const link = event.target.closest('a[href]');
      if (!link) return;
      const filename = new URL(link.href).pathname.split('/').pop();
      const language = languages.find(code => guides[code] === filename);
      if (language) { event.preventDefault(); changeLanguage(language); }
    });
  }

  async function init() {
    const saved = storage.get('insta-g.language', 'en');
    currentLanguage = languages.includes(saved) ? saved : 'en';
    await i18next.init({lng: currentLanguage, fallbackLng: 'en', supportedLngs: languages,
      keySeparator: false, resources: window.SITE_TRANSLATIONS, interpolation: {escapeValue: false}});
    interactions();
    translateDocument();
    updateSplit();
    await renderGuide(currentLanguage, ++languageRevision, null);
    languages.filter(language => language !== currentLanguage).forEach(language => loadGuide(language).catch(() => {}));
    document.documentElement.dataset.siteReady = 'true';
  }
  init().catch(error => { console.error('Site initialization failed:', error); });
})();
