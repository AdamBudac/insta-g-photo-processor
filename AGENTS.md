# Inštrukcie pre AI agentov

Projekt **Insta G Photo Processor** je lokálna desktopová aplikácia pre Windows v Pythone, s GUI PySide6, spracovaním cez Pillow/pillow-heif, NumPy/imagecodecs pre HDR a one-file EXE cez PyInstaller. Komunikácia a vývojová dokumentácia sú v slovenčine. GUI a návod podporujú angličtinu (predvolená), slovenčinu a češtinu. Python modul `insta_g` zostáva zachovaný; distribúcia sa volá `insta-g-photo-processor` a Windows balík `InstaGPhotoProcessor.exe`.

## 1. Osobné poznámky používateľa

- `TODO.md` obsahuje výhradne osobné poznámky používateľa, nie úlohy pre agenta.
- **Agent nesmie implementovať obsah `TODO.md` bez výslovnej osobnej požiadavky používateľa.**
- Čítanie na pochopenie kontextu je povolené. Úpravy poznámok sú povolené iba na konkrétnu požiadavku používateľa. Prvotné vytvorenie dokumentu bolo autorizované pri založení projektu.
- Realizačné úlohy patria do `docs/IMPLEMENTATION_PLAN.md`, nie do `TODO.md`.

## 2. Git a používateľské dáta

- Bez výslovného pokynu nevykonávaj `git commit`, `push`, `rebase` ani publikovanie.
- Nikdy neprepisuj vstupné fotografie. Exporty nesmú bez upozornenia prepísať existujúce súbory.
- Testy používajú dočasné adresáre a generované obrázky; nesmú meniť používateľské nastavenia ani osobné fotografie.
- Projekt nevyžaduje účet, cloud, telemetriu ani pripojenie k Instagramu.

## 3. Architektúra a kvalita

- `insta_g/core/`: dátové modely, geometria, kodeky, bezstavové spracovanie a export. Bez závislosti na GUI či `QApplication`.
- `insta_g/persistence.py`: verzovaný JSON stav, validácia a atómové zápisy.
- `insta_g/gui/`: hlavné okno, samostatné widgety a workery. Widgety sa menia výhradne v hlavnom Qt vlákne.
- `insta_g/app.py`: vstupný bod a inicializácia; `scripts/build.py`: reprodukovateľný Windows build.
- Dodržiavaj KISS, DRY, jasné názvy, typové anotácie a malé moduly. Nezavádzaj špekulatívne frameworky ani kruhové importy.
- Dlhé dekódovanie, preview, import a export patria do workerov. Počas exportu musí byť GUI responzívne a export zrušiteľný.
- Rýchly základ náhľadu má maximálne 2048 px na dlhšej hrane a slúži aj ako fallback. Kvalitný výrez z originálu sa prispôsobuje fyzickému rozlíšeniu viewportu vrátane device pixel ratio, bez pevného 2048 px stropu. Export vždy vychádza z originálu.
- Každá fotografia má vlastné nastavenia. Každá ich zmena sa uloží do pamäte a do `Documents/insta-g-photo-processor/session.json` cez skutočný Windows priečinok Documents (`QStandardPaths`). Ak nový priečinok nemá session.json ani preferences.json a pôvodný `insta-g-image-resizer` aspoň jeden má, používaj pôvodný priečinok bez presúvania dát. Existujúci nový stav má prednosť; explicitné `--data-dir` nepoužíva fallback. Uložený exportný cieľ zachovaj.
- Diskový zápis každej snímky relácie prebieha sériovo mimo GUI. Revízie sa nevynechávajú; zatvorenie počká na dopísanie a chybu posledného zápisu nesmie potichu skryť.
- Vstupný výrez je samostatný nedestruktívny krok pred split/expand. Settings.crop_box je None pre celý originál alebo štvorica celočíselných súradníc (left, top, right, bottom) v správne orientovaných pôvodných pixeloch; pravý a dolný okraj sú výlučné. Výrez musí ležať v origináli a mať aspoň 1 × 1 px, môže mať ľubovoľný pomer a nikdy nemení mierku pixelov. Neplatný uložený výrez neorezávaj ani nezahadzuj potichu.
- Výrez sa ovláda priamo v strednom náhľade úchytmi na hranách a rohoch fotografie, bez samostatného dialógu a číselných polí X/Y/šírka/výška. Počas ťahania zachovaj stabilnú kameru a mapovanie pôvodných pixelov; zmeny sa priebežne ukladajú a zneplatnia exportnú snímku. Escape vráti výrez zo začiatku gesta. Po uvoľnení obnov Fit view s celým pôvodným originálom aj plátnom, nie priblíženie iba na vstupný výrez. Odrezané časti zostávajú viditeľné s tmavým prekrytím aj mimo gesta; hrany možno jedným ťahom rozšíriť späť po pôvodné okraje. Reset crop pod Center image v pravom paneli nastaví crop_box=None a obnoví Fit view.
- Zdieľané výpočty geometrie musia riadiť náhľad aj export. Pomer, split/expand, pozadie a posuny pracujú so vstupným výrezom, prípadne celým originálom pri crop_box=None. Fit/Padding zachová celý tento vstup a pridá pozadie; Fill/Crop smie vykonať ďalšie výslovne zvolené orezanie. Pozadie vzorkuj iba z výrezu. Retained percentage počítaj ako viditeľnú plochu popredia voči celému pôvodnému originálu, vrátane vstupného cropu aj Fill orezania.
- Export zachováva pôvodnú mierku pixelov fotografie (1:1), bez používateľského nastavenia resize. Fit zväčšuje plátno, Fill vyrezáva oblasť; nemenia rozlíšenie popredia interpoláciou. Pomery sa zadávajú priamo od 16:9 po 3:4 bez prepínača orientácie.
- Ľavé tlačidlo myši posúva fotografiu; ľavý dvojklik centruje fotografiu vynulovaním jej posunov a zachová zoom. Zoom 100–1000 % je relatívny k zmesteniu do viewportu; nemení export. Návrat na 100 % vycentruje celý pôvodný originál aj plátno vrátane stmavených odrezaných častí. Počas posúvania sa okamžite kreslí aktuálna geometria nad cache vrátane dostupného natívneho popredia; kvalitný viditeľný výrez sa žiada aj počas manipulácie a zmien nastavení, nie až po ich skončení. Najviac jeden aktívny job a jedna najnovšia čakajúca požiadavka v každej preview/detail pipeline.
- Pravé tlačidlo myši posúva iba viewport rovnako ako stredné alebo Space+ľavé. Pravý dvojklik obnoví pohľad cez rovnaké reset_view ako Fit view: zoom 100 %, bez posunu kamery, s celým pôvodným originálom aj plátnom v zábere. Pravý posun ani pravý dvojklik nesmú meniť zarovnanie fotografie, nastavenia, exportný stav ani zapisovať reláciu. Kontextové menu nesmie odoberať udalosti posunu.
- Aktívny originál pre SDR zobrazenie načítaj vo workerovi už pri základnom 100 % pohľade, ak dovolí pamäťový rozpočet (40 % aktuálne dostupnej RAM), bez pevného 512 MiB/pixelového stropu. Odhad odlišuje priamu SDR bázu gain mapy od float PQ/HLG konverzie a zahŕňa výstupný raster. Uchovávaj najviac jeden natívny zdroj; renderuj iba viditeľný výrez podľa fyzických pixelov viewportu, nevytváraj celé natívne rozšírené plátno. Nedostatok pamäte alebo chybu detailu vysvetli v náhľade; nesmie ticho predstierať natívny detail.
- Sekcia Kompozícia obsahuje päť volieb v poradí Žiadna, 2×2, 3×3, φ (zlatý rez), X (diagonály). Všetky tlačidlá aj tooltipy používajú spoločné písmo a štýl. Interné enumy none/center/thirds/golden/diagonal zachovaj pre kompatibilitu relácie. Ide iba o prekrytie náhľadu každého dielu vrátane paddingu; voľba nesmie zneplatniť zelený exportný stav.
- Pozadie podporuje blur a plnú RGB farbu, kvapkadlo z SDR náhľadu a najviac päť perceptuálne odlišných dominantných farieb.
- Nepoužívaj pevný limit 80 MP. Export renderuj postupne po dieloch; rýchly základ náhľadu zostáva do 2048 px, detail sa riadi viewportom a dostupnou RAM. Kontroluj odhad potrebnej RAM voči dostupnej pamäti a skutočný limit rozmerov JPEG; chyby vysvetli používateľovi.
- Neaktuálna chyba náhľadu sa po úspešnom novom náhľade odstráni. Nesmie pritom zmiznúť nesúvisiaca chyba importu, exportu alebo ukladania.
- Nové fotografie v režime Carousel / Split začínajú s Fill / Crop podľa výslovného zadania používateľa; doplnenie okrajov vždy používa Fit / Padding. Obnovené nastavenia existujúcich fotografií zachovaj.
- Checkboxy hromadných akcií sú nezávislé od aktívnej fotografie náhľadu. Odstránenie z knižnice nikdy nemaže vstup ani export na disku.
- Nové importy zostávajú modré a bez automatického výberu. Žltý stav Pripravené sa nastaví iba po úspešnom zobrazení aktuálne vybratej fotografie v náhľade; miniatúra, checkbox, neúspešný alebo zastaraný náhľad ho nenastavia. Informáciu o zobrazení ukladaj do relácie.
- Úplne exportované fotografie majú zelené pozadie. Všetky tri stavy zachovávajú vlastnú farbu pri hoveri. Zelený stav platí pre úplný úspešný export aktuálnych nastavení; následná úprava ho zneplatní. Označenie checkboxom ani samotný výber fotografie ho nemenia.
- Obe voľby exportu smú spracovať iba stavy Pripravené a Exportované. Stav Importované sa vždy preskočí, aj keď je označený checkboxom. Exportovať vybrané používa snímku oprávnených označených fotografií pri spustení; Exportovať všetky používa všetky oprávnené položky knižnice. Aktívna fotografia náhľadu neurčuje rozsah exportu.
- Neúspešné fotografie sú červené s dôvodom v tooltipe a stavovom riadku. Opakovanie neúspešných je samostatná akcia. Zlyhanie alebo zrušenie uprostred série odstráni iba nové súbory danej nedokončenej série; hotové série a staršie súbory zostanú. Po dávke zobraz súhrn originálov, výstupov a chýb s otvorením cieľového priečinka.
- SDR JPEG export: kvalita 99, RGB/sRGB, bez GPS/EXIF metadát; rešpektuj EXIF orientáciu pri importe. HDR nesmie byť iba označené 8-bitové SDR: dekóduj skutočnú prenosovú krivku/gain mapu a gamut, preview vždy SDR. Nepodporované HDR metadáta odmietni s vysvetlením. HDR výstup používa `_HDR`, konverzia HDR→SDR `_SDR` pred číslovaním; pôvodné SDR je bez prípony.
- Globálne nastavenia sú oddelené od relácie vo preferences.json: jazyk, téma system/light/dark a exportný priečinok. Prvý štart ponúkne nastavenie s preskočením na defaulty. Defaultný Export vedľa session sa vytvára iba pri prvotnom nastavení; neskôr chýbajúci cieľ neobnovuj potichu.
- Rozlišuj používateľom zvolený pomer a aktuálne limity Instagramu; nepodporované pomery označ, neupravuj ich bez vedomia používateľa.
- Relácia používa schému 6; schémy 1–5 sa migrujú so zálohou presných pôvodných bajtov. Chýbajúci crop_box znamená None a nesmie zneplatniť starší zelený exportný stav.
- Chyby importu, exportu aj ukladania zobraz používateľovi. Poškodený stav nesmie byť potichu zahodený ani prepísaný.

## 4. Výskum a MCP

- Pred zmenou externých API používaj oficiálnu dokumentáciu, podľa dostupnosti Context7.
- `pyside6` MCP je vhodný na spustenie, inšpekciu widgetov a screenshoty. Dostupnosť Serena, ffmpeg či iných serverov over; nepredpokladaj ju.
- Na statické fotografie postačuje Pillow; ffmpeg nepridávaj bez reálnej potreby.
- Runtime a testy sú dôkazom správania. Neoznačuj neoverené predpoklady ako úspešné overenie.

## 5. Overovanie a build

- Po zmenách over dotknutú funkcionalitu, syntax a diagnostiku; podľa potreby `pytest`, GUI inšpekciu a zabalené EXE.
- Pri geometrii over zachovanie celej plochy, nadväznosť splitov, zaokrúhľovanie, limit rýchleho preview a veľkosť natívneho detailu podľa viewportu/DPR. Over detail pri 100 %, manipulácii a nedostatku RAM aj odmietnutie zastaraných výsledkov.
- Over JPEG, PNG (vrátane priehľadnosti), skutočný HEIC, orientáciu, zlyhané vstupy, atómové ukladanie, obnovu stavu a kolízie exportných názvov.
- Windows EXE zostavuj na Windows. One-file balík musí obsahovať Qt platform plugin a natívne HEIF DLL. Úspešný build ešte nedokazuje funkčný import HEIC v EXE; spusti aj zabalený smoke test.
- Aktívny interpreter a prostredie najprv over. Závislosti drž v projektovom `.venv`.

## 6. Živá dokumentácia

- `README.md`, `README-sk.md`, `README-cz.md`: vývojárska prezentácia projektu v EN/SK/CS, závislosti, inštalácia, spustenie, testy a build; hlavný README je anglický.
- `README-user.md`, `README-user-sk.md`, `README-user-cz.md`: používateľské EXE návody pre laikov, načítavané pomocníkom aplikácie a priamo statickým webom; pribaliť aj do EXE. Obsah neduplikuj do druhých webových kópií ani PDF.
- `index.html`, `docs/assets/`: statická prezentačná stránka pre GitHub Pages publikovaná z koreňa repozitára. Jazyk EN/SK/CS sa prepína okamžite cez frontend i18next bez reloadu, vzhľad system/light/dark sa riadi preferenciou návštevníka. GitHub a publikovanie spravuje používateľ sám; postup je v `docs/GITHUB_PAGES.md`.
- `CHANGELOG.md`: **pri každej zmene** zaznamenaj príslušnú funkcionalitu, opravu alebo konfiguráciu s aktuálnym dátumom; súvisiace úpravy jednej dodávky môžu tvoriť jednu položku.
- `docs/IMPLEMENTATION_PLAN.md`: postup a reálny stav implementácie/overovania.
- `docs/RESEARCH.md`: zdroje, dátum overenia a podstatné technické rozhodnutia.
- `TODO.md`: výnimka z automatickej aktualizácie; platia pravidlá v časti 1.
