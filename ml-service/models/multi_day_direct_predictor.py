"""
Direct multi-horizon daily predictor for gold close extrapolation.

This module preserves the existing Multi-Bar path and adds a separate
non-recursive predictor for T+1...T+N daily close forecasting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

from models.multi_bar_features import (
    FEATURE_COLUMNS_CROSS,
    FEATURE_COLUMNS_DAILY,
    build_cross_market_features,
    build_daily_features,
)
from models.volatility_regime import (
    classify_regime,
    compute_regime_info,
    dampen_prediction,
    realized_volatility,
)


REGIME_TO_CODE = {
    "low": 0.0,
    "normal": 1.0,
    "high": 2.0,
    "extreme": 3.0,
}

DIRECT_META_COLUMNS = [
    "horizon_days",
    "day_of_week",
    "month",
    "regime_code",
]

DIRECT_FEATURE_COLUMNS = FEATURE_COLUMNS_DAILY + FEATURE_COLUMNS_CROSS + DIRECT_META_COLUMNS


def _build_gbm_pair() -> Tuple[GradientBoostingRegressor, GradientBoostingClassifier]:
    reg = GradientBoostingRegressor(
        n_estimators=220,
        learning_rate=0.03,
        max_depth=3,
        min_samples_leaf=8,
        subsample=0.85,
        random_state=42,
    )
    cls = GradientBoostingClassifier(
        n_estimators=160,
        learning_rate=0.04,
        max_depth=2,
        subsample=0.85,
        random_state=42,
    )
    return reg, cls


def _build_direct_feature_row(
    daily_closes: pd.Series,
    current_close: float,
    current_date: pd.Timestamp,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    horizon_days: int,
) -> Dict[str, float]:
    daily = build_daily_features(daily_closes)
    cross = build_cross_market_features(
        comex_daily=comex_daily,
        usdcny_daily=usdcny_daily,
        cross_market=cross_market,
        shfe_close=current_close,
        target_date=current_date,
    )
    ann_vol = realized_volatility(daily_closes.astype(float), window=20)
    regime = classify_regime(ann_vol)
    meta = {
        "horizon_days": float(horizon_days),
        "day_of_week": float(current_date.dayofweek),
        "month": float(current_date.month),
        "regime_code": REGIME_TO_CODE.get(regime, 1.0),
    }

    row: Dict[str, float] = {}
    row.update(daily)
    row.update(cross)
    row.update(meta)
    return row


def _build_training_dataset(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    horizon_days: int,
    lookback_days: int = 240,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    daily_sorted = daily_df.sort_values("date").reset_index(drop=True)
    usable_end = len(daily_sorted) - horizon_days
    if usable_end <= 20:
        empty_x = pd.DataFrame(columns=DIRECT_FEATURE_COLUMNS)
        return empty_x, pd.Series(dtype=float), pd.Series(dtype=int), pd.Series(dtype=float)

    start_idx = max(20, usable_end - lookback_days)

    rows: List[Dict[str, float]] = []
    y_return: List[float] = []
    y_direction: List[int] = []
    bases: List[float] = []

    for idx in range(start_idx, usable_end):
        current_date = pd.Timestamp(daily_sorted.iloc[idx]["date"])
        current_close = float(daily_sorted.iloc[idx]["close"])
        target_close = float(daily_sorted.iloc[idx + horizon_days]["close"])
        if current_close <= 0 or target_close <= 0:
            continue

        daily_closes = daily_sorted.iloc[max(0, idx - 20): idx + 1]["close"]
        feature_row = _build_direct_feature_row(
            daily_closes=daily_closes,
            current_close=current_close,
            current_date=current_date,
            comex_daily=comex_daily,
            usdcny_daily=usdcny_daily,
            cross_market=cross_market,
            horizon_days=horizon_days,
        )
        rows.append(feature_row)
        ret = target_close / current_close - 1
        y_return.append(float(ret))
        y_direction.append(1 if ret > 0 else 0)
        bases.append(current_close)

    if not rows:
        empty_x = pd.DataFrame(columns=DIRECT_FEATURE_COLUMNS)
        return empty_x, pd.Series(dtype=float), pd.Series(dtype=int), pd.Series(dtype=float)

    x = pd.DataFrame(rows)
    for col in DIRECT_FEATURE_COLUMNS:
        if col not in x.columns:
            x[col] = 0.0
    x = x[DIRECT_FEATURE_COLUMNS]
    return (
        x,
        pd.Series(y_return, dtype=float),
        pd.Series(y_direction, dtype=int),
        pd.Series(bases, dtype=float),
    )


def _evaluate(
    reg: GradientBoostingRegressor,
    cls: Optional[GradientBoostingClassifier],
    x_test: pd.DataFrame,
    y_test: pd.Series,
    y_dir_test: pd.Series,
    base_test: pd.Series,
) -> Dict[str, Any]:
    if len(x_test) == 0:
        return {
            "mae": None,
            "rmse": None,
            "mape_pct": None,
            "direction_accuracy": None,
        }

    pred_ret = reg.predict(x_test)
    pred_close = base_test.values * (1 + pred_ret)
    actual_close = base_test.values * (1 + y_test.values)
    error = pred_close - actual_close
    abs_pct = np.abs(error) / np.maximum(np.abs(actual_close), 1e-8) * 100
    pred_dir = (pred_ret > 0).astype(int)

    cls_dir_acc = None
    if cls is not None:
        cls_pred = cls.predict(x_test)
        cls_dir_acc = float(np.mean(cls_pred == y_dir_test.values) * 100)

    return {
        "mae": round(float(np.abs(error).mean()), 4),
        "rmse": round(float(np.sqrt(np.mean(np.square(error)))), 4),
        "mape_pct": round(float(np.nanmean(abs_pct)), 4),
        "direction_accuracy": round(float(np.mean(pred_dir == y_dir_test.values) * 100), 2),
        "cls_direction_accuracy": round(cls_dir_acc, 2) if cls_dir_acc is not None else None,
    }


def _clip_return(pred_return: float, vol_5: float, horizon_days: int) -> float:
    base_vol = max(float(vol_5 or 0.0), 0.005) * np.sqrt(max(horizon_days, 1))
    cap = max(0.015, min(0.08, 2.2 * base_vol))
    return float(np.clip(pred_return, -cap, cap))


def _train_horizon_model(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    horizon_days: int,
    lookback_days: int,
) -> Dict[str, Any]:
    x, y_ret, y_dir, bases = _build_training_dataset(
        daily_df=daily_df,
        comex_daily=comex_daily,
        usdcny_daily=usdcny_daily,
        cross_market=cross_market,
        horizon_days=horizon_days,
        lookback_days=lookback_days,
    )
    if len(x) < 50:
        return {"trained": False, "reason": f"insufficient data ({len(x)} < 50)"}

    split = int(len(x) * 0.8)
    x_train, x_test = x.iloc[:split], x.iloc[split:]
    y_ret_train, y_ret_test = y_ret.iloc[:split], y_ret.iloc[split:]
    y_dir_train, y_dir_test = y_dir.iloc[:split], y_dir.iloc[split:]
    base_test = bases.iloc[split:]

    reg, cls = _build_gbm_pair()
    reg.fit(x_train, y_ret_train)

    if y_dir_train.nunique() > 1:
        cls.fit(x_train, y_dir_train)
    else:
        cls = None

    metrics = _evaluate(reg, cls, x_test, y_ret_test, y_dir_test, base_test)
    metrics["train_size"] = len(x_train)
    metrics["test_size"] = len(x_test)

    return {
        "trained": True,
        "reg_model": reg,
        "cls_model": cls,
        "metrics": metrics,
    }


def run_direct_multi_day_prediction(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    target_dates: Sequence[pd.Timestamp],
    lookback_days: int = 240,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    if not target_dates:
        return []

    daily_sorted = daily_df.sort_values("date").reset_index(drop=True)
    current_close = float(daily_sorted.iloc[-1]["close"])
    current_date = pd.Timestamp(daily_sorted.iloc[-1]["date"])
    regime_info = compute_regime_info(daily_sorted["close"].astype(float))
    regime = regime_info["regime"]

    if verbose:
        print(
            f"  [Regime] {regime} (vol={regime_info['annualized_vol']}%, dampening={regime_info['dampening']})"
        )

    models: Dict[int, Dict[str, Any]] = {}
    for horizon_days in range(1, len(target_dates) + 1):
        if verbose:
            print(f"  [Train] T+{horizon_days} direct model ...", end=" ")
        model_info = _train_horizon_model(
            daily_df=daily_sorted,
            comex_daily=comex_daily,
            usdcny_daily=usdcny_daily,
            cross_market=cross_market,
            horizon_days=horizon_days,
            lookback_days=lookback_days,
        )
        models[horizon_days] = model_info
        if verbose:
            if model_info["trained"]:
                m = model_info["metrics"]
                print(
                    f"OK (n={m['train_size']}+{m['test_size']}, "
                    f"dir={m['direction_accuracy']}%, mape={m['mape_pct']}%)"
                )
            else:
                print(f"SKIP ({model_info.get('reason', 'unknown')})")

    history_window = daily_sorted.iloc[max(0, len(daily_sorted) - 21):]["close"]
    predictions: List[Dict[str, Any]] = []
    for horizon_days, target_date in enumerate(target_dates, start=1):
        model_info = models.get(horizon_days, {})
        if not model_info.get("trained", False):
            continue

        feature_row = _build_direct_feature_row(
            daily_closes=history_window,
            current_close=current_close,
            current_date=current_date,
            comex_daily=comex_daily,
            usdcny_daily=usdcny_daily,
            cross_market=cross_market,
            horizon_days=horizon_days,
        )
        x_row = pd.DataFrame([[feature_row[col] for col in DIRECT_FEATURE_COLUMNS]], columns=DIRECT_FEATURE_COLUMNS)
        vol_5 = float(feature_row.get("vol_5", 0.0))

        pred_return = float(model_info["reg_model"].predict(x_row)[0])
        pred_return = _clip_return(pred_return, vol_5, horizon_days)
        pred_close_raw = current_close * (1 + pred_return)
        pred_close = float(dampen_prediction(pred_close_raw, current_close, regime))

        up_prob = None
        cls_model = model_info.get("cls_model")
        if cls_model is not None:
            probs = cls_model.predict_proba(x_row)[0]
            up_prob = float(probs[1]) if len(probs) > 1 else None

        metrics = model_info.get("metrics", {})
        prob_conf = abs(up_prob - 0.5) * 2 if up_prob is not None else 0.0
        dir_acc = float(metrics.get("direction_accuracy") or 50.0) / 100.0
        horizon_decay = max(0.45, 1.0 - 0.10 * (horizon_days - 1))
        confidence = (0.55 * prob_conf + 0.45 * dir_acc) * 100 * horizon_decay

        range_pct = max(float(metrics.get("mape_pct") or 1.0) / 100.0, 0.005)
        range_pct *= min(1.6, 1.0 + 0.12 * (horizon_days - 1))
        range_low = pred_close * (1 - range_pct)
        range_high = pred_close * (1 + range_pct)

        delta = pred_close - current_close
        direction = "涨" if delta > 0.5 else ("跌" if delta < -0.5 else "平")
        predictions.append(
            {
                "date": pd.Timestamp(target_date).strftime("%Y-%m-%d"),
                "close": round(pred_close, 2),
                "direction": direction,
                "confidence": round(float(np.clip(confidence, 0.0, 95.0)), 1),
                "range_low": round(range_low, 2),
                "range_high": round(range_high, 2),
                "regime": regime,
                "n_models": 1,
                "model_details": {
                    "model_name": "direct_gbm_multi_horizon_v1",
                    "horizon_days": horizon_days,
                    "pred_return_pct": round(pred_return * 100, 3),
                    "up_probability": round(up_prob, 4) if up_prob is not None else None,
                    "test_mape_pct": metrics.get("mape_pct"),
                    "test_direction_accuracy": metrics.get("direction_accuracy"),
                    "effective_base": round(current_close, 2),
                },
            }
        )

    return predictions


def rolling_backtest_direct(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    lookback: int = 240,
    max_horizon: int = 5,
    stride: int = 10,
) -> pd.DataFrame:
    daily_sorted = daily_df.sort_values("date").reset_index(drop=True)
    start_idx = max(lookback, 80)
    end_idx = len(daily_sorted) - max_horizon
    origins = list(range(start_idx, end_idx, max(stride, 1)))
    total = len(origins)
    records: List[Dict[str, Any]] = []

    for done, oi in enumerate(origins):
        history_daily = daily_sorted.iloc[: oi + 1].copy()
        origin_close = float(history_daily.iloc[-1]["close"])
        origin_date = pd.Timestamp(history_daily.iloc[-1]["date"])
        future_dates = []
        for h in range(1, max_horizon + 1):
            ti = oi + h
            if ti < len(daily_sorted):
                future_dates.append(pd.Timestamp(daily_sorted.iloc[ti]["date"]))

        if not future_dates:
            continue

        try:
            preds = run_direct_multi_day_prediction(
                daily_df=history_daily,
                comex_daily=comex_daily[comex_daily["date"] <= origin_date],
                usdcny_daily=usdcny_daily[usdcny_daily["date"] <= origin_date],
                cross_market=cross_market[cross_market["date"] <= origin_date],
                target_dates=future_dates,
                lookback_days=lookback,
                verbose=False,
            )
        except Exception:
            continue

        for h_idx, pred in enumerate(preds):
            ti = oi + h_idx + 1
            if ti >= len(daily_sorted):
                break
            records.append(
                {
                    "horizon": h_idx + 1,
                    "origin_close": origin_close,
                    "pred_close": pred["close"],
                    "actual_close": float(daily_sorted.iloc[ti]["close"]),
                    "regime": pred.get("regime", "unknown"),
                    "confidence": pred.get("confidence", 0),
                }
            )

        if (done + 1) % 10 == 0:
            print(f"    回测进度: {done + 1}/{total}")

    print(f"    回测完成: {len(records)} 条记录")
    return pd.DataFrame(records)
