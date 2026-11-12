"""Small runtime catalog with English keys and legacy Slovak aliases.

The processing core stays independent of Qt. Widget imports are deliberately
local to the optional widget-tree translation helper.
"""

from __future__ import annotations

import re
from string import Formatter
from typing import Any

LANGUAGES = ("en", "sk", "cs")
_language = "en"
_MAX_NESTED_TRANSLATIONS = 16

# English, Slovak, Czech. Existing Slovak strings remain accepted as aliases.
_ROWS: tuple[tuple[str, str, str], ...] = (
    ("Crop photo", "Orezať fotografiu", "Oříznout fotografii"),
    ("Crop photo…", "Orezať fotografiu…", "Oříznout fotografii…"),
    ("Reset crop", "Obnoviť celý záber", "Obnovit celý záběr"),
    ("Choose the source area before split or padding.", "Vyberte vstupný výrez pred rozdelením alebo doplnením okrajov.", "Vyberte vstupní výřez před rozdělením nebo doplněním okrajů."),
    ("The selected area becomes the source for split and padding. Original files stay unchanged.", "Vybraná oblasť bude vstupom pre rozdelenie a doplnenie okrajov. Originálne súbory sa nemenia.", "Vybraná oblast bude vstupem pro rozdělení a doplnění okrajů. Původní soubory se nemění."),
    ("Drag to select, move inside the selection, or resize its edges. Shift+drag draws a new selection.", "Ťahaním vyberte oblasť, posúvajte ju za vnútro alebo upravte okraje. Shift+ťahanie vytvorí nový výber.", "Tažením vyberte oblast, posouvejte ji za vnitřek nebo upravte okraje. Shift+tažení vytvoří nový výběr."),
    ("A valid photo is required for cropping.", "Na orezanie je potrebná platná fotografia.", "K ořezu je potřeba platná fotografie."),
    ("Crop {width} × {height} px", "Výrez {width} × {height} px", "Výřez {width} × {height} px"),
    ("Full photo {width} × {height} px", "Celá fotografia {width} × {height} px", "Celá fotografie {width} × {height} px"),
    ("X", "X", "X"),
    ("Y", "Y", "Y"),
    ("Width", "Šírka", "Šířka"),
    ("Height", "Výška", "Výška"),
    ("Local processing. Originals remain unchanged.", "Lokálne spracovanie. Originály zostávajú zachované.", "Místní zpracování. Originály zůstávají zachovány."),
    ("Preferences", "Nastavenia aplikácie", "Nastavení aplikace"),
    ("Preferences…", "Nastavenia aplikácie…", "Nastavení aplikace…"),
    ("Welcome to Insta G Photo Processor", "Vitajte v Insta G Photo Processor", "Vítejte v Insta G Photo Processor"),
    ("Restore the whole original photo.", "Obnoviť celú pôvodnú fotografiu.", "Obnovit celou původní fotografii."),
    ("Choose your export folder, appearance and language. You can change these later in Preferences.", "Vyberte exportný priečinok, vzhľad a jazyk. Neskôr ich môžete zmeniť v nastaveniach aplikácie.", "Vyberte složku exportu, vzhled a jazyk. Později je můžete změnit v nastavení aplikace."),
    ("Default export folder", "Predvolený exportný priečinok", "Výchozí složka exportu"),
    ("Browse…", "Prehľadávať…", "Procházet…"),
    ("Choose export folder", "Vyberte exportný priečinok", "Vyberte složku exportu"),
    ("Appearance", "Vzhľad", "Vzhled"),
    ("Follow system", "Podľa systému", "Podle systému"),
    ("Light", "Svetlý", "Světlý"),
    ("Dark", "Tmavý", "Tmavý"),
    ("Language", "Jazyk", "Jazyk"),
    ("English", "Angličtina", "Angličtina"),
    ("Slovak", "Slovenčina", "Slovenština"),
    ("Czech", "Čeština", "Čeština"),
    ("Save", "Uložiť", "Uložit"),
    ("Cancel", "Zrušiť", "Zrušit"),
    ("Close", "Zavrieť", "Zavřít"),
    ("OK", "OK", "OK"),
    ("Use defaults / Skip", "Použiť predvolené / Preskočiť", "Použít výchozí / Přeskočit"),
    ("Use defaults", "Použiť predvolené", "Použít výchozí"),
    ("Export folder must be an absolute path.", "Exportný priečinok musí mať absolútnu cestu.", "Složka exportu musí mít absolutní cestu."),
    ("Choose an existing folder. The application will not recreate a deleted export folder.", "Vyberte existujúci priečinok. Aplikácia vymazaný exportný priečinok znova nevytvorí.", "Vyberte existující složku. Aplikace smazanou složku exportu znovu nevytvoří."),
    ("User guide", "Návod na použitie", "Návod k použití"),
    ("User guide…", "Návod na použitie…", "Návod k použití…"),
    ("The user guide could not be loaded.", "Návod na použitie sa nepodarilo načítať.", "Návod k použití se nepodařilo načíst."),
    ("FULL FRAME. EVERY DETAIL.", "CELÝ ZÁBER. KAŽDÝ DETAIL.", "CELÝ ZÁBĚR. KAŽDÝ DETAIL."),
    ("Panoramas for carousels. Portraits without cropping.", "Panorámy na carousel. Portréty bez orezania.", "Panoramata na carousel. Portréty bez ořezu."),
    ("Your photos", "Vaše fotografie", "Vaše fotografie"),
    ("+  Add photos", "+  Pridať fotografie", "+  Přidat fotografie"),
    ("Add photos", "Pridať fotografie", "Přidat fotografie"),
    ("Add photos…", "Pridať fotografie…", "Přidat fotografie…"),
    ("JPEG · PNG · HEIC\nDrop files here.", "JPEG · PNG · HEIC\nSúbory môžete presunúť priamo sem.", "JPEG · PNG · HEIC\nSoubory můžete přetáhnout přímo sem."),
    ("Remove selected", "Odstrániť vybrané", "Odstranit vybrané"),
    ("Remove all", "Odstrániť všetky", "Odstranit všechny"),
    ("Remove exported", "Odstrániť exportované", "Odstranit exportované"),
    ("Export selected", "Exportovať vybrané", "Exportovat vybrané"),
    ("Export all", "Exportovať všetky", "Exportovat všechny"),
    ("Export selected…", "Exportovať vybrané…", "Exportovat vybrané…"),
    ("Export all…", "Exportovať všetky…", "Exportovat všechny…"),
    ("Remove checked photos", "Odstrániť označené fotografie", "Odstranit označené fotografie"),
    ("Removes library entries only. Files on disk are kept.", "Odstráni položky iba z knižnice. Súbory na disku zostanú zachované.", "Odstraní položky pouze z knihovny. Soubory na disku zůstanou zachovány."),
    ("Composition", "Kompozícia", "Kompozice"),
    ("PREVIEW UP TO 2048 PX", "NÁHĽAD DO 2048 PX", "NÁHLED DO 2048 PX"),
    ("ADAPTIVE PREVIEW", "ADAPTÍVNY NÁHĽAD", "ADAPTIVNÍ NÁHLED"),
    ("Cancel export", "Zrušiť export", "Zrušit export"),
    ("Ready. Original files are unchanged.", "Pripravené. Originálne súbory sa nemenia.", "Připraveno. Původní soubory se nemění."),
    ("File", "Súbor", "Soubor"),
    ("Settings", "Nastavenia", "Nastavení"),
    ("Exit", "Ukončiť", "Ukončit"),
    ("Help", "Pomocník", "Nápověda"),
    ("About", "O aplikácii", "O aplikaci"),
    ("Photos (*.jpg *.jpeg *.png *.heic *.heif);;All files (*)", "Fotografie (*.jpg *.jpeg *.png *.heic *.heif);;Všetky súbory (*)", "Fotografie (*.jpg *.jpeg *.png *.heic *.heif);;Všechny soubory (*)"),
    ("Exports all prepared and exported photos. Imported photos are skipped.", "Exportuje všetky pripravené a už exportované fotografie. Importované preskočí.", "Exportuje všechny připravené a již exportované fotografie. Importované přeskočí."),
    ("Exports checked prepared and exported photos. Imported photos are skipped.", "Exportuje označené pripravené a už exportované fotografie. Importované preskočí.", "Exportuje označené připravené a již exportované fotografie. Importované přeskočí."),
    ("Choose a folder for selected photos", "Vyberte priečinok pre vybrané fotografie", "Vyberte složku pro vybrané fotografie"),
    ("Choose a folder for all exports", "Vyberte priečinok pre všetky exporty", "Vyberte složku pro všechny exporty"),
    ("Exporting photos from originals…", "Exportujem fotografie z originálov…", "Exportuji fotografie z originálů…"),
    ("Export cancelled", "Export zrušený", "Export zrušen"),
    ("Export complete", "Export dokončený", "Export dokončen"),
    ("Preview is up to date.", "Náhľad je aktuálny.", "Náhled je aktuální."),
    ("Finishing the current tile and cancelling export…", "Dokončujem aktuálny diel a ruším export…", "Dokončuji aktuální díl a ruším export…"),
    ("Finishing processing…", "Ukončujem spracovanie…", "Ukončuji zpracování…"),
    ("Unsupported files: ", "Nepodporované súbory: ", "Nepodporované soubory: "),
    ("Loading ", "Načítavam ", "Načítám "),
    (" photos", " fotografií", " fotografií"),
    ("Import complete.", "Import dokončený.", "Import dokončen."),
    ("Automatic saving is working again.", "Automatické ukladanie opäť funguje.", "Automatické ukládání opět funguje."),
    ("Settings could not be saved. Changes are kept in memory only. ", "Nastavenia sa nepodarilo uložiť. Zmeny sú iba v pamäti. ", "Nastavení se nepodařilo uložit. Změny jsou pouze v paměti. "),
    ("Edit photo", "Úprava fotografie", "Úprava fotografie"),
    ("Select a photo in the library", "Vyberte fotografiu v knižnici", "Vyberte fotografii v knihovně"),
    ("Mode", "Režim", "Režim"),
    ("Add padding", "Doplniť okraje", "Doplnit okraje"),
    ("Splits the photo into adjoining carousel tiles.", "Rozdelí fotografiu na nadväzujúce diely carouselu.", "Rozdělí fotografii na navazující díly carouselu."),
    ("Keeps the whole photo and adds padding to the chosen ratio.", "Zachová celú fotografiu a doplní okraje do zvoleného pomeru.", "Zachová celou fotografii a doplní okraje do zvoleného poměru."),
    ("Number of tiles", "Počet dielov", "Počet dílů"),
    ("Automatic ratio", "Automatický pomer", "Automatický poměr"),
    ("The ratio uses the whole original and tile count, between 3:4 and 16:9.", "Pomer vychádza z celého originálu a počtu dielov, v rozsahu 3:4 až 16:9.", "Poměr vychází z celého originálu a počtu dílů, v rozsahu 3:4 až 16:9."),
    ("Tile ratio", "Pomer jedného dielu", "Poměr jednoho dílu"),
    ("Continuous ratio from 3:4 to 16:9. Moving this disables automatic ratio.", "Plynulý pomer od 3:4 po 16:9. Posun vypne automatický pomer.", "Plynulý poměr od 3:4 do 16:9. Posun vypne automatický poměr."),
    ("Original placement", "Umiestnenie originálu", "Umístění originálu"),
    ("Preserves every original pixel; fills the additional canvas with a background.", "Zachová všetky pôvodné pixely; potrebnú plochu doplní pozadím.", "Zachová všechny původní pixely; potřebnou plochu doplní pozadím."),
    ("Fills the canvas with original pixels and crops outside the white frame.", "Vyplní plátno pôvodnými pixelmi a oreže časti mimo bieleho rámu.", "Vyplní plátno původními pixely a ořízne části mimo bílý rám."),
    ("Horizontal", "Vodorovne", "Vodorovně"),
    ("Vertical", "Zvislo", "Svisle"),
    ("Center", "Vycentrovať", "Vycentrovat"),
    ("Background blur", "Rozostrenie doplneného pozadia", "Rozostření doplněného pozadí"),
    ("Blur radius in original pixels. 0 px keeps the background sharp.", "Polomer rozostrenia v pôvodných pixeloch. 0 px ponechá pozadie ostré.", "Poloměr rozostření v původních pixelech. 0 px ponechá pozadí ostré."),
    ("-100 %: left/top · 0 %: center · +100 %: right/bottom", "-100 %: ľavý/horný okraj · 0 %: stred · +100 %: pravý/dolný okraj", "-100 %: levý/horní okraj · 0 %: střed · +100 %: pravý/dolní okraj"),
    ("JPEG · quality 99 % · sRGB\nOriginal pixels without resampling.\nEvery change is saved automatically.", "JPEG · kvalita 99 % · sRGB\nPôvodné pixely bez prevzorkovania.\nKaždá zmena sa automaticky uloží.", "JPEG · kvalita 99 % · sRGB\nPůvodní pixely bez převzorkování.\nKaždá změna se automaticky uloží."),
    ("Fill crops outside the white frame. The preview shows these parts dimmed.", "Fill oreže časti mimo bieleho rámu. V náhľade zostávajú viditeľné tlmene.", "Fill ořízne části mimo bílý rám. V náhledu zůstávají viditelné ztlumeně."),
    ("Prepare your next carousel", "Pripravte svoj ďalší carousel", "Připravte svůj další carousel"),
    ("Loading photo…", "Načítavam fotografiu…", "Načítám fotografii…"),
    ("Add or select a photo in the left panel.\nOriginal files are unchanged.", "Pridajte alebo vyberte fotografiu v ľavom paneli.\nOriginálne súbory sa nemenia.", "Přidejte nebo vyberte fotografii v levém panelu.\nPůvodní soubory se nemění."),
    ("Exported", "Exportované", "Exportováno"),
    ("Prepared", "Pripravené", "Připraveno"),
    ("Imported", "Importované", "Importováno"),
    ("Failed", "Zlyhané", "Nezdařilo se"),
    ("Drop JPEG, PNG or HEIC photos here.", "Presuňte sem fotografie JPEG, PNG alebo HEIC.", "Přetáhněte sem fotografie JPEG, PNG nebo HEIC."),
    ("Remove photo from library", "Odstrániť fotografiu z knižnice", "Odstranit fotografii z knihovny"),
    ("Check for export", "Označiť na export", "Označit k exportu"),
    ("Retry import", "Zopakovať import", "Zopakovat import"),
    ("Retry", "Skúsiť znova", "Zkusit znovu"),
    ("Remove", "Odstrániť", "Odstranit"),
    ("Failed to import photo", "Fotografiu sa nepodarilo importovať", "Fotografii se nepodařilo importovat"),
    ("Zoom", "Priblíženie", "Přiblížení"),
    ("Fit", "Prispôsobiť", "Přizpůsobit"),
    ("Fit to view", "Prispôsobiť náhľadu", "Přizpůsobit náhledu"),
    ("Reset zoom", "Obnoviť priblíženie", "Obnovit přiblížení"),
    ("Grid", "Mriežka", "Mřížka"),
    ("None", "Žiadna", "Žádná"),
    ("Rule of thirds", "Pravidlo tretín", "Pravidlo třetin"),
    ("Golden ratio", "Zlatý rez", "Zlatý řez"),
    ("Diagonal", "Diagonálna", "Diagonální"),
    ("Center cross", "Stredový kríž", "Středový kříž"),
    ("Grid is shown in the preview only and is never exported.", "Mriežka je iba v náhľade a nikdy sa neexportuje.", "Mřížka je pouze v náhledu a nikdy se neexportuje."),
    ("Drag the photo with the left mouse button. Double-click to center.", "Fotografiu posúvajte ľavým tlačidlom myši. Dvojklik ju vycentruje.", "Fotografii posouvejte levým tlačítkem myši. Dvojklik ji vycentruje."),
    ("Background", "Pozadie", "Pozadí"),
    ("Blurred photo", "Rozostrená fotografia", "Rozostřená fotografie"),
    ("Blur", "Rozostrenie", "Rozostření"),
    ("White", "Biele", "Bílé"),
    ("Black", "Čierne", "Černé"),
    ("Custom color", "Vlastná farba", "Vlastní barva"),
    ("Choose color…", "Vybrať farbu…", "Vybrat barvu…"),
    ("Eyedropper", "Kvapkadlo", "Kapátko"),
    ("Pick from photo", "Vybrať z fotografie", "Vybrat z fotografie"),
    ("Dominant colors", "Dominantné farby", "Dominantní barvy"),
    ("Click a color in the photo.", "Kliknite na farbu vo fotografii.", "Klikněte na barvu ve fotografii."),
    ("HDR", "HDR", "HDR"),
    ("Preserve HDR", "Zachovať HDR", "Zachovat HDR"),
    ("Convert to SDR", "Konvertovať na SDR", "Převést na SDR"),
    ("Export summary", "Súhrn exportu", "Souhrn exportu"),
    ("Original photos: {count}", "Pôvodné fotografie: {count}", "Původní fotografie: {count}"),
    ("Output files: {count}", "Výstupné súbory: {count}", "Výstupní soubory: {count}"),
    ("Errors: {count}", "Chyby: {count}", "Chyby: {count}"),
    ("{total} photos · checked: {checked} · imported: {imported} · prepared: {prepared} · exported: {exported} · failed: {failed}", "{total} fotografií · označené: {checked} · importované: {imported} · pripravené: {prepared} · exportované: {exported} · zlyhané: {failed}", "{total} fotografií · označené: {checked} · importované: {imported} · připravené: {prepared} · exportované: {exported} · nezdařilo se: {failed}"),
    ("Original {width} × {height} px\nOutput cannot be created.", "Originál {width} × {height} px\nVýstup nie je možné vytvoriť.", "Originál {width} × {height} px\nVýstup nelze vytvořit."),
    ("Original {width} × {height} px\nOutput {tiles} × {tile_width} × {tile_height} px", "Originál {width} × {height} px\nVýstup {tiles} × {tile_width} × {tile_height} px", "Originál {width} × {height} px\nVýstup {tiles} × {tile_width} × {tile_height} px"),
    ("{count} tiles · tile ratio {ratio:.3f}:1", "{count} dielov · pomer dielu {ratio:.3f}:1", "{count} dílů · poměr dílu {ratio:.3f}:1"),
    (" · updating…", " · aktualizujem…", " · aktualizuji…"),
    ("The export folder does not exist or is not writable. Choose another folder in Preferences.", "Exportný priečinok neexistuje alebo doň nemožno zapisovať. Vyberte iný v nastaveniach aplikácie.", "Složka exportu neexistuje nebo do ní nelze zapisovat. Vyberte jinou v nastavení aplikace."),
    ("Adjust photo", "Upraviť fotografiu", "Upravit fotografii"),
    ("Carousel / Split", "Carousel / Rozdelenie", "Carousel / Rozdělení"),
    ("Expand canvas", "Doplniť plátno", "Doplnit plátno"),
    ("Tile aspect ratio", "Pomer strán dielu", "Poměr stran dílu"),
    ("Center image", "Vycentrovať obrázok", "Vycentrovat obrázek"),
    ("Custom", "Vlastná", "Vlastní"),
    ("Composition guides", "Kompozičné čiary", "Kompoziční čáry"),
    ("No composition grid", "Žiadna kompozičná mriežka", "Žádná kompoziční mřížka"),
    ("2×2 grid (center cross)", "Mriežka 2×2 (stredový kríž)", "Mřížka 2×2 (středový kříž)"),
    ("3×3 grid (rule of thirds)", "Mriežka 3×3 (pravidlo tretín)", "Mřížka 3×3 (pravidlo třetin)"),
    ("Native detail", "Detail z originálu", "Detail z originálu"),
    ("Loading detail…", "Načítavam detail…", "Načítám detail…"),
    ("Reduced preview", "Zmenšený náhľad", "Zmenšený náhled"),
    ("Reduced preview — {reason}", "Zmenšený náhľad — {reason}", "Zmenšený náhled — {reason}"),
    ("Native detail needs approximately {required} MiB; its current memory budget is {budget} MiB. The reduced preview remains visible.", "Detail z originálu potrebuje približne {required} MiB; jeho aktuálny pamäťový rozpočet je {budget} MiB. Zmenšený náhľad zostáva zobrazený.", "Detail z originálu potřebuje přibližně {required} MiB; jeho aktuální paměťový rozpočet je {budget} MiB. Zmenšený náhled zůstává zobrazený."),
    ("The source dimensions changed. Reimport the photo to load native detail.", "Rozmery zdroja sa zmenili. Na načítanie detailu z originálu importujte fotografiu znova.", "Rozměry zdroje se změnily. Pro načtení detailu z originálu importujte fotografii znovu."),
    ("Native detail is unavailable. The reduced preview remains visible.", "Detail z originálu nie je dostupný. Zmenšený náhľad zostáva zobrazený.", "Detail z originálu není dostupný. Zmenšený náhled zůstává zobrazený."),
    ("Diagonals", "Diagonály", "Diagonály"),
    ("Dynamic range", "Dynamický rozsah", "Dynamický rozsah"),
    ("Original HDR", "Pôvodné HDR", "Původní HDR"),
    ("SDR", "SDR", "SDR"),
    ("Retained: {percent}%", "Zachované: {percent}%", "Zachováno: {percent}%"),
    ("Original {width} × {height} px", "Originál {width} × {height} px", "Originál {width} × {height} px"),
    ("Output {count} × {width} × {height} px", "Výstup {count} × {width} × {height} px", "Výstup {count} × {width} × {height} px"),
    ("Preview zoom", "Priblíženie náhľadu", "Přiblížení náhledu"),
    ("Fit view", "Prispôsobiť zobrazenie", "Přizpůsobit zobrazení"),
    ("Zoom out", "Oddialiť", "Oddálit"),
    ("Zoom in", "Priblížiť", "Přiblížit"),
    ("Ready for your next carousel", "Pripravené na váš ďalší carousel", "Připraveno na váš další carousel"),
    ("Updating…", "Aktualizujem…", "Aktualizuji…"),
    ("{count} tiles · tile ratio {ratio}:1", "{count} dielov · pomer dielu {ratio}:1", "{count} dílů · poměr dílu {ratio}:1"),
    ("Could not load image “{name}”: {error}", "Obrázok „{name}“ sa nepodarilo načítať: {error}", "Obrázek „{name}“ se nepodařilo načíst: {error}"),
    ("Export of “{name}” failed: {error}", "Export „{name}“ zlyhal: {error}", "Export „{name}“ selhal: {error}"),
    ("Output folder “{directory}” is unavailable: {error}", "Výstupný priečinok „{directory}“ nie je dostupný: {error}", "Výstupní složka „{directory}“ není dostupná: {error}"),
    ("Custom background color", "Vlastná farba pozadia", "Vlastní barva pozadí"),
    ("Split the photo into adjoining carousel tiles.", "Rozdeľte fotografiu na nadväzujúce diely carouselu.", "Rozdělte fotografii na navazující díly carouselu."),
    ("Keep the entire photo and pad the canvas to the selected ratio.", "Zachovajte celú fotografiu a doplňte plátno do zvoleného pomeru.", "Zachovejte celou fotografii a doplňte plátno do zvoleného poměru."),
    ("Calculate the ratio from the entire source and tile count, between 3:4 and 16:9.", "Vypočíta pomer z celého originálu a počtu dielov v rozsahu 3:4 až 16:9.", "Vypočítá poměr z celého originálu a počtu dílů v rozsahu 3:4 až 16:9."),
    ("Aspect ratio from 3:4 to 16:9. Moving this slider turns off automatic ratio.", "Pomer od 3:4 po 16:9. Posun vypne automatický pomer.", "Poměr od 3:4 do 16:9. Posun vypne automatický poměr."),
    ("Keep all original pixels and fill the extra canvas with the background.", "Zachová všetky pôvodné pixely a doplní plátno pozadím.", "Zachová všechny původní pixely a doplní plátno pozadím."),
    ("Fill the canvas with original pixels and crop outside the white frame.", "Vyplní plátno pôvodnými pixelmi a oreže plochu mimo bieleho rámu.", "Vyplní plátno původními pixely a ořízne plochu mimo bílý rám."),
    ("-100%: left/top · 0%: center · +100%: right/bottom", "-100%: ľavý/horný okraj · 0%: stred · +100%: pravý/dolný okraj", "-100%: levý/horní okraj · 0%: střed · +100%: pravý/dolní okraj"),
    ("JPEG · quality 99% · sRGB\nOriginal pixels without resampling.\nChanges are saved automatically.", "JPEG · kvalita 99% · sRGB\nPôvodné pixely bez prevzorkovania.\nZmeny sa automaticky ukladajú.", "JPEG · kvalita 99% · sRGB\nPůvodní pixely bez převzorkování.\nZměny se automaticky ukládají."),
    ("Unable to create output.", "Výstup nemožno vytvoriť.", "Výstup nelze vytvořit."),
    ("Fill crops outside the white frame. Cropped areas remain dimly visible.", "Fill oreže plochu mimo bieleho rámu. Odrezané časti zostávajú tlmene viditeľné.", "Fill ořízne plochu mimo bílý rám. Oříznuté části zůstávají ztlumeně viditelné."),
    ("Retry failed", "Zopakovať zlyhané", "Zopakovat nezdařené"),
    ("Remove failed", "Odstrániť zlyhané", "Odstranit nezdařené"),
    ("Export completed", "Export bol dokončený", "Export byl dokončen"),
    ("Export canceled", "Export bol zrušený", "Export byl zrušen"),
    ("Originals processed", "Spracované originály", "Zpracované originály"),
    ("Output images created", "Vytvorené výstupné obrázky", "Vytvořené výstupní obrázky"),
    ("Failed originals", "Zlyhané originály", "Nezdařené originály"),
    ("Open export folder", "Otvoriť exportný priečinok", "Otevřít složku exportu"),
    ("Missing export folder", "Chýbajúci exportný priečinok", "Chybějící složka exportu"),
    ("Preview detail unavailable", "Detail náhľadu nie je dostupný", "Detail náhledu není dostupný"),
    ("The source ICC color profile could not be converted to sRGB.", "Vstupný farebný profil ICC sa nepodarilo previesť na sRGB.", "Vstupní barevný profil ICC se nepodařilo převést na sRGB."),
    ("The preview edge must be a positive integer.", "Maximálna hrana náhľadu musí byť kladné celé číslo.", "Maximální hrana náhledu musí být kladné celé číslo."),
    ("Only JPEG, PNG and HEIC/HEIF are supported.", "Podporovaný je iba JPEG, PNG a HEIC/HEIF.", "Podporován je pouze JPEG, PNG a HEIC/HEIF."),
    ("Invalid preview detail region.", "Neplatná oblasť detailu náhľadu.", "Neplatná oblast detailu náhledu."),
    ("Detail requires the original photo resolution.", "Detail vyžaduje originálne rozlíšenie fotografie.", "Detail vyžaduje původní rozlišení fotografie."),
    ("Export requires the original photo resolution, not a reduced preview.", "Export vyžaduje pôvodné rozlíšenie fotografie, nie zmenšený náhľad.", "Export vyžaduje původní rozlišení fotografie, nikoli zmenšený náhled."),
    ("The image must have positive dimensions.", "Obrázok musí mať kladné rozmery.", "Obrázek musí mít kladné rozměry."),
    ("The photo is too narrow for this tile count without enlarging it.", "Fotografia je príliš úzka pre zvolený počet dielov bez zväčšenia.", "Fotografie je příliš úzká pro zvolený počet dílů bez zvětšení."),
    ("Mode must be split or expand.", "Režim musí byť split alebo expand.", "Režim musí být split nebo expand."),
    ("Ratio mode must be auto or fixed.", "Režim pomeru musí byť auto alebo fixed.", "Režim poměru musí být auto nebo fixed."),
    ("Placement must be fit or fill.", "Spôsob umiestnenia musí byť fit alebo fill.", "Způsob umístění musí být fit nebo fill."),
    ("Unknown composition grid.", "Neznáma kompozičná mriežka.", "Neznámá kompoziční mřížka."),
    ("Unknown background mode.", "Neznámy režim pozadia.", "Neznámý režim pozadí."),
    ("Background colour must be #RRGGBB.", "Farba pozadia musí byť #RRGGBB.", "Barva pozadí musí být #RRGGBB."),
    ("Unknown HDR export mode.", "Neznámy režim HDR exportu.", "Neznámý režim HDR exportu."),
    ("{name} must be an integer.", "{name} musí byť celé číslo.", "{name} musí být celé číslo."),
    ("{name} must be between {lower} and {upper}.", "{name} musí byť od {lower} do {upper}.", "{name} musí být od {lower} do {upper}."),
    ("The aspect ratio must be a finite number between 3:4 and 16:9.", "Pomer strán musí byť konečné číslo od 3:4 do 16:9.", "Poměr stran musí být konečné číslo od 3:4 do 16:9."),
    ("{name} must be a finite number between -1 and 1.", "{name} musí byť konečné číslo od -1 do 1.", "{name} musí být konečné číslo od -1 do 1."),
    ("Source dimensions must be positive.", "Rozmery zdrojového obrázka musia byť kladné.", "Rozměry zdrojového obrázku musí být kladné."),
    ("Image settings must be a JSON object.", "Nastavenia obrázka musia byť JSON objekt.", "Nastavení obrázku musí být JSON objekt."),
    ("Invalid orientation in legacy settings.", "Neplatná orientácia v staršom formáte nastavení.", "Neplatná orientace ve starším formátu nastavení."),
    ("Invalid aspect ratio in legacy settings.", "Neplatný pomer v staršom formáte nastavení.", "Neplatný poměr ve starším formátu nastavení."),
    ("Unknown settings: {fields}.", "Neznáme nastavenia: {fields}.", "Neznámá nastavení: {fields}."),
    ("The image path must be non-empty text.", "Cesta obrázka musí byť neprázdny text.", "Cesta obrázku musí být neprázdný text."),
    ("The image check state must be a boolean.", "Označenie obrázka musí byť logická hodnota.", "Označení obrázku musí být logická hodnota."),
    ("The preview state must be a boolean.", "Stav náhľadu obrázka musí byť logická hodnota.", "Stav náhledu obrázku musí být logická hodnota."),
    ("Failure reason must be nonempty text.", "Dôvod zlyhania musí byť neprázdny text.", "Důvod selhání musí být neprázdný text."),
    ("Unknown failed processing stage.", "Neznáma fáza zlyhaného spracovania.", "Neznámá fáze nezdařeného zpracování."),
    ("Image records must be JSON objects.", "Záznam obrázka musí byť JSON objekt.", "Záznam obrázku musí být JSON objekt."),
    ("The image record contains unknown fields.", "Záznam obrázka obsahuje neznáme položky.", "Záznam obrázku obsahuje neznámé položky."),
    ("The session file exceeds 5 MB.", "Súbor relácie presahuje 5 MB.", "Soubor relace přesahuje 5 MB."),
    ("The session schema version is missing.", "Chýba verzia schémy relácie.", "Chybí verze schématu relace."),
    ("Unsupported session schema version.", "Nepodporovaná verzia schémy relácie.", "Nepodporovaná verze schématu relace."),
    ("Invalid photo list.", "Neplatný zoznam fotografií.", "Neplatný seznam fotografií."),
    ("The session contains duplicate photos.", "Relácia obsahuje duplicitné fotografie.", "Relace obsahuje duplicitní fotografie."),
    ("Invalid photo selection.", "Neplatný výber fotografie.", "Neplatný výběr fotografie."),
    ("Invalid export folder.", "Neplatný exportný priečinok.", "Neplatná složka exportu."),
    ("Cannot load session: {path}\n{error}", "Reláciu nemožno načítať: {path}\n{error}", "Relaci nelze načíst: {path}\n{error}"),
    ("Cannot save session: {path}\n{error}", "Reláciu nemožno uložiť: {path}\n{error}", "Relaci nelze uložit: {path}\n{error}"),
    ("The session can contain at most 10,000 photos.", "Relácia môže obsahovať najviac 10 000 fotografií.", "Relace může obsahovat nejvýše 10 000 fotografií."),
    ("Cannot safely back up the invalid session: {error}", "Poškodenú reláciu nemožno bezpečne zálohovať: {error}", "Poškozenou relaci nelze bezpečně zálohovat: {error}"),
    ("The folder does not exist. Choose another export folder in Preferences.", "Priečinok neexistuje. V nastaveniach vyberte iný exportný priečinok.", "Složka neexistuje. V nastavení vyberte jinou složku exportu."),
    ("JPEG supports at most {limit} pixels per tile edge.", "JPEG podporuje najviac {limit} pixelov na jednej hrane dielu.", "JPEG podporuje nejvýše {limit} pixelů na jedné hraně dílu."),
    ("HDR export did not create a complete set of tiles.", "HDR export nevytvoril úplnú sériu dielov.", "HDR export nevytvořil úplnou sérii dílů."),
    ("Export did not create a complete set of tiles.", "Export nevytvoril úplnú sériu dielov.", "Export nevytvořil úplnou sérii dílů."),
    ("The memory estimate must be a non-negative integer in bytes.", "Odhad pamäte musí byť nezáporné celé číslo v bajtoch.", "Odhad paměti musí být nezáporné celé číslo v bajtech."),
    ("The operation name must be non-empty text.", "Názov operácie musí byť neprázdny text.", "Název operace musí být neprázdný text."),
    ("Ready", "Pripravené", "Připraveno"),
    ("Select for export", "Označiť na export", "Označit k exportu"),
    ("Could not remove incomplete export “{name}”: {error}", "Neúplný export „{name}“ sa nepodarilo odstrániť: {error}", "Neúplný export „{name}“ se nepodařilo odstranit: {error}"),
    ("Error: {name}", "Chyba: {name}", "Chyba: {name}"),
    ("JPEG supports at most {limit} pixels per tile edge. Choose more tiles or another aspect ratio.", "JPEG podporuje najviac {limit} pixelov na jednej hrane dielu. Zvoľte viac dielov alebo iný pomer strán.", "JPEG podporuje nejvýše {limit} pixelů na jedné hraně dílu. Zvolte více dílů nebo jiný poměr stran."),
    ("Operation “{operation}” needs approximately {required} MiB of memory; {available} MiB is available. Close other applications or process a smaller image.", "Operácia „{operation}“ vyžaduje približne {required} MiB pamäte, dostupné je {available} MiB. Zatvorte iné aplikácie alebo spracujte menší obrázok.", "Operace „{operation}“ vyžaduje přibližně {required} MiB paměti, dostupných je {available} MiB. Zavřete jiné aplikace nebo zpracujte menší obrázek."),
    ("Incomplete HEIF structure.", "Neúplná štruktúra HEIF.", "Neúplná struktura HEIF."),
    ("Invalid HEIF item size.", "Neplatná veľkosť položky HEIF.", "Neplatná velikost položky HEIF."),
    ("Invalid HEIF structure.", "Neplatná štruktúra HEIF.", "Neplatná struktura HEIF."),
    ("Incomplete HDR HEIC metadata.", "Neúplné metadáta HDR HEIC.", "Neúplná metadata HDR HEIC."),
    ("HEIC must contain exactly one metadata table.", "HEIC musí mať práve jednu tabuľku metadát.", "HEIC musí mít právě jednu tabulku metadat."),
    ("HDR HEIC cannot use external image data.", "HDR HEIC nesmie používať externé obrazové dáta.", "HDR HEIC nesmí používat externí obrazová data."),
    ("HDR HEIC has no unambiguous ISO gain map associated with the photo.", "HDR HEIC nemá jednoznačnú ISO gain mapu priradenú k fotografii.", "HDR HEIC nemá jednoznačnou ISO gain mapu přiřazenou k fotografii."),
    ("Invalid ISO HDR gain map references.", "Neplatné referencie ISO HDR gain mapy.", "Neplatné reference ISO HDR gain mapy."),
    ("The ISO HDR gain map has no metadata.", "ISO HDR gain mape chýbajú metadáta.", "ISO HDR gain mapě chybí metadata."),
    ("Unsupported ISO HDR metadata storage.", "Nepodporované uloženie ISO HDR metadát.", "Nepodporované uložení ISO HDR metadat."),
    ("Corrupt ISO HDR metadata.", "Poškodené ISO HDR metadáta.", "Poškozená ISO HDR metadata."),
    ("Unsupported tmap HDR metadata version.", "Nepodporovaná verzia tmap HDR metadát.", "Nepodporovaná verze tmap HDR metadat."),
    ("Invalid ISO HDR color profile.", "Neplatný farebný profil ISO HDR.", "Neplatný barevný profil ISO HDR."),
    ("Unsupported ISO 21496 HDR metadata version.", "Nepodporovaná verzia ISO 21496 HDR metadát.", "Nepodporovaná verze ISO 21496 HDR metadat."),
    ("ISO HDR metadata contains a zero denominator.", "ISO HDR metadáta obsahujú nulový menovateľ.", "ISO HDR metadata obsahují nulový jmenovatel."),
    ("Invalid ISO HDR gain map range or gamma.", "Neplatný rozsah alebo gamma ISO HDR gain mapy.", "Neplatný rozsah nebo gama ISO HDR gain mapy."),
    ("ISO HDR luminance range exceeds 10,000 cd/m².", "ISO HDR jasový rozsah prekračuje 10000 cd/m².", "ISO HDR jasový rozsah překračuje 10000 cd/m²."),
    ("HDR has an unsupported or corrupt ICC color profile.", "HDR má nepodporovaný alebo poškodený farebný profil ICC.", "HDR má nepodporovaný nebo poškozený barevný profil ICC."),
    ("Corrupt HDR color profile table.", "Poškodená tabuľka farebného profilu HDR.", "Poškozená tabulka barevného profilu HDR."),
    ("Corrupt HDR color profile transfer curve.", "Poškodená prenosová krivka farebného profilu HDR.", "Poškozená přenosová křivka barevného profilu HDR."),
    ("The HDR color profile must contain RGB transfer curves.", "HDR farebný profil musí obsahovať RGB prenosové krivky.", "HDR barevný profil musí obsahovat RGB přenosové křivky."),
    ("The HDR base color profile could not be converted to sRGB.", "Farebný profil HDR bázy sa nepodarilo previesť do sRGB.", "Barevný profil HDR báze se nepodařilo převést do sRGB."),
    ("The HDR gain map does not specify its output color gamut.", "HDR gain mapa neurčuje svoj výstupný farebný gamut.", "HDR gain mapa neurčuje svůj výstupní barevný gamut."),
    ("The Apple HDR gain map is missing exposure metadata.", "Apple HDR gain mape chýbajú expozičné metadáta.", "Apple HDR gain mapě chybí expoziční metadata."),
    ("The Apple HDR gain map has no valid Apple MakerNote metadata.", "Apple HDR gain mapa nemá platné Apple MakerNote metadáta.", "Apple HDR gain mapa nemá platná Apple MakerNote metadata."),
    ("Unknown Apple HDR metadata byte order.", "Neznáme poradie bajtov Apple HDR metadát.", "Neznámé pořadí bajtů Apple HDR metadat."),
    ("Corrupt Apple HDR metadata.", "Poškodené Apple HDR metadáta.", "Poškozená Apple HDR metadata."),
    ("The Apple HDR gain map is missing valid 33/48 luminance range values.", "Apple HDR gain mape chýbajú platné hodnoty 33/48 pre jasový rozsah.", "Apple HDR gain mapě chybí platné hodnoty 33/48 pro jasový rozsah."),
    ("The Apple HDR gain map has an invalid luminance range.", "Apple HDR gain mapa má neplatný jasový rozsah.", "Apple HDR gain mapa má neplatný jasový rozsah."),
    ("Apple HDR requires one gain map and an 8-bit SDR base.", "Apple HDR vyžaduje jednu gain mapu a 8-bitovú SDR bázu.", "Apple HDR vyžaduje jednu gain mapu a 8bitovou SDR bázi."),
    ("The Apple HDR gain map orientation does not match the photo.", "Orientácia Apple HDR gain mapy nezodpovedá fotografii.", "Orientace Apple HDR gain mapy neodpovídá fotografii."),
    ("The Apple HDR base has no ICC color profile.", "Apple HDR báze chýba farebný profil ICC.", "Apple HDR bázi chybí barevný profil ICC."),
    ("The HDR HEIC decoder did not provide high-bit-depth data.", "HDR HEIC dekóder neposkytol vysokobitové dáta.", "HDR HEIC dekodér neposkytl vysokobitová data."),
    ("This HEIC contains an ISO HDR gain map that the available codec cannot process. HDR was not replaced with an 8-bit base.", "Tento HEIC obsahuje ISO HDR gain mapu, ktorú dostupný kodek nevie spracovať. HDR sa nahradením 8-bitovou bázou nestratilo.", "Tento HEIC obsahuje ISO HDR gain mapu, kterou dostupný kodek neumí zpracovat. HDR nebylo nahrazeno 8bitovou bází."),
    ("ISO HDR HEIC requires verified support for its color profile.", "ISO HDR HEIC vyžaduje overenú podporu jeho farebného profilu.", "ISO HDR HEIC vyžaduje ověřenou podporu svého barevného profilu."),
    ("An SDR photo cannot be exported as HDR.", "SDR fotografiu nie je možné exportovať ako HDR.", "SDR fotografii nelze exportovat jako HDR."),
    ("Decoded HDR data contains invalid values.", "Dekódované HDR dáta obsahujú neplatné hodnoty.", "Dekódovaná HDR data obsahují neplatné hodnoty."),
    ("The codec did not create a valid HDR JPEG with a gain map.", "Kodek nevytvoril platný HDR JPEG s gain mapou.", "Kodek nevytvořil platný HDR JPEG s gain mapou."),
    ("HDR HEIC has unsupported color primaries.", "HDR HEIC má nepodporované farebné primárne zložky.", "HDR HEIC má nepodporované barevné primární složky."),
    ("HDR HEIC must contain image data with at least 10 bits per channel.", "HDR HEIC musí obsahovať aspoň 10-bitové obrazové dáta.", "HDR HEIC musí obsahovat alespoň 10bitová obrazová data."),
    ("Unknown HEIC HDR gain map", "Neznáma HEIC HDR gain mapa", "Neznámá HEIC HDR gain mapa"),
    ("This HDR gain map type is not supported yet.", "Tento typ HDR gain mapy zatiaľ nie je podporovaný.", "Tento typ HDR gain mapy zatím není podporován."),
    ("Invalid JPEG HDR gain map", "Neplatná JPEG HDR gain mapa", "Neplatná JPEG HDR gain mapa"),
    ("The JPEG contains HDR metadata, but no valid HDR gain map could be decoded.", "JPEG obsahuje HDR metadáta, ale platnú HDR gain mapu sa nepodarilo dekódovať.", "JPEG obsahuje HDR metadata, ale platnou HDR gain mapu se nepodařilo dekódovat."),
    ("Reading HDR metadata", "Čítanie HDR metadát", "Čtení HDR metadat"),
    ("Reading JPEG HDR metadata", "Čítanie JPEG HDR metadát", "Čtení JPEG HDR metadat"),
    ("Preferences recovery", "Obnova nastavení aplikácie", "Obnova nastavení aplikace"),
    ("{error}\n\nThe original preferences were preserved in:\n{backup}\nThe application will open first-run setup.", "{error}\n\nPôvodné nastavenia zostali zachované v:\n{backup}\nAplikácia otvorí úvodné nastavenie.", "{error}\n\nPůvodní nastavení zůstalo zachováno v:\n{backup}\nAplikace otevře úvodní nastavení."),
    ("Cannot create the default export folder:\n{error}", "Predvolený exportný priečinok nemožno vytvoriť:\n{error}", "Výchozí složku exportu nelze vytvořit:\n{error}"),
    ("Session folder", "Priečinok relácie", "Složka relace"),
    ("Windows did not provide a Documents folder path.", "Windows neposkytol cestu k priečinku Documents.", "Windows neposkytl cestu ke složce Documents."),
    ("Cannot open session", "Reláciu nemožno otvoriť", "Relaci nelze otevřít"),
    ("Session recovery", "Obnova relácie", "Obnova relace"),
    ("{error}\n\nThe original data were preserved in:\n{backup}\nThe application will open a new empty session.", "{error}\n\nPôvodné dáta zostali zachované v:\n{backup}\nAplikácia otvorí novú prázdnu reláciu.", "{error}\n\nPůvodní data zůstala zachována v:\n{backup}\nAplikace otevře novou prázdnou relaci."),
    ("Photos: {count}  ·  checked: {checked}  ·  imported: {imported}  ·  ready: {prepared}  ·  exported: {exported}  ·  failed: {failed}", "Fotografie: {count}  ·  označené: {checked}  ·  importované: {imported}  ·  pripravené: {prepared}  ·  exportované: {exported}  ·  zlyhané: {failed}", "Fotografie: {count}  ·  označené: {checked}  ·  importované: {imported}  ·  připravené: {prepared}  ·  exportované: {exported}  ·  nezdařené: {failed}"),
    ("Export folder does not exist: {directory}. Choose another folder in Preferences.", "Exportný priečinok neexistuje: {directory}. Vyberte iný v nastaveniach aplikácie.", "Složka exportu neexistuje: {directory}. Vyberte jinou v nastavení aplikace."),
    ("{prefix}. Output images: {count}.", "{prefix}. Výstupné obrázky: {count}.", "{prefix}. Výstupní obrázky: {count}."),
    ("Loading {count} photos…", "Načítavam {count} fotografií…", "Načítám {count} fotografií…"),
    ("Unsupported files: {files}", "Nepodporované súbory: {files}", "Nepodporované soubory: {files}"),
    ("Unsupported files: {names}", "Nepodporované súbory: {names}", "Nepodporované soubory: {names}"),
    ("Settings could not be saved. Changes are kept in memory only. {error}", "Nastavenia sa nepodarilo uložiť. Zmeny sú iba v pamäti. {error}", "Nastavení se nepodařilo uložit. Změny jsou pouze v paměti. {error}"),
    ("Export failed: {error}", "Export zlyhal: {error}", "Export selhal: {error}"),
    ("Preview {name}: {error}", "Náhľad {name}: {error}", "Náhled {name}: {error}"),
    ("Cannot load preferences: {path}\n{error}", "Nastavenia aplikácie nemožno načítať: {path}\n{error}", "Nastavení aplikace nelze načíst: {path}\n{error}"),
    ("Cannot save preferences: {path}\n{error}", "Nastavenia aplikácie nemožno uložiť: {path}\n{error}", "Nastavení aplikace nelze uložit: {path}\n{error}"),
    ("Cannot back up invalid preferences: {error}", "Neplatné nastavenia aplikácie nemožno zálohovať: {error}", "Neplatné nastavení aplikace nelze zálohovat: {error}"),
    ("The export folder must be a non-empty absolute path.", "Exportný priečinok musí mať neprázdnu absolútnu cestu.", "Složka exportu musí mít neprázdnou absolutní cestu."),
    ("The export folder must be an absolute path.", "Exportný priečinok musí mať absolútnu cestu.", "Složka exportu musí mít absolutní cestu."),
    ("Unsupported appearance preference.", "Nepodporovaná voľba vzhľadu.", "Nepodporovaná volba vzhledu."),
    ("Unsupported interface language.", "Nepodporovaný jazyk rozhrania.", "Nepodporovaný jazyk rozhraní."),
    ("The onboarding flag must be a boolean.", "Príznak úvodného nastavenia musí byť logická hodnota.", "Příznak úvodního nastavení musí být logická hodnota."),
    ("Duplicate preferences field: {field}", "Duplicitná položka nastavení aplikácie: {field}", "Duplicitní položka nastavení aplikace: {field}"),
    ("The preferences file exceeds 64 KiB.", "Súbor nastavení aplikácie presahuje 64 KiB.", "Soubor nastavení aplikace přesahuje 64 KiB."),
    ("The preferences fields are missing or unrecognized.", "Položky nastavení aplikácie chýbajú alebo sú neznáme.", "Položky nastavení aplikace chybí nebo jsou neznámé."),
    ("Unsupported preferences schema version.", "Nepodporovaná verzia schémy nastavení aplikácie.", "Nepodporovaná verze schématu nastavení aplikace."),
    ("Back up the invalid preferences before saving new settings.", "Pred uložením nových nastavení zálohujte neplatné nastavenia aplikácie.", "Před uložením nového nastavení zálohujte neplatné nastavení aplikace."),
    ("Converting HDR to SDR", "Prevádzanie HDR do SDR", "Převádění HDR do SDR"),
    ("Decoding HDR HEIC", "Dekódovanie HDR HEIC", "Dekódování HDR HEIC"),
    ("Reconstructing ISO HDR HEIC", "Rekonštrukcia ISO HDR HEIC", "Rekonstrukce ISO HDR HEIC"),
    ("Creating a linear HDR background", "Vytvorenie lineárneho HDR pozadia", "Vytvoření lineárního HDR pozadí"),
    ("Encoding HDR export", "Kódovanie HDR exportu", "Kódování HDR exportu"),
    ("Decoding an HDR photo", "Dekódovanie HDR fotografie", "Dekódování HDR fotografie"),
    ("Decoding the SDR preview of HDR HEIC", "Dekódovanie SDR náhľadu HDR HEIC", "Dekódování SDR náhledu HDR HEIC"),
    ("Creating an HDR output tile", "Vytvorenie HDR exportného dielu", "Vytvoření HDR výstupního dílu"),
    ("The Apple HDR gain map version is unsupported or missing.", "Nepodporovaná alebo chýbajúca verzia Apple HDR gain mapy.", "Nepodporovaná nebo chybějící verze Apple HDR gain mapy."),
    ("The ISO HDR gain map requires a supported 8-bit SDR base.", "ISO HDR gain mapa vyžaduje podporovanú 8-bitovú SDR bázu.", "ISO HDR gain mapa vyžaduje podporovanou 8bitovou SDR bázi."),
    ("The HDR export contains invalid values or exceeds the 10,000 cd/m² luminance limit.", "HDR export obsahuje neplatné hodnoty alebo prekračuje jasový limit 10000 cd/m².", "HDR export obsahuje neplatné hodnoty nebo překračuje jasový limit 10000 cd/m²."),
    ("Invalid Apple HDR gain map XML metadata.", "Neplatné XML metadáta Apple HDR gain mapy.", "Neplatná XML metadata Apple HDR gain mapy."),
    ("Corrupt Apple HDR gain map XML metadata.", "Poškodené XML metadáta Apple HDR gain mapy.", "Poškozená XML metadata Apple HDR gain mapy."),
    ("The ISO HEIC HDR base has no supported PQ/HLG color profile.", "HDR báza ISO HEIC nemá podporovaný PQ/HLG farebný profil.", "HDR báze ISO HEIC nemá podporovaný PQ/HLG barevný profil."),
    ("The ISO HDR HEIC SDR base has no ICC color profile.", "SDR báze ISO HDR HEIC chýba farebný profil ICC.", "SDR bázi ISO HDR HEIC chybí barevný profil ICC."),
    ("The ISO HDR gain map orientation does not match the photo.", "Orientácia ISO HDR gain mapy nezodpovedá fotografii.", "Orientace ISO HDR gain mapy neodpovídá fotografii."),
    ("The Apple HDR gain map has no valid HDRGainMapHeadroom.", "Apple HDR gain mape chýba platný HDRGainMapHeadroom.", "Apple HDR gain mapě chybí platný HDRGainMapHeadroom."),
    ("Apple HDR requires one unambiguous gain map.", "Apple HDR vyžaduje jednu jednoznačnú gain mapu.", "Apple HDR vyžaduje jednu jednoznačnou gain mapu."),
    ("The ISO HDR gain map does not specify a supported output color gamut.", "ISO HDR gain mapa neurčuje podporovaný výstupný farebný gamut.", "ISO HDR gain mapa neurčuje podporovaný výstupní barevný gamut."),
    ("The available HDR JPEG codec supports at most 8192 pixels per tile edge. Choose more tiles or another aspect ratio.", "Dostupný HDR JPEG kodek podporuje najviac 8192 pixelov na jednej hrane dielu. Zvoľte viac dielov alebo iný pomer strán.", "Dostupný HDR JPEG kodek podporuje nejvýše 8192 pixelů na jedné hraně dílu. Zvolte více dílů nebo jiný poměr stran."),
    ("HDR JPEG could not be encoded: {error}", "HDR JPEG sa nepodarilo zakódovať: {error}", "HDR JPEG se nepodařilo zakódovat: {error}"),
    # Keep this fallback last: more specific diagnostics must match first.
    ("{name}: {error}", "{name}: {error}", "{name}: {error}"),
)

CATALOG: dict[str, tuple[str, str, str]] = {row[0]: row for row in _ROWS}
_ALIASES: dict[str, str] = {}
for _row in _ROWS:
    for _text in _row:
        _ALIASES.setdefault(_text, _row[0])


def _template_pattern(template: str) -> re.Pattern[str] | None:
    parts: list[str] = []
    fields: set[str] = set()
    for literal, field_name, _format_spec, _conversion in Formatter().parse(template):
        parts.append(re.escape(literal))
        if field_name is not None:
            if not field_name.isidentifier():
                return None
            if field_name in fields:
                parts.append(f"(?P={field_name})")
            else:
                parts.append(f"(?P<{field_name}>.*?)")
                fields.add(field_name)
    return re.compile("".join(parts), re.DOTALL) if fields else None


_TEMPLATES = [
    (key, pattern)
    for key, row in CATALOG.items()
    for template in row
    if (pattern := _template_pattern(template)) is not None
]


def set_language(language: str) -> None:
    global _language
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported interface language: {language}")
    _language = language


def get_language() -> str:
    return _language


def tr(source: str, **values: Any) -> str:
    return _translate(source, values, depth=0)


def _translate(source: str, values: dict[str, Any], *, depth: int) -> str:
    # Saved error messages can contain arbitrary nested filename/operation
    # prefixes. Preserve the remainder verbatim once the bounded depth is hit.
    if depth >= _MAX_NESTED_TRANSLATIONS:
        return source.format(**values) if values else source
    for field in ("error", "operation", "prefix"):
        if isinstance(values.get(field), str):
            values[field] = _translate(values[field], {}, depth=depth + 1)
    key = _ALIASES.get(source, source)
    row = CATALOG.get(key)
    if row is None:
        for template_key, pattern in _TEMPLATES:
            match = pattern.fullmatch(source)
            if match is not None:
                row = CATALOG[template_key]
                template = row[LANGUAGES.index(_language)]
                extracted = match.groupdict()
                for field in ("error", "operation", "prefix"):
                    if field in extracted:
                        extracted[field] = _translate(extracted[field], {}, depth=depth + 1)
                # Captured values already contain any formatting (e.g. 1.250).
                for literal, name, spec, conversion in Formatter().parse(template):
                    if name is not None and (spec or conversion):
                        template = template.replace("{" + name + ("!" + conversion if conversion else "") + (":" + spec if spec else "") + "}", "{" + name + "}")
                return template.format(**{**extracted, **values})
    if row is None and "\n" in source:
        return "\n".join(_translate(line, values, depth=depth + 1) for line in source.split("\n"))
    translated = row[LANGUAGES.index(_language)] if row is not None else source
    return translated.format(**values) if values else translated


def translate_widget_tree(root: Any) -> None:
    """Retranslate known static text without changing filenames or user data.

    Store the canonical source on each QObject so repeated language changes
    always start from the same text. Dynamic fields are translated by callers.
    """
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import QComboBox

    properties = ("text", "title", "windowTitle", "toolTip", "statusTip", "placeholderText")
    for obj in [root, *root.findChildren(QObject)]:
        for name in properties:
            getter = getattr(obj, name, None)
            setter = getattr(obj, "set" + name[0].upper() + name[1:], None)
            if not callable(getter) or not callable(setter):
                continue
            try:
                current = getter()
            except TypeError:
                continue
            if not isinstance(current, str):
                continue
            source_property = f"_i18n_source_{name}"
            last_property = f"_i18n_last_{name}"
            source = obj.property(source_property)
            if source is None or current != obj.property(last_property):
                source = _ALIASES.get(current)
                if source is None:
                    continue
                obj.setProperty(source_property, source)
            translated = tr(source)
            setter(translated)
            obj.setProperty(last_property, translated)
        if isinstance(obj, QComboBox):
            for index in range(obj.count()):
                current = obj.itemText(index)
                source_property = f"_i18n_combo_source_{index}"
                last_property = f"_i18n_combo_last_{index}"
                source = obj.property(source_property)
                if source is None or current != obj.property(last_property):
                    source = _ALIASES.get(current)
                    if source is None:
                        continue
                    obj.setProperty(source_property, source)
                translated = tr(source)
                obj.setItemText(index, translated)
                obj.setProperty(last_property, translated)
