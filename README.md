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

  ## Long-Term System Vision

Sanjeeva Aushadhi is envisioned as an automated medication
allergen intelligence pipeline that retrieves, processes,
validates, and publishes medication allergen information
through a traceable and continuously monitored workflow.

This represents the long-term system vision. Components
will evolve incrementally as the project develops.

![Sanjeeva Aushadhi Long-Term System Vision](images/Sanjeeva%20Aushadhi%20System%20Vision.png)
---

## Current Status

- ✅ Research and problem formulation complete
- ✅ Product specification and architecture defined
- ✅ Data acquisition complete
- 🚧 **Divya Drishti (allergen EDA)** — 20,000-medication sample **complete**; scaling to the full openFDA set (all 14 shards, ~264K medications) **in progress** (cleanup of ambiguous *Review* cases ongoing)
  - 🔗 **Live dashboard (20K sample):** https://saddph1siads521.streamlit.app/
  - Notebook: https://github.com/ushajaki-u/Sanjeeva-Aushadh/tree/main/phase1_divya_drishti/EDA
- 🚧 Data engineering and implementation in progress
- 🎯 Future work includes EHR integration and clinical validation

---

## Related Work & Differentiation

Before building, I surveyed the space to confirm this is a real, under-served problem — and that the approach adds something genuinely new. A couple of efforts touch adjacent ground:

- **[AllergenMaps / AllergenMeds](https://allergenmaps.org/)** — a medication-ingredient allergen database and consumer app.
- **[Hello Pharmacist](https://hellopharmacist.com/drug-supplement-interactions/)** — drug and drug–supplement interaction checking.

What makes **Sanjeevini Aushad** distinct:

- **Open, explainable, auditable** — rule-based tagging over public data, with every allergen flag traceable to the exact ingredient term.
- **Integrative / AYUSH lens** — frames allergen-safe alternatives within an integrative-medicine perspective.
- **A full decision-support arc** — measurement (Divya Drishti) → pre-prescription conflict detection (Lakshmana Rekha) → allergen-safe alternatives (Sanjeevini), not a single lookup.

*A fuller competitive analysis will live in the PRD.*

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
