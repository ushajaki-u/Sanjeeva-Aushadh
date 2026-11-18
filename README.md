# Sanjeevini Aushad

**Applied AI clinical decision support for medication allergen safety.**

Sanjeevini Aushad is an applied AI project that addresses a critical gap in medication safety: patients with documented food allergies can still receive medications containing allergenic inactive ingredients because current prescribing and dispensing workflows rarely cross-check excipients against a patient's allergy profile.

Inspired by my own experience navigating this gap, the project explores how publicly available medication data can be transformed into practical clinical decision support that is explainable, auditable, and designed to assist—not replace—clinical decision-making.
 
---
<p align="center">
  <img src="ChatGPT Image Aug 6, 2026, 09_30_42 AM.png" alt="Sanjeevani product lifecycle infographic showing user impact metrics, drug allergen detection workflow, and therapeutic alternatives" width="85%">
</p>


## Data Sources

This project is built using publicly available healthcare datasets, including:

- **openFDA Drug Label API** – active and inactive ingredient data, updated monthly
- **DailyMed Structured Product Labels (SPL)**
- **RxNorm** for medication normalization and standardization

Primary dataset:
https://open.fda.gov/data/downloads/

---

## Project Vision

The long-term vision consists of three complementary components:

- **Divya Drishti** – Measure and monitor the prevalence of allergens in FDA-approved medications.
- **Lakshmana Rekha** – Detect potential medication-allergen conflicts before a prescription reaches the patient.
- **Sanjeevini** – Recommend therapeutically equivalent, allergen-safe alternatives when available.

---

## Landscape & Prior Art

Food allergens hidden in medication *inactive* ingredients is a real, under-served problem — real enough that others are already building for it. Rather than claim novelty, this project maps where it sits and where it differs:

| Product | What it does | Relation to this work |
|---|---|---|
| [AllergenMaps / AllergenMeds](https://allergenmaps.org/) | A medication ingredient & allergen database (580K+ FDA-listed medications, ~4K fillers) that screens excipients against allergen/dietary/religious exclusions — a pharmacist screening tool plus a consumer app (**AllergenMeds**). | **Closest prior art** — same core idea (excipient-level allergen lookup), offered as a commercial product. |
| [Hello Pharmacist](https://hellopharmacist.com/drug-supplement-interactions/) | A telehealth-pharmacy service with drug and drug–supplement interaction checking. | **Adjacent** — focuses on drug/supplement *interactions*, not food-allergen excipients. |

**How Sanjeevini Aushad is different**

- **Open, explainable, auditable** — rule-based tagging over public data, built in the open as applied-AI research, with every allergen flag traceable to the exact ingredient term (not a closed commercial black box).
- **Integrative / AYUSH lens** — frames allergen-safe alternatives within an integrative-medicine perspective.
- **A full decision-support arc, not a single lookup** — the vision spans *measurement* (Divya Drishti) → *pre-prescription conflict detection* (Lakshmana Rekha) → *allergen-safe therapeutic alternatives* (Sanjeevini).

*A fuller competitive analysis will live in the PRD.*

---

## Current Status

- ✅ Research and problem formulation complete
- ✅ Product specification and architecture defined
- ✅ Data acquisition complete
- 🚧 **Divya Drishti (allergen EDA)** — 20,000-medication sample **complete**; scaling to the full openFDA set (all 14 shards, ~264K medications) **in progress** (cleanup of ambiguous *Review* cases ongoing)
  - 🔗 **Live dashboard (20K sample):** https://saddph1siads521.streamlit.app/
- 🚧 Data engineering and implementation in progress
- 🎯 Future work includes EHR integration and clinical validation

---

## Technology Stack

- Python
- DuckDB
- Pandas
- openFDA
- DailyMed
- RxNorm
- Rule-based decision engine
- Streamlit (planned)

---

*"See the problem. Draw the line. Bring the remedy—in time."*
