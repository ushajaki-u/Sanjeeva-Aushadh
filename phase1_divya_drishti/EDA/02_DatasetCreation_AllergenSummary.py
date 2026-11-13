"""02_DatasetCreation_AllergenSummary.py

Reads the medication-level CSV created by 01_DatasetCreation_4Status.py and creates:
1. allergen_summary.csv
2. overall_allergen_summary.csv
3. allergen_status_breakdown.csv  (long/chart-ready format)

This script does not re-run allergen detection and does not modify Dataset 1.
"""
from pathlib import Path
import pandas as pd

# ============================================================
# CONFIGURATION
# ============================================================

# Project-relative files allow this step to run independently or through 05_Main.py.
PROJECT_FOLDER = Path(__file__).resolve().parent
OUTPUT_FOLDER = PROJECT_FOLDER / "output"
INPUT_FILE = OUTPUT_FOLDER / "01_DatasetCreation_4Status_Output.csv"
PRIMARY_OUTPUT_FILE = OUTPUT_FOLDER / "02_DatasetCreation_AllergenSummary_Output.csv"

STATUS_ORDER = ["Detected", "Review", "Not Detected", "Unknown"]

# Display name mapped to the exact Dataset 1 status column.
ALLERGEN_STATUS_COLUMNS = {
    "Milk": "milk_status",
    "Eggs": "eggs_status",
    "Wheat": "wheat_status",
    "Sesame": "sesame_status",
    "Tree Nuts": "tree_nuts_status",
    "Peanuts": "peanuts_status",
    "Soy": "soy_status",
    "Alpha-Gal": "alpha_gal_status",
}

# Overall medication status follows the agreed priority.
OVERALL_PRIORITY = ["Detected", "Review", "Unknown", "Not Detected"]


# ============================================================
# VALIDATION AND CLEANING
# ============================================================

def validate_input(df: pd.DataFrame) -> None:
    """Confirm that all required allergen status columns are present."""
    missing = [
        column
        for column in ALLERGEN_STATUS_COLUMNS.values()
        if column not in df.columns
    ]
    if missing:
        raise ValueError(
            "The input CSV is missing required status columns: "
            + ", ".join(missing)
        )


def normalize_status_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize status text and convert unexpected values to Unknown.
    This prevents blanks or spelling variations from disappearing silently.
    """
    cleaned = df.copy()
    accepted = {status.lower(): status for status in STATUS_ORDER}

    for column in ALLERGEN_STATUS_COLUMNS.values():
        normalized = (
            cleaned[column]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .str.lower()
        )
        cleaned[column] = normalized.map(accepted).fillna("Unknown")

    return cleaned


# ============================================================
# OVERALL MEDICATION STATUS
# ============================================================

def calculate_overall_status(row: pd.Series) -> str:
    """
    Apply the agreed medication-level roll-up rule:
    Detected > Review > Unknown > Not Detected.
    """
    values = {
        row[column]
        for column in ALLERGEN_STATUS_COLUMNS.values()
    }

    for status in OVERALL_PRIORITY:
        if status in values:
            return status

    # Defensive fallback; normalized data should never reach this line.
    return "Unknown"


# ============================================================
# SUMMARY DATASETS
# ============================================================

def create_allergen_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create one summary row per allergen with counts and percentages."""
    total_records = len(df)
    rows = []

    for allergen, column in ALLERGEN_STATUS_COLUMNS.items():
        counts = df[column].value_counts().reindex(STATUS_ORDER, fill_value=0)

        row = {
            "Allergen": allergen,
            "Detected_Count": int(counts["Detected"]),
            "Review_Count": int(counts["Review"]),
            "Not_Detected_Count": int(counts["Not Detected"]),
            "Unknown_Count": int(counts["Unknown"]),
            "Total_Records": int(total_records),
        }

        for status in STATUS_ORDER:
            output_name = status.replace(" ", "_") + "_Pct"
            row[output_name] = round(
                (counts[status] / total_records * 100) if total_records else 0,
                2,
            )

        # Useful quality metric for prioritizing rule improvements.
        unresolved_count = counts["Review"] + counts["Unknown"]
        row["Unresolved_Count"] = int(unresolved_count)
        row["Unresolved_Pct"] = round(
            (unresolved_count / total_records * 100) if total_records else 0,
            2,
        )
        rows.append(row)

    summary = pd.DataFrame(rows)
    return summary.sort_values(
        by=["Detected_Pct", "Detected_Count"],
        ascending=False,
    ).reset_index(drop=True)


def create_overall_summary(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create the medication-level overall status and its aggregate summary.
    Returns both the aggregate summary and the detailed dataframe containing
    the derived overall_status column for traceability during QA.
    """
    detail_with_overall = df.copy()
    detail_with_overall["overall_status"] = detail_with_overall.apply(
        calculate_overall_status,
        axis=1,
    )

    total_records = len(detail_with_overall)
    counts = (
        detail_with_overall["overall_status"]
        .value_counts()
        .reindex(STATUS_ORDER, fill_value=0)
    )

    overall_summary = pd.DataFrame({
        "Overall_Status": STATUS_ORDER,
        "Count": [int(counts[status]) for status in STATUS_ORDER],
        "Percentage": [
            round((counts[status] / total_records * 100) if total_records else 0, 2)
            for status in STATUS_ORDER
        ],
        "Total_Records": total_records,
    })

    return overall_summary, detail_with_overall


def create_chart_ready_breakdown(allergen_summary: pd.DataFrame) -> pd.DataFrame:
    """Convert the wide allergen summary to long format for charts."""
    rows = []

    for _, item in allergen_summary.iterrows():
        for status in STATUS_ORDER:
            prefix = status.replace(" ", "_")
            rows.append({
                "Allergen": item["Allergen"],
                "Status": status,
                "Count": int(item[f"{prefix}_Count"]),
                "Percentage": float(item[f"{prefix}_Pct"]),
                "Total_Records": int(item["Total_Records"]),
            })

    return pd.DataFrame(rows)


# ============================================================
# MAIN PROCESS
# ============================================================

def create_summary_files(input_file=INPUT_FILE, output_folder=None):
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found:\n{input_path}")

    destination = Path(output_folder) if output_folder else OUTPUT_FOLDER
    destination.mkdir(parents=True, exist_ok=True)

    print(f"Reading: {input_path}")
    df = pd.read_csv(input_path, low_memory=False)
    print(f"Medication records found: {len(df):,}")
    if df.empty:
        raise ValueError("Dataset 1 is empty; summary creation cannot continue.")

    validate_input(df)
    df = normalize_status_columns(df)

    allergen_summary = create_allergen_summary(df)
    overall_summary, detail_with_overall = create_overall_summary(df)
    chart_ready = create_chart_ready_breakdown(allergen_summary)

    allergen_summary_path = destination / PRIMARY_OUTPUT_FILE.name
    overall_summary_path = destination / "overall_allergen_summary.csv"
    chart_ready_path = destination / "allergen_status_breakdown.csv"

    allergen_summary.to_csv(
        allergen_summary_path,
        index=False,
        encoding="utf-8-sig",
    )
    overall_summary.to_csv(
        overall_summary_path,
        index=False,
        encoding="utf-8-sig",
    )
    chart_ready.to_csv(
        chart_ready_path,
        index=False,
        encoding="utf-8-sig",
    )

    # QA checks: every allergen and overall-status count must reconcile
    # to the input medication-record count.
    expected_total = len(df)
    for _, row in allergen_summary.iterrows():
        status_total = (
            row["Detected_Count"]
            + row["Review_Count"]
            + row["Not_Detected_Count"]
            + row["Unknown_Count"]
        )
        if int(status_total) != expected_total:
            raise AssertionError(
                f"Count reconciliation failed for {row['Allergen']}."
            )

    if int(overall_summary["Count"].sum()) != expected_total:
        raise AssertionError("Overall-status count reconciliation failed.")

    print("\nCreated:")
    print(allergen_summary_path)
    print(overall_summary_path)
    print(chart_ready_path)
    validate_summary_outputs(
        allergen_summary_path,
        overall_summary_path,
        chart_ready_path,
        expected_records=len(df),
    )
    print("\nAll counts reconciled to the input record count.")

    return {
        "allergen_summary": allergen_summary,
        "overall_allergen_summary": overall_summary,
        "allergen_status_breakdown": chart_ready,
        "detail_with_overall_status": detail_with_overall,
    }


def validate_summary_outputs(summary_path, overall_path, breakdown_path, expected_records):
    """Validate that all Dataset 2 outputs exist, are readable, and reconcile."""
    for path in (summary_path, overall_path, breakdown_path):
        path = Path(path)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Summary output is missing or empty: {path}")

    summary = pd.read_csv(summary_path)
    count_columns = [
        "Detected_Count", "Review_Count", "Not_Detected_Count", "Unknown_Count"
    ]
    if summary.empty or not (summary[count_columns].sum(axis=1) == expected_records).all():
        raise ValueError("Allergen summary counts do not reconcile to Dataset 1.")

    overall = pd.read_csv(overall_path)
    if int(overall["Count"].sum()) != expected_records:
        raise ValueError("Overall summary counts do not reconcile to Dataset 1.")

    breakdown = pd.read_csv(breakdown_path)
    expected_rows = len(ALLERGEN_STATUS_COLUMNS) * len(STATUS_ORDER)
    if len(breakdown) != expected_rows:
        raise ValueError(
            f"Chart-ready breakdown should contain {expected_rows} rows; found {len(breakdown)}."
        )
    return True


def run(input_file=INPUT_FILE, output_folder=OUTPUT_FOLDER):
    """Independent Step 2 entry point used directly or by 05_Main.py."""
    return create_summary_files(input_file, output_folder)


if __name__ == "__main__":
    outputs = run()
    print("\nAllergen summary preview:")
    print(outputs["allergen_summary"].to_string(index=False))
    print("\nOverall allergen summary:")
    print(outputs["overall_allergen_summary"].to_string(index=False))
