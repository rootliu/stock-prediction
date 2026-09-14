"""Experimental prequential combination. Never train on unmatured labels.

This module does not change the production model selection or confidence score.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE_FEATURES = ['gbm_return', 'vol20']
KRONOS_FEATURES = BASE_FEATURES + ['kronos_return', 'path_std', 'path_up_fraction', 'disagreement']


def mature_history(history: pd.DataFrame, origin, horizon: int) -> pd.DataFrame:
    if history.empty:
        return history.copy()
    origin = pd.Timestamp(origin)
    return history[(history.horizon == horizon) &
                   (pd.to_datetime(history.origin_date) < origin) &
                   (pd.to_datetime(history.target_date) <= origin)].copy()


def predict_combination(history: pd.DataFrame, current: dict, use_kronos: bool) -> float:
    train = mature_history(history, current['origin_date'], current['horizon'])
    if len(train) < 40:
        return float(current['gbm_return'])
    columns = KRONOS_FEATURES if use_kronos else BASE_FEATURES
    model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    residual = train.actual_return - train.gbm_return
    model.fit(train[columns], residual)
    return float(current['gbm_return'] + model.predict(pd.DataFrame([current])[columns])[0])


def calibrated_probability(history: pd.DataFrame, current: dict, column: str):
    train = mature_history(history, current['origin_date'], current['horizon']).dropna(subset=[column])
    value = current.get(column)
    if len(train) < 40 or value is None or not np.isfinite(value):
        return None
    y = (train.actual_return > 0).astype(int)
    if y.nunique() < 2:
        # Smoothed empirical rate is a transparent fallback for one-class history.
        return float((y.sum() + 1) / (len(y) + 2))
    model = LogisticRegression(C=1.0, random_state=42)
    model.fit(train[[column]], y)
    return float(model.predict_proba(pd.DataFrame([{column:current[column]}]))[0,1])


def calibrated_radius(past_predictions: pd.DataFrame, origin, horizon: int):
    train = mature_history(past_predictions, origin, horizon).tail(120)
    if len(train) < 30:
        return None, len(train)
    errors = (train.actual_return-train.pred_return).abs().to_numpy()
    level = min(1.0, np.ceil((len(errors)+1)*.8)/len(errors))
    return float(np.quantile(errors, level, method='higher')), len(train)
