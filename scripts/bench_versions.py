#!/usr/bin/env python3
"""Benchmark the gold forecast versions on one fixed predictions table.

Input: a CSV produced by a model run (or by `--from-snapshot` for the repo's
frozen snapshot). Every version is evaluated on exactly the same rows, so the
leaderboard is a like-for-like comparison.

Outputs (in --out-dir):
  leaderboard.csv   one row per (version, horizon)
  leaderboard.md    human-readable table + selection verdict
  calibration.json  residual quantiles per (version, horizon) for the daily job

This compares POST-PROCESSING versions (shrinkage of the model return) on a
fixed predictions table and never retrains. For model/feature ablations that do
retrain, use scripts/run_gold_model_leaderboard.py instead.

Usage:
  python scripts/bench_versions.py --predictions report/review_20260913/local_predictions.csv
  python scripts/bench_versions.py --from-snapshot          # uses the frozen snapshot
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-service"))

from models.versions import VERSIONS, predict_close  # noqa: E402

SNAPSHOT_PREDICTIONS = ROOT / "report/review_20260913/local_predictions.csv"
HORIZONS = (1, 3, 5, 10)
BOOTSTRAP_REPS = 1000


def wilson_interval(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def load_predictions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["origin_date", "target_date"])
    required = {"origin_date", "target_date", "horizon", "origin_close", "actual_close", "pred_close"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"{path} is missing columns: {sorted(missing)}")
    from gold_daily import validate_predictions
    df = validate_predictions(df)
    if df["actual_close"].isna().any():
        raise ValueError("benchmark requires matured actual_close for every row")
    df["model_return"] = df["pred_close"] / df["origin_close"] - 1.0
    return df.sort_values(["horizon", "origin_date"]).reset_index(drop=True)


def add_version_predictions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for name in VERSIONS:
        out[f"pred_{name}"] = [
            predict_close(name, r.origin_close, r.model_return, r.horizon)
            for r in out.itertuples()
        ]
    return out


def evaluate(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for horizon, group in df.groupby("horizon"):
        # Select intervals before looking at returns or correctness.
        independent = []
        last_target = None
        for idx, row in group.sort_values("origin_date").iterrows():
            if last_target is None or row.origin_date >= last_target:
                independent.append(idx)
                last_target = row.target_date
        thin = group.loc[independent]
        base = group["actual_close"]
        base_mae = float((base - group["pred_v0"]).abs().mean())
        for name in VERSIONS:
            pred = group[f"pred_{name}"]
            err = pred - base
            mae = float(err.abs().mean())
            rmse = float(np.sqrt((err ** 2).mean()))
            signed_hits = int(
                (np.sign(pred - group["origin_close"]) == np.sign(base - group["origin_close"])).sum()
            )
            lo, hi = wilson_interval(signed_hits, len(group))
            independent_hits = int((np.sign(thin[f"pred_{name}"] - thin["origin_close"]) ==
                                    np.sign(thin["actual_close"] - thin["origin_close"])).sum())
            independent_lo, independent_hi = wilson_interval(independent_hits, len(thin))
            rows.append(
                {
                    "version": name,
                    "horizon": int(horizon),
                    "n": len(group),
                    "mae": round(mae, 4),
                    "rmse": round(rmse, 4),
                    "baseline_mae": round(base_mae, 4),
                    "skill": round(1 - mae / base_mae, 4) if base_mae else 0.0,
                    "direction_accuracy": round(100 * signed_hits / len(group), 2),
                    "direction_ci_low": round(100 * lo, 2),
                    "direction_ci_high": round(100 * hi, 2),
                    "nonoverlap_n": len(thin),
                    "nonoverlap_direction_accuracy": round(100 * independent_hits / len(thin), 2),
                    "nonoverlap_direction_ci_low": round(100 * independent_lo, 2),
                    "nonoverlap_direction_ci_high": round(100 * independent_hi, 2),
                }
            )
    return pd.DataFrame(rows)


def bootstrap_skill(df: pd.DataFrame, version: str) -> Dict[str, float]:
    """Block bootstrap over origins (not rows) to respect overlap."""
    origins = df["origin_date"].unique()
    if len(origins) < 5:
        return {"ci_low": float("nan"), "ci_high": float("nan"), "reps": 0}
    rng = np.random.default_rng(20261102)
    by_origin = {o: g for o, g in df.groupby("origin_date")}
    diffs = []
    for _ in range(BOOTSTRAP_REPS):
        sample = rng.choice(origins, size=len(origins), replace=True)
        picked = pd.concat([by_origin[o] for o in sample], ignore_index=True)
        base_mae = (picked["actual_close"] - picked["pred_v0"]).abs().mean()
        model_mae = (picked["actual_close"] - picked[f"pred_{version}"]).abs().mean()
        if base_mae:
            diffs.append(1 - model_mae / base_mae)
    return {
        "ci_low": round(float(np.percentile(diffs, 2.5)), 4),
        "ci_high": round(float(np.percentile(diffs, 97.5)), 4),
        "reps": len(diffs),
    }


def walk_forward_intervals(df: pd.DataFrame, quantile: float = 0.80) -> pd.DataFrame:
    """Causal residual quantiles: only matured rows before each origin are used."""
    out = []
    for horizon, group in df.groupby("horizon"):
        group = group.sort_values("origin_date").reset_index(drop=True)
        origin = group["origin_date"].values
        target = group["target_date"].values
        actual = group["actual_close"].values
        for name in VERSIONS:
            pred = group[f"pred_{name}"].values
            lo = np.full(len(group), np.nan)
            hi = np.full(len(group), np.nan)
            for i in range(len(group)):
                prior = [j for j in range(i) if target[j] <= origin[i]]
                if len(prior) < 10:
                    continue
                resid = actual[prior] - pred[prior]
                lo[i] = pred[i] + np.quantile(resid, (1 - quantile) / 2)
                hi[i] = pred[i] + np.quantile(resid, 1 - (1 - quantile) / 2)
            mask = ~np.isnan(lo)
            covered = ((actual[mask] >= lo[mask]) & (actual[mask] <= hi[mask])).mean() if mask.any() else float("nan")
            out.append(
                {
                    "version": name,
                    "horizon": int(horizon),
                    "interval_n": int(mask.sum()),
                    "coverage": round(float(covered), 4),
                    "width": round(float((hi - lo)[mask].mean()), 2) if mask.any() else float("nan"),
                }
            )
    return pd.DataFrame(out)


def build_calibration(df: pd.DataFrame, quantile: float = 0.80) -> Dict[str, object]:
    """Full-sample residual quantiles per (version, horizon) for the daily job."""
    cal: Dict[str, object] = {"quantile": quantile, "versions": {}}
    for name in VERSIONS:
        per_h = {}
        for horizon, group in df.groupby("horizon"):
            resid = group["actual_close"] - group[f"pred_{name}"]
            per_h[str(int(horizon))] = {
                "q_low": round(float(resid.quantile((1 - quantile) / 2)), 2),
                "q_high": round(float(resid.quantile(1 - (1 - quantile) / 2)), 2),
                "n": int(len(resid)),
            }
        cal["versions"][name] = per_h
    return cal


def select_champion(merged: pd.DataFrame, band: float = -0.02) -> Dict[str, object]:
    """Pre-registered rule.

    The product ships a point + interval, not a direction call, so direction
    accuracy is a disclosure, never a gate (shrinkage keeps the model's sign and
    would inherit its direction record unchanged).

    Gates:
      G1  n >= 40 per horizon
      G2  walk-forward 80% coverage in [0.72, 0.88] for T+1 and T+3
      G3  mean skill over T+1..T+5 >= band (default -0.02: "not materially worse")
    Rank eligible versions by mean skill; v0 is the fallback champion.
    """
    notes: List[str] = []
    mean_skill = merged[merged["horizon"].isin([1, 3, 5])].groupby("version")["skill"].mean()
    eligible: List[str] = []

    for name in VERSIONS:
        if name == "v0" or name not in mean_skill.index:
            continue
        rows = merged[merged["version"] == name]
        short = rows[rows["horizon"].isin([1, 3])]
        reasons = []
        if not set(HORIZONS).issubset(set(rows["horizon"])) or rows["horizon"].duplicated().any():
            reasons.append("missing or duplicate required horizons")
        if not np.isfinite(rows[["n", "skill"]].to_numpy(dtype=float)).all():
            reasons.append("non-finite sample count or skill")
        if rows["n"].min() < 40:
            reasons.append(f"n={int(rows['n'].min())} < 40")
        cov = short["coverage"].dropna()
        if set(short.loc[short["coverage"].notna(), "horizon"]) != {1, 3}:
            reasons.append("missing coverage at T+1/T+3")
        if len(cov) and ((cov < 0.72) | (cov > 0.88)).any():
            reasons.append("coverage outside 0.72-0.88 at T+1/T+3")
        if mean_skill[name] < band:
            reasons.append(f"mean skill {mean_skill[name]:+.3f} < {band:+.2f}")
        if reasons:
            notes.append(f"{name}: rejected — " + "; ".join(reasons))
        else:
            eligible.append(name)
            notes.append(f"{name}: eligible (mean skill {mean_skill[name]:+.3f})")

    if not eligible:
        notes.append("no model version cleared the gates -> champion = v0 (persistence)")
        return {"champion": "v0", "reason": "no_eligible_model", "directional_edge": False, "notes": notes}

    best = max(eligible, key=lambda n: mean_skill[n])
    verdict = {
        "champion": best,
        "reason": "least_worse_informative_model",
        "mean_skill": round(float(mean_skill[best]), 4),
        "baseline_delta_pct": round(float(mean_skill[best]) * 100, 2),
        "notes": notes,
    }

    # Direction is disclosed, not gated.
    champ = merged[merged["version"] == best]
    evidence_cols = ["nonoverlap_n", "nonoverlap_direction_ci_low"]
    evidence = champ.reindex(columns=evidence_cols)
    verdict["directional_edge"] = bool(
        np.isfinite(evidence.to_numpy(dtype=float)).all()
        and (evidence["nonoverlap_n"] >= 30).all()
        and (evidence["nonoverlap_direction_ci_low"] > 50).all()
    )
    if not verdict["directional_edge"]:
        notes.append(f"{best}: insufficient non-overlapping direction evidence; do not claim an edge")

    notes.append(f"{best}: descriptive T+1/T+3/T+5 mean skill {mean_skill[best]:+.3f}; "
                 "selection on this evaluation set is not independent validation")
    if mean_skill[best] <= 0:
        notes.append("not better than a flat forecast; allowed only by the configured tolerance")
    return verdict


def to_markdown(board: pd.DataFrame, intervals: pd.DataFrame, verdict: Dict[str, object]) -> str:
    merged = board.merge(intervals, on=["version", "horizon"], how="left")
    pivot_skill = merged.pivot(index="version", columns="horizon", values="skill")
    pivot_mae = merged.pivot(index="version", columns="horizon", values="mae")
    pivot_cov = merged.pivot(index="version", columns="horizon", values="coverage")
    for table in (pivot_skill, pivot_mae, pivot_cov):
        table.columns = [f"T+{c}" for c in table.columns]

    lines = ["# Gold version leaderboard", ""]
    lines += [
        f"- rows: {len(board)} (per version/horizon)",
        f"- champion: **{verdict['champion']}** ({verdict['reason']})",
    ]
    if "mean_skill" in verdict:
        lines.append(f"- champion mean skill: {verdict['mean_skill']:+.4f}")
    if "directional_edge" in verdict:
        lines.append(f"- directional edge: {verdict['directional_edge']}")
    lines.append("")
    lines += ["## Skill (1 - MAE / persistence MAE)", "", pivot_skill.round(3).to_markdown(), ""]
    lines += ["## MAE (CNY/g)", "", pivot_mae.round(2).to_markdown(), ""]
    lines += ["## 80% interval coverage (walk-forward, causal)", "", pivot_cov.round(3).to_markdown(), ""]
    direction = board[["version", "horizon", "n", "direction_accuracy", "nonoverlap_n",
                       "nonoverlap_direction_accuracy", "nonoverlap_direction_ci_low",
                       "nonoverlap_direction_ci_high"]]
    lines += ["## Direction audit", "", direction.to_markdown(index=False), "",
              "Non-overlapping intervals are selected separately per horizon before scoring. "
              "They reduce overlap, not all market dependence; CI is 95% Wilson. "
              "Fewer than 30 selected samples cannot support a direction-edge claim.", ""]
    lines += ["## Decision", ""] + [f"- {n}" for n in verdict["notes"]] + [""]
    lines += [
        "Selection requires all T+1/3/5/10 horizons, n >= 40, and T+1/3 coverage in [0.72, 0.88].",
        "Rank by mean skill at T+1/3/5; default tolerance is -0.02. Negative skill is not an edge.",
        "Direction is disclosed, not a promotion gate. Overlapping-row Wilson intervals are descriptive only.",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, help="CSV with model predictions")
    parser.add_argument("--from-snapshot", action="store_true", help="use the frozen repo snapshot")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "config/gold_versions")
    parser.add_argument("--quantile", type=float, default=0.80, help="interval nominal coverage")
    args = parser.parse_args()

    path = args.predictions or SNAPSHOT_PREDICTIONS
    if not path.exists():
        raise SystemExit(f"predictions not found: {path}")

    df = load_predictions(path)
    df = add_version_predictions(df)
    board = evaluate(df)
    intervals = walk_forward_intervals(df, args.quantile)
    merged = board.merge(intervals, on=["version", "horizon"], how="left")
    verdict = select_champion(merged)
    calibration = build_calibration(df, args.quantile)

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out / "leaderboard.csv", index=False)
    (out / "leaderboard.md").write_text(to_markdown(board, intervals, verdict), encoding="utf-8")
    (out / "calibration.json").write_text(json.dumps(calibration, indent=2), encoding="utf-8")

    print(f"rows={len(df)}  origins={df.origin_date.nunique()}  horizons={sorted(df.horizon.unique())}")
    print(board.pivot(index="version", columns="horizon", values="skill").round(3).to_string())
    print()
    print(f"champion: {verdict['champion']} ({verdict['reason']})")
    for note in verdict["notes"]:
        print(f"  - {note}")
    print(f"\nwrote {out}/leaderboard.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
