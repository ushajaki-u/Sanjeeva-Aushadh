import json
import re
from pathlib import Path
import pandas as pd

# ============================================================
# FILE CONFIGURATION
# ============================================================
PROJECT_FOLDER = Path(__file__).resolve().parent
RAW_DATA_FOLDER = PROJECT_FOLDER / "raw_data"
OUTPUT_FOLDER = PROJECT_FOLDER / "output"
DEFAULT_OUTPUT_FILE = OUTPUT_FOLDER / "01_DatasetCreation_4Status_Output.csv"

# ============================================================
# V1 ALLERGEN RULES
# Status values: Detected / Review / Not Detected / Unknown
#
# IMPORTANT:
# - Only APPROVED_SEARCH_FIELDS are scanned for allergens.
# - indications_and_usage is retained in the output, but is NOT
#   used for allergen detection.
# - This is a deterministic rule engine, not a clinical decision.
# ============================================================

APPROVED_SEARCH_FIELDS = [
    ("spl_product_data_elements",),
    ("openfda", "substance_name"),
    ("active_ingredient",),
    ("active_ingredient_table",),
    ("inactive_ingredient",),
    ("description",),
]

FIELD_LABELS = {
    "spl_product_data_elements": "SPL product data elements",
    "openfda.substance_name": "openFDA substance name",
    "active_ingredient": "active ingredients",
    "active_ingredient_table": "active ingredient table",
    "inactive_ingredient": "inactive ingredients",
    "description": "description",
}

# direct_terms: a match can produce Detected
# review_terms: a match produces Review unless a direct term also exists
# exclusions: exact phrases that suppress only the overlapping match
ALLERGEN_RULES = {
    "Milk": {
        "direct_terms": [
            "milk", "cow milk", "cow's milk", "cows' milk", "bovine milk",
            "milk protein", "cow milk protein", "milk protein concentrate",
            "milk protein isolate", "milk powder", "dried milk", "dry milk",
            "nonfat dry milk", "skim milk", "skimmed milk", "milk solids",
            "nonfat milk solids", "milk solids nonfat", "whole milk solids",
            "casein", "caseinate", "sodium caseinate", "calcium caseinate",
            "potassium caseinate", "magnesium caseinate", "ammonium caseinate",
            "hydrolyzed casein", "casein hydrolysate", "bovine casein",
            "casamino acid", "casamino acids", "whey", "whey protein",
            "whey protein concentrate", "whey protein isolate", "hydrolyzed whey",
            "whey powder", "sweet whey", "acid whey", "lactalbumin",
            "alpha lactalbumin", "alpha-lactalbumin", "α-lactalbumin",
            "lactoglobulin", "beta lactoglobulin", "beta-lactoglobulin",
            "β-lactoglobulin", "lactose", "lactose monohydrate",
            "lactose anhydrous", "anhydrous lactose", "hydrous lactose",
            "lactose hydrous", "spray dried lactose", "spray-dried lactose",
            "buttermilk", "cheese", "cheese powder", "yogurt", "yoghurt",
            "curd", "curds", "ghee", "butterfat", "butter oil", "milk fat",
            "anhydrous milk fat", "butter", "cream",
        ],
        "review_terms": [
            "lactulose", "albumin", "protein hydrolysate",
        ],
        "exclusions": [
            "coconut milk", "oat milk", "almond milk", "soy milk",
            "soybean milk", "rice milk", "cashew milk", "hemp milk",
            "pea milk", "flax milk", "macadamia milk", "hazelnut milk",
            "pistachio milk", "cocoa butter", "cacao butter", "shea butter",
            "coconut butter", "almond butter", "peanut butter", "cashew butter",
            "pistachio butter", "mango butter", "kokum butter", "seed butter",
            "sunflower seed butter", "butter flavor", "butter flavoring",
            "cream colored", "cream-coloured", "cream coloured", "topical cream",
        ],
    },
    "Eggs": {
        "direct_terms": [
            "egg", "eggs", "egg protein", "egg-derived protein", "egg derived protein",
            "egg white", "egg whites", "egg yolk", "egg yolks", "dried egg",
            "powdered egg", "whole egg", "hen egg", "chicken egg", "egg albumin",
            "egg albumen", "albumen", "ovalbumin", "ovomucoid", "ovomucin",
            "ovotransferrin", "conalbumin", "ovoglobulin", "ovoglobulin g2",
            "ovoglobulin g3", "egg lysozyme", "livetin", "alpha livetin",
            "alpha-livetin", "α-livetin", "vitellin", "ovovitellin", "phosvitin",
            "apovitellenin", "egg lecithin", "egg phospholipid", "egg phosphatide",
            "ovomucoid trypsin inhibitor", "residual egg protein", "residual ovalbumin",
            "albumin egg", "embryonated chicken egg", "embryonated hen egg",
            "embryonated eggs", "egg-grown", "egg grown", "egg-based vaccine",
            "egg based vaccine", "propagated in eggs", "grown in eggs",
        ],
        "review_terms": [
            "albumin", "globulin", "lecithin", "lysozyme", "chick embryo",
            "chicken embryo", "embryo", "chicken protein", "avian protein",
        ],
        "exclusions": [
            "eggplant", "egg plant", "human serum albumin",
            "recombinant human albumin", "bovine serum albumin",
            "serum albumin human", "serum albumin bovine", "soy lecithin",
            "soybean lecithin", "sunflower lecithin", "rapeseed lecithin",
            "synthetic lecithin",
        ],
    },
    "Wheat": {
        "direct_terms": [
            "wheat", "wheat flour", "wheat starch", "wheat gluten", "gluten",
            "semolina", "spelt", "kamut", "khorasan wheat", "triticale",
            "durum", "farina", "bulgur", "seitan",
        ],
        "review_terms": ["flour", "starch", "dextrin", "maltodextrin"],
        "exclusions": ["rice flour", "corn flour", "maize flour", "oat flour",
                       "potato starch", "corn starch", "maize starch", "rice starch",
                       "tapioca starch"],
    },
    "Sesame": {
        "direct_terms": [
            "sesame", "sesame seed", "sesame oil", "sesame flour", "sesame protein",
            "tahini", "benne", "benne seed", "gingelly", "til",
        ],
        "review_terms": [],
        "exclusions": [],
    },
    "Tree nuts": {
        "direct_terms": [
            "tree nut", "tree nuts", "almond", "brazil nut", "cashew", "chestnut",
            "hazelnut", "filbert", "hickory nut", "macadamia", "pecan", "pistachio",
            "walnut", "beechnut", "butternut", "pine nut", "pignoli", "praline",
            "marzipan", "nut meal", "nut flour", "nut oil",
        ],
        "review_terms": ["nuts", "nut"],
        "exclusions": [
            "coconut", "coconut oil", "coconut milk", "coconut butter", "nutmeg",
            "water chestnut", "peanut", "peanuts", "areca nut", "betel nut",
        ],
    },
    "Peanuts": {
        "direct_terms": [
            "peanut", "peanuts", "arachis", "arachis hypogaea", "groundnut",
            "groundnuts", "peanut protein", "peanut oil", "peanut flour",
        ],
        "review_terms": [],
        "exclusions": [],
    },
    "Soy": {
        "direct_terms": [
            "soy", "soya", "soybean", "soy bean", "soy protein", "soy protein isolate",
            "soy flour", "soy oil", "soybean oil", "soy lecithin", "soybean lecithin",
            "tofu", "edamame", "miso", "tempeh", "textured vegetable protein",
        ],
        "review_terms": ["lecithin", "vegetable protein", "hydrolyzed vegetable protein"],
        "exclusions": ["egg lecithin", "sunflower lecithin", "rapeseed lecithin"],
    },
}

STATUS_VALUES = ("Detected", "Review", "Not Detected", "Unknown")


def to_text(value):
    """Convert JSON scalars/lists/dicts into readable text."""
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(to_text(item) for item in value if to_text(item))
    if isinstance(value, dict):
        return " | ".join(to_text(item) for item in value.values() if to_text(item))
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null"} else text


def get_nested(record, path):
    value = record
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def normalize_text(text):
    text = str(text).lower()
    text = text.replace("’", "'").replace("–", "-").replace("—", "-")
    text = re.sub(r"[^\w\s'αβ-]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def term_pattern(term):
    """Phrase-aware, case-insensitive pattern with flexible spaces/hyphens."""
    normalized = normalize_text(term)
    pieces = [re.escape(piece) for piece in re.split(r"[\s-]+", normalized) if piece]
    return r"(?<!\w)" + r"[\s-]+".join(pieces) + r"(?!\w)"


def spans_for(text, phrases):
    spans = []
    for phrase in sorted(set(phrases), key=len, reverse=True):
        for match in re.finditer(term_pattern(phrase), text, flags=re.IGNORECASE):
            spans.append((match.start(), match.end(), phrase, match.group(0)))
    return spans


def overlaps(span_a, span_b):
    return span_a[0] < span_b[1] and span_b[0] < span_a[1]


def approved_text_fields(record):
    """Return only the approved allergen-search fields that have usable text."""
    fields = []
    for path in APPROVED_SEARCH_FIELDS:
        value = get_nested(record, path)
        text = to_text(value)
        if text:
            field_path = ".".join(path)
            fields.append({
                "field_path": field_path,
                "field_label": FIELD_LABELS.get(field_path, field_path),
                "text": text,
            })
    return fields


def match_allergen_in_field(field_text, rules):
    """Find valid direct/review matches after removing overlapping exclusions."""
    normalized = normalize_text(field_text)
    exclusions = spans_for(normalized, rules.get("exclusions", []))
    direct = spans_for(normalized, rules.get("direct_terms", []))
    review = spans_for(normalized, rules.get("review_terms", []))

    valid_direct = [m for m in direct if not any(overlaps(m, e) for e in exclusions)]
    valid_review = [m for m in review if not any(overlaps(m, e) for e in exclusions)]
    suppressed = [m for m in direct + review if any(overlaps(m, e) for e in exclusions)]

    return valid_direct, valid_review, suppressed


def scan_allergens(record):
    fields = approved_text_fields(record)
    results = {}

    for allergen, rules in ALLERGEN_RULES.items():
        direct_evidence = []
        review_evidence = []
        excluded_evidence = []

        for field in fields:
            direct, review, suppressed = match_allergen_in_field(field["text"], rules)

            for _, _, rule_term, actual_text in direct:
                direct_evidence.append({
                    "term": rule_term,
                    "matched_text": actual_text,
                    "field_path": field["field_path"],
                    "field_label": field["field_label"],
                    "rule": "direct_term_match",
                })

            for _, _, rule_term, actual_text in review:
                review_evidence.append({
                    "term": rule_term,
                    "matched_text": actual_text,
                    "field_path": field["field_path"],
                    "field_label": field["field_label"],
                    "rule": "context_review_term",
                })

            for _, _, rule_term, actual_text in suppressed:
                excluded_evidence.append({
                    "term": rule_term,
                    "matched_text": actual_text,
                    "field_path": field["field_path"],
                    "field_label": field["field_label"],
                    "rule": "excluded_phrase_overlap",
                })

        if direct_evidence:
            status = "Detected"
            primary_evidence = direct_evidence
            reason = "Direct allergen term found in an approved source field."
        elif review_evidence:
            status = "Review"
            primary_evidence = review_evidence
            reason = "Only context-sensitive allergen term(s) found; human review is required."
        elif fields:
            status = "Not Detected"
            primary_evidence = []
            if excluded_evidence:
                reason = "Approved fields were searched; only excluded phrase match(es) were found."
            else:
                reason = "Approved fields contained usable data, but no valid allergen term was found."
        else:
            status = "Unknown"
            primary_evidence = []
            reason = "No usable data was present in any approved allergen-search field."

        matched_terms = sorted({item["term"] for item in primary_evidence})
        source_paths = sorted({item["field_path"] for item in primary_evidence})
        source_labels = sorted({item["field_label"] for item in primary_evidence})
        excluded_terms = sorted({item["term"] for item in excluded_evidence})

        if primary_evidence:
            detail = "; ".join(
                f"'{item['matched_text']}' found in {item['field_label']} ({item['field_path']})"
                for item in primary_evidence
            )
            explanation = f"{status}: {detail}."
        elif excluded_evidence:
            detail = "; ".join(
                f"excluded '{item['matched_text']}' in {item['field_label']} ({item['field_path']})"
                for item in excluded_evidence
            )
            explanation = f"{status}: {detail}. {reason}"
        else:
            explanation = f"{status}: {reason}"

        results[allergen] = {
            "status": status,
            "matched_terms": matched_terms,
            "source_paths": source_paths,
            "source_labels": source_labels,
            "excluded_terms": excluded_terms,
            "reason": reason,
            "explanation": explanation,
        }

    return results, fields


def clean_column_name(allergen):
    return re.sub(r"[^a-z0-9]+", "_", allergen.lower()).strip("_")


def first_text(record, *keys):
    for key in keys:
        text = to_text(record.get(key))
        if text:
            return text
    return ""


def process_drug_file(input_file, output_file=DEFAULT_OUTPUT_FILE):
    """Validate one FDA JSON file, create Dataset 1, and validate its CSV output."""
    input_path = Path(input_file)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input JSON not found:\n{input_path}")
    if input_path.suffix.lower() != ".json":
        raise ValueError(f"Input must be a JSON file: {input_path.name}")
    if input_path.stat().st_size == 0:
        raise ValueError(f"Input JSON is empty: {input_path.name}")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as file:
        json_data = json.load(file)

    records = json_data.get("results", []) if isinstance(json_data, dict) else json_data
    if not isinstance(records, list) or not records:
        raise ValueError("No records were found. Expected a JSON 'results' list or a top-level list.")

    output_rows = []

    for record_number, record in enumerate(records, start=1):
        openfda = record.get("openfda", {}) or {}
        allergen_results, searchable_fields = scan_allergens(record)

        row = {
            "record_number": record_number,
            "id": record.get("id", ""),
            "set_id": record.get("set_id", ""),
            "brand_name": to_text(openfda.get("brand_name")),
            "generic_name": to_text(openfda.get("generic_name")),
            "manufacturer_name": to_text(openfda.get("manufacturer_name")),
            "product_ndc": to_text(openfda.get("product_ndc")),
            "product_type": to_text(openfda.get("product_type")),
            "route": to_text(openfda.get("route")),
            "substance_name": to_text(openfda.get("substance_name")),
            "active_ingredient": to_text(record.get("active_ingredient")),
            "active_ingredient_table": to_text(record.get("active_ingredient_table")),
            "inactive_ingredient": to_text(record.get("inactive_ingredient")),
            "spl_product_data_elements": to_text(record.get("spl_product_data_elements")),
            "description": to_text(record.get("description")),
            "indications_and_usage": to_text(record.get("indications_and_usage")),
            "allergen_search_fields_available": " | ".join(
                field["field_path"] for field in searchable_fields
            ),
        }

        for allergen, result in allergen_results.items():
            name = clean_column_name(allergen)
            row[f"{name}_status"] = result["status"]
            row[f"{name}_matched_terms"] = " | ".join(result["matched_terms"])
            row[f"{name}_source_fields"] = " | ".join(result["source_paths"])
            row[f"{name}_explanation"] = result["explanation"]

        output_rows.append(row)

        if record_number % 1000 == 0:
            print(f"Processed {record_number:,} of {len(records):,}")

    df = pd.DataFrame(output_rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    validate_output(output_path, expected_rows=len(records))

    print("DONE")
    print(f"Records processed: {len(df):,}")
    print(f"CSV created: {output_path}")
    return df


def validate_output(output_path, expected_rows):
    """Validate that Dataset 1 exists, is readable, and contains the expected data."""
    output_path = Path(output_path)
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise ValueError(f"Dataset 1 output is missing or empty: {output_path}")

    result = pd.read_csv(output_path, low_memory=False)
    required = {"record_number", "id", "set_id", "indications_and_usage"}
    required.update(f"{clean_column_name(name)}_status" for name in ALLERGEN_RULES)
    missing = sorted(required - set(result.columns))
    if missing:
        raise ValueError(f"Dataset 1 output is missing columns: {', '.join(missing)}")
    if len(result) != expected_rows:
        raise ValueError(
            f"Dataset 1 row-count mismatch: expected {expected_rows:,}, found {len(result):,}."
        )

    allowed = set(STATUS_VALUES)
    for name in ALLERGEN_RULES:
        column = f"{clean_column_name(name)}_status"
        invalid = set(result[column].dropna().astype(str)) - allowed
        if invalid:
            raise ValueError(f"Invalid values in {column}: {sorted(invalid)}")
    return True


def discover_single_json(raw_data_folder=RAW_DATA_FOLDER):
    """Return the only JSON input in raw_data; require an explicit choice if there are several."""
    folder = Path(raw_data_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"raw_data folder not found:\n{folder}")
    files = sorted(folder.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON file found in:\n{folder}")
    if len(files) > 1:
        names = "\n- ".join(path.name for path in files)
        raise ValueError(
            "This version processes one JSON file at a time. "
            f"Keep one JSON in raw_data or call run(input_file=...). Found:\n- {names}"
        )
    return files[0]


def run(input_file=None, output_file=DEFAULT_OUTPUT_FILE):
    """Independent Step 1 entry point used directly or by 05_Main.py."""
    selected_input = Path(input_file) if input_file else discover_single_json()
    return process_drug_file(selected_input, output_file)


if __name__ == "__main__":
    run()
