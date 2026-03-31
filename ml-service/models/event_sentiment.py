"""
Event and sentiment overlay for gold scenario analysis.

This module surveys a small set of news/blog sources, derives heuristic
event-risk features, and builds explainable bull/base/bear scenario paths
without changing the core forecasting logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import csv
import math
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FeedSpec:
    site: str
    source_type: str
    tier: str
    weight: float


DEFAULT_FEEDS: Tuple[FeedSpec, ...] = (
    FeedSpec("reuters.com", "news", "wire", 1.0),
    FeedSpec("bloomberg.com", "news", "wire", 0.95),
    FeedSpec("marketwatch.com", "news", "major", 0.85),
    FeedSpec("cnbc.com", "news", "major", 0.8),
    FeedSpec("kitco.com", "blog", "blog", 0.75),
    FeedSpec("fxstreet.com", "blog", "blog", 0.7),
    FeedSpec("goldseek.com", "blog", "blog", 0.65),
    FeedSpec("investing.com", "blog", "market", 0.7),
)

SOURCE_TIER_MULTIPLIER = {
    "wire": 1.15,
    "major": 1.0,
    "market": 0.82,
    "blog": 0.62,
}


QUERY_TERMS = (
    "gold",
    "tariff",
    "reciprocal tariffs",
    "trade war",
    "Iran",
    "Middle East",
    "oil",
    "DXY",
    "dollar",
    "Treasury yields",
    "Fed",
    "safe haven",
)


PHRASE_RULES: Tuple[Dict[str, Any], ...] = (
    {"phrase": "safe haven", "bull": 1.6, "bucket": "safe_haven"},
    {"phrase": "tariff", "bull": 1.0, "bucket": "policy_risk"},
    {"phrase": "reciprocal tariff", "bull": 1.2, "bucket": "policy_risk"},
    {"phrase": "trade war", "bull": 1.2, "bucket": "policy_risk"},
    {"phrase": "iran", "bull": 1.1, "bucket": "geo_risk"},
    {"phrase": "middle east", "bull": 1.0, "bucket": "geo_risk"},
    {"phrase": "geopolitical", "bull": 0.8, "bucket": "geo_risk"},
    {"phrase": "oil jumps", "bull": 0.5, "bear": 0.3, "bucket": "oil_shock"},
    {"phrase": "oil surge", "bull": 0.5, "bear": 0.3, "bucket": "oil_shock"},
    {"phrase": "oil rises", "bull": 0.3, "bear": 0.2, "bucket": "oil_shock"},
    {"phrase": "central bank buying", "bull": 1.1, "bucket": "structural_support"},
    {"phrase": "profit-taking", "bear": 1.1, "bucket": "sell_the_news"},
    {"phrase": "sell the news", "bear": 1.5, "bucket": "sell_the_news"},
    {"phrase": "ceasefire", "bear": 1.0, "bucket": "geo_relief"},
    {"phrase": "talks", "bear": 0.5, "bucket": "policy_relief"},
    {"phrase": "negotiation", "bear": 0.7, "bucket": "policy_relief"},
    {"phrase": "deal", "bear": 0.4, "bucket": "policy_relief"},
    {"phrase": "dollar rebounds", "bear": 1.4, "bucket": "usd_pressure"},
    {"phrase": "dollar rises", "bear": 1.1, "bucket": "usd_pressure"},
    {"phrase": "dollar stronger", "bear": 1.0, "bucket": "usd_pressure"},
    {"phrase": "dollar weakens", "bull": 0.9, "bucket": "usd_pressure"},
    {"phrase": "yields rise", "bear": 1.2, "bucket": "rate_pressure"},
    {"phrase": "yield rises", "bear": 1.1, "bucket": "rate_pressure"},
    {"phrase": "hawkish", "bear": 0.9, "bucket": "rate_pressure"},
    {"phrase": "rate cuts fade", "bear": 1.0, "bucket": "rate_pressure"},
    {"phrase": "dovish", "bull": 0.7, "bucket": "rate_pressure"},
)


DEFAULT_EVENT_CONTEXT_CSV = Path(__file__).resolve().parents[1] / "data" / "event_context.csv"


def _empty_survey() -> Dict[str, Any]:
    return {
        "articles": [],
        "feature_summary": {
            "news_bull_score": 0.0,
            "news_bear_score": 0.0,
            "blog_bull_score": 0.0,
            "blog_bear_score": 0.0,
            "safe_haven_score": 0.0,
            "policy_risk_score": 0.0,
            "geo_risk_score": 0.0,
            "sell_the_news_score": 0.0,
            "usd_pressure_score": 0.0,
            "rate_pressure_score": 0.0,
            "oil_shock_score": 0.0,
            "structural_support_score": 0.0,
            "policy_relief_score": 0.0,
            "geo_relief_score": 0.0,
            "article_count": 0,
        },
        "top_bull": [],
        "top_bear": [],
    }


def _google_news_rss_url(site: str) -> str:
    query = "(" + " OR ".join(f'"{term}"' for term in QUERY_TERMS) + f') site:{site}'
    return (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )


def _fetch_feed(url: str, timeout: int = 12) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _parse_pub_date(raw_value: Optional[str]) -> Optional[pd.Timestamp]:
    if not raw_value:
        return None
    try:
        return pd.Timestamp(parsedate_to_datetime(raw_value)).tz_convert(None)
    except Exception:
        try:
            return pd.Timestamp(raw_value).tz_localize(None)
        except Exception:
            return None


def _iter_feed_items(xml_bytes: bytes) -> Iterable[Dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        return []

    items: List[Dict[str, Any]] = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date = _parse_pub_date(item.findtext("pubDate"))
        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "published": pub_date,
            }
        )
    return items


def _score_text(text: str) -> Tuple[float, float, Dict[str, float], List[str]]:
    lowered = text.lower()
    bull = 0.0
    bear = 0.0
    buckets: Dict[str, float] = {}
    tags: List[str] = []

    for rule in PHRASE_RULES:
        phrase = rule["phrase"]
        if phrase in lowered:
            tags.append(phrase)
            bull += float(rule.get("bull", 0.0))
            bear += float(rule.get("bear", 0.0))
            bucket = str(rule["bucket"])
            buckets[bucket] = buckets.get(bucket, 0.0) + max(
                float(rule.get("bull", 0.0)),
                float(rule.get("bear", 0.0)),
            )
    return bull, bear, buckets, tags


def _bounded_score(raw_value: float, scale: float) -> float:
    return float(np.tanh(max(raw_value, 0.0) / max(scale, 1e-6)))


def _freshness_weight(published: Optional[pd.Timestamp], now: pd.Timestamp, window_days: int) -> float:
    if published is None:
        return 0.45
    age_days = max((now - published).total_seconds() / 86400.0, 0.0)
    return float(math.exp(-age_days / max(window_days / 2.0, 1.0)))


def _load_event_context(csv_path: str | Path | None) -> List[Dict[str, Any]]:
    if not csv_path:
        return []
    path = Path(csv_path)
    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                event_date = pd.Timestamp(row.get("date"))
            except Exception:
                continue
            rows.append(
                {
                    "date": event_date,
                    "event_name": row.get("event_name", "").strip() or "unnamed_event",
                    "event_type": row.get("event_type", "").strip() or "macro",
                    "pre_bias": float(row.get("pre_bias", row.get("bias", 0.0)) or 0.0),
                    "post_bias": float(row.get("post_bias", row.get("bias", 0.0)) or 0.0),
                    "importance": float(row.get("importance", 1.0) or 1.0),
                    "pre_days": int(float(row.get("pre_days", 0) or 0)),
                    "post_days": int(float(row.get("post_days", 0) or 0)),
                    "sell_the_news_bias": float(row.get("sell_the_news_bias", 0.0) or 0.0),
                    "notes": row.get("notes", "").strip(),
                }
            )
    return rows


def survey_event_sentiment(
    now: pd.Timestamp,
    window_days: int = 7,
    max_items_per_feed: int = 6,
) -> Dict[str, Any]:
    articles: List[Dict[str, Any]] = []
    cutoff = now - pd.Timedelta(days=window_days)
    seen_titles: set[str] = set()

    for spec in DEFAULT_FEEDS:
        try:
            xml_bytes = _fetch_feed(_google_news_rss_url(spec.site))
        except Exception:
            continue

        added = 0
        for item in _iter_feed_items(xml_bytes):
            title = str(item["title"]).strip()
            if not title or title in seen_titles:
                continue
            published = item.get("published")
            if published is not None and published < cutoff:
                continue

            combined_text = f"{title} {item.get('description', '')}"
            bull, bear, buckets, tags = _score_text(combined_text)
            if bull <= 0.0 and bear <= 0.0:
                continue

            freshness = _freshness_weight(published, now, window_days)
            tier_weight = SOURCE_TIER_MULTIPLIER.get(spec.tier, 0.8)
            weight = spec.weight * tier_weight * freshness
            seen_titles.add(title)
            articles.append(
                {
                    "title": title,
                    "link": item.get("link"),
                    "published": published,
                    "site": spec.site,
                    "source_type": spec.source_type,
                    "bull_score": round(bull * weight, 4),
                    "bear_score": round(bear * weight, 4),
                    "weight": round(weight, 4),
                    "tags": tags,
                    "buckets": buckets,
                }
            )
            added += 1
            if added >= max_items_per_feed:
                break

    if not articles:
        return _empty_survey()

    news_bull = sum(a["bull_score"] for a in articles if a["source_type"] == "news")
    news_bear = sum(a["bear_score"] for a in articles if a["source_type"] == "news")
    blog_bull = sum(a["bull_score"] for a in articles if a["source_type"] == "blog")
    blog_bear = sum(a["bear_score"] for a in articles if a["source_type"] == "blog")

    bucket_scores: Dict[str, float] = {
        "safe_haven_score": 0.0,
        "policy_risk_score": 0.0,
        "geo_risk_score": 0.0,
        "sell_the_news_score": 0.0,
        "usd_pressure_score": 0.0,
        "rate_pressure_score": 0.0,
        "oil_shock_score": 0.0,
        "structural_support_score": 0.0,
        "policy_relief_score": 0.0,
        "geo_relief_score": 0.0,
    }
    bucket_mapping = {
        "safe_haven": "safe_haven_score",
        "policy_risk": "policy_risk_score",
        "geo_risk": "geo_risk_score",
        "sell_the_news": "sell_the_news_score",
        "usd_pressure": "usd_pressure_score",
        "rate_pressure": "rate_pressure_score",
        "oil_shock": "oil_shock_score",
        "structural_support": "structural_support_score",
        "policy_relief": "policy_relief_score",
        "geo_relief": "geo_relief_score",
    }
    for article in articles:
        for bucket, score in article["buckets"].items():
            mapped = bucket_mapping.get(bucket)
            if mapped:
                bucket_scores[mapped] += float(score) * float(article["weight"])

    top_bull = sorted(articles, key=lambda row: row["bull_score"] - row["bear_score"], reverse=True)[:3]
    top_bear = sorted(articles, key=lambda row: row["bear_score"] - row["bull_score"], reverse=True)[:3]

    feature_summary = {
        "news_bull_score": round(_bounded_score(news_bull, 8.0), 4),
        "news_bear_score": round(_bounded_score(news_bear, 6.0), 4),
        "blog_bull_score": round(_bounded_score(blog_bull, 5.0), 4),
        "blog_bear_score": round(_bounded_score(blog_bear, 4.0), 4),
        "article_count": len(articles),
    }
    feature_summary.update(
        {
            key: round(_bounded_score(value, 4.0 if "risk" in key else 3.0), 4)
            for key, value in bucket_scores.items()
        }
    )

    return {
        "articles": articles,
        "feature_summary": feature_summary,
        "top_bull": top_bull,
        "top_bear": top_bear,
    }


def _calibrate_event_overlay(
    daily_df: pd.DataFrame,
    events: Sequence[Dict[str, Any]],
    analysis_date: pd.Timestamp,
) -> Dict[str, float]:
    daily_sorted = daily_df.sort_values("date").reset_index(drop=True).copy()
    daily_sorted["date"] = pd.to_datetime(daily_sorted["date"])
    daily_sorted["close"] = pd.to_numeric(daily_sorted["close"], errors="coerce")
    closes = daily_sorted["close"].dropna().astype(float)
    rets = closes.pct_change().dropna()
    recent_rets = rets.tail(min(len(rets), 60))

    recent_abs = recent_rets.abs()
    median_abs = float(recent_abs.median()) if not recent_abs.empty else 0.006
    p75_abs = float(recent_abs.quantile(0.75)) if not recent_abs.empty else 0.009

    historical_pre: List[float] = []
    historical_post: List[float] = []
    historical_sell: List[float] = []

    if not daily_sorted.empty:
        date_index = {pd.Timestamp(row["date"]).normalize(): idx for idx, row in daily_sorted.iterrows()}
        for event in events:
            event_day = pd.Timestamp(event["date"]).normalize()
            if event_day >= analysis_date.normalize():
                continue
            idx = date_index.get(event_day)
            if idx is None:
                continue

            pre_days = int(event.get("pre_days", 0))
            post_days = int(event.get("post_days", 0))
            if pre_days > 0 and idx - pre_days >= 0:
                pre_ret = float(daily_sorted.iloc[idx]["close"] / daily_sorted.iloc[idx - pre_days]["close"] - 1)
                historical_pre.append(abs(pre_ret) / max(pre_days, 1))
            if post_days > 0 and idx + post_days < len(daily_sorted):
                post_ret = float(daily_sorted.iloc[idx + post_days]["close"] / daily_sorted.iloc[idx]["close"] - 1)
                historical_post.append(abs(post_ret) / max(post_days, 1))
                if float(event.get("sell_the_news_bias", 0.0)) < 0 or float(event.get("post_bias", 0.0)) < 0:
                    if post_ret < 0:
                        historical_sell.append(abs(post_ret))

    pre_scale = float(np.median(historical_pre)) if historical_pre else p75_abs
    post_scale = float(np.median(historical_post)) if historical_post else p75_abs * 0.9
    sell_scale = float(np.median(historical_sell)) if historical_sell else median_abs * 1.25

    return {
        "median_abs_return": round(median_abs, 6),
        "p75_abs_return": round(p75_abs, 6),
        "pre_event_scale": round(max(pre_scale, 0.004), 6),
        "post_event_scale": round(max(post_scale, 0.004), 6),
        "sell_the_news_scale": round(max(sell_scale, 0.0035), 6),
    }


def _event_calendar_for_target(
    events: Sequence[Dict[str, Any]],
    analysis_date: pd.Timestamp,
    target_date: pd.Timestamp,
) -> Dict[str, Any]:
    pre_event_score = 0.0
    post_event_score = 0.0
    sell_the_news_score = 0.0
    active_events: List[Dict[str, Any]] = []
    for event in events:
        start = event["date"] - pd.Timedelta(days=event["pre_days"])
        end = event["date"] + pd.Timedelta(days=event["post_days"])
        if not (start <= target_date <= end):
            continue

        event_date = pd.Timestamp(event["date"])
        importance = float(event["importance"])
        if target_date <= event_date:
            days_to_event = max((event_date - target_date).days, 0)
            pre_span = max(int(event["pre_days"]), 1)
            distance_weight = math.exp(-days_to_event / max(pre_span / 1.5, 1.0))
            pre_event_score += float(event["pre_bias"]) * importance * distance_weight
            phase = "pre"
        else:
            days_after_event = max((target_date - event_date).days, 0)
            post_span = max(int(event["post_days"]), 1)
            distance_weight = math.exp(-days_after_event / max(post_span / 1.2, 1.0))
            post_event_score += float(event["post_bias"]) * importance * distance_weight
            sell_bias = float(event.get("sell_the_news_bias", 0.0))
            if sell_bias != 0.0:
                sell_the_news_score += abs(sell_bias) * importance * distance_weight
            phase = "post"

        active_events.append(
            {
                "event_name": event["event_name"],
                "event_type": event["event_type"],
                "event_date": event["date"].strftime("%Y-%m-%d"),
                "phase": phase,
                "pre_bias": event["pre_bias"],
                "post_bias": event["post_bias"],
                "importance": event["importance"],
                "notes": event["notes"],
            }
        )

    return {
        "calendar_score": round(pre_event_score + post_event_score, 4),
        "pre_event_score": round(pre_event_score, 4),
        "post_event_score": round(post_event_score, 4),
        "sell_the_news_score": round(sell_the_news_score, 4),
        "active_events": active_events,
        "days_from_analysis": int((target_date - analysis_date).days),
    }


def _regime_width(regime: str) -> float:
    return {
        "low": 0.004,
        "normal": 0.007,
        "high": 0.012,
        "extreme": 0.018,
    }.get(regime, 0.01)


def build_event_scenario_bundle(
    base_predictions: Sequence[Dict[str, Any]],
    analysis_date: pd.Timestamp,
    regime: str,
    daily_df: pd.DataFrame,
    event_context_csv: str | Path | None = None,
    window_days: int = 7,
    use_live_survey: bool = True,
    survey_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = pd.Timestamp(analysis_date)
    if survey_override is not None:
        survey = survey_override
    elif use_live_survey:
        survey = survey_event_sentiment(now=now, window_days=window_days)
    else:
        survey = _empty_survey()
    events = _load_event_context(event_context_csv or DEFAULT_EVENT_CONTEXT_CSV)
    summary = survey["feature_summary"]
    calibration = _calibrate_event_overlay(daily_df=daily_df, events=events, analysis_date=now)

    bull_total = float(summary.get("news_bull_score", 0.0) + summary.get("blog_bull_score", 0.0))
    bear_total = float(summary.get("news_bear_score", 0.0) + summary.get("blog_bear_score", 0.0))
    bull_strength = min(max(bull_total, 0.0), 1.0)
    bear_strength = min(max(bear_total, 0.0), 1.0)
    intensity = min((bull_strength + bear_strength) / 1.8, 1.0)

    usd_pressure = min(float(summary.get("usd_pressure_score", 0.0)), 1.0)
    sell_news = min(float(summary.get("sell_the_news_score", 0.0)), 1.0)
    geo_risk = min(float(summary.get("geo_risk_score", 0.0)), 1.0)
    policy_risk = min(float(summary.get("policy_risk_score", 0.0)), 1.0)
    safe_haven = min(float(summary.get("safe_haven_score", 0.0)), 1.0)
    rate_pressure = min(float(summary.get("rate_pressure_score", 0.0)), 1.0)

    scenario_rows: List[Dict[str, Any]] = []
    for idx, pred in enumerate(base_predictions, start=1):
        target_date = pd.Timestamp(pred["date"])
        base_close = float(pred["close"])
        base_low = float(pred.get("range_low", base_close))
        base_high = float(pred.get("range_high", base_close))
        calendar = _event_calendar_for_target(events, now, target_date)
        calendar_bias = float(calendar["calendar_score"])
        pre_event_score = max(float(calendar["pre_event_score"]), 0.0)
        post_event_score = max(-float(calendar["post_event_score"]), 0.0)
        sell_the_news_score = max(float(calendar["sell_the_news_score"]), 0.0)
        horizon_multiplier = min(1.28, 1.0 + 0.06 * (idx - 1))
        width = max(_regime_width(regime), calibration["median_abs_return"]) * horizon_multiplier
        width *= (1.0 + 0.35 * intensity)
        base_up_width = max((base_high - base_close) / max(base_close, 1e-8), width)
        base_down_width = max((base_close - base_low) / max(base_close, 1e-8), width)

        bull_signal = bull_strength * 0.35 + safe_haven * 0.15 + geo_risk * 0.25 + policy_risk * 0.15 + pre_event_score * 0.10
        bear_signal = bear_strength * 0.20 + usd_pressure * 0.25 + rate_pressure * 0.15 + post_event_score * 0.20 + sell_news * 0.10 + sell_the_news_score * 0.10

        bull_extra = calibration["pre_event_scale"] * min(bull_signal, 1.8)
        bear_extra = calibration["post_event_scale"] * min(bear_signal, 1.8)
        bear_extra += calibration["sell_the_news_scale"] * min(sell_the_news_score + sell_news, 1.2)
        bull_extra += calibration["median_abs_return"] * max(calendar_bias, 0.0) * 0.35
        bear_extra += calibration["median_abs_return"] * max(-calendar_bias, 0.0) * 0.35

        bull_boost = float(np.clip(base_up_width + bull_extra, base_up_width, 0.06))
        bear_boost = float(np.clip(base_down_width + bear_extra, base_down_width, 0.06))

        bull_close = base_close * (1 + bull_boost)
        bear_close = base_close * (1 - bear_boost)

        bull_driver_parts: List[str] = []
        bear_driver_parts: List[str] = []
        if safe_haven > 0.2:
            bull_driver_parts.append("避险情绪")
        if geo_risk > 0.2:
            bull_driver_parts.append("地缘风险")
        if policy_risk > 0.2:
            bull_driver_parts.append("政策不确定性")
        if pre_event_score > 0.15:
            bull_driver_parts.append("事件窗口前置")

        if sell_news > 0.2 or sell_the_news_score > 0.15:
            bear_driver_parts.append("卖事实风险")
        if usd_pressure > 0.2:
            bear_driver_parts.append("美元反弹")
        if rate_pressure > 0.2:
            bear_driver_parts.append("利率压力")
        if post_event_score > 0.15:
            bear_driver_parts.append("事件落地回吐")

        row = {
            "date": target_date.strftime("%Y-%m-%d"),
            "bear_close": round(float(bear_close), 2),
            "base_close": round(float(base_close), 2),
            "bull_close": round(float(bull_close), 2),
            "base_low": round(float(base_low), 2),
            "base_high": round(float(base_high), 2),
            "bull_driver": "、".join(bull_driver_parts) or "模型中枢上方波动",
            "bear_driver": "、".join(bear_driver_parts) or "模型中枢下方波动",
            "calendar_score": round(calendar_bias, 3),
            "active_events": calendar["active_events"],
        }
        scenario_rows.append(row)

    top_pathways: List[str] = []
    if summary.get("safe_haven_score", 0.0) > 0.8:
        top_pathways.append("主流新闻中的避险叙事偏强，提升 bull 上沿。")
    if summary.get("policy_risk_score", 0.0) > 0.8:
        top_pathways.append("政策/关税类报道偏多，事件窗口前的上行弹性被放大。")
    if summary.get("geo_risk_score", 0.0) > 0.8:
        top_pathways.append("地缘风险新闻较密集，模型将其映射为短线风险溢价。")
    if summary.get("sell_the_news_score", 0.0) > 0.8:
        top_pathways.append("近期标题中出现较多获利了结/兑现类表达，bear 路径下调更深。")
    if summary.get("usd_pressure_score", 0.0) > 0.8:
        top_pathways.append("美元反弹类叙事偏强，bear 路径会额外考虑压制。")
    if not top_pathways:
        top_pathways.append("近一周事件情绪信号偏弱，bull/bear 主要由波动率区间展开。")

    return {
        "feature_summary": summary,
        "top_bull": survey["top_bull"],
        "top_bear": survey["top_bear"],
        "scenario_rows": scenario_rows,
        "pathways": top_pathways,
        "article_count": int(summary.get("article_count", 0)),
        "calibration": calibration,
    }
