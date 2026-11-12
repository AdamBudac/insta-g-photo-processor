# GitHub Pages pre Insta G Photo Processor

Web je jedna statická stránka [index.html](../index.html) s lokálnymi knižnicami v [assets](./assets/). Frontend používa i18next na okamžité prepínanie EN/SK/CS bez reloadu, Bootstrap a vlastné CSS. Nie je potrebný Node.js, npm, frontendový build ani server aplikácie.

## Prvé zverejnenie cez GitHub Desktop a web GitHubu

1. V GitHub Desktop skontroluj a commitni projektové súbory. Tlačidlom **Push origin** ich odošli do svojho repozitára. Dôležité sú koreňový `index.html`, `.nojekyll`, celý `docs/assets/` a tri koreňové `README-user*.md` súbory. Ignorované `.venv`, `build`, `dist` a pracovné dáta sa nenahrávajú.
2. Otvor daný repozitár v prehliadači na GitHube. Nastavenie hostingu sa robí tam; GitHub Desktop slúži na prácu s lokálnymi súbormi a ich odoslanie.
3. Vyber **Settings → Pages**.
4. V **Build and deployment → Source** vyber **Deploy from a branch**.
5. Ako **Branch** zvoľ `main` alebo inú vetvu, na ktorej máš web. Ako priečinok nastav **/(root)**, nie `/docs`. Klikni **Save**.
6. Počkaj na dokončenie nasadenia. Stránka Pages zobrazí výslednú adresu; priebeh a prípadné chyby nájdeš aj na karte **Actions**. GitHub vykoná samotné publikovanie, hoci web nepotrebuje frontendový build.
7. Projektový web bude typicky na `https://TVOJ_UCET.github.io/NAZOV_REPOZITARA/`. Názov repozitára nemusí byť `TVOJ_UCET.github.io`; ten má osobitný význam pre web účtu.
8. Ak je dostupná voľba **Enforce HTTPS**, nechaj ju zapnutú. V nastavení repozitára môžeš neskôr pridať adresu webu do časti **About → Website**.

Nasadenie sa môže prejaviť s oneskorením. Ak zmena ešte nie je viditeľná, najprv skontroluj stav príslušného nasadenia a následne obnov stránku. GitHub Pages je pre verejné repozitáre dostupný aj v pláne GitHub Free.

## Ďalšie aktualizácie

Po úprave webu alebo používateľského návodu stačí v GitHub Desktop opäť vykonať commit a **Push origin** do zvolenej vetvy. GitHub Pages z nej automaticky zverejní aktuálny obsah. Nastavenie Pages netreba zakaždým opakovať.

Používateľské návody majú jediný zdroj:

- [English](../README-user.md)
- [Slovenčina](../README-user-sk.md)
- [Čeština](../README-user-cz.md)

Tie isté súbory číta web priamo z koreňa publikovaného projektu a pribalia sa do EXE. Nie sú tu ďalšie kópie ani PDF, ktoré by bolo treba ručne aktualizovať. Po zmene návodu treba pre aktualizáciu pomocníka vo Windows znovu zostaviť EXE; web získa zmenu po pushnutí.

## Odkazy GitHub a Download

Na štandardnej adrese `*.github.io/NAZOV_REPOZITARA/` web automaticky odvodí URL repozitára. Tlačidlo Download smeruje na asset najnovšieho GitHub Release s názvom `InstaGPhotoProcessor.exe`.

Samotné GitHub Pages nezverejňuje vydania aplikácie. Pripravené EXE nahraj do **Releases** tak, ako to už bežne robíš. Ak sa názov assetu zmení, uprav `downloadAsset` v [config.js](./assets/js/config.js).

Pre lokálny náhľad alebo vlastnú doménu môžeš do `repositoryUrl` v [config.js](./assets/js/config.js) doplniť presnú adresu `https://github.com/UCET/REPOZITAR`. Ak používaš inú vetvu než `main`, uprav tam aj `branch` pre odkazy na zdrojové README. Prázdne `repositoryUrl` na lokálnom náhľade deaktivuje externé GitHub/download tlačidlá; pri štandardnom projektovom GitHub Pages hostingu sa odvodia automaticky. Nevkladaj žiadne tokeny ani prihlasovacie údaje.

## Lokálny náhľad

Z koreňa repozitára spusti v PowerShelli:

```powershell
.\.venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1
```

Otvor `http://127.0.0.1:8765/`. Server ukončíš cez Ctrl+C. Otváranie cez `file://` nie je vhodné, pretože prehliadač môže blokovať načítanie Markdown návodu cez fetch.

Jazyk aj vzhľad sa ukladajú iba v localStorage prehliadača. Predvolený jazyk je angličtina, predvolený vzhľad System. Knižnice, fotografie, preklady a screenshoty sú lokálne súbory webu; na jeho vykreslenie netreba externé CDN. Autori fotografií a podmienky ich použitia sú v [atribúciách](./assets/images/ATTRIBUTION.md); verzie knižníc a licencie v [vendor](./assets/vendor/).

## Oficiálne zdroje

Overené 11. 11. 2026:

- [Čo je GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
- [Nastavenie publikovanej vetvy a priečinka](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Odkaz na najnovší Release a jeho súbor](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases)

V rámci tejto implementácie agent nič necommitoval, nepushoval, nevytváral Release a neaktivoval hosting. Všetky kroky publikovania zostávajú na vlastníkovi repozitára.
