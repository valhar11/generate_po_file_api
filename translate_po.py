#!/usr/bin/env python3
import argparse
import csv
import os
import polib
import deepl

# Default list of strings to exclude from translation.
DEFAULT_EXCLUDED_TERMS = {"tropla"}

def load_csv_translations(csv_path, debug=False):
    """
    Loads a CSV file and returns a dictionary {msgid: translation}.
    The first line is assumed to be a header.
    The CSV must be structured with a semicolon separator (";")
    (example header: EN;FR).
    """
    translations = {}
    if debug:
        print(f"[DEBUG] Reading CSV {csv_path} with separator ';'")
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            # Using the ';' separator to match your requirements.
            reader = csv.reader(csvfile, delimiter=';')
            header = next(reader, None)
            if debug:
                print(f"[DEBUG] CSV Header: {header}")
            for row in reader:
                if len(row) >= 2:
                    msgid = row[0].strip()
                    translation = row[1].strip()
                    if debug:
                        print(f"[DEBUG] CSV mapping found: '{msgid}' -> '{translation}'")
                    translations[msgid] = translation
                else:
                    print(f"[WARNING] Line ignored (invalid): {row}")
    except FileNotFoundError:
        print(f"[ERROR] CSV file '{csv_path}' not found.")
        return None
    except Exception as e:
        print(f"[ERROR] Error while reading CSV file '{csv_path}': {e}")
        return None
    return translations

def match_case(original, translation):
    """
    Adapts the case of 'translation' to match that of 'original'.
    - If 'original' is all uppercase -> translation.upper()
    - If 'original' is all lowercase -> translation.lower()
    - If 'original' is in title case -> translation.title()
    - Otherwise, if the first letter of 'original' is lowercase, forces
      the first letter of 'translation' to lowercase.
    """
    if original.isupper():
        return translation.upper()
    elif original.islower():
        return translation.lower()
    elif original.istitle():
        return translation.title()
    else:
        if original and original[0].islower():
            return translation[0].lower() + translation[1:]
        else:
            return translation

def auto_translate(text, target_lang="FR", api_key=None, debug=False):
    """
    Translates the text via the DeepL API.
    If no text or API key is provided, returns the original text.
    """
    if not text:
        return ""
    if not api_key:
        return text
    try:
        deepl_client = deepl.DeepLClient(api_key)
        result = deepl_client.translate_text(text, target_lang=target_lang.upper())
        if debug:
            print(f"[DEBUG] Translation via DeepL of '{text}' -> '{result.text}'")
        return result.text
    except Exception as e:
        print(f"[ERROR] Problem while translating text '{text}': {e}")
        return text

def process_pot_file(pot_file, csv_file, target_lang, deepl_api_key, disable_api, reference_po, verbose, debug):
    """
    Loads the POT file and updates its entries according to the CSV file and reference PO file.
    
    - The CSV is searched case-insensitively. If a match is found,
      the translation is adjusted to respect the case of the msgid.
    - If a reference PO file is provided, its translation is applied with priority (exact match).
    - If no translation is found in the reference PO or CSV and the DeepL API is enabled,
      the DeepL translation is used.
    - Each entry whose msgid does not already exist in the CSV will be added to the end of the CSV, 
      ONLY IF a non-empty translation is available.
    - The processed file is saved with the .po extension.
    
    A final report is displayed.
    """
    # Loading CSV translations
    csv_translations = load_csv_translations(csv_file, debug)
    if csv_translations is None:
        print("[ERROR] Processing interrupted due to an error with the CSV file.")
        return
    csv_translations_lower = {k.lower(): v for k, v in csv_translations.items()}

    # Loading the reference PO file (exact match required)
    reference_translations = {}
    if reference_po:
        try:
            ref_po = polib.pofile(reference_po)
            if debug:
                print(f"[DEBUG] Loading reference PO file: {reference_po}")
            for entry in ref_po:
                if entry.msgid and entry.msgstr:
                    reference_translations[entry.msgid] = entry.msgstr
                    if debug:
                        print(f"[DEBUG] Reference translation found: '{entry.msgid}' -> '{entry.msgstr}'")
        except Exception as e:
            print(f"[ERROR] Unable to read reference PO file {reference_po}: {e}")

    # Initializing counters for the final report
    translated_from_csv_count = 0
    translated_from_deepl_count = 0
    translated_from_reference_count = 0
    untranslated_count = 0
    already_translated_count = 0

    try:
        pot = polib.pofile(pot_file)
    except Exception as e:
        print(f"[ERROR] Unable to read POT file {pot_file}: {e}")
        return

    # List for new entries to add to the CSV
    new_csv_entries = {}
    
    for entry in pot:
        if debug:
            print(f"[DEBUG] Processing entry: '{entry.msgid}'")
        msgid = entry.msgid
        msgid_lower = msgid.lower()
        
        if entry.msgstr:
            already_translated_count += 1

        # Priority 1: Reference PO
        if msgid in reference_translations:
            entry.msgstr = reference_translations[msgid]
            translated_from_reference_count += 1
            if verbose:
                print(f"[INFO] (Reference) Translation retrieved for '{msgid}': '{entry.msgstr}'")
        # Priority 2: CSV
        elif msgid_lower in csv_translations_lower:
            translation = csv_translations_lower[msgid_lower]
            entry.msgstr = match_case(msgid, translation)
            translated_from_csv_count += 1
            if verbose:
                print(f"[INFO] (CSV) Translation updated for '{msgid}': '{entry.msgstr}'")
        # Priority 3: DeepL
        elif not disable_api and deepl_api_key:
            translation = auto_translate(msgid, target_lang, deepl_api_key, debug)
            entry.msgstr = translation
            translated_from_deepl_count += 1
            if verbose:
                print(f"[INFO] (DeepL) Translation for '{msgid}': '{entry.msgstr}'")
        else:
            untranslated_count += 1
            if verbose:
                print(f"[INFO] (No processing) '{msgid}'. msgstr remains empty.")

        # New logic: Add entry to CSV only if a non-empty translation is available.
        if msgid not in csv_translations and entry.msgstr:
            new_csv_entries[msgid] = entry.msgstr

    output_file = pot_file.rsplit('.', 1)[0] + ".po"
    try:
        pot.save(output_file)
        print(f"[INFO] PO file generated: {output_file}")
    except Exception as e:
        print(f"[ERROR] Failed to save {output_file}: {e}")

    # Updating the CSV: writing new entries with the ';' separator
    added_to_csv_count = 0
    if new_csv_entries:
        try:
            with open(csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                for msgid, msgstr in new_csv_entries.items():
                    writer.writerow([msgid, msgstr])
                    added_to_csv_count += 1
                    if verbose:
                        print(f"[INFO] (CSV Update) Addition: '{msgid}' -> '{msgstr}'")
        except Exception as e:
            print(f"[ERROR] Error while adding entries to CSV file: {e}")

    # Final report
    print("\n[REPORT]")
    print(f"Translated from reference file: {translated_from_reference_count}")
    print(f"Translated from CSV: {translated_from_csv_count}")
    print(f"Translated via DeepL: {translated_from_deepl_count}")
    print(f"Untranslated: {untranslated_count}")
    print(f"Already Translated (initially present in the POT): {already_translated_count}")
    print(f"Added to CSV: {added_to_csv_count}")
    
    if debug:
        print("\n[DEBUG] List of untranslated entries:")
        for entry in pot:
            if not entry.msgstr:
                print(f"  - {entry.msgid}")

def main():
    parser = argparse.ArgumentParser(
        description=("Update a POT file with translations from a CSV file.\n"
                     "Case-insensitive search and adaptation of case to the msgid.\n"
                     "Optional use of a reference PO file to reassign old translations and update the CSV.")
    )
    parser.add_argument("pot", help="Path to the POT file to process")
    parser.add_argument("csv", help="Path to the CSV file containing translations")
    parser.add_argument("--target-lang", default="FR", help="Target language code (default: FR)")
    parser.add_argument("--deepl-api-key", default="", help="API key for DeepL (optional)")
    parser.add_argument("--disable-api", action="store_true", help="Disables the use of the DeepL API")
    parser.add_argument("--reference-po", help="Path to a reference PO file containing translations to reuse", default=None)
    parser.add_argument("--verbose", action="store_true", help="Enables verbose mode (more details)")
    parser.add_argument("--debug", action="store_true", help="Enables debug mode (debugging messages)")
    args = parser.parse_args()

    process_pot_file(args.pot, args.csv, args.target_lang, args.deepl_api_key, args.disable_api,
                     args.reference_po, args.verbose, args.debug)

if __name__ == "__main__":
    main()
