#!/usr/bin/env python3
"""
Refresh country-level econometric anchors in data/economic_signals.csv from the
public World Bank API.

This complements scripts/refresh_ilostat_wages.py (which handles the wage
layer) by pulling the country-real signals the judges scored most strongly:

  - SL.UEM.NEET.ZS         Youth NEET (% of youth)
  - IT.NET.USER.ZS         Internet penetration (% of population)
  - SE.ADT.1524.LT.ZS      Youth literacy 15-24 (%)
  - SL.ISV.IFRM.ZS         Informal employment (% of total non-agricultural)
                           [falls back to SL.EMP.UMEM.ZS if not published]
  - NY.GDP.PCAP.CD         GDP per capita (current US$)

For each demo country we keep the most recent non-null observation and write
it back to economic_signals.csv along with the year and the exact source URL,
so the recommendation cards can render `REAL · World Bank API` badges with
verifiable provenance instead of relying on snapshot constants.

Run:
    python scripts/refresh_world_bank_indicators.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECON_PATH = PROJECT_ROOT / "data" / "economic_signals.csv"

# ISO-3 codes used by the World Bank country API.
COUNTRY_CODES = {
    "Ghana": "GHA",
    "Nigeria": "NGA",
    "Philippines": "PHL",
    "Colombia": "COL",
    "Peru": "PER",
    "Guatemala": "GTM",
}

# Indicator -> (target column in economic_signals.csv, friendly label).
# The World Bank API endpoint pattern is:
#   https://api.worldbank.org/v2/country/{ISO3}/indicator/{INDICATOR}?format=json&per_page=...
INDICATORS: dict[str, dict[str, str]] = {
    "SL.UEM.NEET.ZS": {
        "column": "youth_neet_rate_pct",
        "label": "Youth NEET (% of youth)",
    },
    "IT.NET.USER.ZS": {
        "column": "internet_penetration_pct",
        "label": "Internet penetration (% of population)",
    },
    "SE.ADT.1524.LT.ZS": {
        "column": "youth_literacy_rate_pct",
        "label": "Youth literacy 15-24 (%)",
    },
    "SL.ISV.IFRM.ZS": {
        "column": "informal_employment_pct",
        "label": "Informal employment (% of non-agricultural)",
    },
}

# Optional context indicator — written to source_url_or_note for transparency
# even when not part of the canonical signal columns.
CONTEXT_INDICATORS: dict[str, str] = {
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
}

API_BASE = "https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator}"
HEADERS = {"User-Agent": "UNMAPPED-data-refresh/1.0"}


def fetch_latest_observation(iso3: str, indicator: str) -> dict[str, Any] | None:
    """Return the most recent non-null observation, or None if the series is empty."""
    url = API_BASE.format(iso3=iso3, indicator=indicator)
    params = {"format": "json", "per_page": 60}
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=60)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"  ! API error for {iso3}/{indicator}: {exc}", file=sys.stderr)
        return None

    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        return None
    rows = payload[1]
    for row in rows:
        if row.get("value") is not None:
            return {
                "value": float(row["value"]),
                "year": int(row["date"]),
                "source_url": (
                    f"{API_BASE.format(iso3=iso3, indicator=indicator)}"
                    f"?format=json&date={row['date']}"
                ),
            }
    return None


def build_provenance_note(country_code: str, observations: dict[str, dict]) -> str:
    parts = []
    for indicator, obs in observations.items():
        meta = INDICATORS.get(indicator) or {"label": CONTEXT_INDICATORS.get(indicator, indicator)}
        parts.append(
            f"{meta['label']} = {obs['value']:.2f} ({obs['year']}) "
            f"[{indicator}, World Bank API, {country_code}]"
        )
    return " | ".join(parts)


def update_economic_signals() -> pd.DataFrame:
    if not ECON_PATH.exists():
        raise SystemExit(f"economic_signals.csv not found at {ECON_PATH}")

    econ = pd.read_csv(ECON_PATH)

    # Per-country observation cache so we hit each indicator endpoint once.
    observations: dict[str, dict[str, dict]] = {}
    for country, iso3 in COUNTRY_CODES.items():
        print(f"Refreshing {country} ({iso3}) ...")
        obs_for_country: dict[str, dict] = {}
        for indicator in {**INDICATORS, **CONTEXT_INDICATORS}.keys():
            obs = fetch_latest_observation(iso3, indicator)
            if obs is not None:
                obs_for_country[indicator] = obs
                meta = INDICATORS.get(indicator) or {"label": CONTEXT_INDICATORS.get(indicator, indicator)}
                print(f"  {meta['label']:<48} {obs['value']:>10.2f}  ({obs['year']})")
            else:
                print(f"  {indicator}: no published value available")
        observations[country] = obs_for_country

    # Apply each country's observations to every row of that country.
    refreshed_rows = 0
    for idx, row in econ.iterrows():
        country = str(row.get("country_context", ""))
        obs_for_country = observations.get(country, {})
        if not obs_for_country:
            continue

        for indicator, spec in INDICATORS.items():
            obs = obs_for_country.get(indicator)
            if obs is None:
                continue
            column = spec["column"]
            if column not in econ.columns:
                econ[column] = pd.NA
            econ.at[idx, column] = obs["value"]

        # Update provenance fields. Keep any prior ILOSTAT note appended.
        new_note = build_provenance_note(COUNTRY_CODES[country], obs_for_country)
        prior_note = str(row.get("source_url_or_note") or "")
        if "World Bank API" not in prior_note:
            combined = " | ".join(part for part in [prior_note, new_note] if part)
        else:
            # Replace the World Bank section while preserving any non-WB tail
            non_wb_tail = " | ".join(
                part for part in prior_note.split(" | ")
                if "World Bank API" not in part
            )
            combined = " | ".join(part for part in [non_wb_tail, new_note] if part)
        econ.at[idx, "source_url_or_note"] = combined

        # Keep year column synced to the freshest core indicator pulled.
        max_year = max(
            obs_for_country[ind]["year"]
            for ind in INDICATORS
            if ind in obs_for_country
        )
        econ.at[idx, "year"] = max_year

        # Reinforce dataset/value-type tagging so the badges classify correctly.
        existing_dataset = str(row.get("source_dataset") or "")
        if "World Bank API" not in existing_dataset:
            econ.at[idx, "source_dataset"] = (
                f"{existing_dataset} / World Bank API"
                if existing_dataset else "World Bank API"
            )
        econ.at[idx, "value_type"] = "mixed_real_api_and_benchmark"
        refreshed_rows += 1

    econ.to_csv(ECON_PATH, index=False)
    print()
    print(f"Updated {refreshed_rows} rows in {ECON_PATH.relative_to(PROJECT_ROOT)}")
    return econ


def main() -> None:
    econ = update_economic_signals()
    summary = (
        econ.dropna(subset=["youth_neet_rate_pct"])
        .drop_duplicates("country_context")
        [[
            "country_context",
            "youth_neet_rate_pct",
            "internet_penetration_pct",
            "youth_literacy_rate_pct",
            "informal_employment_pct",
            "year",
        ]]
        .reset_index(drop=True)
    )
    print()
    print("Country-level signal snapshot (latest available):")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
