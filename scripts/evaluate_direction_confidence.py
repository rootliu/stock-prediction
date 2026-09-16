"""Evaluate exported continuation probabilities without retraining/tuning."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm


def direction_audit(frame):
    """Disjoint target intervals per horizon; horizons still share market risk."""
    rows = []
    for horizon, group in frame.groupby("horizon"):
        selected = []
        last_target = None
        for index, row in group.sort_values("origin_date").iterrows():
            origin, target = pd.Timestamp(row.origin_date), pd.Timestamp(row.target_date)
            if target <= origin:
                raise ValueError("Target must follow origin")
            if last_target is None or origin >= last_target:
                selected.append(index)
                last_target = target
        subset = frame.loc[selected]
        for direction, mask in [("all", pd.Series(True, index=subset.index)),
                                ("up", subset.pred_delta > .5),
                                ("down", subset.pred_delta < -.5),
                                ("flat", subset.pred_delta.abs() <= .5)]:
            for threshold in (0, 50, 60, 70):
                signals = subset[mask & (subset.confidence >= threshold)]
                n = len(signals)
                accuracy = signals.direction_match_3class.mean() if n else np.nan
                z = norm.ppf(.95)
                center = (accuracy + z*z/(2*n)) / (1+z*z/n) if n else np.nan
                half = z*np.sqrt(accuracy*(1-accuracy)/n+z*z/(4*n*n))/(1+z*z/n) if n else np.nan
                rows.append(dict(horizon=int(horizon), direction=direction, threshold=threshold,
                                 n=n, available_n=len(subset), coverage=n/len(subset),
                                 accuracy=accuracy, accuracy_low=center-half, accuracy_high=center+half,
                                 mean_confidence=signals.confidence.mean()/100,
                                 status="insufficient_evidence" if n < 30 else "retrospective_only"))
    return pd.DataFrame(rows)


def evaluate(frame):
    probability_columns = ["down_probability", "flat_probability", "up_probability"]
    probabilities = frame[probability_columns].to_numpy(dtype=float)
    if (not np.isfinite(probabilities).all() or (probabilities < 0).any()
            or (probabilities > 1).any() or not np.allclose(probabilities.sum(axis=1), 1)):
        raise ValueError("Invalid or incomplete directional probability rows")
    if "confidence_method" in frame and frame.confidence_method.eq("legacy_score_not_probability").any():
        raise ValueError("Legacy scores are not probabilities; do not evaluate them as confidence")
    rows = []
    for name, subset in [("all", frame), ("T+1~3", frame[frame.horizon <= 3]),
                         ("T+5~10", frame[frame.horizon >= 5])]:
        if subset.empty:
            continue
        actual_up = (subset.actual_delta > 0.5).astype(float)
        actual_down = (subset.actual_delta < -0.5).astype(float)
        actual_flat = 1 - actual_up - actual_down
        probs = subset[["down_probability", "flat_probability", "up_probability"]].to_numpy()
        truth = np.column_stack([actual_down, actual_flat, actual_up])
        confidence = subset.confidence / 100
        correct = subset.direction_match_3class.astype(float)
        supported = subset.direction_signal == "supported"
        raw = subset.calibration_raw_up
        # Binary diagnostic uses >0 (the raw classifier's training target).
        binary_truth = (subset.actual_delta > 0).astype(float)
        rows.append({
            "window": name, "n": len(subset),
            "direction_accuracy_pct": round(correct.mean() * 100, 2),
            "mean_confidence_pct": round(confidence.mean() * 100, 2),
            "multiclass_brier": round(np.mean(np.sum((probs - truth) ** 2, axis=1)), 4),
            "symmetric_prior_brier": round(np.mean(np.sum((np.array([.475, .05, .475]) - truth) ** 2, axis=1)), 4),
            "raw_binary_brier": round(np.mean((raw - binary_truth) ** 2), 4),
            "raw_multiclass_brier": round(np.mean(np.sum((np.column_stack([1 - raw, np.zeros(len(raw)), raw]) - truth) ** 2, axis=1)), 4),
            "supported_n": int(supported.sum()),
            "supported_accuracy_pct": round(correct[supported].mean() * 100, 2) if supported.any() else None,
        })
    reliability = frame.assign(confidence_bin=pd.cut(frame.confidence, [0, 20, 40, 60, 80, 100], include_lowest=True))
    reliability = reliability.groupby("confidence_bin", observed=True).agg(
        n=("confidence", "size"), mean_confidence_pct=("confidence", "mean"),
        accuracy=("direction_match_3class", "mean"),
    ).reset_index()
    return pd.DataFrame(rows), reliability


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    frame = pd.read_csv(args.csv)
    summary, reliability = evaluate(frame)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output / "confidence_metrics.csv", index=False)
    reliability.to_csv(output / "confidence_reliability.csv", index=False)
    direction_audit(frame).to_csv(output / "direction_threshold_audit.csv", index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot([0, 100], [0, 100], "--", color="gray", label="Perfect calibration")
    ax.plot(reliability.mean_confidence_pct, reliability.accuracy * 100, "o-", label="Observed (correlated samples)")
    for row in reliability.itertuples():
        ax.annotate(f"n={row.n}", (row.mean_confidence_pct, row.accuracy * 100), xytext=(5, 5), textcoords="offset points")
    ax.set(xlim=(0, 100), ylim=(0, 105), xlabel="Estimated direction probability (%)",
           ylabel="Observed 3-class accuracy (%)", title="Experimental direction reliability")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "confidence_reliability.png", dpi=150)
    plt.close(fig)
    print(summary.to_string(index=False))
    print(reliability.to_string(index=False))
