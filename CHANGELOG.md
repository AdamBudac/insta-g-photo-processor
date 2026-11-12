# Changelog

## Web a dokumentácia 1.0.0 — 2026-11-12

### Pridané a zmenené

- Statická fotografická prezentácia pre GitHub Pages: pevná navigácia, hero, interaktívny split a doplnenie okrajov, záložky Import/Edit/Export, skutočné snímky GUI, návod a FAQ. Lokálne verzované knižnice Bootstrap/i18next/Marked/DOMPurify nevyžadujú frontendový build ani externé CDN pri návšteve.
- Jedna HTML stránka s okamžitým prepínaním EN/SK/CS bez reloadu a so zapamätaním jazyka. Vzhľad System/Light/Dark rešpektuje preferenciu prehliadača a ručnú voľbu.
- Vývojárske README sú oddelené od návodov pre laikov: README.md (EN), README-sk.md, README-cz.md a samostatné README-user.md, README-user-sk.md, README-user-cz.md. Rovnaké používateľské Markdown súbory číta web aj pomocník aplikácie; PDF a ďalšie kópie nie sú potrebné.
- Pomocník a Windows build používajú nové názvy návodov. Doplnený slovenský postup publikovania cez GitHub Desktop a webové nastavenia GitHub Pages. Používateľ spravuje repozitár, Releases aj publikovanie samostatne.

### Overenie

- Kompletná aplikačná sada **651 passed, 1 skipped** (36,27 s). Ruff, JavaScript syntax a IDE diagnostika dotknutých súborov bez chýb.
- **14 browser scenárov prešlo** v headless Chrome: presný obsah všetkých troch spoločných návodov, okamžité prepínanie bez navigácie, zachovanie ukážok a kapitoly, tri témy, klávesnica a lightbox, nedostupný localStorage, opakovanie po dočasnej chybe návodu a projektový GitHub Pages prefix. Overené šírky 320/390/768/1024/1440 px, vrátane dlhších SK/CS textov, bez horizontálneho presahu. Všetky tri preklady majú 136 kľúčov, všetkých 127 HTML kľúčov je pokrytých.
- Source aj nový Windows EXE **13/13 smoke kontrol, exit 0**, vrátane pribalených návodov, HEIC a dostupnej reálnej ISO gain-map HEIC vzorky. Opt-in 84 MP test sa pri úprave dokumentácie a webu neopakoval. Web zostáva lokálny, bez Git operácií či publikovania; osobný TODO bez úprav.

## 1.0.0 — 2026-11-11

### Zmenené

- Na výslovnú požiadavku používateľa nastavená verzia aplikácie a distribučných metadát na **1.0.0**. Označenie v GUI, príkaze --version a novom Windows EXE vychádza zo spoločnej verzie aplikácie.
- Rozsah funkcií a relácia schémy 6 nadväzujú na 0.8.1. Publikovanie na GitHub ani tvorba prezentačného webu nie sú súčasťou tejto zmeny.

### Overenie

- **15 testov prešlo** (branding a inicializácia). Verzia zdroja, --version a lokálne metadáta balíka zhodne uvádzajú 1.0.0; obnovený aj starší generovaný egg-info záznam. Ruff, syntax a IDE diagnostika zmenených súborov bez chýb.
- Source aj nový Windows one-file EXE **13/13 smoke kontrol, exit 0**, vrátane HEIC, dostupnej reálnej ISO gain-map vzorky, HDR kodekov a GUI. Zabalený report potvrdzuje frozen=true, ok=true a prázdne errors. Kompletná sada ani 84 MP test sa pri samotnom prečíslovaní neopakovali; výsledky 0.8.1 sú uvedené nižšie.

## 0.8.1 — 2026-11-11

### Opravené

- Fit view a 100 % zoom po vstupnom orezaní naďalej zobrazujú celý pôvodný originál aj výstupné plátno. Malý výrez sa automaticky nezväčšuje na celý panel; hrany a rohy možno vrátiť k pôvodným okrajom jedným ťahom.
- Odrezané časti zostávajú viditeľné s tmavým prekrytím aj po uvoľnení úchytu, vrátane oblastí nad paddingom. Dostupný detail sa mapuje podľa pôvodných pixelov bez prenesenia starého pozadia. Kvapkadlo v týchto oblastiach vzorkuje SDR farbu fotografie.
- Návody EN/SK/CS a pravidlá projektu opisujú prispôsobenie na celý originál. Exportný výrez, mierka pixelov a automatické ukladanie zachovávajú svoj význam.

### Overenie

- Celá sada **651 passed, 1 skipped** (38,38 s); samostatná sada výrezu pri 200 % škálovaní **57 passed** (7,00 s). Ruff, compileall a IDE diagnostika zmenených Python súborov bez chýb.
- Živé PySide6 GUI potvrdilo celý originál a trvalé stmavenie po uvoľnení aj spätné rozšírenie rohu jedným gestom. Source aj nový Windows one-file EXE prešli **13/13 smoke kontrolami, exit 0**, vrátane generovaného HEIC, HDR kodekov, dostupnej reálnej ISO gain-map HEIC vzorky a zachovania originálu vo Fit po crope. Historických päť HDR vzoriek sa v tomto behu nepoužilo; opt-in 84 MP test sa neopakoval.

## 0.8.0 — 2026-11-11

### Zmenené

- Produkt sa volá **Insta G Photo Processor**. Aktuálne názvy v aplikácii, metadátach, príkaze, Windows EXE a VS Code workspace používajú novú značku; Python modul `insta_g` a fyzický projektový priečinok zostávajú zachované.
- Vstupný výrez sa upravuje priamo v strednom náhľade úchytmi na hranách a rohoch fotografie. Samostatný crop dialóg a číselné polia X/Y/šírka/výška sú odstránené z používateľského ovládania.
- Kamera pri ťahaní výrezu zostáva stabilná, každá skutočná zmena sa uloží a zneplatní exportnú snímku. Escape obnoví výrez zo začiatku gesta; uvoľnenie myši obnoví Fit view. Hrany možno rozšíriť späť po celý originál bez zmeny jeho súboru.
- Reset crop je priamo pod Center image v pravom paneli. Posúvanie fotografie vnútri záberu, pravý posun kamery a pravý dvojklik pre Fit view zostávajú zachované.
- Nové inštalácie ukladajú stav do Documents/insta-g-photo-processor. Pri existujúcom starom stave aplikácia použije pôvodný dátový priečinok, ak nový nemá session.json ani preferences.json; používateľské dáta sa nepresúvajú a uložený exportný cieľ sa zachová.
- Dokumentácia a EN/SK/CS návody opisujú priame ovládanie výrezu a nový názov. Model výrezu a relácia schémy 6 ostávajú kompatibilné. Zámer open-source zverejnenia je zaznamenaný; konkrétna licencia ani GitHub publikovanie zatiaľ nie sú vykonané. Prezentačný web je v tejto dodávke iba návrh.

### Overenie

- Celá sada **635 passed, 1 skipped** (42,22 s). Regresie pokrývajú úchyty vrátane krajných hodnôt floating-point mapovania, Escape, priebežné uloženie, zatvorenie počas cropu, chybu zápisu, zachovanie staršej exportnej chyby a novej nesúvisiacej chyby. Samostatný opt-in 84 MP test sa pri tejto zmene GUI a značky neopakoval; posledný výsledok patrí 0.7.0.
- Cielené overenie natívneho detailu a cropu: **69 testov prešlo**. Ruff, compileall a IDE diagnostika všetkých zmenených Python súborov bez chýb.
- Source aj finálny Windows EXE prešli **17/17 smoke kontrolami, exit 0**, vrátane piatich reálnych HDR vzoriek a inline crop úchytov bez modalu. Zabalený beh potvrdil frozen=true bez chýb. Živé PySide6 MCP overilo nový názov, panorámu 5000 × 1000 px so šiestimi dielmi, zachovaný natívny detail počas cropu a Reset crop pod Center image.
- Windows one-file EXE **InstaGPhotoProcessor.exe** bol zostavený a samostatne overený; **76 997 113 B**, SHA-256 `A38B85A94F53F434418822BA0AC02C7FDF89DC1D90D7266DEED9F15C9D8DB4B6`.

## 0.7.0 — 2026-11-11

### Pridané a zmenené

- Samostatný nedestruktívny vstupný výrez pred Carousel / Split aj Expand canvas. Editor zobrazuje celý originál, podporuje výber, posun a zmenu veľkosti myšou, nový výber cez Shift + ťahanie aj presné X/Y/šírku/výšku v pôvodných pixeloch. Výrez má ľubovoľný pomer a nemení mierku popredia.
- Crop photo… otvorí editor; OK použije zmenu a obnoví Fit view, Cancel zachová nastavenia. Reset crop obnoví celý záber. Celý originál zostáva dostupný pri ďalšej úprave a vstupný súbor sa nemení.
- Split, doplnenie okrajov, pozadie aj posuny pracujú so zvoleným výrezom. Fit zachová celý výrez; Fill môže ďalej orezať jeho plochu. Dekoratívne pozadie nevzorkuje odrezané okraje originálu.
- Hlavný 100 % pohľad zobrazuje celý vstupný výrez aj plátno. Zachované percentá sa počítajú voči celému pôvodnému originálu, vrátane vstupného aj ďalšieho Fill orezania; 800 × 400 px z 1000 × 500 px predstavuje 64 %.
- Rovnaké súradnice riadia SDR/HDR export, rýchly náhľad aj natívny detail. Detail zdieľa jeden plný zdroj medzi rôznymi výrezmi. Zmenšenie výrezu izoluje jeho okraje pred kvalitným prevzorkovaním, aby sa do výsledku nevracali farby odstránenej plochy.
- Spoločné rasterové helpery SDR/HDR sú oddelené od kodekov bez kruhovej závislosti.
- Relácia schémy 6 ukladá výrez každej fotografie a zahŕňa ho do platnosti exportnej snímky. Migrácia schém 1–5 zálohuje presné pôvodné bajty a pri chýbajúcom výreze zachová celý originál aj platný zelený stav.
- Aktualizované pravidlá, technické rozhodnutia, README a návody v EN/SK/CS; verzia 0.7.0 v metadátach projektu.

### Overenie

- Celá sada **611 passed, 1 skipped** (39,20 s). Regresie pokrývajú súradnice výrezu, pomer/zaokrúhľovanie, SDR/HDR export a zachovanú mierku, farby na okrajoch, natívny detail, editor, retained percentá, exportnú snímku, JSON roundtrip a migráciu schémy 5 so zachovaním zeleného stavu.
- Osobitne zapnutý **84 MP test: 1 passed** (12,60 s), vrátane 4K náhľadu originálu, 50 MP výrezu a natívneho detailu z rovnakej cache aj exportu 147 MP plátna.
- Ruff, compileall a IDE diagnostika všetkých zmenených Python súborov bez chýb.
- Source aj finálny Windows EXE **0.7.0: 17/17 smoke kontrol, exit 0**, vrátane piatich reálnych HDR vzoriek. Nový scenár overuje vstupný výrez, posun/padding, export, nezmenený hash originálu a obnovu celého vstupu.
- Živé GUI cez PySide6 MCP potvrdilo 1000 × 500 → 800 × 400 px, X/Y 100/50, zachovaných 64 % a správny posun na plátne. Finálny Windows one-file EXE bol úspešne zostavený a samostatne overený.

## 0.6.1 — 2026-11-11

### Zmenené

- Pravý dvojklik v náhľade obnoví Fit view: zoom 100 % a vycentrovaný pohľad na celý originál aj plátno. Používa rovnaké obnovenie pohľadu ako tlačidlo Fit view.
- Obnovenie pohľadu nemení posuny fotografie, exportnú snímku ani uloženú reláciu. Pravé ťahanie naďalej posúva iba viewport; ľavý dvojklik centruje fotografiu a zachová zoom.
- Aktualizované pravidlá a návody v EN/SK/CS s rozlíšením ľavého a pravého dvojkliku.

### Overenie

- **40 cielených testov prešlo** (5,73 s): zhoda pravého dvojkliku s Fit view pri 100/250/1000 %, správne ukončenie gesta, kvapkadlo, nezmenené offsety, exportná snímka a presné bajty relácie. Ruff, syntax a IDE diagnostika zmenených súborov bez chýb.
- Nový Windows one-file EXE zostavený. Source aj zabalený smoke **16/16 kontrol**, vrátane pravého dvojkliku a piatich reálnych HDR vzoriek. Celá sada a 84 MP test sa pri zmene kamery neopakovali; ich predchádzajúce výsledky sú zachované pri 0.6.0.

## 0.6.0 — 2026-11-11

### Zmenené

- Adaptívny náhľad načítava aktívny originál na pozadí už pri 100 % pohľade. Malý náhľad do 2048 px zostáva na prvé zobrazenie a ako pamäťový fallback.
- Detail z originálu zodpovedá fyzickým pixelom viewportu vrátane DPR/škálovania Windows, bez pevného 2048 px stropu detailu.
- Dostupné natívne popredie sa okamžite posúva s fotografiou. Kvalitný viditeľný výrez sa priebežne aktualizuje aj pri manipulácii a zmene nastavení, bez čakania na ukončenie gesta.
- Jeden natívny zdroj, render iba viditeľnej oblasti a najviac jedna bežiaca plus jedna najnovšia čakajúca požiadavka. Pamäťový rozpočet zahŕňa cieľový raster a obmedzený náhľad vysvetlí príčinu.
- Najviac dve menšie úrovne rozlíšenia zrýchľujú oddialený pohľad; natívny zoom používa originál. Zlyhanie voliteľnej cache umožní priamy render. Obnovenie základného preview nezahodí dostupný detail a oneskorený stav nesmie označiť novší viewport za úplne načítaný.
- Hlavička náhľadu používa preložený popis Adaptive preview namiesto neaktuálneho limitu 2048 px.
- Aktualizované pravidlá, technické rozhodnutia a používateľské návody v EN/SK/CS. Export naďalej vychádza z originálu a náhľad zostáva SDR.

### Overenie

- Kompletná sada **508 passed, 1 skipped** (55,07 s). Regresie pokrývajú detail pri fit 100 %, DPR, priebežný pohyb, reuse natívneho popredia, zmeny fotografie, LOD, pamäťový fallback a oneskorené stavové správy.
- Osobitne zapnutý reálny **84 MP test: 1 passed** (23,19 s): 4K fit 3840 × 1280 px, výrez z rovnakého natívneho zdroja a export 147 MP plátna.
- Source aj finálny Windows EXE **0.6.0: 16/16 smoke kontrol, exit 0**, vrátane piatich reálnych HDR vzoriek. Ruff, syntax a IDE diagnostika zmeneného kódu bez chýb.
- Syntetický 24 MP benchmark na jednom stroji: medián zahriateho fit renderu 1200 × 800 px **300,193 → 42,970 ms** s LOD faktorom 4. Prvé načítanie s dekódovaním a vytvorením LOD **711,250 ms**; 4K a natívne výrezy zostali porovnateľné s priamym renderom. Nejde o garanciu snímkovej frekvencie GUI.
- Živé Qt GUI overenie: natívny raster široký 2650 px; všetkých 20 pravých posunov zachovalo detail aj presné bajty relácie. Finálny one-file EXE je v štandardnom priečinku dist.

## 0.5.2 — 2026-11-11

### Opravené a pridané

- Zlatý rez opäť používa φ. Odstránené samostatné 16 px písmo; tlačidlo aj tooltip používajú rovnaký štýl a veľkosť písma ako ostatné voľby kompozície.
- Pravé ťahanie myšou posúva iba viewport. Nastavenia zarovnania, exportný stav a relácia zostávajú bez zmeny; ľavé ťahanie naďalej posúva fotografiu.
- Posun ukončí iba uvoľnenie tlačidla, ktoré ho začalo. Pravý dvojklik necentruje fotografiu, kvapkadlo po pravom posune zostáva aktívne a kontextové menu neposúva udalosti rodičovi.

### Overenie

- **485 passed, 1 skipped**; Ruff, syntax a IDE diagnostika zmenených súborov bez chýb. Regresie pokrývajú pravý posun, súbeh tlačidiel, Escape, dvojklik, kvapkadlo a nezmenené exportné nastavenia/JSON.
- Skutočné tooltipy aj tlačidlá majú rovnaké písmo a výšku v EN/SK/CS a oboch témach. PySide6 MCP potvrdil φ, rovnakú výšku tlačidiel a pravý posun (70, 40) pri nezmenenom zarovnaní (0, 0).
- Source aj nový Windows one-file EXE **0.5.2: 16/16 smoke kontrol, exit 0**, vrátane pravého viewport posunu bez zápisu relácie, φ, HEIC a reálnych HDR vzoriek. Výstup je opäť v pôvodnom dist priečinku.

## 0.5.1 — 2026-11-11

### Opravené a zrýchlené

- Sekcia Kompozícia a poradie Žiadna / 2×2 / 3×3 / oko pre zlatý rez / X pre diagonály; kompatibilné uložené enumy, popisné tooltipy a dostupnosť.
- Zoomovanie späť na 100 % vycentruje celú scénu aj pri krajne posunutej fotografii. Počas ťahania ostáva kamera stabilná.
- Okamžité Qt prekreslenie aktuálnej fotografie a rámu pri myši, posuvníkoch a pomere. Samostatné pozadie bez starej fotografie, cache blur pozadia a rýchle identity/solid vetvy namiesto zbytočného bicubic prepočtu.
- Počty knižnice sa pri nezmenenom stave nepočítajú znovu. Každá snímka relácie sa naďalej uloží, ale sériovo mimo GUI; zatvorenie počká na zápisy a chyby sú viditeľné.
- Najviac jeden bežiaci a jeden najnovší čakajúci preview/detail job; staršie požiadavky sa nehromadia.
- Odstránený pevný 512 MiB strop detailu. Rozpočet závisí od dostupnej RAM a skutočného SDR/HDR decode; náhľad ukazuje natívny detail alebo dôvod fallbacku.
- ISO gain-map SDR báza sa číta priamo bez zbytočnej float HDR rekonštrukcie, pri zachovaní farebného profilu a orientácie.
- Build podporuje `--dist-dir` pre alternatívny cieľ. Verzia 0.5.1 je v samostatnom priečinku, pretože starší EXE Windows nepovolil prepísať.

### Overenie

- **471 passed, 1 skipped** v kompletnej sade; samostatný **84 MP test 1 passed** vrátane natívneho hi-res výrezu a exportu plátna 147 MP.
- Source aj Windows EXE 0.5.1: **16/16 smoke kontrol, exit 0**, vrátane jemného detailu z 4096 px originálu, centrovania, FIFO zápisov a piatich reálnych HDR vzoriek.
- Pri 1000 záznamoch s polovicou exportovaných klesol medián opakovanej obsluhy posunu z približne 81 ms na 0,7 ms. Blur kompozícia s cache z približne 683 ms na 99 ms; živý posun na worker nečaká. Ide o merania overeného stroja, nie garantované časy.
- Ruff, syntax a IDE diagnostika zmenených súborov bez chýb. PySide6 MCP vizuálne potvrdil poradie tlačidiel, monochromatické oko a Native detail.

## 0.5.0 — 2026-11-10

### Pridané

- Posun fotografie myšou, centrovanie dvojklikom, zoom náhľadu 100–1000 % a voliteľný detail z originálu v pamäťovom rozpočte.
- Mriežky žiadna, tretiny, zlatý rez, diagonály a stred; informácia o zachovanej ploche originálu.
- Pozadie blur, biela, čierna, kvapkadlo, vlastná RGB farba a päť odlišných dominantných farieb podľa CIELAB.
- Červený stav neúspešných fotografií, dôvod chyby v tooltipe, opakovanie/odstránenie neúspešných a súhrn exportu s otvorením priečinka.
- Nastavenia cieľa exportu, systémovej/svetlej/tmavej témy a EN/SK/CS jazyka; prvotné nastavenie s preskočením a posúvateľný pomocník z README_USER dokumentov.
- HDR jadro pre Ultra HDR JPEG, HEIC PQ/HLG a Apple/ISO gain mapy; SDR náhľady, spracovanie v lineárnom BT.2020 a výstupné prípony _HDR/_SDR.

### Opravené

- Chyba alebo zrušenie uprostred série odstráni všetky jej nové diely. Ďalšie fotografie môžu pokračovať; existujúce súbory sa nemenia.
- Zmazaný nakonfigurovaný exportný priečinok sa potichu nevytvára znova. Predvolený je Export vedľa dát aplikácie.
- Zmena mriežky nemení platnosť úspešného exportu. Chybové príznaky a nové nastavenia sa ukladajú v schéme 5.
- Obnova relácie a cache miss nemenia uloženú voľbu HDR/SDR. Dočasná chyba náhľadu nevymaže predchádzajúce zlyhanie exportu.
- Skip obnovuje skutočné predvoľby aj pri uloženom nedokončenom nastavení. Zmena jazyka preloží aj už zobrazené chyby a tooltipy.
- HDR blur má pamäť podľa malého rastra, nezávislú od polomeru; Fill nevytvára nepotrebné pozadie.

### Prostredie

- Python minimálne 3.12 kvôli natívnej knižnici imagecodecs; pridané NumPy a imagecodecs s libultrahdr/Little CMS.
- Aktualizované requirements-lock a uv.lock pre overenú konfiguráciu.

### Overenie

- Kompletný pytest: **429 passed, 1 skipped**; osobitne aktivovaný reálny **84 MP test: 1 passed**, s plátnom 147 MP. Ruff a syntax bez chýb.
- Source aj finálny Windows one-file EXE 0.5.0: **16/16 smoke kontrol, exit 0**. Skutočné Apple HDR JPEG, Apple HEIC a Samsung ISO HEIC prešli importom, HDR exportom a opätovným dekódovaním.
- Frozen smoke overil natívne Ultra HDR/CMS/HEIF kodeky, SDR export, prípony, rollback neúplnej série a tri pribalené návody.
- PySide6 MCP vizuálne overil onboarding, light/dark, stavy knižnice, zoom, mriežku, súhrn exportu a posúvateľnú pomoc. Finálny EXE približne **73,4 MiB**, overený na Windows 11 x64.
- Osobný TODO zostal nezmenený. Projekt sa nepublikoval a nebola zvolená licencia ani platobný model.

## 0.4.1 — 2026-11-10

### Opravené

- Exportovať všetky aj Exportovať vybrané preskakujú fotografie v stave Importované. Exportovať sa smú iba pripravené a už exportované položky.
- Jeden spoločný filter oprávnenosti riadi tlačidlá, menu, dialógy aj priame spustenie dávky. Samotný checkbox importovanej fotografie export nepovolí.
- Bez oprávnených kandidátov sa neotvorí dialóg, nevytvorí cieľový priečinok a nezmení uložená exportná cesta.

### Overenie

- Celá sada: 267 úspešných testov, jeden opt-in veľký test preskočený. Ruff, syntax a IDE diagnostika bez chýb.
- Zdroj aj Windows one-file EXE 0.4.1: 7/7 kontrol. Overené blokovanie oboch exportov pri čisto importovanej knižnici, preskočenie dvoch modrých položiek v zmiešanej dávke a opakovaný export zelených.

## 0.4.0 — 2026-11-10

### Pridané

- Exportovať vybrané: tlačidlo aj položka menu exportujú iba fotografie označené checkboxom v momente spustenia.
- Samostatný modrý stav Importované; žlté Pripravené až po úspešnom otvorení vybratej fotografie v náhľade. Zelené Exportované zostáva samostatným úspešným exportným stavom.
- Perzistentný príznak zobrazenia previewed a JSON schéma 4 s migráciou starších schém a zálohou pôvodného JSON.

### Opravené

- Import už automaticky nevyberá prvú fotografiu. Checkboxy, miniatúry ani neúspešné/zastarané náhľady nenastavia pripravenosť.
- Prázdny výber zostáva prázdny aj po obnove relácie a po odstránení aktívnej fotografie.

### Overenie

- Celá sada: 262 úspešných testov, jeden opt-in veľký test preskočený. Ruff, syntax a IDE diagnostika bez chýb.
- Zdroj aj Windows one-file EXE 0.4.0: 7/7 kontrol, vrátane HEIC, modrého importu bez výberu, pripravenosti jedinej otvorenej fotografie a exportu iba označenej položky.
- Vizuálne overený modrý/žltý/zelený zoznam a nové tlačidlo Exportovať vybrané cez PySide6 MCP.

## 0.3.0 — 2026-11-10

### Pridané

- Checkboxy nezávislé od aktívneho náhľadu, červený smetný kôš na každom riadku a štyri hromadné akcie v ľavom paneli.
- Žlté rozpracované a zelené exportované riadky s príslušným farebným hoverom; maľovaný Qt delegát bez samostatných widgetov pre každý riadok.
- Stav úplne dokončeného exportu podľa snímky nastavení. Následná úprava ho zneplatní; chyba, prerušený export ani staršia snímka počas úpravy ho nenastavia nesprávne.
- JSON schéma 3: ukladanie checkboxov a exportných snímok, migrácia schém 1/2 so zachovaním pôvodných bajtov.

### Zmenené

- Režim fotografie sa vyberá dvoma tlačidlami; presné popisy prispôsobenia sú Fit / Padding a Fill / Crop.
- Predvolené Fill / Crop pre nový Carousel / Split, Fit / Padding pre doplnenie okrajov. Existujúce uložené nastavenia sa nemenia.
- Aplikácia sa otvára maximalizovaná.

### Opravené

- Vyprázdnenie knižnice počas importu ignoruje jeho neskoré výsledky; opätovný import rovnakej cesty sa nezamieňa so zrušenou požiadavkou.
- Neskorá chyba dekódovania odstránenej fotografie sa nezobrazí ako chyba aktuálnej knižnice.
- Fotografia odstránená a znovu importovaná počas exportu nepreberie stav starého záznamu.

### Overenie

- Celá sada: 234 úspešných testov, jeden opt-in veľký test preskočený. Ruff, syntax a IDE diagnostika bez chýb.
- Zdroj aj Windows one-file EXE 0.3.0: 7/7 diagnostických kontrol, vrátane HEIC, maximalizácie, checkboxov a uložených úspešných exportných stavov.
- PySide6 MCP vizuálne overil zmiešané žlté/zelené riadky, príslušný hover, koše a nové prepínače.

## 0.2.0 — 2026-11-10

### Zmenené

- Natívny export bez nastavenia šírky dielu: Fit/Padding doplní plátno a Fill/Crop vyreže zvolenú oblasť pri zachovaní pôvodnej mierky pixelov fotografie.
- Priamy rozsah pomeru strán 16:9 až 3:4, predvoľby tlačidlami vedľa seba; odstránený prepínač portrait/landscape.
- Horizontálny a vertikálny posun fotografie, spoločná geometria náhľadu a exportu.
- Spracovanie veľkých obrázkov bez pevného 80 MP limitu, export postupne po dieloch a kontrola dostupnej pamäte.
- JSON schéma 2 s migráciou starých nastavení a zachovaním pôvodného JSON pred prvým zápisom.

### Opravené

- Odstránenie neaktuálnej červenej chyby po úspešnom novom náhľade bez vymazania nesúvisiacich chýb.
- Kontrola RAM pre PNG prebehne pred čítaním metadát, ktoré môže samo vyvolať úplné dekódovanie.

### Overenie

- 179 regresných testov prešlo; samostatný reálny 84 MP JPEG test prešiel s náhľadom a exportom troch 7000 × 7000 px dielov zo 147 MP spoločného plátna.
- Ruff, syntax a IDE diagnostika bez chýb; source aj nové Windows one-file EXE 0.2.0 dokončili 7/7 smoke kontrol vrátane HEIC a natívneho Fit/Fill.
- Fit/Fill, posuny a tlačidlá pomerov vizuálne skontrolované cez PySide6 MCP; neaktuálna preview chyba sa vymaže a nesúvisiace chyby zostanú zachované.

## 0.1.0 — 2026-11-09

### Pridané

- Počiatočné pravidlá AI agentov podľa dodanej šablóny a implementačný plán.
- Výskum PySide6, Pillow, HEIC, Instagram pomerov a Windows balenia.
- Projektová konfigurácia Pythonu, závislosti, vstupný bod a Python skript pre one-file Windows build.
- Verzovaná relácia v JSON s atómovým zápisom a zachovaním poškodeného súboru.
- Obrazové jadro s delením spoločného plátna, rozšírením bez orezania, blur 0–1000 px, EXIF orientáciou a sRGB konverziou.
- Trojpanelové PySide6 rozhranie, drag & drop, individuálne nastavenia, náhľady do 2048 px a hromadný zrušiteľný export JPEG 99.
- Predvoľby a plynulý pomer strán, automatický pomer pre splitter a upozornenie na pomery mimo Instagram rozsahu.
- VS Code úlohy pre spustenie, testy a Windows build; presné verzie v requirements-lock.txt.
- Prvý úspešný Windows one-file build; začaté automatické testy až po jeho dokončení.
- 114 automatických testov: 88 obrazové jadro, 17 ukladanie relácie a 9 GUI.
- Izolovaný diagnostický režim zdroja aj zabaleného EXE so siedmimi kontrolami kodekov, exportu, stavu a Windows Qt GUI; oba režimy úspešne overené.
- Používateľská a vývojárska dokumentácia README, osobný TODO so zákazom automatického vykonávania a dokončený implementačný plán.

### Opravené

- Bezpečné publikovanie exportov bez prepisov aj na Windows FAT/exFAT.
- Zhodné limity relácie pri zápise aj čítaní; zachytenie príliš vnoreného poškodeného JSON.
- Zaokrúhľovanie rozmerov exportu pri hraniciach 3:4 a 1,91:1 tak, aby podporovaný pomer zostal v rozsahu aj v celých pixeloch.
- Viditeľné šípky ovládacích prvkov a čitateľný výber v tmavom GUI; presné rozmery a upozornenie pri prekročení limitu plátna.
