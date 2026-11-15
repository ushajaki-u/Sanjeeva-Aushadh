"""
03_Process_All_Drug_Label_Files.py   (EDA_full - full-dataset run)

Purpose
-------
Run the SAME allergen pipeline we built for the assignment across ALL openFDA
drug-label shards (not just one), and combine them into a single master dataset.

Single source of truth - no copied code
---------------------------------------
This file does NOT re-implement any allergen or route logic. It imports and reuses
the exact scripts that power the assignment EDA:

    ../EDA/01_DatasetCreation_4Status.py          (detection -> Dataset 1)
    ../EDA/02_DatasetCreation_AllergenSummary.py  (summaries -> Dataset 2)

Those two files are never modified. If a rule changes there, the full run uses it
automatically. This script only orchestrates: extract -> run 01 per shard ->
concatenate -> run 02 once on the combined file.

Folder layout (phase1_divya_drishti/)
-------------------------------------
    EDA/
        01_DatasetCreation_4Status.py            <- reused, unchanged
        02_DatasetCreation_AllergenSummary.py    <- reused, unchanged
    EDA_full/
        03_Process_All_Drug_Label_Files.py       <- this file
        raw_data/   <- drop the shard .zip downloads here
        output/     <- master dataset + summaries land here (git-ignored: ~800 MB)

Run it (from the EDA_full folder):
    py -3.14 03_Process_All_Drug_Label_Files.py
"""
from pathlib import Path
import importlib.util
import json
import re
import shutil
import zipfile

import pandas as pd

# --- Folders (this file lives in EDA_full) ---
PROJECT_FOLDER = Path(__file__).resolve().parent            # .../EDA_full
EDA_FOLDER = PROJECT_FOLDER.parent / "EDA"                  # the assignment code we reuse
RAW_DATA_FOLDER = PROJECT_FOLDER / "raw_data"
OUTPUT_FOLDER = PROJECT_FOLDER / "output"
TEMP_OUTPUT_FOLDER = OUTPUT_FOLDER / "per_file"             # one CSV per shard (kept for debugging)

# --- Reuse the EXISTING EDA scripts (never copied, never edited) ---
STEP1_SCRIPT = EDA_FOLDER / "01_DatasetCreation_4Status.py"
STEP2_SCRIPT = EDA_FOLDER / "02_DatasetCreation_AllergenSummary.py"

MASTER_DATASET_FILE = OUTPUT_FOLDER / "01_DatasetCreation_4Status_Output.csv"

# openFDA shard filenames look like: drug-label-0001-of-0014.json
PART_NAME_RE = re.compile(r"drug-label-(\d+)-of-(\d+)\.json$", re.IGNORECASE)


def load_module(script_path, module_name):
    """Load one of the EDA scripts as a module so we can call its functions directly."""
    script_path = Path(script_path)
    if not script_path.is_file():
        raise FileNotFoundError(
            f"Required EDA script not found:\n  {script_path}\n"
            "This file reuses the EDA code directly - the EDA folder must sit beside EDA_full."
        )
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_zip_archives(folder):
    """Every ZIP in raw_data, detected by CONTENT (Windows may show them named .json)."""
    return [p for p in sorted(Path(folder).iterdir())
            if p.is_file() and zipfile.is_zipfile(p)]


def extract_missing_json_files(raw_data_folder=RAW_DATA_FOLDER):
    """Extract each archive's JSON only if it is not already extracted."""
    raw_data_folder = Path(raw_data_folder)
    if not raw_data_folder.is_dir():
        raise FileNotFoundError(f"raw_data folder not found: {raw_data_folder}")

    for archive in find_zip_archives(raw_data_folder):
        with zipfile.ZipFile(archive, "r") as zip_file:
            json_members = [n for n in zip_file.namelist() if n.lower().endswith(".json")]
            if not json_members:
                raise ValueError(f"Archive contains no JSON file: {archive.name}")
            for member in json_members:
                destination = raw_data_folder / Path(member).name
                if destination.is_file():
                    continue
                print(f"Extracting {Path(member).name}  (from {archive.name})")
                with zip_file.open(member) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)

    return discover_json_parts(raw_data_folder)


def discover_json_parts(raw_data_folder=RAW_DATA_FOLDER):
    """Find the extracted JSON shards and confirm the set is COMPLETE (parts 1..N of N).

    The total N is read from the filenames' '-of-00NN' suffix - nothing is hardcoded,
    so this works whether openFDA ships 13, 14 or 15 shards.
    """
    raw_data_folder = Path(raw_data_folder)
    found, totals = {}, set()
    for path in sorted(raw_data_folder.iterdir()):
        if not path.is_file() or zipfile.is_zipfile(path):
            continue
        match = PART_NAME_RE.search(path.name)
        if match:
            found[int(match.group(1))] = path
            totals.add(int(match.group(2)))

    if not found:
        raise FileNotFoundError(
            f"No extracted 'drug-label-XXXX-of-YYYY.json' files in:\n  {raw_data_folder}\n"
            "Download the shard .zip files into raw_data first, then run this again."
        )
    if len(totals) != 1:
        raise ValueError(f"Inconsistent '-of-NN' totals across files: {sorted(totals)}")

    total = totals.pop()
    missing = [n for n in range(1, total + 1) if n not in found]
    if missing:
        raise FileNotFoundError(
            f"Expected {total} shards but these are missing:\n- "
            + "\n- ".join(f"drug-label-{n:04d}-of-{total:04d}.json" for n in missing)
        )
    ordered = [found[n] for n in range(1, total + 1)]
    print(f"Validated all {total} extracted JSON shards.")
    return ordered


def validate_json_file(json_path):
    """Confirm one shard is readable JSON with a non-empty results list; return its row count."""
    json_path = Path(json_path)
    if not json_path.is_file() or json_path.stat().st_size == 0:
        raise ValueError(f"Missing or empty JSON file: {json_path}")
    with json_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    records = payload.get("results", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list) or not records:
        raise ValueError(f"No medication records found in: {json_path.name}")
    return len(records)


def process_all_json_files(json_files, step1_module):
    """Run Step 1 (the EDA detector) on every shard and combine into one master CSV."""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEMP_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    dataframes, expected_total_rows = [], 0
    for index, json_file in enumerate(json_files, start=1):
        expected_total_rows += validate_json_file(json_file)
        part_output = TEMP_OUTPUT_FOLDER / f"{json_file.stem}_4status.csv"
        print(f"\n[{index}/{len(json_files)}] Processing {json_file.name}")
        # EXACT same detection code as the assignment - just called per shard.
        part_df = step1_module.process_drug_file(json_file, part_output)
        part_df.insert(0, "source_file", json_file.name)   # provenance (record_number restarts per shard)
        dataframes.append(part_df)

    master_df = pd.concat(dataframes, ignore_index=True)
    if len(master_df) != expected_total_rows:
        raise AssertionError(
            f"Combined row-count mismatch: expected {expected_total_rows:,}, found {len(master_df):,}.")

    master_df.to_csv(MASTER_DATASET_FILE, index=False, encoding="utf-8-sig")
    step1_module.validate_output(MASTER_DATASET_FILE, expected_rows=expected_total_rows)
    print(f"\nCombined Dataset 1 created: {MASTER_DATASET_FILE}")
    print(f"Combined medication records: {len(master_df):,}")
    return master_df


def run_summary(step2_module):
    """Run Step 2 (the EDA summariser) once, on the combined master."""
    print("\nCreating combined allergen summaries...")
    return step2_module.run(input_file=MASTER_DATASET_FILE, output_folder=OUTPUT_FOLDER)


def run():
    """Extract -> detect (per shard) -> combine -> summarise, reusing the EDA 01/02 code."""
    print("Starting the full-dataset Sanjeevini pipeline (reusing EDA 01 + 02)...")
    json_files = extract_missing_json_files(RAW_DATA_FOLDER)
    step1 = load_module(STEP1_SCRIPT, "dataset_creation_4status")
    step2 = load_module(STEP2_SCRIPT, "dataset_creation_allergen_summary")
    master_df = process_all_json_files(json_files, step1)
    summary_outputs = run_summary(step2)
    print("\nPipeline completed successfully.")
    return master_df, summary_outputs


if __name__ == "__main__":
    run()
