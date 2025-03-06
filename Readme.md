# Translate POT Files Using CSV and Reference PO

This script updates a POT file with translations drawn from multiple sources. It uses translations from:
1. A reference PO file (if provided) – exact match (case-sensitive) on `msgid`.
2. A CSV file – the CSV is read with a comma (`,`) separator and searched case-insensitively.
3. The DeepL API – used if no translation is found via the above sources (if enabled).

A final report is printed with counts for:
- Translations obtained from the reference PO.
- Translations obtained from the CSV.
- Translations generated via DeepL.
- Untranslated entries.
- Entries already translated in the POT.

## Requirements

- Python 3.x  
- The Python packages: `polib`, `deepl`  
  Install via pip if necessary:
pip install polib deepl

## Usage

Run the script from the command line as follows:

python translate_po.py <pot_file> <csv_file> [options]

### Positional Arguments
- `pot_file`: Path to the POT file to process.
- `csv_file`: Path to the CSV file containing translations.  
  **Note:** The CSV must use the comma (`,`) delimiter.

### Optional Arguments
- `--target-lang`: Target language code for DeepL translations (default: `FR`).
- `--deepl-api-key`: Your DeepL API key (needed only if using DeepL for translations).
- `--disable-api`: Disables the use of the DeepL API.
- `--reference-po`: Path to a reference PO file; if provided, its translations are used with highest priority.
- `--verbose`: Enables verbose mode to print additional details.
- `--debug`: Enables debug mode to display detailed debugging messages.

## Example Command

python translate_po.py path/to/file.pot path/to/translations.csv --reference-po path/to/reference.po --verbose --debug

## Final Report

At the end of execution, you will see a summary like this:


This report helps you understand how many entries were processed and their sources of translation.
