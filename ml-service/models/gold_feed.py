"""Closed-session inputs for both live gold jobs. Never substitute a different instrument."""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests


class FeedError(RuntimeError):
    pass


ROOT = Path(__file__).resolve().parents[2]
SHFE_BREAKS = (("01-01", "01-03"), ("02-15", "02-23"), ("04-04", "04-06"),
               ("05-01", "05-05"), ("06-19", "06-21"), ("09-25", "09-27"), ("10-01", "10-07"))
US_INDEX_BREAKS = set("01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25".split())
FIELDS = {"shfe": ["open", "high", "low", "close", "volume"], "comex": ["close"],
          "usdcny": ["usdcny"], "cross": ["dxy", "us10y", "vix"]}
SYMBOLS = {"comex": {"close": "GC=F"}, "usdcny": {"usdcny": "USDCNY=X"},
           "cross": {"dxy": "DX-Y.NYB", "us10y": "^TNX", "vix": "^VIX"}}


def cache_dir():
    return Path(os.environ.get("GOLD_CACHE_DIR", ROOT / ".cache/gold"))


def session(day, market):
    if day.year != 2026:
        raise FeedError(f"No verified live calendar for {day.year}: {market}")
    md = day.strftime("%m-%d")
    if day.weekday() >= 5:
        return False
    if market == "shfe":
        return not any(a <= md <= b for a, b in SHFE_BREAKS)
    if market in ("vix", "us10y"):
        return md not in US_INDEX_BREAKS
    # A shortened futures/FX session is not an equity-market closure. If an
    # uncertain weekday has no completed quote, abstain rather than bless stale data.
    return md not in ("01-01", "12-25")


def expected(now, market):
    local = pd.Timestamp(now).tz_convert("Asia/Shanghai")
    shift = int(local.hour < 16) if market == "shfe" else 1 + int(local.hour < 8)
    day = local.tz_localize(None).normalize() - pd.Timedelta(days=shift)
    while not session(day, market):
        day -= pd.Timedelta(days=1)
    return day


def target_after(day, n=3):
    if not isinstance(n, int) or n < 1:
        raise ValueError("horizon must be a positive integer")
    day = pd.Timestamp(day).normalize()
    while n:
        day += pd.Timedelta(days=1)
        n -= int(session(day, "shfe"))
    return day.strftime("%Y-%m-%d")


def chart(name):
    frames = []
    for col, symbol in SYMBOLS[name].items():
        response = requests.get("https://query2.finance.yahoo.com/v8/finance/chart/" + quote(symbol, safe=""),
                                params={"period1": 1672531200, "period2": int(pd.Timestamp.now(tz="UTC").timestamp()),
                                        "interval": "1d"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=(5, 15))
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        meta = result["meta"]
        if meta["symbol"].upper() != symbol.upper():
            raise FeedError(f"symbol mismatch for {symbol}")
        dates = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert(meta["exchangeTimezoneName"])
        frames.append(pd.Series(result["indicators"]["quote"][0]["close"],
                                index=dates.tz_localize(None).normalize(), name=col))
    return pd.concat(frames, axis=1).rename_axis("date").reset_index()


def checked(name, raw, now):
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.normalize()
    if df.date.isna().any() or df.date.duplicated().any():
        raise FeedError(f"{name}: missing/duplicate session")
    df = df.sort_values("date").reset_index(drop=True)
    cutoffs = {}
    for col in FIELDS[name]:
        cutoff = expected(now, col if name == "cross" else name)
        values = pd.to_numeric(df[col], errors="raise")
        df[col] = values.where(df.date <= cutoff)
        valid = df.loc[df[col].notna()]
        if len(valid) < (300 if name == "shfe" else 240) or valid.date.iloc[-1] != cutoff:
            last = str(valid.date.max())[:10]
            raise FeedError(f"{name}.{col}: expected {cutoff.date()}, last {last}, rows {len(valid)}")
        tail = valid[col].tail(240)
        if not np.isfinite(tail).all() or (tail < 0 if col == "volume" else tail <= 0).any():
            raise FeedError(f"{name}.{col}: invalid market value")
        cutoffs[col] = str(cutoff.date())
    df = df.dropna(subset=FIELDS[name], how="all").reset_index(drop=True)
    if name == "shfe":
        recent = df.tail(240)
        if (recent[FIELDS[name]].isna().any().any() or
                (recent.high < recent[["open", "low", "close"]].max(axis=1)).any() or
                (recent.low > recent[["open", "high", "close"]].min(axis=1)).any()):
            raise FeedError("shfe: invalid OHLC")
    return df, cutoffs


def load(fetchers, *, now=None, folder=None, backup=chart):
    now = pd.Timestamp.now(tz="Asia/Shanghai") if now is None else now
    folder = cache_dir() if folder is None else folder
    folder.mkdir(parents=True, exist_ok=True)
    frames, evidence = {}, {}
    for name, fn in fetchers.items():
        path = folder / (name + ".csv")
        sources = [("primary", fn)]
        if name in SYMBOLS:
            sources.append(("yahoo-chart", lambda: backup(name)))
        sources.append(("cache", lambda: pd.read_csv(path, float_precision="round_trip")))
        errors = []
        for source, fetch in sources:
            try:
                df, cutoffs = checked(name, fetch(), now)
            except Exception as exc:
                errors.append(f"{source}: {type(exc).__name__}: {str(exc)[:200]}")
                continue
            payload = df.to_csv(index=False).encode()
            if source != "cache":
                with tempfile.NamedTemporaryFile(dir=folder, delete=False) as stream:
                    stream.write(payload)
                os.replace(stream.name, path)
            frames[name] = df
            evidence[name] = dict(source=source, cutoffs=cutoffs, rows=len(df),
                                  sha256=hashlib.sha256(payload).hexdigest(), fallback_reasons=errors)
            break
        else:
            raise FeedError(f"{name}: " + "; ".join(errors))
    return frames, evidence
