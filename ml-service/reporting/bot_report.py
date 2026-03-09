from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from loguru import logger

from data_collector import get_gold_market_collector
from models.predictor import run_price_prediction

COLOR_MAP = {
    "actual": "#1677ff",
    "forecast": "#fa8c16",
    "SHFE_AU_MAIN": "#f5222d",
    "COMEX": "#1677ff",
    "LBMA_SPOT": "#13c2c2",
    "US_ETF": "#722ed1",
    "DAY": "#13c2c2",
    "NIGHT": "#fa541c",
}


def _display_metric(value: Any, decimals: int = 4) -> str:
    if value is None:
        return "--"
    return str(round(float(value), decimals))


def _build_assessment(latest_price: float | None, forecast_frame: pd.DataFrame, metrics: Dict[str, Any]) -> Dict[str, Any]:
    t1_forecast = None
    t1_gap_pct = None
    if latest_price and not forecast_frame.empty:
        t1_forecast = float(forecast_frame.iloc[0]["close"])
        t1_gap_pct = (t1_forecast / latest_price - 1) * 100

    mape = metrics.get("mape")
    if t1_gap_pct is None:
        risk_level = "UNKNOWN"
        summary = "预测结果不足，无法完成模型评估。"
    else:
        abs_gap = abs(t1_gap_pct)
        if abs_gap >= 5:
            risk_level = "AGGRESSIVE"
            summary = "模型当前预测偏激进，T+1 相对最新价偏离较大，预测值仅供参考。"
        elif abs_gap >= 2:
            risk_level = "ELEVATED"
            summary = "模型当前预测存在一定进攻性，建议结合人工判断使用。"
        else:
            risk_level = "BALANCED"
            summary = "模型当前预测相对平衡，但仍需结合市场波动理解。"

    return {
        "latest_price": latest_price,
        "t1_forecast": round(t1_forecast, 2) if t1_forecast is not None else None,
        "t1_gap_pct": round(t1_gap_pct, 2) if t1_gap_pct is not None else None,
        "mape": round(float(mape), 4) if mape is not None else None,
        "risk_level": risk_level,
        "summary": summary,
        "note": "MAPE 基于历史回测，不代表当前市场状态下的未来稳定性。",
    }


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False)


def _round_frame(frame: pd.DataFrame, decimals: int = 2) -> pd.DataFrame:
    rounded = frame.copy()
    numeric_cols = rounded.select_dtypes(include=["number"]).columns
    rounded[numeric_cols] = rounded[numeric_cols].round(decimals)
    return rounded


def _save_line_chart(
    path: Path,
    series: Iterable[tuple[str, pd.Series, pd.Series, str, str]],
    title: str,
    ylabel: str,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    has_data = False
    for label, x_values, y_values, color, linestyle in series:
        frame = pd.DataFrame({"x": x_values, "y": y_values}).dropna()
        if frame.empty:
            continue
        has_data = True
        ax.plot(frame["x"], frame["y"], label=label, color=color, linestyle=linestyle, linewidth=2)

    if has_data:
        ax.set_title(title, loc="left", fontsize=14, fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.2)
        ax.legend(loc="best")
        ax.tick_params(axis="x", rotation=30)
    else:
        ax.axis("off")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=14)

    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _save_table_chart(path: Path, frame: pd.DataFrame, title: str) -> None:
    table_frame = frame.fillna("--").astype(str)
    height = max(2.2, 0.45 * (len(table_frame) + 2))
    fig, ax = plt.subplots(figsize=(12, height))
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold")

    table = ax.table(
        cellText=table_frame.values,
        colLabels=table_frame.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#f0f5ff")
            cell.set_text_props(weight="bold")

    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _normalize_compare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    normalized = frame.copy()
    for col in normalized.columns:
        if col == "date":
            continue
        valid = normalized[col].dropna()
        if valid.empty:
            continue
        base = float(valid.iloc[0])
        if abs(base) < 1e-8:
            continue
        normalized[col] = normalized[col] / base * 100
    return normalized


def generate_gold_report_bundle(
    output_dir: str | Path,
    source: str = "SHFE_AU_MAIN",
    horizon: int = 5,
    lookback: int = 240,
    compare_days: int = 180,
    session_days: int = 5,
    session_period: str = "15min",
) -> Dict[str, Any]:
    collector = get_gold_market_collector()
    output_path = _ensure_dir(Path(output_dir).expanduser().resolve())
    generated_at = datetime.now().replace(microsecond=0).isoformat()
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    history_start = (today - timedelta(days=max(compare_days, lookback * 3))).strftime("%Y-%m-%d")
    compare_start = (today - timedelta(days=compare_days)).strftime("%Y-%m-%d")

    history_df = collector.get_kline(source, period="daily", start_date=history_start, end_date=today_str)
    if history_df.empty:
        raise RuntimeError(f"无法获取 {source} 的历史数据，无法生成巡检报告")

    quote = collector.get_latest_quote(source)
    predict_result = run_price_prediction(history_df[["date", "close"]], horizon=horizon, lookback=lookback)
    compare_df = collector.compare_sources(
        period="daily",
        start_date=compare_start,
        end_date=today_str,
        group="ALL",
        session="ALL",
    )
    session_df = collector.get_session_data(source=source, period=session_period, days=session_days)

    history_frame = _round_frame(pd.DataFrame(predict_result["history"]))
    forecast_frame = _round_frame(pd.DataFrame(predict_result["prediction"]))
    compare_frame = _round_frame(compare_df.copy()) if not compare_df.empty else pd.DataFrame(columns=["date"])
    session_frame = _round_frame(session_df[["date", "close", "session"]].copy()) if not session_df.empty else pd.DataFrame(columns=["date", "close", "session"])

    if not history_frame.empty:
        history_frame["date"] = pd.to_datetime(history_frame["date"])
    if not forecast_frame.empty:
        forecast_frame["date"] = pd.to_datetime(forecast_frame["date"])
    if not compare_frame.empty:
        compare_frame["date"] = pd.to_datetime(compare_frame["date"])
    if not session_frame.empty:
        session_frame["date"] = pd.to_datetime(session_frame["date"])

    latest_price = float(quote["price"]) if quote and quote.get("price") is not None else None
    assessment = _build_assessment(latest_price, forecast_frame, predict_result["metrics"])

    summary_frame = pd.DataFrame(
        [
            {"Metric": "Generated At", "Value": generated_at},
            {"Metric": "Source", "Value": source},
            {"Metric": "Latest Price", "Value": round(float(quote.get("price", 0.0)), 2) if quote else "--"},
            {"Metric": "Latest Session", "Value": quote.get("session", "ALL") if quote else "--"},
            {"Metric": "Predict Horizon", "Value": horizon},
            {"Metric": "Lookback", "Value": lookback},
            {"Metric": "MAE", "Value": _display_metric(predict_result["metrics"].get("mae"))},
            {"Metric": "MAPE", "Value": _display_metric(predict_result["metrics"].get("mape"))},
            {"Metric": "T+1 Forecast", "Value": round(float(forecast_frame.iloc[0]["close"]), 2) if not forecast_frame.empty else "--"},
            {"Metric": "T+N Forecast", "Value": round(float(forecast_frame.iloc[-1]["close"]), 2) if not forecast_frame.empty else "--"},
            {"Metric": "T+1 Gap %", "Value": _display_metric(assessment["t1_gap_pct"], 2)},
            {"Metric": "Assessment", "Value": assessment["risk_level"]},
        ]
    )

    prediction_chart = output_path / "gold_prediction.png"
    compare_chart = output_path / "gold_compare.png"
    session_chart = output_path / "gold_session.png"
    summary_table_chart = output_path / "gold_summary_table.png"
    forecast_table_chart = output_path / "gold_forecast_table.png"

    history_tail = history_frame.tail(min(len(history_frame), 60)).copy()
    _save_line_chart(
        prediction_chart,
        [
            ("Actual", history_tail["date"], history_tail["close"], COLOR_MAP["actual"], "-"),
            ("Forecast", forecast_frame["date"], forecast_frame["close"], COLOR_MAP["forecast"], "--"),
        ],
        title="Gold Prediction",
        ylabel="Price",
    )

    normalized_compare = _normalize_compare_frame(compare_frame)
    compare_series = []
    for col in normalized_compare.columns:
        if col == "date":
            continue
        compare_series.append(
            (
                col,
                normalized_compare["date"],
                normalized_compare[col],
                COLOR_MAP.get(col, "#595959"),
                "-",
            )
        )
    _save_line_chart(
        compare_chart,
        compare_series,
        title="Gold Domestic vs Foreign (Base=100)",
        ylabel="Indexed Price",
    )

    session_series = []
    if not session_frame.empty:
        for session_name in ["DAY", "NIGHT"]:
            current = session_frame[session_frame["session"] == session_name]
            session_series.append(
                (
                    session_name,
                    current["date"],
                    current["close"],
                    COLOR_MAP[session_name],
                    "-",
                )
            )
    _save_line_chart(
        session_chart,
        session_series,
        title=f"Gold Session Trend ({session_period})",
        ylabel="Price",
    )

    _save_table_chart(summary_table_chart, summary_frame, title="Gold Summary")
    _save_table_chart(
        forecast_table_chart,
        _round_frame(forecast_frame.rename(columns={"date": "Date", "close": "Forecast Close"})),
        title="Gold Forecast Table",
    )

    quote_payload = {
        "generated_at": generated_at,
        "source": source,
        "quote": quote,
    }
    prediction_payload = {
        "generated_at": generated_at,
        "source": source,
        "quote": quote,
        "prediction": predict_result,
        "assessment": assessment,
    }

    _write_json(output_path / "gold_quote.json", quote_payload)
    _write_json(output_path / "gold_prediction.json", prediction_payload)
    _write_csv(output_path / "gold_history.csv", _round_frame(history_frame.assign(date=history_frame["date"].dt.strftime("%Y-%m-%d"))))
    _write_csv(output_path / "gold_forecast.csv", _round_frame(forecast_frame.assign(date=forecast_frame["date"].dt.strftime("%Y-%m-%d"))))

    compare_output = compare_frame.copy()
    if not compare_output.empty:
        compare_output["date"] = compare_output["date"].dt.strftime("%Y-%m-%d")
    _write_csv(output_path / "gold_compare.csv", compare_output)

    session_output = session_frame.copy()
    if not session_output.empty:
        session_output["date"] = session_output["date"].dt.strftime("%Y-%m-%d %H:%M")
    _write_csv(output_path / "gold_session.csv", session_output)

    report_lines = [
        "# 黄金巡检报告",
        "",
        f"- 生成时间: {generated_at}",
        f"- 数据源: {source}",
        f"- 最新价格: {quote.get('price', '--') if quote else '--'}",
        f"- 最新时段: {quote.get('session', '--') if quote else '--'}",
        f"- 预测步长: {horizon}",
        "",
        "## 预测摘要",
        "",
        f"- MAE: {_display_metric(predict_result['metrics'].get('mae'))}",
        f"- MAPE: {_display_metric(predict_result['metrics'].get('mape'))}",
        f"- T+1 预测: {round(float(forecast_frame.iloc[0]['close']), 2) if not forecast_frame.empty else '--'}",
        f"- T+N 预测: {round(float(forecast_frame.iloc[-1]['close']), 2) if not forecast_frame.empty else '--'}",
        "",
        "## 模型评估",
        "",
        f"- T+1 相对最新价偏离: {_display_metric(assessment['t1_gap_pct'], 2)}%",
        f"- 评估结论: {assessment['summary']}",
        f"- 说明: {assessment['note']}",
        "",
        "## 产出文件",
        "",
        "- manifest.json",
        "- gold_quote.json",
        "- gold_prediction.json",
        "- gold_history.csv",
        "- gold_forecast.csv",
        "- gold_compare.csv",
        "- gold_session.csv",
        "- gold_prediction.png",
        "- gold_compare.png",
        "- gold_session.png",
        "- gold_summary_table.png",
        "- gold_forecast_table.png",
    ]
    (output_path / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    manifest = {
        "generated_at": generated_at,
        "mode": "bot_report",
        "source": source,
        "quote": quote,
        "metrics": predict_result["metrics"],
        "assessment": assessment,
        "files": {
            "manifest_json": "manifest.json",
            "report_markdown": "report.md",
            "quote_json": "gold_quote.json",
            "prediction_json": "gold_prediction.json",
            "history_csv": "gold_history.csv",
            "forecast_csv": "gold_forecast.csv",
            "compare_csv": "gold_compare.csv",
            "session_csv": "gold_session.csv",
            "prediction_chart": prediction_chart.name,
            "compare_chart": compare_chart.name,
            "session_chart": session_chart.name,
            "summary_table_chart": summary_table_chart.name,
            "forecast_table_chart": forecast_table_chart.name,
        },
    }
    _write_json(output_path / "manifest.json", manifest)

    logger.info(f"黄金巡检报告已生成: {output_path}")
    return manifest
