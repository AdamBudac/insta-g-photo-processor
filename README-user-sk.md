# Návod na použitie — Insta G Photo Processor

Pripravte panorámu ako nadväzujúce diely carouselu alebo doplňte pozadie okolo portrétu. Spracovanie prebieha vo vašom počítači. Aplikácia nevyžaduje účet, neposiela fotografie na server a nemení originálne súbory.

## Stiahnutie a spustenie vo Windows

1. V repozitári projektu na GitHube otvorte **Releases** a v časti **Assets** najnovšieho vydania stiahnite **InstaGPhotoProcessor.exe**. Archívy **Source code** sú určené na vývoj a na používanie aplikácie ich nepotrebujete.
2. EXE uložte do ľubovoľného priečinka a spustite dvojklikom. Netreba inštalátor, Python ani samostatný HEIC kodek. Použite Windows x64; overeným prostredím je Windows 11 x64.
3. Pred otvorením novej verzie zatvorte staršiu, pretože používajú rovnakú uloženú reláciu. Prvé spustenie one-file aplikácie môže chvíľu trvať, kým sa pribalené súčasti rozbalia do dočasného priečinka.

Nastavenia sa ukladajú samostatne v priečinku Windows Documents. Presunutím alebo výmenou EXE ich neodstránite.

## Prvé spustenie a nastavenia aplikácie

Pri prvom spustení vyberte **predvolený exportný priečinok**, **vzhľad** a **jazyk**. **OK** potvrdí vaše voľby; **Použiť predvolené / Preskočiť** dokončí úvodné nastavenie s predvolenými hodnotami. Predvolený jazyk je angličtina a vzhľad sa riadi systémom. Predvolený priečinok `Export` je v dátovom priečinku aplikácie v skutočnom priečinku Windows Documents.

Voľby neskôr zmeníte cez **Nastavenia aplikácie**. Dostupná je angličtina, slovenčina a čeština. Vzhľad môže byť svetlý, tmavý alebo podľa Windows; systémová voľba reaguje aj na neskoršiu zmenu vzhľadu Windows. **Zrušiť** zachová pôvodné nastavenia.

Exporty sa ukladajú do nastaveného priečinka. Ak ho vymažete alebo presuniete, vyberte existujúci cieľ v nastaveniach. Aplikácia problém oznámi a vymazaný vlastný priečinok potichu nevytvorí znova.

## Prvý export

1. Kliknite na **Pridať fotografie** alebo presuňte JPEG/JPG, PNG či HEIC/HEIF do ľavej knižnice. Import fotografiu automaticky neotvorí.
2. Kliknite na fotografiu a počkajte na dokončenie aktuálneho náhľadu. Fotografia získa žltý stav **Pripravené**.
3. Voliteľný výrez upravte priamo v strednom náhľade ťahaním úchytov na hranách a rohoch fotografie. Zvoľte **Carousel / Rozdelenie** pre viac nadväzujúcich dielov alebo **Doplniť plátno** pre jeden obrázok s okrajmi. Nastavte počet dielov a pomer strán.
4. Upravte polohu a pozadie. Skontrolujte biely rám výstupu a rozmery v pravom paneli.
5. **Exportovať všetky** spracuje všetky pripravené a exportované fotografie. Pre menší výber ich označte checkboxmi a zvoľte **Exportovať vybrané**. Modré importované sa vždy preskočia.
6. Počkajte na súhrn exportu. Samostatne uvádza počet pôvodných fotografií, výstupných súborov a chýb.

## Farby knižnice a výber

| Stav | Význam |
| --- | --- |
| Modré — Importované | Fotografia ešte nebola úspešne zobrazená v aktuálnom náhľade. Pred exportom ju otvorte. |
| Žlté — Pripravené | Aktuálny náhľad vybratej fotografie sa úspešne zobrazil. Fotografia je oprávnená na export. |
| Zelené — Exportované | Všetky diely sa úspešne uložili s aktuálnymi nastaveniami fotografie. |
| Červené — Zlyhané | Zlyhal import, náhľad alebo export. Dôvod nájdete v tooltipe alebo stavovom riadku; odstráňte príčinu a skúste to znova. |

Kliknutie na riadok otvorí náhľad. Checkbox označuje fotografiu pre hromadné akcie nezávisle od aktívneho náhľadu. Samotné zaškrtnutie fotografiu nepripraví, nemení nastavenia ani platný zelený stav.

Úprava kompozície zneplatní zelený stav. Chybný alebo zastaraný náhľad nemôže nastaviť pripravenosť. Pri prechode myšou zostáva rozpoznateľná farba daného stavu.

**Odstrániť vybrané**, **Odstrániť všetky**, **Odstrániť exportované** a ikona koša odstraňujú iba položky knižnice. Nemažú originály ani hotové exporty. **Zopakovať zlyhané** skúsi neúspešné fotografie znova po odstránení príčiny problému.

## Vstupný výrez

V strednom náhľade ťahajte úchyty na hranách a rohoch fotografie. Ťahaním dovnútra plochu odrežete, smerom von môžete vrátiť skoršie odrezané pixely až po pôvodný okraj fotografie. Neotvára sa samostatný dialóg a netreba zadávať pixelové súradnice. Ľavé ťahanie vnútri fotografie naďalej mení jej polohu na výstupnom plátne.

Pri ťahaní zostáva kamera stabilná a zmeny sa automaticky ukladajú. **Escape** vráti výrez zo začiatku gesta. Po uvoľnení úchytu zostáva v prispôsobenom zobrazení celý pôvodný originál aj výstupné plátno. Odrezané časti sú viditeľné s tmavým prekrytím, takže hranu môžete jedným ťahom vrátiť až na pôvodný okraj fotografie. Výrez môže mať ľubovoľný pomer; zostáva vnútri originálu a má aspoň 1 × 1 px.

**Obnoviť celý záber (Reset crop)** priamo pod tlačidlom **Vycentrovať obrázok** v pravom paneli vráti celú fotografiu. Skutočná zmena výrezu zneplatní predchádzajúci zelený exportný stav. Zdrojový súbor zostáva nezmenený, takže odrezané časti možno vždy vrátiť.

Výrez sa stáva vstupom pre rozdelenie, doplnenie okrajov, polohu aj pozadie bez zmeny mierky pixelov. Aj blur pozadie sa odvodzuje iba z neho. Stmavený originál mimo výrezu slúži na orientáciu v náhľade. **Zachované** vždy porovnáva viditeľnú plochu s celým pôvodným originálom: výrez 800 × 400 px z fotografie 1000 × 500 px zachová **64 %**, aj pri Fit / Padding. Ďalší Fill / Crop môže podiel ešte znížiť.

## Carousel a doplnenie plátna

Carousel podporuje **2–20 dielov** zľava doprava. Diely majú rovnaké rozmery a tvoria jednu nadväzujúcu kompozíciu. Nová fotografia začína s **Fill / Crop**. Obnovená fotografia zachová uložené nastavenia.

**Automatický pomer** vypočíta pomer dielu zo šírky a výšky zvoleného vstupného výrezu a počtu dielov v rozsahu **3:4 až 16:9**. Bez výrezu používa celý originál. Predvoľby sú **16:9, 3:2, 4:3, 5:4, 1:1, 4:5 a 3:4**. Posuvník umožňuje medzihodnoty; jeho posun vypne automatický pomer. Pomer znamená šírku delenú výškou, bez samostatného prepínača orientácie.

**Fit / Padding** zachová celý zvolený vstup v pôvodnej mierke pixelov a doplní chýbajúcu plochu pozadím. **Fill / Crop** môže odstrániť ďalšiu časť tohto vstupu. Tlmený obraz za bielym rámom ukazuje plochu odstránenú režimom Fill. Vstupný výrez môžete zväčšiť ťahaním úchytov smerom von alebo tlačidlom Obnoviť celý záber.

**Doplniť plátno** vytvára jeden obrázok a vždy používa Fit / Padding. Zachová celý zvolený vstup a pridá okraje po bokoch alebo hore a dole.

Panoráma 6000 × 2000 px pri troch štvorcových dieloch vytvorí tri súbory 2000 × 2000 px. Popredie sa neprepočítava na pevné rozlíšenie Instagramu.

## Poloha, priblíženie a kompozícia

Použite posuvníky **Vodorovne** a **Zvislo** alebo fotografiu v náhľade ťahajte **ľavým tlačidlom myši**. Ťahanie mení rovnakú polohu ako export. **Vycentrovať obrázok** alebo **ľavý dvojklik** vynuluje oba posuny fotografie a zachová priblíženie. Na osi bez voľného pozadia alebo presahu už fotografia nemá kam pokračovať.

**Pravým tlačidlom myši** ťaháte iba pohľad na priblížený obrázok. Rovnako funguje stredné tlačidlo alebo Space + ľavé ťahanie; Escape posúvanie ukončí. **Pravý dvojklik** obnoví **prispôsobené zobrazenie (Fit view)**: 100 % priblíženie a vycentrovaný pohľad na celý pôvodný originál aj plátno. Pravé ťahanie ani pravý dvojklik nemenia polohu fotografie, exportný stav ani uložené nastavenia.

**Priblíženie náhľadu** je **100–1000 % vzhľadom na prispôsobené zobrazenie**. Návrat na 100 % automaticky vycentruje celý pôvodný originál aj plátno a odrezané časti zostávajú stmavené. Priblíženie nemení export. Pri pohybe sa fotografia okamžite kreslí z cache. Dostupný detail popredia sa pohybuje spolu s fotografiou a aplikácia na pozadí dopĺňa aktuálnu viditeľnú oblasť.

Najskôr sa zobrazí malý náhľad do 2048 px. Aktívny originál sa potom načíta na pozadí, už pri 100 % priblížení, ak je dostupná pamäť. Viditeľný **detail z originálu** sa prispôsobuje veľkosti panela a škálovaniu displeja vrátane monitorov s vysokým rozlíšením; nemá pevný limit 2048 px. Detail sa aktualizuje aj počas ťahania, zoomovania alebo zmeny polohy a pomeru strán.

Stav pod obrázkom rozlišuje načítavanie, natívny detail a zmenšený náhľad s dôvodom. Pre náhľad sa uchováva iba jeden plný originál; pamäťové nároky závisia od fotografie, viditeľnej oblasti a dostupnej RAM. Prvé dekódovanie veľkého zdroja môže chvíľu trvať. Malý náhľad zostáva použiteľný počas načítavania aj pri nedostatku pamäte na natívny detail. Náhľad vždy zobrazuje SDR verziu, aj pri HDR origináli.

**Kompozícia** ponúka v poradí **Žiadna, 2×2, 3×3, φ pre zlatý rez a X pre diagonály**. Tlačidlá aj tooltipy používajú rovnaké písmo a štýl. Sú iba v náhľade a **nikdy sa neexportujú**. Aj hranice dielov sú pomocné značky náhľadu.

## Pozadie a farby

Pre doplnené okraje zvoľte **rozostrenú fotografiu**, **bielu**, **čiernu** alebo **vlastnú farbu**. **Kvapkadlo** umožní kliknúť na farbu v náhľade. K dispozícii je aj päť dominantných farieb získaných z fotografie a vlastný výber farby.

**Rozostrenie pozadia** je 0–1000 px v mierke výstupu. Pri 0 px zostáva fotografické pozadie ostré. Dekoratívne pozadie sa môže pripravovať v zníženom rozlíšení pre úsporu pamäte; originálne popredie zostáva v pôvodnej mierke pixelov.

## Dynamický rozsah a kvalita

Pri rozpoznanom HDR zdroji voľba **Dynamický rozsah** prepína pôvodné HDR alebo konverziu na SDR. Podporované zdroje zahŕňajú 10/12-bitový PQ alebo HLG HEIC s podporovaným farebným označením BT.709, BT.2020 či Display P3, podporované Apple HEIC gain mapy, ISO 21496 HEIC gain mapy a podporované Ultra HDR či Apple HDR JPEG. Neznáme alebo poškodené HDR údaje vyvolajú viditeľnú chybu namiesto nesprávne označeného HDR exportu.

Náhľad vždy zobrazuje SDR verziu. Pri fotografiách s gain mapou používa SDR bázu vytvorenú fotoaparátom a konvertuje jej farebný profil do sRGB. PQ/HLG zdroje prevádza mapovaním jasov a kompresiou svetiel aj farebného gamutu. Náhľad slúži na kompozíciu na bežnom displeji; nezobrazuje HDR jas displeja.

HDR export má pred číslom dielu `_HDR`. Konverzia HDR zdroja na SDR používa `_SDR`. Bežné SDR zdroje zachovávajú štandardný názov bez týchto prípon rozsahu.

Bežný SDR výstup je **JPEG s kvalitou 99**, profilom sRGB a bez pôvodných EXIF či GPS metadát. Kvalita 99 je parameter kodeku, nie percento zachovaných dát. Priehľadnosť PNG sa pri výstupe skladá na podklad. Orientácia vstupu sa rešpektuje.

Zachovanie HDR ponecháva rodinu kontajnera zdroja: HEIC vytvára **10-bitový PQ BT.2020 HEIC**, podporovaný HDR JPEG vytvára **JPEG s ISO gain mapou a SDR bázou**. Pôvodná reprezentácia HDR sa tak môže zmeniť pri zachovaní HDR obrazu a pôvodných rozmerov popredia. Výstupy neobsahujú pôvodné EXIF ani GPS metadáta. Samotná prípona nedokazuje prítomnosť HDR dát.

Pribalený kodek HDR JPEG podporuje najviac **8192 px na každej hrane jedného dielu**. Ide o skutočný limit kodeku. Viac dielov môže zmenšiť príliš veľkú šírku; nadmerná výška vyžaduje iný výrez alebo menší zdroj. Aj HDR HEIC a ostatné veľké exporty podliehajú dostupnej pamäti a limitom kodeku.

## Správanie exportu

Exportovať možno iba **Pripravené** a **Exportované** fotografie. **Exportovať vybrané** pri spustení zachytí oprávnené označené položky. **Exportovať všetky** zachytí všetky oprávnené položky aj bez checkboxu. Aktívny náhľad neurčuje rozsah exportu. Neskoršia zmena checkboxov alebo nastavení ovplyvní ďalšiu dávku.

Fotografia sa spracúva ako celok: úspešné musia byť všetky diely. Pri chybe alebo zrušení sa odstránia neúplné výstupy práve spracúvanej fotografie. Hotové fotografie zo skoršej časti dávky zostanú zachované. Chyba jednej fotografie nezastaví ostatné.

Okno zostáva počas exportu použiteľné. **Zrušiť export** požiada o zastavenie; aktuálne dekódovanie alebo renderovanie sa môže najskôr dokončiť. Súhrn rozlišuje úspešne exportované originály a počet zapísaných súborov.

Existujúce súbory sa neprepisujú; aplikácia vyberie iný voľný názov. Originály sa nikdy neprepisujú. Zelený stav znamená úspešný export celej fotografie s aktuálnymi nastaveniami.

Popredie zostáva v **mierke 1:1**. Fit zväčšuje plátno, Fill vyrezáva časť fotografie. Zaokrúhľovanie na celé pixely môže pridať trochu pozadia alebo upraviť výrez. Rozhodujúce sú rozmery v pravom paneli.

Veľké operácie sa porovnávajú s dostupnou pamäťou. **SDR JPEG** podporuje najviac **65 500 px na hrane dielu**, **HDR JPEG** s pribaleným kodekom **8192 px na hrane dielu**. Pevný limit 80 MP neplatí. Malý náhľad nezaručuje, že originál možno exportovať s dostupnou RAM.

## Uložené údaje a obnova

Nastavenia fotografií vrátane vstupných výrezov, cesty, checkboxy, pripravenosť náhľadu a exportné stavy sa v novej inštalácii automaticky ukladajú do `session.json` v `<Windows Documents>/insta-g-photo-processor`. Globálny vzhľad, jazyk, úvodné nastavenie a predvolený exportný priečinok sú samostatne v `preferences.json`. Presmerovanie Windows Documents sa rešpektuje.

Aktualizácia z Insta G Image Resizer zachová existujúce údaje: ak nový priečinok nemá ani jeden zo stavových súborov a pôvodný `<Windows Documents>/insta-g-image-resizer` aspoň jeden má, aplikácia naďalej používa pôvodný priečinok bez presúvania súborov. Existujúci stav v novom priečinku má prednosť. Nastavený exportný priečinok zostáva zachovaný.

Tieto súbory obsahujú nastavenia a cesty, nie kópie fotografií. Presunutý originál treba znovu importovať z novej cesty. Chyba zápisu sa zobrazí; dovtedy môžu posledné zmeny zostať iba v pamäti.

Každá zmena sa zapisuje v poradí mimo GUI; zatvorenie počká na dopísanie. Zápis používa dočasný súbor a atómovú náhradu. Neplatné uložené údaje sa oznámia a zachovajú v časovo označenej zálohe pred uložením nových dát. Nečitateľný stav sa nesmie potichu zahodiť ani prepísať.

## Pomocník a klávesové skratky

**Pomocník → Návod na použitie** otvorí tento posúvateľný návod v zvolenom jazyku. **O aplikácii** identifikuje aplikáciu. Skratky: **Ctrl+O** import, **Ctrl+E** export všetkých oprávnených fotografií, **Delete** odstránenie označených položiek z knižnice a **Alt+F4** zavretie okna.

Aplikácia pripravuje lokálne súbory a nepublikuje na Instagram. Instagram môže pri nahratí meniť rozlíšenie a kompresiu; podporované pomery sa môžu meniť. Aplikácia zvolený pomer potichu neupravuje.
