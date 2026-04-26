"""
UNMAPPED Normalization Pipeline (Dual Mode)
============================================

MODE 1 — Youth Profile Mode
    Input:  one row from raw_youth_profiles.csv (or a live form)
    Output: portable skills profile with standardized roles, normalized
            skills, missing bridge skills, recommended opportunities,
            visible economic signals, confidence, and a plain-language
            explanation.

MODE 2 — Labor Data Mode
    Input:  one row from raw_global_labor_data.csv
    Output: standardized role mapping with cross-market matches +
            economic signals where region/role overlap exists.

Core functions exposed:
    extract_normalized_skills(text)
    map_profile_to_portable_roles(profile)
    compute_confidence(role_signal_score, skill_count, core_skill_overlap,
                       constraint_penalty=None)
    identify_missing_bridge_skills(normalized_skills, target_role)
    get_economic_signals(country_context, standardized_role)
    recommend_opportunities(profile, standardized_roles, economic_signals)
    normalize_youth_profile(row)
    normalize_labor_record(row)
    run_youth_pipeline()
    run_labor_pipeline()
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from taxonomy import GLOBAL_TAXONOMY, SKILL_NORMALIZATION_MAP  # noqa: E402
from config import (  # noqa: E402
    get_country_config,
    map_education_to_portable_level,
)
from semantic_matching import (  # noqa: E402
    DEFAULT_ROLE_THRESHOLD,
    DEFAULT_SKILL_THRESHOLD,
    FALLBACK_ROLE_THRESHOLD,
    ROLE_SIMILARITY_WEIGHT,
    score_skills_semantically,
    score_roles_semantically,
    semantic_backend_status,
)


PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

RAW_YOUTH_PATH = DATA_DIR / "raw_youth_profiles.csv"
RAW_LABOR_PATH = DATA_DIR / "raw_global_labor_data.csv"
ECON_SIGNALS_PATH = DATA_DIR / "economic_signals.csv"
VALIDATION_CASES_PATH = DATA_DIR / "matching_validation_cases.csv"

NORM_YOUTH_CSV = DATA_DIR / "normalized_youth_profiles.csv"
NORM_YOUTH_JSON = DATA_DIR / "normalized_youth_profiles.json"
NORM_LABOR_CSV = DATA_DIR / "normalized_global_labor_data.csv"
NORM_LABOR_JSON = DATA_DIR / "normalized_global_labor_data.json"


# ---------------------------------------------------------------------------
# 1. Skill extraction (word-boundary safe; informal-aware)
# ---------------------------------------------------------------------------

# Allow `&` and `+` and `/` to live inside skill terms (e.g. "fp&a", "html/css")
# but otherwise rely on standard word boundaries.
def _compile_skill_patterns(skill_map: dict[str, str]) -> list[tuple[re.Pattern, str, str]]:
    patterns = []
    for term, canonical in skill_map.items():
        clean_term = term.strip()
        patterns.append((
            re.compile(
                r"(?<![\w&/+])" + re.escape(clean_term) + r"(?![\w&/+])",
                re.IGNORECASE,
            ),
            clean_term,
            canonical,
        ))
    return patterns


_SKILL_PATTERNS = _compile_skill_patterns(SKILL_NORMALIZATION_MAP)


def extract_normalized_skills(
    raw_text: str,
    country_context: str | None = None,
) -> tuple[list[str], list[str]]:
    """
    Scan free text for known skill markers (formal + informal).
    Returns:
        normalized: deduplicated canonical skill list
        matched_raw: the raw terms that fired (for explainability)
    """
    text = raw_text or ""
    matched_raw: list[str] = []
    normalized: list[str] = []
    seen_canon: set[str] = set()
    seen_raw: set[str] = set()

    skill_patterns = list(_SKILL_PATTERNS)
    if country_context:
        local_terms = get_country_config(country_context).get("local_skill_terms", {})
        if local_terms:
            skill_patterns.extend(_compile_skill_patterns(local_terms))

    for pattern, raw_term, canonical in skill_patterns:
        if pattern.search(text):
            if raw_term not in seen_raw:
                matched_raw.append(raw_term)
                seen_raw.add(raw_term)
            if canonical not in seen_canon:
                normalized.append(canonical)
                seen_canon.add(canonical)

    return normalized, matched_raw


# ---------------------------------------------------------------------------
# 2. Role mapping
# ---------------------------------------------------------------------------

def _signal_match_count(text: str, signals: list[str]) -> int:
    """Count case-insensitive substring hits for each role signal."""
    text_lower = text.lower()
    return sum(1 for sig in signals if sig in text_lower)


def map_profile_to_portable_roles(profile_text: str, top_k: int = 3) -> list[dict]:
    """
    Score every role in the taxonomy using a hybrid of deterministic signal
    counts and optional Hugging Face semantic similarity.

    Rule-based counts remain the main audit trail. Semantic similarity is used
    as a recall layer for informal phrasing and multilingual variants.

    Returns the top-K roles with:
      - role_id
      - role dict
      - signal_score
      - semantic_score
      - hybrid_score
      - match_basis

    If nothing clears the thresholds, returns a semantic fallback when one is
    plausible. Otherwise it falls back to Microenterprise Operator.
    """
    semantic_matches = {
        match["role_id"]: match
        for match in score_roles_semantically(profile_text)
    }
    scored = []
    for role_id, role in GLOBAL_TAXONOMY.items():
        signal_score = _signal_match_count(profile_text, role["skill_signals"])
        semantic_score = float(
            semantic_matches.get(role_id, {}).get("semantic_score", 0.0)
        )
        hybrid_score = signal_score + (semantic_score * ROLE_SIMILARITY_WEIGHT)

        if signal_score > 0 and semantic_score >= DEFAULT_ROLE_THRESHOLD:
            match_basis = "hybrid_rule_and_semantic"
        elif signal_score > 0:
            match_basis = "rule_based"
        elif semantic_score >= DEFAULT_ROLE_THRESHOLD:
            match_basis = "semantic_only"
        else:
            match_basis = "below_threshold"

        if signal_score > 0 or semantic_score >= DEFAULT_ROLE_THRESHOLD:
            scored.append({
                "role_id": role_id,
                "role": role,
                "signal_score": signal_score,
                "semantic_score": round(semantic_score, 4),
                "hybrid_score": round(hybrid_score, 4),
                "match_basis": match_basis,
            })

    scored.sort(
        key=lambda r: (
            -r["hybrid_score"],
            -r["signal_score"],
            -r["semantic_score"],
            r["role"]["title"],
        )
    )
    if not scored:
        top_semantic = next(iter(semantic_matches.values()), None)
        if top_semantic and top_semantic["semantic_score"] >= FALLBACK_ROLE_THRESHOLD:
            fallback_role = GLOBAL_TAXONOMY[top_semantic["role_id"]]
            scored = [{
                "role_id": top_semantic["role_id"],
                "role": fallback_role,
                "signal_score": 0,
                "semantic_score": round(float(top_semantic["semantic_score"]), 4),
                "hybrid_score": round(
                    float(top_semantic["semantic_score"]) * ROLE_SIMILARITY_WEIGHT,
                    4,
                ),
                "match_basis": "semantic_fallback",
            }]
        else:
            scored = [{
                "role_id": "GR-MICRO-001",
                "role": GLOBAL_TAXONOMY["GR-MICRO-001"],
                "signal_score": 0,
                "semantic_score": 0.0,
                "hybrid_score": 0.0,
                "match_basis": "taxonomy_fallback",
            }]
    return scored[:top_k]


def map_profile_to_portable_roles_rule_only(profile_text: str, top_k: int = 3) -> list[dict]:
    """
    Deterministic baseline used for validation storytelling.

    Mirrors the pre-semantic behavior: rank only by signal-match count.
    """
    scored = []
    for role_id, role in GLOBAL_TAXONOMY.items():
        score = _signal_match_count(profile_text, role["skill_signals"])
        if score > 0:
            scored.append({
                "role_id": role_id,
                "role": role,
                "signal_score": score,
            })

    scored.sort(key=lambda r: (-r["signal_score"], r["role"]["title"]))
    if not scored:
        scored = [{
            "role_id": "GR-MICRO-001",
            "role": GLOBAL_TAXONOMY["GR-MICRO-001"],
            "signal_score": 0,
        }]
    return scored[:top_k]


def map_to_global_role(raw_title: str, raw_skills: str) -> tuple[str, dict, int]:
    """Single-best role match used by labor-data mode."""
    matches = map_profile_to_portable_roles(f"{raw_title} {raw_skills}", top_k=1)
    top = matches[0]
    return top["role_id"], top["role"], top["signal_score"]


# ---------------------------------------------------------------------------
# 3. Confidence scoring
# ---------------------------------------------------------------------------

def compute_confidence(
    role_signal_score: int,
    skill_count: int,
    core_skill_overlap: int,
    constraint_penalty: int | None = None,
) -> tuple[int, str]:
    """
    Transparent, explainable confidence model:
      - Base 40
      - + min(role_signal * 8, 24)
      - + min(skill_count * 5, 25)
      - + min(core_overlap * 6, 18)
      - − constraint_penalty (e.g. low broadband, no credential)
    Tiers: High >=85, Medium 65–84, Low <65.
    """
    score = 40
    score += min(role_signal_score * 8, 24)
    score += min(skill_count * 5, 25)
    score += min(core_skill_overlap * 6, 18)
    if constraint_penalty:
        score -= int(constraint_penalty)
    score = max(0, min(score, 99))

    if score >= 85:
        tier = "High"
    elif score >= 65:
        tier = "Medium"
    else:
        tier = "Low"
    return score, tier


_CONSTRAINT_WEIGHTS_DF: pd.DataFrame | None = None


def _load_constraint_weights() -> pd.DataFrame:
    """Load constraint penalty rules from data/constraint_weights.csv (cached)."""
    global _CONSTRAINT_WEIGHTS_DF
    if _CONSTRAINT_WEIGHTS_DF is None:
        weights_path = DATA_DIR / "constraint_weights.csv"
        if weights_path.exists():
            _CONSTRAINT_WEIGHTS_DF = pd.read_csv(weights_path)
        else:
            # Empty fallback so the pipeline still runs if the file is missing
            _CONSTRAINT_WEIGHTS_DF = pd.DataFrame(
                columns=["constraint_keyword", "penalty_score", "category", "description"]
            )
    return _CONSTRAINT_WEIGHTS_DF


def _constraint_penalty(profile_row: pd.Series) -> tuple[int, list[dict]]:
    """
    Data-driven penalty model. Reads weights from constraint_weights.csv so the
    rules are auditable and adjustable without code changes. Each match is
    deduplicated by category — multiple keywords in the same category only
    fire once (so 'limited broadband; intermittent power' doesn't double-bill
    the Connectivity / Infrastructure axis spuriously).

    Returns:
        total penalty score, and a list of matched-constraint records for
        downstream explainability/audit.
    """
    constraints = (profile_row.get("constraints", "") or "").lower()
    weights_df = _load_constraint_weights()

    matched: list[dict] = []
    seen_categories: set[str] = set()

    # Iterate longest-keyword-first so 'no formal credential' beats 'no degree'
    rules = sorted(
        weights_df.to_dict(orient="records"),
        key=lambda r: -len(str(r.get("constraint_keyword", ""))),
    )
    for rule in rules:
        kw = str(rule.get("constraint_keyword", "")).strip().lower()
        if not kw or kw not in constraints:
            continue
        category = str(rule.get("category", "Other"))
        if category in seen_categories:
            continue
        seen_categories.add(category)
        matched.append({
            "keyword": kw,
            "category": category,
            "penalty": int(rule.get("penalty_score", 0)),
            "description": rule.get("description", ""),
        })

    total = sum(m["penalty"] for m in matched)
    return total, matched


def extract_semantic_skill_hints(
    raw_text: str,
    existing_skills: list[str],
    allowed_skills: set[str] | None = None,
    top_k: int = 4,
) -> list[dict]:
    """
    Return semantic skill hints that are not already explicitly extracted.

    These are treated as adjacent evidence, not merged into the canonical
    extracted-skill list, so the system preserves a clean distinction between
    explicit evidence and model inference.
    """
    existing = set(existing_skills)
    hints = []
    for match in score_skills_semantically(raw_text, top_k=12):
        if match["canonical_skill"] in existing:
            continue
        if allowed_skills is not None and match["canonical_skill"] not in allowed_skills:
            continue
        if match["semantic_score"] < DEFAULT_SKILL_THRESHOLD:
            continue
        hints.append({
            "canonical_skill": match["canonical_skill"],
            "semantic_score": round(match["semantic_score"], 4),
            "example_phrases": match.get("example_phrases", []),
        })
        if len(hints) >= top_k:
            break
    return hints


# ---------------------------------------------------------------------------
# 4. Bridge skills
# ---------------------------------------------------------------------------

def identify_missing_bridge_skills(
    normalized_skills: list[str],
    target_role: dict,
) -> dict:
    """
    Compare the profile's normalized skills against the role's core
    skills and return what's missing (core gap) plus the role's
    explicit bridge skills (the upskilling target).
    """
    have = set(normalized_skills)
    core = set(target_role.get("core_skills", []))
    bridges = list(target_role.get("bridge_skills", []))
    missing_core = sorted(core - have)
    return {
        "missing_core_skills": missing_core,
        "bridge_skills": bridges,
    }


# ---------------------------------------------------------------------------
# 5. Economic signals
# ---------------------------------------------------------------------------

_ECON_DF: pd.DataFrame | None = None


def _load_econ_df() -> pd.DataFrame:
    global _ECON_DF
    if _ECON_DF is None:
        _ECON_DF = pd.read_csv(ECON_SIGNALS_PATH)
    return _ECON_DF


def get_economic_signals(country_context: str, standardized_role: str) -> dict | None:
    """
    Return the economic signal record for a given (country, role) pair,
    if one exists. Otherwise None.
    """
    df = _load_econ_df()
    # Strip any trailing level suffix (e.g. "Data Analyst – Entry" -> "Data Analyst")
    role_base = standardized_role.split(" – ")[0].strip()
    match = df[
        (df["country_context"] == country_context)
        & (df["standardized_role"] == role_base)
    ]
    if match.empty:
        return None
    rec = match.iloc[0].to_dict()
    return rec


def _coerce_float(value) -> float | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_best_wage_signal(signals: dict | None) -> dict:
    """
    Return the best available wage evidence with clear provenance.

    Preference order:
      1. Official occupation-aligned monthly earnings in U.S. dollars
      2. Official country minimum-wage anchor in U.S. dollars
      3. Official occupation-aligned PPP / local-currency fallback (display only)
      4. Legacy planning proxy (USD)
    """
    signals = signals or {}

    occupation_value = _coerce_float(signals.get("official_occupation_monthly_earnings_value"))
    occupation_currency = str(signals.get("official_occupation_monthly_earnings_currency") or "")
    occupation_group = str(signals.get("official_occupation_group") or "")
    occupation_year = signals.get("official_occupation_monthly_earnings_year")
    occupation_quality = str(signals.get("official_occupation_quality_note") or "")

    if occupation_value is not None and occupation_currency == "Currency: U.S. dollars":
        return {
            "label": "Official occupation-aligned earnings",
            "display_value": occupation_value,
            "display_currency": occupation_currency,
            "numeric_usd_month": occupation_value,
            "year": occupation_year,
            "group": occupation_group,
            "quality": occupation_quality or "direct_major_group_usd",
        }

    minimum_value = _coerce_float(signals.get("official_country_min_wage_value"))
    minimum_currency = str(signals.get("official_country_min_wage_currency") or "")
    minimum_year = signals.get("official_country_min_wage_year")

    if minimum_value is not None and minimum_currency == "Currency: U.S. dollars":
        return {
            "label": "Official country wage anchor",
            "display_value": minimum_value,
            "display_currency": minimum_currency,
            "numeric_usd_month": minimum_value,
            "year": minimum_year,
            "group": "Country minimum wage",
            "quality": "country_minimum_wage_usd",
        }

    if occupation_value is not None:
        return {
            "label": "Official occupation earnings fallback",
            "display_value": occupation_value,
            "display_currency": occupation_currency,
            "numeric_usd_month": None,
            "year": occupation_year,
            "group": occupation_group,
            "quality": occupation_quality or "non_usd_fallback",
        }

    proxy_value = _coerce_float(signals.get("wage_floor_proxy_usd_month"))
    if proxy_value is not None:
        return {
            "label": "Planning estimate",
            "display_value": proxy_value,
            "display_currency": "Currency: U.S. dollars",
            "numeric_usd_month": proxy_value,
            "year": signals.get("year"),
            "group": "Legacy modeled pathway estimate",
            "quality": "planning_proxy",
        }

    return {
        "label": "No wage evidence",
        "display_value": None,
        "display_currency": "",
        "numeric_usd_month": None,
        "year": None,
        "group": "",
        "quality": "missing",
    }


# ---------------------------------------------------------------------------
# 6. Opportunity recommendation
# ---------------------------------------------------------------------------

_CATALOG_DF: pd.DataFrame | None = None


def _load_opportunity_catalog() -> pd.DataFrame:
    """Load opportunity_catalog.csv (cached). Returns empty DF if missing."""
    global _CATALOG_DF
    if _CATALOG_DF is None:
        path = DATA_DIR / "opportunity_catalog.csv"
        if path.exists():
            _CATALOG_DF = pd.read_csv(path)
        else:
            _CATALOG_DF = pd.DataFrame(
                columns=["country", "role", "opportunity_label",
                         "type", "entry_barrier", "typical_pathway"]
            )
    return _CATALOG_DF


def get_catalog_pathways(country: str, role_title: str) -> list[dict]:
    """Look up real-market opportunity pathways from the catalog."""
    df = _load_opportunity_catalog()
    matches = df[(df["country"] == country) & (df["role"] == role_title)]
    return matches.to_dict(orient="records")


# ---------------------------------------------------------------------------
# AI Readiness module (Module 2 — at-risk / durable / resilience tasks)
# ---------------------------------------------------------------------------

_AI_READINESS_DF: pd.DataFrame | None = None


def _load_ai_readiness() -> pd.DataFrame:
    """Load ai_readiness.csv (at-risk / durable / resilience by role)."""
    global _AI_READINESS_DF
    if _AI_READINESS_DF is None:
        path = DATA_DIR / "ai_readiness.csv"
        if path.exists():
            _AI_READINESS_DF = pd.read_csv(path)
        else:
            _AI_READINESS_DF = pd.DataFrame(
                columns=["global_role_id", "role_title",
                         "at_risk_tasks", "durable_skills", "resilience_bridge_skills"]
            )
    return _AI_READINESS_DF


def get_ai_readiness(role_id: str) -> dict | None:
    """Return the AI Readiness breakdown for a role, or None."""
    df = _load_ai_readiness()
    match = df[df["global_role_id"] == role_id]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


# ---------------------------------------------------------------------------
# Education projections (Wittgenstein-style 2035)
# ---------------------------------------------------------------------------

_PROJECTION_DF: pd.DataFrame | None = None


def _load_education_projections() -> pd.DataFrame:
    global _PROJECTION_DF
    if _PROJECTION_DF is None:
        path = DATA_DIR / "education_projection_signals.csv"
        if path.exists():
            _PROJECTION_DF = pd.read_csv(path)
        else:
            _PROJECTION_DF = pd.DataFrame(columns=[
                "country_context", "year",
                "secondary_completion_projection",
                "tertiary_attainment_projection",
                "structural_signal", "source_notes",
            ])
    return _PROJECTION_DF


def get_education_projection(country_context: str) -> dict | None:
    """Return the Wittgenstein-style 2035 education projection for a country."""
    df = _load_education_projections()
    match = df[df["country_context"] == country_context]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def recommend_opportunities(
    profile: pd.Series,
    standardized_roles: list[dict],
    economic_signals_by_role: dict[str, dict | None],
) -> list[dict]:
    """
    Build a realistic, ranked list of opportunity options for the
    profile. Each option includes:
      - opportunity_label (from cross_market_examples in taxonomy)
      - opportunity_type
      - matched_role
      - missing_bridge_skills
      - next_best_step
      - economic_signals (visible, with provenance)
      - catalog_pathways (real-market pathways from opportunity_catalog.csv)
    """
    country = profile.get("country_context", "")
    cfg = get_country_config(country)
    interest = (profile.get("opportunity_interest", "") or "").lower()
    constraints = (profile.get("constraints", "") or "").lower()

    opportunity_interest_tokens = {token.strip() for token in interest.split(";") if token.strip()}
    device_access = str(profile.get("device_access", "") or "").lower()
    internet_access = str(profile.get("internet_access", "") or "").lower()
    income_bracket = str(profile.get("income_bracket", "") or "").lower()
    education_level = str(profile.get("education_level", "") or "").lower()

    def score_economic_context(
        pathway_type: str,
        pathway_label: str,
        role_title: str,
        signals: dict,
    ) -> tuple[int, list[str], list[str]]:
        """Use country-real signals as part of pathway ranking, with benchmark notes kept separate."""
        score = 0
        country_reasons: list[str] = []
        benchmark_reasons: list[str] = []
        haystack = " ".join([
            pathway_type.lower(),
            pathway_label.lower(),
            role_title.lower(),
        ])

        internet = signals.get("internet_penetration_pct")
        if internet is not None:
            if any(token in haystack for token in ["remote", "digital", "web", "assistant", "support", "whatsapp"]):
                if internet >= 70:
                    score += 2
                    country_reasons.append(
                        f"internet access is comparatively strong for this country ({internet:.1f}%)"
                    )
                elif internet >= 55:
                    score += 1
                    country_reasons.append(
                        f"internet access is workable for phone-first digital pathways ({internet:.1f}%)"
                    )
                else:
                    score -= 2
                    country_reasons.append(
                        f"internet access remains a real bottleneck for digital-heavy work ({internet:.1f}%)"
                    )

        literacy = signals.get("youth_literacy_rate_pct")
        if literacy is not None and any(
            token in haystack for token in ["employment", "assistant", "clerk", "support", "finance", "operations"]
        ):
            if literacy >= 95:
                score += 1
                country_reasons.append(
                    f"youth literacy is high enough to support structured entry pathways ({literacy:.1f}%)"
                )
            elif literacy < 85:
                score -= 1
                country_reasons.append(
                    f"literacy constraints can make formal screening less forgiving ({literacy:.1f}%)"
                )

        neet = signals.get("youth_neet_rate_pct")
        if neet is not None:
            if neet <= 13:
                score += 1
                country_reasons.append(
                    f"youth NEET is relatively lower here, suggesting somewhat less congestion ({neet:.1f}%)"
                )
            elif neet >= 22:
                score -= 1
                country_reasons.append(
                    f"youth NEET is elevated, so even reachable pathways may face tougher competition ({neet:.1f}%)"
                )

        automation = signals.get("automation_exposure_score")
        if automation is not None:
            if automation < 0.30:
                score += 1
                benchmark_reasons.append(
                    f"automation exposure is low for this role ({automation:.2f})"
                )
            elif automation >= 0.80:
                score -= 2
                benchmark_reasons.append(
                    f"automation exposure is high for this role ({automation:.2f})"
                )
            elif automation >= 0.55:
                score -= 1
                benchmark_reasons.append(
                    f"automation exposure is moderate-to-high for this role ({automation:.2f})"
                )

        wage_signal = get_best_wage_signal(signals)
        wage = wage_signal.get("numeric_usd_month")
        if wage:
            if wage >= 250:
                score += 1
                benchmark_reasons.append(
                    f"{wage_signal.get('label', 'wage evidence')} is relatively stronger "
                    f"(about USD {int(wage)}/month)"
                )
            elif wage <= 150:
                benchmark_reasons.append(
                    f"{wage_signal.get('label', 'wage evidence')} is modest "
                    f"(about USD {int(wage)}/month)"
                )

        return score, country_reasons, benchmark_reasons

    def fit_band(score: int) -> str:
        if score >= 7:
            return "Strong Now"
        if score >= 4:
            return "Reachable with One Step"
        return "Longer Ramp"

    def score_pathway(
        role_title: str,
        pathway_type: str,
        entry_barrier: str,
        pathway_label: str,
        pathway_text: str,
    ) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []

        if entry_barrier == "low":
            score += 3
            reasons.append("low entry barrier")
        elif entry_barrier == "medium":
            score += 1
            reasons.append("moderate entry barrier")

        haystack = " ".join([
            pathway_type.lower(),
            pathway_label.lower(),
            pathway_text.lower(),
            role_title.lower(),
        ])

        if "remote" in haystack or "virtual assistant" in haystack or "upwork" in haystack:
            if "intermittent" in internet_access or "intermittent" in constraints or "unstable" in constraints:
                score -= 3
                reasons.append("internet instability makes remote work harder right now")
            if "smartphone" in device_access and "laptop" not in device_access:
                score -= 2
                reasons.append("current device setup is better for phone-based work than laptop-heavy remote work")
            elif "shared laptop" in device_access:
                score -= 1
                reasons.append("shared laptop setup may limit consistent remote availability")

        if "self-employment" in haystack or "trader" in haystack or "stall" in haystack:
            if (
                "self-employment" in opportunity_interest_tokens
                or "microenterprise" in opportunity_interest_tokens
                or "sales" in opportunity_interest_tokens
                or "trade" in opportunity_interest_tokens
                or "repair work" in opportunity_interest_tokens
            ):
                score += 2
                reasons.append("matches stated self-employment interest")
            if "low-income" in income_bracket:
                score -= 1
                reasons.append("starter capital may still be a constraint")
            if "home" in constraints or "mobility" in constraints:
                score += 1
                reasons.append("can be started closer to home")

        if "employment" in haystack or "formal" in haystack:
            if "no formal credential" in constraints or "no degree" in constraints or "unfinished" in education_level:
                score -= 1
                reasons.append("formal screening may be a hurdle")

        if "gig" in haystack and (
            "gig work" in opportunity_interest_tokens
            or "remote gig work" in opportunity_interest_tokens
            or "gig" in opportunity_interest_tokens
        ):
            score += 2
            reasons.append("matches stated gig-work preference")

        if "training pathway" in haystack and "training pathway" in opportunity_interest_tokens:
            score += 2
            reasons.append("aligns with stated upskilling interest")

        if (
            "digital support" in opportunity_interest_tokens
            or "customer support" in opportunity_interest_tokens
        ) and any(token in haystack for token in ["support", "assistant", "customer"]):
            score += 2
            reasons.append("matches stated support-work interest")

        if (
            "junior web support" in opportunity_interest_tokens
            or "web support" in opportunity_interest_tokens
        ) and any(token in haystack for token in ["web", "wordpress", "shopify", "no-code", "freelancer"]):
            score += 2
            reasons.append("matches stated web-support interest")

        if "admin support" in opportunity_interest_tokens and any(
            token in haystack for token in ["admin", "clerk", "data", "records", "back-office"]
        ):
            score += 2
            reasons.append("matches stated admin-support interest")

        if "bookkeeping" in opportunity_interest_tokens and any(
            token in haystack for token in ["bookkeeping", "account", "finance"]
        ):
            score += 2
            reasons.append("matches stated bookkeeping interest")

        if "device repair" in opportunity_interest_tokens and "repair" in haystack:
            score += 2
            reasons.append("matches stated repair-work interest")

        if "phone repair" in pathway_label.lower() or "repair" in role_title.lower():
            if "smartphone" in device_access or "shared smartphone" in device_access:
                score += 1
                reasons.append("builds on existing repair-oriented experience")

        if "whatsapp" in haystack or "mobile money" in haystack:
            if "smartphone" in device_access:
                score += 1
                reasons.append("fits a phone-first setup")

        if "family obligations" in constraints or "time-poor" in constraints:
            if "gig" in haystack or "self-employment" in haystack:
                score += 1
                reasons.append("more flexible around current time constraints")

        if "gendered mobility" in constraints and ("remote" in haystack or "home" in pathway_text.lower()):
            score += 1
            reasons.append("reduces mobility burden")

        if not reasons:
            reasons.append("closest current fit based on skills, interest, and constraints")

        return score, reasons

    options = []
    for role_rank, sr in enumerate(standardized_roles):
        role = sr["role"]
        role_id = sr["role_id"]
        role_title = role["title"]
        role_priority_bonus = max(0, 2 - role_rank)

        # Cross-reference country opportunity types
        country_examples = cfg["opportunity_types"]

        # Bridge skills from the role
        bridges = role.get("bridge_skills", [])

        # Visible economic signals (the key World Bank requirement)
        signals = economic_signals_by_role.get(role_id)
        visible_signals = {}
        if signals:
            wage_signal = get_best_wage_signal(signals)
            visible_signals = {
                "wage_floor_proxy_usd_month": signals.get("wage_floor_proxy_usd_month"),
                "wage_signal_label": wage_signal.get("label"),
                "wage_signal_display_value": wage_signal.get("display_value"),
                "wage_signal_display_currency": wage_signal.get("display_currency"),
                "wage_signal_numeric_usd_month": wage_signal.get("numeric_usd_month"),
                "official_country_min_wage_value": signals.get("official_country_min_wage_value"),
                "official_country_min_wage_currency": signals.get("official_country_min_wage_currency"),
                "official_country_min_wage_year": signals.get("official_country_min_wage_year"),
                "official_country_min_wage_note": signals.get("official_country_min_wage_note"),
                "official_country_min_wage_source": signals.get("official_country_min_wage_source"),
                "official_country_min_wage_source_url": signals.get("official_country_min_wage_source_url"),
                "official_occupation_monthly_earnings_value": signals.get("official_occupation_monthly_earnings_value"),
                "official_occupation_monthly_earnings_currency": signals.get("official_occupation_monthly_earnings_currency"),
                "official_occupation_monthly_earnings_year": signals.get("official_occupation_monthly_earnings_year"),
                "official_occupation_group": signals.get("official_occupation_group"),
                "official_occupation_quality_note": signals.get("official_occupation_quality_note"),
                "official_occupation_note": signals.get("official_occupation_note"),
                "official_occupation_source": signals.get("official_occupation_source"),
                "official_occupation_source_url": signals.get("official_occupation_source_url"),
                "automation_exposure_score": signals.get("automation_exposure_score"),
                # Real-source numeric indicators (added in v2 upgrade)
                "youth_neet_rate_pct": signals.get("youth_neet_rate_pct"),
                "internet_penetration_pct": signals.get("internet_penetration_pct"),
                "youth_literacy_rate_pct": signals.get("youth_literacy_rate_pct"),
                "informal_employment_pct": signals.get("informal_employment_pct"),
                # Narrative signals
                "digital_readiness_signal": signals.get("digital_readiness_signal"),
                "informality_signal": signals.get("informality_signal"),
                "youth_unemployment_signal": signals.get("youth_unemployment_signal"),
                "sector_growth_signal": signals.get("sector_growth_signal"),
                # Provenance
                "value_type": signals.get("value_type"),
                "source_dataset": signals.get("source_dataset"),
                "source_url_or_note": signals.get("source_url_or_note"),
                "year": signals.get("year"),
                "data_quality_flag": signals.get("data_quality_flag"),
            }

        # Localize the surface label using cross-market examples if available
        local_label = role.get("cross_market_examples", {}).get(country, role_title)

        # Real-market pathways from opportunity_catalog.csv (additive — does
        # not replace the taxonomy-derived label, but enriches it with entry
        # barriers and typical pathway descriptions for this country/role).
        catalog_pathways = get_catalog_pathways(country, role_title)
        if not catalog_pathways:
            catalog_pathways = [{
                "country": country,
                "role": role_title,
                "opportunity_label": local_label,
                "type": role.get("opportunity_types", ["employment"])[0],
                "entry_barrier": "medium",
                "typical_pathway": "bridge skill completion + local validation",
            }]

        scored_pathways = []
        for pathway in catalog_pathways:
            pathway_score, pathway_reasons = score_pathway(
                role_title=role_title,
                pathway_type=str(pathway.get("type", "")),
                entry_barrier=str(pathway.get("entry_barrier", "medium")).lower(),
                pathway_label=str(pathway.get("opportunity_label", local_label)),
                pathway_text=str(pathway.get("typical_pathway", "")),
            )
            if role_rank == 0:
                pathway_score += 1
                pathway_reasons.append("builds on the strongest detected role signal")
            econ_score = 0
            country_signal_reasons: list[str] = []
            benchmark_signal_reasons: list[str] = []
            if visible_signals:
                econ_score, country_signal_reasons, benchmark_signal_reasons = score_economic_context(
                    pathway_type=str(pathway.get("type", "")),
                    pathway_label=str(pathway.get("opportunity_label", local_label)),
                    role_title=role_title,
                    signals=visible_signals,
                )
            scored_pathways.append({
                **pathway,
                "reachability_score": pathway_score + econ_score + role_priority_bonus,
                "base_pathway_score": pathway_score,
                "economic_readiness_score": econ_score,
                "role_priority_bonus": role_priority_bonus,
                "reachability_reasons": pathway_reasons,
                "country_signal_reasons": country_signal_reasons,
                "benchmark_signal_reasons": benchmark_signal_reasons,
            })

        scored_pathways.sort(
            key=lambda p: (-p["reachability_score"], p.get("entry_barrier", ""), p.get("opportunity_label", ""))
        )
        best_pathway = scored_pathways[0]
        chosen_type = best_pathway.get("type", role.get("opportunity_types", ["employment"])[0])

        if bridges:
            next_step = bridges[0]
        else:
            next_step = "Validate local fit and continue building a work sample"

        starting_assets = []
        if device_access:
            starting_assets.append(f"device access: {profile.get('device_access')}")
        if internet_access:
            starting_assets.append(f"internet access: {profile.get('internet_access')}")
        if opportunity_interest_tokens:
            starting_assets.append(
                "stated interest: " + ", ".join(sorted(opportunity_interest_tokens))
            )

        why_fit_now = (
            f"Best immediate pathway is **{best_pathway.get('opportunity_label', local_label)}** "
            f"because it is a {best_pathway.get('entry_barrier', 'reachable')}-barrier option and "
            + "; ".join(best_pathway["reachability_reasons"][:3])
            + "."
        )
        if best_pathway.get("country_signal_reasons"):
            why_fit_now += (
                " Country context also supports this direction because "
                + "; ".join(best_pathway["country_signal_reasons"][:2])
                + "."
            )

        evidence_mix_label = "Country-real indicators + ILOSTAT wages + automation benchmark"
        if not visible_signals:
            evidence_mix_label = "Catalog-only fallback"

        # AI Readiness breakdown — at-risk vs durable vs resilience-bridge tasks.
        # This is the explicit Module 2 requirement from the brief.
        ai_readiness = get_ai_readiness(role_id)

        options.append({
            "opportunity_label": best_pathway.get("opportunity_label", local_label),
            "opportunity_type": chosen_type,
            "matched_role_id": role_id,
            "matched_role_title": role_title,
            "missing_bridge_skills": bridges,
            "next_best_step": next_step,
            "reachability_score": best_pathway.get("reachability_score", 0),
            "base_pathway_score": best_pathway.get("base_pathway_score", 0),
            "economic_readiness_score": best_pathway.get("economic_readiness_score", 0),
            "role_priority_bonus": best_pathway.get("role_priority_bonus", 0),
            "fit_band": fit_band(best_pathway.get("reachability_score", 0)),
            "reachability_reasons": best_pathway.get("reachability_reasons", []),
            "country_signal_reasons": best_pathway.get("country_signal_reasons", []),
            "benchmark_signal_reasons": best_pathway.get("benchmark_signal_reasons", []),
            "why_it_fits_now": why_fit_now,
            "evidence_mix_label": evidence_mix_label,
            "starting_assets": starting_assets,
            "economic_signals": visible_signals,
            "country_context_pathways": country_examples,
            "catalog_pathways": scored_pathways,
            "ai_readiness": ai_readiness,
        })

    options.sort(
        key=lambda option: (
            -option.get("reachability_score", 0),
            option.get("matched_role_title", ""),
        )
    )
    return options


def build_validation_story() -> dict:
    """
    Return one concrete story showing where hybrid semantic matching helps.
    """
    case = {
        "title": "Semantic rescue case: paraphrased repair work",
        "profile_name": "Demo youth case",
        "country_context": "Ghana",
        "input_text": (
            "Fixes cracked screens and charging issues for neighbors, learned from "
            "video tutorials, keeps a handwritten queue of customers, and wants "
            "to grow into steady tech support work."
        ),
        "why_this_case_matters": (
            "The wording is realistic but avoids the exact taxonomy phrases like "
            "'phone repair' or 'screen replacement'."
        ),
    }
    if VALIDATION_CASES_PATH.exists():
        try:
            validation_df = pd.read_csv(VALIDATION_CASES_PATH)
            rescued = validation_df.loc[
                validation_df["rescued_by_semantic"].astype(str).str.lower().eq("yes")
            ]
            if not rescued.empty:
                first = rescued.iloc[0].to_dict()
                case = {
                    "title": f"Semantic rescue case: {first.get('case_id', 'validation benchmark')}",
                    "profile_name": first.get("case_id", "Validation case"),
                    "country_context": first.get("country_context", "Unknown"),
                    "input_text": first.get("input_text", ""),
                    "why_this_case_matters": first.get("notes", ""),
                }
        except Exception:
            pass
    rule_only = map_profile_to_portable_roles_rule_only(case["input_text"], top_k=1)[0]
    hybrid = map_profile_to_portable_roles(case["input_text"], top_k=1)[0]

    case["rule_only_role"] = rule_only["role"]["title"]
    case["rule_only_role_id"] = rule_only["role_id"]
    case["rule_only_signal_score"] = rule_only["signal_score"]
    case["hybrid_role"] = hybrid["role"]["title"]
    case["hybrid_role_id"] = hybrid["role_id"]
    case["hybrid_signal_score"] = hybrid["signal_score"]
    case["hybrid_semantic_score"] = round(hybrid.get("semantic_score", 0.0), 4)
    case["semantic_skill_hints"] = extract_semantic_skill_hints(
        case["input_text"],
        [],
        allowed_skills=set(hybrid["role"].get("core_skills", [])),
    )
    case["improvement_summary"] = (
        f"Rule-only mapping returned **{case['rule_only_role']}**, but hybrid matching "
        f"rescued the case to **{case['hybrid_role']}** with semantic support "
        f"{case['hybrid_semantic_score']:.2f}."
    )
    return case


# ---------------------------------------------------------------------------
# 7. Per-record normalization
# ---------------------------------------------------------------------------

def normalize_youth_profile(row: pd.Series) -> dict:
    """
    The MODE 1 contract. Takes one youth profile row and produces a
    portable skills profile with explainability and visible economic
    signals.
    """
    profile_id = row.get("profile_id", "")
    name = row.get("name", "")
    country = row.get("country_context", "")
    local_context = row.get("local_context", "")
    education_raw = row.get("education_level", "")
    informal_exp = row.get("informal_experience", "")
    demonstrated = row.get("demonstrated_skills", "")
    languages = row.get("languages", "")
    constraints = row.get("constraints", "")
    interest = row.get("opportunity_interest", "")

    # Combine all free-text fields for skill + role matching
    combined_text = " ".join([
        str(informal_exp), str(demonstrated), str(interest),
    ])

    # 1. Education → portable level
    education_portable = map_education_to_portable_level(country, education_raw)

    # 2. Skill extraction
    normalized_skills, matched_terms = extract_normalized_skills(combined_text, country)
    # 3. Role mapping (top-3 candidates). Feed back canonical extracted skills
    # so country-specific aliases can influence downstream role ranking.
    role_match_text = " ".join([combined_text, " ".join(normalized_skills)]).strip()
    role_matches = map_profile_to_portable_roles(role_match_text, top_k=3)
    allowed_hint_skills = set()
    for match in role_matches:
        allowed_hint_skills.update(match["role"].get("core_skills", []))
    semantic_skill_hints = extract_semantic_skill_hints(
        combined_text,
        normalized_skills,
        allowed_skills=allowed_hint_skills,
    )
    semantic_status = semantic_backend_status()
    role_match_details = [
        {
            "role_id": match["role_id"],
            "role_title": match["role"]["title"],
            "role_level": match["role"]["level"],
            "signal_score": match["signal_score"],
            "semantic_score": match.get("semantic_score", 0.0),
            "hybrid_score": match.get("hybrid_score", match["signal_score"]),
            "match_basis": match.get("match_basis", "rule_based"),
        }
        for match in role_matches
    ]

    # 4. Confidence using best role match
    top = role_matches[0]
    core = set(top["role"].get("core_skills", []))
    core_overlap = len(set(normalized_skills) & core)
    penalty, matched_constraints = _constraint_penalty(row)
    confidence, tier = compute_confidence(
        top["signal_score"],
        len(normalized_skills),
        core_overlap,
        constraint_penalty=penalty,
    )

    # 5. Bridge gaps
    bridge = identify_missing_bridge_skills(normalized_skills, top["role"])

    # 6. Economic signals (one per candidate role)
    econ_by_role = {}
    for r in role_matches:
        econ_by_role[r["role_id"]] = get_economic_signals(country, r["role"]["title"])

    # 7. Recommended opportunities
    opportunities = recommend_opportunities(row, role_matches, econ_by_role)

    # 8. Standardized role labels
    standardized_roles = [
        f"{r['role']['title']} – {r['role']['level']}" for r in role_matches
    ]

    # 9. Portable skills profile (the "passport")
    portable_profile = {
        "profile_id": profile_id,
        "name": name,
        "country_context": country,
        "local_context": local_context,
        "education_portable_level": education_portable["portable_level"],
        "education_completion": education_portable["completion"],
        "languages": languages,
        "normalized_skills": normalized_skills,
        "semantic_skill_hints": semantic_skill_hints,
        "informal_evidence": informal_exp,
    }

    # 10. Explanation
    primary_role = top["role"]["title"]
    matched_terms_str = ", ".join(matched_terms[:6]) + (
        "..." if len(matched_terms) > 6 else ""
    ) if matched_terms else "limited explicit skill markers"
    explanation_parts = [
        f"matched {top['signal_score']} role signal(s) for {primary_role}",
        f"detected skill markers: {matched_terms_str}",
        f"{core_overlap}/{len(core)} core skill(s) present for primary role",
    ]
    if top.get("semantic_score", 0) >= DEFAULT_ROLE_THRESHOLD:
        explanation_parts.append(
            f"semantic similarity support {top['semantic_score']:.2f} via "
            f"{semantic_status['model_name'].split('/')[-1]}"
        )
    if semantic_skill_hints:
        explanation_parts.append(
            "adjacent skill hints "
            + ", ".join(
                hint["canonical_skill"] for hint in semantic_skill_hints[:3]
            )
        )
    if penalty:
        constraint_categories = sorted({m["category"] for m in matched_constraints})
        cat_str = ", ".join(constraint_categories)
        explanation_parts.append(
            f"applied -{penalty} confidence penalty across "
            f"{len(constraint_categories)} constraint categor"
            f"{'y' if len(constraint_categories) == 1 else 'ies'} ({cat_str})"
        )
    explanation = (
        "Mapped because " + "; ".join(explanation_parts) + ". "
        f"Confidence is {tier.lower()}."
    )

    # 11. Human-readable summary (for the user, not the judge)
    constraint_clause = (
        f" Some constraints — {constraints} — affected confidence."
        if penalty else ""
    )
    languages_clause = f" Languages: {languages}." if languages else ""
    primary_signals = econ_by_role.get(top["role_id"]) or {}
    primary_wage_signal = get_best_wage_signal(primary_signals)
    if primary_wage_signal.get("display_value") is not None:
        if primary_wage_signal.get("display_currency") == "Currency: U.S. dollars":
            wage_clause = (
                f" {primary_wage_signal.get('label')} for this role is around "
                f"USD {int(round(primary_wage_signal.get('display_value')))} per month."
            )
        elif primary_wage_signal.get("display_currency"):
            wage_clause = (
                f" {primary_wage_signal.get('label')} for this role is around "
                f"{primary_wage_signal.get('display_value'):.0f} "
                f"({primary_wage_signal.get('display_currency')}) per month."
            )
        else:
            wage_clause = ""
    else:
        wage_clause = ""

    top_opportunity = opportunities[0] if opportunities else {}
    fit_clause = (
        f" Best immediate pathway: {top_opportunity.get('opportunity_label')}."
        if top_opportunity.get("opportunity_label")
        else ""
    )
    top_opportunity_signals = top_opportunity.get("economic_signals", {}) or primary_signals
    asset_clause = ""
    if top_opportunity.get("starting_assets"):
        asset_clause = (
            " Current strengths to build from: "
            + "; ".join(top_opportunity["starting_assets"][:3])
            + "."
        )
    hint_clause = ""
    if semantic_skill_hints:
        hint_clause = (
            " Adjacent strengths the model also sees: "
            + ", ".join(h["canonical_skill"] for h in semantic_skill_hints[:2])
            + "."
        )

    pathway_step = top_opportunity.get("next_best_step") or (
        bridge["bridge_skills"][0] if bridge["bridge_skills"] else "continue building portfolio"
    )
    top_wage_signal = get_best_wage_signal(top_opportunity_signals)
    if top_wage_signal.get("display_value") is not None:
        if top_wage_signal.get("display_currency") == "Currency: U.S. dollars":
            top_wage_clause = (
                f" {top_wage_signal.get('label')} for this pathway is around "
                f"USD {int(round(top_wage_signal.get('display_value')))} per month."
            )
        elif top_wage_signal.get("display_currency"):
            top_wage_clause = (
                f" {top_wage_signal.get('label')} for this pathway is around "
                f"{top_wage_signal.get('display_value'):.0f} "
                f"({top_wage_signal.get('display_currency')}) per month."
            )
        else:
            top_wage_clause = wage_clause
    else:
        top_wage_clause = wage_clause

    human_summary = (
        f"{name or 'This profile'} shows informal evidence aligned with "
        f"{primary_role} and {len(normalized_skills)} explicitly extracted skill(s)."
        f"{fit_clause} Realistic next step: "
        f"{pathway_step}."
        f"{asset_clause}{hint_clause}{top_wage_clause}{languages_clause}{constraint_clause}"
    )

    return {
        "profile_id": profile_id,
        "name": name,
        "country_context": country,
        "portable_skills_profile": portable_profile,
        "standardized_roles": standardized_roles,
        "primary_role_id": top["role_id"],
        "primary_role_title": primary_role,
        "isco_like_category": top["role"].get("isco_like_category"),
        "normalized_skills": normalized_skills,
        "semantic_skill_hints": semantic_skill_hints,
        "role_match_details": role_match_details,
        "missing_bridge_skills": bridge,
        "recommended_opportunities": opportunities,
        "economic_signals": primary_signals,  # signals for the primary role
        "education_projection": get_education_projection(country),
        "confidence_score": confidence,
        "confidence_tier": tier,
        "constraint_penalty": penalty,
        "matched_constraints": matched_constraints,  # audit trail
        "semantic_matching_status": semantic_status,
        "validation_story": build_validation_story(),
        "explanation": explanation,
        "human_readable_summary": human_summary,
    }


def normalize_labor_record(row: pd.Series) -> dict:
    """The MODE 2 contract — preserves the previous labor-side behavior."""
    raw_title = row.get("raw_role_title", "")
    raw_skills = row.get("raw_skills_text", "")
    region = row.get("region", "Unknown")
    education = row.get("local_education_level", "")

    normalized_skills, matched_raw = extract_normalized_skills(raw_skills, region)
    role_match_text = " ".join([raw_title, raw_skills, " ".join(normalized_skills)]).strip()
    role_id, role, signal_score = map_to_global_role(raw_title, role_match_text)
    semantic_status = semantic_backend_status()
    top_match = map_profile_to_portable_roles(role_match_text, top_k=1)[0]
    semantic_skill_hints = extract_semantic_skill_hints(
        raw_skills,
        normalized_skills,
        allowed_skills=set(top_match["role"].get("core_skills", [])),
    )
    core_overlap = len(set(normalized_skills) & set(role["core_skills"]))
    confidence, tier = compute_confidence(
        signal_score, len(normalized_skills), core_overlap
    )
    cross_market = [
        {"region": r, "equivalent_role": label}
        for r, label in role["cross_market_examples"].items()
        if r != region
    ]

    # Add econ signals if region matches a known country in the signal table
    econ = get_economic_signals(region, role["title"])

    parts = []
    if signal_score > 0:
        parts.append(f"matched {signal_score} role signal(s) for {role['title']}")
    if matched_raw:
        head = ", ".join(matched_raw[:5]) + ("..." if len(matched_raw) > 5 else "")
        parts.append(f"detected skill terms: {head}")
    if core_overlap > 0:
        parts.append(f"{core_overlap}/{len(role['core_skills'])} core skill(s) present")
    if not parts:
        parts.append("low signal — fallback mapping applied")
    explanation = "Mapped because " + "; ".join(parts) + "."

    return {
        "region": region,
        "raw_role_title": raw_title,
        "global_role_id": role_id,
        "standardized_role": f"{role['title']} – {role['level']}",
        "normalized_skills": normalized_skills,
        "semantic_skill_hints": semantic_skill_hints,
        "role_match_details": [{
            "role_id": top_match["role_id"],
            "role_title": top_match["role"]["title"],
            "role_level": top_match["role"]["level"],
            "signal_score": top_match["signal_score"],
            "semantic_score": top_match.get("semantic_score", 0.0),
            "hybrid_score": top_match.get("hybrid_score", top_match["signal_score"]),
            "match_basis": top_match.get("match_basis", "rule_based"),
        }],
        "core_skill_overlap": core_overlap,
        "local_education_level": education,
        "confidence_score": confidence,
        "confidence_tier": tier,
        "cross_market_matches": cross_market,
        "economic_signals": econ,
        "semantic_matching_status": semantic_status,
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# 8. Pipeline runners
# ---------------------------------------------------------------------------

def run_youth_pipeline(raw_path: Path = RAW_YOUTH_PATH) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    records = [normalize_youth_profile(row) for _, row in df.iterrows()]
    return pd.DataFrame(records)


def run_labor_pipeline(raw_path: Path = RAW_LABOR_PATH) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    records = [normalize_labor_record(row) for _, row in df.iterrows()]
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# 9. CLI entry point
# ---------------------------------------------------------------------------

def _persist(df: pd.DataFrame, csv_path: Path, json_path: Path,
             list_cols: list[str], dict_cols: list[str] = None) -> None:
    csv_df = df.copy()
    for col in list_cols:
        if col in csv_df.columns:
            csv_df[col] = csv_df[col].apply(json.dumps)
    for col in (dict_cols or []):
        if col in csv_df.columns:
            csv_df[col] = csv_df[col].apply(
                lambda v: json.dumps(v) if v is not None else ""
            )
    csv_df.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(df.to_dict(orient="records"), indent=2,
                                    default=str))


def main():
    print("=" * 72)
    print(" UNMAPPED — Portable Skills Infrastructure for Invisible Talent")
    print("=" * 72)

    # === Mode 1: Youth pipeline ===
    print(f"\n[MODE 1] Youth Profile Pipeline — input: {RAW_YOUTH_PATH.name}")
    youth_df = run_youth_pipeline()
    _persist(
        youth_df,
        NORM_YOUTH_CSV,
        NORM_YOUTH_JSON,
        list_cols=["standardized_roles", "normalized_skills", "semantic_skill_hints", "role_match_details"],
        dict_cols=[
            "portable_skills_profile",
            "missing_bridge_skills",
            "recommended_opportunities",
            "economic_signals",
            "semantic_matching_status",
            "validation_story",
        ],
    )
    print(f"  -> wrote {NORM_YOUTH_CSV.name} and {NORM_YOUTH_JSON.name}")
    print(f"  -> {len(youth_df)} youth profiles normalized across "
          f"{youth_df['country_context'].nunique()} countries")

    print("\n  Confidence distribution:")
    print(youth_df["confidence_tier"].value_counts().to_string(
        header=False))

    print("\n  Primary role distribution:")
    print(youth_df["primary_role_title"].value_counts().to_string(
        header=False))

    # === Mode 2: Labor pipeline ===
    print(f"\n[MODE 2] Labor Data Pipeline — input: {RAW_LABOR_PATH.name}")
    labor_df = run_labor_pipeline()
    _persist(
        labor_df,
        NORM_LABOR_CSV,
        NORM_LABOR_JSON,
        list_cols=["normalized_skills", "semantic_skill_hints", "role_match_details"],
        dict_cols=["cross_market_matches", "economic_signals", "semantic_matching_status"],
    )
    print(f"  -> wrote {NORM_LABOR_CSV.name} and {NORM_LABOR_JSON.name}")
    print(f"  -> {len(labor_df)} labor records normalized")

    # === Sample output ===
    print("\n" + "═" * 72)
    print(" SAMPLE — Amara (Ghana)")
    print("═" * 72)
    sample = youth_df.iloc[0].to_dict()  # P001 = Amara
    print(f"\n  Name:                   {sample['name']}")
    print(f"  Country:                {sample['country_context']}")
    print(f"  Primary Role:           {sample['primary_role_title']}")
    print(f"  ISCO-like:              {sample['isco_like_category']}")
    print(f"  Normalized Skills:      {sample['normalized_skills']}")
    print(f"  Confidence:             {sample['confidence_score']} ({sample['confidence_tier']})")
    print(f"  Standardized Roles:     {sample['standardized_roles']}")
    print(f"\n  Top Opportunity:")
    if sample['recommended_opportunities']:
        op = sample['recommended_opportunities'][0]
        print(f"    Label:                {op['opportunity_label']}")
        print(f"    Type:                 {op['opportunity_type']}")
        print(f"    Next best step:       {op['next_best_step']}")
        sig = op.get('economic_signals', {})
        wage_signal = get_best_wage_signal(sig)
        if wage_signal.get("display_value") is not None:
            if wage_signal.get("display_currency") == "Currency: U.S. dollars":
                wage_text = f"USD {int(round(wage_signal.get('display_value')))}"
            elif wage_signal.get("display_currency") == "Currency: 2021 PPP $":
                wage_text = f"PPP$ {int(round(wage_signal.get('display_value')))}"
            else:
                wage_text = f"{wage_signal.get('display_value'):.0f}"
            print(f"    Wage evidence:        {wage_signal.get('label')} ({wage_text}/month)")
        print(f"    Automation exposure:  {sig.get('automation_exposure_score')}")
        print(f"    Informality:          {sig.get('informality_signal')}")
    print(f"\n  Explanation:            {sample['explanation']}")
    print(f"\n  Human summary:          {sample['human_readable_summary']}")
    print()


if __name__ == "__main__":
    main()
