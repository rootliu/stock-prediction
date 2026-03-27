"""
黄金市场数据采集模块
统一聚合国外、国内和夜盘相关黄金行情
"""

from datetime import datetime, timedelta, time as dt_time
from typing import Optional, Dict, Any, List, Tuple

import akshare as ak
import pandas as pd
import yfinance as yf
from loguru import logger

GOLD_SOURCE_MAP: Dict[str, Dict[str, Any]] = {
    "SHFE_AU_MAIN": {
        "symbol": "AU0",
        "name": "SHFE Gold Main Contract",
        "exchange": "SHFE",
        "description": "上期所黄金主力连续合约",
        "market_group": "DOMESTIC",
        "provider": "akshare",
        "supports_intraday": True,
        "supports_session": True,
    },
    "COMEX": {
        "symbol": "GC=F",
        "name": "COMEX Gold Futures",
        "exchange": "CME/COMEX",
        "description": "纽约商品交易所黄金期货主力代理",
        "market_group": "FOREIGN",
        "provider": "yfinance",
        "supports_intraday": False,
        "supports_session": False,
    },
    "LBMA_SPOT": {
        "symbol": "XAUUSD=X",
        "name": "Gold Spot (XAUUSD)",
        "exchange": "LBMA/OTC",
        "description": "伦敦现货金价格代理（XAUUSD）",
        "market_group": "FOREIGN",
        "provider": "yfinance",
        "supports_intraday": False,
        "supports_session": False,
    },
    "US_ETF": {
        "symbol": "GLD",
        "name": "SPDR Gold Shares",
        "exchange": "NYSE Arca",
        "description": "美国黄金 ETF（GLD）",
        "market_group": "FOREIGN",
        "provider": "yfinance",
        "supports_intraday": False,
        "supports_session": False,
    },
}

PERIOD_TO_INTERVAL = {
    "daily": "1d",
    "weekly": "1wk",
    "monthly": "1mo",
}

INTRADAY_PERIOD_MAP = {
    "5min": "5",
    "15min": "15",
    "30min": "30",
    "60min": "60",
}

DERIVED_INTRADAY_RULE_MAP = {
    "4h": "4h",
}

DAY_SESSION_RANGES = [
    (dt_time(9, 0), dt_time(10, 15)),
    (dt_time(10, 30), dt_time(11, 30)),
    (dt_time(13, 30), dt_time(15, 0)),
]

NIGHT_SESSION_RANGES = [
    (dt_time(21, 0), dt_time(23, 59, 59)),
    (dt_time(0, 0), dt_time(2, 30)),
]


def _normalize_date(date_str: Optional[str]) -> Optional[str]:
    """支持 YYYYMMDD 和 YYYY-MM-DD 两种输入格式"""
    if not date_str:
        return None

    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"不支持的日期格式: {date_str}，请使用 YYYYMMDD 或 YYYY-MM-DD")


def _in_ranges(current: dt_time, ranges: List[Tuple[dt_time, dt_time]]) -> bool:
    """判断时间是否落在给定时段内"""
    for start, end in ranges:
        if start <= current <= end:
            return True
    return False


def _classify_au_session(ts: pd.Timestamp) -> str:
    """根据上期所黄金交易时段分类白盘/夜盘"""
    current = ts.time()
    if _in_ranges(current, DAY_SESSION_RANGES):
        return "DAY"
    if _in_ranges(current, NIGHT_SESSION_RANGES):
        return "NIGHT"
    return "OFF"


class GoldMarketCollector:
    """黄金市场数据采集器"""

    def __init__(self):
        logger.info("初始化黄金市场数据采集器")

    def _get_meta(self, source: str) -> Dict[str, Any]:
        source_key = source.upper()
        if source_key not in GOLD_SOURCE_MAP:
            raise ValueError(f"不支持的黄金来源: {source}")
        return GOLD_SOURCE_MAP[source_key]

    def list_source_codes(self, group: str = "ALL") -> List[str]:
        """返回所有支持的来源代码"""
        group_upper = group.upper()
        if group_upper == "ALL":
            return list(GOLD_SOURCE_MAP.keys())

        return [
            source
            for source, meta in GOLD_SOURCE_MAP.items()
            if meta["market_group"] == group_upper
        ]

    def get_markets(self) -> Dict[str, Any]:
        """返回前端可用的黄金视图分组"""
        return {
            "groups": [
                {
                    "key": "ALL",
                    "label": "全部",
                    "description": "查看国内与国外黄金来源的统一视图",
                    "sources": self.list_source_codes("ALL"),
                },
                {
                    "key": "DOMESTIC",
                    "label": "国内",
                    "description": "国内黄金主力连续合约",
                    "sources": self.list_source_codes("DOMESTIC"),
                },
                {
                    "key": "FOREIGN",
                    "label": "国外",
                    "description": "COMEX、现货金与黄金 ETF",
                    "sources": self.list_source_codes("FOREIGN"),
                },
                {
                    "key": "NIGHT",
                    "label": "夜盘",
                    "description": "上期所黄金白盘与夜盘时段分拆视图",
                    "sources": self.list_source_codes("DOMESTIC"),
                },
            ],
            "default_predict_source": "SHFE_AU_MAIN",
            "default_session_source": "SHFE_AU_MAIN",
        }

    def get_sources(self, group: str = "ALL") -> List[Dict[str, Any]]:
        """获取黄金来源元信息"""
        selected_sources = self.list_source_codes(group)
        data: List[Dict[str, Any]] = []
        for source in selected_sources:
            meta = GOLD_SOURCE_MAP[source]
            data.append(
                {
                    "source": source,
                    "symbol": meta["symbol"],
                    "name": meta["name"],
                    "exchange": meta["exchange"],
                    "description": meta["description"],
                    "market_group": meta["market_group"],
                    "supports_intraday": meta["supports_intraday"],
                    "supports_session": meta["supports_session"],
                }
            )
        return data

    def get_source_name(self, source: str) -> str:
        """获取来源名称"""
        return self._get_meta(source)["name"]

    def get_symbol(self, source: str) -> str:
        """获取来源对应 symbol"""
        return self._get_meta(source)["symbol"]

    def _download_yfinance_kline(
        self,
        symbol: str,
        interval: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """下载并标准化 yfinance OHLCV 数据"""
        try:
            df = yf.download(
                symbol,
                interval=interval,
                start=start_date,
                end=end_date,
                auto_adjust=False,
                progress=False,
            )
        except Exception as e:
            logger.error(f"下载黄金行情失败 {symbol}: {e}")
            return pd.DataFrame()

        if df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df = df.reset_index()
        if "Date" in df.columns:
            df = df.rename(columns={"Date": "date"})
        elif "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "date"})

        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        return self._normalize_ohlcv_frame(df)

    def _rename_first_match(self, df: pd.DataFrame, target: str, candidates: List[str]) -> pd.DataFrame:
        """把首个命中的列名重命名为统一目标列"""
        for candidate in candidates:
            if candidate in df.columns:
                return df.rename(columns={candidate: target})
        return df

    def _normalize_ohlcv_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化不同来源的行情列"""
        frame = df.copy()

        frame = self._rename_first_match(frame, "date", ["date", "datetime", "Date", "Datetime", "日期", "时间"])
        frame = self._rename_first_match(frame, "open", ["open", "Open", "开盘", "开盘价"])
        frame = self._rename_first_match(frame, "high", ["high", "High", "最高", "最高价"])
        frame = self._rename_first_match(frame, "low", ["low", "Low", "最低", "最低价"])
        frame = self._rename_first_match(frame, "close", ["close", "Close", "收盘", "收盘价", "最新价"])
        frame = self._rename_first_match(frame, "volume", ["volume", "Volume", "成交量"])
        frame = self._rename_first_match(frame, "amount", ["amount", "Amount", "成交额"])

        expected_cols = ["date", "open", "high", "low", "close", "volume"]
        for col in expected_cols:
            if col not in frame.columns:
                frame[col] = 0

        frame["date"] = pd.to_datetime(frame["date"])
        for col in ["open", "high", "low", "close", "volume"]:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

        if "amount" in frame.columns:
            frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
        else:
            frame["amount"] = frame["close"] * frame["volume"].fillna(0)

        frame["volume"] = frame["volume"].fillna(0)
        frame = frame.dropna(subset=["open", "high", "low", "close"])
        frame = frame.sort_values("date").reset_index(drop=True)
        frame["pct_change"] = frame["close"].pct_change() * 100

        return frame[["date", "open", "high", "low", "close", "volume", "amount", "pct_change"]]

    def _get_shfe_daily(
        self,
        symbol: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """获取上期所黄金日线"""
        try:
            df = ak.futures_zh_daily_sina(symbol=symbol)
        except Exception as e:
            logger.error(f"获取国内黄金日线失败 {symbol}: {e}")
            return pd.DataFrame()

        if df.empty:
            return pd.DataFrame()

        frame = self._normalize_ohlcv_frame(df)
        start_norm = _normalize_date(start_date)
        end_norm = _normalize_date(end_date)

        if start_norm:
            frame = frame[frame["date"] >= pd.Timestamp(start_norm)]
        if end_norm:
            frame = frame[frame["date"] <= pd.Timestamp(end_norm)]

        return frame.reset_index(drop=True)

    def _get_shfe_intraday(
        self,
        symbol: str,
        period: str,
        start_date: Optional[str],
        end_date: Optional[str],
        session: str = "ALL",
    ) -> pd.DataFrame:
        """获取上期所黄金分时并切分白盘/夜盘"""
        if period not in INTRADAY_PERIOD_MAP:
            raise ValueError(f"不支持的分时周期: {period}")

        try:
            df = ak.futures_zh_minute_sina(symbol=symbol, period=INTRADAY_PERIOD_MAP[period])
        except Exception as e:
            logger.error(f"获取国内黄金分时失败 {symbol}: {e}")
            return pd.DataFrame()

        if df.empty:
            return pd.DataFrame()

        frame = self._normalize_ohlcv_frame(df)
        frame["session"] = frame["date"].apply(_classify_au_session)
        frame = frame[frame["session"] != "OFF"]

        start_norm = _normalize_date(start_date)
        end_norm = _normalize_date(end_date)

        if start_norm:
            frame = frame[frame["date"] >= pd.Timestamp(start_norm)]
        if end_norm:
            frame = frame[frame["date"] <= pd.Timestamp(end_norm) + pd.Timedelta(days=1)]

        session_upper = session.upper()
        if session_upper in {"DAY", "NIGHT"}:
            frame = frame[frame["session"] == session_upper]

        return frame.reset_index(drop=True)

    def _resample_frame(self, df: pd.DataFrame, rule: str) -> pd.DataFrame:
        """把日线数据重采样为周线/月线"""
        if df.empty:
            return df

        frame = df.copy().set_index("date")
        aggregated = frame.resample(rule).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
                "amount": "sum",
            }
        )
        aggregated = aggregated.dropna(subset=["open", "high", "low", "close"]).reset_index()
        aggregated["pct_change"] = aggregated["close"].pct_change() * 100
        return aggregated

    def _resample_intraday_frame(
        self,
        df: pd.DataFrame,
        rule: str,
        by_session: bool = False,
    ) -> pd.DataFrame:
        """把分时数据聚合到更高周期，例如 4h"""
        if df.empty:
            return df

        def _aggregate(frame: pd.DataFrame) -> pd.DataFrame:
            agg_map = {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
                "amount": "sum",
            }
            if "session" in frame.columns:
                # Preserve the source session instead of reclassifying on the
                # resampled timestamp, otherwise the 16:00 day-close bucket is
                # incorrectly dropped as OFF.
                agg_map["session"] = "last"

            resampled = (
                frame.sort_values("date")
                .set_index("date")
                .resample(rule, label="right", closed="right")
                .agg(agg_map)
                .dropna(subset=["open", "high", "low", "close"])
                .reset_index()
            )
            resampled["pct_change"] = resampled["close"].pct_change() * 100
            return resampled

        if by_session and "session" in df.columns:
            chunks: List[pd.DataFrame] = []
            for session_name, current in df.groupby("session"):
                aggregated = _aggregate(current)
                if aggregated.empty:
                    continue
                aggregated["session"] = session_name
                chunks.append(aggregated)
            if not chunks:
                return pd.DataFrame(columns=df.columns)
            return pd.concat(chunks, ignore_index=True).sort_values("date").reset_index(drop=True)

        aggregated = _aggregate(df)
        if "session" not in aggregated.columns and "session" in df.columns:
            aggregated["session"] = aggregated["date"].apply(_classify_au_session)
            aggregated = aggregated[aggregated["session"] != "OFF"].reset_index(drop=True)
        return aggregated

    def get_kline(
        self,
        source: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        session: str = "ALL",
    ) -> pd.DataFrame:
        """获取黄金 K 线 / 分时"""
        source_key = source.upper()
        meta = self._get_meta(source_key)
        symbol = meta["symbol"]

        if meta["provider"] == "yfinance":
            if period not in PERIOD_TO_INTERVAL:
                raise ValueError(f"{source_key} 不支持分时周期 {period}")

            interval = PERIOD_TO_INTERVAL[period]
            start_norm = _normalize_date(start_date) or (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
            end_norm = _normalize_date(end_date) or datetime.now().strftime("%Y-%m-%d")
            df = self._download_yfinance_kline(symbol, interval, start_norm, end_norm)
        else:
            if period in INTRADAY_PERIOD_MAP:
                df = self._get_shfe_intraday(symbol, period, start_date, end_date, session=session)
            elif period in DERIVED_INTRADAY_RULE_MAP:
                base_frame = self._get_shfe_intraday(symbol, "60min", start_date, end_date, session=session)
                df = self._resample_intraday_frame(base_frame, DERIVED_INTRADAY_RULE_MAP[period])
            else:
                df = self._get_shfe_daily(symbol, start_date, end_date)
                if period == "weekly":
                    df = self._resample_frame(df, "W-FRI")
                elif period == "monthly":
                    df = self._resample_frame(df, "ME")

        if df.empty:
            return pd.DataFrame()

        df["source"] = source_key
        df["symbol"] = symbol
        if "session" not in df.columns:
            df["session"] = "ALL"
        return df

    def get_latest_quote(self, source: str) -> Dict[str, Any]:
        """获取最新行情快照"""
        source_key = source.upper()
        meta = self._get_meta(source_key)

        if meta["supports_intraday"]:
            df = self.get_kline(source_key, period="5min")
        else:
            start = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
            end = datetime.now().strftime("%Y-%m-%d")
            df = self.get_kline(source_key, period="daily", start_date=start, end_date=end)

        if df.empty:
            return {}

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        change = float(latest["close"] - prev["close"])
        pct_change = float((change / prev["close"]) * 100) if prev["close"] else 0.0

        return {
            "source": source_key,
            "symbol": meta["symbol"],
            "name": meta["name"],
            "market_group": meta["market_group"],
            "price": float(latest["close"]),
            "change": change,
            "pct_change": pct_change,
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "open": float(latest["open"]),
            "volume": int(latest["volume"]),
            "timestamp": latest["date"].strftime("%Y-%m-%d %H:%M") if latest["date"].hour else latest["date"].strftime("%Y-%m-%d"),
            "session": latest.get("session", "ALL"),
        }

    def compare_sources(
        self,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group: str = "ALL",
        session: str = "ALL",
    ) -> pd.DataFrame:
        """多来源按日期对齐对比（close）"""
        merged: Optional[pd.DataFrame] = None
        selected_sources = self.list_source_codes(group)

        for source in selected_sources:
            df = self.get_kline(source, period=period, start_date=start_date, end_date=end_date, session=session)
            if df.empty:
                continue

            current = df[["date", "close"]].rename(columns={"close": source})
            if merged is None:
                merged = current
            else:
                merged = merged.merge(current, on="date", how="outer")

        if merged is None:
            return pd.DataFrame()

        return merged.sort_values("date").reset_index(drop=True)

    def get_session_data(
        self,
        source: str = "SHFE_AU_MAIN",
        period: str = "5min",
        days: int = 5,
    ) -> pd.DataFrame:
        """获取国内黄金白盘/夜盘分时数据"""
        source_key = source.upper()
        meta = self._get_meta(source_key)
        if not meta["supports_session"]:
            raise ValueError(f"{source_key} 不支持夜盘数据")

        if period == "4h":
            base_frame = self.get_kline(source_key, period="60min", session="ALL")
            frame = self._resample_intraday_frame(base_frame, "4h", by_session=True)
        else:
            frame = self.get_kline(source_key, period=period, session="ALL")
        if frame.empty:
            return frame

        start_cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
        frame = frame[frame["date"] >= start_cutoff]
        frame = frame[frame["session"].isin(["DAY", "NIGHT"])]
        return frame.reset_index(drop=True)


# 单例模式
_collector_instance: Optional[GoldMarketCollector] = None


def get_gold_market_collector() -> GoldMarketCollector:
    """获取黄金数据采集器单例"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = GoldMarketCollector()
    return _collector_instance
