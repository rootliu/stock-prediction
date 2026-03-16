"""
价格预测基线模型
当前使用线性回归做短期时间序列预测（可替换为 XGBoost/LSTM）
"""

from datetime import timedelta
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

FEATURE_COLUMNS = [
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


def _build_feature_frame(close: pd.Series) -> pd.DataFrame:
    """从 close 序列构建监督学习特征"""
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

    return df


def _build_feature_from_window(window: List[float]) -> Dict[str, float]:
    """使用最近窗口构造下一时点预测特征"""
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
    return features


def _clip_predicted_return(pred_return: float, volatility: float) -> float:
    """
    对预测收益率加风险上限。
    目标不是消除方向判断，而是避免单日预测出现明显失真的极端跳变。
    """
    base_vol = max(float(volatility or 0.0), 0.005)
    cap = max(0.012, min(0.03, 2.5 * base_vol))
    return float(np.clip(pred_return, -cap, cap))


def run_price_prediction(
    df: pd.DataFrame,
    horizon: int = 5,
    lookback: int = 240,
) -> Dict[str, Any]:
    """
    对给定时间序列做短期收盘价预测
    Args:
        df: 至少包含 date, close 两列
        horizon: 预测未来天数
        lookback: 用于建模的历史样本长度
    """
    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError("输入数据缺少 date 或 close 列")

    if horizon < 1 or horizon > 30:
        raise ValueError("horizon 取值范围应为 1~30")
    if lookback < 60:
        raise ValueError("lookback 不能小于 60")

    data = df[["date", "close"]].copy()
    data["date"] = pd.to_datetime(data["date"])
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.dropna().sort_values("date").reset_index(drop=True)

    if len(data) < 80:
        raise ValueError("历史数据不足，至少需要 80 条")

    history_data = data.tail(lookback).copy().reset_index(drop=True)
    feature_df = _build_feature_frame(history_data["close"]).dropna().reset_index(drop=True)

    if len(feature_df) < 40:
        raise ValueError("可训练样本不足，请增加 lookback 或检查数据质量")

    x = feature_df[FEATURE_COLUMNS]
    y = feature_df["target"]
    current_close = feature_df["close"]

    split_idx = max(int(len(feature_df) * 0.8), 1)
    x_train, y_train = x.iloc[:split_idx], y.iloc[:split_idx]
    x_test, y_test = x.iloc[split_idx:], y.iloc[split_idx:]
    current_close_test = current_close.iloc[split_idx:]

    model = LinearRegression()
    model.fit(x_train, y_train)

    mae = None
    mape = None
    if len(x_test) > 0:
        y_pred_ret = model.predict(x_test)
        y_pred_ret = np.array(
            [
                _clip_predicted_return(pred_ret, vol_5)
                for pred_ret, vol_5 in zip(y_pred_ret, x_test["vol_5"].values)
            ]
        )
        y_pred_test = current_close_test.values * (1 + y_pred_ret)
        y_true_test = current_close_test.values * (1 + y_test.values)
        mae = float(mean_absolute_error(y_true_test, y_pred_test))
        safe_denominator = np.where(np.abs(y_true_test) < 1e-8, np.nan, y_true_test)
        mape_arr = np.abs((y_true_test - y_pred_test) / safe_denominator) * 100
        mape = float(np.nanmean(mape_arr))

    rolling_window = history_data["close"].tolist()
    last_date = history_data["date"].iloc[-1]
    future_dates = pd.bdate_range(last_date + timedelta(days=1), periods=horizon)

    predictions: List[Dict[str, Any]] = []
    for future_date in future_dates:
        features = _build_feature_from_window(rolling_window)
        x_future = pd.DataFrame([[features[col] for col in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
        pred_return = float(model.predict(x_future)[0])
        pred_return = _clip_predicted_return(pred_return, features["vol_5"])
        pred_close = float(rolling_window[-1] * (1 + pred_return))
        rolling_window.append(pred_close)
        predictions.append(
            {
                "date": future_date.strftime("%Y-%m-%d"),
                "close": pred_close,
            }
        )

    history = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
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
            "train_size": int(len(x_train)),
            "test_size": int(len(x_test)),
        },
        "model": {
            "name": "linear_regression_return_baseline",
            "feature_count": len(FEATURE_COLUMNS),
        },
    }
