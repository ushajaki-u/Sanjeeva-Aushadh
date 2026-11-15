"""
Divya Drishti - Food Allergens in U.S. Medications
SIADS 521 - interactive dashboard (allergen-centric).

ONE control: pick an allergen in the sidebar. Every chart on the page reconfigures
to that allergen - that single control driving four charts at once is the
assignment's "linked interactivity".

App shell: Streamlit.  Charts: Plotly (the new-to-me library).
Data: openFDA Drug Label (one 20,000-medication shard), allergen-tagged by the
Phase-1 rule-based pipeline (01_DatasetCreation_4Status.py).
"""
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).parent / "output" / "01_DatasetCreation_4Status_Output.csv"

# Display name -> the column stem used by the pipeline (milk_status, milk_matched_terms, ...)
ALLERGENS = {
    "Milk": "milk", "Eggs": "eggs", "Wheat": "wheat", "Sesame": "sesame",
    "Tree Nuts": "tree_nuts", "Peanuts": "peanuts", "Soy": "soy", "Alpha-Gal": "alpha_gal",
}
ROUTES = {
    "oral": "is_oral", "injectable": "is_injectable", "topical": "is_topical",
    "inhaled/nasal": "is_inhaled", "other-local": "is_other_route",
}
DETECTED = "#c1121f"   # red
REVIEW = "#f3722c"     # orange
MUTED = "#d9c9c0"      # un-selected bars


@st.cache_data
def load_data():
    df = pd.read_csv(DATA, low_memory=False)
    for c in list(ROUTES.values()) + ["has_route"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.lower().isin(["true", "1"])
    return df


def top_terms(df, stem, status, k):
    """How many medications contain each matched word, for one allergen + status."""
    counter = Counter()
    for cell in df.loc[df[f"{stem}_status"] == status, f"{stem}_matched_terms"].dropna():
        for term in {t.strip() for t in str(cell).split("|") if t.strip()}:
            counter[term] += 1
    return counter.most_common(k)


# ---------------------------------------------------------------------------
st.set_page_config(page_title="Divya Drishti", page_icon="💊", layout="wide")
df = load_data()
TOTAL = len(df)

# ---- The ONE control ----
st.sidebar.title("💊 Divya Drishti")
st.sidebar.caption("Food allergens hidden in U.S. medications")
allergen = st.sidebar.selectbox(
    "Choose an allergen", list(ALLERGENS), index=0,
    help="Pick one. Every chart on the page updates to this allergen.")
topn = st.sidebar.radio("Worst-offenders: show top", [3, 5, 10], index=1, horizontal=True)
st.sidebar.markdown("---")
st.sidebar.info("**One control, four linked charts.** Change the allergen and watch the "
                "whole page reconfigure - that is the dashboard's interactivity.")
st.sidebar.caption("Data: openFDA Drug Label (public domain), one 20,000-med shard. "
                   "Educational prototype - not medical advice.")

stem = ALLERGENS[allergen]

# ---- Header + headline metrics ----
st.title(f"{allergen} in U.S. Medications")
st.caption("Of 20,000 FDA medications, here is where this allergen hides. "
           "Pick a different allergen in the sidebar to reconfigure every chart.")

det = int((df[f"{stem}_status"] == "Detected").sum())
rev = int((df[f"{stem}_status"] == "Review").sum())
clean = int((df[f"{stem}_status"] == "Not Detected").sum())
m1, m2, m3 = st.columns(3)
# Plain captions for the % (no st.metric "delta" - its coloured up/down arrow would
# wrongly imply a trend, and green-up on "Detected" reads as "good" on a safety number).
m1.metric(f"{allergen} Detected", f"{det:,}")
m1.caption(f"**{det / TOTAL * 100:.1f}%** of {TOTAL:,} medications")
m2.metric("Needs Review (ambiguous)", f"{rev:,}")
m2.caption(f"**{rev / TOTAL * 100:.1f}%** of {TOTAL:,}")
m3.metric("Clean (Not Detected)", f"{clean:,}")
m3.caption(f"**{clean / TOTAL * 100:.1f}%** of {TOTAL:,}")

st.markdown("")

# ---- Row A: where it ranks  |  route signature ----
colA1, colA2 = st.columns(2)

with colA1:
    st.subheader("Where it ranks")
    st.caption("How this allergen compares with the other seven (share of all 20,000 meds Detected).")
    rows = [{"Allergen": a,
             "Detected %": round((df[f"{s}_status"] == "Detected").mean() * 100, 2),
             "selected": "this allergen" if a == allergen else "other"}
            for a, s in ALLERGENS.items()]
    rank = pd.DataFrame(rows).sort_values("Detected %")
    fig = px.bar(rank, x="Detected %", y="Allergen", orientation="h", text="Detected %",
                 color="selected",
                 color_discrete_map={"this allergen": DETECTED, "other": MUTED})
    fig.update_traces(texttemplate="%{text:.1f}%")
    fig.update_layout(showlegend=False, yaxis_title="", margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with colA2:
    st.subheader("Route signature")
    st.caption("What % of each route's drugs carry this allergen. "
               "(Only ~20% of meds have a route recorded in openFDA.)")
    rr = []
    for rlabel, rcol in ROUTES.items():
        sub = df[df[rcol]]
        n = len(sub)
        rr.append({"route": rlabel,
                   "pct": round((sub[f"{stem}_status"] == "Detected").mean() * 100, 1) if n else 0,
                   "n drugs in route": n})
    rdf = pd.DataFrame(rr).sort_values("n drugs in route", ascending=False)
    fig = px.bar(rdf, x="route", y="pct", text="pct", hover_data=["n drugs in route"],
                 labels={"pct": "% of route's drugs Detected", "route": ""})
    fig.update_traces(texttemplate="%{text}%", marker_color=DETECTED)
    fig.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ---- Row B: worst offenders  |  why review ----
colB1, colB2 = st.columns(2)

with colB1:
    st.subheader("Worst offenders")
    st.caption(f"The actual ingredient words our rule matched (Detected) - top {topn}.")
    det_terms = top_terms(df, stem, "Detected", topn)
    if det_terms:
        ddf = pd.DataFrame(det_terms, columns=["word", "meds"]).sort_values("meds")
        fig = px.bar(ddf, x="meds", y="word", orientation="h", text="meds")
        fig.update_traces(marker_color=DETECTED)
        fig.update_layout(yaxis_title="", xaxis_title="# medications", margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No Detected ingredients for {allergen} in this shard.")

with colB2:
    st.subheader('Why "Review"?')
    st.caption("Ambiguous words that pushed meds into Review - the next-cleaning worklist.")
    rev_terms = top_terms(df, stem, "Review", topn)
    if rev_terms:
        rvdf = pd.DataFrame(rev_terms, columns=["word", "meds"]).sort_values("meds")
        fig = px.bar(rvdf, x="meds", y="word", orientation="h", text="meds")
        fig.update_traces(marker_color=REVIEW)
        fig.update_layout(yaxis_title="", xaxis_title="# meds in Review", margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success(f"No Review items for {allergen} - nothing ambiguous to clean up. ✅")

st.markdown("---")
st.caption("⚠️ Educational prototype. A 'Detected' tag is not a safety guarantee; always verify the "
           "physical product and consult a clinician. Rule-based detection over openFDA label text. "
           "Benchmark: Reker et al., Sci Transl Med 2019.")
