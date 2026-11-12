# Implementačný plán

## Aktuálna implementácia webu a dokumentácie 1.0.0 — 12. 11. 2026

Stav: **dokončené a overené vrátane nového Windows EXE**. Používateľ výslovne žiada realizáciu, okamžité frontendové prepínanie jazykov a spoločné Markdown návody bez PDF. Publikovanie spravuje sám; agent nevykonáva Git operácie ani nasadenie.

- [x] Rozdeliť vývojárske README EN/SK/CZ a používateľské EXE návody EN/SK/CZ; upraviť pomocníka a build na nové názvy.
- [x] Pripraviť lokálne verzované knižnice a fotografie s atribúciami, skutočné snímky GUI v izolovanej relácii.
- [x] Dokončiť prezentáciu s jedným HTML, i18next, interaktívnymi ukážkami a tromi vzhľadmi.
- [x] Overiť desktop/tablet/mobil, okamžité prepínanie jazykov, návody, lokálne uloženie, klávesnicu a cesty pri projektovom GitHub Pages prefixe.
- [x] Vysvetliť prvé nastavenie Pages na webe GitHubu a neskoršie aktualizácie cez GitHub Desktop.
- [x] Dokončiť testy, diagnostiku, Windows build a source/frozen smoke s novými názvami návodov.
- [x] Zaznamenať konečné výsledky; nič nepublikovať a nemeniť osobný TODO.

### Výsledky webu a dokumentácie 1.0.0

- Kompletná aplikačná sada **651 passed, 1 skipped** (36,27 s); cielená integrácia návodov, brandingu a GUI **54 passed** (6,10 s). Samostatný 84 MP test sa pri tejto dodávke neopakoval.
- **14 browser scenárov prešlo** v headless Chrome na existujúcom lokálnom prehliadači. Šírky 320/390/768/1024/1440 px vrátane SK/CS, tri vzhľady, presný obsah Markdown návodov, žiadne navigácie pri zmene jazyka, zachovanie splitu/pozadia/tabu/kapitoly, klávesnica, Escape a návrat fokusu z lightboxu, blokovaný localStorage a retry dočasnej chyby návodu. Runtime bez chýb a chýbajúcich požiadaviek; projektový prefix otestovaný so simulovanou GitHub Pages adresou bez publikovania.
- Opravené opakovanie načítania po neúspešnom prefetchi a zdvojený odstup kapitoly pod pevnou navigáciou, ktoré odhalilo review a browser test. Všetky tri jazyky majú 136 prekladových kľúčov; všetkých 127 HTML kľúčov je pokrytých. Audit 90 lokálnych README odkazov bez chýb.
- Ruff, syntax JavaScriptu a IDE diagnostika dotknutých Python/HTML/CSS/JS súborov bez chýb. Integrovaný browser pozastavoval vizuálne vykresľovanie skrytého tabu, preto sa spoľahlivá responzívna a vizuálna kontrola vykonala v samostatnom headless Chrome s dočasným testovacím ovládačom v ignorovanom build priečinku; web tým nezískal Node závislosť ani build krok.
- Source aj nový Windows one-file EXE **13/13 smoke kontrol, exit 0**, application=1.0.0, frozen=true v zabalenom reporte a errors=[]. Zahŕňa načítanie troch premenovaných návodov v pomocníkovi, HEIC, HDR kodeky a dostupnú reálnu ISO gain-map HEIC vzorku. Historické ďalšie HDR vzorky sa nepoužili.
- Výstup: `dist/InstaGPhotoProcessor.exe`, **76 999 277 B**, SHA-256 `B9531EAA88B6DD10DA5E7B8536A30FCC5138EC06B3BB52E929B6A294BA322132`. Osobné fotografie, nastavenia a TODO sa nemenili. Bez commitu, pushu, vytvárania Releases a aktivácie Pages.

## História prečíslovania na 1.0.0 — 11. 11. 2026

Stav: **dokončené a overené vrátane Windows EXE**. Používateľ žiada aj posúdenie technológií a štruktúry budúceho GitHub Pages webu do chatu; jeho vytvorenie zatiaľ nežiada.

- [x] Nastaviť verziu v aplikácii a metadátach na 1.0.0 bez zmeny funkcionality či schémy relácie.
- [x] Overiť lokálne metadáta, --version, dotknuté testy a diagnostiku.
- [x] Zostaviť nový Windows EXE a overiť ho izolovaným smoke testom.
- [x] Zapísať skutočné výsledky a údaje buildu.

### Výsledky 1.0.0

- **15 passed** (0,53 s), branding a inicializácia aplikácie. Zdroj, CLI --version, koreňový egg-info aj nainštalovaná distribúcia sú 1.0.0. Obnovené editable metadáta lokálne, bez sťahovania či zmeny závislostí.
- Ruff, compileall a IDE diagnostika dotknutých súborov bez chýb.
- Source aj Windows EXE **13/13 smoke kontrol, exit 0**, s rovnakým dostupným rozsahom vstupov ako 0.8.1. Zabalený report: application=1.0.0, frozen=true, ok=true, errors=[]. Celá sada a samostatný opt-in 84 MP test sa pri zmene verzie neopakovali; posledné úplné výsledky sú pri 0.8.1.
- Výstup: `dist/InstaGPhotoProcessor.exe`, **76 998 269 B**, SHA-256 `B95CC7842C461D8FB3B7A4E419136C47D14A24C1759ECF83D797C95B991DE859`. Bez Git publikovania, osobný TODO sa nemenil.

## História opravy 0.8.1 — 11. 11. 2026

Stav: **implementované a overené vrátane nového Windows EXE**.

- [x] Reprodukovať priblíženie iba na výrez a chýbajúce trvalé stmavenie regresnými testmi.
- [x] Zahrnúť celý originál do Fit pohľadu aj po uvoľnení crop úchytu; zachovať zmrazenú kameru počas gesta.
- [x] Vykresliť odrezané pixely s tmavým prekrytím aj nad paddingom; zachovať správne mapovanie dostupného natívneho detailu a kvapkadla.
- [x] Overiť spätné rozšírenie všetkými ôsmimi úchytmi jedným gestom a aktualizovať EN/SK/CS návody.
- [x] Dokončiť kompletné testy, Ruff, syntax, diagnostiku a živú GUI kontrolu.
- [x] Zostaviť Windows one-file EXE a overiť source/frozen smoke.

### Výsledky 0.8.1

- Celá sada **651 passed, 1 skipped** (38,38 s). Štrnásť nových prípadov pred opravou reprodukovalo nesprávny Fit a chýbajúce stmavenie; nové regresie overujú aj natívny kontext bez starého paddingu a nadväzujúce crop gestá s uložením relácie.
- Pri **200 % škálovaní displeja 57 passed** (7,00 s) pre inline úchyty a celý workflow výrezu. Ruff, compileall a IDE diagnostika zmenených Python súborov bez chýb.
- Živé PySide6 MCP GUI so vzorkou 1600 × 900 px potvrdilo tmavý kontext po uvoľnení, celý originál pri 100 % a návrat pravého dolného rohu jedným gestom. Natívny detail sa úspešne obnovil a workery skončili; izolovaná aplikácia sa ukončila s exit 0.
- Source aj nový one-file Windows EXE **13/13 smoke kontrol, exit 0**, frozen=true v zabalenom behu a errors=[]. Zahŕňa orientáciu, priehľadnosť, generovaný HEIC, HDR kodeky, dostupnú reálnu ISO gain-map HEIC vzorku, export, kolízie, reláciu a nový Fit po výreze. Zvyšné štyri historické HDR vzorky v aktuálnom priečinku nie sú; 84 MP test sa pri oprave GUI neopakoval.
- Výstup: `dist/InstaGPhotoProcessor.exe`, **76 998 269 B**, SHA-256 `056E68CC1CE37115861457A29F4B94B71EC5D1CBE9C35F0E596C352FCCCE8CD3`. Osobný TODO a používateľské fotografie ani nastavenia sa nemenili; bez Git publikovania.

## História úpravy 0.8.0 — 11. 11. 2026

Stav: **implementované a overené vrátane finálneho Windows EXE**. Používateľ výslovne žiada priame crop úchyty a premenovanie aplikácie. Prezentačný web sa iba navrhuje do chatu; osobný TODO zostáva nezmenený.

- [x] Nahradiť modal a číselný crop editor úchytmi na hranách a rohoch v strednom náhľade.
- [x] Pri ťahaní zachovať kameru a pôvodné pixelové mapovanie, priebežne ukladať zmeny, po uvoľnení obnoviť Fit view; Escape vracia počiatočný výrez.
- [x] Overiť obnovu orezaných okrajov smerom von, hranice originálu, rohy a minimum 1 × 1 px bez resize.
- [x] Umiestniť Reset crop pod Center image vpravo a zachovať gestá pre posun fotografie a viewportu aj pravý dvojklik.
- [x] Premenovať produkt na Insta G Photo Processor, EXE, metadáta, CLI a súbor .code-workspace; zachovať modul insta_g a fyzickú koreňovú cestu.
- [x] Zachovať pôvodné dáta pomocou fallbacku zo zatiaľ prázdneho nového priečinka na existujúci starý stav; explicitné --data-dir nemení význam.
- [x] Aktualizovať pravidlá a EN/SK/CS návody; zaznamenať open-source zámer bez vymýšľania licencie.
- [x] Overiť oficiálne podklady GitHub Pages a pripraviť návrh webu do chatu bez jeho vytvorenia či publikovania.
- [x] Dokončiť regresie, syntax, diagnostiku a živú GUI kontrolu.
- [x] Zostaviť nový Windows one-file EXE a overiť source smoke.
- [x] Dokončiť frozen smoke finálneho EXE.
- [x] Doplniť konečné výsledky a údaje buildu.

### Výsledky 0.8.0

- Celá sada **635 passed, 1 skipped** (42,22 s). Zahŕňa zatvorenie počas cropu a chybu ukladania, Escape s obnovou staršej exportnej chyby bez straty novej nesúvisiacej chyby a floating-point hraničné hit testy úchytov.
- Cielená sada natívneho detailu a cropu: **69 testov prešlo**. Ruff, compileall a IDE diagnostika všetkých zmenených Python súborov bez chýb.
- Samostatný opt-in 84 MP test sa pri zmene GUI a značky neopakoval. Historický úspech v 0.7.0 je zachovaný nižšie a nepredstavuje nový beh pre 0.8.0.
- Source aj finálny Windows EXE prešli **17/17 smoke kontrolami, exit 0**, s piatimi reálnymi HDR vzorkami; inline_crop_handles potvrdzuje priame úchyty bez modalu. Zabalený beh potvrdil frozen=true a prázdny zoznam chýb.
- Živé PySide6 MCP GUI overilo nový titulok/onboarding a panorámu 5000 × 1000 px so šiestimi dielmi. Počas ťahania bol aktívny crop (100, 100, 5000, 1000) a natívny detail zostal dostupný. Reset crop leží pod Center image; reset obnovil crop_box=None a natívny stav bez dialógu.
- Nainštalované metadáta .egg-info a CLI používajú nový názov projektu a verziu 0.8.0.
- Výstup: `dist/InstaGPhotoProcessor.exe`, **76 997 113 B**, SHA-256 `A38B85A94F53F434418822BA0AC02C7FDF89DC1D90D7266DEED9F15C9D8DB4B6`. Build aj frozen smoke dokončené. Osobný TODO bez úprav; bez Git publikovania.

Historické výsledky nižšie patria svojim vydaniam a nedokazujú overenie aktuálneho kódu.

## História rozšírenia 0.7.0 — 11. 11. 2026

Stav: **implementované a overené vrátane finálneho Windows EXE**. Rozsah vychádza z výslovnej požiadavky používateľa; osobný TODO zostáva nezmenený.

- [x] Zaviesť crop_box v pôvodných správne orientovaných pixeloch, prísnu validáciu a zdieľanú geometriu vstupného výrezu bez resize.
- [x] Zachovať úplný rozmer originálu a source_box; retained percentá počítať voči celej pôvodnej fotografii.
- [x] Zaviesť schému 6, migráciu schém 1–5 s presnou zálohou a zachovaním platného exportu bez výrezu.
- [x] Dokončiť a overiť SDR/HDR render a export, crop-only pozadie, natívnu cache a správne vzorkovanie zmenšeného náhľadu.
- [x] Overiť editor nad celým originálom: kreslenie, posun, hrany/rohy, presné X/Y/šírku/výšku, OK/Cancel/Reset a všetky tri jazyky.
- [x] Overiť prepojenie hlavného okna, invalidáciu exportu, reláciu a obnovenie Fit view na celý výrez aj plátno.
- [x] Aktualizovať verziu, pravidlá a EN/SK/CS návody.
- [x] Dokončiť celú sadu, Ruff a syntax; overiť IDE diagnostiku modelov a GUI.
- [x] Dokončiť IDE diagnostiku renderovacej časti, samostatný 84 MP test, živé GUI a source smoke.
- [x] Zostaviť Windows one-file EXE a overiť frozen smoke vrátane reálnych HDR vstupov.
- [x] Doplniť konečné namerané výsledky a údaje buildu.

### Výsledky 0.7.0

- Celá sada: **611 passed, 1 skipped** (39,20 s). Nové regresie overujú pôvodné crop súradnice, SDR/HDR export, mierku a farby na okrajoch, natívny detail, editor, retained percentá a exportný stav.
- Samostatný opt-in **84 MP test: 1 passed** (12,60 s). Overuje celý originál, 4K prehľad, 50 MP vstupný výrez (1000, 1000, 11000, 6000), jeho natívny ROI aj 4K náhľad z tej istej cache a export 147 MP plátna.
- Migrácia v5 uchováva presné pôvodné UTF-8 bajty vrátane CRLF, neprepisuje starý súbor pri načítaní a zachováva exportovaný stav bez cropu. Neplatný vstupný ani exportovaný crop v JSON sa nevynecháva; neplatný save zachová pôvodnú reláciu.
- Ruff a compileall čisté. IDE diagnostika všetkých zmenených Python súborov vrátane HDR/renderu a workerov bez chýb.
- Zmenšenie cropu používa izolovanú celočíselnú redukciu ROI a záverečný Lanczos. Crop obchádza LOD celého originálu, aby sa nevracali odrezané farby; natívny export zostáva 1:1 bez resize.
- Source aj finálny Windows EXE **0.7.0: 17/17 smoke kontrol, exit 0**, vrátane piatich reálnych HDR vzoriek. Nová kontrola source_crop_preview_export overuje 1000 × 500 → 800 × 400 px, posun a padding na 800 × 800 px, export a nezmenený hash originálu; GUI scenár potvrdzuje modal aj obnovu celého vstupu.
- Živé PySide6 MCP GUI potvrdilo editor 1000 × 500 → 800 × 400 px pri X/Y 100/50 a 64 %. Expand 1:1 s offset_y=0,75 vytvára plátno 800 × 800 a foreground_box (0, 350, 800, 750), detail zdieľa plný zdroj 1000 × 500 px. Integračný split scenár vytvára dva diely 400 × 400 px.
- Živé GUI overilo opätovné otvorenie, Cancel bez zmeny výrezu a uvoľnenie zatvoreného editora.
- Source aj frozen skončili s exit 0. Zdieľané rasterové helpery SDR/HDR sú v [raster.py](../insta_g/core/raster.py), bez kruhovej závislosti.
- Výstup: `dist/InstaGImageResizer.exe`, **77 000 037 B**, SHA-256 `3A191F1289A9C869E07222571B90A99193954F641652A3FB4E91DC09F1F0EBA1`. Osobný TODO bez úprav; bez Git publikovania.

## História úpravy 0.6.1 — 11. 11. 2026

Stav: **implementované a overené vrátane Windows EXE**. Pravý dvojklik obnovuje iba pohľad rovnako ako Fit view; osobný TODO zostáva nezmenený.

- [x] Overiť existujúce reset_view a jeho väzbu na Fit view; nie sú potrebné nové externé API.
- [x] Pravý dvojklik ukončí prípadný viewport drag a obnoví zoom 100 % a vycentrovaný celý originál aj plátno.
- [x] Zachovať pravé ťahanie a ľavý dvojklik centrujúci fotografiu bez zmeny zoomu.
- [x] Overiť zachovanie offsetov fotografie, exportnej snímky a bajtov relácie pri pravom dvojkliku.
- [x] Overiť regresie, syntax, diagnostiku, source/frozen smoke a Windows EXE.
- [x] Aktualizovať verziu, pravidlá a EN/SK/CS návody.
- [x] Doplniť skutočné výsledky overenia a konečného buildu.

### Výsledky 0.6.1

- Pred opravou tri varianty regresie potvrdili chýbajúci reset pravým dvojklikom. Po oprave **40 cielených testov prešlo** (5,73 s); Ruff, compileall a IDE diagnostika zmenených súborov bez chýb.
- Overená zhoda s Fit view pri 100/250/1000 %, uvoľnenie tlačidla a následný pohyb, zachovanie kvapkadla, offsetov, exportnej snímky a presných bajtov relácie. Obsluha používa spoločné reset_view a ukončenie gesta.
- Source aj nový Windows one-file EXE **16/16 smoke kontrol**, vrátane pravého dvojkliku, HEIC a piatich reálnych HDR vzoriek. Build cez rovnaký projektový scripts/build.py; úloha VS Code v tomto kontexte vracala No invocation context.
- Source aj frozen skončili s exit 0. EXE: `dist/InstaGImageResizer.exe`, **76 978 765 B**, SHA-256 `94524567AB9E6C1A1797173483135B3687CDD691A1B2A03D783A9029B5CCDC6F`.
- Celá sada ani 84 MP test sa pri zmene kamery neopakovali; posledné úplné výsledky zostávajú v histórii 0.6.0. Osobný TODO bez úprav; bez Git publikovania.

## História rozšírenia 0.6.0 — 11. 11. 2026

Stav: **implementované a overené vrátane Windows EXE**. Rozsah vychádza z výslovnej požiadavky na adaptívny náhľad; osobný TODO sa nemení.

- [x] Overiť oficiálne podklady pre fyzické pixely viewportu/DPR, Qt kreslenie a Pillow resampling/dekódovanie.
- [x] Ponechať rýchly základ do 2048 px a automaticky načítať jeden aktívny SDR originál už pri 100 % pohľade podľa dostupnej RAM.
- [x] Natívny výrez prispôsobiť fyzickým pixelom viewportu bez pevného 2048 px stropu; nevytvárať celé rozšírené natívne plátno.
- [x] Zachovať okamžitú transformáciu dostupného natívneho popredia a priebežné spresňovanie počas myši, zoomu, posuvníkov a pomeru.
- [x] Zachovať jednu aktívnu a jednu najnovšiu čakajúcu požiadavku, odmietanie zastaraných výsledkov a viditeľné vysvetlenie fallbacku.
- [x] Regresie pre fit 100 %, DPR, pohyb a geometriu, RAM, cache, zmenu fotografie a nezmenené exportné/persistované správanie.
- [x] Overiť syntax, diagnostiku, celú sadu, veľký originál a source smoke.
- [x] Dokončiť Windows EXE a frozen smoke.
- [x] Aktualizovať verziu, pravidlá a EN/SK/CS návody pre nový model náhľadu.
- [x] Doplniť skutočné výsledky overovania a konečného buildu.

### Výsledky 0.6.0

- Kompletná finálna sada: **508 passed, 1 skipped** (55,07 s). Preskočený opt-in veľký test sa spustil samostatne: **1 passed** (23,19 s).
- Reálny 84 MP originál prešiel 4K fit náhľadom 3840 × 1280 px, natívnym detailným výrezom zo spoločnej cache a exportom 147 MP plátna. Náhľad nevytvoril plný raster rozšíreného plátna.
- Source aj finálny Windows EXE **0.6.0: 16/16 smoke kontrol, exit 0**, s piatimi reálnymi HDR vzorkami. Ruff, compileall a IDE diagnostika zmeneného kódu bez chýb.
- Natívne popredie zostáva dostupné aj po dokončení malého preview; regresia chráni reuse pri vynechaní už existujúcej zdrojovej vrstvy. Pamäťová chyba voliteľnej LOD cache umožní priamy render z originálu, ak sa samotný viewport zmestí do rozpočtu.
- Syntetický benchmark 24 MP (6000 × 4000 px), mediány piatich zahriatych behov: fit 1200 × 800 px **300,193 → 42,970 ms** (LOD faktor 4); 4K **496,101 → 502,386 ms** (bez LOD); natívny výrez **25,862 → 27,199 ms**. Prvý adaptívny fit vrátane decode/LOD **711,250 ms**. Ide o jeden stroj a worker render, nie dôkaz 60 FPS; GUI dostupné pixely transformuje bez čakania.
- PySide6 MCP overil živý natívny raster 2650 × 1055 px a 20 pravých posunov bez straty detailu a bez zmeny bajtov relácie. Doplnková regresia chráni stav pri oneskorenom dokončení staršieho viewportu.
- Windows build cez projektovú úlohu VS Code a frozen smoke dokončené. EXE: `dist/InstaGImageResizer.exe`, **76 978 311 B**, SHA-256 `F38CD800C3E909E77DC89A1BCA4C832138B545A5230181AF95D5E57F8B51698C`. Osobný TODO bez úprav; bez Git publikovania.

## História opravy 0.5.2 — 11. 11. 2026

- [x] Vrátiť φ a odstrániť rozdielne písmo tlačidla/tooltipu.
- [x] Pravý posun viewportu bez zmeny fotografie, exportného stavu či ukladania.
- [x] Overiť rozlíšenie uvoľnenia tlačidiel, dvojklik, kvapkadlo a Escape.
- [x] Regresie rovnakého štýlu v troch jazykoch a oboch témach.
- [x] Konečná sada, source/frozen smoke, vizuálna kontrola a Windows build.
- [x] Konečné výsledky dokumentácie.

### Výsledky 0.5.2

- Celá sada: **485 passed, 1 skipped** (58,42 s). Veľký opt-in test sa pri tejto vstupnej/UI zmene neopakoval; predchádzajúci výsledok zostáva v histórii. Ruff, syntax a IDE diagnostika zmenených súborov bez chýb.
- Osem nových testov pravého posunu pokrýva fit aj zoom, pravý dvojklik, kvapkadlo, vlastníctvo gesta pri viacerých tlačidlách, Escape, prázdny náhľad a skutočný MainWindow s nezmenenou exportnou snímkou a bajtmi session.json.
- Šesť štýlových regresií (EN/SK/CS × light/dark) overuje φ, rovnakú výšku tlačidiel, spoločné písmo a výšku skutočne zobrazených tooltipov. Vizuálne Qt overenie potvrdilo 37 px výšku všetkých volieb a spoločné 10 pt písmo.
- Source aj Windows one-file EXE **16/16 smoke kontrol, exit 0**, s overeným pravým posunom bez mutácie fotografie/relácie a symbolom φ. Nový EXE bol úspešne zostavený do štandardného dist priečinka po zatvorení staršej aplikácie.
- EXE: `dist/InstaGImageResizer.exe`, **76 971 370 B**, SHA-256 `712201B1873BD450B901A4EACC2A1A7B04CE08233E284023F0ED4FB544767D5C`. Osobný TODO bez úprav; bez Git publikovania.

## História opravy 0.5.1 — 11. 11. 2026

- [x] Reprodukovať zlé centrovanie zoomu, nevykreslené živé posuny, blokovanie GUI a odmietané hi-res detaily.
- [x] Kompozícia s poradím Žiadna, 2×2, 3×3, oko, X; zachovanie enumov relácie.
- [x] Okamžitá Qt geometria nad cache, stabilná kamera a centrovanie celého originálu pri 100 %.
- [x] Cache pozadia, identity/solid rýchle vetvy a najnovšie požiadavky bez hromadenia jobov.
- [x] Každá revízia relácie uložená asynchrónne v poradí; bezpečný close a chybové stavy.
- [x] Detail podľa dostupnej RAM bez pevného 512 MiB capu, presnejší HDR odhad a zobrazený dôvod fallbacku.
- [x] Regresie vrátane reálneho 12 MP HDR a viditeľného jemného natívneho detailu.
- [x] Konečné porovnanie výkonu, celá sada, source/frozen smoke a Windows EXE.
- [x] Konečné výsledky a návody.

### Výsledky 0.5.1

- Kompletná sada **471 passed, 1 skipped** (62,06 s). Osobitne zapnutý reálny **84 MP test: 1 passed** (21,95 s), vrátane natívneho hi-res výrezu a 147 MP exportného plátna.
- Source aj finálny Windows one-file EXE **0.5.1: 16/16 smoke kontrol, exit 0**. Jemné pruhy z 4096 px originálu sa pri zoome obnovili; 2048 px základ bol v tejto oblasti bez detailu. Overený návrat na 100 %, relácia dopísaná mimo GUI a päť reálnych HDR vzoriek.
- Meraná opakovaná obsluha posunu pri 1000 záznamoch (polovica zelených): medián **80,684 → 0,711 ms**, p95 novej cesty 1,133 ms. Prvý prechod zelená→žltá má jeden prepočet knižnice (30,991 ms). Namerané na overenom stroji, 40 následných zmien.
- Worker expand/blur pri opakovaných offsetoch: **682,745 → 99,156 ms** po zahriatí cache; samotný živý Qt pohyb má približne 4 ms v meranom viewporte a na worker nečaká. Pri zmene filtra sa pozadie musí znovu pripraviť.
- Regresie overujú FIFO každého zápisu, privátne snímky, členstvo knižnice, recovery, bezpečný close aj viditeľnú konečnú diskovú chybu. Preview/detail sa nehromadia: jeden aktívny a jedna najnovšia čakajúca požiadavka.
- Vizuálne PySide6 MCP: Composition s poradím None / 2×2 / 3×3 / monochromatické oko / X a Native detail. Jednotkové interakčné testy overujú aj SK/CS, všetky ovládače zoomu a fit pri krajných posunoch.
- Finálny EXE: `dist/0.5.1/InstaGImageResizer.exe`, **76 969 384 B**, SHA-256 `147AAD7C3485697E6848BE3C688CA567197439BD410DB90EC6F565AF0433C744`. Pôvodný cieľ Windows nepovolil prepísať; dokončený build je vo verziovanom priečinku. Bežiace používateľské procesy sa neukončovali.
- Ruff, syntax a IDE diagnostika zmenených súborov bez chýb. Osobný TODO zostal bez úprav; licencia projektu ani predaj sa nemenili.

## História dodávky 0.5 — 10. 11. 2026

- [x] Výskum kompozičných mriežok, dominantných farieb, Qt interakcie a skutočného HDR/gain-map spracovania.
- [x] Ťahanie fotografie, centrovanie dvojklikom, zoom 100–1000 % a detail originálu s pamäťovým rozpočtom.
- [x] Päť kompozičných mriežok, pozadia blur/RGB/kvapkadlo a odlišné dominantné farby.
- [x] Červený stav chýb, retry/remove, rollback neúplnej série a súhrnný dialóg exportu.
- [x] Preferences, prvotné nastavenie, systémová/light/dark téma a EN/SK/CS GUI s návodom.
- [x] Výpočet zachovanej plochy a migrácia relácie na schému 5.
- [x] HDR dekódovanie a farebné prevody v samostatnom jadre; nové natívne kodeky v build skripte.
- [x] Dokončiť integráciu HDR testov a presne zapísať overený rozsah/obmedzenia.
- [x] Kompletný pytest, statická diagnostika, source/frozen smoke a vizuálna kontrola.
- [x] Nový Windows EXE a konečné výsledky dokumentácie.

Osobný TODO sa nemení. Publikovanie, licencia projektu, predaj a web sú zatiaľ iba diskusia s používateľom.

### Výsledky 0.5

- **429 passed, 1 skipped** v kompletnej finálnej sade (41,19 s). Samostatne zapnutý **84 MP test 1 passed** (18,65 s), spoločné plátno 147 MP a natívne exportné diely.
- Source aj finálny one-file EXE: **16/16 smoke kontrol, exit 0**, s reálnymi Apple HDR JPEG new/old, Apple HEIC v1, Samsung ISO HEIC a malým Google ISO HEIC. Overené opätovné HDR dekódovanie, SDR prevod a prípony.
- Frozen smoke overil pribalené imagecodecs/libultrahdr/Little CMS a HEIF DLL, Windows Qt platform plugin, tri návody, neúplnú sériu aj pokračovanie ďalšou fotografiou.
- Nezávislý audit našiel a regresie pokrývajú nechcenú stratu HDR voľby pri cache miss, prepísanie exportnej chyby dočasnou chybou náhľadu, Skip s nepredvolenými uloženými hodnotami, preklad už zobrazených chýb a pamäť HDR blur. Fill preskakuje nepotrebné pozadie.
- Vizuálne PySide6 MCP: prvotný dialóg, light/dark, modré/zelené/červené položky, ovládanie zoomu bez orezaných ±, kompozičné čiary, súhrnný dialóg a dlhý scrollable pomocník.
- Ruff a syntax bez chýb. IDE diagnostika zmenených súborov bez chýb; existujúce upozornenie MD037 v osobnom TODO sa neopravovalo, pretože poznámky zostali nezmenené.
- Finálny EXE **76 951 307 B** (~73,4 MiB), SHA-256 `DA5B99D9B1BB8A71037261A584BBBC041FD4DE73DBFEDE271FD9B6F9F96474EB`. Zostavený na Windows 11 x64 a následne overený frozen smoke.
- Overenie fyzického HDR monitora, všetkých telefónov a čistej Windows VM sa nevykonalo. HDR JPEG má skutočný limit kodeku 8192 px/hrana, SDR JPEG 65 500 px/hrana. HDR HEIC sa znovu kóduje ako 10-bit PQ/BT.2020; pôvodný bitstream sa nekopíruje.

## História opravy 0.4.1 — 10. 11. 2026

- [x] Spoločný filter povoľuje export iba stavov Pripravené/Exportované, aj pri označených fotografiách.
- [x] Tlačidlá, menu, dialógy aj priame start_export používajú rovnakú podmienku a nemenný zoznam kandidátov pri spustení.
- [x] Prázdny oprávnený výber nemení exportný cieľ ani nevytvára priečinok; importované záznamy zostávajú nedotknuté.
- [x] Regresie, source/frozen smoke a nové Windows EXE.
- [x] Konečné výsledky dokumentácie.

### Výsledky 0.4.1

- Kompletný pytest: **267 passed, 1 skipped**. Ruff, syntax a IDE diagnostika bez chýb.
- Source aj Windows one-file EXE **0.4.1**: **7/7 kontrol, exit 0**. Pri troch modrých importoch zostali oba exporty vypnuté aj po zaškrtnutí; priame spustenie nevytvorilo priečinok. Po otvorení prvej fotografie export vybraných aj všetkých spracoval iba ju a dve stále modré preskočil. Po otvorení zvyšných fotografií sa úspešne exportovali všetky tri.
- Jeden spoločný `_export_candidates` filter je použitý v tlačidlách, menu, dialógoch aj `start_export`. Snímka kandidátov sa po štarte nemení, ani keď používateľ otvorí ďalšiu fotografiu alebo zmení checkboxy.
- Jedenásť workflow testov pokrýva aj zmiešané žlté/zelené/modré fotografie, označené modré položky, opakovaný export zeleného obnoveného záznamu a zachovanie importovaných dát bez mutácie.
- Finálny približne 61 MiB EXE zostavený na Windows 11 x64 cez VS Code úlohu. Existujúce nastavenia ani osobný TODO sa nemenili.

## História úpravy 0.4 — 10. 11. 2026

- [x] Export označených fotografií podľa snímky checkboxov; aktívny náhľad neurčuje exportný rozsah.
- [x] Modré Importované, žlté Pripravené po úspešnom aktívnom náhľade a zelené Exportované.
- [x] Bez automatického výberu po importe; neúspešný, zrušený alebo zastaraný náhľad pripravenosť nenastaví.
- [x] JSON schéma 4 s príznakom previewed, migráciou a zachovaním prázdneho výberu.
- [x] Regresie stavov, perzistencie, selektívneho exportu a súbežných zmien checkboxov.
- [x] Celá sada, source/frozen smoke, vizuálna kontrola a nové Windows EXE.
- [x] Zápis konečných výsledkov do dokumentácie.

### Výsledky 0.4

- Kompletný pytest: **262 passed, 1 skipped**. Opt-in veľký test zostáva v bežnom behu preskočený. Ruff, syntax aj IDE diagnostika bez chýb.
- Source aj Windows one-file EXE **0.4.0**: **7/7 kontrol, exit 0**. GUI kontrola potvrdila tri pôvodne importované fotografie bez náhľadu, príznak previewed iba na jednej otvorenej fotografii a selektívny export jednej označenej položky pred exportom všetkých.
- PySide6 MCP: po importe všetky tri riadky modré a žiadny aktívny náhľad; po výbere druhého riadka zožltol iba druhý, po exporte prvého checkboxu vznikol zoznam zelená/žltá/modrá. Príznaky previewed boli False/True/False.
- Pripravenosť sa zapisuje iba pre úspešne prijatý aktuálny náhľad. Zrušenie, oneskorená generácia, chyba, miniatúra a checkbox ju nemenia. Stav aj prázdny výber sa obnovia z JSON schémy 4.
- Rozsah selektívneho exportu je nemenná snímka checkboxov pri spustení. Aktívny náhľad ani zmeny checkboxov počas dávky ho nemenia.
- Finálny približne 61 MiB EXE zostavený cez VS Code úlohu a overený na Windows 11 x64. Osobný TODO zostal bez úprav.

## História úpravy 0.3 — 10. 11. 2026

- [x] Samostatné checkboxy a červený kôš v každom riadku, žlté/zelené stavové pozadie s hoverom.
- [x] Štyri ľavé akcie: odstrániť vybrané, všetky, exportovať všetky a odstrániť exportované. Odstránenie iba z knižnice.
- [x] Úspešné exportné snímky a checkboxy v JSON schéme 3 s migráciou v1/v2; ochrana pred partial exportom a zmenami počas batchu.
- [x] Dva prepínače režimu, anglické Fit / Padding a Fill / Crop, nové predvoľby a maximalizovaný štart.
- [x] Integračné regresie hromadných akcií, obnovenia stavov a súbežného importu/exportu.
- [x] Celý pytest, source/frozen smoke, vizuálne overenie a nový Windows build.
- [x] Konečné výsledky dokumentácie.

### Výsledky 0.3

- **234 passed, 1 skipped**; opt-in 84 MP test zostáva v bežnej sade preskočený. Overených 163 core/persistence, 28 resources, 20 integračných GUI, 15 delegát/zoznam a 8 panelových testov.
- Source aj Windows one-file EXE **0.3.0**: **7/7 kontrol, exit 0**. Overený HEIC, export, maximalizované okno, checkbox a tri úspešne exportované fotografie so zeleným stavom uloženým do JSON.
- Regresie zachytia partial export, zmeny nastavení počas batchu, nahradenie záznamu rovnakou cestou aj oneskorené úspešné/chybové výsledky už odstráneného importu.
- PySide6 MCP vizuálne potvrdil žlté aj zelené pozadie vrátane hoveru, checkboxy, červené koše, štyri akcie vľavo a presné Fit / Padding, Fill / Crop.
- Ruff, syntax a IDE diagnostika bez chýb; nový EXE približne 61 MiB zostavený cez VS Code úlohu a overený na Windows 11 x64.
- Hromadné odstránenie aj kôš menia iba knižnicu. Vstupné ani exportované súbory sa nemažú; osobný TODO zostal bez úprav.

## História úpravy 0.2 — 10. 11. 2026

- [x] Overiť príčinu 80 MP limitu, správanie pamäte a JPEG limity v oficiálnych zdrojoch.
- [x] Nahradiť pevný limit kontrolou dostupnej RAM, úsporným JPEG náhľadom a exportom po dieloch.
- [x] Zachovať pôvodnú mierku pixelov: Fit pridáva plátno, Fill vyrezáva oblasť; bez resize ovládača.
- [x] Pridať horizontálny/vertikálny posun, priame ratio tlačidlá 16:9 až 3:4 a odstrániť orientáciu.
- [x] Odstraňovať iba neaktuálne chyby náhľadu po úspešnom novom náhľade.
- [x] Pripraviť JSON schému 2 a migráciu v1 so zachovaním pôvodného JSON pred prvým zápisom.
- [x] Spustiť regresie, reálny 84 MP import/export, GUI inšpekciu a Windows build so smoke testom.
- [x] Doplniť konečné výsledky do dokumentácie; osobný TODO zostáva bez úprav.

Natívne pixely znamenajú mierku 1:1 popredia. Výsledné rozmery sa menia iba doplnením plátna alebo orezaním. Pamäťový odhad nenahrádza fyzickú RAM; PNG/HEIC môžu stále vyžadovať plné dekódovanie. JPEG limit 65 500 px platí pre jeden diel, nie súčet celej panorámy. Dekoratívne pozadie smie používať malý raster, popredie exportu nie.

### Výsledky 0.2

- Celá bežná sada: **179 passed, 1 skipped** (117 core, 28 resources, 21 persistence, 13 GUI); veľký test sa v bežnom behu preskakuje.
- Osobitný reálny 84 MP JPEG test: **1 passed**, 23,92 s. Vstup 12 000 × 7000 px; spoločné plátno 21 000 × 7000 px = 147 MP; tri výstupy 7000 × 7000 px. Overené rozmery, preview limit a pôvodná poloha farebných oblastí.
- Nezávislá kontrola našla predčasné PNG dekódovanie pri getexif; RAM kontrola je presunutá aj pred čítanie metadát. Obe vetvy (plný vstup/náhľad) sú pokryté regresiou.
- Source aj Windows one-file EXE **0.2.0**: **7/7 kontrol, exit 0**, reálny HEIC, natívny Fit/Fill a posun, JPEG 99/sRGB/bez EXIF, bezpečný opakovaný export, JSON stav, Qt platform plugin a workery.
- PySide6 MCP: vizuálne skontrolovaný Fit s paddingom aj Fill s tlmeným presahom, bielym rámom a číslovaním; pri 1800 × 600 px a štyroch štvorcových dieloch Fill vytvára 4 × 450 × 450 px. Resize/orientácia ani ratio combobox sa nezobrazujú.
- Ruff, syntax aj IDE diagnostika bez chýb. Finálny EXE má približne 61 MiB a je zostavený cez VS Code build úlohu. Testované na Windows 11 x64; samostatná čistá Windows VM nebola použitá.
- Starý stav schema1 sa migruje a jeho pôvodné bajty sa pred prvým zápisom zachovajú v samostatnom v1-backup JSON. Osobný TODO nebol upravený.

## História 0.1 — zadanie a rozhodnutia

Windows aplikácia s tromi nastaviteľnými panelmi: knižnica fotografií s drag & drop, stredový náhľad a pravý panel nastavení vybratej fotografie. GUI bude v slovenčine. Ponuka Súbor poskytne import, export a ukončenie; Pomocník informácie o aplikácii.

Pillow + pillow-heif zabezpečia JPEG, PNG a HEIC. Export bude JPEG kvalita 99, bez chromatického podvzorkovania, predvolene šírka 1080 px na jeden diel. Používateľ bude môcť zmeniť výstupnú šírku. Originály zostanú nedotknuté.

Split rozdelí celý zdroj na nadväzujúce vertikálne pásy. Automatický pomer vychádza z `šírka / (výška × počet dielov)` a ohraničí sa na Instagram rozsah 3:4 až 1.91:1; prípadný nesúlad doplní pozadie. Pevné pomery tiež zachovajú celý obraz doplnením pozadia. Expand vloží celý originál do výsledného plátna; pri vertikálnych fotografiách typicky doplní boky. Pozadie tvorí vyplnená kópia fotografie s Gaussian blur 0–1000 px, meraným vo výstupných pixeloch. Orezanie je prípustné len pri dekoratívnom pozadí.

Predvoľby: 16:9, 3:2, 4:3, 5:4, 1:1, s orientáciou krajina/portrét. Plynulý slider 1:1 až 16:9 používa pre portrét recipročnú hodnotu. Portréty 9:16 a 2:3 sú dostupné podľa zadania, ale GUI upozorní na prekročenie limitov Instagramu. Auto je dostupné len pri splite. Počet dielov 2–20. Preview celej kompozície bude maximálne 2048 px na dlhšej hrane, s hranicami a číslami dielov.

Stav obsahuje verzovanú schému, zoznam ciest, individuálne nastavenia, výber a posledný exportný priečinok. Zápis po každej zmene je atómový. Umiestnenie sa určí cez Windows Documents; poškodený JSON sa zachová a chyba sa oznámi. Import, dekódovanie, preview a export bežia na pozadí; zastarané preview sa ignorujú.

## Poradie realizácie

1. [x] Prečítať šablónu a preskúmať repozitár.
2. [x] Dokončiť online výskum a zaznamenať zdroje.
3. [x] Vytvoriť pravidlá `AGENTS.md` a tento plán pred implementáciou.
4. [x] Implementovať dátové modely, geometriu, kodeky a export.
5. [x] Implementovať perzistenciu, GUI a workery.
6. [x] Vytvoriť Python build skript a úspešne zostaviť Windows one-file EXE.
7. [x] Po prvom úspešnom builde vytvoriť automatické testy a vykonať ich.
8. [x] Overiť GUI, JPEG/PNG/HEIC aj zabalené EXE; po opravách build zopakovať.
9. [x] Dokončiť README, osobný TODO a CHANGELOG; zaznamenať skutočné výsledky.

## Stratégia overovania

Testy overujú obsah a rozmery obrazov, hranice splitov bez stratených pixelov, pomery a zaokrúhľovanie, blur, ICC/EXIF, priehľadnosť, kolízie názvov, obnovu/poškodenie JSON a individuálny stav GUI. Integračný smoke režim spustiteľný aj v EXE overuje dekódery, spracovanie, export a Qt platform plugin v izolovanom dočasnom priečinku. Reálne výsledky sú uvedené nižšie.

## Výsledky realizácie — 9. 11. 2026

- Prvý Windows one-file build dokončený pred tvorbou testov, podľa požadovaného poradia. Po opravách sa EXE zostavilo znovu.
- Kompletný pytest beh: **114 passed** (88 core, 17 persistence, 9 GUI). Ruff aj kompilácia syntaxe bez chýb.
- Source aj frozen EXE diagnostika: **7/7 kontrol**, návratový kód 0, vrátane skutočného HEIC a natívneho Windows Qt pluginu.
- Cez PySide6 MCP vizuálne overené tri panely, import JPEG/PNG/HEIC, náhľad splitu aj expand a dávkový export.
- Testy odhalili a pokryli zaokrúhľovanie pomerov na hraniciach Instagram rozsahu; GUI aj export používajú tú istú geometriu. Nadmerné plátno zobrazí chybu bez pádu Qt slotu.
- Ukladanie používa zhodné limity pri save/load, atómové zápisy a zachovanie poškodeného JSON. Export neprepisuje existujúce súbory a funguje aj na Windows FAT/exFAT.
- Výstup je `dist/InstaGImageResizer.exe`, približne 61 MiB. Overený Windows 11 x64 / Python 3.13.17; samostatný čistý Windows VM test nebol vykonaný.
- Úvodné prerušenie pre nedostatok kreditov a nefunkčný spúšťač úloh neovplyvnili konečné overenie. Finálne buildy už úspešne spustila VS Code úloha.
- Dokumentácia vysvetľuje nepodporované úzke portréty, HDR obmedzenie, pixelový limit a ochranu osobného TODO.
