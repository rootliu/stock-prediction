"""
黄金市场数据采集模块
使用 yfinance 获取主要黄金交易市场代理行情
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import pandas as pd
import yfinance as yf
from loguru import logger

# 黄金来源映射（source -> metadata）
GOLD_SOURCE_MAP: Dict[str, Dict[str, str]] = {
    "COMEX": {
        "symbol": "GC=F",
        "name": "COMEX Gold Futures",
        "exchange": "CME/COMEX",
        "description": "纽约商品交易所黄金期货主力代理",
    },
    "LBMA_SPOT": {
        "symbol": "XAUUSD=X",
        "name": "Gold Spot (XAUUSD)",
        "exchange": "LBMA/OTC",
        "description": "伦敦现货金价格代理（XAUUSD）",
    },
    "US_ETF": {
        "symbol": "GLD",
        "name": "SPDR Gold Shares",
        "exchange": "NYSE Arca",
        "description": "美国黄金 ETF（GLD）",
    },
}

PERIOD_TO_INTERVAL = {
    "daily": "1d",
    "weekly": "1wk",
    "monthly": "1mo",
}


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


class GoldMarketCollector:
    """黄金市场数据采集器"""

    def __init__(self):
        logger.info("初始化黄金市场数据采集器")

    def list_source_codes(self) -> List[str]:
        """返回所有支持的来源代码"""
        return list(GOLD_SOURCE_MAP.keys())

    def get_sources(self) -> List[Dict[str, str]]:
        """获取黄金来源元信息"""
        data: List[Dict[str, str]] = []
        for source, meta in GOLD_SOURCE_MAP.items():
            data.append(
                {
                    "source": source,
                    "symbol": meta["symbol"],
                    "name": meta["name"],
                    "exchange": meta["exchange"],
                    "description": meta["description"],
                }
            )
        return data

    def get_source_name(self, source: str) -> str:
        """获取来源名称"""
        source_key = source.upper()
        if source_key not in GOLD_SOURCE_MAP:
            raise ValueError(f"不支持的黄金来源: {source}")
        return GOLD_SOURCE_MAP[source_key]["name"]

    def get_symbol(self, source: str) -> str:
        """获取来源对应 symbol"""
        source_key = source.upper()
        if source_key not in GOLD_SOURCE_MAP:
            raise ValueError(f"不支持的黄金来源: {source}")
        return GOLD_SOURCE_MAP[source_key]["symbol"]

    def _download_kline(
        self,
        symbol: str,
        interval: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """下载并标准化 OHLCV 数据"""
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

        rename_map = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
        df = df.rename(columns=rename_map)

        expected_cols = ["date", "open", "high", "low", "close", "volume"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0

        df["date"] = pd.to_datetime(df["date"])
        df["open"] = pd.to_numeric(df["open"], errors="coerce")
        df["high"] = pd.to_numeric(df["high"], errors="coerce")
        df["low"] = pd.to_numeric(df["low"], errors="coerce")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)

        df = df.sort_values("date")
        df["pct_change"] = df["close"].pct_change() * 100
        df["amount"] = df["close"] * df["volume"]
        df = df.dropna(subset=["open", "high", "low", "close"])

        return df[["date", "open", "high", "low", "close", "volume", "amount", "pct_change"]]

    def get_kline(
        self,
        source: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取黄金 K 线"""
        source_key = source.upper()
        if source_key not in GOLD_SOURCE_MAP:
            raise ValueError(f"不支持的黄金来源: {source}")

        interval = PERIOD_TO_INTERVAL.get(period, "1d")
        symbol = GOLD_SOURCE_MAP[source_key]["symbol"]

        start_norm = _normalize_date(start_date) or (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
        end_norm = _normalize_date(end_date) or datetime.now().strftime("%Y-%m-%d")

        df = self._download_kline(symbol, interval, start_norm, end_norm)
        if df.empty:
            return pd.DataFrame()

        df["source"] = source_key
        df["symbol"] = symbol
        return df

    def get_latest_quote(self, source: str) -> Dict[str, Any]:
        """获取最新行情快照"""
        source_key = source.upper()
        if source_key not in GOLD_SOURCE_MAP:
            raise ValueError(f"不支持的黄金来源: {source}")

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
            "symbol": GOLD_SOURCE_MAP[source_key]["symbol"],
            "name": GOLD_SOURCE_MAP[source_key]["name"],
            "price": float(latest["close"]),
            "change": change,
            "pct_change": pct_change,
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "open": float(latest["open"]),
            "volume": int(latest["volume"]),
            "timestamp": latest["date"].strftime("%Y-%m-%d"),
        }

    def compare_sources(
        self,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """多来源按日期对齐对比（close）"""
        merged: Optional[pd.DataFrame] = None

        for source in self.list_source_codes():
            df = self.get_kline(source, period=period, start_date=start_date, end_date=end_date)
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


# 单例模式
_collector_instance: Optional[GoldMarketCollector] = None


def get_gold_market_collector() -> GoldMarketCollector:
    """获取黄金数据采集器单例"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = GoldMarketCollector()
    return _collector_instance
