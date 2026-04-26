#!/usr/bin/env python3
"""
Refresh wage evidence in data/economic_signals.csv from official ILOSTAT APIs.

This script adds:
  - official country minimum-wage anchors
  - official occupation-aligned monthly earnings
  - wage metadata and source URLs

The project keeps the existing planning proxy column for backward
compatibility, but headline wage evidence should prefer the official fields.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECON_PATH = PROJECT_ROOT / "data" / "economic_signals.csv"
OPPORTUNITY_PATH = PROJECT_ROOT / "data" / "opportunity_catalog.csv"

MIN_WAGE_URL = (
    "https://rplumber.ilo.org/data/indicator"
    "?id=EAR_INEE_CUR_NB_A&lang=en&type=label&latestyear=TRUE&format=.csv&channel=ilostat"
)
OCC_WAGE_URL = (
    "https://rplumber.ilo.org/data/indicator"
    "?id=EAR_EMTA_SEX_OCU_CUR_NB_A&lang=en&type=label&latestyear=TRUE&format=.csv&channel=ilostat"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://ilostat.ilo.org/data/snapshots/earnings/",
}

CURRENCY_PREFERENCE = [
    "Currency: U.S. dollars",
    "Currency: 2021 PPP $",
    "Currency: Local currency",
]

ROLE_OCCUPATION_PREFERENCES = {
    "Device Repair Technician": [
        "Occupation (ISCO-08): 7. Craft and related trades workers",
        "Occupation (Skill level): Skill level 2 ~ medium",
    ],
    "Digital Support Assistant": [
        "Occupation (ISCO-08): 4. Clerical support workers",
        "Occupation (Skill level): Skill level 2 ~ medium",
    ],
    "Mobile Money Agent": [
        "Occupation (ISCO-08): 5. Service and sales workers",
        "Occupation (Skill level): Skill level 2 ~ medium",
        "Occupation (Skill level): Skill level 1 ~ low",
    ],
    "Data Analyst": [
        "Occupation (ISCO-08): 2. Professionals",
        "Occupation (Skill level): Skill levels 3 and 4 ~ high",
    ],
    "Operations Data Coordinator": [
        "Occupation (ISCO-08): 4. Clerical support workers",
        "Occupation (Skill level): Skill level 2 ~ medium",
    ],
    "Finance Operations Associate": [
        "Occupation (ISCO-08): 3. Technicians and associate professionals",
        "Occupation (Skill level): Skill levels 3 and 4 ~ high",
    ],
    "Customer Support / BPO Agent": [
        "Occupation (ISCO-08): 4. Clerical support workers",
        "Occupation (Skill level): Skill level 2 ~ medium",
    ],
    "Microenterprise Operator": [
        "Occupation (ISCO-08): 5. Service and sales workers",
        "Occupation (Skill level): Skill level 1 ~ low",
    ],
    "Junior Web Support / No-Code Assistant": [
        "Occupation (ISCO-08): 3. Technicians and associate professionals",
        "Occupation (Skill level): Skill levels 3 and 4 ~ high",
    ],
}


def fetch_csv(url: str) -> pd.DataFrame:
    response = requests.get(url, headers=HEADERS, timeout=90)
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text))


def first_nonempty(*values: object) -> str:
    for value in values:
        if pd.notna(value) and str(value).strip():
            return str(value).strip()
    return ""


def pick_minimum_wage(country: str, min_df: pd.DataFrame) -> dict:
    subset = min_df[min_df["ref_area.label"] == country]
    for currency in CURRENCY_PREFERENCE:
        matches = subset[subset["classif1.label"] == currency].sort_values("time", ascending=False)
        if not matches.empty:
            rec = matches.iloc[0]
            return {
                "value": float(rec["obs_value"]),
                "currency": str(rec["classif1.label"]),
                "year": int(rec["time"]),
                "note": first_nonempty(rec.get("note_indicator.label"), rec.get("note_source.label")),
                "source": first_nonempty(rec.get("source.label")),
            }
    return {}


def pick_occupation_wage(country: str, role: str, occ_df: pd.DataFrame) -> dict:
    subset = occ_df[
        (occ_df["ref_area.label"] == country)
        & (occ_df["sex.label"] == "Total")
    ]
    for occupation_label in ROLE_OCCUPATION_PREFERENCES.get(role, []):
        occ_subset = subset[subset["classif1.label"] == occupation_label]
        for currency in CURRENCY_PREFERENCE:
            matches = occ_subset[occ_subset["classif2.label"] == currency].sort_values("time", ascending=False)
            if not matches.empty:
                rec = matches.iloc[0]
                if occupation_label.startswith("Occupation (ISCO-08)") and currency == "Currency: U.S. dollars":
                    quality = "direct_major_group_usd"
                elif occupation_label.startswith("Occupation (ISCO-08)"):
                    quality = "direct_major_group_non_usd_fallback"
                else:
                    quality = "skill_level_fallback"
                return {
                    "value": float(rec["obs_value"]),
                    "currency": str(rec["classif2.label"]),
                    "year": int(rec["time"]),
                    "group": occupation_label,
                    "quality": quality,
                    "note": first_nonempty(rec.get("note_indicator.label"), rec.get("note_source.label")),
                    "source": first_nonempty(rec.get("source.label")),
                }
    return {}


def update_economic_signals() -> pd.DataFrame:
    econ = pd.read_csv(ECON_PATH)
    opportunity_catalog = pd.read_csv(OPPORTUNITY_PATH)
    econ = ensure_country_role_coverage(econ, opportunity_catalog)
    min_df = fetch_csv(MIN_WAGE_URL)
    occ_df = fetch_csv(OCC_WAGE_URL)

    min_cache: dict[str, dict] = {}
    occ_cache: dict[tuple[str, str], dict] = {}

    for idx, row in econ.iterrows():
        country = row["country_context"]
        role = row["standardized_role"]

        if country not in min_cache:
            min_cache[country] = pick_minimum_wage(country, min_df)
        if (country, role) not in occ_cache:
            occ_cache[(country, role)] = pick_occupation_wage(country, role, occ_df)

        min_wage = min_cache[country]
        occ_wage = occ_cache[(country, role)]

        econ.at[idx, "official_country_min_wage_value"] = min_wage.get("value")
        econ.at[idx, "official_country_min_wage_currency"] = min_wage.get("currency")
        econ.at[idx, "official_country_min_wage_year"] = min_wage.get("year")
        econ.at[idx, "official_country_min_wage_note"] = min_wage.get("note")
        econ.at[idx, "official_country_min_wage_source"] = min_wage.get("source")
        econ.at[idx, "official_country_min_wage_source_url"] = MIN_WAGE_URL

        econ.at[idx, "official_occupation_monthly_earnings_value"] = occ_wage.get("value")
        econ.at[idx, "official_occupation_monthly_earnings_currency"] = occ_wage.get("currency")
        econ.at[idx, "official_occupation_monthly_earnings_year"] = occ_wage.get("year")
        econ.at[idx, "official_occupation_group"] = occ_wage.get("group")
        econ.at[idx, "official_occupation_quality_note"] = occ_wage.get("quality")
        econ.at[idx, "official_occupation_note"] = occ_wage.get("note")
        econ.at[idx, "official_occupation_source"] = occ_wage.get("source")
        econ.at[idx, "official_occupation_source_url"] = OCC_WAGE_URL

        source_dataset = first_nonempty(row.get("source_dataset"))
        if "ILOSTAT Earnings API" not in source_dataset:
            source_dataset = (
                f"{source_dataset} / ILOSTAT Earnings API"
                if source_dataset else "ILOSTAT Earnings API"
            )
        econ.at[idx, "source_dataset"] = source_dataset

        source_note = first_nonempty(row.get("source_url_or_note"))
        min_note = ""
        if min_wage:
            min_note = (
                f"ILOSTAT min wage {min_wage.get('value'):.3f} "
                f"({min_wage.get('currency')}, {min_wage.get('year')})"
            )
        occ_note = ""
        if occ_wage:
            occ_note = (
                f"ILOSTAT occupation earnings {occ_wage.get('value'):.3f} "
                f"[{occ_wage.get('group')}] ({occ_wage.get('currency')}, {occ_wage.get('year')})"
            )
        combined = " | ".join([part for part in [source_note, min_note, occ_note] if part])
        econ.at[idx, "source_url_or_note"] = combined

        econ.at[idx, "value_type"] = "mixed_real_api_and_benchmark"
        if occ_wage.get("quality") == "direct_major_group_usd":
            econ.at[idx, "data_quality_flag"] = (
                "real_country_indicators_plus_direct_ilostat_wages_plus_role_benchmarks"
            )
        else:
            econ.at[idx, "data_quality_flag"] = (
                "real_country_indicators_plus_ilostat_wages_with_fallback_plus_role_benchmarks"
            )

    econ.to_csv(ECON_PATH, index=False)
    return econ


def ensure_country_role_coverage(econ: pd.DataFrame, opportunity_catalog: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure every country/role pair shown in the opportunity catalog has an
    economic-signals row. Missing rows inherit country-real indicators from
    the same country and role-level narratives from the nearest existing role
    template so the app does not silently lose evidence in the UI.
    """
    needed_pairs = {
        (row.country, row.role)
        for row in opportunity_catalog[["country", "role"]].drop_duplicates().itertuples(index=False)
    }
    existing_pairs = {
        (row.country_context, row.standardized_role)
        for row in econ[["country_context", "standardized_role"]].drop_duplicates().itertuples(index=False)
    }
    missing_pairs = sorted(needed_pairs - existing_pairs)
    if not missing_pairs:
        return econ

    additions: list[dict] = []
    for country, role in missing_pairs:
        country_template_df = econ[econ["country_context"] == country]
        role_template_df = econ[econ["standardized_role"] == role]
        if country_template_df.empty or role_template_df.empty:
            continue

        country_template = country_template_df.iloc[0].to_dict()
        role_template = role_template_df.iloc[0].to_dict()
        role_proxy = (
            pd.to_numeric(role_template_df["wage_floor_proxy_usd_month"], errors="coerce")
            .dropna()
            .median()
        )

        row = {
            "country_context": country,
            "sector": role_template.get("sector", ""),
            "standardized_role": role,
            "wage_floor_proxy_usd_month": round(float(role_proxy), 3) if pd.notna(role_proxy) else role_template.get("wage_floor_proxy_usd_month"),
            "automation_exposure_score": role_template.get("automation_exposure_score"),
            "youth_neet_rate_pct": country_template.get("youth_neet_rate_pct"),
            "internet_penetration_pct": country_template.get("internet_penetration_pct"),
            "youth_literacy_rate_pct": country_template.get("youth_literacy_rate_pct"),
            "informal_employment_pct": country_template.get("informal_employment_pct"),
            "youth_unemployment_signal": country_template.get("youth_unemployment_signal"),
            "sector_growth_signal": role_template.get("sector_growth_signal"),
            "digital_readiness_signal": country_template.get("digital_readiness_signal"),
            "education_quality_signal": country_template.get("education_quality_signal"),
            "informality_signal": role_template.get("informality_signal"),
            "value_type": country_template.get("value_type"),
            "source_dataset": country_template.get("source_dataset"),
            "source_url_or_note": country_template.get("source_url_or_note"),
            "year": country_template.get("year"),
            "data_quality_flag": country_template.get("data_quality_flag"),
        }
        additions.append(row)

    if additions:
        econ = pd.concat([econ, pd.DataFrame(additions)], ignore_index=True)
    return econ


def main() -> None:
    econ = update_economic_signals()
    print(f"Updated {len(econ)} economic signal rows in {ECON_PATH}")
    print(
        econ[
            [
                "country_context",
                "standardized_role",
                "official_country_min_wage_value",
                "official_country_min_wage_currency",
                "official_occupation_monthly_earnings_value",
                "official_occupation_monthly_earnings_currency",
                "official_occupation_group",
                "official_occupation_quality_note",
            ]
        ].head(12).to_string(index=False)
    )


if __name__ == "__main__":
    main()
