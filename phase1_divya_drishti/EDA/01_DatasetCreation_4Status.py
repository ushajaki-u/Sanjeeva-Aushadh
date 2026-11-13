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
            "durum", "farina", "bulgur", "seitan","cracked wheat", "wheat bran", "wheat germ", "wheat protein",
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
    "Alpha_Gal": {
        # Alpha-gal syndrome: reaction to mammalian (non-primate) material.
        # Covers gelatin/collagen, mammalian meats/fats, and mammalian-derived drugs/biologics.
        "direct_terms": [
            # Gelatin & collagen (capsules, surgical, supplements)
            "gelatin", "gelatine", "bovine gelatin", "porcine gelatin",
            "kosher gelatin", "halal gelatin", "hydrolyzed gelatin",
            "gelatin hydrolysate", "succinylated gelatin", "modified fluid gelatin",
            "polygeline", "oxipolygelatin", "urea-linked gelatin",
            "gelatin crosspolymer", "absorbable gelatin", "absorbable gelatin sponge",
            "absorbable gelatin powder", "absorbable gelatin film",
            "gelatin-thrombin matrix", "gelatin capsule", "gelatin capsules",
            "hard gelatin capsule", "soft gelatin capsule", "softgel", "softgels",
            "e441", "e-441", "9000-70-8",
            "bovine collagen", "porcine collagen", "mammalian collagen",
            "hydrolyzed bovine collagen", "hydrolyzed porcine collagen",
            "bovine collagen peptides", "porcine collagen peptides",
            "hydrolyzed animal protein", "animal protein hydrolysate",
            "sodium lauryl hydrolyzed collagen", "potassium cocoyl hydrolyzed collagen",
            "amp-isostearoyl hydrolyzed collagen",
            "gelfoam", "surgifoam", "gelfilm", "floseal", "surgiflo",
            "gelofusine", "haemaccel", "aspic",
            # Mammalian meats, game & culinary extracts
            "beef", "veal", "pork", "ham", "bacon", "prosciutto", "pancetta",
            "pepperoni", "salami", "chorizo", "sausage", "hot dog", "bologna",
            "lamb", "mutton", "goat", "chevon", "venison", "deer", "elk",
            "bison", "buffalo", "boar", "wild boar", "rabbit", "hare",
            "squirrel", "kangaroo", "horse", "red meat", "mammalian meat",
            "organ meat", "offal", "liver", "kidney", "tripe", "sweetbreads",
            "tongue", "oxtail", "marrow", "bone marrow",
            "tallow", "beef tallow", "mutton tallow", "dripping", "beef dripping",
            "lard", "pork lard", "leaf lard", "suet", "schmaltz", "fatback",
            "salt pork", "pork fat", "beef fat", "lamb fat", "animal fat",
            "animal shortening", "oleo", "oleostearin", "oleomargarine",
            "beef extract", "beef broth", "beef stock", "beef bouillon",
            "pork broth", "pork stock", "pork bouillon", "lamb stock",
            "veal stock", "demi-glace", "meat extract", "meat broth",
            "rennet", "animal rennet", "calf rennet", "pepsin", "porcine pepsin",
            # Mammalian active drugs, biologics & topical bases
            "heparin", "heparin sodium", "heparin calcium", "porcine heparin",
            "bovine heparin", "unfractionated heparin", "enoxaparin", "lovenox",
            "dalteparin", "fragmin", "tinzaparin",
            "cetuximab", "erbitux",
            "desiccated thyroid", "natural desiccated thyroid", "thyroid usp",
            "armour thyroid", "np thyroid", "nature-throid", "wp thyroid",
            "pancrelipase", "pancreatin", "creon", "zenpep", "pancreaze",
            "pertzye", "viokace",
            "poractant alfa", "curosurf", "beractant", "survanta", "calfactant", "infasurf",
            "hyaluronidase", "amphadase", "hydase", "vitrase",
            "thrombin", "bovine thrombin", "thrombin-jmi", "recothrom",
            "antivenom", "antivenin", "crofab", "anavip",
            "lanolin", "wool fat", "wool wax", "wool alcohol", "adeps lanae",
            "animal cholesterol", "ovine cholesterol", "mammalian squalene",
            "placenta extract", "bovine serum", "fetal bovine serum",
            "bovine serum albumin",
        ],
        "review_terms": [
            "collagen", "hydrolyzed collagen", "collagen hydrolysate",
            "collagen peptides", "soluble collagen", "native collagen",
            "atelocollagen", "type i collagen", "type ii collagen",
            "type iii collagen", "type 1 collagen", "type 2 collagen",
            "type 3 collagen", "hydrolyzed elastin", "elastin",
            "bone broth", "bone broth protein", "bone marrow extract",
            "cartilage extract", "isinglass", "glycine", "hydroxyproline",
            "magnesium stearate", "stearic acid", "calcium stearate",
            "zinc stearate", "sodium stearate", "sodium stearyl fumarate",
            "glyceryl monostearate", "glyceryl distearate", "glyceryl tristearate",
            "sorbitan monostearate", "peg stearate", "polyoxyl stearate",
            "glycerin", "glycerine", "glycerol",
            "polysorbate 80", "polysorbate 60", "polysorbate 40", "polysorbate 20",
            "oleic acid", "palmitic acid", "myristic acid", "caprylic acid",
            "fatty acids", "mono- and diglycerides", "monoglycerides", "diglycerides",
            "cholesterol", "squalene", "lecithin", "taurine", "l-cysteine", "cysteine",
            "vitamin d3", "cholecalciferol",
            "lactose", "lactose monohydrate", "lactose anhydrous",
            "anhydrous lactose", "spray-dried lactose", "spray dried lactose",
            "capsule", "capsules", "beadlets", "microencapsulated",
            "marshmallow", "marshmallows", "gummy", "gummies",
            "confectioner's glaze", "confectioners glaze",
            "natural flavor", "natural flavors", "natural flavoring",
            "meat flavor", "savory flavor", "broth", "stock", "bouillon",
            "shortening", "enzymes", "lipase", "amylase", "protease",
        ],
        "exclusions": [
            "chicken", "turkey", "duck", "goose", "quail", "pheasant",
            "ostrich", "emu", "poultry", "fowl", "bird", "avian",
            "fish", "salmon", "tuna", "cod", "tilapia", "trout", "halibut",
            "sardine", "anchovy", "shrimp", "prawn", "crab", "lobster",
            "clam", "mussel", "oyster", "scallop", "squid", "calamari",
            "octopus", "seafood", "shellfish", "crustacean", "mollusk",
            "chicken broth", "chicken stock", "chicken bouillon",
            "turkey broth", "turkey stock", "turkey bacon", "turkey sausage",
            "chicken sausage", "duck fat", "goose fat",
            "fish gelatin", "piscine gelatin", "marine gelatin",
            "fish collagen", "marine collagen", "piscine collagen",
            "hydrolyzed fish collagen", "hydrolyzed marine collagen",
            "chicken collagen", "avian collagen", "eggshell membrane collagen",
            "vegan gelatin", "vegetarian gelatin", "plant gelatin",
            "agar", "agar-agar", "agar agar", "pectin", "carrageenan",
            "hypromellose", "hpmc", "hydroxypropyl methylcellulose",
            "pullulan", "modified cellulose", "vegetable cellulose",
            "microcrystalline cellulose", "croscarmellose sodium",
            "sodium starch glycolate", "povidone", "copovidone",
            "polyethylene glycol", "peg", "vegetable glycerin",
            "vegetable magnesium stearate", "vegetable stearic acid",
            "vegan capsule", "vegetarian capsule", "veggie capsule",
            "plant-based capsule", "konjac", "konjac gum", "xanthan gum",
            "guar gum", "locust bean gum", "carob bean gum",
            "acacia gum", "gum arabic", "vegetable shortening",
            "plant-based", "vegan", "vegetarian", "beefsteak tomato",
            "buffalo sauce", "buffalo wing", "buffalo wings",
            "buffalo cauliflower", "butternut squash", "peanut", "walnut",
            "chestnut", "hazelnut", "coconut", "almond", "soy", "tofu",
            "tempeh", "seitan", "microbial rennet", "vegetable rennet",
            "plant-derived squalane", "olive squalane", "sugarcane squalane",
            "synthetic thrombin", "recombinant",
        ],
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


def _term_core(term):
    """Inner regex for one phrase (flexible spaces/hyphens), WITHOUT word boundaries."""
    normalized = normalize_text(term)
    pieces = [re.escape(piece) for piece in re.split(r"[\s-]+", normalized) if piece]
    return r"[\s-]+".join(pieces)


def _build_combined(terms):
    """Compile ONE alternation regex for a whole term list (longest phrase first), or None.

    Performance: instead of scanning the text once per term (hundreds of scans for
    Alpha-Gal), we scan once with a single combined pattern compiled a single time.
    """
    cores = [c for c in (_term_core(t) for t in sorted(set(terms), key=len, reverse=True)) if c]
    if not cores:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(cores) + r")(?!\w)", flags=re.IGNORECASE)


def _spans(text, compiled):
    if compiled is None:
        return []
    return [(m.start(), m.end(), m.group(0), m.group(0)) for m in compiled.finditer(text)]


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


# Pre-compile every allergen's term lists ONCE (major speedup, especially Alpha-Gal).
COMPILED_RULES = {
    allergen: {
        "direct": _build_combined(r.get("direct_terms", [])),
        "review": _build_combined(r.get("review_terms", [])),
        "exclusions": _build_combined(r.get("exclusions", [])),
    }
    for allergen, r in ALLERGEN_RULES.items()
}


def match_allergen_in_field(field_text, compiled):
    """Find valid direct/review matches after removing overlapping exclusions."""
    normalized = normalize_text(field_text)
    exclusions = _spans(normalized, compiled["exclusions"])
    direct = _spans(normalized, compiled["direct"])
    review = _spans(normalized, compiled["review"])

    valid_direct = [m for m in direct if not any(overlaps(m, e) for e in exclusions)]
    valid_review = [m for m in review if not any(overlaps(m, e) for e in exclusions)]
    suppressed = [m for m in direct + review if any(overlaps(m, e) for e in exclusions)]

    return valid_direct, valid_review, suppressed


def scan_allergens(record):
    fields = approved_text_fields(record)
    results = {}

    for allergen, compiled in COMPILED_RULES.items():
        direct_evidence = []
        review_evidence = []
        excluded_evidence = []

        for field in fields:
            direct, review, suppressed = match_allergen_in_field(field["text"], compiled)

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


ROUTE_SEPARATOR = re.compile(r"\s*\|\s*")

# Route grouping (approved by the clinician/PM):
#  - ORAL, SUBLINGUAL, BUCCAL are all "in the mouth" -> oral
#  - TRANSDERMAL (skin patch) -> topical
#  - injectable also catches any "INTRA..." route so new intra-* routes in the full
#    250K dataset are classified correctly without editing this list.
# A drug can have several routes, so these are independent Yes/No flags (a drug can be
# oral AND injectable). "is_other_route" = a known route not in any named bucket
# (e.g. OPHTHALMIC, OTIC, DENTAL, RECTAL, VAGINAL). Record count stays one row per drug.
ROUTE_ORAL = {"ORAL", "SUBLINGUAL", "BUCCAL"}
ROUTE_TOPICAL = {"TOPICAL", "CUTANEOUS", "TRANSDERMAL", "PERCUTANEOUS"}
ROUTE_INHALED = {"RESPIRATORY (INHALATION)", "NASAL"}
ROUTE_INJECTABLE = {
    "INTRAVENOUS", "INTRAMUSCULAR", "SUBCUTANEOUS", "INTRA-ARTICULAR", "INTRA-ARTERIAL",
    "INTRATHECAL", "EPIDURAL", "INTRAVASCULAR", "INTRAVITREAL", "INTRALESIONAL",
    "INFILTRATION", "PERINEURAL", "INTRACAVERNOUS", "INTRACAVITARY", "INTRAVESICAL",
    "INTRAMEDULLARY", "INTRAUTERINE", "ENDOTRACHEAL", "INTRAPLEURAL", "SUBCONJUNCTIVAL",
    "SOFT TISSUE", "PARENTERAL", "INTRACAUDAL", "EXTRACORPOREAL",
}


def _is_injectable(route):
    return route in ROUTE_INJECTABLE or route.startswith("INTRA")


def clean_route(route_value):
    """Clean the multi-valued 'route' field into a normalized string + route-group flags.

    openFDA stores route as a list we join with ' | ' (e.g. 'DENTAL | ORAL | TOPICAL').
    Returns a dict: route_clean (normalized string), has_route (bool), and independent
    Yes/No flags is_oral / is_injectable / is_topical / is_inhaled / is_other_route.
    """
    text = to_text(route_value)
    if not text:
        return {"route_clean": "", "has_route": False, "is_oral": False,
                "is_injectable": False, "is_topical": False, "is_inhaled": False,
                "is_other_route": False}
    routes = sorted({p.strip().upper() for p in ROUTE_SEPARATOR.split(text) if p.strip()})

    def bucketed(r):
        return (r in ROUTE_ORAL or _is_injectable(r)
                or r in ROUTE_TOPICAL or r in ROUTE_INHALED)

    return {
        "route_clean": " | ".join(routes),
        "has_route": True,
        "is_oral": any(r in ROUTE_ORAL for r in routes),
        "is_injectable": any(_is_injectable(r) for r in routes),
        "is_topical": any(r in ROUTE_TOPICAL for r in routes),
        "is_inhaled": any(r in ROUTE_INHALED for r in routes),
        "is_other_route": any(not bucketed(r) for r in routes),
    }


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
        route_info = clean_route(openfda.get("route"))

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
            "route_clean": route_info["route_clean"],
            "has_route": route_info["has_route"],
            "is_oral": route_info["is_oral"],
            "is_injectable": route_info["is_injectable"],
            "is_topical": route_info["is_topical"],
            "is_inhaled": route_info["is_inhaled"],
            "is_other_route": route_info["is_other_route"],
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
