# generate_kwb_wiki_data.py

import cbsodata
import json
import os
import datetime
import sys
import argparse
import gc
from datetime import datetime, timezone # Explicitly import timezone

# --- Configuratie ---
DEFAULT_DATASET_ID_PATTERN = '85984NED' # Basis patroon, pas aan per jaar indien nodig
REGION_IDENTIFIER_KEY = 'Codering_3'    # CBS sleutel voor regiocode (GMxxxx, WKxxxxxx, BUxxxxxxxx)
REGION_TYPE_KEY = 'SoortRegio_2'        # CBS sleutel voor regio soort (Gemeente, Wijk, Buurt, etc.)

# Definieer welke statistieken (BASISNAMEN) we willen behouden.
# Script zoekt automatisch de volledige sleutel met suffix (bv. _5).
REQUIRED_STATS_BASE_NAMES = [
    'AantalInwoners',
    'Mannen',
    'Vrouwen',
    'Woningvoorraad',
    'OppervlakteTotaal',
    'OppervlakteLand',
    'OppervlakteWater',
    'Bevolkingsdichtheid'
    # Voeg hier meer basisnamen toe indien gewenst, bv. 'k_0Tot15Jaar'
]

# Definieer welke regio soorten behouden moeten blijven (opgeschoonde waarden)
TARGET_REGION_TYPES = {'Gemeente', 'Wijk'}

# Bestandsnaam voor de gecachte gestripte & gefilterde data (in data map)
STRIPPED_DATA_CACHE_FILENAME = "stripped_filtered_data_{year}.json" # Added 'filtered' to name

# Map voor template bestanden
TEMPLATE_DIR = "templates"

# --- Wiki Paden en Namen (Constanten voor duidelijkheid) ---
LUA_DISPATCHER_MODULE_PATH = "Module:CBS_Kerncijfers_Wijken_en_Buurten_Data"
TEMPLATE_STAT_PATH = "Template:CBS_Kerncijfers_Wijken_en_Buurten_Stat"
TEMPLATE_INFO_PATH = "Template:CBS_Kerncijfers_Wijken_en_Buurten"


# --- Hulpfuncties ---

def check_data_files_exist(data_dir):
    """Controleert of essentiële CBS download bestanden bestaan."""
    required_files = ['TypedDataSet.json', 'DataProperties.json', 'TableInfos.json']
    if not os.path.isdir(data_dir): return False
    for filename in required_files:
        if not os.path.isfile(os.path.join(data_dir, filename)):
            print(f"  Info: Vereist bronbestand '{filename}' niet gevonden in '{data_dir}'.")
            return False
    return True

def download_data(dataset_id, data_dir, overwrite=False):
    """Downloadt CBS data, checkt eerst of data al bestaat."""
    print(f"Controleren bron data directory: {data_dir}")
    os.makedirs(os.path.dirname(data_dir), exist_ok=True)
    should_download = overwrite or not check_data_files_exist(data_dir)
    if not should_download:
        print("  Bron data bestanden gevonden. Download overgeslagen.")
        return True
    action = "Overschrijven" if overwrite else "Downloaden"
    print(f"  {action} bron data...")
    print(f"Poging tot download dataset '{dataset_id}' naar '{data_dir}'...")
    try:
        os.makedirs(data_dir, exist_ok=True)
        cbsodata.download_data(dataset_id, dir=data_dir)
        if check_data_files_exist(data_dir):
            print("Download succesvol en geverifieerd.")
            return True
        else:
            print("Fout: Download commando voltooid, maar vereiste bronbestanden missen nog.")
            return False
    except Exception as e:
        print(f"Fout tijdens data download: {e}")
        return False

def load_json(filepath):
    """Laadt JSON data uit een bestand."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return None
    except Exception as e: print(f"Fout bij laden {filepath}: {e}"); return None

def save_json(data, filepath):
    """Slaat data op naar een JSON bestand."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        return True
    except Exception as e: print(f"Fout bij opslaan JSON naar {filepath}: {e}"); return False

def clean_key(key):
    """Verwijdert spaties aan begin/eind van strings."""
    if isinstance(key, str): return key.strip()
    return key

def load_and_strip_typed_data(filepath, identifier_key, region_type_key, target_region_types, full_keys_to_keep):
    """Laadt TypedDataSet, filtert op regio type, en behoudt alleen vereiste volledige sleutels."""
    print(f"Laden, filteren ({'/'.join(target_region_types)}), en strippen {filepath}...")
    stripped_data = {}
    keys_to_keep_set = set(full_keys_to_keep)
    keys_to_keep_set.add(identifier_key)

    try:
        full_data = load_json(filepath)
        if full_data is None:
            print(f"Fout: Kon bronbestand {filepath} niet laden voor stripping.")
            return None

        print(f"  Verwerken {len(full_data)} records...")
        processed_count = 0
        filtered_out_count = 0
        for record in full_data:
            region_type_cleaned = clean_key(record.get(region_type_key))
            if region_type_cleaned not in target_region_types:
                filtered_out_count += 1; continue

            region_code = clean_key(record.get(identifier_key))
            if region_code:
                stats_for_region = {k: record[k] for k in keys_to_keep_set if k in record}
                has_required_stat = any(k in stats_for_region for k in full_keys_to_keep)

                if identifier_key in stats_for_region and has_required_stat:
                    value_dict = {k: v for k, v in stats_for_region.items() if k != identifier_key}
                    stripped_data[region_code] = value_dict
                    processed_count += 1

        print(f"  {filtered_out_count} records uitgefilterd (Buurten, etc.).")
        print(f"  Succesvol data gestript voor {processed_count} regio's (Gemeenten/Wijken).")
        del full_data; gc.collect()
        return stripped_data
    except Exception as e:
        print(f"Onverwachte fout tijdens filteren/strippen van {filepath}: {e}")
        return None

def format_lua_value(value):
    """Formatteert Python waarden voor Lua."""
    if value is None: return "nil"
    if isinstance(value, bool): return str(value).lower()
    if isinstance(value, (int, float)):
        if value != value: return "nil --[[NaN]]"
        if value == float('inf'): return "nil --[[Infinity]]"
        if value == float('-inf'): return "nil --[[-Infinity]]"
        return str(value)
    if isinstance(value, str):
        processed = value.strip().replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
        processed = processed.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{processed}"'
    return f'"{str(value)}" --[[Onbekend Type: {type(value)}]]'

def apply_template(template_filename, replacements):
    """Leest een template bestand en voert vervangingen uit."""
    try:
        tpl_path = os.path.join(TEMPLATE_DIR, template_filename)
        with open(tpl_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, str(value))
        return content
    except FileNotFoundError:
        print(f"Fout: Template bestand niet gevonden: {tpl_path}")
        return None
    except Exception as e:
        print(f"Fout bij toepassen template {template_filename}: {e}")
        return None

def write_output_file(content, output_filename):
    """Schrijft content naar het output bestand."""
    if content is None: return False # Geef aan dat er niets geschreven is
    try:
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Gegenereerd: {os.path.basename(output_filename)}")
        return True
    except Exception as e:
        print(f"Fout bij schrijven output bestand {output_filename}: {e}")
        return False

def generate_lua_data_submodule(stripped_data, metadata_dict, key_map, dataset_id, year, lua_filename, lua_doc_filename):
    """Genereert de JAARLIJKSE Lua data submodule EN de bijbehorende documentatie."""
    print(f"Genereren Lua data submodule en doc: {os.path.basename(lua_filename)}, {os.path.basename(lua_doc_filename)}...")

    full_keys_required_set = set(key_map.values())

    # -- Genereer Metadata Entries --
    metadata_entries_list = []
    for full_key in sorted(metadata_dict.keys()):
        if full_key in full_keys_required_set:
            meta = metadata_dict.get(full_key)
            if meta:
                metadata_entries_list.append(
                    f'  ["{full_key}"] = {{ title = {format_lua_value(meta.get("Title"))}, unit = {format_lua_value(meta.get("Unit"))}, decimals = {format_lua_value(meta.get("Decimals"))}, description = {format_lua_value(meta.get("Description"))} }},'
                )
    metadata_entries_str = "\n".join(metadata_entries_list)

    # -- Genereer Data Entries --
    data_entries_list = []
    for region_code in sorted(stripped_data.keys()):
        stats = stripped_data[region_code]
        stat_entries = []
        for stat_key in sorted(stats.keys()):
             stat_entries.append(f'    ["{stat_key}"] = {format_lua_value(stats[stat_key])},')
        data_entries_list.append(f'  ["{region_code}"] = {{\n' + '\n'.join(stat_entries) + '\n  },')
    data_entries_str = "\n".join(data_entries_list)

    # -- Vul template voor Lua code in --
    generation_timestamp = datetime.now(timezone.utc).isoformat()
    module_replacements = {
        '%%YEAR%%': year,
        '%%DATASET_ID%%': dataset_id,
        '%%GENERATION_TIMESTAMP%%': generation_timestamp,
        '%%REGION_TYPES%%': ", ".join(sorted(TARGET_REGION_TYPES)),
        '%%STATS_LIST_FULL%%': ", ".join(sorted(full_keys_required_set)),
        '%%METADATA_ENTRIES%%': metadata_entries_str,
        '%%DATA_ENTRIES%%': data_entries_str,
    }
    module_content = apply_template("module_data.lua", module_replacements)
    write_output_file(module_content, lua_filename)

    # --- Genereer Documentatie ---
    doc_replacements = {
        '%%YEAR%%': year,
        '%%DATASET_ID%%': dataset_id,
        '%%GENERATION_TIMESTAMP%%': generation_timestamp,
        '%%REGION_ID_KEY%%': REGION_IDENTIFIER_KEY,
        '%%STATS_LIST_FULL%%': ", ".join(sorted(full_keys_required_set)),
        '%%REGION_TYPES%%': ", ".join(sorted(TARGET_REGION_TYPES)),
        '%%LUA_DISPATCHER_PATH%%': LUA_DISPATCHER_MODULE_PATH,
        '%%TEMPLATE_STAT_PATH%%': TEMPLATE_STAT_PATH,
        '%%TEMPLATE_STAT_NAME%%': TEMPLATE_STAT_PATH.split(':', 1)[1],
    }
    module_doc_content = apply_template("module_data_doc.wikitext", doc_replacements)
    write_output_file(module_doc_content, lua_doc_filename)

def generate_dispatcher_lua(key_map, output_filename):
    """Genereert de Dispatcher Lua module vanuit een template (voor handmatige upload)."""
    print(f"Genereren Dispatcher Lua module (voor handmatig kopiëren): {os.path.basename(output_filename)}...")

    alias_mapping_block_list = []
    for base_name, full_key in key_map.items():
        if base_name != full_key:
            alias_mapping_block_list.append(f"    if stat_alias == '{base_name}' then internal_stat_key = '{full_key}' end")

    replacements = {
        '%%MODULE_BASE_NAME%%': LUA_DISPATCHER_MODULE_PATH.split(':')[1], # Naam zonder 'Module:'
        '%%ALIAS_MAPPING_BLOCK%%': "\n".join(alias_mapping_block_list)
    }
    dispatcher_content = apply_template("module_dispatcher.lua", replacements)
    write_output_file(dispatcher_content, output_filename)

def generate_dispatcher_doc(key_map, year, dataset_id, output_doc_filename):
    """Genereert de documentatie voor de Dispatcher Lua module vanuit een template."""
    print(f"Genereren Dispatcher Lua documentatie: {os.path.basename(output_doc_filename)}...")

    # Bouw Wikitext tabelrijen voor aliassen
    alias_table_rows_list = []
    for base_name in sorted(key_map.keys()):
        full_key = key_map[base_name]
        # Alleen rijen toevoegen als het een echte alias is
        if base_name != full_key:
            row = f"|-\n| <code>{base_name}</code> \n|| <code>{full_key}</code>"
            alias_table_rows_list.append(row)

    # Definieer placeholders en hun waarden
    replacements = {
        '%%TEMPLATE_STAT_PATH%%': TEMPLATE_STAT_PATH,
        '%%TEMPLATE_STAT_NAME%%': TEMPLATE_STAT_PATH.split(':', 1)[1],
        '%%LUA_DISPATCHER_PATH%%': LUA_DISPATCHER_MODULE_PATH,
        '%%LUA_DATA_SUBMODULE_EXAMPLE_PATH%%': f"{LUA_DISPATCHER_MODULE_PATH}/{year}", # Gebruik huidig jaar als voorbeeld
        '%%EXAMPLE_YEAR%%': str(year),
        '%%ALIAS_TABLE_ROWS%%': "\n".join(alias_table_rows_list) if alias_table_rows_list else "|-\n| ''(Geen aliassen gedefinieerd)'' \n|| -", # Fallback als er geen aliassen zijn
        # %%DATASET_ID%% en andere placeholders indien nodig in de doc template
        '%%DATASET_ID%%': dataset_id,
    }

    # Pas template toe en schrijf weg
    dispatcher_doc_content = apply_template("module_dispatcher_doc.wikitext", replacements)
    write_output_file(dispatcher_doc_content, output_doc_filename)

def generate_wikitemplates(metadata_dict, key_map, year, dataset_id, stat_filename, info_filename, stat_doc_filename, info_doc_filename):
    """Genereert de Wiki sjabloon boilerplate/documentatie IN HET NEDERLANDS vanuit templates."""
    print(f"Genereren Nederlandse Wikitext sjablonen vanuit templates...")

    # Paden en namen setup
    lua_data_submodule_path = f"{LUA_DISPATCHER_MODULE_PATH}/{year}"
    template_stat_name = TEMPLATE_STAT_PATH.split(':', 1)[1]

    # Zorg dat output directories bestaan
    os.makedirs(os.path.dirname(stat_filename), exist_ok=True)
    os.makedirs(os.path.dirname(info_filename), exist_ok=True)
    os.makedirs(os.path.dirname(stat_doc_filename), exist_ok=True)
    os.makedirs(os.path.dirname(info_doc_filename), exist_ok=True)

    # Strings voor documentatie
    user_facing_keys = sorted(key_map.keys())
    included_stats_str = ", ".join(user_facing_keys)
    included_regions_str = ", ".join(sorted(TARGET_REGION_TYPES))

    # --- Sjabloon: ... Stat ---
    stat_replacements = {
        '%%MODULE_INVOKE_PATH%%': LUA_DISPATCHER_MODULE_PATH.split(':', 1)[1],
        '%%YEAR%%': str(year),
    }
    stat_content = apply_template("template_stat.wikitext", stat_replacements)
    write_output_file(stat_content, stat_filename)

    # --- Documentatie voor Stat Sjabloon (/doc pagina) ---
    available_stats_table_rows = []
    for base_name in user_facing_keys: # Al gesorteerd
        full_key = key_map[base_name]
        meta = metadata_dict.get(full_key, {})
        title = meta.get('Title', 'N/A')
        unit = meta.get('Unit', '')
        unit_str = f" ({unit})" if unit else ""
        details = f"CBS: <code>{full_key}</code>" if base_name != full_key else ""
        row = f"|-\n| <code>{base_name}</code> \n|| {title}{unit_str} \n|| {details}"
        available_stats_table_rows.append(row)
    available_stats_table_str = "\n".join(available_stats_table_rows)

    stat_doc_replacements = {
        '%%TEMPLATE_STAT_NAME%%': template_stat_name,
        '%%YEAR%%': str(year),
        '%%REGION_ID_KEY%%': REGION_IDENTIFIER_KEY,
        '%%STATS_LIST_USER%%': included_stats_str,
        '%%REGION_TYPES%%': included_regions_str,
        '%%AVAILABLE_STATS_TABLE%%': available_stats_table_str,
        '%%LUA_DISPATCHER_PATH%%': LUA_DISPATCHER_MODULE_PATH,
        '%%LUA_DATA_SUBMODULE_PATH%%': lua_data_submodule_path,
        '%%DATASET_ID%%': dataset_id,
    }
    stat_doc_content = apply_template("template_stat_doc.wikitext", stat_doc_replacements)
    write_output_file(stat_doc_content, stat_doc_filename)

    # --- Sjabloon: ... Info ---
    info_replacements = {
        '%%TEMPLATE_STAT_PATH%%': TEMPLATE_STAT_PATH,
        '%%TEMPLATE_STAT_NAME%%': template_stat_name
    }
    info_content = apply_template("template_info.wikitext", info_replacements)
    write_output_file(info_content, info_filename)

    # --- Documentatie voor Info Sjabloon (/doc pagina) ---
    info_doc_replacements = {
        '%%TEMPLATE_STAT_PATH%%': TEMPLATE_STAT_PATH,
        '%%TEMPLATE_STAT_NAME%%': template_stat_name,
        '%%YEAR%%': str(year),
        '%%LUA_DISPATCHER_PATH%%': LUA_DISPATCHER_MODULE_PATH,
        '%%LUA_DATA_SUBMODULE_PATH%%': lua_data_submodule_path,
        '%%STATS_LIST_USER%%': included_stats_str,
        '%%REGION_TYPES%%': included_regions_str,
        '%%DATASET_ID%%': dataset_id,
    }
    info_doc_content = apply_template("template_info_doc.wikitext", info_doc_replacements)
    write_output_file(info_doc_content, info_doc_filename)


# --- Hoofd Uitvoeringslogica ---

if __name__ == "__main__":
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Download/verwerk CBS KWB data en genereer Wiki Lua/sjablonen.")
    parser.add_argument("year", type=int, help="Het doeljaar voor de data.")
    parser.add_argument("--overwrite", action="store_true", help="Forceer opnieuw downloaden CBS bron data.")
    parser.add_argument("--overwrite-stripped", action="store_true", help="Forceer opnieuw filteren/strippen van data.")
    parser.add_argument("--dataset-id", type=str, default=None, help="Overschrijf het standaard CBS dataset ID.")
    args = parser.parse_args()

    # --- Variabelen Setup ---
    TARGET_YEAR = args.year
    OVERWRITE_SOURCE_DATA = args.overwrite
    OVERWRITE_STRIPPED_DATA = args.overwrite_stripped
    YEAR_BASE_DIR = str(TARGET_YEAR)
    DATA_DIR = os.path.join(YEAR_BASE_DIR, "cbs_data")
    OUTPUT_DIR = os.path.join(YEAR_BASE_DIR, "wiki_output")

    # Paden naar bron en cache bestanden
    full_typed_data_set_path = os.path.join(DATA_DIR, 'TypedDataSet.json')
    stripped_data_cache_path = os.path.join(DATA_DIR, STRIPPED_DATA_CACHE_FILENAME.format(year=TARGET_YEAR))
    data_properties_path = os.path.join(DATA_DIR, 'DataProperties.json')

    # Definieer Wiki paden en output bestandsnamen
    lua_data_submodule_path = f"{LUA_DISPATCHER_MODULE_PATH}/{TARGET_YEAR}"
    lua_data_submodule_filename = os.path.join(OUTPUT_DIR, f"{LUA_DISPATCHER_MODULE_PATH.replace(':', '_')}_{TARGET_YEAR}.lua")
    lua_data_submodule_doc_filename = os.path.join(OUTPUT_DIR, f"{LUA_DISPATCHER_MODULE_PATH.replace(':', '_')}_{TARGET_YEAR}_doc.wikitext")

    template_stat_filename = os.path.join(OUTPUT_DIR, f"{TEMPLATE_STAT_PATH.replace(':', '_')}.wikitext")
    template_info_filename = os.path.join(OUTPUT_DIR, f"{TEMPLATE_INFO_PATH.replace(':', '_')}.wikitext")
    template_stat_doc_filename = os.path.join(OUTPUT_DIR, f"{TEMPLATE_STAT_PATH.replace(':', '_')}_doc.wikitext")
    template_info_doc_filename = os.path.join(OUTPUT_DIR, f"{TEMPLATE_INFO_PATH.replace(':', '_')}_doc.wikitext")
    dispatcher_lua_output_filename = os.path.join(OUTPUT_DIR, f"{LUA_DISPATCHER_MODULE_PATH.replace(':', '_')}_DISPATCHER_MANUAL_COPY.lua")
    dispatcher_lua_doc_output_filename = os.path.join(OUTPUT_DIR, f"{LUA_DISPATCHER_MODULE_PATH.replace(':', '_')}_doc.wikitext")
    
    # --- Start Proces ---
    print(f"--- Start KWB Generator {TARGET_YEAR} (Templates, Suffix-Agnostisch) ---")
    print(f"Benodigde Stats (basisnamen): {', '.join(REQUIRED_STATS_BASE_NAMES)}")
    print(f"Gefilterde Regio Types: {', '.join(TARGET_REGION_TYPES)}")
    print(f"Bron Data: {DATA_DIR}, Cache: {stripped_data_cache_path}, Output: {OUTPUT_DIR}")
    print(f"Overschrijf bron: {OVERWRITE_SOURCE_DATA}, Overschrijf stripped: {OVERWRITE_STRIPPED_DATA}")

    dataset_id = args.dataset_id if args.dataset_id else DEFAULT_DATASET_ID_PATTERN
    print(f"Gebruikt Dataset ID: {dataset_id}")

    # 1. Download Bron Data
    if not download_data(dataset_id, DATA_DIR, OVERWRITE_SOURCE_DATA): sys.exit(1)

    # 2. Laad Metadata
    print("Laden metadata (DataProperties)...")
    data_properties = load_json(data_properties_path)
    if not data_properties: print("AFGEBROKEN: Kon DataProperties.json niet laden."); sys.exit(1)

    # 3. Bouw Key Map
    print("Bouwen key map van metadata...")
    key_map, metadata_dict, missing_bases = {}, {}, set(REQUIRED_STATS_BASE_NAMES)
    for prop in data_properties:
        if prop.get('odata.type') == 'Cbs.OData.Topic':
             full_key = clean_key(prop.get('Key', ''))
             if not full_key: continue
             metadata_dict[full_key] = { k: prop.get(k) for k in ['Title', 'Description', 'Unit', 'Decimals'] }
             base_name = full_key
             if '_' in full_key and full_key.split('_')[-1].isdigit():
                 base_name = '_'.join(full_key.split('_')[:-1])
             if base_name in REQUIRED_STATS_BASE_NAMES:
                 if base_name not in key_map: key_map[base_name] = full_key; missing_bases.discard(base_name)
                 elif key_map[base_name] != full_key: print(f"Waarschuwing: Dubbele basisnaam '{base_name}'")
    if missing_bases: print(f"AFGEBROKEN: Mapping mist voor: {missing_bases}"); sys.exit(1)
    full_keys_required_set = set(key_map.values())
    print(f"Afgeleide volledige sleutels: {', '.join(sorted(full_keys_required_set))}")

    # 4. Verkrijg Stripped/Filtered Data
    processed_data = None
    use_cache = not OVERWRITE_STRIPPED_DATA and os.path.exists(stripped_data_cache_path)
    if use_cache:
        print(f"Poging tot laden data uit cache: {stripped_data_cache_path}")
        processed_data = load_json(stripped_data_cache_path)
        if processed_data:
            first_rec_keys = set(next(iter(processed_data.values())).keys()) if processed_data else set()
            if not full_keys_required_set.issubset(first_rec_keys):
                 print("Waarschuwing: Cache data verouderd. Forceer re-strip."); processed_data = None
            else: print(f"Succesvol {len(processed_data)} regios geladen uit cache.")
        else: print("Waarschuwing: Cache bestand corrupt/leeg. Zal opnieuw strippen.")
    if processed_data is None:
        reason = "(--overwrite-stripped)" if OVERWRITE_STRIPPED_DATA else "(cache mist/fout/verouderd)"
        print(f"Uitvoeren data filtering en stripping {reason}...")
        if not os.path.exists(full_typed_data_set_path): print(f"Fout: Bronbestand mist: {full_typed_data_set_path}"); sys.exit(1)
        processed_data = load_and_strip_typed_data(full_typed_data_set_path, REGION_IDENTIFIER_KEY, REGION_TYPE_KEY, TARGET_REGION_TYPES, full_keys_required_set)
        if processed_data is not None:
            print(f"Opslaan data naar cache: {stripped_data_cache_path}")
            if not save_json(processed_data, stripped_data_cache_path): print("Waarschuwing: Opslaan cache mislukt.")
            print(f"NOTE: Cache reflecteert basisnamen: {', '.join(REQUIRED_STATS_BASE_NAMES)}.")
    if processed_data is None: print("AFGEBROKEN: Kon data niet verkrijgen."); sys.exit(1)

    # 5. Genereer Lua Data Submodule EN Documentatie
    generate_lua_data_submodule(
        processed_data, metadata_dict, key_map, dataset_id, TARGET_YEAR,
        lua_data_submodule_filename, lua_data_submodule_doc_filename
    )

    # 6. Genereer Dispatcher Lua code (voor handmatige upload)
    generate_dispatcher_lua(key_map, dispatcher_lua_output_filename)    
    generate_dispatcher_doc(key_map, TARGET_YEAR, dataset_id, dispatcher_lua_doc_output_filename)

    # 7. Genereer Wiki Sjablonen en Hun Documentatie
    generate_wikitemplates(
        metadata_dict, key_map, TARGET_YEAR, dataset_id,
        template_stat_filename, template_info_filename,
        template_stat_doc_filename, template_info_doc_filename
    )

    # --- Afronden ---
    print("-" * 30)
    print("Script succesvol voltooid.")
    print(f"Gegenereerde bestanden staan in: {OUTPUT_DIR}")
    print(f"  - Lua Data Submodule: {os.path.basename(lua_data_submodule_filename)}")
    print(f"    -> Upload naar Wiki Pagina: '{lua_data_submodule_path}'")
    print(f"  - Lua Data Submodule Doc: {os.path.basename(lua_data_submodule_doc_filename)}")
    print(f"    -> Upload naar Wiki Pagina: '{lua_data_submodule_path}/doc'")
    print(f"  - Stat Sjabloon: {os.path.basename(template_stat_filename)}")
    print(f"    -> Upload naar Wiki Pagina: '{TEMPLATE_STAT_PATH}'")
    print(f"  - Stat Sjabloon Doc: {os.path.basename(template_stat_doc_filename)}")
    print(f"    -> Upload naar Wiki Pagina: '{TEMPLATE_STAT_PATH}/doc'")
    print(f"  - Info Sjabloon: {os.path.basename(template_info_filename)}")
    print(f"    -> Upload naar Wiki Pagina: '{TEMPLATE_INFO_PATH}'")
    print(f"  - Info Sjabloon Doc: {os.path.basename(template_info_doc_filename)}")
    print(f"  - Dispatcher Lua Doc: {os.path.basename(dispatcher_lua_doc_output_filename)}")
    print(f"    -> Upload naar Wiki Pagina: '{TEMPLATE_INFO_PATH}/doc'")
    print(f"  - Dispatcher Lua (Handmatig): {os.path.basename(dispatcher_lua_output_filename)}")
    print(f"\n!!! BELANGRIJK: Handmatige Actie Nodig !!!")
    if os.path.exists(dispatcher_lua_output_filename):
        print(f"1. Creëer/Update de hoofdmodule '{LUA_DISPATCHER_MODULE_PATH}' op de wiki.")
        print(f"2. Kopieer de inhoud van '{os.path.basename(dispatcher_lua_output_filename)}' hiernaartoe.")
    else:
         print(f"1. CREËER de hoofdmodule '{LUA_DISPATCHER_MODULE_PATH}' handmatig op de wiki met de Lua code!")
    print(f"3. Upload de inhoud van de andere gegenereerde bestanden (incl. /doc) naar hun respectievelijke pagina's.")