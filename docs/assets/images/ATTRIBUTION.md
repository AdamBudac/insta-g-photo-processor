# Fotografie a snímky aplikácie

Overené 11. novembra 2026. Fotografie sú lokálnou súčasťou webu; pri otvorení stránky sa nesťahujú z externého servera.

## Panoráma

- Súbor: [panorama.jpg](./panorama.jpg), 1800 × 675 px.
- Autor: [Dino Reichmuth](https://unsplash.com/@dinoreichmuth).
- Zdroj: [Landscape photography of black and white mountain](https://unsplash.com/photos/landscape-photography-of-black-and-white-mountain-kk3W5-0b6e0), Niederbauen-Chulm, Švajčiarsko; publikované 3. júna 2016.
- [Zdrojový obrázok](https://images.unsplash.com/photo-1464983953574-0892a716854b).
- Úpravy: panoramatický výrez a zmenšenie pre web, optimalizácia JPEG.

## Portrétový formát

- Súbor: [portrait.jpg](./portrait.jpg), 1000 × 1500 px.
- Autorka: [Annie Spratt](https://unsplash.com/@anniespratt).
- Zdroj: [Green leaf / Minimal eucalyptus leaves](https://unsplash.com/photos/green-leaf-hX_hf2lPpUU); publikované 31. júla 2018.
- [Zdrojový obrázok](https://images.unsplash.com/photo-1533038590840-1cde6e668a91).
- Úpravy: zmenšenie pre web a optimalizácia JPEG.

Obe fotografie sú dostupné pod [Unsplash License](https://unsplash.com/license). Tá povoľuje bezplatné stiahnutie, použitie, úpravu a šírenie vrátane komerčného použitia. Fotografie nie sú súčasťou licencie zdrojového kódu projektu; naďalej sa na ne vzťahuje licencia Unsplash. Nie sú ponúkané na samostatný predaj ani ako konkurenčná fotobanka.

## Snímky aplikácie

[gui-import.png](./gui-import.png), [gui-edit.png](./gui-edit.png), [gui-expand.png](./gui-expand.png) a [gui-export.png](./gui-export.png) sú skutočné snímky lokálne spustenej aplikácie Insta G Photo Processor 1.0.0, v angličtine a tmavej téme. Rozmery každej snímky sú 1600 × 1000 px. Fotografie na nich pochádzajú z vyššie uvedených zdrojov a podliehajú rovnakým licenciám.

Snímky vznikli cez PySide6 MCP v samostatnej relácii s explicitným `--data-dir build/site-qa/app-state`. Neboli použité osobné fotografie ani používateľské nastavenia. Import zobrazuje dve práve pridané fotografie; editácia skutočný náhľad troch nadväzujúcich dielov panorámy; expand skutočné doplnenie okrajov portrétového vstupu na štvorec. Export bol vykonaný do izolovaného pracovného priečinka: úspešne spracoval dva originály, vytvoril štyri JPEG výstupy a nezaznamenal žiadnu chybu.
