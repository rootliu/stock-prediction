"""
黄金价格预测 — 改进版
输出: CNY/克, 每天一行 16:00 收盘预测

改进点:
  1. 主数据源切换为 SHFE AU (已是 CNY/克)
  2. 跨市场信号注入 (DXY, VIX, US10Y, USDCNY, COMEX 价差)
  3. 逐日 horizon=1 顺序预测 (消除递归误差累积)
  4. 自适应模型加权 + 极端行情均值回归过滤
  5. 回测与预测输出统一为 CNY/克
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure the correct site-packages is on sys.path
_code_sp = Path(r"C:\Users\liuya\Documents\code\Lib\site-packages")
if _code_sp.is_dir() and str(_code_sp) not in sys.path:
    sys.path.insert(0, str(_code_sp))

import akshare as ak
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

ML_DIR = Path(__file__).resolve().parent / "ml-service"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from models.predictor import run_price_prediction

TROY_OZ_TO_GRAM = 31.1035


# ═══════════════════════════════════════════════════════════════════════
# Step 1: 多数据源获取
# ═══════════════════════════════════════════════════════════════════════

def _flatten_yf(raw: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance MultiIndex columns if present."""
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0] for col in raw.columns]
    return raw


def fetch_shfe_au_daily() -> pd.DataFrame:
    """获取上期所黄金主力合约日线 (CNY/克)."""
    print("  [数据] 获取 SHFE AU 主力合约 ...")
    try:
        df = ak.futures_zh_daily_sina(symbol="AU0")
    except Exception as e:
        raise RuntimeError(f"akshare 获取 SHFE AU 失败: {e}")

    if df is None or df.empty:
        raise RuntimeError("SHFE AU 数据为空")

    # 列名归一化 (akshare 不同版本列名可能不同)
    rename_map = {}
    for target, candidates in [
        ("date", ["日期", "date", "Date", "datetime"]),
        ("open", ["开盘价", "open", "Open", "开盘"]),
        ("high", ["最高价", "high", "High", "最高"]),
        ("low", ["最低价", "low", "Low", "最低"]),
        ("close", ["收盘价", "close", "Close", "收盘", "最新价"]),
        ("volume", ["成交量", "volume", "Volume"]),
    ]:
        for c in candidates:
            if c in df.columns and target not in rename_map.values():
                rename_map[c] = target
                break

    df = df.rename(columns=rename_map)
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    print(f"         {len(df)} 行, {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}")
    return df


def fetch_comex_daily() -> pd.DataFrame:
    """获取 COMEX 黄金期货日线 (USD/盎司)."""
    print("  [数据] 获取 COMEX GC=F ...")
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
    """获取 USDCNY 汇率日线."""
    print("  [数据] 获取 USDCNY ...")
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
    """获取跨市场指标: DXY, VIX, US10Y."""
    tickers = {"DX-Y.NYB": "dxy", "^VIX": "vix", "^TNX": "us10y"}
    frames = []
    for ticker, col_name in tickers.items():
        print(f"  [数据] 获取 {col_name.upper()} ({ticker}) ...")
        try:
            raw = yf.download(ticker, start="2023-01-01", interval="1d",
                              auto_adjust=False, progress=False)
            if raw is None or raw.empty:
                print(f"         {col_name} 无数据, 跳过")
                continue
            df = _flatten_yf(raw).reset_index()
            df = df.rename(columns={"Date": "date", "Close": col_name})
            df["date"] = pd.to_datetime(df["date"])
            df[col_name] = pd.to_numeric(df[col_name], errors="coerce")
            frames.append(df[["date", col_name]].dropna())
            print(f"         {len(df)} 行")
        except Exception as e:
            print(f"         {col_name} 获取失败: {e}")

    if not frames:
        return pd.DataFrame(columns=["date"])

    merged = frames[0]
    for f in frames[1:]:
        merged = merged.merge(f, on="date", how="outer")
    return merged.sort_values("date").reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════
# Step 2: 跨市场信号注入 — 合成调整收盘价
# ═══════════════════════════════════════════════════════════════════════

def compute_cross_market_adjustment(
    shfe: pd.DataFrame,
    comex: pd.DataFrame,
    usdcny: pd.DataFrame,
    cross: pd.DataFrame,
) -> pd.Series:
    """
    基于跨市场信号计算每日微调量 (CNY/克).
    总调整幅度限制在 ±0.3% close 以内.
    """
    m = shfe[["date", "close"]].copy()

    # COMEX 折合 CNY/克
    comex_cny = comex.merge(usdcny, on="date", how="inner")
    comex_cny["comex_cny_g"] = comex_cny["close"] * comex_cny["usdcny"] / TROY_OZ_TO_GRAM
    m = m.merge(comex_cny[["date", "comex_cny_g"]], on="date", how="left")
    m = m.merge(usdcny, on="date", how="left")
    m = m.merge(cross, on="date", how="left")
    m = m.sort_values("date").reset_index(drop=True)

    # 前向填充 (不同交易日历)
    for col in ["comex_cny_g", "usdcny", "dxy", "vix", "us10y"]:
        if col in m.columns:
            m[col] = m[col].ffill()

    adj = pd.Series(0.0, index=m.index)

    # 信号 1: SHFE-COMEX 溢价/折价 → 均值回归
    if "comex_cny_g" in m.columns and m["comex_cny_g"].notna().sum() > 30:
        premium = m["close"] / m["comex_cny_g"] - 1
        p_mean = premium.rolling(20, min_periods=5).mean()
        p_std = premium.rolling(20, min_periods=5).std().clip(lower=0.001)
        premium_z = (premium - p_mean) / p_std
        adj -= premium_z.fillna(0) * 0.0005 * m["close"]

    # 信号 2: DXY (美元强→金弱)
    if "dxy" in m.columns and m["dxy"].notna().sum() > 30:
        dxy_ret = m["dxy"].pct_change(5)
        d_mean = dxy_ret.rolling(20, min_periods=5).mean()
        d_std = dxy_ret.rolling(20, min_periods=5).std().clip(lower=0.001)
        dxy_z = (dxy_ret - d_mean) / d_std
        adj -= dxy_z.fillna(0) * 0.0003 * m["close"]

    # 信号 3: VIX (避险情绪→金涨)
    if "vix" in m.columns and m["vix"].notna().sum() > 30:
        v_mean = m["vix"].rolling(20, min_periods=5).mean()
        v_std = m["vix"].rolling(20, min_periods=5).std().clip(lower=0.1)
        vix_z = (m["vix"] - v_mean) / v_std
        adj += vix_z.fillna(0) * 0.0002 * m["close"]

    # 信号 4: US10Y (收益率升→金跌, 机会成本)
    if "us10y" in m.columns and m["us10y"].notna().sum() > 30:
        y_ret = m["us10y"].pct_change(5)
        y_mean = y_ret.rolling(20, min_periods=5).mean()
        y_std = y_ret.rolling(20, min_periods=5).std().clip(lower=0.001)
        y_z = (y_ret - y_mean) / y_std
        adj -= y_z.fillna(0) * 0.0002 * m["close"]

    # 限幅: ±0.3% close
    cap = 0.003 * m["close"]
    adj = adj.clip(-cap, cap)
    return adj


# ═══════════════════════════════════════════════════════════════════════
# Step 3 & 4: 逐日预测 + 自适应加权
# ═══════════════════════════════════════════════════════════════════════

MODEL_CONFIGS: List[Tuple[str, Dict[str, Any]]] = [
    ("linear", {
        "model_type": "linear",
        "use_external_direction": False,
        "enable_direction_head": True,
        "enable_bias_correction": False,
    }),
    ("boosting", {
        "model_type": "boosting",
        "use_external_direction": True,
        "enable_direction_head": True,
        "enable_bias_correction": True,
    }),
    ("ensemble", {
        "model_type": "ensemble",
        "use_external_direction": False,
        "enable_direction_head": False,
        "enable_bias_correction": False,
    }),
]


def _weighted_combine(
    preds: Dict[str, Dict[str, Any]],
    history_close: pd.Series,
) -> Tuple[float, str, float]:
    """
    多模型加权合并.
    返回: (combined_close, 方向标签, 信心度%)
    """
    prev_close = float(history_close.iloc[-1])

    # A. 按 MAPE + 方向准确率计算权重
    weights: Dict[str, float] = {}
    for name, p in preds.items():
        mape = p.get("mape") or 5.0
        dir_acc = p.get("dir_acc") or 50.0
        w = 0.6 / max(mape, 0.1) + 0.4 * max(dir_acc - 45.0, 5.0) / 55.0
        weights[name] = w

    w_total = sum(weights.values())
    if w_total > 0:
        weights = {k: v / w_total for k, v in weights.items()}
    else:
        n = len(preds)
        weights = {k: 1.0 / n for k in preds}

    # B. 加权平均
    combined = sum(weights[m] * preds[m]["close"] for m in preds)

    # C. 极端行情均值回归过滤
    tail = history_close.tail(20).values
    if len(tail) >= 6:
        ret_5 = tail[-1] / tail[-6] - 1
        ret_std = float(pd.Series(tail).pct_change().std() * np.sqrt(5))
        if ret_std > 0 and abs(ret_5) > 2.0 * ret_std:
            combined = prev_close + (combined - prev_close) * 0.6

    # D. 方向 & 信心
    change = combined - prev_close
    direction = "涨" if change > 0 else ("跌" if change < 0 else "平")

    up_votes = sum(1 for m in preds if preds[m]["close"] > prev_close)
    total = len(preds)
    agreement = max(up_votes, total - up_votes) / total if total > 0 else 0.5

    probs = [float(preds[m]["up_prob"]) for m in preds
             if preds[m].get("up_prob") is not None]
    if probs:
        prob_conf = abs(np.mean(probs) - 0.5) * 2
        confidence = 0.5 * agreement + 0.5 * prob_conf
    else:
        confidence = agreement

    return combined, direction, round(confidence * 100, 1)


def sequential_forecast(
    data: pd.DataFrame,
    future_dates: pd.DatetimeIndex,
    lookback: int = 240,
) -> pd.DataFrame:
    """
    逐日 horizon=1 预测: 每天用 3 个模型预测 → 加权合并 → 追加到历史.
    """
    working = data[["date", "close"]].copy()
    rows: List[Dict[str, Any]] = []

    for fdate in future_dates:
        preds: Dict[str, Dict[str, Any]] = {}

        for model_name, kwargs in MODEL_CONFIGS:
            try:
                result = run_price_prediction(
                    working,
                    horizon=1,
                    lookback=min(lookback, len(working) - 1),
                    future_dates=pd.DatetimeIndex([fdate]),
                    **kwargs,
                )
                preds[model_name] = {
                    "close": float(result["prediction"][0]["close"]),
                    "up_prob": result["prediction"][0].get("up_probability"),
                    "mape": result["metrics"].get("mape"),
                    "dir_acc": result["metrics"].get("direction_accuracy"),
                }
            except Exception as e:
                print(f"    {model_name} @ {fdate.date()} 失败: {e}")

        if not preds:
            print(f"    {fdate.date()} 所有模型失败, 停止预测")
            break

        combined_close, direction, confidence = _weighted_combine(
            preds, working["close"],
        )

        rows.append({
            "date": fdate.strftime("%Y-%m-%d"),
            "close": round(combined_close, 2),
            "direction": direction,
            "confidence": confidence,
        })

        # 追加到历史供下一步使用
        working = pd.concat([working, pd.DataFrame([{
            "date": fdate, "close": combined_close,
        }])], ignore_index=True)

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# Step 5: 回测 (CNY/克)
# ═══════════════════════════════════════════════════════════════════════

def rolling_backtest(
    data: pd.DataFrame,
    lookback: int = 240,
    max_horizon: int = 5,
    stride: int = 10,
) -> pd.DataFrame:
    """SHFE AU 滚动回测, 所有指标为 CNY/克."""
    configs = [
        ("linear", {"model_type": "linear", "use_external_direction": False,
                     "enable_direction_head": False, "enable_bias_correction": False}),
        ("boosting", {"model_type": "boosting", "use_external_direction": True,
                      "enable_direction_head": True, "enable_bias_correction": True}),
        ("ensemble", {"model_type": "ensemble", "use_external_direction": False,
                      "enable_direction_head": False, "enable_bias_correction": False}),
    ]

    records: List[Dict[str, Any]] = []
    start_idx = max(lookback, 80)
    end_idx = len(data) - max_horizon
    origins = list(range(start_idx, end_idx, max(stride, 1)))
    total = len(origins) * len(configs)
    done = 0

    for label, kwargs in configs:
        for oi in origins:
            history = data.loc[:oi, ["date", "close"]].copy()
            origin_close = float(data.iloc[oi]["close"])
            try:
                result = run_price_prediction(
                    history, horizon=max_horizon, lookback=lookback, **kwargs,
                )
            except Exception:
                done += 1
                continue
            for h in range(1, max_horizon + 1):
                ti = oi + h
                if ti >= len(data):
                    continue
                records.append({
                    "model": label,
                    "horizon": h,
                    "origin_close": origin_close,
                    "pred_close": float(result["prediction"][h - 1]["close"]),
                    "actual_close": float(data.iloc[ti]["close"]),
                })
            done += 1
            if done % 30 == 0:
                print(f"    回测进度: {done}/{total}")

    print(f"    回测完成: {len(records)} 条记录")
    return pd.DataFrame(records)


def compute_metrics(bt: pd.DataFrame) -> pd.DataFrame:
    """按 model × horizon 汇总回测指标."""
    rows = []
    for model in bt["model"].unique():
        for h in sorted(bt["horizon"].unique()):
            sub = bt[(bt["model"] == model) & (bt["horizon"] == h)]
            if sub.empty:
                continue
            error = sub["pred_close"] - sub["actual_close"]
            abs_pct = (error.abs() / sub["actual_close"].replace(0, np.nan)) * 100
            dir_match = (
                np.sign(sub["pred_close"] - sub["origin_close"])
                == np.sign(sub["actual_close"] - sub["origin_close"])
            )
            rows.append({
                "模型": model,
                "周期": f"T+{h}",
                "样本数": len(sub),
                "MAE(元/克)": round(float(error.abs().mean()), 2),
                "RMSE(元/克)": round(float(np.sqrt(np.mean(np.square(error)))), 2),
                "MAPE%": round(float(np.nanmean(abs_pct)), 2),
                "方向准确率%": round(float(dir_match.mean() * 100), 1),
            })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# Step 6: 输出格式 + Main
# ═══════════════════════════════════════════════════════════════════════

def format_forecast(predictions: pd.DataFrame, base_close: float) -> str:
    """格式化每日预测表格."""
    header = (
        f"{'日期':<12}  {'预测16:00收盘(元/克)':>20}  {'方向':>4}"
        f"  {'较前日涨跌(元/克)':>16}  {'信心度':>6}"
    )
    sep = "-" * 72
    lines = [header, sep]

    prev = base_close
    for _, row in predictions.iterrows():
        c = row["close"]
        d = row["direction"]
        chg = c - prev
        chg_str = f"{'+' if chg >= 0 else ''}{chg:.2f}"
        conf = f"{row['confidence']:.1f}%"
        lines.append(
            f"{row['date']:<12}  {c:>20.2f}  {d:>4}  {chg_str:>16}  {conf:>6}"
        )
        prev = c

    return "\n".join(lines)


def main(
    source: str = "shfe",
    target_end: str = "2026-04-03",
    lookback: int = 240,
    backtest_stride: int = 10,
    backtest_horizon: int = 5,
    skip_backtest: bool = False,
    skip_cross_market: bool = False,
):
    """
    黄金价格预测主函数.

    Parameters
    ----------
    source : str
        数据源. "shfe" = SHFE AU 主力合约 (CNY/克, 默认),
        "comex" = COMEX GC=F (自动转换为 CNY/克).
    target_end : str
        预测截止日期, 格式 YYYY-MM-DD. 默认 "2026-04-03".
    lookback : int
        模型训练窗口大小. 默认 240.
    backtest_stride : int
        回测步长 (越大越快, 样本越少). 默认 10.
    backtest_horizon : int
        回测最大预测天数. 默认 5.
    skip_backtest : bool
        跳过回测, 仅输出预测. 默认 False.
    skip_cross_market : bool
        跳过跨市场信号调整. 默认 False.
    """
    source = source.lower()

    print("=" * 72)
    print(f"  黄金价格预测 — {'SHFE AU 主力合约' if source == 'shfe' else 'COMEX GC=F'} (CNY/克)")
    print(f"  预测截止: {target_end}, 每日 16:00 收盘")
    print("=" * 72)

    # ── 1. 获取数据 ──────────────────────────────────────────────────
    print()
    comex = fetch_comex_daily()
    usdcny = fetch_usdcny_daily()
    latest_usdcny = float(usdcny["usdcny"].iloc[-1])

    if source == "shfe":
        shfe = fetch_shfe_au_daily()
        primary = shfe[["date", "close"]].copy()
        primary_label = "SHFE AU"
    else:
        # 将 COMEX USD/oz 转换为 CNY/克
        primary = comex[["date", "close"]].copy()
        primary = primary.merge(usdcny, on="date", how="left")
        primary["usdcny"] = primary["usdcny"].ffill()
        primary["close"] = primary["close"] * primary["usdcny"] / TROY_OZ_TO_GRAM
        primary = primary[["date", "close"]].dropna().reset_index(drop=True)
        primary_label = "COMEX (CNY/克)"
        shfe = primary  # alias for cross-market adjustment

    latest_close = float(primary["close"].iloc[-1])
    latest_date = primary["date"].iloc[-1].strftime("%Y-%m-%d")

    # COMEX 折合 CNY/克
    latest_comex_usd = float(comex["close"].iloc[-1])
    comex_cny_g = latest_comex_usd * latest_usdcny / TROY_OZ_TO_GRAM

    print(f"\n  {primary_label} 最新收盘: {latest_close:.2f} 元/克  ({latest_date})")
    if source == "shfe":
        print(f"  COMEX 折合:       {comex_cny_g:.2f} 元/克  (${latest_comex_usd:.2f} x {latest_usdcny:.4f} / {TROY_OZ_TO_GRAM})")
        print(f"  内外盘价差:       {latest_close - comex_cny_g:+.2f} 元/克")

    # ── 2. 跨市场信号调整 ────────────────────────────────────────────
    adjusted = primary[["date", "close"]].copy()
    if not skip_cross_market:
        print(f"\n  [计算] 跨市场信号调整 ...")
        cross = fetch_cross_market()
        adjustment = compute_cross_market_adjustment(shfe, comex, usdcny, cross)
        # adjustment 长度对齐 shfe, 需对齐 primary
        if len(adjustment) == len(primary):
            adjusted["close"] = primary["close"] + adjustment
            adj_mean = adjustment.tail(20).mean()
            adj_std = adjustment.tail(20).std()
            print(f"         近20日调整均值: {adj_mean:+.2f} 元/克, 标准差: {adj_std:.2f}")
        else:
            print("         跨市场数据对齐失败, 使用原始数据")
    else:
        print("\n  [跳过] 跨市场信号调整")

    # ── 3. 回测 ──────────────────────────────────────────────────────
    if not skip_backtest:
        print("\n" + "-" * 72)
        print(f"  回测摘要 ({primary_label}, stride={backtest_stride}, lookback={lookback}, horizon={backtest_horizon})")
        print("-" * 72)
        bt = rolling_backtest(primary[["date", "close"]], lookback=lookback,
                              max_horizon=backtest_horizon, stride=backtest_stride)
        if not bt.empty:
            metrics = compute_metrics(bt)
            print("\n" + metrics.to_string(index=False))
        else:
            print("  (回测无有效数据)")
    else:
        print("\n  [跳过] 回测")

    # ── 4. 逐日预测 ──────────────────────────────────────────────────
    last_date = primary["date"].iloc[-1]
    future_dates = pd.bdate_range(last_date + pd.Timedelta(days=1), target_end)

    if len(future_dates) == 0:
        print("\n  无未来交易日需要预测")
        return pd.DataFrame()

    print("\n" + "-" * 72)
    print(f"  逐日预测 ({future_dates[0].date()} ~ {future_dates[-1].date()}, 16:00 收盘)")
    print("-" * 72)

    forecast = sequential_forecast(adjusted, future_dates, lookback=lookback)

    if not forecast.empty:
        print()
        print(format_forecast(forecast, latest_close))
    else:
        print("  (无预测结果)")

    # ── 5. 完成 ──────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  分析完成")
    print("=" * 72)

    return forecast


def _parse_args():
    """解析命令行参数, 支持 agent/cron 调用."""
    import argparse
    parser = argparse.ArgumentParser(
        description="黄金价格预测工具 (CNY/克)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认: SHFE AU, 预测到 2026-04-03, 含回测
  python run_gold_analysis.py

  # 仅预测, 跳过回测 (快速模式, ~30秒)
  python run_gold_analysis.py --skip-backtest

  # 使用 COMEX 数据源, 预测到指定日期
  python run_gold_analysis.py --source comex --target-end 2026-04-10

  # 调整回测粒度 (更细 stride=5, 更长 horizon=10)
  python run_gold_analysis.py --backtest-stride 5 --backtest-horizon 10

  # 快速预测: 跳过回测和跨市场信号
  python run_gold_analysis.py --skip-backtest --skip-cross-market
""",
    )
    parser.add_argument(
        "--source", default="shfe", choices=["shfe", "comex"],
        help="数据源: shfe=上期所黄金主力(默认), comex=纽约商品交易所",
    )
    parser.add_argument(
        "--target-end", default="2026-04-03",
        help="预测截止日期 YYYY-MM-DD (默认 2026-04-03)",
    )
    parser.add_argument(
        "--lookback", type=int, default=240,
        help="模型训练窗口大小 (默认 240)",
    )
    parser.add_argument(
        "--backtest-stride", type=int, default=10,
        help="回测步长, 越大越快 (默认 10)",
    )
    parser.add_argument(
        "--backtest-horizon", type=int, default=5,
        help="回测最大预测天数 (默认 5)",
    )
    parser.add_argument(
        "--skip-backtest", action="store_true",
        help="跳过回测, 仅输出预测 (快速模式)",
    )
    parser.add_argument(
        "--skip-cross-market", action="store_true",
        help="跳过跨市场信号调整",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    forecast = main(
        source=args.source,
        target_end=args.target_end,
        lookback=args.lookback,
        backtest_stride=args.backtest_stride,
        backtest_horizon=args.backtest_horizon,
        skip_backtest=args.skip_backtest,
        skip_cross_market=args.skip_cross_market,
    )
