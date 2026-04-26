# 🌍 UNMAPPED

### Portable Skills Infrastructure for Invisible Talent

> Turning informal experience into explainable, opportunity-ready skills profiles.

> **UNMAPPED doesn't just match skills — it grounds every recommendation in real economic signals like wage levels, automation exposure, sector growth, and digital readiness, with explicit provenance per metric.**

Built for the **World Bank UNMAPPED challenge** at the 5th Hack-Nation Global AI Hackathon (Apr. 25–26, 2026).

---

## The Problem

Hundreds of millions of young people in low- and middle-income countries have meaningful skills — from informal work, repair shops, family businesses, mobile money kiosks, online selling, self-teaching from YouTube, and community labor — but those skills rarely translate into recognized labor market signals. Formal hiring systems and credentialing infrastructures are blind to most of this human capital. The result is structural underemployment, hidden talent, and policy decisions made on impoverished data.

## Why It Matters

A young person like **Amara** in peri-urban Accra has repaired phones for years, tracks customer payments, speaks three languages, and learned basic HTML from YouTube. To formal labor systems she is invisible. Her secondary school certificate signals far less than she actually knows. She has no portable, machine-readable record of her demonstrated competencies — and no realistic, locally-grounded view of which opportunities her skills could already reach.

Multiply Amara by tens of millions of youth across Sub-Saharan Africa, South & Southeast Asia, and Latin America, and the labor market interoperability gap becomes one of the largest unsolved coordination problems in global development.

## Official Challenge Alignment

UNMAPPED implements **all three** of the World Bank challenge's modules (the brief requires at least two):

- **Module 1 — Skills Signal Engine**: a youth user inputs education, informal work experience, demonstrated competencies, languages, and constraints. The system maps these into a standardized, portable, human-readable skills profile grounded in real taxonomies (ISCO-08-aligned, with explicit hooks for ESCO and O*NET).

- **Module 2 — AI Readiness & Displacement Lens**: for each matched role, the system surfaces an explicit task-level breakdown — `at_risk_tasks` (likely to be automated or co-piloted by AI, calibrated against Frey-Osborne 2017), `durable_skills` (resistant to automation), and `resilience_bridge_skills` (adjacent capabilities that future-proof the worker). The lens is calibrated to LMIC contexts and integrates Wittgenstein-style 2035 education projections per country.

- **Module 3 — Opportunity Matching & Econometric Dashboard**: the system connects the portable skills profile to realistic, reachable opportunities and visibly surfaces multiple real-source econometric signal categories — official ILOSTAT wage anchors, occupation-aligned monthly earnings, youth NEET, internet penetration, youth literacy, automation exposure (Frey-Osborne), sector growth, and education quality — each with per-row provenance (`value_type`, `source_dataset`, `source_url_or_note`). For the six-country demo set (Ghana, Nigeria, Philippines, Colombia, Peru, Guatemala), the country-level NEET / internet / youth-literacy anchors are pulled live from the World Bank API and the wage layer is refreshed live from the official ILOSTAT earnings API.

## What UNMAPPED Is (And Is Not)

UNMAPPED is **infrastructure**. Country-specific labor market data, education taxonomies, automation calibration, language and local-term mappings, opportunity types, economic signal sources, and **all UI copy** are configurable inputs — country configs live in `data/country_configs.json` (loaded at import time by `src/config.py`), economic signals in `data/economic_signals.csv`, AI Readiness breakdowns in `data/ai_readiness.csv`, and UI terminology modes (176 keys × 7 languages) in `data/ui_terms.json`. **To support a new country or interface language, edit configuration files. No code changes required.**

UNMAPPED is **not** a generic job-matching app. We do not chase aspirational mismatches (a phone-repair youth becoming an AI researcher overnight). Recommendations are realistic, locally grounded, and explicitly linked to bridge-skill upskilling pathways.

## Provenance Badge System (Real vs Fallback vs Benchmark)

Every metric on a recommendation card is tagged with one of five tiers, so the source of each value is visible at a glance:

| Tier | Meaning | Color |
|------|---------|-------|
| **REAL · World Bank API** | Live published indicator pulled from the World Bank API (NEET, internet, youth literacy, informal employment, GDP/cap). | Green |
| **OFFICIAL · ILOSTAT (USD)** | Direct major-group monthly earnings in U.S. dollars from the ILOSTAT earnings API. | Blue |
| **OFFICIAL FALLBACK · ILOSTAT (PPP/skill-level)** | Official ILOSTAT pull, but no direct USD major-group series available — using PPP$ or skill-level series instead. | Amber |
| **BENCHMARK · Frey-Osborne** | Published academic benchmark (Frey & Osborne 2017 automation probability), aligned to ISCO group. | Indigo |
| **LEGACY PROXY · modeled estimate** | Modeled planning estimate retained as a fallback when no official API series matches this role. | Red |

Whenever a fallback fires (unknown country, unparseable config, no role match, missing wage series), a top-of-page banner names the exact issue and which file to fix. No silent fallbacks.

## Hugging Face Semantic Layer

UNMAPPED includes an optional Hugging Face semantic matching layer using
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.

Why this model fits the project:
- It is a multilingual sentence-transformer, which aligns better with UNMAPPED's cross-country and local-language goals than an English-only embedding model.
- It produces 384-dimensional dense embeddings suitable for semantic search and similarity, which is exactly the retrieval problem behind informal skill-to-role mapping.
- It complements the existing rule-based taxonomy instead of replacing it, so the system stays explainable for users and implementers.

How it is used:
- Rule-based keyword extraction remains the primary audit trail.
- Semantic similarity is blended into role ranking to rescue good matches when youth describe skills in non-standard wording.
- Semantic skill hints are surfaced separately from explicit extracted skills, so the model can add nuance without pretending inferred skills were directly stated.
- If the model or dependency is unavailable, the pipeline falls back cleanly to the deterministic matcher (and the fallback is surfaced as a visible warning, not hidden).

Environment toggles:
- `UNMAPPED_ENABLE_SEMANTIC_MATCHING=0` disables the semantic layer.
- `UNMAPPED_EMBEDDING_MODEL=...` swaps the default model without code changes.
- `UNMAPPED_EMBEDDING_OFFLINE=1` forces cached-only model loading after the first download.

---

## Data Layers

| File | Purpose |
|------|---------|
| `data/raw_youth_profiles.csv` | 29 synthetic-but-realistic youth profiles across Ghana, Nigeria, Philippines, Colombia, Peru, and Guatemala. Columns include `gender`, `age`, `device_access`, `internet_access`, `income_bracket` for constraint-aware modeling. |
| `data/raw_global_labor_data.csv` | 30 messy localized job postings (labor-side input). Tagged with `industry_sector` and `employment_type`. |
| `data/economic_signals.csv` | Econometric signal layer keyed by (country, role). Carries **real published indicators** (`youth_neet_rate_pct`, `internet_penetration_pct`, `youth_literacy_rate_pct`), official ILOSTAT minimum-wage anchors, official occupation-aligned monthly earnings, the Frey-Osborne `automation_exposure_score` (benchmark-aligned to ISCO), narrative signals, and full provenance (`value_type`, `source_dataset`, `source_url_or_note`, `year`, `data_quality_flag`). |
| `data/matching_validation_cases.csv` | Small benchmark set showing where rule-only matching succeeds or fails and whether the hybrid semantic layer rescues the case. |
| `data/ai_readiness.csv` | **Module 2 (AI Readiness Lens):** for each role, the explicit `at_risk_tasks`, `durable_skills`, and `resilience_bridge_skills` per the brief's requirement. |
| `data/education_projection_signals.csv` | **Wittgenstein-style 2035 education projections** per country (secondary completion trajectory, tertiary attainment trajectory, structural signal). |
| `data/constraint_weights.csv` | Data-driven constraint penalty rules. 18 rules across 9 categories (Credentialing, Connectivity, Device Access, Language, Literacy, Infrastructure, Social, Time, Geographic, Tenure). Tunable per program/country without code changes. |
| `data/opportunity_catalog.csv` | 43 country-level realistic pathways. Each entry carries `opportunity_label`, `type`, `entry_barrier`, and `typical_pathway` — surfaces in the UI under each matched opportunity. |
| `data/country_configs.json` | **Country-agnostic compliance:** all country configs (education taxonomies, opportunity types, automation calibration, language terms, local terminology labels) externalized to JSON. Adding a country requires no code changes. |
| `data/country_runtime_config.json` | Runtime scope: role aliases, visible econometric priorities, and enabled opportunity types per country. |
| `data/ui_terms.json` | **176 UI keys × 7 modes** (English, Ghana, Nigeria, Philippines, Colombia, Peru, Guatemala). Section headers, form labels, captions, warning copy — all re-localize together when the user picks an interface language from the sidebar. |
| `data/normalized_youth_profiles.{csv,json}` | Pipeline output (Mode 1). Includes `matched_constraints` audit trail, full `economic_signals` with provenance, `ai_readiness` per opportunity, and `education_projection`. |
| `data/normalized_global_labor_data.{csv,json}` | Pipeline output (Mode 2). |
| `src/taxonomy.py` | Portable global role taxonomy + skill normalization map. |
| `src/config.py` | Thin loader — reads `data/country_configs.json` at import time, with an inline fallback dict for safety. Exposes `COUNTRY_CONFIGS_LOAD_STATUS` so the UI can surface a visible warning if the JSON failed to parse. |
| `src/semantic_matching.py` | Optional Hugging Face MiniLM semantic role-assist layer with clean fallback to deterministic matching. |
| `src/normalize_pipeline.py` | Dual-mode normalization pipeline (youth + labor demand). |
| `scripts/refresh_world_bank_indicators.py` | **Live ingestion** — pulls youth NEET, internet penetration, youth literacy, informal employment, and GDP/cap from the World Bank API for all 6 demo countries; writes back into `economic_signals.csv` with per-row source URLs. |
| `scripts/refresh_ilostat_wages.py` | **Live ingestion** — refreshes country minimum wage and occupation-aligned monthly earnings from the official ILOSTAT earnings API. |
| `app.py` | 6-tab Streamlit app: Skills Signal Engine, Opportunity Matching, Localizability Layer, **Architecture**, Policymaker Dashboard, Audit Trail. Includes hero panel, provenance badges, silent-fallback banner, and `t()` localization helper. |
| `.streamlit/config.toml` | World Bank teal theme. |
| `assets/architecture.dot` | Source-of-truth Graphviz diagram of every component. |
| `assets/architecture.html` | Self-contained browser-renderable architecture diagram for slides. |

### Real-source values embedded in `economic_signals.csv`

Per the brief's requirement that the tool be "grounded in real economic data, not synthetic proxies", the following **real published values** are pulled live from the World Bank API and cached with citations in `source_url_or_note`:

| Country | Youth NEET | Internet penetration | Youth literacy | Source family |
|---------|------------|----------------------|----------------|---------------|
| Ghana | 23.91% (2024) | 72.18% (2024) | 91.51% (2021) | World Bank API (`SL.UEM.NEET.ZS`, `IT.NET.USER.ZS`, `SE.ADT.1524.LT.ZS`) |
| Nigeria | 11.91% (2024) | 41.21% (2024) | 81.36% (2024) | World Bank API (`SL.UEM.NEET.ZS`, `IT.NET.USER.ZS`, `SE.ADT.1524.LT.ZS`) |
| Philippines | 12.36% (2023) | 67.26% (2024) | 99.77% (2022) | World Bank API (`SL.UEM.NEET.ZS`, `IT.NET.USER.ZS`, `SE.ADT.1524.LT.ZS`) |
| Colombia | 21.98% (2025) | 79.35% (2024) | 98.96% (2024) | World Bank API (`SL.UEM.NEET.ZS`, `IT.NET.USER.ZS`, `SE.ADT.1524.LT.ZS`) |
| Peru | 22.78% (2022) | 81.96% (2024) | 99.49% (2024) | World Bank API (`SL.UEM.NEET.ZS`, `IT.NET.USER.ZS`, `SE.ADT.1524.LT.ZS`) |
| Guatemala | 24.03% (2024) | 60.22% (2024) | 95.36% (2024) | World Bank API (`SL.UEM.NEET.ZS`, `IT.NET.USER.ZS`, `SE.ADT.1524.LT.ZS`) |

To refresh these values from live APIs at any time, run `python scripts/refresh_world_bank_indicators.py`.

Role rows also carry:
- **Frey-Osborne automation benchmarks** aligned to standardized roles (tagged BENCHMARK in the UI)
- **Official ILOSTAT wage anchors** refreshed from the public earnings API (tagged OFFICIAL or OFFICIAL FALLBACK)
- A retained **legacy planning proxy** for fallback scoring where a direct occupation-level U.S.-dollar series is not exposed for that country (tagged LEGACY PROXY)

The `value_type` column uses **`mixed_real_api_and_benchmark`** because each opportunity row combines real published country indicators, official ILOSTAT wage API pulls, and benchmarked automation overlays. The `data_quality_flag` clarifies whether the wage side is a direct major-group USD pull or an official fallback.

### Why this dataset structure matters

UNMAPPED uses **seven** complementary data layers — not just youth profiles and job postings. Each layer maps to a real World Bank-ecosystem data anchor:

1. **Individual-level data** (`raw_youth_profiles.csv`) — informal experience + structured constraints
2. **Labor demand data** (`raw_global_labor_data.csv`) — messy localized job postings
3. **Economic signals** (`economic_signals.csv`) — real published NEET / internet / youth literacy + official ILOSTAT wages + Frey-Osborne automation, with full provenance per row
4. **AI Readiness** (`ai_readiness.csv`) — at-risk / durable / resilience task breakdown per role (Module 2 brief requirement)
5. **Education projections** (`education_projection_signals.csv`) — Wittgenstein-style 2035 trajectory per country
6. **Constraint modeling** (`constraint_weights.csv`) — externalized, auditable penalty rules
7. **Opportunity mapping** (`opportunity_catalog.csv`) — country-level realistic pathways with entry barriers

Plus three configuration files (`country_configs.json`, `country_runtime_config.json`, `ui_terms.json`) that externalize country, runtime, and UI parameters so adding new countries or new UI modes requires zero code changes.

### Note on data sources

Youth profiles are **synthetic** for demo purposes — we do not collect real youth data without consent. Economic signals are a mix of **real published country anchors** (live World Bank API pulls for youth NEET, internet penetration, youth literacy, informal employment, GDP/cap), **official ILOSTAT wage API pulls** (country minimum wage + occupation-aligned monthly earnings where published), and **explicit automation benchmarks** (Frey-Osborne probabilities) — each row is explicitly tagged via `value_type` and visually badged in the UI. Real-source taxonomies that the World Bank ecosystem uses are referenced throughout:

- **ILOSTAT** — wage, employment, labor force participation, sector employment
- **World Bank WDI** — education, employment, poverty, macro indicators
- **World Bank Human Capital Index** — learning-adjusted years of schooling
- **ILO ISCO-08** — occupational classification backbone
- **Frey & Osborne** — automation exposure scores by occupation
- **ILO Future of Work** — routine/non-routine and cognitive/manual task content
- **ITU Digital Development** — broadband and internet penetration
- **UNESCO Institute for Statistics** — enrollment, completion, gender parity
- **Wittgenstein Centre** — education projections
- **ESCO / O*NET** — skills and occupation taxonomies

Country indicators and wage pulls are cited directly in `data/economic_signals.csv` (`source_url_or_note` plus dedicated ILOSTAT source columns).

---

## Project Structure

```
unmapped/
├── app.py                                    # 6-tab Streamlit app
├── README.md
├── requirements.txt
├── .streamlit/
│   └── config.toml                           # World Bank teal theme
├── assets/
│   ├── architecture.dot                      # Source-of-truth architecture diagram
│   └── architecture.html                     # Self-contained browser-renderable version
├── data/
│   ├── raw_youth_profiles.csv                # 29 youth profiles
│   ├── raw_global_labor_data.csv             # 30 messy job postings
│   ├── economic_signals.csv                  # Live WB + ILOSTAT + Frey-Osborne, with provenance per row
│   ├── ai_readiness.csv                      # Module 2: at-risk / durable / resilience per role
│   ├── education_projection_signals.csv      # Wittgenstein-style 2035 projections per country
│   ├── constraint_weights.csv                # Data-driven penalty rules
│   ├── opportunity_catalog.csv               # Country-level realistic pathways
│   ├── matching_validation_cases.csv         # Rule-only vs hybrid rescue benchmark
│   ├── country_configs.json                  # Externalized country configs
│   ├── country_runtime_config.json           # Runtime: role aliases, visible signals
│   ├── ui_terms.json                         # 176 UI keys × 7 languages
│   ├── normalized_youth_profiles.{csv,json}  # Pipeline output (Mode 1)
│   └── normalized_global_labor_data.{csv,json}
├── scripts/
│   ├── refresh_world_bank_indicators.py      # Live World Bank API ingestion
│   └── refresh_ilostat_wages.py              # Live ILOSTAT earnings ingestion
└── src/
    ├── taxonomy.py                           # Global role taxonomy
    ├── config.py                             # Country configs loader (with load-status flag)
    ├── semantic_matching.py                  # Optional Hugging Face MiniLM assist
    └── normalize_pipeline.py                 # Dual-mode pipeline
```

---

## How to Run

```bash
pip install -r requirements.txt

# Refresh country indicators from the live World Bank API (optional — values are cached)
python scripts/refresh_world_bank_indicators.py

# Refresh wage layer from the live ILOSTAT API (optional)
python scripts/refresh_ilostat_wages.py

# CLI run (regenerates both normalized outputs and prints a summary)
python src/normalize_pipeline.py

# Streamlit demo (6 tabs)
streamlit run app.py
```

To switch interface language: pick a mode from the sidebar (English, Local terminology — Ghana / Nigeria / Philippines, Español — Colombia / Peru / Guatemala). Every section header, form label, caption, and warning re-localizes together.

---

## Why This Is Infrastructure, Not Just an App

| Differentiator | Why it matters for the challenge |
|---|---|
| **Stable role IDs** (`GR-REPAIR-001`, etc.) | Designed like ISCO codes — permanent, opaque, and machine-readable across systems |
| **Externalized country configs** | `data/country_configs.json` is the single source of truth; adding a country requires zero code changes |
| **Externalized UI copy** | `data/ui_terms.json` holds 176 keys × 7 languages — the entire interface re-localizes from a sidebar toggle |
| **Bridge skills explicitly named** | Every role carries an explicit upskilling pathway — actionable for training providers |
| **Visible provenance badges** | Every metric on every card declares whether it is REAL (World Bank API), OFFICIAL (ILOSTAT USD), OFFICIAL FALLBACK (PPP/skill-level), BENCHMARK (Frey-Osborne), or LEGACY PROXY |
| **No silent fallbacks** | When a fallback fires (unknown country, parse failure, no role match, missing wage series), a top-of-page banner names the exact issue and the file to fix |
| **Live API ingestion** | `scripts/refresh_world_bank_indicators.py` and `scripts/refresh_ilostat_wages.py` pull live from public endpoints — not snapshot constants |
| **Explainable confidence** | Every output has an audit trail; constraint penalties are visible per category, not hidden |
| **AI Readiness module per role** | Explicit `at_risk_tasks` / `durable_skills` / `resilience_bridge_skills` for every standardized role |
| **Wittgenstein 2035 projection** | Forward-looking education trajectory per country, not just a snapshot |
| **Dual interface** | A youth-facing Skills Signal Engine **and** a policymaker dashboard share the same underlying data |
| **Architecture tab + standalone diagram** | A dedicated tab plus `assets/architecture.html` show every layer of the system, every file, and every data-flow edge |
| **Informal-skill-aware** | "Phone repair", "WhatsApp Business", "MoMo agent", "sari-sari", "vlookup self-taught from YouTube" — all surface as standardized skills |

---

## Limitations

- **Synthetic profiles for the demo.** Production deployment requires real youth-consented data collection, ideally via NGO and government partnerships.
- **Mixed real and benchmarked signals.** Real published values are pulled live for youth NEET, internet penetration, youth literacy, informal employment, and wage evidence across all six demo countries. Automation exposure remains a benchmark-aligned mapping (Frey-Osborne), and some wage rows fall back to PPP / skill-level series when direct U.S.-dollar major-group earnings are not published — every row is tagged via `value_type`, `data_quality_flag`, and a visible badge.
- **API refreshes are manual.** The refresh scripts are runnable on demand; promoting them to scheduled jobs (cron / GitHub Actions) is the next deployment step.
- **Country depth still varies.** Ghana, Nigeria, and the Philippines remain the most mature scenario contexts. Colombia, Peru, and Guatemala have three profiles each, additional validation cases, and deeper pathway coverage, but could still benefit from more country-specific wage and vacancy evidence.
- **Rule-based extraction.** A production system would augment with LLM-based skill extraction (preserving the same pipeline contract) for more nuanced informal-text understanding.
- **Semantic retrieval is role-first, not full skill extraction.** The Hugging Face layer currently improves role recall more than skill canonicalization; semantic skill extraction is the next natural extension.
- **No live job feeds yet.** Mode 2 (labor data) ingests static CSVs; live integration with Greenhouse / Lever / regional job boards is Phase 2.

## Next Steps

1. **Scheduled live ingestion** — promote `scripts/refresh_world_bank_indicators.py` and `scripts/refresh_ilostat_wages.py` from on-demand scripts to scheduled jobs (cron / GitHub Actions), then add ITU broadband and vacancy APIs.
2. **LLM-augmented extraction** — drop in an LLM-based extractor while preserving the existing `extract_normalized_skills` contract; calibrate against the rule-based baseline.
3. **Semantic skill extraction** — continue upgrading the new hint layer into stronger canonical skill extraction so phrases like "fixes cracked screens", "handles customer disputes", or mixed-language descriptions map more reliably to the portable skill vocabulary.
4. **Validation set for rescue cases** — expand the built-in "rule-only missed, hybrid rescued" stories into a small benchmark that any team can inspect directly.
5. **Partnership pilots** — co-design with NGOs and ministries running youth employment programs in West Africa and Southeast Asia.
6. **Public read-only API** — expose the standardized portable skills profile as a portable JSON-LD passport that any platform can consume.
7. **Translation pipeline** — add more local languages (Twi, Hausa, Bisaya, etc.) by extending `data/ui_terms.json`.

---

## Project Summary

UNMAPPED is a portable skills infrastructure layer for young people whose real capabilities are invisible to formal labor systems. Many youth in low- and middle-income countries have meaningful skills from informal work, self-teaching, family businesses, repair work, digital platforms, or community labor, but those skills rarely translate into recognized labor market signals.

Our prototype implements all three of the brief's modules: a **Skills Signal Engine**, an **AI Readiness & Displacement Lens**, and an **Opportunity Matching & Econometric Dashboard**. The Skills Signal Engine converts informal experience, education level, demonstrated competencies, languages, and constraints into a portable, human-readable skills profile mapped to standardized role and skill taxonomies. The Opportunity Matching layer connects that profile to realistic employment, self-employment, gig, and training pathways while surfacing visible economic signals — each badged with its evidence tier (REAL API, OFFICIAL, OFFICIAL FALLBACK, BENCHMARK, LEGACY PROXY).

UNMAPPED is designed as infrastructure rather than a standalone app. Country-specific labor market data, education mappings, automation calibration, language and local terms, opportunity types, and **the entire UI copy layer** are configurable inputs rather than hardcoded assumptions. The result is an explainable, auditable, and localizable system that helps governments, NGOs, training providers, and employers turn invisible skills into actionable opportunity signals.
