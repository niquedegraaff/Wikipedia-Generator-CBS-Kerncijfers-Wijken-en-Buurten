# CBS Kerncijfers Wijken en Buurten Wiki Generator

**Note:** This project and documentation are primarily intended for Dutch users interacting with Dutch CBS data and MediaWiki installations (like nl.wikipedia.org).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Dit project bevat een Python script om data van het Centraal Bureau voor de Statistiek (CBS) betreffende Kerncijfers Wijken en Buurten te downloaden, te verwerken, en om te zetten naar Lua data modules en Wiki-sjablonen voor gebruik op MediaWiki-gebaseerde wiki's zoals Wikipedia.

## Doel

Het doel is om een gestandaardiseerde en makkelijk te onderhouden manier te bieden om actuele CBS Kerncijfers (zoals inwonersaantallen, man/vrouw-verdeling, woningvoorraad) per gemeente en wijk weer te geven op wiki-pagina's. Het lost het probleem op van verouderde, handmatig ingevoerde data en complexe, moeilijk te updaten sjablonen.

## Kenmerken

*   **Automatische Data Download:** Gebruikt de `cbsodata` library om de meest recente dataset op te halen van CBS StatLine Open Data.
*   **Filtering & Stripping:** Verwerkt alleen data voor Gemeenten (GM) en Wijken (WK), en behoudt alleen vooraf gedefinieerde essentiële statistieken om de bestandsgrootte (lua scripts) te beperken.
*   **Suffix-Agnostisch:** Detecteert automatisch de juiste volledige CBS-sleutel (bv. `AantalInwoners_5`) op basis van een opgegeven basisnaam (bv. `AantalInwoners`), waardoor het script robuuster is voor toekomstige dataset-versies.
*   **Caching:** Slaat zowel de gedownloade CBS-bronbestanden als de verwerkte (gestripte/gefilterde) data lokaal op om onnodige downloads en verwerking bij herhaaldelijk draaien te voorkomen. Overwrite-opties zijn beschikbaar.
*   **Template-gebaseerde Generatie:** Gebruikt lokale template-bestanden (`*.lua`, `*.wikitext`) voor een schone scheiding tussen code-logica en de structuur van de output.
*   **Wiki Output:** Genereert de benodigde bestanden klaar voor upload naar een MediaWiki-installatie:
    *   Jaarlijkse Lua data submodules (`Module:Naam/JAAR`)
    *   Eenmalig te plaatsen Lua dispatcher module code
    *   Gebruiksvriendelijke Wiki-sjablonen (`Template:Naam_Stat`, `Template:Naam_Info`)
    *   Bijbehorende documentatiepagina's (`/doc`) in het Nederlands.
*   **Referentie Generatie:** Biedt een optie (`stat=Ref`) in het sjabloon om een gestandaardiseerde `<ref>` tag te genereren voor correcte bronvermelding.

## Vereisten

*   Python 3.12.4+
*   `cbsodata` library: `pip install -r requirements.txt`. 

## Installatie

1.  Clone deze repository:
    ```bash
    git clone https://github.com/niquedegraaff/Wikipedia-Generator-CBS-Kerncijfers-Wijken-en-Buurten.git
    cd Wikipedia-Generator-CBS-Kerncijfers-Wijken-en-Buurten
    ```
2.  Installeer de benodigde library:
    ```bash
    pip install -r requirements.txt
    ```

## Configuratie

Voordat je het script draait, controleer/configureer de volgende onderdelen bovenaan in `main.py`:

*   **`REQUIRED_STATS_BASE_NAMES`**: Lijst met de '''basisnamen''' van de statistieken die je wilt opnemen (bv. `'AantalInwoners'`, `'Mannen'`). Het script zoekt de volledige CBS-sleutel met suffix erbij.
*   **`TARGET_REGION_TYPES`**: Set met de regio-typen die behouden moeten blijven (standaard `{'Gemeente', 'Wijk'}`).
*   **`TEMPLATE_DIR`**: De map waar de template-bestanden staan (standaard `"templates"`).
*   **`LUA_DISPATCHER_MODULE_PATH`**, **`TEMPLATE_STAT_PATH`**, **`TEMPLATE_INFO_PATH`**: Definieer de gewenste namen voor de module en sjablonen op de wiki.

Zorg ervoor dat de map `templates/` bestaat en de volgende bestanden bevat (zie repository):
*   `module_data.lua`
*   `module_dispatcher.lua`
*   `template_stat.wikitext`
*   `template_stat_doc.wikitext`
*   `template_info.wikitext`
*   `template_info_doc.wikitext`

## Gebruik van het Script

Draai het script vanuit de hoofdmap van het project via de command line:

```bash
python main.py <jaar> [opties]
```

**Parameters:**

*   `<jaar>` (verplicht): Het jaartal waarvoor de data gegenereerd moet worden (bv. `2024`).

**Opties:**

*   `--overwrite`: Forceert het opnieuw downloaden van de bronbestanden van het CBS, zelfs als ze al bestaan in de `cbs_data` map.
*   `--overwrite-stripped`: Forceert het opnieuw filteren en strippen van de data, zelfs als het `stripped_filtered_data_{YYYY}.json` cache-bestand bestaat. Gebruik dit als je `REQUIRED_STATS_BASE_NAMES` of `TARGET_REGION_TYPES` hebt aangepast.
*   `--dataset-id <ID>`: Overschrijft het standaard CBS dataset ID dat het script probeert te gebruiken (standaard gebaseerd op `DEFAULT_DATASET_ID_PATTERN`). Nuttig als CBS het ID voor een specifiek jaar verandert.

**Voorbeeld:** Data voor 2023 genereren, waarbij de cache met gestripte data opnieuw wordt opgebouwd:

```bash
python generate_kwb_wiki_data.py 2023 --overwrite-stripped
```

## Gegenereerde Bestanden

Het script maakt een map aan voor het opgegeven jaar (bv. `2024/`) met daarin:

1.  **`cbs_data/`**: Bevat de originele gedownloade CBS JSON-bestanden en het cache-bestand `stripped_filtered_data_{YYYY}.json`.
2.  **`wiki_output/`**: Bevat de bestanden die klaar zijn voor upload naar de wiki:
    *   `Module_CBS_Kerncijfers_Wijken_en_Buurten_Data_YYYY.lua`: De jaarlijkse data submodule.
    *   `Module_CBS_Kerncijfers_Wijken_en_Buurten_Data_YYYY_doc.wikitext`: Documentatie voor de submodule.
    *   `Template_CBS_Kerncijfers_Wijken_en_Buurten_Stat.wikitext`: Het hoofdsjabloon voor data-ophaling.
    *   `Template_CBS_Kerncijfers_Wijken_en_Buurten_Stat_doc.wikitext`: Documentatie voor het Stat-sjabloon.
    *   `Template_CBS_Kerncijfers_Wijken_en_Buurten.wikitext`: Het centrale info-sjabloon.
    *   `Template_CBS_Kerncijfers_Wijken_en_Buurten_doc.wikitext`: Documentatie voor het Info-sjabloon.
    *   `Module_CBS_Kerncijfers_Wijken_en_Buurten_Data_DISPATCHER_MANUAL_COPY.lua`: De code voor de *handmatig* aan te maken/updaten hoofd dispatcher module.

## Wiki Implementatie

Volg deze stappen om de gegenereerde code op een MediaWiki-wiki te implementeren:

1.  **Maak/Update Dispatcher Module (Handmatig, Eenmalig/Incidenteel):**
    *   **Letop! deze stap is vrijwel nooit nodig tenzij de *logica* van de dispatcher zelf verandert.**
    *   Ga naar de wiki-pagina `https://nl.wikipedia.org/wiki/Module:CBS_Kerncijfers_Wijken_en_Buurten_Data`.
    *   Kopieer de **volledige inhoud** van het lokaal gegenereerde bestand `..._DISPATCHER_MANUAL_COPY.lua`.
    *   Plak deze code in de wiki-editor voor de dispatcher module en sla op.

2.  **Upload Jaarlijkse Data Submodule:**
    *   Ga naar de wiki-pagina `https://nl.wikipedia.org/wiki/Module:CBS_Kerncijfers_Wijken_en_Buurten_Data/YYYY` Vervang YYYY met het jaar dat je wil aanmaken/updaten. 
    *   Kopieer de inhoud van het lokaal gegenereerde `Module_CBS_Kerncijfers_Wijken_en_Buurten_Data_YYYY.lua` bestand.
    *   Plak en sla op.
    *   Upload de inhoud van `..._Data_YYYY_doc.wikitext` naar de `/doc` subpagina.

3.  **Upload Sjablonen:**
    *   Maak/update de pagina `Template:CBS_Kerncijfers_Wijken_en_Buurten_Stat` met de inhoud van het corresponderende `.wikitext` bestand.
    *   Maak/update de `/doc` subpagina (`Template:CBS_Kerncijfers_Wijken_en_Buurten_Stat/doc`) met de inhoud van het corresponderende `_doc.wikitext` bestand.
    *   Doe hetzelfde voor `Template:CBS_Kerncijfers_Wijken_en_Buurten` en zijn `/doc` pagina.

## Voorbeeld gebruik in wiki pagina's

Aantal inwoners meest recent:
```wikitext
{{CBS_Kerncijfers_Wijken_en_Buurten_Stat |regio=GM1680 |stat=AantalInwoners}}
```

Aantal inwoners in 2024:
```wikitext
{{CBS_Kerncijfers_Wijken_en_Buurten_Stat |jaar=2024 |regio=GM1680 |stat=AantalInwoners}}
```

Referentie genereren:
```wikitext
{{CBS_Kerncijfers_Wijken_en_Buurten_Stat |jaar=2024 |stat=Ref}}
```

## Bijdragen

Bijdragen zijn welkom! Maak een Issue aan om bugs te melden of features voor te stellen, of maak een Pull Request met je wijzigingen.

## Licentie

Dit project valt onder de [MIT License](LICENSE).