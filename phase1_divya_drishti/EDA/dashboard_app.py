"""
Divya Drishti - Food Allergens in U.S. Medications
SIADS 521 Assignment 3 - interactive dashboard.

App shell: Streamlit.  Charts: Plotly (the new-to-me visualization library).
Data: openFDA Drug Label (one shard = 20,000 medications), allergen-tagged by the
Phase-1 rule-based pipeline (01_DatasetCreation_4Status.py).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / "output" / "01_DatasetCreation_4Status_Output.csv"

ALLERGENS = {
    "Milk": "milk_status", "Eggs": "eggs_status", "Wheat": "wheat_status",
    "Sesame": "sesame_status", "Tree Nuts": "tree_nuts_status",
    "Peanuts": "peanuts_status", "Soy": "soy_status", "Alpha-Gal": "alpha_gal_status",
}
ROUTES = {
    "oral": "is_oral", "injectable": "is_injectable", "topical": "is_topical",
    "inhaled/nasal": "is_inhaled", "other-local": "is_other_route",
}
STATUS_ORDER = ["Detected", "Review", "Not Detected"]
STATUS_COLORS = {"Detected": "#e4572e", "Review": "#f4a259", "Not Detected": "#7fb069"}


@st.cache_data
def load_data():
    df = pd.read_csv(DATA, low_memory=False)
    for c in list(ROUTES.values()) + ["has_route"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.lower().isin(["true", "1"])
    return df


def apply_route_filter(df, selected_routes, include_unknown):
    """One medication can have several routes; keep it if ANY of its route groups is selected."""
    if not selected_routes and include_unknown:
        return df
    mask = pd.Series(False, index=df.index)
    for r in selected_routes:
        mask = mask | df[ROUTES[r]]
    if include_unknown:
        mask = mask | (~df["has_route"])
    return df[mask]


def overall_status(row):
    vals = {row[c] for c in ALLERGENS.values()}
    for s in ("Detected", "Review"):
        if s in vals:
            return s
    return "Not Detected"


# ----------------------------------------------------------------------------
st.set_page_config(page_title="Divya Drishti", page_icon="💊", layout="wide")
st.title("💊 Divya Drishti - Food Allergens in U.S. Medications")
st.caption("SIADS 521 · interactive dashboard · data: openFDA Drug Label (20,000 medications) · "
           "replicating Reker et al. (Sci Transl Med 2019) on fresh FDA data.")

df = load_data()

# ---- Sidebar: the interactive control ----
st.sidebar.header("🔎 Filter the medications")
route_sel = st.sidebar.multiselect(
    "Route of administration", list(ROUTES.keys()), default=[],
    help="A medication can have several routes; it is shown if ANY selected route matches.")
include_unknown = st.sidebar.checkbox(
    "Include medications with no recorded route (80% of the data)", value=True)
st.sidebar.info("👉 **Try it:** select only **oral** and watch *Milk* jump toward ~38% — "
                "lactose is a tablet filler. Then switch to **injectable** and it collapses to ~2%.")

fdf = apply_route_filter(df, route_sel, include_unknown)

if len(fdf) == 0:
    st.warning("No medications match this filter. Pick at least one route, or include no-route meds.")
    st.stop()

# ---- Headline metrics (update with the filter) ----
status_cols = list(ALLERGENS.values())
any_detected = (fdf[status_cols] == "Detected").any(axis=1)
m1, m2, m3 = st.columns(3)
m1.metric("Medications shown", f"{len(fdf):,}")
m2.metric("Have ≥1 allergen Detected", f"{any_detected.mean() * 100:.1f}%")
m3.metric("Milk Detected", f"{(fdf['milk_status'] == 'Detected').mean() * 100:.1f}%")

col_left, col_right = st.columns(2)

# ---- Chart A: overall status donut (updates with filter) ----
with col_left:
    st.subheader("How many are clean?")
    status = fdf.apply(overall_status, axis=1).value_counts().reindex(STATUS_ORDER, fill_value=0)
    fig = px.pie(values=status.values, names=status.index, hole=0.4,
                 color=status.index, color_discrete_map=STATUS_COLORS)
    fig.update_traces(textinfo="label+percent")
    st.plotly_chart(fig, use_container_width=True)

# ---- Chart B: per-allergen prevalence bar (updates with filter) ----
with col_right:
    st.subheader("Which allergen dominates?")
    rows = [{"Allergen": a, "Detected %": round((fdf[c] == "Detected").mean() * 100, 2)}
            for a, c in ALLERGENS.items()]
    bar = px.bar(pd.DataFrame(rows).sort_values("Detected %"), x="Detected %", y="Allergen",
                 orientation="h", text="Detected %")
    bar.update_traces(texttemplate="%{text:.1f}%")
    st.plotly_chart(bar, use_container_width=True)

# ---- Chart C: allergen × route heatmap (full dataset, context) ----
st.subheader("Prevalence by route (full dataset)")
mat, ylabels = [], []
for rlabel, rcol in ROUTES.items():
    sub = df[df[rcol]]
    if len(sub) == 0:
        continue
    mat.append([round((sub[acol] == "Detected").mean() * 100, 1) for acol in ALLERGENS.values()])
    ylabels.append(f"{rlabel} (n={len(sub)})")
heat = px.imshow(mat, x=list(ALLERGENS.keys()), y=ylabels, text_auto=True, aspect="auto",
                 color_continuous_scale="Reds", labels=dict(color="% Detected"))
st.plotly_chart(heat, use_container_width=True)

# ---- Chart D (NEW METHOD): sunburst route -> allergen · Chart E (NEW): waffle ----
c4, c5 = st.columns(2)

with c4:
    st.subheader("Drill-down: route → allergen (sunburst)")
    rows = []
    for rlabel, rcol in ROUTES.items():
        sub = fdf[fdf[rcol]]
        for aname, acol in ALLERGENS.items():
            cnt = int((sub[acol] == "Detected").sum())
            if cnt > 0:
                rows.append({"route": rlabel, "allergen": aname, "count": cnt})
    if rows:
        sb = pd.DataFrame(rows)
        sun = px.sunburst(sb, path=["route", "allergen"], values="count", color="route")
        sun.update_traces(textinfo="label+value")
        st.plotly_chart(sun, use_container_width=True)
    else:
        st.info("No route-tagged detections in the current selection.")

with c5:
    st.subheader("Allergens per medication (waffle)")
    n_det = sum((fdf[c] == "Detected").astype(int) for c in ALLERGENS.values())
    order = ["0 (none)", "1", "2", "3 or more"]
    bucket = n_det.apply(lambda n: order[0] if n == 0 else (order[1] if n == 1 else (order[2] if n == 2 else order[3])))
    counts = bucket.value_counts().reindex(order, fill_value=0)
    pct = counts / counts.sum() * 100
    base = np.floor(pct).astype(int)
    for i in np.argsort(-(pct - base).values)[: int(100 - base.sum())]:
        base.iloc[i] += 1
    wcolors = {"0 (none)": "#7fb069", "1": "#f4a259", "2": "#e4572e", "3 or more": "#9b2226"}
    seq = [cat for cat in order for _ in range(int(base[cat]))]
    waf = go.Figure(go.Scatter(
        x=[i % 10 for i in range(len(seq))], y=[i // 10 for i in range(len(seq))], mode="markers",
        marker=dict(size=22, symbol="square", color=[wcolors[c] for c in seq],
                    line=dict(width=2, color="white")), text=seq, hoverinfo="text", showlegend=False))
    for cat in order:
        waf.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
            marker=dict(size=11, symbol="square", color=wcolors[cat]),
            name=f"{cat}: {int(counts[cat]):,}"))
    waf.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"),
                      plot_bgcolor="white", height=430, margin=dict(t=10),
                      legend=dict(orientation="h", y=-0.08))
    st.plotly_chart(waf, use_container_width=True)

st.caption("⚠️ Educational prototype. A 'Detected' tag is not a safety guarantee; always verify the "
           "physical product and consult a clinician. Rule-based detection over openFDA label text.")
