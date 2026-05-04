#!/usr/bin/env python3
"""Run leak-safe direct-model leaderboard variants for gold forecasts.

The script keeps model code untouched at runtime by temporarily changing
feature lists or router functions, then restoring them after each variant.
It is intended for fast smoke tests with a coarse stride and for more
reliable validation with stride=10.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = REPO_ROOT / "ml-service"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

import run_gold_analysis as rga  # noqa: E402
from data_collector.cot_fetcher import fetch_gold_cot, upsample_cot_to_daily  # noqa: E402
from models import multi_day_direct_predictor as mdp  # noqa: E402


COMEX_FEATURES = {"comex_overnight_return", "comex_shfe_premium"}


@dataclass(frozen=True)
class Variant:
    name: str
    description: str
    use_cot: bool = False
    drop_comex: bool = False
    zero_jump_trend_router: bool = False


VARIANTS: Dict[str, Variant] = {
    "current": Variant(
        name="current",
        description="Current direct path: COMEX/cross-market features, COT columns zero-filled.",
    ),
    "no_comex": Variant(
        name="no_comex",
        description="Disable COMEX overnight/premium features and their jump-router premium input.",
        drop_comex=True,
    ),
    "no_jump_trend_router": Variant(
        name="no_jump_trend_router",
        description="Keep features but zero jump/trend router signals.",
        zero_jump_trend_router=True,
    ),
    "with_cot": Variant(
        name="with_cot",
        description="Current direct path plus leak-safe CFTC COT features.",
        use_cot=True,
    ),
    "with_cot_no_comex": Variant(
        name="with_cot_no_comex",
        description="COT features enabled, COMEX overnight/premium disabled.",
        use_cot=True,
        drop_comex=True,
    ),
    "with_cot_no_jump_trend_router": Variant(
        name="with_cot_no_jump_trend_router",
        description="COT enabled, jump/trend router signals zeroed.",
        use_cot=True,
        zero_jump_trend_router=True,
    ),
}


@contextlib.contextmanager
def temporary_variant(variant: Variant):
    original_columns = list(mdp.DIRECT_FEATURE_COLUMNS)
    original_jump: Callable = mdp._compute_jump_signal
    original_trend: Callable = mdp._compute_trend_reversal_signal

    try:
        if variant.drop_comex:
            mdp.DIRECT_FEATURE_COLUMNS = [
                col for col in original_columns if col not in COMEX_FEATURES
            ]

        if variant.zero_jump_trend_router:
            mdp._compute_jump_signal = lambda *args, **kwargs: (0.0, 0.0)
            mdp._compute_trend_reversal_signal = lambda *args, **kwargs: (0.0, 0.0)

        yield
    finally:
        mdp.DIRECT_FEATURE_COLUMNS = original_columns
        mdp._compute_jump_signal = original_jump
        mdp._compute_trend_reversal_signal = original_trend


def _empty_comex() -> pd.DataFrame:
    return pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"), "close": pd.Series(dtype=float)})


def _load_cot_daily(
    shfe_daily: pd.DataFrame,
    *,
    skip_cot: bool,
    cot_start: str,
    cot_alignment: str,
) -> Optional[pd.DataFrame]:
    if skip_cot:
        print("  [COT] skipped by --skip-cot")
        return None

    try:
        cot_raw = fetch_gold_cot(start_date=cot_start)
        if cot_raw.empty:
            print("  [COT] unavailable: empty frame")
            return None
        cot_daily = upsample_cot_to_daily(
            cot_raw,
            shfe_daily["date"],
            alignment=cot_alignment,  # type: ignore[arg-type]
        )
        print(
            "  [COT] "
            f"weekly={len(cot_raw)}, daily={len(cot_daily)}, "
            f"latest_report={pd.Timestamp(cot_raw['report_date'].max()).date()}, "
            f"alignment={cot_alignment}"
        )
        return cot_daily
    except Exception as exc:
        print(f"  [COT] unavailable: {exc}")
        return None


def _compute_metrics(bt: pd.DataFrame) -> pd.DataFrame:
    rows: List[dict] = []
    if bt.empty:
        return pd.DataFrame(rows)

    for horizon in sorted(pd.Series(bt["horizon"]).dropna().astype(int).unique()):
        sub = bt[bt["horizon"] == horizon].copy()
        if sub.empty:
            continue

        error = sub["pred_close"].astype(float) - sub["actual_close"].astype(float)
        abs_error = error.abs()
        abs_pct = abs_error / sub["actual_close"].replace(0, np.nan).astype(float) * 100
        pred_dir = np.sign(sub["pred_close"].astype(float) - sub["origin_close"].astype(float))
        actual_dir = np.sign(sub["actual_close"].astype(float) - sub["origin_close"].astype(float))
        direction_accuracy = float((pred_dir == actual_dir).mean() * 100)

        rows.append(
            {
                "horizon": int(horizon),
                "samples": int(len(sub)),
                "mae": round(float(abs_error.mean()), 4),
                "rmse": round(float(np.sqrt(np.mean(np.square(error)))), 4),
                "mape_pct": round(float(np.nanmean(abs_pct)), 4),
                "direction_accuracy_pct": round(direction_accuracy, 2),
                "avg_confidence": round(float(sub.get("confidence", pd.Series([0])).mean()), 2),
            }
        )

    return pd.DataFrame(rows)


def _summarize_variant(variant: Variant, metrics: pd.DataFrame) -> dict:
    row = {
        "variant": variant.name,
        "description": variant.description,
        "samples": 0,
        "avg_mae": np.nan,
        "avg_mape_pct": np.nan,
        "avg_direction_accuracy_pct": np.nan,
        "t1_mae": np.nan,
        "t3_mae": np.nan,
        "t5_mae": np.nan,
    }
    if metrics.empty:
        return row

    weights = metrics["samples"].astype(float)
    row.update(
        {
            "samples": int(metrics["samples"].sum()),
            "avg_mae": round(float(np.average(metrics["mae"], weights=weights)), 4),
            "avg_mape_pct": round(float(np.average(metrics["mape_pct"], weights=weights)), 4),
            "avg_direction_accuracy_pct": round(
                float(np.average(metrics["direction_accuracy_pct"], weights=weights)), 2
            ),
        }
    )
    for horizon in (1, 3, 5):
        hrow = metrics[metrics["horizon"] == horizon]
        if not hrow.empty:
            row[f"t{horizon}_mae"] = float(hrow.iloc[0]["mae"])
    return row


def _select_variants(names: str) -> List[Variant]:
    if names.strip().lower() == "all":
        return list(VARIANTS.values())

    selected: List[Variant] = []
    for raw_name in names.split(","):
        name = raw_name.strip()
        if not name:
            continue
        if name not in VARIANTS:
            valid = ", ".join(sorted(VARIANTS))
            raise SystemExit(f"Unknown variant '{name}'. Valid variants: {valid}")
        selected.append(VARIANTS[name])
    if not selected:
        raise SystemExit("No variants selected")
    return selected


def run_leaderboard(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    print("=" * 88)
    print("  Gold Direct Model Leaderboard")
    print("=" * 88)
    print(f"  stride={args.stride}, lookback={args.lookback}, horizon={args.horizon}")

    comex = rga.fetch_comex_daily()
    usdcny = rga.fetch_usdcny_daily()
    shfe_daily = rga.fetch_shfe_au_daily()
    cross = rga.fetch_cross_market()
    cot_daily = _load_cot_daily(
        shfe_daily,
        skip_cot=args.skip_cot,
        cot_start=args.cot_start,
        cot_alignment=args.cot_alignment,
    )

    selected = _select_variants(args.variants)
    summary_rows: List[dict] = []
    horizon_frames: List[pd.DataFrame] = []

    for variant in selected:
        if variant.use_cot and cot_daily is None:
            print(f"\n[skip] {variant.name}: COT data unavailable")
            continue

        print(f"\n[run] {variant.name}")
        print(f"      {variant.description}")
        variant_comex = _empty_comex() if variant.drop_comex else comex
        variant_cot = cot_daily if variant.use_cot else None

        with temporary_variant(variant):
            bt = mdp.rolling_backtest_direct(
                daily_df=shfe_daily,
                comex_daily=variant_comex,
                usdcny_daily=usdcny,
                cross_market=cross,
                lookback=args.lookback,
                max_horizon=args.horizon,
                stride=args.stride,
                cot_daily=variant_cot,
            )

        metrics = _compute_metrics(bt)
        if metrics.empty:
            print("      no valid backtest records")
            continue

        metrics.insert(0, "variant", variant.name)
        horizon_frames.append(metrics)
        summary_rows.append(_summarize_variant(variant, metrics))
        print(metrics.to_string(index=False))

    summary = pd.DataFrame(summary_rows)
    by_horizon = pd.concat(horizon_frames, ignore_index=True) if horizon_frames else pd.DataFrame()

    if not summary.empty:
        summary = summary.sort_values(["avg_mae", "avg_mape_pct"], ascending=[True, True]).reset_index(drop=True)
    return summary, by_horizon


def write_outputs(
    summary: pd.DataFrame,
    by_horizon: pd.DataFrame,
    out_dir: Path,
    *,
    stride: int,
    horizon: int,
) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"gold_model_leaderboard_s{stride}_h{horizon}_{stamp}"
    summary_path = out_dir / f"{prefix}_summary.csv"
    horizon_path = out_dir / f"{prefix}_by_horizon.csv"
    summary.to_csv(summary_path, index=False)
    by_horizon.to_csv(horizon_path, index=False)
    return {"summary": summary_path, "by_horizon": horizon_path}


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run gold direct-model leaderboard variants.")
    parser.add_argument("--stride", type=int, default=100, help="Rolling backtest stride.")
    parser.add_argument("--lookback", type=int, default=240, help="Training lookback days.")
    parser.add_argument("--horizon", type=int, default=5, help="Max T+N horizon.")
    parser.add_argument(
        "--variants",
        default="all",
        help="Comma-separated variant names, or 'all'.",
    )
    parser.add_argument(
        "--skip-cot",
        action="store_true",
        help="Do not fetch/use COT data; COT variants will be skipped.",
    )
    parser.add_argument("--cot-start", default="2020-01-01", help="COT fetch start date.")
    parser.add_argument(
        "--cot-alignment",
        default="leak_safe",
        choices=["leak_safe", "report_date"],
        help="COT daily join alignment. Use leak_safe for real backtests.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / "analysis_outputs" / "model_leaderboard"),
        help="Directory for leaderboard CSV outputs.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    summary, by_horizon = run_leaderboard(args)

    print("\n" + "=" * 88)
    print("  Leaderboard Summary")
    print("=" * 88)
    if summary.empty:
        print("  No leaderboard results.")
        return 1

    display_cols = [
        "variant",
        "samples",
        "avg_mae",
        "avg_mape_pct",
        "avg_direction_accuracy_pct",
        "t1_mae",
        "t3_mae",
        "t5_mae",
    ]
    print(summary[display_cols].to_string(index=False))

    outputs = write_outputs(
        summary,
        by_horizon,
        Path(args.out_dir),
        stride=args.stride,
        horizon=args.horizon,
    )
    print("\n  Outputs:")
    print(f"    summary:    {outputs['summary']}")
    print(f"    by_horizon: {outputs['by_horizon']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
