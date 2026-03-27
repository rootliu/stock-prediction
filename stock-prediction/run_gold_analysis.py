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

import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

ML_DIR = Path(__file__).resolve().parent / "ml-service"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

try:
    import akshare as ak
except ImportError:
    raise RuntimeError("akshare is required: pip install akshare")

from models.multi_bar_predictor import run_multi_bar_prediction
from models.volatility_regime import compute_regime_info

TROY_OZ_TO_GRAM = 31.1035


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
    raw = yf.download("CNY=X", start="2023-01-01", interval="1d",
                      auto_adjust=False, progress=False)
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


# ═══════════════════════════════════════════════════════════════════════
# Output formatting
# ═══════════════════════════════════════════════════════════════════════

def format_forecast(predictions: List[Dict[str, Any]], base_close: float) -> str:
    header = (
        f"{'日期':<12}  {'16:00预测(元/克)':>16}  {'方向':>4}"
        f"  {'涨跌':>10}  {'信心度':>6}  {'波动区间':>16}  {'checkpoint':>6}"
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
        n_cp = str(pred.get("n_checkpoints", "?"))
        lines.append(
            f"{pred['date']:<12}  {c:>16.2f}  {d:>4}  {chg_str:>10}  {conf:>6}  {rng:>16}  {n_cp:>6}"
        )
        prev = c

    return "\n".join(lines)


def format_checkpoint_details(pred: Dict[str, Any]) -> str:
    details = pred.get("checkpoint_details", {})
    if not details:
        return "  (无 checkpoint 细节)"
    lines = ["  Checkpoint Details:"]
    for cp in ["04:00", "09:00", "12:00", "16:00", "20:00", "24:00"]:
        if cp in details:
            d = details[cp]
            prob_str = f"prob={d['up_probability']:.1%}" if d.get("up_probability") is not None else "prob=N/A"
            lines.append(
                f"    {cp}  pred={d['pred_close']:>8.2f}  w={d['weight']:.3f}  {prob_str}  base={d['effective_base']:.2f}"
            )
    return "\n".join(lines)


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
):
    print("=" * 85)
    print("  黄金价格预测 — Multi-Bar Model (SHFE AU, CNY/克)")
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
    if not skip_backtest:
        print("\n" + "-" * 85)
        print(f"  Multi-Bar 回测 (stride={backtest_stride}, lookback={lookback}, horizon={backtest_horizon})")
        print("-" * 85)
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
        if not bt.empty:
            metrics = compute_backtest_metrics(bt)
            print("\n" + metrics.to_string(index=False))
        else:
            print("  (回测无有效数据)")
    else:
        print("\n  [跳过] 回测")

    # ── 3. 逐日预测 ──────────────────────────────────────────────────
    last_date = shfe_daily["date"].iloc[-1]
    future_dates = pd.bdate_range(last_date + pd.Timedelta(days=1), target_end)

    if len(future_dates) == 0:
        print("\n  无未来交易日需要预测")
        return []

    print("\n" + "-" * 85)
    print(f"  Multi-Bar 逐日预测 ({future_dates[0].date()} ~ {future_dates[-1].date()}, 16:00 收盘)")
    print("-" * 85)

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

    if predictions:
        print()
        print(format_forecast(predictions, latest_close))

        # Show first day's checkpoint details
        print()
        print(format_checkpoint_details(predictions[0]))
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
    )
