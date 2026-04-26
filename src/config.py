"""
UNMAPPED Country Configuration
==============================

This is the localizability layer. UNMAPPED is built as infrastructure,
not a one-country app — country-specific knowledge lives in
**data/country_configs.json** (loaded at import time) rather than
being hardcoded in the pipeline.

To add a new country, edit `data/country_configs.json`. No code
changes required. The pipeline does not need to know.

The inline `COUNTRY_CONFIGS_FALLBACK` dict at the bottom of this file
is a safety net: if the JSON is missing or unreadable, the system
still runs against the bundled defaults.

Each country config covers:
  - education_taxonomy: how local credentials map to a portable level
  - language_terms: local-language skill markers the matcher should know
  - opportunity_types: which opportunity pathways are realistic locally
  - economic_signal_source: which real-source anchors apply
  - automation_calibration: country-specific multiplier on automation
    exposure (proxy for labor market context)
  - local_terminology_labels: country-specific term overrides used by
    the UI's local-terminology toggle
"""

import json
from pathlib import Path

_CONFIG_JSON_PATH = Path(__file__).parent.parent / "data" / "country_configs.json"

# Tracks whether the JSON load succeeded. Consumers (e.g. the Streamlit app)
# can read this to surface a visible banner instead of silently relying on
# the inline fallback dict — judges flagged silent config fallbacks as a risk.
COUNTRY_CONFIGS_LOAD_STATUS: dict = {
    "loaded_from": "fallback_inline_dict",
    "error": None,
    "path": str(_CONFIG_JSON_PATH),
}


def _load_country_configs() -> dict:
    """Load country configs from JSON. Falls back to inline dict on failure."""
    try:
        if _CONFIG_JSON_PATH.exists():
            with open(_CONFIG_JSON_PATH) as f:
                data = json.load(f)
            COUNTRY_CONFIGS_LOAD_STATUS["loaded_from"] = "json"
            return data
        COUNTRY_CONFIGS_LOAD_STATUS["error"] = "country_configs.json not found"
    except (json.JSONDecodeError, OSError) as exc:
        COUNTRY_CONFIGS_LOAD_STATUS["error"] = f"{type(exc).__name__}: {exc}"
    return COUNTRY_CONFIGS_FALLBACK


COUNTRY_CONFIGS_FALLBACK = {
    "Ghana": {
        "education_taxonomy": {
            "JHS": {"portable_level": "Lower Secondary", "completion": True},
            "JHS dropout": {"portable_level": "Lower Secondary", "completion": False},
            "SHS": {"portable_level": "Upper Secondary", "completion": True},
            "Secondary school certificate": {"portable_level": "Upper Secondary", "completion": True},
            "SHS graduate": {"portable_level": "Upper Secondary", "completion": True},
            "NVTI": {"portable_level": "Vocational Cert", "completion": True},
            "Polytechnic HND": {"portable_level": "Diploma (HND)", "completion": True},
            "Polytechnic HND incomplete": {"portable_level": "Diploma (HND)", "completion": False},
            "Diploma": {"portable_level": "Diploma", "completion": True},
            "Bachelor": {"portable_level": "Bachelor's", "completion": True},
        },
        "language_terms": ["Twi", "Ga", "Ewe", "Fante", "Dagbani", "Akan"],
        "local_skill_terms": {
            "momo": "Mobile Money",
            "mtn momo": "Mobile Money",
            "vodafone cash": "Mobile Money",
            "nvti": "Vocational Certification",
            "trotro": "Local Transport Ops",
        },
        "opportunity_types": [
            "Self-employment (microenterprise)",
            "Mobile money agent",
            "Device repair",
            "Junior web/digital support (remote)",
            "Operations/clerical (urban)",
            "Training pathway: Excel / bookkeeping / digital basics",
        ],
        "economic_signal_source": "ILOSTAT (West Africa) + WDI (Ghana) + ITU + Frey-Osborne + ISCO-08",
        "automation_calibration": 1.0,
        "currency_symbol": "GHS (proxy USD shown)",
        "broadband_constraint": "Mobile-first, fixed broadband uneven outside urban hubs",
    },

    "Nigeria": {
        "education_taxonomy": {
            "WAEC SSCE": {"portable_level": "Upper Secondary", "completion": True},
            "WAEC": {"portable_level": "Upper Secondary", "completion": True},
            "SSCE": {"portable_level": "Upper Secondary", "completion": True},
            "OND": {"portable_level": "Diploma (OND)", "completion": True},
            "OND incomplete": {"portable_level": "Diploma (OND)", "completion": False},
            "HND": {"portable_level": "Diploma (HND)", "completion": True},
            "NCE": {"portable_level": "Teaching Cert (NCE)", "completion": True},
            "B.Sc": {"portable_level": "Bachelor's", "completion": True},
            "Bachelor": {"portable_level": "Bachelor's", "completion": True},
            "Quranic + secondary": {"portable_level": "Upper Secondary", "completion": True},
        },
        "language_terms": ["Yoruba", "Igbo", "Hausa", "Pidgin", "Arabic"],
        "local_skill_terms": {
            "opay": "Mobile Money",
            "paga": "Mobile Money",
            "moniepoint": "Mobile Money",
            "interswitch": "Payments Systems",
            "paystack": "Payments Systems",
            "flutterwave": "Payments Systems",
            "kobotoolbox": "Survey/M&E Tools",
        },
        "opportunity_types": [
            "POS/agent banking",
            "Self-employment (microenterprise)",
            "BPO / customer support",
            "Junior web/digital support (remote)",
            "NGO M&E / data entry",
            "Training pathway: SQL / Excel / digital marketing",
        ],
        "economic_signal_source": "ILOSTAT + WDI (Nigeria) + CBN (agent banking) + ITU + Frey-Osborne",
        "automation_calibration": 1.0,
        "currency_symbol": "NGN (proxy USD shown)",
        "broadband_constraint": "Power and broadband instability are structural constraints",
    },

    "Philippines": {
        "education_taxonomy": {
            "Senior High": {"portable_level": "Upper Secondary", "completion": True},
            "Senior High graduate": {"portable_level": "Upper Secondary", "completion": True},
            "SHS": {"portable_level": "Upper Secondary", "completion": True},
            "TESDA NC II": {"portable_level": "Vocational Cert", "completion": True},
            "B.S.": {"portable_level": "Bachelor's", "completion": True},
            "B.S. incomplete": {"portable_level": "Bachelor's", "completion": False},
            "College Graduate": {"portable_level": "Bachelor's", "completion": True},
            "Bachelor": {"portable_level": "Bachelor's", "completion": True},
        },
        "language_terms": ["Tagalog", "Cebuano", "Hiligaynon", "Bisaya", "Kapampangan", "Ilocano", "Taglish"],
        "local_skill_terms": {
            "shopee": "E-commerce Platform",
            "lazada": "E-commerce Platform",
            "grabpay": "Mobile Money",
            "gcash": "Mobile Money",
            "maya": "Mobile Money",
            "tesda": "Vocational Certification",
            "sari-sari": "Microenterprise",
        },
        "opportunity_types": [
            "BPO / customer support",
            "Virtual assistant / digital support",
            "E-commerce ops (Shopee/Lazada)",
            "Junior web/no-code support (remote)",
            "Shared services / clerical",
            "Training pathway: SQL / accounting / English-comms upgrade",
        ],
        "economic_signal_source": "ILOSTAT + PSA Labor Force Survey + ITU + Frey-Osborne + TESDA",
        "automation_calibration": 1.05,  # slightly higher BPO/clerical exposure
        "currency_symbol": "PHP (proxy USD shown)",
        "broadband_constraint": "Strong baseline broadband; uneven outside metro areas",
    },
}


# Resolve actual configs at import time: prefer JSON, fall back to inline dict.
# This is what the rest of the codebase consumes.
COUNTRY_CONFIGS = _load_country_configs()


def get_country_config(country_context: str) -> dict:
    """Return the config for a country, with sensible fallbacks."""
    return COUNTRY_CONFIGS.get(country_context, COUNTRY_CONFIGS["Ghana"])


def list_countries() -> list[str]:
    return list(COUNTRY_CONFIGS.keys())


def map_education_to_portable_level(country_context: str, raw_education: str) -> dict:
    """
    Translate a free-text local credential to a portable level.
    Searches the country's taxonomy for any matching key as a substring.
    Returns dict with portable_level, completion, and the raw key used.
    """
    cfg = get_country_config(country_context)
    raw_lower = (raw_education or "").lower()

    # Prefer longest-key match (so 'Polytechnic HND incomplete' beats 'HND')
    matches = [
        (key, val) for key, val in cfg["education_taxonomy"].items()
        if key.lower() in raw_lower
    ]
    if matches:
        matches.sort(key=lambda kv: -len(kv[0]))
        key, val = matches[0]
        return {**val, "matched_key": key, "raw": raw_education}

    generic_rules = [
        (["college graduate", "university graduate", "bachelor", "b.sc", "bs ", "ba "], {
            "portable_level": "Bachelor's",
            "completion": True,
            "matched_key": "generic_tertiary_complete",
        }),
        (["college", "university", "undergraduate", "college level"], {
            "portable_level": "Tertiary / College",
            "completion": False,
            "matched_key": "generic_tertiary_incomplete",
        }),
        (["technical institute", "technical college", "technical school", "vocational", "trade school", "certificate"], {
            "portable_level": "Vocational / Technical",
            "completion": True,
            "matched_key": "generic_vocational_complete",
        }),
        (["technical", "vocational incomplete", "trade course"], {
            "portable_level": "Vocational / Technical",
            "completion": False,
            "matched_key": "generic_vocational_incomplete",
        }),
        (["senior high", "high school", "secondary", "shs", "ssce", "waec", "bachillerato", "secundaria", "diversificado"], {
            "portable_level": "Upper Secondary",
            "completion": not any(token in raw_lower for token in ["incomplete", "dropout", "unfinished"]),
            "matched_key": "generic_upper_secondary",
        }),
        (["junior high", "jhs", "lower secondary"], {
            "portable_level": "Lower Secondary",
            "completion": not any(token in raw_lower for token in ["incomplete", "dropout", "unfinished"]),
            "matched_key": "generic_lower_secondary",
        }),
    ]
    for patterns, fallback in generic_rules:
        if any(pattern in raw_lower for pattern in patterns):
            return {**fallback, "raw": raw_education}

    return {
        "portable_level": "Unmapped",
        "completion": False,
        "matched_key": None,
        "raw": raw_education,
    }
