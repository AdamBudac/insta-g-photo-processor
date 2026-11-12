# Insta G Photo Processor

**Verze 1.0.0** · Desktopová aplikace pro Windows · Python / PySide6

[English](./README.md) · [Slovenčina](./README-sk.md) · [Čeština](./README-cz.md)

Připravte fotografie pro Instagram přímo ve svém počítači. Aplikace nedestruktivně ořízne záběr, rozdělí panorama na navazující díly carouselu nebo doplní portrét rozmazaným či barevným pozadím. Při exportu zachovává původní měřítko pixelů popředí a nevyžaduje účet, cloud ani připojení k Instagramu.

**Chcete pouze používat EXE?** Otevřete uživatelský návod: [English](./README-user.md), [Slovenčina](./README-user-sk.md), [Čeština](./README-user-cz.md). Z části Assets ve vydáních Releases tohoto repozitáře stáhněte `InstaGPhotoProcessor.exe`. Python i HEIC kodeky jsou přibalené. Stejné návody najdete v posouvatelné nápovědě aplikace i na [prezentačním webu](https://adambudac.github.io/insta-g-photo-processor/).

## Funkce

- **Carousel / Rozdělení:** 2–20 navazujících dílů zleva doprava, poměry od 3:4 do 16:9 a automatický poměr.
- **Doplnit plátno:** jedna fotografie s okraji, rozmazaným pozadím nebo plnou RGB barvou. S výběrem pomáhá kapátko a nejvýše pět odlišných dominantních barev.
- **Přímé úchyty výřezu:** táhněte hrany a rohy fotografie. Celý originál zůstává viditelný s tmavým překrytím; oříznuté části vrátíte tažením ven nebo tlačítkem Reset crop.
- **Fit / Padding a Fill / Crop:** Fit zachová celý zvolený vstup, Fill výslovně povoluje další oříznutí. Ani jeden režim nemění měřítko pixelů popředí.
- **Responzivní náhled:** zoom, posouvání, kompoziční čáry a detail z originálu přizpůsobený viditelnému viewportu a škálování displeje.
- **Hromadné zpracování:** nezávislé checkboxy, nastavení pro každou fotografii, stavy importováno/připraveno/exportováno/nezdařilo se, zrušitelný export a souhrn výsledků.
- **Vstupy JPEG, PNG a HEIC/HEIF**, včetně podporovaných HDR zdrojů. Náhled je vždy SDR; kompatibilní HDR vstup lze zachovat v HDR nebo převést na SDR.
- **Angličtina, slovenština a čeština**, vzhled System, Light a Dark. Zpracování i uložené údaje zůstávají místní.

## Požadavky a závislosti

Zabalená aplikace je určena pro **Windows x64**. Ověřené prostředí je **Windows 11 x64 s Pythonem 3.13**; Windows 10 ani čistá virtuální instalace nebyly samostatně ověřeny. Vývoj ze zdrojů vyžaduje **Python 3.12+** a virtuální prostředí projektu.

| Balíček | Deklarovaný rozsah | Účel |
| --- | --- | --- |
| PySide6 | `>=6.8,<7` | Desktopové rozhraní Qt |
| Pillow | `>=11,<13` | Zpracování SDR a JPEG/PNG |
| pillow-heif | `>=1,<2` | Podpora HEIC/HEIF |
| NumPy | `>=2.2,<3` | Pixelová pole a HDR |
| imagecodecs | `>=2026.10.10` | HDR JPEG a barevné kodeky |
| PyInstaller | `>=6.11,<7` | Windows one-file build; vývojová závislost |
| pytest / pytest-qt / Ruff | Viz konfigurace projektu | Testy a lint; vývojové závislosti |

Závislosti jsou v [pyproject.toml](./pyproject.toml) a [requirements.txt](./requirements.txt); [requirements-dev.txt](./requirements-dev.txt) přidává vývojové nástroje. [requirements-lock.txt](./requirements-lock.txt) zaznamenává přesné ověřené prostředí a [uv.lock](./uv.lock) slouží pro uv. Dostupnost nativních kodeků může omezit verze Pythonu s použitelnými wheels.

## Instalace a spuštění ze zdrojů

Naklonujte repozitář, otevřete PowerShell v jeho kořenové složce a spusťte:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe run_app.py --data-dir .dev-data
```

Explicitní datová složka oddělí vývoj od běžné uložené relace. Bez `--data-dir` se používá skutečný Windows Documents. Na příkazovém řádku lze předat také cesty fotografií. Nainstalovaný vstupní příkaz je `insta-g-photo-processor`; Python modul zůstává `insta_g`.

Ve VS Code otevřete [insta-g-photo-processor.code-workspace](./insta-g-photo-processor.code-workspace) s nastaveným interpretem a [úlohami](./.vscode/tasks.json) Run application, Run tests a Build Windows EXE.

## Testování a lint

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check insta_g scripts tests run_app.py
.\.venv\Scripts\python.exe run_app.py --smoke-test .test-artifacts/source-smoke.json
```

Testy používají generované obrázky, dočasné složky, skutečný HEIC encoder/dekóder a licencovanou malou HDR fixture. Nemění osobní fotografie ani běžnou relaci v Documents. Souběžné samostatné procesy pytest musí mít odlišný `--basetemp`.

Volitelný test velkých obrázků je ve výchozím nastavení vypnutý:

```powershell
$env:INSTA_G_TEST_LARGE = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_large_images.py -q
Remove-Item Env:INSTA_G_TEST_LARGE
```

Smoke test zapíše JSON a screenshot bez otevření běžného uloženého stavu. Úspěch vyžaduje exit 0 a `"ok": true`. Volitelný `--smoke-hdr-dir` ověří další HDR vzorky pouze pro čtení.

## Sestavení Windows EXE

Build spusťte **ve Windows** a nejprve zavřete starší kopii cílového EXE:

```powershell
.\.venv\Scripts\python.exe scripts/build.py
Start-Process -FilePath .\dist\InstaGPhotoProcessor.exe -ArgumentList '--smoke-test','.test-artifacts/frozen-smoke.json' -WindowStyle Hidden -Wait
```

[scripts/build.py](./scripts/build.py) vytvoří `dist/InstaGPhotoProcessor.exe` s Qt platform pluginem, nativními HEIF DLL, HDR/barevnými kodeky a všemi třemi návody. `--console` zapne ladicí konzoli; `--dist-dir` určí jinou cílovou složku. Zabalený smoke musí obsahovat také `"frozen": true`; samotný úspěšný build nedokazuje funkční import HEIC. Bitově shodné buildy se negarantují.

## Údaje a bezpečné zpracování

Nová instalace ukládá `session.json` a `preferences.json` do `<skutečný Windows Documents>/insta-g-photo-processor/`. Výchozí podsložka `Export` vzniká pouze při prvotním nastavení. Smazaný nastavený cíl je třeba znovu vybrat v nastavení.

Každá fotografie má vlastní nastavení. Relace schématu 6 obsahuje výřez, připravenost, exportní snímek a cesty, nikoli kopie fotografií. Zápisy probíhají sériově mimo GUI a používají atomickou náhradu; zavření počká na dokončení. Chyby se zobrazí. Schémata 1–5 se migrují se zálohou původních bajtů a poškozený stav se před obnovou zachová.

Vstupy se nikdy nepřepisují. Při kolizi exportu vznikne volný název. Chyba nebo zrušení odstraní pouze nové soubory nedokončené série dané fotografie; hotové série zůstanou. Odstranění z knihovny nemaže diskové soubory. Oba exporty přeskočí modré Importováno, dokud se úspěšně nezobrazí jejich aktuální náhled.

## Chování a limity obrázků

- Export zachovává popředí v **měřítku 1:1**. Fit přidává plátno, Fill vyřezává. Uživatelský resize není dostupný. Zaokrouhlování může upravit plátno nebo výřez o několik pixelů.
- Souřadnice výřezu patří správně orientovanému originálu. Výřez je vstupem pro geometrii, polohu i vzorkování pozadí. Zachovaný podíl se počítá vůči **celému originálu**, včetně vstupního výřezu i Fill oříznutí.
- SDR export je **sRGB JPEG s kvalitou 99**, bez původních EXIF/GPS metadat. Kvalita 99 je nastavení kodeku, nikoli procento zachovaných dat. Průhlednost PNG se skládá na podklad a EXIF orientace se respektuje.
- Podpora HDR zahrnuje platné Ultra HDR/Apple HDR JPEG gain mapy, podporované Apple/ISO HEIC gain mapy a 10/12bitový PQ/HLG HEIC se známými barevnými metadaty. Nepodporované či poškozené HDR se výslovně odmítne. Náhled je vždy SDR.
- HDR→SDR používá `_SDR`, zachované HDR `_HDR`. HDR JPEG obsahuje ISO gain mapu; HDR HEIC používá 10bitový PQ/BT.2020. Původní reprezentace HDR se při novém kódování může změnit.
- **Pevný limit 80 MP neplatí.** Export vykresluje po dílech a kontroluje dostupnou RAM. SDR JPEG dovoluje nejvýše **65 500 px na hranu dílu**, přibalený HDR JPEG kodek **8192 px na hranu**.
- Rychlý náhled má nejvýše **2048 px** na delší hraně. Nativní detail se řídí fyzickým viewportem včetně DPR a rozpočtem 40 % právě dostupné RAM. Aplikace vysvětlí použití pouze zmenšeného náhledu.
- Blur pozadí může používat zmenšený rastr. Instagram může soubory zmenšit či rekomprimovat a měnit podporované poměry. Aplikace nic nenahrává a neslibuje stejný vzhled na každém HDR zařízení.

Podrobná barevná rozhodnutí, podmínky měření a zdroje jsou v [technickém výzkumu](./docs/RESEARCH.md).

## Generované soubory a čištění

Ignorované `.pytest_cache/` a `.pytest-tmp*/` lze po ukončení testů smazat; pytest je vytvoří znovu. `.dev-data/` je samostatná relace vývojové spouštěcí úlohy: smazáním resetujete tento vývojový stav. `.test-artifacts/` obsahuje historické reporty, screenshoty, benchmarky a volitelné externí HDR vzorky; lze ho odstranit, když tyto soubory už nepotřebujete. Běžné testy používají vlastní dočasná data a verzovanou [HDR ukázku](./tests/fixtures/hdr/). Zabalené EXE tyto složky k běhu nepotřebuje.

`insta_g/` je Python balíček v aktuálním flat uspořádání. Případné src uspořádání by používalo `src/insta_g/` a zachovalo název balíčku i importy.

## Struktura projektu a web

| Umístění | Odpovědnost |
| --- | --- |
| [insta_g/core/](./insta_g/core/) | Modely, geometrie, kodeky, zpracování a export bez GUI |
| [insta_g/gui/](./insta_g/gui/) | Hlavní okno, widgety a workery |
| [persistence.py](./insta_g/persistence.py), [preferences.py](./insta_g/preferences.py) | Verzovaná relace a globální nastavení |
| [i18n.py](./insta_g/i18n.py) | Překlady aplikace |
| [index.html](./index.html), [docs/assets/](./docs/assets/) | Statický prezentační web bez buildu |
| [README-user.md](./README-user.md), [README-user-sk.md](./README-user-sk.md), [README-user-cz.md](./README-user-cz.md) | Společné zdrojové návody aplikace i webu |

Web přepíná EN/SK/CS okamžitě přes JavaScript bez reloadu, podporuje systémový/světlý/tmavý vzhled a načítá zvolený návod přímo z těchto Markdown souborů.

## Stav, přispívání a licence

Ověření webu a dokumentace, dokončené 12. listopadu 2026: aplikační sada **651 passed, 1 skipped**; **14 browser scénářů prošlo**, včetně okamžitého přepínání jazyků, společných návodů, motivů, klávesnice a responzivního rozložení od 320 do 1440 px. Source i nový Windows EXE prošly **13/13 smoke kontrolami**. Volitelný 84 MP test se při této dodávce neopakoval. Podrobné důkazy a meze ověření jsou v [implementačním plánu](./docs/IMPLEMENTATION_PLAN.md), dodané změny v [changelogu](./CHANGELOG.md).

Při hlášení chyby uveďte verzi aplikace a Windows, kroky, očekávané chování a zobrazenou chybu. Použijte generované nebo sdílené vzorky. Pravidla automatizace přispěvatelů jsou v [AGENTS.md](./AGENTS.md). Projekt je určen pro veřejný open-source vývoj; konkrétní licence zatím nebyla zvolena a repozitář aktuálně neposkytuje dodatečné licenční oprávnění.
