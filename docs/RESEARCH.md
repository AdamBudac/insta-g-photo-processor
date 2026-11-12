# Technický výskum

## Konkrétne odkazy na repozitár a vydanie — 12. 11. 2026

- Používateľ potvrdil [repozitár](https://github.com/AdamBudac/insta-g-photo-processor), [vydanie v1.0.0](https://github.com/AdamBudac/insta-g-photo-processor/releases/tag/v1.0.0) a [priamy EXE súbor](https://github.com/AdamBudac/insta-g-photo-processor/releases/download/v1.0.0/InstaGPhotoProcessor.exe). HTTP HEAD na súbor vrátil 200, application/octet-stream a 76 999 277 B. Lokálne Git referencie potvrdili main aj origin/main.
- Explicitná repositoryUrl aktivuje tlačidlá aj mimo GitHub Pages. releaseTag smeruje download a poznámky na rovnaké konkrétne vydanie, aby sa číslo prezentovanej aplikácie neodlišovalo od stiahnutého súboru. Pri prázdnom tagu ostáva pôvodný fallback na latest.
- Tri browser scenáre v EN/SK/CS overili lokálne aj projektové cesty, všetky odkazy a kompatibilný fallback; syntax a IDE diagnostika JavaScriptu bez chýb. Zmena sa týka webovej konfigurácie a URL, aplikačný kód a EXE sa nemenili.

## Audit projektu a opravy rozloženia webu — 12. 11. 2026

- [PyPA: src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) rozlišuje importovateľný balík a jeho nadradený zdrojový adresár. Názov balíka insta_g sa nemení. Prípadný budúci presun by používal src/insta_g a upravil packaging, build a editable inštaláciu; súčasný flat layout je platný a táto dodávka ho zachováva.
- [Git ignore pravidlá](https://git-scm.com/docs/gitignore) boli overené skutočným check-ignore v oddelenom testovacom repozitári, keďže koreň projektu zatiaľ nemá .git. Globálne *.spec je redundantné pri --specpath build; odstránenie umožní prípadnú budúcu ručnú build konfiguráciu verzovať. Windows Desktop.ini a Thumbs.db nemajú byť súčasťou zdroja. Prenosné .vscode úlohy, lock súbory, webové knižnice a testové fixtures zostávajú viditeľné.
- Pracovné .pytest_cache a .pytest-tmp* sú obnoviteľné dáta pytestu. .dev-data je explicitná vývojová relácia používaná spúšťacou úlohou, nie predvolené Documents dáta aplikácie. .test-artifacts obsahuje historické reporty, benchmarky, stavy, exporty a externé HDR vstupy; žiadna povinná runtime alebo test-suite cesta naň pevne neodkazuje. Priečinky sa iba skontrolovali, nič sa neodstraňovalo.
- Expand chyba vznikala kombináciou gridu, percentuálnej výšky obrázka a jeho prirodzenej veľkosti pri rozmere rodiča určenom aspect-ratio. Plátno je teraz štvorcové a popredie má absolútne ohraničenie v plátne s object-fit: contain. Fotografia sa zobrazí celá a prázdne boky zviditeľnia doplnenie pozadia.
- [Bootstrap Accordion](https://getbootstrap.com/docs/5.3/components/accordion/) používa už pribalený Collapse. Spoločný data-bs-parent zabezpečí exkluzívne otváranie, existujúce prechody animujú oba smery a rešpektujú reduced motion. Buttony zachovávajú Enter/Space a správne aria-expanded. Nová animačná knižnica nie je potrebná.
- Release riadok používa align-items: baseline a zdedenú veľkosť/line-height verzie. Overenie inline markermi potvrdilo spoločnú základnú čiaru rôznych písiem; samotná zhoda obdĺžnikov textu by to nedokázala.
- **Runtime overenie:** 6 cielených a 14 existujúcich browser scenárov prešlo; Git kontrola 14 ignorovaných a 8 zachovaných ciest. Všetky tri jazyky a responzívne šírky 320–1440 px bez presahu. IDE diagnostika HTML/CSS bez chýb.

## Implementovaný web s frontendovými prekladmi — 12. 11. 2026

Táto implementácia nahrádza predchádzajúci návrh samostatných jazykových stránok a PDF podľa výslovného spresnenia používateľa.

- Koreňový index.html a .nojekyll umožňujú GitHub Pages z vetvy main a priečinka /(root). Relatívne cesty fungujú aj pri projektovom prefixe. Používateľské README sa načítavajú priamo z koreňa; aplikácia aj web preto používajú totožné súbory bez synchronizačného generovania a bez PDF.
- [i18next](https://www.i18next.com/overview/getting-started) 26.0.0 má všetky tri slovníky pripravené v pamäti. [changeLanguage](https://www.i18next.com/overview/api#changelanguage) prepína texty aj prístupné názvy bez reloadu; revízia bráni prepísaniu novšieho výsledku oneskoreným návodom. Fetch cache vynechá neúspešné požiadavky, aby sa dali zopakovať.
- Bootstrap 5.3.8, i18next 26.0.0, Marked 18.2.0 a DOMPurify 3.4.17 sú pribalené lokálne s licenciami a manifestom verzií/zdrojov/SHA-256. [Marked](https://marked.js.org/) nevykonáva sanitizáciu; jeho HTML výstup prechádza DOMPurify. Web nevyžaduje npm, bundler ani externé CDN pri návšteve.
- Téma sa použije pred vykreslením CSS, System sleduje zmeny prefers-color-scheme a explicitná voľba má prednosť. Chýbajúci alebo blokovaný localStorage nebráni ovládaniu. Pri zmene jazyka sa zachová aktuálna ukážka, tab a kapitola návodu. Natívny dialog poskytuje modalitu, Escape a návrat fokusu; záložky používajú Bootstrap klávesové správanie.
- [Oficiálny postup GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) rozlišuje odoslanie súborov a nastavenie publikovanej vetvy. Postup pre používateľa je v [GITHUB_PAGES.md](./GITHUB_PAGES.md); agent nič nepublikoval. Odkazy na repozitár sa na štandardnej projektovej Pages adrese odvodia automaticky, vlastná doména môže použiť explicitné repositoryUrl.
- **Overenie:** 14 browser scenárov v headless Chrome, bez horizontálneho presahu pri 320/390/768/1024/1440 px a bez runtime chýb. Presná zhoda všetkých troch návodov s Markdown zdrojom, okamžité prepínanie, témy, obnova po chybe, nedostupné úložisko, klávesnica a projektový prefix prešli. Aplikačná sada 651 passed, 1 skipped; source/frozen smoke po novom builde 13/13, exit 0. Podrobné hranice overenia sú v implementačnom pláne.

## História návrhu technológií prezentačného webu — 11. 11. 2026

Posúdenie na výslovnú požiadavku používateľa, zatiaľ bez implementácie webu. GitHub Pages môže priamo hostovať statické HTML/CSS/JS; build je voliteľný. Odporúčanie je hotový Bootstrap 5.3 pre spoločné ovládacie prvky, vlastné CSS pre fotografický vzhľad a malé vanilla JS moduly pre ukážky, jazykové preferencie a tému. Vlastné CSS/JS bez frameworku zostáva rozumnou ľahšou alternatívou; rozhodnutie používateľa ešte nebolo vyžiadané ani nahradené implementáciou.

- [Bootstrap — priamy import](https://getbootstrap.com/docs/5.3/getting-started/introduction/), [záložky](https://getbootstrap.com/docs/5.3/components/navs-tabs/) a [farebné režimy](https://getbootstrap.com/docs/5.3/customize/color-modes/): hotové skompilované súbory nevyžadujú npm ani bundler. Tri voľby témy a ich zapamätanie sa musia doplniť; samotná existencia dark štýlov neznamená automatický prepínač.
- [Tailwind Play CDN](https://tailwindcss.com/docs/installation/play-cdn) je podľa autora určený na vývoj, nie produkciu. Pre finálny web bez generovania CSS nie je odporúčanou cestou.
- [Vue cez CDN](https://vuejs.org/guide/quick-start.html#using-vue-from-cdn) funguje bez buildu; pre prezentačnú stránku s niekoľkými ovládačmi by zatiaľ predstavovalo ďalšiu nepotrebnú vrstvu.
- [GSAP](https://gsap.com/docs/v3/Installation/) podporuje načítanie script tagom; zmysel by malo až pre konkrétnu zložitejšiu názornú animáciu. Jemné prechody a manuálne ukážky nepotrebujú samostatný animačný framework.
- [WAI vzor záložiek](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) opisuje význam, stavy a ovládanie klávesnicou. Vizuálny štýl sám nezaručuje prístupnosť; vlastné úpravy musia zachovať fokus a klávesové správanie.
- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages): statické jazykové stránky a PDF môžu byť hostované spolu s webom. Návrh počíta s EN ako predvoleným jazykom, SK/CS verziami, HTML návodom a samostatnými vopred pripravenými PDF pre každý jazyk. Príprava návodu/PDF pri vydaní je oddelená od frontendového bundlera.

Verzia aplikácie sa na samostatnú požiadavku zmenila na 1.0.0; samotná zmena verzie nepredstavuje publikovanie projektu, voľbu licencie ani realizáciu návrhu webu.

## Celý originál pri orezávaní 0.8.1 — 11. 11. 2026

- Runtime reprodukcia: 14 nových cielených regresií zlyhalo na pôvodnom náhľade. Fit kamera používala iba spojenie plátna a vstupného výrezu; pri výreze 100 × 50 px z 1000 × 500 px fotografie sa originál mapoval na 10 000 × 5000 px a pôvodné okraje boli mimo viewportu.
- Fit scéna teraz zahŕňa plátno a celý orientovaný originál. Jeho začiatok v súradniciach plátna je foreground.topLeft − source_box.topLeft, mierka fotografie zostáva 1:1. Počas crop gesta sa naďalej používa zmrazená transformácia; po uvoľnení sa prispôsobí celý originál aj plátno.
- Rozdiel plochy originálu a vstupného výrezu sa kreslí cez samostatnú masku po bežnej kompozícii. Nepriehľadný tmavý základ a 25 % fotografie dávajú rovnaké stmavenie aj nad svetlým paddingom. Zachovaný detail používa vlastný source_box a foreground_box, takže staré pozadie nevstúpi do odrezanej fotografie. Kvapkadlo vzorkuje pôvodnú SDR farbu aj v stmavenom kontexte.
- Export, spoločná geometria, relácia schémy 6 a pamäťový rozpočet sa nemenia. Oprava používa existujúce Qt API bez novej závislosti či zmeny externého rozhrania.

### Runtime overenie 0.8.1

- **651 passed, 1 skipped** (38,38 s) v celej sade; pri 200 % škálovaní **57 passed** (7,00 s). Pixlové regresie overujú trvalé rovnaké stmavenie aj nad paddingom, návrat všetkých ôsmich úchytov k originálu a správne využitie staršieho natívneho popredia bez prenesenia pozadia. Ruff, syntax a IDE diagnostika zmenených Python súborov bez chýb.
- Živá MCP kontrola ukázala celý generovaný originál 1600 × 900 px pri 100 % aj po zmenšení výrezu; odrezané časti zostali stmavené. Pravý dolný roh sa jedným nadväzujúcim gestom vrátil k pôvodnému okraju. Natívny detail zostal dostupný po dokončení workerov.
- Source a frozen EXE **13/13 smoke kontrol, exit 0**. Aktuálny beh použil dostupnú reálnu ISO gain-map HEIC vzorku a generované vstupy pre HEIC/HDR kodeky; nepoužil všetkých päť historických HDR vzoriek ani opt-in 84 MP test.

## Priamy crop a nová značka 0.8.0 — 11. 11. 2026

Táto časť nahrádza používateľské ovládanie crop editora z 0.7.0. Výpočty pôvodných pixelov, model crop_box, relácia schémy 6 a SDR/HDR exportný krok zostávajú rovnaké.

- **Priame úchyty:** crop má hrany a rohy priamo v strednom náhľade. Ťahanie mení iba príslušné okraje v pôvodných správne orientovaných pixeloch a dovolí obnoviť plochu smerom k hraniciam originálu. Samostatný modal ani číselné polia nie sú súčasťou nového ovládania.
- **Stabilné gesto:** na začiatku ťahania sa zachová transformácia obrazu a kamery. Priebežné nastavenia cropu sa ukladajú ako ostatné úpravy, ale kamera neskáče po každom pixeli. Po uvoľnení sa prispôsobí novému vstupu; Escape obnoví počiatočný výrez. Bežné ľavé ťahanie vnútri fotografie upravuje zarovnanie; pravé/stredné a Space+ľavé zostávajú posunom kamery.
- **Reset:** tlačidlo Reset crop pod Center image vráti crop_box=None a Fit view. Zdroj je nedestruktívny; žiadny nový predvolený pomer ani resize sa tým nezavádza.
- **Názov:** Insta G Photo Processor zrozumiteľne pokrýva crop, split, expand, pozadia aj SDR/HDR výstup. Preprocessor je technický výraz pre prípravný krok a môže evokovať programátorský nástroj. Jeden konzistentný názov je použitý v GUI, metadátach, CLI, EXE aj workspace. Modul insta_g nemeníme.
- **Kompatibilita dát:** čistá inštalácia používa Documents/insta-g-photo-processor. Ak nový priečinok nemá ani session.json ani preferences.json a legacy Documents/insta-g-image-resizer aspoň jeden obsahuje, vyberie sa legacy priečinok bez presúvania dát. Existujúci nový stav má prednosť a explicitné --data-dir obchádza automatický výber. Uložený exportný priečinok sa nemení.
- **Stavy pri Escape a zatvorení:** gesto má začiatok aj koniec mimo obyčajného uvoľnenia myši. Návrat obnovuje pôvodný crop a exportnú snímku so staršou chybou, ale nesmie zahodiť novú nesúvisiacu chybu. Zatvorenie pri držanom úchyte gesto ukončí pred uložením konečného stavu; zlyhanie zápisu zostáva viditeľné.

### Runtime overenie 0.8.0

- Celá sada **635 passed, 1 skipped** (42,22 s), vrátane crop úchytov, krajných floating-point hit testov, Escape a zachovania správnej exportnej chyby, priebežného ukladania a zatvorenia počas gesta pri chybe zápisu. Cielené overenie natívneho detailu a cropu: **69 testov prešlo**. Ruff, compileall a IDE diagnostika všetkých zmenených Python súborov bez chýb.
- Samostatný opt-in 84 MP test sa pri tejto úprave GUI a značky neopakoval; posledný samostatný úspech je uvedený v histórii 0.7.0.
- Source aj finálny Windows EXE prešli **17/17 smoke kontrolami, exit 0**, s piatimi reálnymi HDR vzorkami. Nový scenár inline_crop_handles overuje priame úchyty bez modalu. Zabalený beh potvrdil frozen=true a prázdny zoznam chýb.
- Živé PySide6 MCP overilo nový názov a onboarding, panorámu 5000 × 1000 px so šiestimi dielmi a pracovný crop (100, 100, 5000, 1000). Natívny detail počas gesta zostal dostupný. Reset crop je pod Center image a obnovil crop_box=None bez dialógu.
- Windows one-file EXE bol zostavený a samostatne overený cez frozen smoke. Runtime výsledky sú oddelené od návrhových rozhodnutí a samotného úspechu buildu.

## Návrh prezentačného webu — overené 11. 11. 2026

Používateľ žiada návrh do chatu, preto sa v tejto dodávke nevytvára web, hosting ani publikácia. Nasledujúce rozhodnutia sú návrh, nie implementovaný stav.

- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) hostuje statické HTML/CSS/JavaScript priamo z repozitára s voliteľným buildom. Pre menší prezentačný web a používateľský návod postačuje sémantické HTML, responzívne CSS a malé množstvo JavaScriptu pre carousel/before-after ukážku. Aplikačný backend nie je potrebný.
- Projektová Pages adresa obsahuje názov repozitára ako prefix. Odkazy na obrázky, návody a skripty musia používať relatívne cesty alebo správny base path; root-relative /assets by smerovalo na koreň účtu, nie automaticky na projektový web. Zdroj: [typy Pages webov](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages#types-of-github-pages-sites).
- [Možnosti publikovania](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) sú branch root, branch docs/ alebo vlastný GitHub Actions workflow. Projekt už používa docs/ na vývojové podklady, preto je vhodné oddelené site/ a cielený Pages artifact cez Actions. Pred zverejnením treba samostatné výslovné zadanie.
- Vizuálny návrh: fotografie ako hlavný obsah, tmavé neutrálne pozadie, tyrkysové ovládacie prvky, široká panoráma s jasne rozdelenými dielmi. Viditeľné tlačidlá Download for Windows a GitHub; stručná výhoda a skutočný screenshot namiesto množstva abstraktných kariet.
- Obsah: úvod, interaktívne ukážky split/padding/crop na pribalených vzorkách, tri kroky použitia, konkrétne funkcie, stiahnutie a FAQ. Samostatný používateľský návod má krátky rýchly štart, snímky s označenými ovládačmi a krátke animácie pre gestá; EN/SK/CS rovnako ako aplikácia. Vývojové README zostáva pre vývojárov.
- Ukážkové fotografie majú byť vlastné alebo s overenou licenciou. Ukážka môže fungovať čisto lokálne v prehliadači s pribalenými obrázkami, bez uploadu fotografií. Optimalizované WebP/AVIF s fallbackom, lazy loading pod prvým viewportom, klávesnicové ovládanie a rešpektovanie prefers-reduced-motion patria k návrhu prístupnosti a výkonu.
- Open-source zámer je zvolený používateľom, konkrétna licencia zatiaľ nie. Do aplikácie ani repozitára sa nevkladá vymyslené licenčné udelenie a nepublikuje sa bez pokynu.

## Vstupný výrez 0.7.0 — zdroje a rozhodnutia 11. 11. 2026

Táto časť dopĺňa adaptívny náhľad a nahrádza predpoklad, že vstupom split/expand je vždy celý originál. Stav implementačného overenia je oddelený od dokumentačných podkladov.

- [Pillow 12.3.0: Image.crop](https://github.com/python-pillow/Pillow/blob/12.3.0/src/PIL/Image.py) používa štvoricu left/upper/right/lower. Model uchováva celočíselný polootvorený obdĺžnik v pôvodných pixeloch po aplikovaní orientácie. Pravý a dolný okraj sú výlučné, takže 100/50/900/450 znamená 800 × 400 px. Rozmery sa nemenia resamplingom; súradnice mimo originálu aplikácia odmietne namiesto pridania skrytého paddingu.
- [Qt QPainter](https://doc.qt.io/qt-6/qpainter.html#drawImage-3) umožňuje samostatný zdrojový a cieľový obdĺžnik. Editor preto ukazuje celý malý SDR náhľad, ale ovládač mapuje myš na pôvodné pixelové súradnice. Pri exporte a natívnom detaile sa vzorkuje originál, nie editorový raster. Výrez nesľubuje lacné regionálne dekódovanie každého kodeku.
- **Dva druhy orezania:** vstupný crop zvolí oblasť ešte pred tvorbou plátna a nie je obmedzený pomermi Instagramu. Až potom sa odvodí auto pomer dielov, Fit/Fill plátno a posuny. Fit zachová celý vstupný výrez v mierke 1:1; Fill môže pridať druhé orezanie. Zdroj dekoratívneho pozadia tvorí iba výrez, aby sa odrezané okraje nevracali cez blur.
- **Nedestruktívna editácia:** Crop photo… otvorí modal s celým originálom. Používateľ kreslí nový výber, presúva ho, mení hrany/rohy alebo zadáva X/Y/šírku/výšku. OK aplikuje zmenu; Cancel ju zahodí bez zápisu nastavení. Reset mimo dialógu ihneď obnoví celý vstup, Reset v dialógu čaká na OK. Zmena vstupu obnoví Fit view; hlavný 100 % náhľad zobrazuje celý vstupný výrez aj plátno, celý originál zostáva v editore.
- **Zachovaná plocha:** retained percentage je plocha popredia viditeľná na výstupnom plátne delená celou pôvodnou plochou. Zahŕňa oba crop kroky, nepočíta pridaný padding a nevynuluje informáciu o strate pri Fit. Príklad 1000 × 500 → 800 × 400 px = 64 %; následný štvorcový Fill 400 × 400 px = 32 %.
- **Pamäť a HDR:** jeden natívny zdroj ostáva v plnej veľkosti; zmena výrezu nemá vytvárať druhú plnú cache ani meniť exportnú mierku. Výrez sa premietne do mapovania zdrojových pixelov SDR aj HDR, vrátane gain-map bázy a lineárnych HDR dát. Náhľad zostáva SDR a bežné decode/memory/codec limity stále platia.
- **Izolované zmenšovanie cropu:** priamy Lanczos nad pôvodným obrazom môže do okraja výrezu zahrnúť už odstránené susedné farby. [Pillow Image.reduce](https://github.com/python-pillow/Pillow/blob/12.3.0/src/PIL/Image.py) s celočíselným ROI najskôr izoluje výrez a BOX redukciou vytvorí medziraster najviac približne dvojnásobný oproti cieľu na každej osi; záverečný resize používa Lanczos nad presným zlomkovým ROI. Nejde o alokáciu celého natívneho cropu ani celého rozšíreného plátna. Pri exporte v natívnej mierke 1:1 zostáva priame vzorkovanie bez resize.
- **LOD a rozpočet výrezu:** natívny viewport s cropom obchádza úrovne LOD vytvorené z celého originálu, pretože odrezané farby by už boli primiešané do ich pixelov. Jeden plný zdroj aj existujúce LOD zostávajú zdieľané pre návrat k neorezanému pohľadu. Odhad pracovného rastra crop detailu je 40 B na cieľový pixel vrátane medzivýpočtu, neorezaného 16 B; porovnáva sa s rovnakým 40 % rozpočtom aktuálne dostupnej RAM. Je to odhad, nie rezervácia pamäte.
- **Kompatibilita:** crop_box=None znamená celý originál. JSON pole sa normalizuje na tuple, aby snímky a cache zostali hashovateľné; bool/float/neplatná plocha sa odmietajú. Schéma 6 prijíma migráciu 1–5 a pred prvým novým uložením zálohuje presné pôvodné bajty. Staršie exportné snímky bez crop_box zodpovedajú None a zostávajú zelené, kým používateľ neurobí skutočnú zmenu.

- **Závislosti:** zdieľané rozmerové a bounded-crop helpery sú v [raster.py](../insta_g/core/raster.py). SDR aj HDR ich používajú bez spätného importu kodekov.

### Runtime overenie 0.7.0

Celá sada: **611 passed, 1 skipped** (39,20 s). Regresie overujú SDR/HDR crop, zachovanú mierku a izolované farby okrajov, natívny detail, editor, striktne platné pôvodné súradnice, pomer/zaokrúhľovanie a retained percentá, invalidáciu exportu a JSON roundtrip. Migrácia v5 zachováva zelený stav aj presné pôvodné bajty; neplatný crop sa nevynecháva ani neprepisuje. Ruff, compileall a IDE diagnostika všetkých zmenených Python súborov vrátane HDR/renderu a workerov bez chýb.

- Samostatný opt-in **84 MP test: 1 passed** (12,60 s). Ten istý natívny zdroj poskytol 4K prehľad originálu, 50 MP crop (1000, 1000, 11000, 6000), natívny ROI aj 4K raster výrezu; export pôvodného 147 MP plátna zostal funkčný.
- Source aj finálny Windows EXE **0.7.0: 17/17 smoke kontrol, exit 0**, s piatimi reálnymi HDR vzorkami. source_crop_preview_export overuje výrez 800 × 400 px z 1000 × 500 px originálu, posun/padding a export 800 × 800 px; vstupný hash zostáva totožný. GUI scenár potvrdzuje editor aj obnovu celého vstupu.
- Živé GUI cez PySide6 MCP potvrdilo X/Y 100/50, crop 800 × 400 px a 64 %. Expand 1:1 s offset_y=0,75 zobrazil canvas 800 × 800 a foreground_box (0, 350, 800, 750); plný zdroj detailu zostal 1000 × 500 px. Samostatný integračný test splitu potvrdil dva diely 400 × 400 px.
- Finálny Windows one-file EXE bol úspešne zostavený a samostatne overený.

## Pravý dvojklik obnovuje pohľad 0.6.1 — 11. 11. 2026

- Existujúce `PreviewWidget.reset_view` v [preview.py](../insta_g/gui/preview.py) vynuluje posun kamery a cez `set_zoom(100)` obnoví pohľad na celý originál aj exportné plátno. Rovnakú metódu používa tlačidlo Fit view; pravý dvojklik má zdieľať túto cestu, bez nového externého API.
- Ide o zmenu kamery náhľadu. Nastavenia offset_x/offset_y fotografie, exportná snímka a uložená relácia zostávajú nezmenené. Ľavý dvojklik naďalej centruje fotografiu a zachová aktuálny zoom; pravé ťahanie zostáva posunom viewportu.
- Runtime overenie: pred opravou regresia zlyhala pri 100/250/1000 %. Po oprave prešlo **40 cielených testov** (5,73 s), vrátane reálnej sekvencie myši a nezmenených bajtov relácie/exportného stavu. Zdieľané ukončenie gesta zabraňuje tomu, aby následný pohyb alebo release obnovil starý pan; kvapkadlo zostáva aktívne.
- Source aj nový Windows EXE **0.6.1: 16/16 smoke kontrol**, vrátane pravého dvojkliku a piatich reálnych HDR vzoriek. Ruff, syntax a IDE diagnostika zmenených súborov bez chýb. Pri zmene kamery sa neopakovala celá sada ani 84 MP spracovanie; výsledky 0.6.0 nižšie ostávajú historické.

## Adaptívny náhľad 0.6.0 — overené zdroje 11. 11. 2026

Táto časť nahrádza staršie rozhodnutia o detaile až po ustálení pohybu a pevnom 2048 px limite detailu. Odkazy dokladajú vlastnosti API; nižšie sú samostatne uvedené výsledky runtime testov a Windows buildu verzie 0.6.0.

- [Qt High DPI](https://doc.qt.io/qt-6/highdpi.html) rozlišuje logické rozmery widgetu a fyzické pixely obrazového rastra. Cieľ detailu je viditeľná plocha násobená aktuálnym device pixel ratio; pri presune medzi monitormi či zmene škálovania sa musí znovu vyhodnotiť. Napríklad 1500 logických px pri DPR 2 potrebuje 3000 fyzických px, preto všeobecný limit detailu 2048 px môže znižovať ostrosť.
- [Qt QPainter](https://doc.qt.io/qt-6/qpainter.html) podporuje kreslenie zdrojovej časti obrazu do cieľového obdĺžnika, transformácie a orezanie. Náhľad preto potrebuje raster viditeľnej oblasti a geometriu; nemusí vytvárať celé natívne rozšírené plátno. Dostupný detail popredia možno okamžite transformovať pri posune a zvyšok doplniť z malého zdroja, kým worker pripraví aktuálny výrez. Samotné používanie QWidget/QPainter nie je zárukou GPU renderera.
- [Pillow 12.3.0: filtre](https://github.com/python-pillow/Pillow/blob/12.3.0/docs/handbook/concepts.rst) a [dekodér](https://github.com/python-pillow/Pillow/blob/12.3.0/docs/handbook/tutorial.rst) boli overené cez Context7 pre používanú verziu. Lanczos je kvalitný filter pre resize/thumbnail; `draft` vie znížiť dekódovanie JPEG/MPO pred načítaním. Samotný crop nepredstavuje záruku lacného regionálneho dekódovania každého formátu, preto prvý natívny zdroj môže potrebovať celý decode.
- **Dve úrovne cache:** základ do 2048 px na rýchle zobrazenie a fallback; najviac jeden plný aktívny zdroj pre SDR zobrazenie, zahriaty na pozadí už pri fit 100 %. Kvalitný výrez sa riadi fyzickým viewportom, nie rozmerom celého exportu. Dekoratívne pozadie má naďalej vlastnú malú cache.
- **Voliteľné LOD:** pri výraznom zmenšení sa z natívneho zdroja lenivo vytvorí primeraná úroveň rozlíšenia s aspoň 1,25 zdrojového pixelu na cieľový pixel. Uchovávajú sa najviac dve úrovne spolu do tretiny rozpočtu jedného natívneho rastra; pri native 1:1 sa používa originál. Voliteľná cache sa pri nedostatku pamäte vynechá a priamy render môže pokračovať. Nevytvára sa kompletná pyramída ani dlaždicová databáza.
- **Interakcia:** detail sa žiada aj pri pohybe a zmene geometrie, nie až po skončení gesta. Jedna aktívna a jedna najnovšia čakajúca požiadavka v každej pipeline bránia narastaniu frontu; pri zmene fotografie alebo nastavení sa starý výsledok nesmie považovať za aktuálny. Vstupné udalosti ani GUI nečakajú na natívny decode.
- **Pamäť:** ponecháva sa 40 % aktuálne dostupnej RAM s odhadom podľa SDR/autorskej SDR bázy alebo float PQ/HLG spracovania; kontrola zahŕňa aj výstupný raster. Nejde o rezerváciu pamäte ani garanciu úspechu. Pri nedostatku RAM alebo chybe zostáva malý náhľad s vysvetlením; plný zdroj pre všetky fotografie ani plné rozšírené plátno sa neukladajú.
- **Rozlíšenie a HDR sú oddelené:** plný originál pre náhľad znamená priestorové detaily; obraz sa stále zobrazuje ako SDR. Gain-map fotografie používajú autorskú SDR bázu a PQ/HLG prechádzajú existujúcim tone mappingom. Exportná geometria, natívna mierka pixelov a HDR/SDR export sa tým nemenia.

### Overenie 0.6.0 — 11. 11. 2026

- Kompletná finálna sada **508 passed, 1 skipped** (55,07 s); osobitne zapnutý reálny **84 MP test: 1 passed** (23,19 s). Ten istý originál poskytol 4K fit náhľad 3840 × 1280 px aj natívny výrez a úspešne sa exportovalo 147 MP plátno.
- Source aj finálny Windows EXE **16/16 smoke kontrol, exit 0**, vrátane piatich reálnych HDR vzoriek. Ruff, compileall a IDE diagnostika zmeneného kódu bez chýb. Regresie pokrývajú DPR, fit 100 %, priebežné požiadavky, transformáciu detailu bez starého pozadia, cache/LOD, nedostatok pamäte, zmenu fotografie, oneskorený stav a zachovanie exportnej geometrie.
- Živá kontrola cez PySide6 MCP zobrazila pri 400 % výrez 2650 × 1055 px z 24 MP zdroja. Všetkých 20 pravých posunov zachovalo natívnu vrstvu a presné bajty relácie. Priemerný čas testovacieho kroku vrátane QTest pohybu a screenshotu widgetu bol 20,44 ms; nejde o samostatný benchmark vstupnej latencie ani garanciu FPS.

### Syntetické meranie adaptívneho renderu — 11. 11. 2026

Meraná bola generovaná 24 MP fotografia **6000 × 4000 px** na jednom vývojovom stroji. Nasledujúce časy sú mediány piatich behov po zahriatí cache a merajú prípravu rastra vo workeri. Nejde o latenciu vstupnej udalosti, celý import, benchmark všetkých kodekov ani garanciu 60 FPS.

| Oblasť a výstup | Priamy render z originálu | Adaptívny render | Použitá úroveň |
| --- | ---: | ---: | --- |
| Celá fotografia → 1200 × 800 px | 300,193 ms | 42,970 ms | LOD faktor 4 |
| 4K viewport → 3840 × 2160 px | 496,101 ms | 502,386 ms | Originál, bez LOD |
| Natívny výrez 1000 × 667 px → 1200 × 800 px | 25,862 ms | 27,199 ms | Originál, bez LOD |

Prvý adaptívny fit render vrátane dekódovania a vytvorenia LOD trval **711,250 ms**. Zahriata LOD pomáha najmä pri výraznom zmenšení; pri 4K a natívnom výreze sa používa originál s malou réžiou. Počas čakania GUI okamžite transformuje dostupné pixely a kvalitný raster ho priebežne spresňuje. Ďalší výkon závisí od fotografie, monitora, kodeku a dostupnej pamäte.

## Pravé posúvanie a rovnaký štýl φ — 11. 11. 2026

- Osobitný stylesheet zlatého rezu nastavoval Segoe UI Symbol/16 px; tým sa odlišovalo tlačidlo aj dedené písmo tooltipu. φ teraz používa spoločný štýl ostatných volieb. Skutočne zobrazené tooltipy majú v regresii rovnaké písmo a výšku pri globálnej aplikačnej téme, v EN/SK/CS a svetlej aj tmavej téme.
- [Qt ContextMenuPolicy](https://doc.qt.io/qtforpython-6/PySide6/QtCore/Qt.html#PySide6.QtCore.Qt.ContextMenuPolicy) overené cez Context7: PreventContextMenu garantuje doručenie pravého mousePress/Release widgetu a neodovzdáva kontextové menu rodičovi.
- [QMouseEvent](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QMouseEvent.html) popisuje automatické zachytenie myši po stlačení. Preview navyše eviduje tlačidlo, ktoré začalo gesto; uvoľnenie iného tlačidla ho neukončí.
- Pravý drag mení iba pan kamery. Regresie overujú nezmenenú Geometry/nastavenia/platnosť exportu aj presné bajty session.json, bez volania ukladania. Pravý dvojklik necentruje fotografiu; kvapkadlo po pravom posune ostáva aktívne.

## Oprava interaktívneho náhľadu 0.5.1 — 11. 11. 2026

- Runtime reprodukcia potvrdila: 30 pohybov menilo offset, ale nie kreslenú geometriu. Trailing debounce 100 ms neustále čakal na koniec pohybu. Živý náhľad teraz prekresľuje cache podľa tej istej Geometry ako export; následný worker spresní filtre. [Qt QPainter](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainter.html) kreslí zdroj a samostatné pozadie, takže sa neposúva stará hotová kompozícia s duchom pôvodného popredia.
- Zoom pri návrate na 100 % znovu určí stred celého originálu aj plátna. Pôvodné centrovanie iba plátna orezávalo krajne posunutý zdroj o 130,5 px v reprodukovanom viewporte. Pri samotnom ťahaní ostáva kamera stabilná.
- Hi-res bol vo verzii 0.5 podmienený rozpočtom min(512 MiB, 20 % dostupnej RAM). Odhad 80 B/pixel odmietol 12 MP HDR (960 MB) a 16 B/pixel 48 MP SDR (768 MB). Fallback bol tichý; používateľ preto videl iba zväčšený raster do 2048 px. Od 0.5.1 platí dynamický rozpočet 40 % dostupnej RAM, 16 B/pixel pre SDR a autorskú SDR bázu, vyšší odhad 112 B/pixel pre float PQ/HLG. Pripočítavajú sa metadáta a cieľový raster; core RAM kontroly zostávajú aktívne.
- ISO SDR báza sa číta priamo bez HDR rekonštrukcie. Reálny Samsung 4000 × 1848 px mal rovnaké všetky výstupné pixelové bajty aj ICC ako predchádzajúca cesta; jednorazové meranie 3,563 s → 0,357 s. Nie je to sľub rovnakého zrýchlenia každého kodeku.
- Pozadie sa cachuje pri rovnakom zdroji, plátne, rozostrení a farbe aj pre natívne viewport výrezy. Offset ho nemení. Identická affine transformácia sa nahradila kópiou, 1×1 plná farba priamym vyplnením. Nové regresie porovnávajú presné pixely s pôvodnou spoločnou kompozíciou.
- Výkon na overenom Windows/Python 3.13 stroji: pri 1000 záznamoch, z ktorých polovica bola exportovaná, medián obsluhy nastavenia klesol z 80,684 ms na 0,711 ms (40 následných zmien, p95 1,133 ms). Prvá zmena zeleného stavu na žltý vyžaduje jeden prepočet počtov; nameraná 30,991 ms. Časy nezahŕňajú celý export a nie sú garantované pre každý hardvér.
- Pri zmenách offsetu rozšíreného blur obrázka klesol nameraný čas worker kompozície+Qt rasterov zo 682,745 ms na 99,156 ms po zahriatí cache. Okamžité Qt kreslenie malej cache má približne 4 ms v meranom viewporte; worker sa nečaká pri posune. Zmena samotného blur/ratio môže stále vyžadovať nový filter pozadia.
- Atómové save/fsync sa pôvodne vykonávalo v GUI (pri 1000 záznamoch samotné save približne 20–30 ms). Teraz má každá revízia privátnu snímku a sériový worker; snímky sa nevynechávajú, staršie zápisy neprepisujú novšie a close čaká na dopísanie. Capture zmeneného záznamu plus plytký zoznam mal medián 0,298 ms. Chyba pri zatváraní ponechá reláciu otvorenú s viditeľnou chybou.
- Preview aj detail majú najviac jeden aktívny a jednu najnovšiu čakajúcu požiadavku. Rušený decode môže dokončený natívny zdroj ponechať pre najnovší výrez; nepredstiera sa okamžité prerušenie natívneho kodeku. Caption a tooltip vysvetľujú Native detail / Loading detail / Reduced preview s dôvodom.

### Licencie overené podľa dodávaných binárnych súborov

- [pillow-heif 1.8.1 LICENSES_bundled](https://raw.githubusercontent.com/bigcat88/pillow_heif/v1.8.1/LICENSES_bundled.txt) odlišuje zdrojový BSD-3-Clause wrapper od binárneho wheelu označeného GPLv2. Uvádza libheif 1.23.6 LGPLv3, libde265 1.1.3 LGPLv3 a x265 4.3 GPLv2. PyInstaller archive inspection potvrdila reálne x265/libde265 DLL aj toto licenčné oznámenie v EXE.
- [x265 4.3 header](https://raw.githubusercontent.com/Multicorewareinc/x265/4.3/source/x265.h) povoľuje GPLv2 alebo novšiu verziu a alternatívnu komerčnú licenciu. [Oficiálne právne oznámenie x265](https://x265.readthedocs.io/en/master/introduction.html) odlišuje licenciu autorských práv od prípadných patentov HEVC.
- [libheif](https://github.com/strukturag/libheif) je kontajnerová knižnica s rôznymi kodekmi; HEIF kontajner nie je totožný s encoderom x265. [Qt LGPL podmienky](https://www.qt.io/development/open-source-lgpl-obligations) vysvetľujú možnosť uzavretej aplikácie pri splnení povinností voči knižnici. Samotný one-file build nie je dôkaz kompletného licenčného súladu distribúcie. Licencia projektu ani predajný model sa touto úpravou nevolili.

## Rozšírenie 0.5 — overené 10. 11. 2026

### Náhľad, mriežky a dominantné farby

- [Qt QStyleHints](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QStyleHints.html) poskytuje colorSchemeChanged pre systémový vzhľad. Témy používajú jeden stylesheet a explicitný príznak pre vlastné maľovanie knižnice.
- [darktable guides overlays](https://darktable-org.github.io/dtdocs/en/module-reference/utility-modules/darkroom/guides-overlays/) uvádza tretiny, zlatý rez, diagonály a stredové vodiace čiary. Zvolené maximum piatich tlačidiel: žiadna, tretiny 3×3, zlatý rez (0,381966/0,618034), diagonály a stredový kríž. Každá mriežka patrí jednému výslednému dielu vrátane paddingu.
- [W3C sRGB](https://www.w3.org/Graphics/Color/srgb) a [CSS Color conversions](https://www.w3.org/TR/css-color/#color-conversion-code) sú podkladom prevodu sRGB → XYZ D65 → CIELAB. Paleta používa malý RGB raster, median-cut kandidátov, váhy zastúpenia a prah vzdialenosti CIELAB 12; chýbajúce odlišné farby sa nevymýšľajú. Nie je to sémantický výber farieb objektov.
- Zoom je relatívny k základnému zmesteniu (100–1000 %), nie absolútne mapovanie pixelov displeja. Lanczos zmenšuje popredie, bicubic mapuje dekoratívne pozadie, Qt SmoothPixmapTransform zobrazuje raster. Výrez originálu sa dopĺňa po 120 ms pokoja, do 2048 px, z jedného natívneho zdroja. Jeho decode odhad musí byť pod 512 MiB aj 20 % dostupnej RAM. Pri prekročení sa ponechá základný náhľad; Pillow nedokáže garantovať lacný regionálny decode každého HEIC/PNG.

### Skutočné HDR

- [imagecodecs HDR API](https://github.com/cgohlke/imagecodecs/blob/master/imagecodecs/_ultrahdr.pyx) a [vydania](https://github.com/cgohlke/imagecodecs/releases): Windows wheel 2026.10.10 obsahuje libultrahdr 2.0.2 a float farebné prevody Little CMS. Vyžaduje Python 3.12+. Runtime overený na CPython 3.13.17 x64.
- [Google libultrahdr](https://github.com/google/libultrahdr) poskytuje skutočné JPEG gain mapy; [ISO metadata implementation](https://github.com/google/libultrahdr/blob/main/lib/src/gainmapmetadata.cpp) a [Apple metadáta](https://github.com/google/libultrahdr/blob/main/lib/src/jpegrutils.cpp) sú primárny podklad dekódovania. `use_base_cg` určuje, či použiť gamut SDR bázy alebo gain-map JPEG; nemožno vždy predpokladať sRGB.
- [Apple: Applying Apple HDR effect](https://developer.apple.com/documentation/appkit/applying-apple-hdr-effect-to-your-photos) popisuje v1 gain mapu, Rec.709 gamma a výpočet headroom z MakerNote 33/48. V2 používa logaritmickú gain mapu a log2 headroom podľa referenčného kodeku. Verzie sa nesmú zamieňať.
- [libheif tmap podpora](https://github.com/strukturag/libheif/pull/1503) vysvetľuje HEIF odvodenú tone-map položku. V pribalenom imagecodecs/libultrahdr wheel je priamy HEIF gain-map backend vypnutý; aplikácia preto bezpečne parsuje BMFF meta/iinf/iloc/iref/ipma/tmap a dekóduje príslušný pomocný obraz cez libheif. Pôvodný súbor sa nemení; prípadné sprístupnenie skrytej položky existuje iba v pamäťovej kópii.
- [ITU-R BT.2100](https://www.itu.int/rec/R-REC-BT.2100) definuje PQ/HLG HDR. Pracovné dáta sú lineárne BT.2020 float32, 1 = 203 cd/m². PQ rešpektuje absolútnu jasovú škálu ST 2084; HLG referenčný vrchol 1000 nitov a systémovú gamma 1,2. Pre NCLX sú podporované BT.709, BT.2020 a Display P3.
- SDR náhľad/export gain-map fotografie používa autorskú SDR bázu po ICC konverzii do sRGB. Pri samostatnom PQ/HLG je použitý globálny extended Reinhard tone mapping jasu s kompresiou gamutu k neutrálu. Nie je to presná reprodukcia adaptívneho renderingu každého telefónu.
- HDR JPEG výstup je nová ISO gain mapa; HEIC je nové 10-bit PQ/BT.2020, kvalita 99. To zachováva HDR jasový zámer, nie pôvodný bitstream či pôvodnú HLG/gain-map reprezentáciu. SDR fotografie sa neoznačujú ako HDR.
- Reálne overený limit libultrahdr je 8192 px na hranu dielu, samostatný od SDR libjpeg limitu 65 500 px. Chyba je vysvetlená, nevykonáva sa skrytý resize. HDR blur používa separabilné kumulatívne súčty bez paddingu závislého od polomeru; pracovná pamäť rastie podľa malého rastra pozadia.

### Reálne testovacie vzorky a hranice dôkazu

- [Apple HDR JPEG new](https://raw.githubusercontent.com/google/libultrahdr/main/tests/data/apple_gainmap_new.jpg), [old](https://raw.githubusercontent.com/google/libultrahdr/main/tests/data/apple_gainmap_old.jpg) a [malý ISO HEIC](https://raw.githubusercontent.com/google/libultrahdr/main/tests/data/gainmap_hevc_16x16.heic) sú z oficiálnych testov Google. Malá ISO fixture je v testoch aj s licenciou a atribúciou.
- [Samsung ISO HEIC](https://raw.githubusercontent.com/bigcat88/pillow_heif/master/tests/images/heif_special/aux_YCbCr.heic) je z oficiálneho repozitára pillow-heif; rozmer 4000 × 1848 px.
- [Verejná Apple Photos HEIC príloha KDE](https://bugs.kde.org/attachment.cgi?id=197623) má 3873 × 2582 px a Apple v1 auxiliary gain mapu. Použitá iba v ignorovanom lokálnom testovacom adresári; licencia ďalšieho šírenia nebola overená, preto sa nepribaľuje k aplikácii ani do repozitára.
- Vzorky prešli skutočným dekódovaním, rozdelením, HDR kódovaním a opätovným dekódovaním, vrátane hodnôt nad SDR bielou. Apple HEIC v2 je overené cez kalibráciu referenčného kodeku a parametrické regresie; reálna v2 HEIC vzorka nebola k dispozícii. Fyzický HDR monitor ani všetky telefóny neboli testované.

### Dávky a nastavenia

- Neúspech/cancel uprostred série vráti späť iba nové súbory daného originálu; neskôr spracované fotografie môžu pokračovať a staršie súbory zostanú. Zlyhanie cleanup sa výslovne ohlási. Nejde o transakciu garantovanú pri náhlom výpadku napájania.
- Preferences majú samostatný atómový JSON. Prvotný defaultný Export sa vytvorí iba pri prvotnom nastavení; neskorší chýbajúci nakonfigurovaný cieľ sa nesmie potichu obnoviť.
- Nezávislý audit odhalil a následné regresie overujú zachovanie HDR voľby pri cache miss, oddelenie chyby exportu od dočasnej chyby náhľadu, skutočný reset Skip a pamäť HDR blur nezávislú od polomeru.

Pôvodné časti dokumentujú verziu 0.1. Pre natívny export zavedený od verzie 0.2 má prednosť časť **Veľké originály a natívny export — 10. 11. 2026**: priame pomery 16:9 až 3:4, Fit/Fill, natívny export a kontrola RAM bez 80 MP stropu.

Verzia 0.3 navyše používa maľovaný delegát zoznamu s natívnym `CheckStateRole`; checkbox je oddelený od aktívneho výberu a farba riadku sa riadi exportným stavom. Vlastné `paint`, `sizeHint` a `editorEvent` obsluhujú checkbox, miniatúru a kôš bez tisícov samostatných widgetov. API bolo overené v [Qt dokumentácii delegáta](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QStyledItemDelegate.html), [model/view](https://doc.qt.io/qtforpython-6/overviews/qtwidgets-model-view-programming.html) a [showMaximized](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html). Stav úplného exportu sa viaže na snímku nastavení aj identitu existujúceho záznamu, preto starší výsledok neoznačí novú upravenú fotografiu ako hotovú.

Verzia 0.4 rozlišuje aj históriu skutočného otvorenia náhľadu. Nový import je modrý; príznak previewed sa uloží až po prijatí aktuálnej úspešnej generácie pre aktívnu fotografiu. Samotné dokončenie thumbnail workeru alebo checkbox nesvedčí o tom, že používateľ fotografiu videl. Export vybraných používa vlastnú snímku checkboxov, nezávislú od aktívneho náhľadu. Neúspešný alebo oneskorený worker nesmie zmeniť pripravenosť iného záznamu.

Oprava 0.4.1 zjednocuje oprávnenosť oboch exportných akcií: kandidát musí mať stav Pripravené alebo Exportované, pri selektívnom exporte navyše checkbox. Samotné Importované sa vždy preskočí. Filter je spoločný pre dostupnosť ovládania, dialóg a spustenie dávky; geometrický exportný mechanizmus dostáva až už vyfiltrovanú nemennú snímku.

Overené online a cez Context7: **9. 11. 2026**. Dokument zachytáva podklady a rozhodnutia pre prvú verziu aplikácie.

## Instagram a pomery strán

- Aktuálne publikované pravidlá feed fotografií uvádzajú rozsah **3:4 až 1.91:1** a šírku do **1080 px**. Ako praktický predvolený export použijeme šírku jednej fotografie 1080 px; 3:4 zodpovedá 1080 × 1440 px.
- Primárne zdroje: [Instagram Help — Image resolution of photos you share](https://help.instagram.com/1631821640426723) a [oznámenie Adama Mosseriho o podpore 3:4](https://www.threads.com/@mosseri/post/DKOIbJkRNIb/instagram-now-supports-34-aspect-ratio-photos-the-format-that-almost-every-phone).
- **Obmedzenie overenia:** oba primárne endpointy pri priamom načítaní počas výskumu vracali HTTP 429. Rozsah 3:4 až 1.91:1 je konzistentne citovaný vo verejne indexovaných výsledkoch; priamy aktuálny text Instagram Help sa nepodarilo načítať. Preto pravidlá nepredstavujú garanciu správania každého klienta, carouselu alebo budúcej verzie Instagramu. Zmena 3:4 je doložená aj dobovým [spravodajstvom s odkazom na primárne oznámenie](https://www.theverge.com/news/676549/instagram-3-4-aspect-ratio-photos-phones-square-rectangle).
- Žiadané presety 16:9, 3:2, 4:3, 5:4 a 1:1 zostanú dostupné v landscape aj portrait orientácii. Preset **4:3 + portrait znamená 3:4**. Portrait 9:16 a 2:3 sú užšie než feed limit; aplikácia pri takom výbere zobrazí upozornenie, ale zvolený pomer sama nezmení.
- Kontinuálny slider pracuje s pomerom od 1:1 po 16:9 a orientácia určí, či sa použije priamo alebo prevrátene.

## Geometria bez straty originálu

- Auto pomer jednej dlaždice sa odvodí z rozmerov správne orientovaného originálu: `r = clamp(W / (N × H), 3/4, 1.91)`, kde `N` je počet splitov a `r` je šírka/výška jednej dlaždice.
- Najskôr vznikne **spoločné plátno** rozmerov `N × tile_width` na `tile_height`. Celý originál sa doň vloží spôsobom **contain**, bez orezania popredia. Nesúlad pomerov doplní pozadie.
- Až spoločný vyrenderovaný raster sa rozdelí na rovnako veľké dlaždice. Tento postup zachová celý obraz, rovnaké rozlíšenie exportov aj nadväznosť susedných dielov.
- Expand používa rovnaký princíp s jednou výslednou fotografiou. Pri úzkom portréte sa doplnia bočné okraje; pri inom nesúlade pomerov môžu vzniknúť okraje aj hore a dole.
- Rozostrenie pozadia má polomer 0–1000 px, interpretovaný v pixeloch exportného plátna. Preview používa rovnakú geometriu a primerane škálovaný polomer. Hodnota 0 znamená nerozostrené doplnené pozadie.
- Náhľad má najviac 2048 px na dlhšej hrane. Export sa vždy vyrába nanovo z originálu, nikdy zo zmenšeného náhľadu.

## Knižnice a dekódovanie

- **PySide6** poskytne Windows GUI, tri nastaviteľné panely, drag and drop, menu, workery a natívne dialógy.
- **Pillow** postačuje pre JPEG/PNG, LANCZOS resize, kompozíciu, GaussianBlur a JPEG export. Pre statické obrázky netreba ffmpeg ani OpenCV. [Dokumentácia Pillow](https://pillow.readthedocs.io/en/stable/).
- **pillow-heif** pridá HEIC cez `register_heif_opener()` pred otvorením obrázkov v Pillow. Pre Windows sú odporúčané binárne wheels s natívnymi kodekmi. [Projekt](https://github.com/bigcat88/pillow_heif), [inštalácia](https://pillow-heif.readthedocs.io/en/stable/installation.html).
- JPEG a PNG s EXIF orientáciou sa normalizujú cez `ImageOps.exif_transpose`. HEIF Pillow plugin už rieši transformačné vlastnosti a normalizáciu orientácie; aplikácia nemá osobitne opakovať HEIF rotácie. [ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html), [HEIF orientácia](https://pillow-heif.readthedocs.io/en/stable/workaround-orientation.html).
- Priehľadnosť PNG sa pred JPEG exportom zloží na nepriehľadné pozadie. Výsledkom je RGB fotografia.

## Farby a JPEG export

- Vložený ICC profil sa podľa možností konvertuje cez `ImageCms.profileToProfile` do **sRGB**; výsledný sRGB profil sa zapíše do JPEG. [ImageCms](https://pillow.readthedocs.io/en/stable/reference/ImageCms.html).
- JPEG sa ukladá s `quality=99`, `subsampling=0` a optimalizáciou. Hodnota 99 je explicitná požiadavka používateľa; dokumentácia Pillow odporúča hodnoty do 95 pre menšie súbory. Číslo kvality nie je percento vernosti ani percento zachovaných dát. [JPEG save options](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#jpeg).
- Export nezachová GPS ani ostatné EXIF metadáta. Orientácia je už aplikovaná na pixely.
- **HDR obmedzenie:** `convert_hdr_to_8bit=True` v pillow-heif redukuje bitovú hĺbku, no nie je dôkazom plnohodnotného HDR → SDR tone mappingu. HEIC bez ICC, iba s NCLX/HDR charakteristikami, môže vyžadovať dodatočnú správu farieb; prvá verzia nesľubuje verný HDR rendering. [Podporované režimy](https://pillow-heif.readthedocs.io/en/stable/image-modes.html), [HDR a NCLX metadata](https://pillow-heif.readthedocs.io/en/latest/saving-images.html).

## Stav, responzivita a balenie

- Umiestnenie relácie: skutočný priečinok Windows Documents získaný cez `QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)` a podpriečinok `insta-g-image-resizer/session.json`. To rešpektuje lokalizáciu aj presmerovanie Documents, napríklad do OneDrive. Stav sa zapisuje atómovo a s verziou schémy. [QStandardPaths](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QStandardPaths.html).
- Dekódovanie, príprava náhľadu a export patria do workerov. Widgety a `QPixmap` sa obsluhujú v hlavnom Qt vlákne; workery odovzdávajú obrazové dáta alebo `QImage` cez signály. [Qt threading example](https://doc.qt.io/qtforpython-6/examples/example_corelib_threads.html).
- **PyInstaller** vytvorí Windows `--onefile --windowed` EXE. Windows distribúcia sa zostavuje na Windows; Qt hooks zbierajú potrebné Qt knižnice a pluginy. Pri HEIF treba skontrolovať natívne DLL a skutočný import v zabalenom EXE. Ak automatická analýza niektoré DLL neobjaví, použije sa cielený hook, nie nekontrolovaný zber všetkých balíkov. [Qt deployment](https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html), [PyInstaller hooks](https://pyinstaller.org/en/stable/hooks.html).
- One-file EXE sa pri štarte rozbalí do dočasného priečinka, preto môže štart trvať dlhšie. Používateľská relácia nesmie byť uložená v tomto dočasnom priečinku ani vedľa EXE. [Princíp one-file balenia](https://pyinstaller.org/en/stable/operating-mode.html).
- Úspešná kompilácia sama osebe nedokazuje funkčný program. Potrebné sú testy geometrie, kodekov, orientácie, transparentnosti, uloženia/obnovy stavu, exportných kolízií, GUI aj smoke test zabaleného EXE vrátane skutočného HEIC vstupu.

## Použité dokumentačné nástroje

Context7 bol použitý na aktuálnu dokumentáciu Pillow, Qt for Python a PyInstaller. Webové vyhľadávanie a priame načítanie oficiálnych zdrojov doplnili pravidlá Instagramu, pillow-heif a správanie Windows balenia. Verzie nainštalovaných závislostí a reálne správanie programu sa overujú osobitne pri implementácii a testovaní.

## Veľké originály a natívny export — 10. 11. 2026

Nasledujúce rozhodnutia dopĺňajú pôvodný výskum a pri zmene požiadaviek nahrádzajú pôvodný pevný limit 80 miliónov pixelov aj predvolený resize exportu na šírku 1080 px.

- **Pamäť podľa hostiteľa:** veľkosť vstupu ani spoločného panoramatického plátna nemá pevný aplikačný limit v megapixeloch. Pred veľkou alokáciou sa porovná praktický odhad potrebných bajtov so 75 % aktuálne dostupnej fyzickej RAM. Pre dekódovanie originálu a render jednej dlaždice sa používa odhad 12 bajtov na pixel, ktorý počíta s pracovnými kópiami. Ide o heuristiku, nie rezerváciu pamäte alebo záruku úspechu.
- **Windows:** `GlobalMemoryStatusEx` a `MEMORYSTATUSEX.ullAvailPhys` poskytujú momentálne dostupné fyzické bajty vrátane okamžite znovupoužiteľných stránok. `dwLength` sa musí pred volaním nastaviť na veľkosť štruktúry. Hodnoty sa môžu meniť medzi dvoma volaniami. [Microsoft: funkcia](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-globalmemorystatusex), [štruktúra](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/ns-sysinfoapi-memorystatusex).
- **Prenositeľný fallback:** na POSIX sa podľa dostupnosti použije `os.sysconf("SC_AVPHYS_PAGES") × os.sysconf("SC_PAGE_SIZE")`. Ak operačný systém údaj neposkytne, helper vráti `None` a nenahradí ho vymysleným pevným limitom. Skutočný `MemoryError` sa musí stále obslúžiť. [Python os.sysconf](https://docs.python.org/3/library/os.html#os.sysconf).
- **Pillow pixelová ochrana:** `Image.MAX_IMAGE_PIXELS` je prah pre `DecompressionBombWarning`; nad dvojnásobkom prahu vzniká `DecompressionBombError`. Nastavenie `None` oba pixelové prahy vypína. Pre lokálny nástroj s explicitne požadovanou podporou veľkých originálov nahradí tento pevný prah pamäťový odhad aplikácie. Neznamená to odstránenie limitov kodekov alebo spoľahlivú ochranu pred každým poškodeným súborom. [Pillow Image.open](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open), [interné limity](https://pillow.readthedocs.io/en/stable/reference/limits.html).
- **Úsporné JPEG preview:** `thumbnail` zavolá podľa možností dekodéra `draft`, čo umožní JPEG dekódovať v redukovanom rozlíšení. Musí sa zavolať pred `load`, `exif_transpose`, konverziou ICC a kopírovaním celého obrazu. Pôvodné rozmery a EXIF orientácia sa uložia ešte pred redukciou; pri orientáciách 5–8 sa v metadátach pôvodné hrany vymenia. Náhľad sa následne normalizuje a odpojí od otvoreného súboru. Samotné `draft` negarantuje presné cieľové rozmery, preto zostáva potrebné `thumbnail` a limit dlhšej hrany 2048 px. PNG a HEIC nemusia podporovať rovnakú úsporu dekódovania. [Thumbnail](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.thumbnail), [ovládanie dekodéra](https://pillow.readthedocs.io/en/stable/handbook/tutorial.html#controlling-the-decoder).
- **JPEG limit jednej dlaždice:** libjpeg-turbo definuje `JPEG_MAX_DIMENSION` ako **65 500 px**. Pred exportom sa kontroluje každá hrana jednotlivého výsledného JPEG, nie šírka súčtu všetkých splitov. Panorama môže mať širšie spoločné súradnice, ak jej jednotlivé exportované dlaždice limit spĺňajú. [Primárny zdroj libjpeg-turbo](https://github.com/libjpeg-turbo/libjpeg-turbo/blob/main/src/jmorecfg.h).
- **Natívny rozmer, Fit/Fill a offset:** nové požiadavky uprednostňujú export bez predvoleného zmenšenia originálu. Geometria a render musia zdieľať definíciu plátna, režim Fit/Fill a posun obrazu, aby overlay zodpovedal reálnemu exportu. Veľké panorámy sa spracúvajú po výstupných dlaždiciach; nevyrába sa zbytočne celý veľký spoločný raster iba preto, aby sa hneď rozrezal. Náhľad doplneného pozadia môže používať zdieľaný malý raster, výsledný export však vychádza z originálu.

Overenie helpera pamäte: 28 izolovaných testov úspešne preverilo Windows API, POSIX fallback, neznámu dostupnosť, validáciu vstupov, presnú hranicu 75 %, veľké odhady bez pevného limitu a zachovanie prostredia procesu. Testy nealokujú veľké obrázky ani nemenia používateľské dáta.
