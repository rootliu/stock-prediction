"""
Price prediction baseline with optional boosting and external direction factors.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import mean_absolute_error

from models.external_direction import (
    EXTERNAL_DIRECTION_COLUMNS,
    build_external_direction_features,
)

BASE_FEATURE_COLUMNS = [
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_5",
    "ret_1",
    "ret_3",
    "ret_5",
    "ma_5",
    "ma_10",
    "ma_20",
    "ma_gap_5",
    "ma_gap_10",
    "ma_gap_20",
    "vol_5",
]


def _resolve_feature_columns(use_external_direction: bool) -> List[str]:
    if use_external_direction:
        return BASE_FEATURE_COLUMNS + EXTERNAL_DIRECTION_COLUMNS
    return BASE_FEATURE_COLUMNS


def _format_prediction_date(value: pd.Timestamp) -> str:
    ts = pd.Timestamp(value)
    if ts.hour == 0 and ts.minute == 0 and ts.second == 0:
        return ts.strftime("%Y-%m-%d")
    return ts.strftime("%Y-%m-%d %H:%M")


def _build_feature_frame(
    close: pd.Series,
    dates: pd.Series,
    use_external_direction: bool = False,
    external_direction_csv: str | None = None,
) -> pd.DataFrame:
    df = pd.DataFrame({"close": close.astype(float)})

    df["lag_1"] = df["close"].shift(1)
    df["lag_2"] = df["close"].shift(2)
    df["lag_3"] = df["close"].shift(3)
    df["lag_5"] = df["close"].shift(5)

    df["ret_1"] = df["close"].pct_change(1)
    df["ret_3"] = df["close"].pct_change(3)
    df["ret_5"] = df["close"].pct_change(5)

    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_10"] = df["close"].rolling(10).mean()
    df["ma_20"] = df["close"].rolling(20).mean()

    df["ma_gap_5"] = df["close"] / df["ma_5"] - 1
    df["ma_gap_10"] = df["close"] / df["ma_10"] - 1
    df["ma_gap_20"] = df["close"] / df["ma_20"] - 1

    df["vol_5"] = df["ret_1"].rolling(5).std()
    df["target"] = df["close"].shift(-1) / df["close"] - 1

    if use_external_direction:
        external_df = build_external_direction_features(
            dates,
            csv_path=external_direction_csv,
            allow_fallback=True,
        )
        for col in EXTERNAL_DIRECTION_COLUMNS:
            df[col] = external_df[col].values

    return df


def _build_feature_from_window(
    window: List[float],
    external_feature_row: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    if len(window) < 20:
        raise ValueError("窗口长度不足，至少需要 20 个收盘价样本")

    s = pd.Series(window, dtype=float)
    ret_1 = s.iloc[-1] / s.iloc[-2] - 1
    ret_3 = s.iloc[-1] / s.iloc[-4] - 1
    ret_5 = s.iloc[-1] / s.iloc[-6] - 1

    ma_5 = s.tail(5).mean()
    ma_10 = s.tail(10).mean()
    ma_20 = s.tail(20).mean()

    features = {
        "lag_1": float(s.iloc[-1]),
        "lag_2": float(s.iloc[-2]),
        "lag_3": float(s.iloc[-3]),
        "lag_5": float(s.iloc[-5]),
        "ret_1": float(ret_1),
        "ret_3": float(ret_3),
        "ret_5": float(ret_5),
        "ma_5": float(ma_5),
        "ma_10": float(ma_10),
        "ma_20": float(ma_20),
        "ma_gap_5": float(s.iloc[-1] / ma_5 - 1),
        "ma_gap_10": float(s.iloc[-1] / ma_10 - 1),
        "ma_gap_20": float(s.iloc[-1] / ma_20 - 1),
        "vol_5": float(s.pct_change().tail(5).std() or 0.0),
    }
    if external_feature_row:
        features.update(external_feature_row)
    return features


def _build_models(model_type: str) -> Tuple[Any, Any, str]:
    model_type_lower = model_type.lower()
    if model_type_lower == "linear":
        reg_model = LinearRegression()
        cls_model = LogisticRegression(max_iter=600, class_weight="balanced")
        return reg_model, cls_model, "linear_regression_direction_head"
    if model_type_lower == "boosting":
        reg_model = GradientBoostingRegressor(
            random_state=42,
            n_estimators=300,
            learning_rate=0.03,
            max_depth=3,
            min_samples_leaf=8,
            subsample=0.85,
        )
        cls_model = GradientBoostingClassifier(
            random_state=42,
            n_estimators=220,
            learning_rate=0.04,
            max_depth=2,
            subsample=0.85,
        )
        return reg_model, cls_model, "gradient_boosting_direction_head"
    raise ValueError("model_type 仅支持 linear 或 boosting")


def _clip_predicted_return(pred_return: float, volatility: float) -> float:
    base_vol = max(float(volatility or 0.0), 0.005)
    cap = max(0.012, min(0.03, 2.5 * base_vol))
    return float(np.clip(pred_return, -cap, cap))


def _fuse_directional_return(
    reg_return: float,
    up_probability: Optional[float],
) -> float:
    if up_probability is None:
        return reg_return
    confidence = min(1.0, abs(up_probability - 0.5) * 2.0)
    sign_from_head = 1.0 if up_probability >= 0.5 else -1.0
    directional_return = sign_from_head * abs(reg_return)
    return float((confidence * directional_return) + ((1.0 - confidence) * reg_return))


def _predict_return(
    reg_model: Any,
    cls_model: Any,
    x_row: pd.DataFrame,
    volatility: float,
    enable_direction_head: bool,
) -> Tuple[float, Optional[float]]:
    reg_ret = float(reg_model.predict(x_row)[0])
    reg_ret = _clip_predicted_return(reg_ret, volatility)
    up_prob: Optional[float] = None

    if enable_direction_head and cls_model is not None:
        probs = cls_model.predict_proba(x_row)[0]
        up_prob = float(probs[1]) if len(probs) > 1 else None

    fused = _fuse_directional_return(reg_ret, up_prob)
    fused = _clip_predicted_return(fused, volatility)
    return fused, up_prob


def _resolve_regime(volatility: float, cutoff: float) -> str:
    return "high" if float(volatility) >= float(cutoff) else "normal"


def _apply_bias_correction(pred_close: float, bias_pct: float) -> float:
    bounded = float(np.clip(float(bias_pct), -5.0, 5.0))
    denom = 1 + bounded / 100
    if abs(denom) < 1e-8:
        return pred_close
    return float(pred_close / denom)


def _safe_metric(value: Any, default: float) -> float:
    if value is None:
        return float(default)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float(default)
    if np.isnan(numeric):
        return float(default)
    return numeric


def _close_to_direction_probability(pred_close: float, anchor_close: float) -> float:
    if pred_close > anchor_close:
        return 1.0
    if pred_close < anchor_close:
        return 0.0
    return 0.5


def _resolve_ensemble_weights(
    linear_metrics: Dict[str, Any],
    boosting_metrics: Dict[str, Any],
) -> Tuple[float, float]:
    linear_mape = max(_safe_metric(linear_metrics.get("mape"), 5.0), 0.05)
    boosting_mape = max(_safe_metric(boosting_metrics.get("mape"), 5.0), 0.05)
    linear_dir = _safe_metric(linear_metrics.get("direction_accuracy"), 50.0)
    boosting_dir = _safe_metric(boosting_metrics.get("direction_accuracy"), 50.0)

    inv_linear = 1.0 / linear_mape
    inv_boosting = 1.0 / boosting_mape
    weight_boosting = inv_boosting / (inv_linear + inv_boosting)

    # Keep the blend reversible and avoid collapsing into a single component.
    weight_boosting = float(np.clip(weight_boosting, 0.25, 0.75))
    if linear_dir - boosting_dir >= 5:
        weight_boosting = min(weight_boosting, 0.6)
    elif boosting_dir - linear_dir >= 5:
        weight_boosting = max(weight_boosting, 0.4)

    return float(1.0 - weight_boosting), float(weight_boosting)


def _build_bias_calibration_map(
    history_data: pd.DataFrame,
    reg_model: Any,
    cls_model: Any,
    feature_columns: List[str],
    horizon: int,
    use_external_direction: bool,
    external_direction_csv: str | None,
    enable_direction_head: bool,
    calibration_origin_cap: int,
) -> Dict[str, Any]:
    closes = history_data["close"].astype(float).tolist()
    dates = pd.to_datetime(history_data["date"]).reset_index(drop=True)
    if len(closes) < 80:
        return {
            "volatility_cutoff": 0.0,
            "normal": {h: 0.0 for h in range(1, horizon + 1)},
            "high": {h: 0.0 for h in range(1, horizon + 1)},
            "samples": 0,
        }

    ext_history = None
    if use_external_direction:
        ext_history = build_external_direction_features(
            dates,
            csv_path=external_direction_csv,
            allow_fallback=True,
        ).reset_index(drop=True)

    end_idx = len(closes) - horizon - 1
    start_idx = max(40, end_idx - 120)
    if end_idx <= start_idx:
        return {
            "volatility_cutoff": 0.0,
            "normal": {h: 0.0 for h in range(1, horizon + 1)},
            "high": {h: 0.0 for h in range(1, horizon + 1)},
            "samples": 0,
        }

    origin_indices = list(range(start_idx, end_idx))
    cap = max(int(calibration_origin_cap), 1)
    if len(origin_indices) > cap:
        sampled = np.linspace(0, len(origin_indices) - 1, cap, dtype=int)
        origin_indices = [origin_indices[idx] for idx in sampled]

    rows: List[Dict[str, Any]] = []
    vol_samples: List[float] = []

    for origin_idx in origin_indices:
        origin_window = closes[: origin_idx + 1]
        origin_vol = float(pd.Series(origin_window).pct_change().tail(5).std() or 0.0)
        vol_samples.append(origin_vol)
        rolling = origin_window.copy()

        for h in range(1, horizon + 1):
            external_row = None
            if use_external_direction and ext_history is not None and (origin_idx + h) < len(ext_history):
                ext_values = ext_history.iloc[origin_idx + h].to_dict()
                external_row = {col: float(ext_values.get(col, 0.0)) for col in EXTERNAL_DIRECTION_COLUMNS}

            features = _build_feature_from_window(rolling, external_feature_row=external_row)
            x_future = pd.DataFrame([[features[col] for col in feature_columns]], columns=feature_columns)
            pred_return, _ = _predict_return(
                reg_model=reg_model,
                cls_model=cls_model,
                x_row=x_future,
                volatility=features["vol_5"],
                enable_direction_head=enable_direction_head,
            )
            next_close = float(rolling[-1] * (1 + pred_return))
            rolling.append(next_close)

            actual_close = float(closes[origin_idx + h])
            bias_pct = ((next_close / actual_close) - 1) * 100 if actual_close else 0.0
            rows.append(
                {
                    "horizon": h,
                    "origin_vol": origin_vol,
                    "bias_pct": float(bias_pct),
                }
            )

    if not rows:
        return {
            "volatility_cutoff": 0.0,
            "normal": {h: 0.0 for h in range(1, horizon + 1)},
            "high": {h: 0.0 for h in range(1, horizon + 1)},
            "samples": 0,
        }

    table = pd.DataFrame(rows)
    cutoff = float(np.quantile(vol_samples, 0.75)) if vol_samples else 0.0
    table["regime"] = np.where(table["origin_vol"] >= cutoff, "high", "normal")

    result = {
        "volatility_cutoff": cutoff,
        "normal": {},
        "high": {},
        "samples": int(len(table)),
    }
    for h in range(1, horizon + 1):
        for regime in ["normal", "high"]:
            mask = (table["horizon"] == h) & (table["regime"] == regime)
            if mask.any():
                bias_pct = float(table.loc[mask, "bias_pct"].median())
            else:
                bias_pct = 0.0
            result[regime][h] = float(np.clip(bias_pct, -5.0, 5.0))
    return result


def _run_ensemble_prediction(
    df: pd.DataFrame,
    horizon: int,
    lookback: int,
    external_direction_csv: str | None,
    calibration_origin_cap: int,
    future_step_hours: int | None,
) -> Dict[str, Any]:
    linear_result = run_price_prediction(
        df=df,
        horizon=horizon,
        lookback=lookback,
        model_type="linear",
        use_external_direction=False,
        external_direction_csv=external_direction_csv,
        enable_direction_head=False,
        enable_bias_correction=False,
        calibration_origin_cap=calibration_origin_cap,
        future_step_hours=future_step_hours,
    )
    boosting_result = run_price_prediction(
        df=df,
        horizon=horizon,
        lookback=lookback,
        model_type="boosting",
        use_external_direction=True,
        external_direction_csv=external_direction_csv,
        enable_direction_head=True,
        enable_bias_correction=True,
        calibration_origin_cap=calibration_origin_cap,
        future_step_hours=future_step_hours,
    )

    anchor_close = float(linear_result["history"][-1]["close"])
    linear_weight, boosting_weight = _resolve_ensemble_weights(
        linear_result["metrics"],
        boosting_result["metrics"],
    )
    linear_dir_acc = _safe_metric(linear_result["metrics"].get("direction_accuracy"), 50.0)
    boosting_dir_acc = _safe_metric(boosting_result["metrics"].get("direction_accuracy"), 50.0)

    forecast_dates = pd.to_datetime([item["date"] for item in boosting_result["prediction"]])
    external_future = build_external_direction_features(
        pd.Series(forecast_dates),
        csv_path=external_direction_csv,
        allow_fallback=True,
    ).reset_index(drop=True)

    predictions: List[Dict[str, Any]] = []
    for idx in range(horizon):
        linear_point = linear_result["prediction"][idx]
        boosting_point = boosting_result["prediction"][idx]

        linear_close = float(linear_point["close"])
        boosting_close = float(boosting_point["close"])
        linear_delta = linear_close - anchor_close
        boosting_delta = boosting_close - anchor_close

        linear_prob = _close_to_direction_probability(linear_close, anchor_close)
        boosting_prob = boosting_point.get("up_probability")
        if boosting_prob is None:
            boosting_prob = _close_to_direction_probability(boosting_close, anchor_close)
        else:
            boosting_prob = float(boosting_prob)

        blended_close = (linear_weight * linear_close) + (boosting_weight * boosting_close)
        blended_prob = (linear_weight * linear_prob) + (boosting_weight * boosting_prob)

        linear_sign = np.sign(linear_delta)
        boosting_sign = np.sign(boosting_delta)
        if linear_sign != 0 and boosting_sign != 0 and linear_sign != boosting_sign:
            if linear_dir_acc - boosting_dir_acc >= 5:
                blended_close = anchor_close + (linear_sign * abs(boosting_delta))
                blended_prob = (0.65 * linear_prob) + (0.35 * boosting_prob)
            else:
                blended_close = anchor_close + ((blended_close - anchor_close) * 0.35)
                blended_prob = 0.5 + ((blended_prob - 0.5) * 0.6)

        ext_level = float(external_future.iloc[idx]["ext_dir_level"])
        ext_conf = float(np.clip(external_future.iloc[idx]["ext_conf_level"] / 1.5, 0.0, 1.0))
        ext_sign = np.sign(ext_level)
        blended_sign = np.sign(blended_close - anchor_close)
        if ext_sign != 0 and blended_sign != 0 and blended_sign != ext_sign and abs(ext_level) >= 0.08 and ext_conf >= 0.25:
            clamp = 0.55 if ext_conf >= 0.5 else 0.7
            blended_close = anchor_close + ((blended_close - anchor_close) * clamp)
            blended_prob = 0.5 + ((blended_prob - 0.5) * clamp)

        blended_prob = float(np.clip(blended_prob, 0.0, 1.0))
        predictions.append(
            {
                "date": boosting_point["date"],
                "close": float(blended_close),
                "up_probability": blended_prob,
                "bias_correction_pct": boosting_point.get("bias_correction_pct"),
                "regime": boosting_point.get("regime", "normal"),
            }
        )

    metrics = {
        "mae": round(
            (linear_weight * _safe_metric(linear_result["metrics"].get("mae"), 0.0))
            + (boosting_weight * _safe_metric(boosting_result["metrics"].get("mae"), 0.0)),
            6,
        ),
        "mape": round(
            (linear_weight * _safe_metric(linear_result["metrics"].get("mape"), 0.0))
            + (boosting_weight * _safe_metric(boosting_result["metrics"].get("mape"), 0.0)),
            6,
        ),
        "direction_accuracy": round(
            (linear_weight * linear_dir_acc) + (boosting_weight * boosting_dir_acc),
            6,
        ),
        "direction_head_accuracy": boosting_result["metrics"].get("direction_head_accuracy"),
        "train_size": max(
            int(_safe_metric(linear_result["metrics"].get("train_size"), 0)),
            int(_safe_metric(boosting_result["metrics"].get("train_size"), 0)),
        ),
        "test_size": max(
            int(_safe_metric(linear_result["metrics"].get("test_size"), 0)),
            int(_safe_metric(boosting_result["metrics"].get("test_size"), 0)),
        ),
    }

    return {
        "history": boosting_result["history"],
        "prediction": predictions,
        "metrics": metrics,
        "model": {
            "name": "ensemble_linear_boosting_external_v1",
            "feature_count": int(
                _safe_metric(linear_result["model"].get("feature_count"), 0)
                + _safe_metric(boosting_result["model"].get("feature_count"), 0)
            ),
            "use_external_direction": True,
            "enable_direction_head": True,
            "enable_bias_correction": True,
            "ensemble": {
                "linear_weight": round(linear_weight, 4),
                "boosting_weight": round(boosting_weight, 4),
                "disagreement_policy": "linear_sign_or_shrink",
                "external_veto": True,
                "fallback_models": ["boosting", "linear"],
            },
            "components": {
                "linear": linear_result["model"],
                "boosting": boosting_result["model"],
            },
        },
    }


def run_price_prediction(
    df: pd.DataFrame,
    horizon: int = 5,
    lookback: int = 240,
    model_type: str = "linear",
    use_external_direction: bool = False,
    external_direction_csv: str | None = None,
    enable_direction_head: bool = True,
    enable_bias_correction: bool = True,
    calibration_origin_cap: int = 8,
    future_step_hours: int | None = None,
) -> Dict[str, Any]:
    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError("输入数据缺少 date 或 close 列")
    if horizon < 1 or horizon > 30:
        raise ValueError("horizon 取值范围应为 1~30")
    if lookback < 60:
        raise ValueError("lookback 不能小于 60")
    if model_type.lower() == "ensemble":
        return _run_ensemble_prediction(
            df=df,
            horizon=horizon,
            lookback=lookback,
            external_direction_csv=external_direction_csv,
            calibration_origin_cap=calibration_origin_cap,
            future_step_hours=future_step_hours,
        )

    data = df[["date", "close"]].copy()
    data["date"] = pd.to_datetime(data["date"])
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.dropna().sort_values("date").reset_index(drop=True)

    if len(data) < 80:
        raise ValueError("历史数据不足，至少需要 80 条")

    history_data = data.tail(lookback).copy().reset_index(drop=True)
    external_meta = None
    if use_external_direction:
        _, external_meta = build_external_direction_features(
            history_data["date"],
            csv_path=external_direction_csv,
            allow_fallback=True,
            return_meta=True,
        )

    feature_df = _build_feature_frame(
        history_data["close"],
        history_data["date"],
        use_external_direction=use_external_direction,
        external_direction_csv=external_direction_csv,
    ).dropna().reset_index(drop=True)

    if len(feature_df) < 40:
        raise ValueError("可训练样本不足，请增加 lookback 或检查数据质量")

    feature_columns = _resolve_feature_columns(use_external_direction)
    x = feature_df[feature_columns]
    y = feature_df["target"]
    current_close = feature_df["close"]
    y_cls = (y > 0).astype(int)

    split_idx = max(int(len(feature_df) * 0.8), 1)
    x_train, y_train = x.iloc[:split_idx], y.iloc[:split_idx]
    x_test, y_test = x.iloc[split_idx:], y.iloc[split_idx:]
    y_cls_train, y_cls_test = y_cls.iloc[:split_idx], y_cls.iloc[split_idx:]
    current_close_test = current_close.iloc[split_idx:]

    reg_model, cls_model, model_name = _build_models(model_type)
    reg_model.fit(x_train, y_train)

    use_direction_model = enable_direction_head and y_cls_train.nunique() > 1
    if use_direction_model:
        cls_model.fit(x_train, y_cls_train)
    else:
        cls_model = None

    mae = None
    mape = None
    direction_accuracy = None
    direction_head_accuracy = None
    if len(x_test) > 0:
        pred_returns: List[float] = []
        up_probs: List[float] = []
        for idx in range(len(x_test)):
            x_row = x_test.iloc[idx : idx + 1]
            volatility = float(x_row["vol_5"].iloc[0])
            pred_ret, up_prob = _predict_return(
                reg_model=reg_model,
                cls_model=cls_model,
                x_row=x_row,
                volatility=volatility,
                enable_direction_head=enable_direction_head,
            )
            pred_returns.append(pred_ret)
            if up_prob is not None:
                up_probs.append(up_prob)

        y_pred_ret = np.array(pred_returns)
        y_pred_test = current_close_test.values * (1 + y_pred_ret)
        y_true_test = current_close_test.values * (1 + y_test.values)
        mae = float(mean_absolute_error(y_true_test, y_pred_test))
        safe_denominator = np.where(np.abs(y_true_test) < 1e-8, np.nan, y_true_test)
        mape_arr = np.abs((y_true_test - y_pred_test) / safe_denominator) * 100
        mape = float(np.nanmean(mape_arr))

        pred_dir = np.sign(y_pred_ret)
        true_dir = np.sign(y_test.values)
        direction_accuracy = float(np.mean(pred_dir == true_dir) * 100)
        if up_probs:
            head_pred = np.array([1 if p >= 0.5 else 0 for p in up_probs])
            direction_head_accuracy = float(np.mean(head_pred == y_cls_test.values) * 100)

    bias_map = {
        "volatility_cutoff": 0.0,
        "normal": {h: 0.0 for h in range(1, horizon + 1)},
        "high": {h: 0.0 for h in range(1, horizon + 1)},
        "samples": 0,
    }
    if enable_bias_correction:
        bias_map = _build_bias_calibration_map(
            history_data=history_data,
            reg_model=reg_model,
            cls_model=cls_model,
            feature_columns=feature_columns,
            horizon=horizon,
            use_external_direction=use_external_direction,
            external_direction_csv=external_direction_csv,
            enable_direction_head=enable_direction_head,
            calibration_origin_cap=calibration_origin_cap,
        )

    rolling_window = history_data["close"].tolist()
    last_date = history_data["date"].iloc[-1]
    if future_step_hours is not None:
        future_dates = pd.DatetimeIndex(
            [pd.Timestamp(last_date) + timedelta(hours=future_step_hours * step) for step in range(1, horizon + 1)]
        )
    else:
        future_dates = pd.bdate_range(last_date + timedelta(days=1), periods=horizon)

    external_timeline = None
    if use_external_direction:
        timeline_dates = pd.Series(list(history_data["date"]) + list(future_dates))
        external_timeline = build_external_direction_features(
            timeline_dates,
            csv_path=external_direction_csv,
            allow_fallback=True,
        ).reset_index(drop=True)

    predictions: List[Dict[str, Any]] = []
    history_count = len(history_data)
    for step_idx, future_date in enumerate(future_dates):
        external_row = None
        if use_external_direction and external_timeline is not None:
            ext_values = external_timeline.iloc[history_count + step_idx].to_dict()
            external_row = {col: float(ext_values.get(col, 0.0)) for col in EXTERNAL_DIRECTION_COLUMNS}

        features = _build_feature_from_window(rolling_window, external_feature_row=external_row)
        x_future = pd.DataFrame([[features[col] for col in feature_columns]], columns=feature_columns)
        pred_return, up_prob = _predict_return(
            reg_model=reg_model,
            cls_model=cls_model,
            x_row=x_future,
            volatility=features["vol_5"],
            enable_direction_head=enable_direction_head,
        )

        pred_close_raw = float(rolling_window[-1] * (1 + pred_return))
        regime = _resolve_regime(features["vol_5"], bias_map["volatility_cutoff"])
        bias_pct = float(bias_map.get(regime, {}).get(step_idx + 1, 0.0)) if enable_bias_correction else 0.0
        pred_close = _apply_bias_correction(pred_close_raw, bias_pct) if enable_bias_correction else pred_close_raw
        rolling_window.append(pred_close)
        predictions.append(
            {
                "date": _format_prediction_date(future_date),
                "close": pred_close,
                "up_probability": up_prob,
                "bias_correction_pct": bias_pct,
                "regime": regime,
            }
        )

    history = [
        {
            "date": _format_prediction_date(pd.Timestamp(row["date"])),
            "close": float(row["close"]),
        }
        for _, row in history_data.iterrows()
    ]

    return {
        "history": history,
        "prediction": predictions,
        "metrics": {
            "mae": mae,
            "mape": mape,
            "direction_accuracy": direction_accuracy,
            "direction_head_accuracy": direction_head_accuracy,
            "train_size": int(len(x_train)),
            "test_size": int(len(x_test)),
        },
        "model": {
            "name": model_name,
            "feature_count": len(feature_columns),
            "use_external_direction": bool(use_external_direction),
            "enable_direction_head": bool(enable_direction_head),
            "enable_bias_correction": bool(enable_bias_correction),
            "external_direction_meta": external_meta,
            "bias_calibration": bias_map,
        },
    }
