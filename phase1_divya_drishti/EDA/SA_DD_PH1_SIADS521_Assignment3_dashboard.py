"""
Food Allergens in U.S. Medications - Initial exploratory dashboard
SIADS 521 - interactive dashboard.

The page tells the whole story, top to bottom:
  (1) Scope of the problem - STATIC overview (pie, bar-by-allergen, waffle)
  (2) Explore by allergen  - INTERACTIVE: pick an allergen in the sidebar and the
      metrics, route signature, worst offenders and why-review all reconfigure.
  (3) Additional views     - sunburst (the new-to-course method, driven by the
      allergen pick) + a static heatmap, kept at the very bottom.

App shell: Streamlit.  Charts: Plotly (the new-to-me library).
Data: openFDA Drug Label (one 20,000-med shard), allergen-tagged by the Phase-1
rule-based pipeline (01_DatasetCreation_4Status.py).
"""
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / "output" / "01_DatasetCreation_4Status_Output.csv"

# Display name -> the column stem the pipeline uses (milk_status, milk_matched_terms, ...)
ALLERGENS = {
    "Milk": "milk", "Eggs": "eggs", "Wheat": "wheat", "Sesame": "sesame",
    "Tree Nuts": "tree_nuts", "Peanuts": "peanuts", "Soy": "soy", "Alpha-Gal": "alpha_gal",
}
ROUTES = {
    "oral": "is_oral", "injectable": "is_injectable", "topical": "is_topical",
    "inhaled/nasal": "is_inhaled", "other-local": "is_other_route",
}
STATUS_COLORS = {"Detected": "#c1121f", "Review": "#f3722c", "Not Detected": "#7fb069", "Unknown": "#b0a89f"}
DETECTED, REVIEW, MUTED = "#c1121f", "#f3722c", "#d9c9c0"
WAFFLE_COLORS = {"0 (none)": "#7fb069", "1": "#f4a259", "2": "#e4572e", "3 or more": "#9b2226"}

@st.cache_data
def load_data():
    df = pd.read_csv(DATA, low_memory=False)
    for c in list(ROUTES.values()) + ["has_route"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.lower().isin(["true", "1"])
    status_cols = [f"{s}_status" for s in ALLERGENS.values()]
    det_any = (df[status_cols] == "Detected").any(axis=1)
    rev_any = (df[status_cols] == "Review").any(axis=1)
    df["_overall"] = np.where(det_any, "Detected", np.where(rev_any, "Review", "Not Detected"))
    df["_n_detected"] = sum((df[c] == "Detected").astype(int) for c in status_cols)
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

# ---- Sidebar: the ONE interactive control (drives Part 2 only) ----
st.sidebar.title("💊 Divya Drishti")
st.sidebar.caption("Food allergens hidden in U.S. medications")
st.sidebar.markdown("### 🔎 Explore by allergen")
allergen = st.sidebar.selectbox(
    "Choose an allergen", list(ALLERGENS), index=0,
    help="Drives the middle section: metrics, route, worst offenders, why-review.")
topn = st.sidebar.radio("Worst-offenders: show top", [3, 5, 10], index=1, horizontal=True)
st.sidebar.markdown("---")
st.sidebar.caption("Data: openFDA Drug Label (public domain), one 20,000-med shard. "
                   "Educational prototype - not medical advice.")
stem = ALLERGENS[allergen]

st.title("💊 Sanjeevani Aushad")
st.subheader("Phase 1 - Divya Drishti")
st.caption("Food Allergens in U.S. Medications")

import streamlit as st

st.caption(
    "How widespread are food allergens in medications - and where do they hide?  \n"
    "Data: [openFDA Downloads](https://open.fda.gov/data/downloads/)  \n"
    "Inspired by: [PMC Study (PMC7122736)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7122736/)"
)

# ============================================================
# PART 1 - SCOPE OF THE PROBLEM  (static, all 20,000 meds)
# ============================================================
st.header("① How big is the problem?")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Overall status")
    st.caption("Every medication is exactly one of these three.")
    oc = df["_overall"].value_counts().reindex(["Detected", "Review", "Not Detected"], fill_value=0)
    pie = px.pie(values=oc.values, names=oc.index, hole=0.35,
                 color=oc.index, color_discrete_map=STATUS_COLORS)
    pie.update_traces(textinfo="label+percent")
    pie.update_layout(margin=dict(t=10, b=10), legend=dict(orientation="h", y=-0.08))
    st.plotly_chart(pie, use_container_width=True)
with c2:
    st.subheader("Which allergen dominates?")
    st.caption("Share of all 20,000 meds where each allergen is Detected.")
    rows = [{"Allergen": a, "Detected %": round((df[f"{s}_status"] == "Detected").mean() * 100, 2)}
            for a, s in ALLERGENS.items()]
    bar = px.bar(pd.DataFrame(rows).sort_values("Detected %"), x="Detected %", y="Allergen",
                 orientation="h", text="Detected %")
    bar.update_traces(texttemplate="%{text:.1f}%", marker_color=DETECTED)
    bar.update_layout(yaxis_title="", margin=dict(t=10, b=10))
    st.plotly_chart(bar, use_container_width=True)

st.markdown("---")

# ============================================================
# PART 2 - EXPLORE BY ALLERGEN  (interactive - sidebar picker drives all of this)
# ============================================================
st.header(f"② Explore by allergen — showing: {allergen}")
st.caption("👈 Change the allergen in the sidebar; every chart in this section reconfigures.")

det = int((df[f"{stem}_status"] == "Detected").sum())
rev = int((df[f"{stem}_status"] == "Review").sum())
clean = int((df[f"{stem}_status"] == "Not Detected").sum())
m1, m2, m3 = st.columns(3)
m1.metric(f"{allergen} Detected", f"{det:,}")
m1.caption(f"**{det / TOTAL * 100:.1f}%** of {TOTAL:,}")
m2.metric("Needs Review (ambiguous)", f"{rev:,}")
m2.caption(f"**{rev / TOTAL * 100:.1f}%** of {TOTAL:,}")
m3.metric("Clean (Not Detected)", f"{clean:,}")
m3.caption(f"**{clean / TOTAL * 100:.1f}%** of {TOTAL:,}")

st.markdown("")
d1, d2 = st.columns(2)
with d1:
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
    rfig = px.bar(rdf, x="route", y="pct", text="pct", hover_data=["n drugs in route"],
                  labels={"pct": "% of route's drugs Detected", "route": ""})
    rfig.update_traces(texttemplate="%{text}%", marker_color=DETECTED)
    rfig.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(rfig, use_container_width=True)
with d2:
    st.subheader("Worst offenders")
    st.caption(f"The actual ingredient words our rule matched - lactose, casein, cream… (top {topn}).")
    dt = top_terms(df, stem, "Detected", topn)
    if dt:
        ddf = pd.DataFrame(dt, columns=["word", "meds"]).sort_values("meds")
        ofig = px.bar(ddf, x="meds", y="word", orientation="h", text="meds")
        ofig.update_traces(marker_color=DETECTED)
        ofig.update_layout(yaxis_title="", xaxis_title="# medications", margin=dict(t=10, b=10))
        st.plotly_chart(ofig, use_container_width=True)
    else:
        st.info(f"No Detected ingredients for {allergen} in this shard.")

st.subheader(f"☀️ Sunburst — {allergen} status across routes")
st.caption("New-to-course method, driven by your sidebar allergen pick. "
           f"Center = {allergen}; middle ring = the 5 route buckets (sized by how many "
           "medications take that route); outer ring = all 4 statuses "
           "(Detected / Review / Not Detected / Unknown). "
           "Click a wedge to drill in, click the center to zoom back out. "
           "A medication can take more than one route, so route counts overlap.")
sb_rows = []
for rlabel, rcol in ROUTES.items():
    sub = df[df[rcol]]
    for status in ("Detected", "Review", "Not Detected", "Unknown"):
        cnt = int((sub[f"{stem}_status"] == status).sum())
        if cnt > 0:
            sb_rows.append({"lens": allergen, "route": rlabel, "status": status, "count": cnt})
if sb_rows:
    sun = px.sunburst(
        pd.DataFrame(sb_rows), path=["lens", "route", "status"], values="count",
        color="status", color_discrete_map=STATUS_COLORS,
    )
    sun.update_traces(
        textinfo="label+value", insidetextorientation="radial",
        hovertemplate="<b>%{label}</b><br>%{value} medications<br>%{percentParent} of parent<extra></extra>",
    )
    sun.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=520)
    st.plotly_chart(sun, use_container_width=True)
else:
    st.info(f"No route-tagged {allergen} detections to chart.")

st.markdown("---")

st.subheader("How many allergens does one medication carry?")
st.caption("Each square ≈ 1% of medications, colored by number of allergens Detected (of 8).")
order = ["0 (none)", "1", "2", "3 or more"]
bucket = df["_n_detected"].apply(
    lambda n: order[0] if n == 0 else (order[1] if n == 1 else (order[2] if n == 2 else order[3])))
counts = bucket.value_counts().reindex(order, fill_value=0)
pct = counts / counts.sum() * 100
base = np.floor(pct).astype(int)
for i in np.argsort(-(pct - base).values)[: int(100 - base.sum())]:
    base.iloc[i] += 1
seq = [cat for cat in order for _ in range(int(base[cat]))]
waf = go.Figure(go.Scatter(
    x=[i % 10 for i in range(len(seq))], y=[i // 10 for i in range(len(seq))], mode="markers",
    marker=dict(size=22, symbol="square", color=[WAFFLE_COLORS[c] for c in seq],
                line=dict(width=2, color="white")),
    text=seq, hoverinfo="text", showlegend=False))
for cat in order:
    waf.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
        marker=dict(size=12, symbol="square", color=WAFFLE_COLORS[cat]),
        name=f"{cat}: {int(counts[cat]):,} meds ({pct[cat]:.1f}%)"))
waf.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"),
                  plot_bgcolor="white", height=430, margin=dict(t=10),
                  legend=dict(orientation="h", y=-0.08))
st.plotly_chart(waf, use_container_width=True)

st.markdown("---")

st.subheader('Why "Review"?')
st.caption("The ambiguous words that pushed meds into Review for this allergen - our cleanup workload "
           "(how much, and exactly which words, we still have to resolve).")
rtv = top_terms(df, stem, "Review", topn)
if rtv:
    rvdf = pd.DataFrame(rtv, columns=["word", "meds"]).sort_values("meds")
    rvfig = px.bar(rvdf, x="meds", y="word", orientation="h", text="meds")
    rvfig.update_traces(marker_color=REVIEW)
    rvfig.update_layout(yaxis_title="", xaxis_title="# meds in Review", margin=dict(t=10, b=10))
    st.plotly_chart(rvfig, use_container_width=True)
else:
    st.success(f"No Review items for {allergen} - nothing ambiguous to clean up. ✅")

st.markdown("---")
st.caption("⚠️ Educational prototype. A 'Detected' tag is not a safety guarantee; always verify the "
           "physical product and consult a clinician. Rule-based detection over openFDA label text. "
           )
