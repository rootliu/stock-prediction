"""Replay archived points; optionally reconstruct one new target using frozen origin inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from bench_versions import add_version_predictions, load_predictions
from models import gold_shadow as shadow


def replay(archive, data, out, next_label=None):
    digests = dict(line.split()[::-1] for line in (archive / "inputs.sha256").read_text().splitlines())
    def frozen(name):
        path = data / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digests[name]:
            raise ValueError(f"snapshot mismatch: {name}")
        return pd.read_csv(path, parse_dates=["date"])
    daily, comex = frozen("shfe.csv"), frozen("comex.csv")
    points = add_version_predictions(load_predictions(archive / "full.csv"))
    dates = sorted(points.target_date.unique())[-5:]
    out.mkdir(exist_ok=True, parents=True)
    if next_label:
        from run_gold_continuation_backtest import _build_records
        from models.gold_feed import target_after
        date, close = pd.Timestamp(next_label[0]), float(next_label[1])
        if str(date.date()) != target_after(daily.date.max(), 1) or not (0 < close < float("inf")):
            raise ValueError("expected the next completed SHFE session and a valid close")
        # Last row is a label only. Every model origin is strictly before it.
        labeled = pd.concat([daily, pd.DataFrame([{"date": date, "close": close}])], ignore_index=True)
        new = _build_records(labeled, comex, frozen("fx.csv"), frozen("cross.csv"), daily.date.max(), 240, 10)
        path = out / "next_target.csv"
        new.to_csv(path, index=False)
        points = pd.concat([points, add_version_predictions(load_predictions(path))], ignore_index=True)
    points = points[points.origin_date > shadow.FROZEN]
    cal = json.loads(shadow.CAL.read_bytes())["versions"]
    signals = {o: shadow.features(daily, comex, o) for o in pd.DatetimeIndex(points.origin_date.unique())}
    records = []
    for v in ("v1", "v7"):
        history = points.assign(residual=points.actual_close - points["pred_" + v])
        for r in history.itertuples():
            inputs = signals[r.origin_date]
            row = shadow.interval(cal[v], r.origin_date, r.horizon, getattr(r, "pred_" + v), inputs, history)
            records.append(dict(version=v, origin_date=r.origin_date, target_date=r.target_date,
                                actual=r.actual_close, **inputs, **row))
    rows = pd.DataFrame(records)
    scores = []
    original = rows[rows.target_date <= dates[-1]]
    windows = [("all", original), ("last5", original[original.target_date.isin(dates)]),
               ("range_ratio_le_1", original[original.range_ratio <= 1])]
    if next_label:
        windows.append(("next_target", rows[rows.target_date == date]))
    for window, values in windows:
        for (v, h), g in values.groupby(["version", "horizon"]):
            for mode in ("fixed", "shadow"):
                lo, hi = g[mode + "_low"], g[mode + "_high"]
                below, above = (lo - g.actual).clip(lower=0), (g.actual - hi).clip(lower=0)
                hits = ((below == 0) & (above == 0)).sum()
                scores.append(dict(window=window, version=v, horizon=h, mode=mode, n=len(g),
                                   hits=hits, below=(below > 0).sum(), above=(above > 0).sum(),
                                   mean_width=(hi-lo).mean(), score80=(hi-lo+10*(below+above)).mean()))
    rows.to_csv(out / "shadow_rows.csv", index=False)
    pd.DataFrame(scores).to_csv(out / "shadow_scores.csv", index=False, float_format="%.3f")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("data", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--next-label", nargs=2, metavar=("SESSION", "SHFE_CLOSE"))
    args = parser.parse_args()
    replay(args.archive, args.data, args.out, args.next_label)
