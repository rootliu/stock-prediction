"""
Multi-bar gold price predictor.

Trains per-checkpoint GBM models, each targeting the same-day or next-day
16:00 close. Aggregates predictions via time-decay weighted averaging with
volatility regime dampening.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

from models.multi_bar_features import (
    CHECKPOINTS,
    CHECKPOINT_TARGET_OFFSET,
    HOURS_TO_TARGET,
    all_feature_columns,
    build_checkpoint_features,
    build_training_dataset,
    _filter_bars_for_checkpoint,
)
from models.volatility_regime import (
    classify_regime,
    compute_regime_info,
    dampen_prediction,
    get_direction_threshold,
    realized_volatility,
)

# ---------------------------------------------------------------------------
# Per-checkpoint model
# ---------------------------------------------------------------------------

BASE_WEIGHTS: Dict[str, float] = {
    "04:00": 0.05,
    "09:00": 0.10,
    "12:00": 0.20,
    "16:00": 0.35,
    "20:00": 0.15,
    "24:00": 0.15,
}


def _build_gbm_pair() -> Tuple[GradientBoostingRegressor, GradientBoostingClassifier]:
    reg = GradientBoostingRegressor(
        n_estimators=250,
        learning_rate=0.03,
        max_depth=3,
        min_samples_leaf=8,
        subsample=0.85,
        random_state=42,
    )
    cls = GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.04,
        max_depth=2,
        subsample=0.85,
        random_state=42,
    )
    return reg, cls


def train_checkpoint_model(
    X: pd.DataFrame,
    y_return: pd.Series,
    y_direction: pd.Series,
) -> Dict[str, Any]:
    """Train regressor + classifier for one checkpoint."""
    if len(X) < 40:
        return {"trained": False, "reason": f"insufficient data ({len(X)} < 40)"}

    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_ret_train, y_ret_test = y_return.iloc[:split], y_return.iloc[split:]
    y_dir_train, y_dir_test = y_direction.iloc[:split], y_direction.iloc[split:]

    reg, cls = _build_gbm_pair()
    reg.fit(X_train, y_ret_train)

    has_cls = y_dir_train.nunique() > 1
    if has_cls:
        cls.fit(X_train, y_dir_train)
    else:
        cls = None

    # Evaluate on test set
    metrics = _evaluate(reg, cls, X_test, y_ret_test, y_dir_test)
    metrics["train_size"] = len(X_train)
    metrics["test_size"] = len(X_test)

    return {
        "trained": True,
        "reg_model": reg,
        "cls_model": cls,
        "metrics": metrics,
    }


def _evaluate(
    reg: GradientBoostingRegressor,
    cls: Optional[GradientBoostingClassifier],
    X_test: pd.DataFrame,
    y_ret_test: pd.Series,
    y_dir_test: pd.Series,
) -> Dict[str, Any]:
    if len(X_test) == 0:
        return {"mae_pct": None, "mape_pct": None, "direction_accuracy": None}

    pred_ret = reg.predict(X_test)
    errors = np.abs(pred_ret - y_ret_test.values) * 100  # as percentage
    mae_pct = float(errors.mean())
    mape_arr = errors / np.maximum(np.abs(y_ret_test.values) * 100, 0.01)
    mape_pct = float(np.nanmean(mape_arr))

    # Direction accuracy from regression sign
    pred_dir = (pred_ret > 0).astype(int)
    dir_acc = float(np.mean(pred_dir == y_dir_test.values) * 100)

    # Direction accuracy from classifier
    cls_dir_acc = None
    if cls is not None:
        cls_pred = cls.predict(X_test)
        cls_dir_acc = float(np.mean(cls_pred == y_dir_test.values) * 100)

    return {
        "mae_pct": round(mae_pct, 4),
        "mape_pct": round(mape_pct, 4),
        "direction_accuracy": round(dir_acc, 1),
        "cls_direction_accuracy": round(cls_dir_acc, 1) if cls_dir_acc is not None else None,
    }


# ---------------------------------------------------------------------------
# Prediction for a single checkpoint
# ---------------------------------------------------------------------------

def predict_single_checkpoint(
    model_info: Dict[str, Any],
    features: Dict[str, float],
    effective_base: float,
    vol_5: float,
) -> Dict[str, Any]:
    """Run prediction for one checkpoint model."""
    if not model_info.get("trained", False):
        return {"valid": False, "reason": model_info.get("reason", "not trained")}

    reg = model_info["reg_model"]
    cls = model_info["cls_model"]
    feature_cols = all_feature_columns()

    x_row = pd.DataFrame(
        [[features.get(col, 0.0) for col in feature_cols]],
        columns=feature_cols,
    )

    pred_return = float(reg.predict(x_row)[0])

    # Clip return to reasonable range
    base_vol = max(vol_5, 0.005)
    cap = max(0.012, min(0.03, 2.5 * base_vol))
    pred_return = float(np.clip(pred_return, -cap, cap))

    up_prob = None
    if cls is not None:
        probs = cls.predict_proba(x_row)[0]
        up_prob = float(probs[1]) if len(probs) > 1 else None

    pred_close = effective_base * (1 + pred_return)

    return {
        "valid": True,
        "pred_close": pred_close,
        "pred_return": pred_return,
        "up_probability": up_prob,
        "effective_base": effective_base,
    }


# ---------------------------------------------------------------------------
# Multi-checkpoint aggregation
# ---------------------------------------------------------------------------

def aggregate_checkpoint_predictions(
    checkpoint_results: Dict[str, Dict[str, Any]],
    regime: str,
    prev_close_16: float,
) -> Dict[str, Any]:
    """
    Weighted aggregation of per-checkpoint predictions.

    Weights are adjusted by:
    1. Base time-proximity weights
    2. Model confidence
    3. Direction agreement bonus
    """
    valid_results = {
        cp: r for cp, r in checkpoint_results.items()
        if r.get("valid", False)
    }

    if not valid_results:
        return {
            "close": prev_close_16,
            "direction": "平",
            "confidence": 0.0,
            "range_low": prev_close_16,
            "range_high": prev_close_16,
            "checkpoint_details": {},
            "regime": regime,
            "n_checkpoints": 0,
        }

    # Step 1: Compute raw weights
    weights: Dict[str, float] = {}
    for cp, r in valid_results.items():
        base_w = BASE_WEIGHTS.get(cp, 0.1)
        # Adjust by classifier confidence if available
        up_prob = r.get("up_probability")
        if up_prob is not None:
            conf_boost = abs(up_prob - 0.5) * 2.0  # 0~1
            base_w *= (0.7 + 0.3 * conf_boost)
        weights[cp] = base_w

    # Step 2: Direction agreement bonus
    directions = {cp: np.sign(r["pred_close"] - prev_close_16) for cp, r in valid_results.items()}
    direction_counts = {-1: 0, 0: 0, 1: 0}
    for d in directions.values():
        direction_counts[d] = direction_counts.get(d, 0) + 1
    majority_dir = max(direction_counts, key=direction_counts.get)

    for cp in weights:
        if directions[cp] == majority_dir and majority_dir != 0:
            weights[cp] *= 1.15  # 15% bonus for agreeing with majority

    # Normalize weights
    w_total = sum(weights.values())
    if w_total > 0:
        weights = {cp: w / w_total for cp, w in weights.items()}

    # Step 3: Weighted average close
    raw_close = sum(weights[cp] * valid_results[cp]["pred_close"] for cp in valid_results)

    # Step 4: Apply volatility regime dampening
    final_close = dampen_prediction(raw_close, prev_close_16, regime)

    # Step 5: Compute direction + confidence
    change = final_close - prev_close_16
    direction = "涨" if change > 0.5 else ("跌" if change < -0.5 else "平")

    # Confidence from multiple signals
    up_probs = [
        r["up_probability"] for r in valid_results.values()
        if r.get("up_probability") is not None
    ]
    n_up = sum(1 for d in directions.values() if d > 0)
    n_total = len(directions)
    vote_agreement = max(n_up, n_total - n_up) / n_total if n_total > 0 else 0.5

    if up_probs:
        avg_prob = np.mean(up_probs)
        prob_confidence = abs(avg_prob - 0.5) * 2.0
        confidence = 0.4 * vote_agreement + 0.6 * prob_confidence
    else:
        confidence = vote_agreement

    # If below regime direction threshold, reduce confidence
    dir_threshold = get_direction_threshold(regime)
    if confidence < dir_threshold - 0.5:
        # Force toward neutral
        final_close = prev_close_16 + change * confidence
        direction = "涨" if (final_close - prev_close_16) > 0.5 else ("跌" if (final_close - prev_close_16) < -0.5 else "平")

    # Range estimate
    pred_values = [r["pred_close"] for r in valid_results.values()]
    range_low = min(pred_values) * 0.998
    range_high = max(pred_values) * 1.002

    # Checkpoint details for transparency
    details = {}
    for cp, r in valid_results.items():
        details[cp] = {
            "pred_close": round(r["pred_close"], 2),
            "weight": round(weights.get(cp, 0.0), 3),
            "up_probability": round(r["up_probability"], 3) if r.get("up_probability") is not None else None,
            "effective_base": round(r["effective_base"], 2),
        }

    return {
        "close": round(final_close, 2),
        "direction": direction,
        "confidence": round(confidence * 100, 1),
        "range_low": round(range_low, 2),
        "range_high": round(range_high, 2),
        "checkpoint_details": details,
        "regime": regime,
        "dampening": round(1.0 - abs(final_close - prev_close_16) / max(abs(raw_close - prev_close_16), 0.01), 2) if abs(raw_close - prev_close_16) > 0.01 else 0.0,
        "n_checkpoints": len(valid_results),
    }


# ---------------------------------------------------------------------------
# High-level orchestrator
# ---------------------------------------------------------------------------

def run_multi_bar_prediction(
    bars_60min: pd.DataFrame,
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    target_dates: List[pd.Timestamp],
    lookback_days: int = 240,
    checkpoints: Optional[List[str]] = None,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """
    Run multi-bar prediction for a list of target dates.

    Each target date gets predictions from multiple checkpoints,
    aggregated into a final 16:00 close estimate.
    """
    if checkpoints is None:
        checkpoints = CHECKPOINTS

    daily_sorted = daily_df.sort_values("date").reset_index(drop=True)
    daily_closes = daily_sorted["close"].astype(float)

    # Regime info
    regime_info = compute_regime_info(daily_closes)
    regime = regime_info["regime"]
    if verbose:
        print(f"  [Regime] {regime} (vol={regime_info['annualized_vol']}%, dampening={regime_info['dampening']})")

    # Compute average session volume for normalization
    if not bars_60min.empty:
        vol_by_date = bars_60min.groupby(bars_60min["date"].dt.date)["volume"].sum()
        avg_vol = float(vol_by_date.tail(60).mean()) if len(vol_by_date) > 0 else 1.0
    else:
        avg_vol = 1.0

    # Train models for each checkpoint
    models: Dict[str, Dict[str, Any]] = {}
    for cp in checkpoints:
        if verbose:
            print(f"  [Train] {cp} checkpoint model ...", end=" ")

        X, y_ret, y_dir = build_training_dataset(
            bars_60min=bars_60min,
            daily_df=daily_sorted,
            comex_daily=comex_daily,
            usdcny_daily=usdcny_daily,
            cross_market=cross_market,
            checkpoint=cp,
            lookback_days=lookback_days,
        )

        model_info = train_checkpoint_model(X, y_ret, y_dir)
        models[cp] = model_info

        if verbose:
            if model_info["trained"]:
                m = model_info["metrics"]
                print(f"OK (n={m['train_size']}+{m['test_size']}, "
                      f"dir={m['direction_accuracy']}%)")
            else:
                print(f"SKIP ({model_info.get('reason', 'unknown')})")

    # Predict for each target date
    results: List[Dict[str, Any]] = []
    prev_close_16 = float(daily_closes.iloc[-1])

    for target_date in target_dates:
        checkpoint_preds: Dict[str, Dict[str, Any]] = {}

        for cp in checkpoints:
            if not models[cp].get("trained", False):
                continue

            features = build_checkpoint_features(
                checkpoint=cp,
                bars_60min=bars_60min,
                daily_closes=daily_closes,
                prev_close_16=prev_close_16,
                avg_session_volume=avg_vol / 6,
                comex_daily=comex_daily,
                usdcny_daily=usdcny_daily,
                cross_market=cross_market,
                target_date=target_date,
            )

            # Effective base for this checkpoint
            filtered = _filter_bars_for_checkpoint(bars_60min, cp, target_date)
            if not filtered.empty:
                effective_base = float(filtered.iloc[-1]["close"])
            else:
                effective_base = prev_close_16

            pred = predict_single_checkpoint(
                models[cp], features, effective_base, features.get("vol_5", 0.01),
            )
            checkpoint_preds[cp] = pred

        aggregated = aggregate_checkpoint_predictions(
            checkpoint_preds, regime, prev_close_16,
        )
        aggregated["date"] = target_date.strftime("%Y-%m-%d")

        results.append(aggregated)

        # Update prev_close for next iteration
        prev_close_16 = aggregated["close"]

        # Append to daily closes for feature building
        daily_closes = pd.concat(
            [daily_closes, pd.Series([aggregated["close"]])],
            ignore_index=True,
        )

    return results
