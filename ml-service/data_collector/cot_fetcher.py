"""CFTC COT gold futures fetcher + daily up-sampler.

Data source: CFTC Socrata JSON API (Disaggregated Futures-Only).
- URL: https://publicreporting.cftc.gov/resource/72hh-3qpy.json
- Gold contract: cftc_contract_market_code='088691' (GOLD - COMMODITY
  EXCHANGE INC., COMEX GC 100oz)
- History: 2006-06-13 onwards (Managed Money breakdown available)
- Release: every Friday 15:30 ET, data "as-of" prior Tuesday (3-day lag)

Integration notes:
- The "known_from" column = report_date + 4 days is the earliest timestamp
  at which the COT row is publicly known. Use this for leak-safe joins with
  daily price data.
- The raw "report_date" is for optimistic/biased backtests (3-day lookahead).
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
import requests


DEFAULT_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
GOLD_CMC = "088691"  # CFTC contract_market_code for COMEX GC 100oz

SELECT_FIELDS = [
    "report_date_as_yyyy_mm_dd",
    "open_interest_all",
    "m_money_positions_long_all",
    "m_money_positions_short_all",
    "m_money_positions_spread",
    "prod_merc_positions_long",
    "prod_merc_positions_short",
    "swap_positions_long_all",
    "swap__positions_short_all",  # sic: CFTC's double underscore
    "other_rept_positions_long",
    "other_rept_positions_short",
    "nonrept_positions_long_all",
    "nonrept_positions_short_all",
    "traders_m_money_long_all",
    "traders_m_money_short_all",
]


def _default_cache_path() -> Path:
    here = Path(__file__).resolve().parents[1]  # ml-service/
    return here / "data" / "cot_gold.csv"


def fetch_gold_cot(
    start_date: str = "2020-01-01",
    end_date: Optional[str] = None,
    cache_path: Optional[Path] = None,
    force_refresh: bool = False,
    timeout: int = 30,
) -> pd.DataFrame:
    """Fetch gold COT weekly data from CFTC Socrata API with local caching.

    Returns DataFrame sorted by report_date ASC with columns:
        report_date (datetime), known_from (datetime),
        open_interest, mm_long_abs, mm_short_abs, mm_spread_abs,
        prod_merc_long, prod_merc_short, swap_long, swap_short,
        other_rept_long, other_rept_short,
        nonrept_long, nonrept_short,
        mm_traders_long, mm_traders_short,
        mm_net, mm_net_pct_oi, mm_long_pct_oi, mm_short_pct_oi,
        comm_net, comm_net_pct_oi, swap_net

    Derived columns use Managed Money net = long - short.
    """
    cache_path = cache_path or _default_cache_path()
    end_date = end_date or date.today().isoformat()

    cached: Optional[pd.DataFrame] = None
    if cache_path.exists() and not force_refresh:
        try:
            cached = pd.read_csv(cache_path, parse_dates=["report_date", "known_from"])
            if not cached.empty:
                latest_cached = pd.Timestamp(cached["report_date"].max()).normalize()
                # Refresh from last known + 1 day to pick up new weekly releases
                start_date = (latest_cached + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception:
            cached = None

    start_iso = f"{start_date}T00:00:00"
    end_iso = f"{end_date}T00:00:00"
    if start_iso >= end_iso:
        # Cache is already up-to-date — return as is
        if cached is not None:
            return cached.sort_values("report_date").reset_index(drop=True)
        return pd.DataFrame()

    params = {
        "$where": (
            f"cftc_contract_market_code='{GOLD_CMC}' "
            f"AND report_date_as_yyyy_mm_dd >= '{start_iso}' "
            f"AND report_date_as_yyyy_mm_dd <= '{end_iso}'"
        ),
        "$select": ",".join(SELECT_FIELDS),
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": "50000",
    }

    resp = requests.get(DEFAULT_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    rows = resp.json()

    if not rows:
        new_df = pd.DataFrame()
    else:
        new_df = pd.DataFrame(rows)
        new_df["report_date"] = pd.to_datetime(new_df["report_date_as_yyyy_mm_dd"])
        new_df = new_df.drop(columns=["report_date_as_yyyy_mm_dd"])

        rename = {
            "open_interest_all": "open_interest",
            "m_money_positions_long_all": "mm_long_abs",
            "m_money_positions_short_all": "mm_short_abs",
            "m_money_positions_spread": "mm_spread_abs",
            "prod_merc_positions_long": "prod_merc_long",
            "prod_merc_positions_short": "prod_merc_short",
            "swap_positions_long_all": "swap_long",
            "swap__positions_short_all": "swap_short",
            "other_rept_positions_long": "other_rept_long",
            "other_rept_positions_short": "other_rept_short",
            "nonrept_positions_long_all": "nonrept_long",
            "nonrept_positions_short_all": "nonrept_short",
            "traders_m_money_long_all": "mm_traders_long",
            "traders_m_money_short_all": "mm_traders_short",
        }
        new_df = new_df.rename(columns=rename)
        numeric_cols = [c for c in new_df.columns if c not in ("report_date",)]
        for col in numeric_cols:
            new_df[col] = pd.to_numeric(new_df[col], errors="coerce")

        # known_from = report_date + 4 days (Friday release after Tue report)
        new_df["known_from"] = new_df["report_date"] + pd.Timedelta(days=4)

        # Derived features
        oi = new_df["open_interest"].replace(0, pd.NA)
        new_df["mm_net"] = new_df["mm_long_abs"] - new_df["mm_short_abs"]
        new_df["mm_net_pct_oi"] = (new_df["mm_net"] / oi).fillna(0.0)
        new_df["mm_long_pct_oi"] = (new_df["mm_long_abs"] / oi).fillna(0.0)
        new_df["mm_short_pct_oi"] = (new_df["mm_short_abs"] / oi).fillna(0.0)
        comm_net = (new_df["prod_merc_long"] + new_df["swap_long"]) - \
                   (new_df["prod_merc_short"] + new_df["swap_short"])
        new_df["comm_net"] = comm_net
        new_df["comm_net_pct_oi"] = (comm_net / oi).fillna(0.0)
        new_df["swap_net"] = new_df["swap_long"] - new_df["swap_short"]

    # Merge with cache
    if cached is not None and not cached.empty:
        if not new_df.empty:
            combined = pd.concat([cached, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["report_date"], keep="last")
        else:
            combined = cached
    else:
        combined = new_df

    combined = combined.sort_values("report_date").reset_index(drop=True)

    # Persist cache
    if not combined.empty:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(cache_path, index=False)

    return combined


def upsample_cot_to_daily(
    cot_df: pd.DataFrame,
    daily_dates: pd.Series,
    alignment: Literal["leak_safe", "report_date"] = "leak_safe",
) -> pd.DataFrame:
    """Forward-fill weekly COT rows to daily frequency.

    alignment='leak_safe': join on known_from (Tue + 4 days = Fri/Sat next week)
    alignment='report_date': join on report_date (Tue, has 3-day lookahead)

    Returns DataFrame indexed by date with all COT columns forward-filled.
    Dates before first available COT return NaN in all numeric columns.
    """
    if cot_df is None or cot_df.empty:
        # Empty passthrough keeps downstream code simple
        dates = pd.to_datetime(pd.Series(daily_dates)).reset_index(drop=True)
        return pd.DataFrame({"date": dates})

    key_col = "known_from" if alignment == "leak_safe" else "report_date"
    if key_col not in cot_df.columns:
        raise ValueError(f"cot_df missing column '{key_col}'")

    left = pd.DataFrame({"date": pd.to_datetime(pd.Series(daily_dates)).reset_index(drop=True)})
    left = left.sort_values("date").reset_index(drop=True)

    right = cot_df.copy()
    right[key_col] = pd.to_datetime(right[key_col])
    right = right.sort_values(key_col).reset_index(drop=True)

    merged = pd.merge_asof(
        left,
        right,
        left_on="date",
        right_on=key_col,
        direction="backward",
    )
    return merged


if __name__ == "__main__":
    # Quick manual test
    start = (date.today() - timedelta(days=5 * 365)).isoformat()
    df = fetch_gold_cot(start_date=start)
    print(f"Fetched {len(df)} rows, latest report_date: {df['report_date'].max()}")
    print(df[["report_date", "known_from", "mm_net", "mm_net_pct_oi"]].tail())
