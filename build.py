import requests
import os
import json
from pathlib import Path
import re
import unicodedata
import shutil

requests.packages.urllib3.disable_warnings()

LANG_ENCODINGS = {
    'DE':   {'encoding': 'cp1252', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/DE/Recorded_Media_DE.txt'},
    'EN':   {'encoding': 'utf-8',  'file_path': 'Contents/mods/Shrek1and2intheirENTIRETYasvhs\'s/media/lua/shared/Translate/EN/Recorded_Media_EN.txt'},
    'ES':   {'encoding': 'cp1252', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/ES/Recorded_Media_ES.txt'},
    'FR':   {'encoding': 'cp1252', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/FR/Recorded_Media_FR.txt'},
    'ID':   {'encoding': 'utf-8',  'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/ID/Recorded_Media_ID.txt'},
    'IT':   {'encoding': 'cp1252', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/IT/Recorded_Media_IT.txt'},
    'JP':   {'encoding': 'utf-8',  'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/JP/Recorded_Media_JP.txt'},
    'NL':   {'encoding': 'cp1252', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/NL/Recorded_Media_NL.txt'},
    'PL':   {'encoding': 'cp1250', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/PL/Recorded_Media_PL.txt'},
    'PT':   {'encoding': 'cp1252', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/PT/Recorded_Media_PT.txt'},
    'PTBR': {'encoding': 'cp1252', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/PTBR/Recorded_Media_PTBR.txt'},
    'RO':   {'encoding': 'utf-8',  'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/RO/Recorded_Media_RO.txt'},
    'RU':   {'encoding': 'cp1251', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/RU/Recorded_Media_RU.txt'},
    'UA':   {'encoding': 'cp1251', 'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/UA/Recorded_Media_UA.txt'},
    'CH':   {'encoding': 'utf-8',  'file_path': 'Contents/mods/Shrek1and2intheirTranslate/media/lua/shared/Translate/CH/Recorded_Media_CH.txt'},
}

CASSETTES = {
    'shrek1': {
        'cassette_uuid': 'shrektape',
        'item_display_name_key': 'shrek1',
        'title_key': 'Shrek 1',
        'author_key': 'nil',
        'output_dir': 'Contents/mods/Shrek1and2intheirENTIRETYasvhs\'s/media/lua/shared'
    },
    'shrek2': {
        'cassette_uuid': 'shrek2tape',
        'item_display_name_key': 'shrek2',
        'title_key': 'Shrek 2',
        'author_key': 'nil',
        'output_dir': 'Contents/mods/Shrek1and2intheirENTIRETYasvhs\'s/media/lua/shared'
    }
}

def normalize_text(text, encoding):
    text = text.replace('\u200b', '')
    normalized = unicodedata.normalize('NFKD', text)
    try:
        normalized.encode(encoding)
        return normalized
    except UnicodeEncodeError:
        result = ''
        for char in normalized:
            if char.encode(encoding, errors='ignore') == b'':
                result += '@'
            else:
                result += char
        return result

def parse_translations(json_data):
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        exit(1)
    translations_by_lang = {}
    for timecode, value in data.items():
        rgb = value.get("rgb", "255,255,255")
        langs = value.get("langs", {})
        for lang, text in langs.items():
            if lang not in translations_by_lang:
                translations_by_lang[lang] = []
            translations_by_lang[lang].append({
                "timecode": timecode,
                "text": text,
                "rgb": rgb
            })
    return translations_by_lang

def write_translations_to_files(translations_by_lang, base_dir=""):
    for lang, lines in translations_by_lang.items():
        lang_info = LANG_ENCODINGS.get(lang, {'encoding': 'utf-8', 'file_path': f'Translate/{lang}/Recorded_Media_{lang}.txt'})
        encoding = lang_info['encoding']
        file_path = os.path.join(base_dir, lang_info['file_path'])
        Path(os.path.dirname(file_path)).mkdir(parents=True, exist_ok=True)

        try:
            content = "\n".join(
                f'{re.sub(r"\[img:music\] | \[img:music\]", "", line["timecode"])} = "{normalize_text(line["text"], encoding)}"'
                for line in lines
            )
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)
            print(f"Saved file: {file_path} ({encoding})")
        except UnicodeEncodeError as e:
            print(f"Encoding error for {lang} ({file_path}): {e}")
            problematic_text = content[max(0, e.start - 40):min(len(content), e.start + 40)]
            print(f"Issue near position {e.start}: ...{problematic_text}...")
            exit(1)
        except Exception as e:
            print(f"Error for {lang} ({file_path}): {e}")
            exit(1)

def create_lua_file(cassette_uuid, item_display_name_key, title_key, author_key, lines, output_dir):
    lua_content = f"""RecMedia = RecMedia or {{}}

RecMedia["{cassette_uuid}"] = {{
    itemDisplayName = "{item_display_name_key}",
    title = "{title_key}",
    subtitle = nil,
    author = "{author_key}",
    extra = nil,
    spawning = 0,
    category = "Retail-VHS",
    lines = {{
"""
    for line in lines.get('EN', []):
        r, g, b = line["rgb"].split(',')
        lua_content += f'        {{ text = "{line["timecode"]}", r = {r}, g = {g}, b = {b}, codes = "BOR-1" }},\n'
    lua_content += """    },
};
"""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{cassette_uuid}.lua")
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(lua_content)
    print(f"Created Lua file: {output_path}")

def main():
    url = os.getenv('GOOGLE_EXEC_URL')
    if not url:
        print("Error: GOOGLE_EXEC_URL not set in environment variables")
        exit(1)

    try:
        response = requests.post(url, json={'method': 'export', 'sheet': 'Shrek 1'}, verify=False)
        response.raise_for_status()
        json_data = response.text
    except requests.RequestException as e:
        print(f"Request error to Google Apps Script: {e}")
        exit(1)

    translations = parse_translations(json_data)
    write_translations_to_files(translations)

    for cassette_id, config in CASSETTES.items():
        create_lua_file(
            config['cassette_uuid'],
            config['item_display_name_key'],
            config['title_key'],
            config['author_key'],
            translations,
            config['output_dir']
        )

    base_translate_dir = 'Contents/mods/Shrek1and2intheirTranslate'
    base_entirety_dir = 'Contents/mods/Shrek1and2intheirENTIRETYasvhs\'s'
    version_42_translate_dir = 'Contents/mods/Shrek1and2intheirTranslate/42'
    version_42_entirety_dir = 'Contents/mods/Shrek1and2intheirENTIRETYasvhs\'s/42'

    for item in ['poster.png', 'mod.info']:
        shutil.copy(os.path.join(base_translate_dir, item), os.path.join(version_42_translate_dir, item))
        shutil.copy(os.path.join(base_entirety_dir, item), os.path.join(version_42_entirety_dir, item))

    shutil.copytree(os.path.join(base_translate_dir, 'media'), os.path.join(version_42_translate_dir, 'media'), dirs_exist_ok=True)
    shutil.copytree(os.path.join(base_entirety_dir, 'media'), os.path.join(version_42_entirety_dir, 'media'), dirs_exist_ok=True)

    print("Created version 42 build with selected files and directories")

if __name__ == '__main__':
    main()