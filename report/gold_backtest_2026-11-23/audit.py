"""Reproduce the November audit from frozen inputs or saved prediction rows."""
import argparse
from hashlib import sha256
from pathlib import Path
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bench_versions as bench
import evaluate_direction_confidence as confidence
from gold_daily import interval_for, load_calibration
import run_gold_continuation_backtest as continuation

CAL = ROOT / "config/gold_versions/calibration.json"
CUTOFF = pd.Timestamp("2026-11-02")
LAST = pd.Timestamp("2026-11-20")


def inputs(folder):
    result = {}
    for line in (HERE / "inputs.sha256").read_text().splitlines():
        digest, name = line.split()
        path = folder / name
        if sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Snapshot hash mismatch: {name}")
        df = pd.read_csv(path, parse_dates=["date"])
        if not df.date.is_unique or not df.date.is_monotonic_increasing or df.date.max() != LAST:
            raise ValueError(f"Invalid trading dates: {name}")
        result[path.stem] = df
    return [result[key] for key in ("shfe", "comex", "fx", "cross")]


def audit(folder, retrain, out):
    frames = inputs(folder)
    if retrain:
        for name in ("full", "domestic"):
            external = frames[1:] if name == "full" else [f.iloc[:0] for f in frames[1:]]
            df = continuation._build_records(frames[0], *external, CUTOFF, 240, 10)
            df.to_csv(out / f"{name}.csv", index=False)
    base = out if retrain else HERE
    f = bench.add_version_predictions(bench.load_predictions(base / "full.csv"))
    d = bench.load_predictions(base / "domestic.csv")
    keys = ["origin_date", "target_date", "horizon"]
    f = f.merge(d[keys + ["pred_close", "actual_close"]], on=keys, validate="one_to_one",
                suffixes=("", "_dom"), how="outer", indicator=True)
    if not (f._merge.eq("both").all() and f.actual_close.eq(f.actual_close_dom).all()
            and f.groupby("horizon").size().tolist() == [14] * 10):
        raise ValueError("Unmatched evaluation rows")
    spot = frames[0].set_index("date")
    f["momentum_sign"] = f.origin_date.map(np.sign(spot.close.diff(3)))
    f["actual_sign"] = np.sign(f.actual_delta)
    cal = load_calibration(CAL, "v7")
    bounds = [interval_for(cal, r.horizon, r.pred_v7) for r in f.itertuples()]
    f["lo"], f["hi"] = zip(*bounds)
    f["covered"] = f.actual_close.between(f.lo, f.hi)
    rows = []
    metrics = []
    for name, group in (("all", f), ("last5", f[f.target_date >= "2026-11-16"])):
        metrics.append(confidence.evaluate(group)[0].assign(period=name))
        for h, g in group.groupby("horizon"):
            # The committed intervals were available after Nov 2, not in October.
            eligible = g[g.origin_date > CUTOFF]
            rows.append(dict(period=name, horizon=h, n=len(g), hits=int(g.dir_match.sum()),
                             momentum_hits=int(g.momentum_sign.eq(g.actual_sign).sum()),
                             down_actual=int(g.actual_sign.lt(0).sum()),
                             down_pred=int(g.pred_delta.lt(0).sum()),
                             v0_mae=g.actual_delta.abs().mean(), v1_mae=g.abs_error.mean(),
                             v7_mae=(g.pred_v7 - g.actual_close).abs().mean(),
                             domestic_mae=(g.pred_close_dom - g.actual_close).abs().mean(),
                             v1_mape=g.ape_pct.mean(), interval_n=len(eligible),
                             interval_hits=int(eligible.covered.sum())))
    pd.DataFrame(rows).round(5).to_csv(out / "by_horizon.csv", index=False)
    pd.concat(metrics, ignore_index=True).to_csv(out / "probabilities.csv", index=False)
    bench.evaluate(f).query("version == 'v1'").to_csv(out / "direction_audit.csv", index=False)
    t1 = f[f.horizon == 1].sort_values("target_date")
    t1.loc[t1.origin_date <= CUTOFF, ["lo", "hi"]] = np.nan
    t1[keys + ["origin_close", "actual_close", "pred_v1", "pred_v7", "lo", "hi", "regime",
               "confidence", "direction_signal"]].round(2).to_csv(out / "t1_daily.csv", index=False)
    daily = pd.DataFrame({"abs_return_pct": spot.close.pct_change().abs() * 100,
                          "range_pct": (spot.high - spot.low) / spot.close.shift() * 100,
                          "log_return": np.log(spot.close).diff()}).tail(25)
    vol = []
    for name, w in [("prior20", daily.iloc[:20]), ("last5", daily.iloc[20:])]:
        vol.append(dict(period=name, start=w.index.min().date(), end=w.index.max().date(),
                        n=len(w), abs_return_pct=w.abs_return_pct.mean(), range_pct=w.range_pct.mean(),
                        ann_vol_pct=w.log_return.std() * np.sqrt(252) * 100,
                        cumulative_return_pct=np.expm1(w.log_return.sum()) * 100))
    pd.DataFrame(vol).round(5).to_csv(out / "volatility.csv", index=False)
    fig, (a, b) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, height_ratios=[2, 1])
    shown = t1[t1.origin_date > CUTOFF]
    a.fill_between(shown.target_date, shown.lo, shown.hi, color="#c8ddd5", alpha=.6,
                   label="Frozen v7 80% interval")
    for col, label, color in [("actual_close", "Actual close", "#172d48"),
                              ("pred_v1", "Direct (v1)", "#b45309"),
                              ("pred_v7", "Shrunk (v7)", "#13786c")]:
        a.plot(t1.target_date, t1[col], ".-", color=color, label=label)
    a.set(ylabel="CNY / gram", title="SHFE AU0 | One-session-ahead forecasts by target date")
    a.legend(ncol=2, fontsize=9)
    b.bar(t1.target_date, daily.range_pct.reindex(t1.target_date), color="#5d8099")
    b.axhline(vol[0]["range_pct"], color="#953a34", ls="--", label="Oct 19 - Nov 13 mean")
    b.set(ylabel="Intraday range (%)", xlabel="Target trading date (2026)")
    b.legend(fontsize=9)
    b.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    fig.tight_layout()
    fig.savefig(out / "diagnostics.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("--retrain", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    audit(args.data, args.retrain, args.output)
