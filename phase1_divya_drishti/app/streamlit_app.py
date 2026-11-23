"""
Sanjeevani Aushadh — Life-giving medicine, safe for your food allergies.

A rule-based allergen finder over openFDA drug labels (the full 264k-medication
Phase-1 tagged dataset). Two tabs:

  1. Find safe medicine — pick the food allergens you avoid, get medicines that are
     SUPER-CONSERVATIVELY safe: a medicine is "safe" for an allergen ONLY if its
     status is explicitly "Not Detected". Detected / Review / Unknown are all treated
     as NOT safe (we never imply a safety we cannot prove).

  2. Check a medicine — search one drug by name, see its per-allergen status AND the
     exact ingredient word that triggered each flag (explainability).

Data: Phase-1 rule-based tagging of openFDA Drug Label text, slimmed to a compressed
Parquet (./data/medications.parquet) so it deploys on Streamlit Community Cloud.
Educational prototype — NOT medical advice. Always read the physical label.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# 1. PAGE CONFIG & STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Sanjeevani Aushadh — Safe Medicine Finder",
                   page_icon="🪔", layout="wide")

st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; color: #9a3412; font-weight: 800; margin-bottom: 0; }
    .sub-header  { font-size: 1.15rem; color: #b45309; font-weight: 600; font-style: italic;
                   margin-bottom: 4px; }
    .tag-line    { font-size: 0.95rem; color: #6b7280; margin-bottom: 16px; }
    .verify-banner {
        background-color: #fff7ed; border: 1px solid #fed7aa; padding: 12px;
        border-radius: 8px; margin: 10px 0 16px 0; color: #7c2d12; font-weight: 500;
    }
    .disclaimer-box {
        background-color: #fff3e0; border-left: 5px solid #ff9800; padding: 15px;
        border-radius: 6px; margin-top: 28px; font-size: 0.86rem; color: #424242;
    }
    .badge { font-weight: 700; font-size: 0.8rem; padding: 4px 12px; border-radius: 10px;
             display: inline-block; color: white; }
    .b-safe   { background:#15803d; }   /* Not Detected  -> green  */
    .b-contain{ background:#b91c1c; }   /* Detected      -> red    */
    .b-review { background:#d97706; }   /* Review        -> amber  */
    .b-unknown{ background:#6b7280; }   /* Unknown       -> grey   */
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ALLERGEN SCOPE
# ---------------------------------------------------------
# Display name -> column stem used by the Phase-1 pipeline.
ALLERGENS = {
    "Milk": "milk", "Eggs": "eggs", "Wheat": "wheat", "Sesame": "sesame",
    "Tree Nuts": "tree_nuts", "Peanuts": "peanuts", "Soy": "soy", "Alpha-Gal": "alpha_gal",
}
DATA_PATH = Path(__file__).parent / "data" / "medications.parquet"

# status -> (css class, label shown to the user)
STATUS_STYLE = {
    "Not Detected": ("b-safe",    "✓ Not detected"),
    "Detected":     ("b-contain", "⛔ Contains"),
    "Review":       ("b-review",  "⚠️ Needs checking — not cleared"),
    "Unknown":      ("b-unknown", "❔ Unknown — not cleared"),
}


# ---------------------------------------------------------
# 3. DATA LOADER
# ---------------------------------------------------------
@st.cache_data(show_spinner="Loading medicine intelligence…")
def load_meds(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_parquet(path)
    for stem in ALLERGENS.values():
        df[f"{stem}_status"] = df[f"{stem}_status"].astype(str)
    # Display name: brand if present, else generic, else a placeholder.
    brand = df["brand_name"].fillna("").str.strip()
    generic = df["generic_name"].fillna("").str.strip()
    # Drop products with no usable name — you can't act on an unnamed medicine.
    df = df[(brand != "") | (generic != "")].copy()
    brand = brand[df.index]
    generic = generic[df.index]
    df["display_name"] = brand.where(brand != "", generic)
    df["secondary"] = generic.where(brand != "", "")   # show generic under brand when both exist
    # Drop exact duplicate label rows so one medicine isn't listed many times.
    df = df.drop_duplicates(
        subset=["display_name", "active_ingredient", "inactive_ingredient"]
    ).reset_index(drop=True)
    # Lowercase search blob built once.
    df["_search"] = (df["display_name"] + " " + df["generic_name"].fillna("") + " "
                     + df["manufacturer_name"].fillna("")).str.lower()
    return df


MEDS = load_meds()
TOTAL = len(MEDS)


def status_badge(status: str) -> str:
    cls, label = STATUS_STYLE.get(status, STATUS_STYLE["Unknown"])
    return f'<span class="badge {cls}">{label}</span>'


# ---------------------------------------------------------
# 4. HEADER
# ---------------------------------------------------------
st.markdown('<div class="main-header">🪔 Sanjeevani Aushadh</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Life-giving medicine — safe for your food allergies</div>',
            unsafe_allow_html=True)
st.markdown(f'<div class="tag-line">Because medicine should heal, not harm — rule-based allergen '
            f'discovery over <b>{TOTAL:,} real medications</b> (openFDA Drug Label).</div>',
            unsafe_allow_html=True)
st.divider()

tab_find, tab_check = st.tabs(["🔍 Find safe medicine", "💊 Check a medicine"])

# =========================================================
# TAB 1 — FIND SAFE MEDICINE  (super-conservative)
# =========================================================
with tab_find:
    st.subheader("1. Which food allergens do you need to avoid?")
    selected = st.multiselect(
        "Select the allergens you avoid:",
        options=list(ALLERGENS), default=[],
        help="A medicine is shown as safe ONLY if every allergen you pick is explicitly "
             "'Not Detected'. Anything Detected, Review, or Unknown is treated as not safe.",
    )

    st.markdown("""<div class="verify-banner">🛡️ <b>Super-conservative safety:</b> a medicine
        counts as “safe” only when the allergen is <b>explicitly Not Detected</b>. If the data is
        ambiguous (Review) or missing (Unknown), we treat it as <b>not safe</b> — we never imply a
        safety we can’t prove.</div>""", unsafe_allow_html=True)

    st.divider()

    if not selected:
        st.info("👆 Pick one or more allergens above to see medicines that are safe for you.")
    else:
        stems = [ALLERGENS[a] for a in selected]
        safe_mask = pd.Series(True, index=MEDS.index)
        for stem in stems:
            safe_mask &= (MEDS[f"{stem}_status"] == "Not Detected")
        safe = MEDS[safe_mask]

        m1, m2, m3 = st.columns(3)
        m1.metric("💊 Medicines in database", f"{TOTAL:,}")
        m2.metric("✅ Super-conservatively safe", f"{len(safe):,}")
        m3.metric("🚫 Excluded (not cleared)", f"{TOTAL - len(safe):,}")

        st.caption(f"Filtering out any medicine where **{', '.join(selected)}** is "
                   "Detected, Review, *or* Unknown.")

        if len(safe) == 0:
            st.error("No medicines are fully cleared for every allergen you selected. "
                     "Try removing one, or use the **Check a medicine** tab for a specific drug.")
        else:
            max_show = min(50, len(safe))
            n_show = st.slider("How many to show:", 5, max_show, min(10, max_show), 5) \
                if max_show > 5 else max_show
            st.markdown(f"Showing **{n_show}** of **{len(safe):,}** safe medicine(s):")
            for i, (_, med) in enumerate(safe.head(n_show).iterrows(), 1):
                title = med["display_name"]
                if med["secondary"]:
                    title += f"  ·  {med['secondary']}"
                with st.expander(f"#{i} — {title}", expanded=(n_show <= 5)):
                    st.markdown('<span class="badge b-safe">✓ Safe for your selected '
                                'allergens</span>', unsafe_allow_html=True)
                    # Show status for ALL allergens so nothing is hidden.
                    chips = " ".join(
                        f'{a}: {status_badge(med[f"{s}_status"])}'
                        for a, s in ALLERGENS.items())
                    st.markdown("**Full allergen profile:**", unsafe_allow_html=True)
                    st.markdown(chips, unsafe_allow_html=True)
                    if med["manufacturer_name"]:
                        st.caption(f"Manufacturer: {med['manufacturer_name']}")
                    if med["active_ingredient"]:
                        st.markdown("**Active ingredient(s):**")
                        st.write(f"_{med['active_ingredient']}_")
                    if med["inactive_ingredient"]:
                        st.markdown("**Inactive ingredient(s):**")
                        st.write(f"_{med['inactive_ingredient']}_")
                    if med["product_ndc"]:
                        st.caption(f"Product NDC: {med['product_ndc']}")

# =========================================================
# TAB 2 — CHECK A MEDICINE  (search + explainability)
# =========================================================
with tab_check:
    st.subheader("Is a specific medicine safe for you?")
    st.caption(f"Type part of a drug name or manufacturer. Only the {TOTAL:,} medicines in our "
               "database are searchable — if a drug isn’t here, we don’t have its data (we won’t guess).")

    query = st.text_input("Search a medicine (e.g., ibuprofen, Tylenol, amoxicillin):",
                          placeholder="Start typing a drug name…").strip().lower()

    if query:
        hits = MEDS[MEDS["_search"].str.contains(query, regex=False, na=False)]
        if len(hits) == 0:
            st.warning("No medicine in the database matches that. Try a different spelling or a "
                       "generic name.")
        else:
            options = hits.head(300).index.tolist()
            st.caption(f"{len(hits):,} match(es){' — showing first 300' if len(hits) > 300 else ''}.")
            idx = st.selectbox(
                "Pick the exact medicine:", options=options,
                format_func=lambda i: (MEDS.at[i, "display_name"]
                                       + (f" · {MEDS.at[i, 'secondary']}" if MEDS.at[i, "secondary"] else "")),
                index=None, placeholder="Select a medicine from the matches…")

            if idx is not None:
                med = MEDS.loc[idx]
                head = f"#### {med['display_name']}"
                if med["secondary"]:
                    head += f"  ·  {med['secondary']}"
                st.markdown(head)
                if med["manufacturer_name"]:
                    st.caption(f"Manufacturer: {med['manufacturer_name']}  ·  NDC: {med['product_ndc']}")

                st.markdown("##### Allergen profile")
                for a, stem in ALLERGENS.items():
                    status = med[f"{stem}_status"]
                    terms = str(med[f"{stem}_matched_terms"]).strip()
                    expl = str(med[f"{stem}_explanation"]).strip()
                    line = f'<div style="margin:7px 0;"><b>{a}:</b> {status_badge(status)}'
                    if status in ("Detected", "Review") and terms and terms.lower() != "nan":
                        pretty = ", ".join(t.strip() for t in terms.split("|") if t.strip())
                        if pretty:
                            color = "#b91c1c" if status == "Detected" else "#d97706"
                            line += f'&nbsp;&nbsp;<span style="color:{color};">from: <b>{pretty}</b></span>'
                    line += "</div>"
                    st.markdown(line, unsafe_allow_html=True)
                    if expl and expl.lower() != "nan":
                        st.caption(f"↳ {expl}")

                st.markdown("""<div class="verify-banner">🔎 <b>Verify before you take it:</b> this is
                    based on openFDA label text, which can be incomplete or out of date.
                    <b>Always read the physical package label</b> and ask your pharmacist or doctor —
                    and when in doubt, don’t.</div>""", unsafe_allow_html=True)

                with st.expander("See the full ingredient text"):
                    st.markdown("**Active ingredient(s):**")
                    st.write(f"_{med['active_ingredient'] or '—'}_")
                    st.markdown("**Inactive ingredient(s):**")
                    st.write(f"_{med['inactive_ingredient'] or '—'}_")

# ---------------------------------------------------------
# DISCLAIMER
# ---------------------------------------------------------
st.markdown("""
<div class="disclaimer-box">
    <b>⚖️ Legal & Medical Disclaimer:</b><br>
    Sanjeevani Aushadh is an educational MVP prototype for information discovery only. It does NOT
    provide medical advice, and a data match is never a guarantee of safety. Allergen tags are
    derived by rule-based scanning of public openFDA label text, which may be incomplete or
    outdated. Always read the physical package label and consult a qualified physician or
    pharmacist before taking any medication.
</div>
""", unsafe_allow_html=True)
