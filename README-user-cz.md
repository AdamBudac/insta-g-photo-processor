# Návod k použití — Insta G Photo Processor

Připravte panorama jako navazující díly carouselu nebo doplňte pozadí kolem portrétu. Zpracování probíhá ve vašem počítači. Aplikace nevyžaduje účet, neposílá fotografie na server a nemění původní soubory.

## Stažení a spuštění ve Windows

1. V repozitáři projektu na GitHubu otevřete **Releases** a v části **Assets** nejnovějšího vydání stáhněte **InstaGPhotoProcessor.exe**. Archivy **Source code** jsou určené pro vývoj a pro používání aplikace je nepotřebujete.
2. EXE uložte do libovolné složky a spusťte dvojklikem. Nepotřebujete instalátor, Python ani samostatný HEIC kodek. Použijte Windows x64; ověřeným prostředím je Windows 11 x64.
3. Před otevřením nové verze zavřete starší, protože používají stejnou uloženou relaci. První spuštění one-file aplikace může chvíli trvat, než se přibalené součásti rozbalí do dočasné složky.

Nastavení se ukládají samostatně ve složce Windows Documents. Přesunutím nebo výměnou EXE je neodstraníte.

## První spuštění a nastavení aplikace

Při prvním spuštění vyberte **výchozí složku exportu**, **vzhled** a **jazyk**. **OK** potvrdí vaše volby; **Použít výchozí / Přeskočit** dokončí úvodní nastavení s výchozími hodnotami. Výchozím jazykem je angličtina a vzhled se řídí systémem. Výchozí složka `Export` je v datové složce aplikace ve skutečné složce Windows Documents.

Volby později změníte přes **Nastavení aplikace**. K dispozici je angličtina, slovenština a čeština. Vzhled může být světlý, tmavý nebo podle Windows; systémová volba reaguje i na pozdější změnu vzhledu Windows. **Zrušit** zachová původní nastavení.

Exporty se ukládají do nastavené složky. Pokud ji smažete nebo přesunete, vyberte existující cíl v nastavení. Aplikace problém oznámí a smazanou vlastní složku potichu nevytvoří znovu.

## První export

1. Klikněte na **Přidat fotografie** nebo přetáhněte JPEG/JPG, PNG či HEIC/HEIF do knihovny vlevo. Import fotografii automaticky neotevře.
2. Klikněte na fotografii a počkejte na dokončení aktuálního náhledu. Fotografie získá žlutý stav **Připraveno**.
3. Volitelný výřez upravte přímo v prostředním náhledu tažením úchytů na hranách a rozích fotografie. Zvolte **Carousel / Rozdělení** pro několik navazujících dílů nebo **Doplnit plátno** pro jeden obrázek s okraji. Nastavte počet dílů a poměr stran.
4. Upravte polohu a pozadí. Zkontrolujte bílý rám výstupu a rozměry v pravém panelu.
5. **Exportovat všechny** zpracuje všechny připravené a exportované fotografie. Pro menší výběr je označte checkboxy a zvolte **Exportovat vybrané**. Modré importované se vždy přeskočí.
6. Počkejte na souhrn exportu. Samostatně uvádí počet původních fotografií, výstupních souborů a chyb.

## Barvy knihovny a výběr

| Stav | Význam |
| --- | --- |
| Modré — Importováno | Fotografie ještě nebyla úspěšně zobrazena v aktuálním náhledu. Před exportem ji otevřete. |
| Žluté — Připraveno | Aktuální náhled vybrané fotografie se úspěšně zobrazil. Fotografie je způsobilá k exportu. |
| Zelené — Exportováno | Všechny díly se úspěšně uložily s aktuálním nastavením fotografie. |
| Červené — Nezdařilo se | Selhal import, náhled nebo export. Důvod najdete v tooltipu nebo stavovém řádku; odstraňte příčinu a zkuste to znovu. |

Kliknutí na řádek otevře náhled. Checkbox označuje fotografii pro hromadné akce nezávisle na aktivním náhledu. Samotné zaškrtnutí fotografii nepřipraví, nemění nastavení ani platný zelený stav.

Úprava kompozice zneplatní zelený stav. Chybný nebo zastaralý náhled nemůže nastavit připravenost. Při přejetí myší zůstává rozpoznatelná barva daného stavu.

**Odstranit vybrané**, **Odstranit všechny**, **Odstranit exportované** a ikona koše odstraňují pouze položky knihovny. Nemažou originály ani dokončené exporty. **Zopakovat nezdařené** zkusí neúspěšné fotografie znovu po odstranění příčiny problému.

## Vstupní výřez

V prostředním náhledu táhněte za úchyty na hranách a rozích fotografie. Tažením dovnitř plochu oříznete, směrem ven můžete vrátit dříve oříznuté pixely až po původní okraj fotografie. Neotevírá se samostatný dialog a není třeba zadávat pixelové souřadnice. Levé tažení uvnitř fotografie nadále mění její polohu na výstupním plátně.

Při tažení zůstává kamera stabilní a změny se automaticky ukládají. **Escape** vrátí výřez ze začátku gesta. Po uvolnění úchytu zůstává v přizpůsobeném zobrazení celý původní originál i výstupní plátno. Oříznuté části jsou viditelné s tmavým překrytím, takže hranu můžete jedním tažením vrátit až na původní okraj fotografie. Výřez může mít libovolný poměr; zůstává uvnitř originálu a má alespoň 1 × 1 px.

**Obnovit celý záběr (Reset crop)** přímo pod tlačítkem **Vycentrovat obrázek** v pravém panelu vrátí celou fotografii. Skutečná změna výřezu zneplatní předchozí zelený stav exportu. Zdrojový soubor zůstává nezměněný, takže oříznuté části lze vždy vrátit.

Výřez se stává vstupem pro rozdělení, doplnění okrajů, polohu i pozadí bez změny měřítka pixelů. Také blur pozadí se odvozuje pouze z něj. Ztlumený originál mimo výřez slouží pro orientaci v náhledu. **Zachováno** vždy porovnává viditelnou plochu s celým původním originálem: výřez 800 × 400 px z fotografie 1000 × 500 px zachová **64 %**, i při Fit / Padding. Další Fill / Crop může podíl ještě snížit.

## Carousel a doplnění plátna

Carousel podporuje **2–20 dílů** zleva doprava. Díly mají stejné rozměry a tvoří jednu navazující kompozici. Nová fotografie začíná s **Fill / Crop**. Obnovená fotografie zachová uložené nastavení.

**Automatický poměr** vypočítá poměr dílu ze šířky a výšky zvoleného vstupního výřezu a počtu dílů v rozsahu **3:4 až 16:9**. Bez výřezu používá celý originál. Předvolby jsou **16:9, 3:2, 4:3, 5:4, 1:1, 4:5 a 3:4**. Posuvník umožňuje mezihodnoty; jeho posun vypne automatický poměr. Poměr znamená šířku dělenou výškou, bez samostatného přepínače orientace.

**Fit / Padding** zachová celý zvolený vstup v původním měřítku pixelů a doplní chybějící plochu pozadím. **Fill / Crop** může odstranit další část tohoto vstupu. Ztlumený obraz za bílým rámem ukazuje plochu odstraněnou režimem Fill. Vstupní výřez lze zvětšit tažením úchytů směrem ven nebo tlačítkem Obnovit celý záběr.

**Doplnit plátno** vytváří jeden obrázek a vždy používá Fit / Padding. Zachová celý zvolený vstup a přidá okraje po stranách nebo nahoře a dole.

Panorama 6000 × 2000 px při třech čtvercových dílech vytvoří tři soubory 2000 × 2000 px. Popředí se nepřepočítává na pevné rozlišení Instagramu.

## Poloha, přiblížení a kompozice

Použijte posuvníky **Vodorovně** a **Svisle** nebo fotografii v náhledu táhněte **levým tlačítkem myši**. Tažení mění stejnou polohu jako export. **Vycentrovat obrázek** nebo **levý dvojklik** vynuluje oba posuny fotografie a zachová přiblížení. Na ose bez volného pozadí nebo přesahu už fotografie nemá kam pokračovat.

**Pravým tlačítkem myši** táhnete pouze pohled na přiblížený obrázek. Stejně funguje prostřední tlačítko nebo Space + levé tažení; Escape posouvání ukončí. **Pravý dvojklik** obnoví **přizpůsobené zobrazení (Fit view)**: 100% přiblížení a vycentrovaný pohled na celý původní originál i plátno. Pravé tažení ani pravý dvojklik nemění polohu fotografie, stav exportu ani uložené nastavení.

**Přiblížení náhledu** je **100–1000 % vzhledem k přizpůsobenému zobrazení**. Návrat na 100 % automaticky vycentruje celý původní originál i plátno a oříznuté části zůstávají ztlumené. Přiblížení nemění export. Při pohybu se fotografie okamžitě kreslí z cache. Dostupný detail popředí se pohybuje spolu s fotografií a aplikace na pozadí doplňuje aktuální viditelnou oblast.

Nejprve se zobrazí malý náhled do 2048 px. Aktivní originál se potom načte na pozadí, už při 100% přiblížení, pokud je dostupná paměť. Viditelný **detail z originálu** se přizpůsobuje velikosti panelu a škálování displeje včetně monitorů s vysokým rozlišením; nemá pevný limit 2048 px. Detail se aktualizuje i během tažení, přibližování nebo změny polohy a poměru stran.

Stav pod obrázkem rozlišuje načítání, nativní detail a zmenšený náhled s důvodem. Pro náhled se uchovává pouze jeden plný originál; nároky na paměť závisí na fotografii, viditelné oblasti a dostupné RAM. První dekódování velkého zdroje může chvíli trvat. Malý náhled zůstává použitelný během načítání i při nedostatku paměti na nativní detail. Náhled vždy zobrazuje SDR verzi, i u HDR originálu.

**Kompozice** nabízí v pořadí **Žádná, 2×2, 3×3, φ pro zlatý řez a X pro diagonály**. Tlačítka i tooltipy používají stejné písmo a styl. Jsou pouze v náhledu a **nikdy se neexportují**. I hranice dílů jsou pomocné značky náhledu.

## Pozadí a barvy

Pro doplněné okraje zvolte **rozostřenou fotografii**, **bílou**, **černou** nebo **vlastní barvu**. **Kapátko** umožní kliknout na barvu v náhledu. K dispozici je také pět dominantních barev získaných z fotografie a vlastní výběr barvy.

**Rozostření pozadí** je 0–1000 px v měřítku výstupu. Při 0 px zůstává fotografické pozadí ostré. Dekorativní pozadí se může připravovat ve sníženém rozlišení pro úsporu paměti; původní popředí zůstává v původním měřítku pixelů.

## Dynamický rozsah a kvalita

U rozpoznaného HDR zdroje volba **Dynamický rozsah** přepíná původní HDR nebo převod na SDR. Podporované zdroje zahrnují 10/12bitový PQ nebo HLG HEIC s podporovaným barevným označením BT.709, BT.2020 či Display P3, podporované Apple HEIC gain mapy, ISO 21496 HEIC gain mapy a podporované Ultra HDR či Apple HDR JPEG. Neznámá nebo poškozená HDR data vyvolají viditelnou chybu místo nesprávně označeného HDR exportu.

Náhled vždy zobrazuje SDR verzi. U fotografií s gain mapou používá SDR bázi vytvořenou fotoaparátem a převádí její barevný profil do sRGB. PQ/HLG zdroje převádí mapováním jasů a kompresí světel i barevného gamutu. Náhled slouží ke kompozici na běžném displeji; nezobrazuje HDR jas displeje.

HDR export má před číslem dílu `_HDR`. Převod HDR zdroje na SDR používá `_SDR`. Běžné SDR zdroje zachovávají standardní název bez těchto přípon rozsahu.

Běžný SDR výstup je **JPEG s kvalitou 99**, profilem sRGB a bez původních EXIF či GPS metadat. Kvalita 99 je parametr kodeku, nikoli procento zachovaných dat. Průhlednost PNG se při výstupu skládá na podklad. Orientace vstupu se respektuje.

Zachování HDR ponechává rodinu kontejneru zdroje: HEIC vytváří **10bitový PQ BT.2020 HEIC**, podporovaný HDR JPEG vytváří **JPEG s ISO gain mapou a SDR bází**. Původní reprezentace HDR se tak může změnit při zachování HDR obrazu a původních rozměrů popředí. Výstupy neobsahují původní EXIF ani GPS metadata. Samotná přípona nedokazuje přítomnost HDR dat.

Přibalený kodek HDR JPEG podporuje nejvýše **8192 px na každé hraně jednoho dílu**. Jde o skutečný limit kodeku. Více dílů může zmenšit příliš velkou šířku; nadměrná výška vyžaduje jiný výřez nebo menší zdroj. Také HDR HEIC a ostatní velké exporty podléhají dostupné paměti a omezením kodeku.

## Chování exportu

Exportovat lze pouze **Připraveno** a **Exportováno**. **Exportovat vybrané** při spuštění zachytí způsobilé označené položky. **Exportovat všechny** zachytí všechny způsobilé položky i bez checkboxu. Aktivní náhled neurčuje rozsah exportu. Pozdější změna checkboxů nebo nastavení ovlivní další dávku.

Fotografie se zpracovává jako celek: úspěšné musí být všechny díly. Při chybě nebo zrušení se odstraní neúplné výstupy právě zpracovávané fotografie. Dokončené fotografie ze starší části dávky zůstanou zachovány. Chyba jedné fotografie nezastaví ostatní.

Okno zůstává během exportu použitelné. **Zrušit export** požádá o zastavení; aktuální dekódování nebo vykreslování se může nejprve dokončit. Souhrn rozlišuje úspěšně exportované originály a počet zapsaných souborů.

Existující soubory se nepřepisují; aplikace vybere jiný volný název. Originály se nikdy nepřepisují. Zelený stav znamená úspěšný export celé fotografie s aktuálním nastavením.

Popředí zůstává v **měřítku 1:1**. Fit zvětšuje plátno, Fill vyřezává část fotografie. Zaokrouhlování na celé pixely může přidat trochu pozadí nebo upravit výřez. Rozhodující jsou rozměry v pravém panelu.

Velké operace se porovnávají s dostupnou pamětí. **SDR JPEG** podporuje nejvýše **65 500 px na hraně dílu**, **HDR JPEG** s přibaleným kodekem **8192 px na hraně dílu**. Pevný limit 80 MP neplatí. Malý náhled nezaručuje, že originál lze exportovat s dostupnou RAM.

## Uložené údaje a obnova

Nastavení fotografií včetně vstupních výřezů, cesty, checkboxy, připravenost náhledu a stavy exportu se v nové instalaci automaticky ukládají do `session.json` v `<Windows Documents>/insta-g-photo-processor`. Globální vzhled, jazyk, úvodní nastavení a výchozí složka exportu jsou samostatně v `preferences.json`. Přesměrování Windows Documents se respektuje.

Aktualizace z Insta G Image Resizer zachová existující údaje: pokud nová složka nemá ani jeden ze stavových souborů a původní `<Windows Documents>/insta-g-image-resizer` alespoň jeden má, aplikace nadále používá původní složku bez přesouvání souborů. Existující stav v nové složce má přednost. Nastavená složka exportu zůstává zachována.

Tyto soubory obsahují nastavení a cesty, nikoli kopie fotografií. Každá změna se zapisuje v pořadí mimo GUI; zavření počká na dokončení zápisů. Přesunutý originál je nutné znovu importovat z nové cesty. Chyba zápisu se zobrazí; do té doby mohou poslední změny zůstat pouze v paměti.

Zápis používá dočasný soubor a atomickou náhradu. Neplatné uložené údaje se oznámí a zachovají v časově označené záloze před uložením nových dat. Nečitelný stav se nesmí potichu zahodit ani přepsat.

## Nápověda a klávesové zkratky

**Nápověda → Návod k použití** otevře tento posouvatelný návod ve zvoleném jazyce. **O aplikaci** identifikuje aplikaci. Zkratky: **Ctrl+O** import, **Ctrl+E** export všech způsobilých fotografií, **Delete** odstranění označených položek z knihovny a **Alt+F4** zavření okna.

Aplikace připravuje místní soubory a nepublikuje na Instagram. Instagram může při nahrání měnit rozlišení a kompresi; podporované poměry se mohou měnit. Aplikace zvolený poměr potichu neupravuje.
