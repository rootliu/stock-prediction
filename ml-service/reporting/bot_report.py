from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger

from data_collector import get_gold_market_collector
from models.predictor import run_price_prediction
from reporting.external_gold_consensus import build_external_gold_curve_comparison

plt.rcParams["font.sans-serif"] = [
    "Hiragino Sans GB",
    "STHeiti",
    "Arial Unicode MS",
    "Arial Unicode",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False

COLOR_MAP = {
    "actual": "#1677ff",
    "forecast": "#fa8c16",
    "external_main": "#a35a00",
    "internal_model": "#fa8c16",
    "blended_curve": "#2f855a",
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


def _format_timestamp_value(value: Any) -> str:
    ts = pd.Timestamp(value)
    if ts.hour == 0 and ts.minute == 0 and ts.second == 0:
        return ts.strftime("%Y-%m-%d")
    return ts.strftime("%Y-%m-%d %H:%M")


def _format_timestamp_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).map(_format_timestamp_value)


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


def _build_deviation_summary(comparison_frame: pd.DataFrame) -> Dict[str, Any]:
    if comparison_frame.empty:
        return {
            "t1_label": "UNKNOWN",
            "max_abs_deviation_pct": None,
            "dominant_label": "UNKNOWN",
        }

    deviation_series = comparison_frame["Internal vs External %"].astype(float)
    labels = comparison_frame["Deviation Label"].astype(str)
    return {
        "t1_label": labels.iloc[0],
        "max_abs_deviation_pct": round(float(deviation_series.abs().max()), 2),
        "dominant_label": labels.value_counts().idxmax(),
    }


def _resample_close_to_four_hour(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["date", "close"])

    resampled = (
        frame.sort_values("date")
        .set_index("date")
        .resample("4h", label="right", closed="right")
        .agg({"close": "last"})
        .dropna(subset=["close"])
        .reset_index()
    )
    return resampled[["date", "close"]]


def _build_four_hour_forecast_frame(
    latest_price: float,
    forecast_frame: pd.DataFrame,
    reference_time: pd.Timestamp,
    step_hours: int = 4,
) -> pd.DataFrame:
    if forecast_frame.empty:
        return pd.DataFrame(columns=["date", "close"])

    horizon_days = len(forecast_frame)
    anchor_offsets = np.arange(0, horizon_days + 1) * 24
    anchor_values = np.concatenate(([latest_price], forecast_frame["close"].astype(float).values))
    target_offsets = np.arange(step_hours, horizon_days * 24 + step_hours, step_hours)
    target_values = np.interp(target_offsets, anchor_offsets, anchor_values)
    target_dates = [reference_time + pd.Timedelta(hours=int(offset)) for offset in target_offsets]
    return pd.DataFrame({"date": target_dates, "close": np.round(target_values, 2)})


def _resolve_prediction_source_frame(
    collector: Any,
    source: str,
    lookback: int,
    end_date: str,
) -> tuple[pd.DataFrame, str, int, int | None]:
    source_meta = next(
        (item for item in collector.get_sources("ALL") if item["source"] == source.upper()),
        {},
    )
    if source_meta.get("supports_intraday"):
        intraday_start = (datetime.now() - timedelta(days=max(lookback * 3, 120))).strftime("%Y-%m-%d")
        intraday_df = collector.get_kline(
            source,
            period="4h",
            start_date=intraday_start,
            end_date=end_date,
            session="ALL",
        )
        if not intraday_df.empty and len(intraday_df) >= 80:
            resolved_lookback = min(lookback, max(len(intraday_df) - 6, 60))
            return intraday_df[["date", "close"]].copy(), "4h", resolved_lookback, 4

    daily_start = (datetime.now() - timedelta(days=max(180, lookback * 3))).strftime("%Y-%m-%d")
    daily_df = collector.get_kline(source, period="daily", start_date=daily_start, end_date=end_date)
    return daily_df[["date", "close"]].copy(), "daily", lookback, None


def generate_gold_report_bundle(
    output_dir: str | Path,
    source: str = "SHFE_AU_MAIN",
    horizon: int = 5,
    lookback: int = 240,
    predict_model: str = "ensemble",
    compare_days: int = 180,
    session_days: int = 5,
    session_period: str = "4h",
) -> Dict[str, Any]:
    collector = get_gold_market_collector()
    output_path = _ensure_dir(Path(output_dir).expanduser().resolve())
    generated_at = datetime.now().replace(microsecond=0).isoformat()
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    history_start = (today - timedelta(days=max(compare_days, lookback * 3))).strftime("%Y-%m-%d")
    compare_start = (today - timedelta(days=compare_days)).strftime("%Y-%m-%d")
    intraday_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")

    predict_input_df, predict_period, resolved_lookback, future_step_hours = _resolve_prediction_source_frame(
        collector=collector,
        source=source,
        lookback=lookback,
        end_date=today_str,
    )
    if predict_input_df.empty:
        raise RuntimeError(f"无法获取 {source} 的历史数据，无法生成巡检报告")

    quote = collector.get_latest_quote(source)
    predict_result = run_price_prediction(
        predict_input_df,
        horizon=horizon,
        lookback=resolved_lookback,
        model_type=predict_model,
        use_external_direction=(predict_model == "boosting" and predict_period == "4h"),
        enable_direction_head=(predict_model == "boosting" and predict_period == "4h"),
        enable_bias_correction=(predict_model == "boosting" and predict_period == "4h"),
        future_step_hours=future_step_hours,
    )
    compare_df = collector.compare_sources(
        period="daily",
        start_date=compare_start,
        end_date=today_str,
        group="ALL",
        session="ALL",
    )
    session_df = collector.get_session_data(source=source, period=session_period, days=session_days)
    intraday_context_df = collector.get_kline(source, period="4h", start_date=intraday_start, end_date=today_str, session="ALL")

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
    if latest_price is None and not predict_input_df.empty:
        latest_price = float(predict_input_df.iloc[-1]["close"])
    assessment = _build_assessment(latest_price, forecast_frame, predict_result["metrics"])

    intraday_context_frame = intraday_context_df[["date", "close"]].copy() if not intraday_context_df.empty else pd.DataFrame(columns=["date", "close"])
    if intraday_context_frame.empty and not history_frame.empty:
        intraday_context_frame = history_frame.tail(7)[["date", "close"]].copy()

    reference_time = pd.to_datetime(intraday_context_frame["date"]).max() if not intraday_context_frame.empty else pd.Timestamp(today.replace(minute=0, second=0, microsecond=0))
    if predict_period == "4h":
        forecast_4h_frame = forecast_frame.copy()
        if not forecast_4h_frame.empty:
            forecast_4h_frame["date"] = pd.to_datetime(forecast_4h_frame["date"])
    else:
        forecast_4h_frame = _build_four_hour_forecast_frame(
            latest_price=latest_price,
            forecast_frame=forecast_frame,
            reference_time=reference_time,
        )

    prediction_chart = output_path / "gold_prediction.png"
    compare_chart = output_path / "gold_compare.png"
    session_chart = output_path / "gold_session.png"
    curve_chart = output_path / "gold_curve_comparison.png"
    summary_table_chart = output_path / "gold_summary_table.png"
    forecast_table_chart = output_path / "gold_forecast_table.png"
    survey_table_chart = output_path / "gold_external_survey_table.png"
    curve_table_chart = output_path / "gold_curve_comparison_table.png"

    curve_bundle = build_external_gold_curve_comparison(
        latest_price=latest_price,
        forecast_frame=forecast_4h_frame,
        reference_time=reference_time,
        horizon_days=float(len(forecast_frame)),
    )
    survey_frame = _round_frame(curve_bundle["survey_frame"])
    curve_compare_frame = _round_frame(curve_bundle["comparison_frame"])
    curve_frame = _round_frame(curve_bundle["curve_frame"])
    external_summary = curve_bundle["summary"]
    deviation_summary = _build_deviation_summary(curve_compare_frame)

    summary_frame = pd.DataFrame(
        [
            {"Metric": "Generated At", "Value": generated_at},
            {"Metric": "Source", "Value": source},
            {"Metric": "Latest Price", "Value": round(float(latest_price), 2) if latest_price is not None else "--"},
            {"Metric": "Latest Session", "Value": quote.get("session", "ALL") if quote else "--"},
            {"Metric": "Predict Horizon", "Value": horizon},
            {"Metric": "Predict Period", "Value": predict_period},
            {"Metric": "Predict Model", "Value": predict_model},
            {"Metric": "Lookback", "Value": lookback},
            {"Metric": "Resolved Lookback", "Value": resolved_lookback},
            {"Metric": "MAE", "Value": _display_metric(predict_result["metrics"].get("mae"))},
            {"Metric": "MAPE", "Value": _display_metric(predict_result["metrics"].get("mape"))},
            {"Metric": "T+1 Forecast", "Value": round(float(forecast_frame.iloc[0]["close"]), 2) if not forecast_frame.empty else "--"},
            {"Metric": "T+N Forecast", "Value": round(float(forecast_frame.iloc[-1]["close"]), 2) if not forecast_frame.empty else "--"},
            {"Metric": "T+1 Gap %", "Value": _display_metric(assessment["t1_gap_pct"], 2)},
            {"Metric": "Assessment", "Value": assessment["risk_level"]},
            {"Metric": "Context Window", "Value": "Past 7 days / 4h"},
            {"Metric": "Curve Horizon", "Value": f"Next {int(round(external_summary['horizon_days']))} days / 4h"},
            {"Metric": "External Horizon Return %", "Value": _display_metric(external_summary["external_horizon_return_pct"], 2)},
            {"Metric": "T+1 Deviation Label", "Value": deviation_summary["t1_label"]},
        ]
    )

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
    _save_line_chart(
        curve_chart,
        [
            ("Actual 4H", intraday_context_frame["date"], intraday_context_frame["close"], COLOR_MAP["actual"], "-"),
            ("External Main", pd.to_datetime(curve_frame["date"]), curve_frame["external_main"], COLOR_MAP["external_main"], "-"),
            ("Internal Model", pd.to_datetime(curve_frame["date"]), curve_frame["internal_model"], COLOR_MAP["internal_model"], "--"),
            ("Blended Curve", pd.to_datetime(curve_frame["date"]), curve_frame["blended_curve"], COLOR_MAP["blended_curve"], "-."),
        ],
        title="Gold Past Week + Next 5 Days (4H)",
        ylabel="Price",
    )
    _save_table_chart(
        survey_table_chart,
        survey_frame[["Source", "Published", "Weight", "Bias", "Implied Horizon Return %", "Anchor"]],
        title="External English Site Survey",
    )
    _save_table_chart(
        curve_table_chart,
        curve_compare_frame,
        title="Curve Comparison and Deviation",
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
        "external_consensus": {
            "summary": external_summary,
            "survey": survey_frame.to_dict(orient="records"),
            "comparison": curve_compare_frame.to_dict(orient="records"),
        },
    }

    _write_json(output_path / "gold_quote.json", quote_payload)
    _write_json(output_path / "gold_prediction.json", prediction_payload)
    history_output = history_frame.copy()
    if not history_output.empty:
        history_output["date"] = _format_timestamp_series(history_output["date"])
    _write_csv(output_path / "gold_history.csv", _round_frame(history_output))

    forecast_output = forecast_frame.copy()
    if not forecast_output.empty:
        forecast_output["date"] = _format_timestamp_series(forecast_output["date"])
    _write_csv(output_path / "gold_forecast.csv", _round_frame(forecast_output))

    compare_output = compare_frame.copy()
    if not compare_output.empty:
        compare_output["date"] = compare_output["date"].dt.strftime("%Y-%m-%d")
    _write_csv(output_path / "gold_compare.csv", compare_output)

    session_output = session_frame.copy()
    if not session_output.empty:
        session_output["date"] = session_output["date"].dt.strftime("%Y-%m-%d %H:%M")
    _write_csv(output_path / "gold_session.csv", session_output)
    _write_csv(output_path / "external_gold_survey.csv", survey_frame)
    _write_csv(output_path / "gold_curve_comparison.csv", curve_compare_frame)
    curve_output = pd.merge(
        intraday_context_frame.rename(columns={"close": "actual_4h"}),
        curve_frame.assign(date=pd.to_datetime(curve_frame["date"])),
        on="date",
        how="outer",
    ).sort_values("date")
    curve_output["date"] = curve_output["date"].dt.strftime("%Y-%m-%d %H:%M")
    _write_csv(output_path / "gold_external_main_curve.csv", curve_output)

    report_lines = [
        "# 黄金巡检报告",
        "",
        f"- 生成时间: {generated_at}",
        f"- 数据源: {source}",
        f"- 最新价格: {quote.get('price', '--') if quote else '--'}",
        f"- 最新时段: {quote.get('session', '--') if quote else '--'}",
        f"- 预测步长: {horizon}",
        f"- 预测粒度: {predict_period}",
        f"- 预测模型: {predict_model}",
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
        "## 外部英文网站主曲线",
        "",
        f"- Survey 日期: {external_summary['survey_as_of']}",
        f"- 站点数量: {external_summary['source_count']}",
        f"- 主曲线角色: {external_summary['external_curve_role']}",
        f"- 图像窗口: 过去 7 天实际走势 + 未来 {int(round(external_summary['horizon_days']))} 天预测",
        "- 时间粒度: 4 小时",
        f"- 主曲线区间收益率: {_display_metric(external_summary['external_horizon_return_pct'], 2)}%",
        "- 说明: 外部英文网站曲线作为主曲线，内部模型只作为短期局部修正输入。",
        "",
        "## 曲线对比",
        "",
        f"- T+1 偏离标签: {deviation_summary['t1_label']}",
        f"- 最大绝对偏离: {_display_metric(deviation_summary['max_abs_deviation_pct'], 2)}%",
        f"- 主导偏离标签: {deviation_summary['dominant_label']}",
        "",
        "### 外部 survey 样本",
        "",
    ]
    for row in survey_frame.to_dict(orient="records"):
        report_lines.extend(
            [
                f"- {row['Source']} ({row['Published']}): {row['Bias']}, 区间隐含收益 {row['Implied Horizon Return %']}%, 权重 {row['Weight']}, 锚点 {row['Anchor']}",
                f"  链接: {row['URL']}",
            ]
        )

    report_lines.extend(
        [
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
            "- external_gold_survey.csv",
            "- gold_curve_comparison.csv",
            "- gold_external_main_curve.csv",
            "- gold_prediction.png",
            "- gold_compare.png",
            "- gold_session.png",
            "- gold_curve_comparison.png",
            "- gold_summary_table.png",
            "- gold_forecast_table.png",
            "- gold_external_survey_table.png",
            "- gold_curve_comparison_table.png",
        ]
    )
    (output_path / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    manifest = {
        "generated_at": generated_at,
        "mode": "bot_report",
        "source": source,
        "quote": quote,
        "metrics": predict_result["metrics"],
        "assessment": assessment,
        "external_consensus": {
            "summary": external_summary,
            "deviation": deviation_summary,
        },
        "files": {
            "manifest_json": "manifest.json",
            "report_markdown": "report.md",
            "quote_json": "gold_quote.json",
            "prediction_json": "gold_prediction.json",
            "history_csv": "gold_history.csv",
            "forecast_csv": "gold_forecast.csv",
            "compare_csv": "gold_compare.csv",
            "session_csv": "gold_session.csv",
            "external_survey_csv": "external_gold_survey.csv",
            "curve_comparison_csv": "gold_curve_comparison.csv",
            "external_curve_csv": "gold_external_main_curve.csv",
            "prediction_chart": prediction_chart.name,
            "compare_chart": compare_chart.name,
            "session_chart": session_chart.name,
            "curve_chart": curve_chart.name,
            "summary_table_chart": summary_table_chart.name,
            "forecast_table_chart": forecast_table_chart.name,
            "survey_table_chart": survey_table_chart.name,
            "curve_table_chart": curve_table_chart.name,
        },
    }
    _write_json(output_path / "manifest.json", manifest)

    logger.info(f"黄金巡检报告已生成: {output_path}")
    return manifest
