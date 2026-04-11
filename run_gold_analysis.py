"""
黄金价格预测 — Multi-Bar 版

改进点 (v2):
  1. 基于 SHFE AU 60min K线的多时点 checkpoint 预测
  2. 6 个 checkpoint (04:00/09:00/12:00/16:00/20:00/24:00) 各自训练模型
  3. 时间衰减加权聚合 → 输出 16:00 收盘预测
  4. 波动率 regime 自适应压缩
  5. 丰富特征: 夜盘/日盘分时 + 跨市场信号 + 日线统计
  6. 仍支持回测对比
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)
matplotlib.use("Agg")

import matplotlib.pyplot as plt

ML_DIR = Path(__file__).resolve().parent / "ml-service"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

try:
    import akshare as ak
except ImportError:
    raise RuntimeError("akshare is required: pip install akshare")

from models.multi_bar_predictor import run_multi_bar_prediction
from models.multi_day_direct_predictor import (
    rolling_backtest_direct,
    run_direct_multi_day_prediction,
)
from models.event_sentiment import build_event_scenario_bundle
from models.volatility_regime import compute_regime_info

TROY_OZ_TO_GRAM = 31.1035
_TRADE_CALENDAR_CACHE: pd.DatetimeIndex | None = None


# ═══════════════════════════════════════════════════════════════════════
# Data fetching (reused from legacy, with minor additions)
# ═══════════════════════════════════════════════════════════════════════

def _flatten_yf(raw: pd.DataFrame) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0] for col in raw.columns]
    return raw


def fetch_shfe_au_daily() -> pd.DataFrame:
    print("  [数据] SHFE AU 日线 ...")
    df = ak.futures_zh_daily_sina(symbol="AU0")
    if df is None or df.empty:
        raise RuntimeError("SHFE AU 日线数据为空")
    rename_map = {}
    for target, candidates in [
        ("date", ["日期", "date", "Date", "datetime"]),
        ("open", ["开盘价", "open", "Open"]),
        ("high", ["最高价", "high", "High"]),
        ("low", ["最低价", "low", "Low"]),
        ("close", ["收盘价", "close", "Close", "最新价"]),
        ("volume", ["成交量", "volume", "Volume"]),
    ]:
        for c in candidates:
            if c in df.columns and target not in rename_map.values():
                rename_map[c] = target
                break
    df = df.rename(columns=rename_map)
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    print(f"         {len(df)} 行, {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}")
    return df


def fetch_shfe_au_60min() -> pd.DataFrame:
    print("  [数据] SHFE AU 60min K线 ...")
    df = ak.futures_zh_minute_sina(symbol="AU0", period="60")
    if df is None or df.empty:
        raise RuntimeError("SHFE AU 60min 数据为空")
    # Normalize columns
    rename_map = {}
    for target, candidates in [
        ("date", ["datetime", "date", "Date"]),
        ("open", ["open", "Open", "开盘"]),
        ("high", ["high", "High", "最高"]),
        ("low", ["low", "Low", "最低"]),
        ("close", ["close", "Close", "收盘"]),
        ("volume", ["volume", "Volume", "成交量"]),
        ("hold", ["hold", "Hold", "持仓量"]),
    ]:
        for c in candidates:
            if c in df.columns and target not in rename_map.values():
                rename_map[c] = target
                break
    df = df.rename(columns=rename_map)
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "amount" not in df.columns:
        df["amount"] = df["close"] * df["volume"].fillna(0)
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    print(f"         {len(df)} 行, {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    return df


def fetch_comex_daily() -> pd.DataFrame:
    print("  [数据] COMEX GC=F ...")
    raw = yf.download("GC=F", start="2023-01-01", interval="1d",
                      auto_adjust=False, progress=False)
    if raw is None or raw.empty:
        raise RuntimeError("COMEX GC=F 数据为空")
    df = _flatten_yf(raw).reset_index()
    df = df.rename(columns={"Date": "date", "Close": "close"})
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df[["date", "close"]].dropna().sort_values("date").reset_index(drop=True)
    print(f"         {len(df)} 行")
    return df


def fetch_usdcny_daily() -> pd.DataFrame:
    print("  [数据] USDCNY ...")
    # CNY=X broke around Apr 2026; try USDCNY=X first, then CNY=X as fallback
    raw = None
    for ticker in ("USDCNY=X", "CNY=X"):
        raw = yf.download(ticker, start="2023-01-01", interval="1d",
                          auto_adjust=False, progress=False)
        if raw is not None and not raw.empty:
            print(f"         (使用 {ticker})")
            break
    if raw is None or raw.empty:
        raise RuntimeError("USDCNY 数据为空")
    df = _flatten_yf(raw).reset_index()
    df = df.rename(columns={"Date": "date", "Close": "usdcny"})
    df["date"] = pd.to_datetime(df["date"])
    df["usdcny"] = pd.to_numeric(df["usdcny"], errors="coerce")
    df = df[["date", "usdcny"]].dropna().sort_values("date").reset_index(drop=True)
    print(f"         {len(df)} 行, 最新汇率 {df['usdcny'].iloc[-1]:.4f}")
    return df


def fetch_cross_market() -> pd.DataFrame:
    tickers = {"DX-Y.NYB": "dxy", "^VIX": "vix", "^TNX": "us10y"}
    frames = []
    for ticker, col_name in tickers.items():
        print(f"  [数据] {col_name.upper()} ({ticker}) ...")
        try:
            raw = yf.download(ticker, start="2023-01-01", interval="1d",
                              auto_adjust=False, progress=False)
            if raw is None or raw.empty:
                continue
            df = _flatten_yf(raw).reset_index()
            df = df.rename(columns={"Date": "date", "Close": col_name})
            df["date"] = pd.to_datetime(df["date"])
            df[col_name] = pd.to_numeric(df[col_name], errors="coerce")
            frames.append(df[["date", col_name]].dropna())
            print(f"         {len(df)} 行")
        except Exception as e:
            print(f"         失败: {e}")
    if not frames:
        return pd.DataFrame(columns=["date"])
    merged = frames[0]
    for f in frames[1:]:
        merged = merged.merge(f, on="date", how="outer")
    return merged.sort_values("date").reset_index(drop=True)


def fetch_trade_calendar() -> pd.DatetimeIndex:
    global _TRADE_CALENDAR_CACHE
    if _TRADE_CALENDAR_CACHE is not None:
        return _TRADE_CALENDAR_CACHE

    try:
        calendar_df = ak.tool_trade_date_hist_sina()
        if calendar_df is None or calendar_df.empty:
            raise RuntimeError("trade calendar empty")
        column = "trade_date" if "trade_date" in calendar_df.columns else calendar_df.columns[0]
        trade_dates = pd.to_datetime(calendar_df[column]).dt.normalize().sort_values().unique()
        _TRADE_CALENDAR_CACHE = pd.DatetimeIndex(trade_dates)
        return _TRADE_CALENDAR_CACHE
    except Exception as exc:
        raise RuntimeError(f"交易日历获取失败: {exc}") from exc


def build_future_trade_dates(
    last_trade_date: pd.Timestamp,
    target_end: str | pd.Timestamp,
    bars_60min: pd.DataFrame | None = None,
) -> tuple[pd.DatetimeIndex, Dict[str, Any]]:
    last_trade_date = pd.Timestamp(last_trade_date).normalize()
    target_end_ts = pd.Timestamp(target_end).normalize()
    if target_end_ts <= last_trade_date:
        return pd.DatetimeIndex([]), {
            "target_end": target_end_ts,
            "target_end_is_trade_day": False,
            "calendar_source": "none",
        }

    target_end_is_trade_day = False
    try:
        trade_calendar = fetch_trade_calendar()
        target_end_is_trade_day = bool((trade_calendar == target_end_ts).any())
        future_dates = trade_calendar[(trade_calendar > last_trade_date) & (trade_calendar <= target_end_ts)]
        return pd.DatetimeIndex(future_dates), {
            "target_end": target_end_ts,
            "target_end_is_trade_day": target_end_is_trade_day,
            "calendar_source": "akshare_trade_calendar",
        }
    except Exception:
        observed: List[pd.Timestamp] = []
        if bars_60min is not None and not bars_60min.empty:
            observed = sorted(
                {
                    pd.Timestamp(ts).normalize()
                    for ts in pd.to_datetime(bars_60min["date"])
                    if last_trade_date < pd.Timestamp(ts).normalize() <= target_end_ts
                }
            )
        future_dates = pd.DatetimeIndex(observed)
        return future_dates, {
            "target_end": target_end_ts,
            "target_end_is_trade_day": bool((future_dates == target_end_ts).any()),
            "calendar_source": "observed_intraday_fallback",
        }


# ═══════════════════════════════════════════════════════════════════════
# Backtest (multi-bar aware)
# ═══════════════════════════════════════════════════════════════════════

def rolling_backtest(
    bars_60min: pd.DataFrame,
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    lookback: int = 240,
    max_horizon: int = 5,
    stride: int = 10,
) -> pd.DataFrame:
    """Walk-forward backtest using multi-bar predictor."""
    daily_sorted = daily_df.sort_values("date").reset_index(drop=True)
    start_idx = max(lookback, 80)
    end_idx = len(daily_sorted) - max_horizon
    origins = list(range(start_idx, end_idx, max(stride, 1)))
    total = len(origins)
    records: List[Dict[str, Any]] = []

    for done, oi in enumerate(origins):
        history_daily = daily_sorted.iloc[:oi + 1].copy()
        origin_close = float(history_daily.iloc[-1]["close"])
        origin_date = pd.Timestamp(history_daily.iloc[-1]["date"])

        # Target dates
        future_dates = []
        for h in range(1, max_horizon + 1):
            ti = oi + h
            if ti < len(daily_sorted):
                future_dates.append(pd.Timestamp(daily_sorted.iloc[ti]["date"]))

        if not future_dates:
            continue

        try:
            preds = run_multi_bar_prediction(
                bars_60min=bars_60min,
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
            records.append({
                "horizon": h_idx + 1,
                "origin_close": origin_close,
                "pred_close": pred["close"],
                "actual_close": float(daily_sorted.iloc[ti]["close"]),
                "regime": pred.get("regime", "unknown"),
                "n_checkpoints": pred.get("n_checkpoints", 0),
                "confidence": pred.get("confidence", 0),
            })

        if (done + 1) % 10 == 0:
            print(f"    回测进度: {done + 1}/{total}")

    print(f"    回测完成: {len(records)} 条记录")
    return pd.DataFrame(records)


def compute_backtest_metrics(bt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for h in sorted(bt["horizon"].unique()):
        sub = bt[bt["horizon"] == h]
        if sub.empty:
            continue
        error = sub["pred_close"] - sub["actual_close"]
        abs_pct = (error.abs() / sub["actual_close"].replace(0, np.nan)) * 100
        dir_match = (
            np.sign(sub["pred_close"] - sub["origin_close"])
            == np.sign(sub["actual_close"] - sub["origin_close"])
        )
        rows.append({
            "周期": f"T+{h}",
            "样本数": len(sub),
            "MAE(元/克)": round(float(error.abs().mean()), 2),
            "RMSE(元/克)": round(float(np.sqrt(np.mean(np.square(error)))), 2),
            "MAPE%": round(float(np.nanmean(abs_pct)), 2),
            "方向准确率%": round(float(dir_match.mean() * 100), 1),
            "平均信心度": round(float(sub["confidence"].mean()), 1),
        })
    return pd.DataFrame(rows)


def rolling_event_backtest_direct(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    lookback: int = 240,
    max_horizon: int = 5,
    stride: int = 10,
    event_context_csv: str | None = None,
    event_window_days: int = 7,
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
            if not preds:
                continue
            regime = compute_regime_info(history_daily["close"].astype(float))["regime"]
            scenario_bundle = build_event_scenario_bundle(
                base_predictions=preds,
                analysis_date=origin_date,
                regime=regime,
                daily_df=history_daily,
                event_context_csv=event_context_csv,
                window_days=event_window_days,
                use_live_survey=False,
            )
            scenario_rows = {row["date"]: row for row in scenario_bundle.get("scenario_rows", [])}
        except Exception:
            continue

        for h_idx, pred in enumerate(preds):
            ti = oi + h_idx + 1
            if ti >= len(daily_sorted):
                break
            row = scenario_rows.get(pred["date"])
            if row is None:
                continue
            actual_close = float(daily_sorted.iloc[ti]["close"])
            base_low = float(pred["range_low"])
            base_high = float(pred["range_high"])
            event_low = float(row["bear_close"])
            event_high = float(row["bull_close"])
            records.append(
                {
                    "horizon": h_idx + 1,
                    "origin_close": origin_close,
                    "actual_close": actual_close,
                    "base_low": base_low,
                    "base_high": base_high,
                    "event_low": event_low,
                    "event_high": event_high,
                    "base_hit": base_low <= actual_close <= base_high,
                    "event_hit": event_low <= actual_close <= event_high,
                    "base_width_pct": (base_high - base_low) / max(origin_close, 1e-8) * 100,
                    "event_width_pct": (event_high - event_low) / max(origin_close, 1e-8) * 100,
                }
            )
        if (done + 1) % 10 == 0:
            print(f"    事件回测进度: {done + 1}/{total}")

    print(f"    事件回测完成: {len(records)} 条记录")
    return pd.DataFrame(records)


def compute_event_backtest_metrics(bt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if bt.empty:
        return pd.DataFrame(rows)

    for h in sorted(bt["horizon"].unique()):
        sub = bt[bt["horizon"] == h]
        if sub.empty:
            continue
        rows.append(
            {
                "周期": f"T+{h}",
                "样本数": int(len(sub)),
                "Base区间命中率%": round(float(sub["base_hit"].mean() * 100), 1),
                "Event区间命中率%": round(float(sub["event_hit"].mean() * 100), 1),
                "命中率改善%": round(float((sub["event_hit"].mean() - sub["base_hit"].mean()) * 100), 1),
                "Base平均宽度%": round(float(sub["base_width_pct"].mean()), 2),
                "Event平均宽度%": round(float(sub["event_width_pct"].mean()), 2),
            }
        )
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# Output formatting
# ═══════════════════════════════════════════════════════════════════════

def format_forecast(
    predictions: List[Dict[str, Any]],
    base_close: float,
    detail_label: str = "checkpoint",
) -> str:
    header = (
        f"{'日期':<12}  {'16:00预测(元/克)':>16}  {'方向':>4}"
        f"  {'涨跌':>10}  {'信心度':>6}  {'波动区间':>16}  {detail_label:>6}"
    )
    sep = "-" * 85
    lines = [header, sep]

    prev = base_close
    for pred in predictions:
        c = pred["close"]
        d = pred["direction"]
        chg = c - prev
        chg_str = f"{'+' if chg >= 0 else ''}{chg:.2f}"
        conf = f"{pred['confidence']:.1f}%"
        rng = f"[{pred['range_low']:.0f}~{pred['range_high']:.0f}]"
        detail_count = pred.get("n_checkpoints", pred.get("n_models", "?"))
        lines.append(
            f"{pred['date']:<12}  {c:>16.2f}  {d:>4}  {chg_str:>10}  {conf:>6}  {rng:>16}  {str(detail_count):>6}"
        )
        prev = c

    return "\n".join(lines)


def format_prediction_details(pred: Dict[str, Any]) -> str:
    details = pred.get("checkpoint_details", {})
    if details:
        lines = ["  Checkpoint Details:"]
        for cp in ["04:00", "09:00", "12:00", "16:00", "20:00", "24:00"]:
            if cp in details:
                d = details[cp]
                prob_str = f"prob={d['up_probability']:.1%}" if d.get("up_probability") is not None else "prob=N/A"
                lines.append(
                    f"    {cp}  pred={d['pred_close']:>8.2f}  w={d['weight']:.3f}  {prob_str}  base={d['effective_base']:.2f}"
                )
        return "\n".join(lines)

    model_details = pred.get("model_details")
    if model_details:
        prob = model_details.get("up_probability")
        prob_str = f"{prob:.1%}" if prob is not None else "N/A"
        return "\n".join(
            [
                "  Direct Model Details:",
                (
                    f"    horizon=T+{model_details['horizon_days']}  "
                    f"pred_ret={model_details['pred_return_pct']:+.3f}%  "
                    f"prob={prob_str}  "
                    f"test_mape={model_details.get('test_mape_pct')}%  "
                    f"dir_acc={model_details.get('test_direction_accuracy')}%  "
                    f"base={model_details['effective_base']:.2f}"
                ),
            ]
        )

    return "  (无附加细节)"


def format_event_feature_summary(feature_summary: Dict[str, Any]) -> str:
    lines = ["  Event Feature Summary:"]
    lines.append(
        "    "
        f"news_bull={feature_summary.get('news_bull_score', 0.0):.2f}  "
        f"news_bear={feature_summary.get('news_bear_score', 0.0):.2f}  "
        f"blog_bull={feature_summary.get('blog_bull_score', 0.0):.2f}  "
        f"blog_bear={feature_summary.get('blog_bear_score', 0.0):.2f}"
    )
    lines.append(
        "    "
        f"safe_haven={feature_summary.get('safe_haven_score', 0.0):.2f}  "
        f"policy_risk={feature_summary.get('policy_risk_score', 0.0):.2f}  "
        f"geo_risk={feature_summary.get('geo_risk_score', 0.0):.2f}"
    )
    lines.append(
        "    "
        f"sell_the_news={feature_summary.get('sell_the_news_score', 0.0):.2f}  "
        f"usd_pressure={feature_summary.get('usd_pressure_score', 0.0):.2f}  "
        f"rate_pressure={feature_summary.get('rate_pressure_score', 0.0):.2f}  "
        f"oil_shock={feature_summary.get('oil_shock_score', 0.0):.2f}"
    )
    lines.append(f"    article_count={int(feature_summary.get('article_count', 0))}")
    return "\n".join(lines)


def format_event_calibration(calibration: Dict[str, Any]) -> str:
    lines = ["  Event Calibration:"]
    lines.append(
        "    "
        f"median_abs_return={float(calibration.get('median_abs_return', 0.0))*100:.2f}%  "
        f"p75_abs_return={float(calibration.get('p75_abs_return', 0.0))*100:.2f}%"
    )
    lines.append(
        "    "
        f"pre_event_scale={float(calibration.get('pre_event_scale', 0.0))*100:.2f}%  "
        f"post_event_scale={float(calibration.get('post_event_scale', 0.0))*100:.2f}%  "
        f"sell_the_news_scale={float(calibration.get('sell_the_news_scale', 0.0))*100:.2f}%"
    )
    return "\n".join(lines)


def format_event_headlines(bundle: Dict[str, Any]) -> str:
    lines = ["  Event Headlines:"]
    top_bull = bundle.get("top_bull", [])
    top_bear = bundle.get("top_bear", [])
    if not top_bull and not top_bear:
        lines.append("    (未抓到可用新闻/博客标题，情景区间仅基于波动率展开)")
        return "\n".join(lines)

    if top_bull:
        lines.append("    Bullish:")
        for row in top_bull:
            published = row.get("published")
            pub_str = pd.Timestamp(published).strftime("%m-%d") if published is not None else "--"
            lines.append(f"      [{pub_str}] {row['site']} | {row['title']}")
    if top_bear:
        lines.append("    Bearish:")
        for row in top_bear:
            published = row.get("published")
            pub_str = pd.Timestamp(published).strftime("%m-%d") if published is not None else "--"
            lines.append(f"      [{pub_str}] {row['site']} | {row['title']}")
    return "\n".join(lines)


def format_event_calendar(bundle: Dict[str, Any]) -> str:
    rows = bundle.get("scenario_rows", [])
    lines = ["  Event Calendar Impact:"]
    has_event = False
    for row in rows:
        active_events = row.get("active_events", [])
        if not active_events:
            continue
        has_event = True
        labels = []
        for event in active_events[:3]:
            labels.append(
                f"{event['event_name']}({event['phase']}, pre={event['pre_bias']:+.2f}, post={event['post_bias']:+.2f})"
            )
        lines.append(f"    {row['date']}: " + " | ".join(labels))
    if not has_event:
        lines.append("    (当前窗口没有命中的本地事件日历项)")
    return "\n".join(lines)


def format_scenario_table(bundle: Dict[str, Any]) -> str:
    scenario_rows = bundle.get("scenario_rows", [])
    if not scenario_rows:
        return "  (无情景路径)"

    header = (
        f"{'日期':<12}  {'Bear':>10}  {'Base':>10}  {'Bull':>10}  "
        f"{'Bull逻辑':<18}  {'Bear逻辑':<18}"
    )
    sep = "-" * 90
    lines = ["  Scenario Path:", header, sep]
    for row in scenario_rows:
        lines.append(
            f"{row['date']:<12}  "
            f"{row['bear_close']:>10.2f}  "
            f"{row['base_close']:>10.2f}  "
            f"{row['bull_close']:>10.2f}  "
            f"{row['bull_driver']:<18.18}  "
            f"{row['bear_driver']:<18.18}"
        )
    return "\n".join(lines)


def _ensure_dir(path: str | Path) -> Path:
    target = Path(path).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def _summarize_event_drivers(scenario_bundle: Dict[str, Any] | None) -> List[str]:
    if not scenario_bundle:
        return []

    summary = scenario_bundle.get("feature_summary", {}) or {}
    bullish_labels = {
        "geo_risk_score": "地缘风险",
        "policy_risk_score": "政策不确定性",
        "safe_haven_score": "避险情绪",
        "structural_support_score": "结构性买盘",
    }
    bearish_labels = {
        "sell_the_news_score": "卖事实风险",
        "usd_pressure_score": "美元反弹压力",
        "rate_pressure_score": "利率压力",
        "policy_relief_score": "政策缓和预期",
        "geo_relief_score": "地缘缓和预期",
    }

    lines: List[str] = []
    if bullish_labels:
        bull_key = max(bullish_labels, key=lambda key: float(summary.get(key, 0.0)))
        bull_val = float(summary.get(bull_key, 0.0))
        if bull_val > 0.05:
            lines.append(f"主 bullish 因子: {bullish_labels[bull_key]} ({bull_val:.2f})")

    if bearish_labels:
        bear_key = max(bearish_labels, key=lambda key: float(summary.get(key, 0.0)))
        bear_val = float(summary.get(bear_key, 0.0))
        if bear_val > 0.05:
            lines.append(f"主 bearish 因子: {bearish_labels[bear_key]} ({bear_val:.2f})")

    for pathway in scenario_bundle.get("pathways", [])[:2]:
        lines.append(f"路径解释: {pathway}")
    return lines


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _write_report_outputs(
    report_dir: str | Path,
    forecast_mode: str,
    latest_date: pd.Timestamp,
    latest_close: float,
    daily_df: pd.DataFrame,
    predictions: List[Dict[str, Any]],
    scenario_bundle: Dict[str, Any] | None,
    backtest_metrics: pd.DataFrame | None,
    event_backtest_metrics: pd.DataFrame | None,
) -> Dict[str, str]:
    output_dir = _ensure_dir(report_dir)
    stamp = latest_date.strftime("%Y-%m-%d")
    prefix = f"gold_{forecast_mode}_scenario_{stamp}"
    scenario_csv = output_dir / f"{prefix}.csv"
    report_md = output_dir / f"{prefix}.md"
    chart_png = output_dir / f"{prefix}.png"
    metrics_csv = output_dir / f"{prefix}_backtest.csv"
    event_metrics_csv = output_dir / f"{prefix}_event_backtest.csv"
    scenario_json = output_dir / f"{prefix}.json"

    scenario_rows = scenario_bundle.get("scenario_rows", []) if scenario_bundle else []
    scenario_frame = pd.DataFrame(scenario_rows)
    if not scenario_frame.empty:
        scenario_frame.to_csv(scenario_csv, index=False)

    if backtest_metrics is not None and not backtest_metrics.empty:
        backtest_metrics.to_csv(metrics_csv, index=False)
    if event_backtest_metrics is not None and not event_backtest_metrics.empty:
        event_backtest_metrics.to_csv(event_metrics_csv, index=False)

    payload = {
        "forecast_mode": forecast_mode,
        "latest_date": latest_date.strftime("%Y-%m-%d"),
        "latest_close": latest_close,
        "predictions": predictions,
        "scenario_bundle": scenario_bundle,
        "backtest_metrics": [] if backtest_metrics is None else backtest_metrics.to_dict(orient="records"),
        "event_backtest_metrics": [] if event_backtest_metrics is None else event_backtest_metrics.to_dict(orient="records"),
    }
    scenario_json.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pred_frame = pd.DataFrame(
        [
            {
                "date": row["date"],
                "close": row["close"],
                "direction": row["direction"],
                "confidence": row["confidence"],
                "range_low": row["range_low"],
                "range_high": row["range_high"],
            }
            for row in predictions
        ]
    )

    report_frame = pd.DataFrame()
    if not scenario_frame.empty:
        report_frame = scenario_frame.merge(
            pred_frame[["date", "direction", "confidence"]],
            on="date",
            how="left",
        )

    md_lines = [
        f"# Gold {forecast_mode} Scenario Report",
        "",
        f"- latest_date: {latest_date.strftime('%Y-%m-%d')}",
        f"- latest_close: {latest_close:.2f}",
        f"- forecast_mode: {forecast_mode}",
        "",
        "## 汇报版",
        "",
    ]
    if predictions:
        first_pred = predictions[0]
        md_lines.extend(
            [
                f"- 最新基准: `{latest_date.strftime('%Y-%m-%d')}` 收盘 `{latest_close:.2f}` 元/克",
                f"- 首日预测: `{first_pred['date']}` 基础情景 `{first_pred['close']:.2f}` 元/克，方向 `{first_pred['direction']}`，置信度 `{first_pred['confidence']:.1f}%`",
                f"- 波动区间: `{first_pred['range_low']:.2f} ~ {first_pred['range_high']:.2f}` 元/克",
            ]
        )
    for line in _summarize_event_drivers(scenario_bundle):
        md_lines.append(f"- {line}")
    if not report_frame.empty:
        md_lines.extend(
            [
                "",
                report_frame[
                    ["date", "bear_close", "base_close", "bull_close", "direction", "confidence", "bull_driver", "bear_driver"]
                ].to_markdown(index=False),
                "",
                f"![gold-{forecast_mode}-scenario]({chart_png})",
                "",
            ]
        )
    md_lines.extend(
        [
            "### 调用说明",
            "",
            "其它 agent 优先使用 wrapper 定时生成固定文件名的报告包：",
            "",
            "```bash",
            f"/Users/rootliu/code/stock-prediction/scripts/run_gold_direct_report.sh {output_dir} <截止日期>",
            "```",
            "",
            "如果只需要原始动态命名产物，也可以直接调用：",
            "",
            "```bash",
            f"cd /Users/rootliu/code/stock-prediction && .venv/bin/python run_gold_analysis.py --forecast-mode {forecast_mode} --skip-backtest --target-end <截止日期> --report-dir /Users/rootliu/code/report",
            "```",
            "",
            "推荐读取顺序：",
            "",
            "1. 读取本 Markdown 作为汇报版正文",
            "2. 读取同名 PNG 用于展示曲线图",
            "3. 如需结构化数据，读取同名 CSV / JSON",
            "",
            "## Forecast",
            "",
        ]
    )
    if predictions:
        md_lines.append(pred_frame.to_markdown(index=False))
        md_lines.append("")
    if scenario_frame is not None and not scenario_frame.empty:
        md_lines.extend(
            [
                "## Bull / Base / Bear",
                "",
                scenario_frame[
                    ["date", "bear_close", "base_low", "base_close", "base_high", "bull_close", "bull_driver", "bear_driver"]
                ].to_markdown(index=False),
                "",
            ]
        )
    if scenario_bundle:
        md_lines.extend(["## Event Features", "", f"```json\n{json.dumps(scenario_bundle.get('feature_summary', {}), ensure_ascii=False, indent=2)}\n```", ""])
        md_lines.extend(["## Event Calibration", "", f"```json\n{json.dumps(scenario_bundle.get('calibration', {}), ensure_ascii=False, indent=2)}\n```", ""])
        headlines = scenario_bundle.get("top_bull", []) + scenario_bundle.get("top_bear", [])
        if headlines:
            headline_frame = pd.DataFrame(
                [
                    {
                        "site": row["site"],
                        "published": pd.Timestamp(row["published"]).strftime("%Y-%m-%d") if row.get("published") is not None else "",
                        "title": row["title"],
                    }
                    for row in headlines
                ]
            )
            md_lines.extend(["## Key Headlines", "", headline_frame.to_markdown(index=False), ""])
    if backtest_metrics is not None and not backtest_metrics.empty:
        md_lines.extend(["## Base Backtest", "", backtest_metrics.to_markdown(index=False), ""])
    if event_backtest_metrics is not None and not event_backtest_metrics.empty:
        md_lines.extend(["## Event Interval Backtest", "", event_backtest_metrics.to_markdown(index=False), ""])
    report_md.write_text("\n".join(md_lines), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(12, 6))
    hist = daily_df.tail(20).copy()
    ax.plot(hist["date"], hist["close"], label="Actual", color="#1677ff", linewidth=2)
    if predictions:
        pred_frame = pd.DataFrame(predictions)
        pred_frame["date"] = pd.to_datetime(pred_frame["date"])
        ax.plot(pred_frame["date"], pred_frame["close"], label="Base", color="#fa8c16", linewidth=2)
    if not scenario_frame.empty:
        scenario_frame["date"] = pd.to_datetime(scenario_frame["date"])
        ax.plot(scenario_frame["date"], scenario_frame["bear_close"], label="Bear", color="#cf1322", linestyle="--")
        ax.plot(scenario_frame["date"], scenario_frame["bull_close"], label="Bull", color="#237804", linestyle="--")
        ax.fill_between(
            scenario_frame["date"],
            scenario_frame["bear_close"],
            scenario_frame["bull_close"],
            color="#91caff",
            alpha=0.18,
            label="Scenario Band",
        )
    ax.set_title(f"Gold {forecast_mode} Forecast with Event Scenarios", loc="left", fontsize=14, fontweight="bold")
    ax.grid(alpha=0.2)
    ax.legend(loc="best")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(chart_png, dpi=180, bbox_inches="tight")
    plt.close(fig)

    return {
        "scenario_csv": str(scenario_csv),
        "report_md": str(report_md),
        "chart_png": str(chart_png),
        "metrics_csv": str(metrics_csv),
        "event_metrics_csv": str(event_metrics_csv),
        "scenario_json": str(scenario_json),
    }


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main(
    target_end: str = "2026-04-03",
    lookback: int = 240,
    backtest_stride: int = 10,
    backtest_horizon: int = 5,
    skip_backtest: bool = False,
    skip_cross_market: bool = False,
    forecast_mode: str = "multibar",
    enable_event_scenarios: bool = True,
    event_window_days: int = 7,
    event_context_csv: str | None = None,
    report_dir: str | None = None,
):
    mode_label = "Multi-Bar Model" if forecast_mode == "multibar" else "Direct Multi-Horizon Model"
    print("=" * 85)
    print(f"  黄金价格预测 — {mode_label} (SHFE AU, CNY/克)")
    print(f"  预测截止: {target_end}, 每日 16:00 收盘")
    print("=" * 85)

    # ── 1. 获取数据 ──────────────────────────────────────────────────
    print()
    comex = fetch_comex_daily()
    usdcny = fetch_usdcny_daily()
    latest_usdcny = float(usdcny["usdcny"].iloc[-1])

    shfe_daily = fetch_shfe_au_daily()
    shfe_60min = fetch_shfe_au_60min()

    latest_close = float(shfe_daily["close"].iloc[-1])
    latest_date = shfe_daily["date"].iloc[-1]

    latest_comex_usd = float(comex["close"].iloc[-1])
    comex_cny_g = latest_comex_usd * latest_usdcny / TROY_OZ_TO_GRAM

    print(f"\n  SHFE AU 最新收盘: {latest_close:.2f} 元/克  ({latest_date.date()})")
    print(f"  COMEX 折合:       {comex_cny_g:.2f} 元/克  (${latest_comex_usd:.2f} x {latest_usdcny:.4f} / {TROY_OZ_TO_GRAM})")
    print(f"  内外盘价差:       {latest_close - comex_cny_g:+.2f} 元/克")

    # Night session latest
    night_bars = shfe_60min[
        (shfe_60min["date"].dt.hour >= 21) | (shfe_60min["date"].dt.hour < 3)
    ]
    if not night_bars.empty:
        last_night = night_bars.iloc[-1]
        print(f"  最新夜盘:         {float(last_night['close']):.2f} 元/克  ({last_night['date']})")

    # Cross-market
    if not skip_cross_market:
        print()
        cross = fetch_cross_market()
    else:
        print("\n  [跳过] 跨市场信号")
        cross = pd.DataFrame(columns=["date"])

    # Regime info
    regime_info = compute_regime_info(shfe_daily["close"])
    print(f"\n  [Regime] {regime_info['regime'].upper()} — "
          f"年化波动率 {regime_info['annualized_vol']}%, "
          f"预测压缩 {(1-regime_info['dampening'])*100:.0f}%, "
          f"方向阈值 {regime_info['direction_threshold']*100:.0f}%")

    # ── 2. 回测 ──────────────────────────────────────────────────────
    metrics = pd.DataFrame()
    event_metrics = pd.DataFrame()
    if not skip_backtest:
        print("\n" + "-" * 85)
        backtest_label = "Multi-Bar" if forecast_mode == "multibar" else "Direct Multi-Horizon"
        print(f"  {backtest_label} 回测 (stride={backtest_stride}, lookback={lookback}, horizon={backtest_horizon})")
        print("-" * 85)
        if forecast_mode == "multibar":
            bt = rolling_backtest(
                bars_60min=shfe_60min,
                daily_df=shfe_daily,
                comex_daily=comex,
                usdcny_daily=usdcny,
                cross_market=cross,
                lookback=lookback,
                max_horizon=backtest_horizon,
                stride=backtest_stride,
            )
        else:
            bt = rolling_backtest_direct(
                daily_df=shfe_daily,
                comex_daily=comex,
                usdcny_daily=usdcny,
                cross_market=cross,
                lookback=lookback,
                max_horizon=backtest_horizon,
                stride=backtest_stride,
        )
        if not bt.empty:
            metrics = compute_backtest_metrics(bt)
            print("\n" + metrics.to_string(index=False))
        else:
            print("  (回测无有效数据)")

        if forecast_mode == "direct" and enable_event_scenarios:
            print("\n" + "-" * 85)
            print("  Event Scenario 区间回测")
            print("-" * 85)
            event_bt = rolling_event_backtest_direct(
                daily_df=shfe_daily,
                comex_daily=comex,
                usdcny_daily=usdcny,
                cross_market=cross,
                lookback=lookback,
                max_horizon=backtest_horizon,
                stride=backtest_stride,
                event_context_csv=event_context_csv,
                event_window_days=event_window_days,
            )
            if not event_bt.empty:
                event_metrics = compute_event_backtest_metrics(event_bt)
                print("\n" + event_metrics.to_string(index=False))
            else:
                print("  (事件区间回测无有效数据)")
    else:
        print("\n  [跳过] 回测")

    # ── 3. 逐交易日预测 ──────────────────────────────────────────────
    last_date = shfe_daily["date"].iloc[-1]
    future_dates, calendar_meta = build_future_trade_dates(
        last_trade_date=last_date,
        target_end=target_end,
        bars_60min=shfe_60min,
    )

    if len(future_dates) == 0:
        print("\n  无未来交易日需要预测")
        return []

    if not calendar_meta.get("target_end_is_trade_day", False):
        print(
            f"\n  [Calendar] 截止日 {pd.Timestamp(target_end).date()} 不是交易日，"
            f"已按 SHFE 交易日历截断到 {future_dates[-1].date()}"
        )
    print(
        f"  [Calendar] 来源={calendar_meta.get('calendar_source')}，"
        f"目标交易日数={len(future_dates)}"
    )

    print("\n" + "-" * 85)
    predict_label = "Multi-Bar" if forecast_mode == "multibar" else "Direct Multi-Horizon"
    print(f"  {predict_label} 逐交易日预测 ({future_dates[0].date()} ~ {future_dates[-1].date()}, 16:00 收盘)")
    print("-" * 85)

    if forecast_mode == "multibar":
        predictions = run_multi_bar_prediction(
            bars_60min=shfe_60min,
            daily_df=shfe_daily,
            comex_daily=comex,
            usdcny_daily=usdcny,
            cross_market=cross,
            target_dates=list(future_dates),
            lookback_days=lookback,
            verbose=True,
        )
        detail_label = "checkpoint"
    else:
        predictions = run_direct_multi_day_prediction(
            daily_df=shfe_daily,
            comex_daily=comex,
            usdcny_daily=usdcny,
            cross_market=cross,
            target_dates=list(future_dates),
            lookback_days=lookback,
            verbose=True,
        )
        detail_label = "model"

    if predictions:
        print()
        print(format_forecast(predictions, latest_close, detail_label=detail_label))

        # Show first day's detail summary
        print()
        print(format_prediction_details(predictions[0]))

        scenario_bundle = None
        if enable_event_scenarios:
            scenario_bundle = build_event_scenario_bundle(
                base_predictions=predictions,
                analysis_date=latest_date,
                regime=regime_info["regime"],
                daily_df=shfe_daily,
                event_context_csv=event_context_csv,
                window_days=event_window_days,
            )
            print()
            print(format_event_feature_summary(scenario_bundle["feature_summary"]))
            print()
            print(format_event_calibration(scenario_bundle["calibration"]))
            print()
            print(format_event_headlines(scenario_bundle))
            print()
            print(format_event_calendar(scenario_bundle))
            print()
            for line in scenario_bundle.get("pathways", []):
                print(f"  Pathway: {line}")
            print()
            print(format_scenario_table(scenario_bundle))

            scenario_map = {row["date"]: row for row in scenario_bundle.get("scenario_rows", [])}
            for pred in predictions:
                current = scenario_map.get(pred["date"])
                if current:
                    pred["scenarios"] = {
                        "bear_close": current["bear_close"],
                        "base_close": current["base_close"],
                        "bull_close": current["bull_close"],
                        "bull_driver": current["bull_driver"],
                        "bear_driver": current["bear_driver"],
                    }

        if report_dir:
            outputs = _write_report_outputs(
                report_dir=report_dir,
                forecast_mode=forecast_mode,
                latest_date=latest_date,
                latest_close=latest_close,
                daily_df=shfe_daily,
                predictions=predictions,
                scenario_bundle=scenario_bundle,
                backtest_metrics=metrics,
                event_backtest_metrics=event_metrics,
            )
            print()
            print(f"  Report written to: {outputs['report_md']}")
            print(f"  Scenario CSV:      {outputs['scenario_csv']}")
            print(f"  Chart PNG:         {outputs['chart_png']}")
    else:
        print("  (无预测结果)")

    print("\n" + "=" * 85)
    print("  分析完成")
    print("=" * 85)

    return predictions


def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="黄金价格预测 — Multi-Bar Model (CNY/克)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认模式: 含回测 + 预测
  python run_gold_analysis.py

  # 快速预测: 跳过回测
  python run_gold_analysis.py --skip-backtest

  # 使用新增的多日直推模型
  python run_gold_analysis.py --forecast-mode direct --skip-backtest

  # 输出事件驱动的 bull/base/bear 三情景
  python run_gold_analysis.py --forecast-mode direct --skip-backtest --event-window-days 7

  # 导出到 report 目录
  python run_gold_analysis.py --forecast-mode direct --report-dir /Users/rootliu/code/report

  # 极速模式: 跳过回测和跨市场
  python run_gold_analysis.py --skip-backtest --skip-cross-market

  # 使用旧版日线模型
  python run_gold_analysis_legacy.py --skip-backtest
""",
    )
    parser.add_argument("--target-end", default="2026-04-03",
                        help="预测截止日期 YYYY-MM-DD")
    parser.add_argument("--lookback", type=int, default=240,
                        help="模型训练窗口大小 (天)")
    parser.add_argument("--backtest-stride", type=int, default=10,
                        help="回测步长")
    parser.add_argument("--backtest-horizon", type=int, default=5,
                        help="回测最大预测天数")
    parser.add_argument("--skip-backtest", action="store_true",
                        help="跳过回测")
    parser.add_argument("--skip-cross-market", action="store_true",
                        help="跳过跨市场信号")
    parser.add_argument(
        "--forecast-mode",
        default="multibar",
        choices=["multibar", "direct"],
        help="预测模式：保留原有 multibar，或使用新增 direct 多日外推",
    )
    parser.add_argument(
        "--disable-event-scenarios",
        action="store_true",
        help="关闭新闻/博客事件情绪调查与 bull/base/bear 三情景输出",
    )
    parser.add_argument(
        "--event-window-days",
        type=int,
        default=7,
        help="事件情绪回看窗口天数",
    )
    parser.add_argument(
        "--event-context-csv",
        default=None,
        help="可选事件日历 CSV，用于补充已知事件窗口",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="可选输出目录：保存 markdown/csv/png/json 报告产物",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    main(
        target_end=args.target_end,
        lookback=args.lookback,
        backtest_stride=args.backtest_stride,
        backtest_horizon=args.backtest_horizon,
        skip_backtest=args.skip_backtest,
        skip_cross_market=args.skip_cross_market,
        forecast_mode=args.forecast_mode,
        enable_event_scenarios=not args.disable_event_scenarios,
        event_window_days=args.event_window_days,
        event_context_csv=args.event_context_csv,
        report_dir=args.report_dir,
    )
