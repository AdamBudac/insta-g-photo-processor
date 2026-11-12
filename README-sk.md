# Insta G Photo Processor

**Verzia 1.0.0** · Desktopová aplikácia pre Windows · Python / PySide6

[English](./README.md) · [Slovenčina](./README-sk.md) · [Čeština](./README-cz.md)

Pripravte fotografie pre Instagram priamo vo svojom počítači. Aplikácia nedestruktívne oreže záber, rozdelí panorámu na nadväzujúce diely carouselu alebo doplní portrét rozmazaným či farebným pozadím. Pri exporte zachováva pôvodnú mierku pixelov popredia a nevyžaduje účet, cloud ani pripojenie k Instagramu.

**Chcete iba používať EXE?** Otvorte používateľský návod: [English](./README-user.md), [slovenčina](./README-user-sk.md), [čeština](./README-user-cz.md). Z časti Assets vo vydaniach Releases tohto repozitára stiahnite `InstaGPhotoProcessor.exe`. Python aj HEIC kodeky sú pribalené. Rovnaké návody nájdete v posúvateľnom pomocníkovi aplikácie aj na [prezentačnom webe](./index.html).

## Funkcie

- **Carousel / Rozdelenie:** 2–20 nadväzujúcich dielov zľava doprava, pomery od 3:4 do 16:9 a automatický pomer.
- **Doplniť plátno:** jedna fotografia s okrajmi, rozmazaným pozadím alebo plnou RGB farbou. Pri výbere pomáha kvapkadlo a najviac päť odlišných dominantných farieb.
- **Priame úchyty výrezu:** ťahajte hrany a rohy fotografie. Celý originál zostáva viditeľný s tmavým prekrytím; odrezané časti vrátite ťahaním von alebo tlačidlom Reset crop.
- **Fit / Padding a Fill / Crop:** Fit zachová celý zvolený vstup, Fill výslovne povoľuje ďalšie orezanie. Ani jeden režim nemení mierku pixelov popredia.
- **Responzívny náhľad:** zoom, posúvanie, kompozičné čiary a detail z originálu prispôsobený viditeľnému viewportu a škálovaniu displeja.
- **Hromadné spracovanie:** nezávislé checkboxy, nastavenia pre každú fotografiu, stavy importované/pripravené/exportované/zlyhané, zrušiteľný export a súhrn výsledkov.
- **Vstupy JPEG, PNG a HEIC/HEIF**, vrátane podporovaných HDR zdrojov. Náhľad je vždy SDR; kompatibilný HDR vstup možno zachovať v HDR alebo previesť na SDR.
- **Angličtina, slovenčina a čeština**, vzhľad System, Light a Dark. Spracovanie aj uložené údaje zostávajú lokálne.

## Požiadavky a závislosti

Zabalená aplikácia je určená pre **Windows x64**. Overené prostredie je **Windows 11 x64 s Pythonom 3.13**; Windows 10 ani čistá virtuálna inštalácia neboli samostatne overené. Vývoj zo zdrojov vyžaduje **Python 3.12+** a virtuálne prostredie projektu.

| Balík | Deklarovaný rozsah | Účel |
| --- | --- | --- |
| PySide6 | `>=6.8,<7` | Desktopové rozhranie Qt |
| Pillow | `>=11,<13` | Spracovanie SDR a JPEG/PNG |
| pillow-heif | `>=1,<2` | Podpora HEIC/HEIF |
| NumPy | `>=2.2,<3` | Pixelové polia a HDR |
| imagecodecs | `>=2026.10.10` | HDR JPEG a farebné kodeky |
| PyInstaller | `>=6.11,<7` | Windows one-file build; vývojová závislosť |
| pytest / pytest-qt / Ruff | Pozri konfiguráciu projektu | Testy a lint; vývojové závislosti |

Závislosti sú v [pyproject.toml](./pyproject.toml) a [requirements.txt](./requirements.txt); [requirements-dev.txt](./requirements-dev.txt) pridáva vývojové nástroje. [requirements-lock.txt](./requirements-lock.txt) zaznamenáva presné overené prostredie a [uv.lock](./uv.lock) slúži pre uv. Dostupnosť natívnych kodekov môže obmedziť verzie Pythonu s použiteľnými wheels.

## Inštalácia a spustenie zo zdrojov

Naklonujte repozitár, otvorte PowerShell v jeho koreňovom priečinku a spustite:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe run_app.py --data-dir .dev-data
```

Explicitný dátový priečinok oddelí vývoj od bežnej uloženej relácie. Bez `--data-dir` sa používa skutočný Windows Documents. Na príkazovom riadku možno odovzdať aj cesty fotografií. Nainštalovaný vstupný príkaz je `insta-g-photo-processor`; Python modul zostáva `insta_g`.

Vo VS Code otvorte [insta-g-photo-processor.code-workspace](./insta-g-photo-processor.code-workspace) s nastaveným interpreterom a [úlohami](./.vscode/tasks.json) Run application, Run tests a Build Windows EXE.

## Testovanie a lint

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check insta_g scripts tests run_app.py
.\.venv\Scripts\python.exe run_app.py --smoke-test .test-artifacts/source-smoke.json
```

Testy používajú generované obrázky, dočasné priečinky, reálny HEIC encoder/dekóder a licencovanú malú HDR fixture. Nemenia osobné fotografie ani bežnú reláciu v Documents. Súbežné samostatné procesy pytest musia mať rozdielny `--basetemp`.

Voliteľný test veľkých obrázkov je predvolene vypnutý:

```powershell
$env:INSTA_G_TEST_LARGE = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_large_images.py -q
Remove-Item Env:INSTA_G_TEST_LARGE
```

Smoke test zapíše JSON a screenshot bez otvorenia bežného uloženého stavu. Úspech vyžaduje exit 0 a `"ok": true`. Voliteľný `--smoke-hdr-dir` overí ďalšie HDR vzorky iba na čítanie.

## Zostavenie Windows EXE

Build spustite **na Windows** a najprv zatvorte staršiu kópiu cieľového EXE:

```powershell
.\.venv\Scripts\python.exe scripts/build.py
Start-Process -FilePath .\dist\InstaGPhotoProcessor.exe -ArgumentList '--smoke-test','.test-artifacts/frozen-smoke.json' -WindowStyle Hidden -Wait
```

[scripts/build.py](./scripts/build.py) vytvorí `dist/InstaGPhotoProcessor.exe` s Qt platform pluginom, natívnymi HEIF DLL, HDR/farebnými kodekmi a všetkými tromi návodmi. `--console` zapne ladiacu konzolu; `--dist-dir` určí iný cieľový priečinok. Zabalený smoke musí obsahovať aj `"frozen": true`; samotný úspešný build nedokazuje funkčný import HEIC. Bitovo identické buildy sa negarantujú.

## Údaje a bezpečné spracovanie

Nová inštalácia ukladá `session.json` a `preferences.json` do `<skutočný Windows Documents>/insta-g-photo-processor/`. Predvolený podpriečinok `Export` vzniká iba pri prvotnom nastavení. Vymazaný nastavený cieľ treba znovu vybrať v nastaveniach.

Každá fotografia má vlastné nastavenia. Relácia schémy 6 obsahuje výrez, pripravenosť, exportnú snímku a cesty, nie kópie fotografií. Zápisy prebiehajú sériovo mimo GUI a používajú atómovú náhradu; zatvorenie počká na dopísanie. Chyby sa zobrazia. Schémy 1–5 sa migrujú so zálohou pôvodných bajtov a poškodený stav sa pred obnovou zachová.

Ak v novom dátovom priečinku nie je ani jeden stavový súbor a pôvodný `insta-g-image-resizer` aspoň jeden má, aplikácia naďalej používa pôvodný priečinok bez presúvania. Existujúci nový stav má prednosť; explicitné `--data-dir` tento fallback vypína. Exportný cieľ sa zachová.

Vstupy sa nikdy neprepisujú. Pri kolízii exportu vznikne voľný názov. Chyba alebo zrušenie odstráni iba nové súbory nedokončenej série danej fotografie; hotové série zostanú. Odstránenie z knižnice nemaže diskové súbory. Oba exporty preskočia modré Importované, kým sa úspešne nezobrazí ich aktuálny náhľad.

## Správanie a limity obrázkov

- Export zachováva popredie v **mierke 1:1**. Fit pridáva plátno, Fill vyrezáva. Používateľský resize nie je dostupný. Zaokrúhľovanie môže upraviť plátno alebo výrez o niekoľko pixelov.
- Súradnice výrezu patria správne orientovanému originálu. Výrez je vstupom pre geometriu, polohu aj vzorkovanie pozadia. Zachovaný podiel sa počíta voči **celému originálu**, vrátane vstupného výrezu aj Fill orezania.
- SDR export je **sRGB JPEG s kvalitou 99**, bez pôvodných EXIF/GPS metadát. Kvalita 99 je nastavenie kodeku, nie percento zachovaných dát. Priehľadnosť PNG sa skladá na podklad a EXIF orientácia sa rešpektuje.
- HDR podpora zahŕňa platné Ultra HDR/Apple HDR JPEG gain mapy, podporované Apple/ISO HEIC gain mapy a 10/12-bit PQ/HLG HEIC so známymi farebnými metadátami. Nepodporované či poškodené HDR sa výslovne odmietne. Náhľad je vždy SDR.
- HDR→SDR používa `_SDR`, zachované HDR `_HDR`. HDR JPEG obsahuje ISO gain mapu; HDR HEIC používa 10-bit PQ/BT.2020. Pôvodná reprezentácia HDR sa pri opätovnom kódovaní môže zmeniť.
- **Pevný limit 80 MP neplatí.** Export renderuje po dieloch a kontroluje dostupnú RAM. SDR JPEG dovoľuje najviac **65 500 px na hranu dielu**, pribalený HDR JPEG kodek **8192 px na hranu**.
- Rýchly náhľad má najviac **2048 px** na dlhšej hrane. Natívny detail sa riadi fyzickým viewportom vrátane DPR a rozpočtom 40 % práve dostupnej RAM. Aplikácia vysvetlí použitie iba zmenšeného náhľadu.
- Blur pozadie môže používať zmenšený raster. Instagram môže súbory zmenšiť či rekomprimovať a meniť podporované pomery. Aplikácia nič nenahráva a nesľubuje rovnaký vzhľad na každom HDR zariadení.

Podrobné farebné rozhodnutia, podmienky meraní a zdroje sú v [technickom výskume](./docs/RESEARCH.md).

## Generované súbory a čistenie

Ignorované `.pytest_cache/` a `.pytest-tmp*/` možno po ukončení testov zmazať; pytest ich vytvorí znova. `.dev-data/` je samostatná relácia vývojovej spúšťacej úlohy: jej zmazanie resetuje tento vývojový stav. `.test-artifacts/` obsahuje historické reporty, screenshoty, benchmarky a voliteľné externé HDR vzorky; možno ho odstrániť, keď tieto súbory už nepotrebujete. Bežné testy používajú vlastné dočasné dáta a verzovanú [HDR vzorku](./tests/fixtures/hdr/). Na chod zabaleného EXE tieto priečinky netreba.

`insta_g/` je Python balík v aktuálnom flat rozložení. Prípadné src rozloženie by používalo `src/insta_g/` a zachovalo názov balíka aj importy.

## Štruktúra projektu a web

| Umiestnenie | Zodpovednosť |
| --- | --- |
| [insta_g/core/](./insta_g/core/) | Modely, geometria, kodeky, spracovanie a export bez GUI |
| [insta_g/gui/](./insta_g/gui/) | Hlavné okno, widgety a workery |
| [persistence.py](./insta_g/persistence.py), [preferences.py](./insta_g/preferences.py) | Verziovaná relácia a globálne nastavenia |
| [i18n.py](./insta_g/i18n.py) | Preklady aplikácie |
| [index.html](./index.html), [docs/assets/](./docs/assets/) | Statický prezentačný web bez buildu |
| [README-user.md](./README-user.md), [README-user-sk.md](./README-user-sk.md), [README-user-cz.md](./README-user-cz.md) | Spoločné zdrojové návody aplikácie aj webu |

Web prepína EN/SK/CS okamžite cez JavaScript bez reloadu, podporuje systémový/svetlý/tmavý vzhľad a načítava zvolený návod priamo z týchto Markdown súborov. Samostatné PDF netreba udržiavať. [Nastavenie GitHub Pages a lokálny náhľad](./docs/GITHUB_PAGES.md) vysvetľuje publikovanie z koreňa repozitára aj konfiguráciu GitHub/download odkazov.

## Stav, prispievanie a licencia

Overenie webu a dokumentácie, dokončené 12. novembra 2026: aplikačná sada **651 passed, 1 skipped**; **14 browser scenárov prešlo**, vrátane okamžitého prepínania jazykov, spoločných návodov, tém, klávesnice a responzívneho rozloženia od 320 do 1440 px. Source aj nový Windows EXE prešli **13/13 smoke kontrolami**. Voliteľný 84 MP test sa pri tejto dodávke neopakoval. Podrobné dôkazy a hranice overenia sú v [implementačnom pláne](./docs/IMPLEMENTATION_PLAN.md), dodané zmeny v [changelogu](./CHANGELOG.md).

Pri hlásení chyby uveďte verziu aplikácie a Windows, kroky, očakávané správanie a zobrazenú chybu. Použite generované alebo zdieľateľné vzorky. Pravidlá automatizácie prispievateľov sú v [AGENTS.md](./AGENTS.md). Projekt je určený na verejný open-source vývoj; konkrétna licencia zatiaľ nebola zvolená a repozitár aktuálne neposkytuje dodatočné licenčné oprávnenie.
