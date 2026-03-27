"""
股票预测分析系统 - ML服务主入口
FastAPI 服务提供股票数据、技术分析和预测API
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
import pandas as pd

from data_collector import (
    get_a_stock_collector,
    get_hk_stock_collector,
    get_gold_market_collector,
)
from models.predictor import run_price_prediction
from utils.indicators import calculate_all_indicators, TechnicalIndicators

# 配置日志
logger.add(
    "logs/ml_service_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO"
)


# ==================== Pydantic 模型 ====================

class StockQuote(BaseModel):
    """股票实时行情"""
    code: str
    name: str
    price: float
    pct_change: float
    change: float
    volume: int
    amount: float
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    pre_close: Optional[float] = None
    turnover_rate: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    market: Optional[str] = "CN"
    timestamp: Optional[str] = None


class KLineData(BaseModel):
    """K线数据"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: Optional[float] = None
    pct_change: Optional[float] = None


class KLineResponse(BaseModel):
    """K线响应"""
    code: str
    name: Optional[str] = None
    market: str
    period: str
    data: List[KLineData]


class IndexQuote(BaseModel):
    """指数行情"""
    code: str
    name: str
    price: float
    pct_change: float
    change: float
    volume: Optional[float] = None
    amount: Optional[float] = None
    timestamp: str


class NorthFlowData(BaseModel):
    """北向/南向资金数据"""
    timestamp: str
    hk_sh: Optional[Dict[str, Any]] = None
    hk_sz: Optional[Dict[str, Any]] = None
    sh_hk: Optional[Dict[str, Any]] = None
    sz_hk: Optional[Dict[str, Any]] = None


class IndicatorRequest(BaseModel):
    """技术指标请求"""
    code: str
    market: str = "CN"  # CN or HK
    period: str = "daily"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class IndicatorResponse(BaseModel):
    """技术指标响应"""
    code: str
    market: str
    indicators: Dict[str, List[Optional[float]]]


class PredictRequest(BaseModel):
    """预测请求参数"""
    horizon: int = Field(default=5, ge=1, le=30, description="预测未来天数")
    lookback: int = Field(default=240, ge=60, le=2000, description="建模历史窗口")
    model_type: str = Field(default="ensemble", pattern="^(linear|boosting|ensemble)$", description="预测模型策略")


class GoldSessionPoint(BaseModel):
    """黄金时段点位"""
    date: str
    close: float
    session: str


class GoldSessionResponse(BaseModel):
    """黄金时段响应"""
    source: str
    period: str
    days: int
    data: List[GoldSessionPoint]


# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("ML服务启动中...")
    # 初始化数据采集器
    get_a_stock_collector()
    get_hk_stock_collector()
    get_gold_market_collector()
    logger.info("数据采集器初始化完成")
    yield
    logger.info("ML服务关闭")


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="股票预测分析系统 - ML服务",
    description="提供A股和港股数据采集、技术分析和AI预测API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ml-service"
    }


# ==================== A股 API ====================

@app.get("/api/v1/a-stock/list", summary="获取A股列表")
async def get_a_stock_list(
    limit: int = Query(default=100, ge=1, le=5000, description="返回数量限制")
):
    """获取A股所有股票列表"""
    try:
        collector = get_a_stock_collector()
        df = collector.get_stock_list()
        if df.empty:
            raise HTTPException(status_code=503, detail="无法获取股票列表")
        
        data = df.head(limit).to_dict(orient="records")
        return {
            "total": len(df),
            "data": data
        }
    except Exception as e:
        logger.error(f"获取A股列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/a-stock/quote/{symbol}", response_model=StockQuote, summary="获取A股实时行情")
async def get_a_stock_quote(symbol: str):
    """获取单只A股实时行情"""
    try:
        collector = get_a_stock_collector()
        quote = collector.get_realtime_quote(symbol)
        if not quote:
            raise HTTPException(status_code=404, detail=f"未找到股票: {symbol}")
        quote['market'] = 'CN'
        return quote
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取A股行情失败 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/a-stock/quotes", summary="批量获取A股行情")
async def get_a_stock_quotes(symbols: List[str]):
    """批量获取多只A股实时行情"""
    try:
        collector = get_a_stock_collector()
        quotes = collector.get_batch_realtime_quotes(symbols)
        return {"data": quotes}
    except Exception as e:
        logger.error(f"批量获取A股行情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/a-stock/kline/{symbol}", response_model=KLineResponse, summary="获取A股K线")
async def get_a_stock_kline(
    symbol: str,
    period: str = Query(default="daily", enum=["daily", "weekly", "monthly"]),
    start_date: Optional[str] = Query(default=None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(default=None, description="结束日期 YYYYMMDD"),
    adjust: str = Query(default="qfq", enum=["qfq", "hfq", ""])
):
    """获取A股K线数据"""
    try:
        collector = get_a_stock_collector()
        
        if period == "daily":
            df = collector.get_daily_kline(symbol, start_date, end_date, adjust)
        elif period == "weekly":
            df = collector.get_weekly_kline(symbol, adjust)
        else:
            df = collector.get_monthly_kline(symbol, adjust)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到K线数据: {symbol}")
        
        # 转换为响应格式
        data = []
        for _, row in df.iterrows():
            data.append(KLineData(
                date=row['date'].strftime('%Y-%m-%d'),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume']),
                amount=float(row['amount']) if 'amount' in row else None,
                pct_change=float(row['pct_change']) if 'pct_change' in row else None
            ))
        
        return KLineResponse(
            code=symbol,
            market="CN",
            period=period,
            data=data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取A股K线失败 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/a-stock/index/{code}", response_model=IndexQuote, summary="获取A股指数")
async def get_a_stock_index(code: str = "000001"):
    """
    获取A股指数实时数据
    常用指数: 000001-上证指数, 399001-深证成指, 399006-创业板指
    """
    try:
        collector = get_a_stock_collector()
        data = collector.get_index_realtime(code)
        if not data:
            raise HTTPException(status_code=404, detail=f"未找到指数: {code}")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取A股指数失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/a-stock/north-flow", summary="获取北向资金")
async def get_north_flow():
    """获取北向资金实时数据"""
    try:
        collector = get_a_stock_collector()
        data = collector.get_north_flow_realtime()
        return data
    except Exception as e:
        logger.error(f"获取北向资金失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/a-stock/sectors", summary="获取板块列表")
async def get_a_stock_sectors():
    """获取A股行业板块列表"""
    try:
        collector = get_a_stock_collector()
        df = collector.get_sector_list()
        if df.empty:
            return {"data": []}
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"获取板块列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 港股 API ====================

@app.get("/api/v1/hk-stock/list", summary="获取港股列表")
async def get_hk_stock_list(
    limit: int = Query(default=100, ge=1, le=5000, description="返回数量限制")
):
    """获取港股所有股票列表"""
    try:
        collector = get_hk_stock_collector()
        df = collector.get_stock_list()
        if df.empty:
            raise HTTPException(status_code=503, detail="无法获取港股列表")
        
        data = df.head(limit).to_dict(orient="records")
        return {
            "total": len(df),
            "data": data
        }
    except Exception as e:
        logger.error(f"获取港股列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/hk-stock/quote/{symbol}", response_model=StockQuote, summary="获取港股实时行情")
async def get_hk_stock_quote(symbol: str):
    """获取单只港股实时行情"""
    try:
        collector = get_hk_stock_collector()
        quote = collector.get_realtime_quote(symbol)
        if not quote:
            raise HTTPException(status_code=404, detail=f"未找到港股: {symbol}")
        return quote
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取港股行情失败 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/hk-stock/quotes", summary="批量获取港股行情")
async def get_hk_stock_quotes(symbols: List[str]):
    """批量获取多只港股实时行情"""
    try:
        collector = get_hk_stock_collector()
        quotes = collector.get_batch_realtime_quotes(symbols)
        return {"data": quotes}
    except Exception as e:
        logger.error(f"批量获取港股行情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/hk-stock/kline/{symbol}", response_model=KLineResponse, summary="获取港股K线")
async def get_hk_stock_kline(
    symbol: str,
    period: str = Query(default="daily", enum=["daily", "weekly", "monthly"]),
    start_date: Optional[str] = Query(default=None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(default=None, description="结束日期 YYYYMMDD"),
    adjust: str = Query(default="qfq", enum=["qfq", "hfq", ""])
):
    """获取港股K线数据"""
    try:
        collector = get_hk_stock_collector()
        
        if period == "daily":
            df = collector.get_daily_kline(symbol, start_date, end_date, adjust)
        elif period == "weekly":
            df = collector.get_weekly_kline(symbol, adjust)
        else:
            df = collector.get_monthly_kline(symbol, adjust)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到K线数据: {symbol}")
        
        data = []
        for _, row in df.iterrows():
            data.append(KLineData(
                date=row['date'].strftime('%Y-%m-%d'),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume']),
                amount=float(row['amount']) if 'amount' in row else None,
                pct_change=float(row['pct_change']) if 'pct_change' in row else None
            ))
        
        return KLineResponse(
            code=symbol,
            market="HK",
            period=period,
            data=data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取港股K线失败 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/hk-stock/hsi", response_model=IndexQuote, summary="获取恒生指数")
async def get_hsi():
    """获取恒生指数实时数据"""
    try:
        collector = get_hk_stock_collector()
        data = collector.get_hsi_realtime()
        if not data:
            raise HTTPException(status_code=404, detail="无法获取恒生指数")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取恒生指数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/hk-stock/south-flow", summary="获取南向资金")
async def get_south_flow():
    """获取南向资金（港股通）实时数据"""
    try:
        collector = get_hk_stock_collector()
        data = collector.get_south_flow_realtime()
        return data
    except Exception as e:
        logger.error(f"获取南向资金失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/hk-stock/hot", summary="获取热门港股")
async def get_hot_hk_stocks(count: int = Query(default=20, ge=1, le=100)):
    """获取热门港股排行（按成交额）"""
    try:
        collector = get_hk_stock_collector()
        df = collector.get_hot_stocks(count)
        if df.empty:
            return {"data": []}
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"获取热门港股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/hk-stock/ggt", summary="获取港股通标的")
async def get_hk_ggt_stocks():
    """获取港股通标的股票列表"""
    try:
        collector = get_hk_stock_collector()
        df = collector.get_hk_ggt_stocks()
        if df.empty:
            return {"data": []}
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"获取港股通标的失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 黄金 API ====================

@app.get("/api/v1/gold/sources", summary="获取黄金数据来源")
async def get_gold_sources(
    group: str = Query(default="ALL", enum=["ALL", "DOMESTIC", "FOREIGN"])
):
    """获取可用黄金数据来源"""
    try:
        collector = get_gold_market_collector()
        return {"data": collector.get_sources(group=group)}
    except Exception as e:
        logger.error(f"获取黄金来源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gold/markets", summary="获取黄金市场视图")
async def get_gold_markets():
    """获取黄金市场分组与默认配置"""
    try:
        collector = get_gold_market_collector()
        return collector.get_markets()
    except Exception as e:
        logger.error(f"获取黄金市场视图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gold/quote/{source}", summary="获取黄金行情快照")
async def get_gold_quote(source: str):
    """获取单来源黄金最新行情"""
    try:
        collector = get_gold_market_collector()
        data = collector.get_latest_quote(source)
        if not data:
            raise HTTPException(status_code=404, detail=f"未找到黄金行情: {source}")
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取黄金行情失败 {source}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gold/kline/{source}", response_model=KLineResponse, summary="获取黄金K线")
async def get_gold_kline(
    source: str,
    period: str = Query(default="daily", enum=["daily", "weekly", "monthly", "4h", "5min", "15min", "30min", "60min"]),
    start_date: Optional[str] = Query(default=None, description="开始日期 YYYYMMDD 或 YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="结束日期 YYYYMMDD 或 YYYY-MM-DD"),
    session: str = Query(default="ALL", enum=["ALL", "DAY", "NIGHT"]),
):
    """获取黄金 K 线数据"""
    try:
        collector = get_gold_market_collector()
        df = collector.get_kline(
            source,
            period=period,
            start_date=start_date,
            end_date=end_date,
            session=session,
        )
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到K线数据: {source}")

        data = []
        for _, row in df.iterrows():
            data.append(
                KLineData(
                    date=row["date"].strftime("%Y-%m-%d %H:%M") if period in {"4h", "5min", "15min", "30min", "60min"} else row["date"].strftime("%Y-%m-%d"),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]) if row["volume"] == row["volume"] else 0,
                    amount=float(row["amount"]) if row["amount"] == row["amount"] else None,
                    pct_change=float(row["pct_change"]) if row["pct_change"] == row["pct_change"] else None,
                )
            )

        return KLineResponse(
            code=source.upper(),
            name=collector.get_source_name(source),
            market="GOLD",
            period=period,
            data=data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取黄金K线失败 {source}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gold/compare", summary="对比多个黄金来源走势")
async def compare_gold_sources(
    period: str = Query(default="daily", enum=["daily", "weekly", "monthly"]),
    group: str = Query(default="ALL", enum=["ALL", "DOMESTIC", "FOREIGN"]),
    start_date: Optional[str] = Query(default=None, description="开始日期 YYYYMMDD 或 YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="结束日期 YYYYMMDD 或 YYYY-MM-DD"),
    session: str = Query(default="ALL", enum=["ALL", "DAY", "NIGHT"]),
):
    """多来源黄金价格对比（close 对齐）"""
    try:
        collector = get_gold_market_collector()
        df = collector.compare_sources(
            period=period,
            start_date=start_date,
            end_date=end_date,
            group=group,
            session=session,
        )
        if df.empty:
            raise HTTPException(status_code=404, detail="未获取到可对比的黄金数据")

        source_codes = collector.list_source_codes(group=group)
        data = []
        for _, row in df.iterrows():
            item: Dict[str, Any] = {"date": row["date"].strftime("%Y-%m-%d")}
            for source in source_codes:
                value = row[source] if source in row else None
                item[source] = float(value) if value is not None and value == value else None
            data.append(item)

        return {
            "period": period,
            "group": group,
            "session": session,
            "sources": source_codes,
            "data": data,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对比黄金来源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gold/session/{source}", response_model=GoldSessionResponse, summary="获取黄金白盘/夜盘走势")
async def get_gold_session_data(
    source: str,
    period: str = Query(default="4h", enum=["4h", "5min", "15min", "30min", "60min"]),
    days: int = Query(default=5, ge=1, le=30),
):
    """获取国内黄金白盘/夜盘分时走势"""
    try:
        collector = get_gold_market_collector()
        df = collector.get_session_data(source=source, period=period, days=days)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到夜盘数据: {source}")

        data = [
            GoldSessionPoint(
                date=row["date"].strftime("%Y-%m-%d %H:%M"),
                close=float(row["close"]),
                session=str(row["session"]),
            )
            for _, row in df.iterrows()
        ]

        return GoldSessionResponse(
            source=source.upper(),
            period=period,
            days=days,
            data=data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取黄金时段走势失败 {source}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/gold/predict/{source}", summary="预测黄金未来走势")
async def predict_gold(source: str, request: PredictRequest):
    """预测指定黄金来源未来收盘走势"""
    try:
        collector = get_gold_market_collector()
        source_meta = next(
            (item for item in collector.get_sources("ALL") if item["source"] == source.upper()),
            {},
        )
        predict_period = "daily"
        future_step_hours = None
        resolved_lookback = request.lookback

        df = pd.DataFrame()
        if source_meta.get("supports_intraday"):
            intraday_start = (datetime.now() - timedelta(days=max(request.lookback * 3, 120))).strftime("%Y-%m-%d")
            intraday_df = collector.get_kline(
                source,
                period="4h",
                start_date=intraday_start,
                end_date=datetime.now().strftime("%Y-%m-%d"),
                session="ALL",
            )
            if not intraday_df.empty and len(intraday_df) >= 80:
                df = intraday_df
                predict_period = "4h"
                future_step_hours = 4
                resolved_lookback = min(request.lookback, max(len(df) - request.horizon - 1, 60))

        if df.empty:
            df = collector.get_kline(source, period="daily")
            resolved_lookback = request.lookback

        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到可预测数据: {source}")

        result = run_price_prediction(
            df=df[["date", "close"]],
            horizon=request.horizon,
            lookback=resolved_lookback,
            model_type=request.model_type,
            use_external_direction=request.model_type == "boosting",
            external_direction_csv=None,
            enable_direction_head=request.model_type == "boosting",
            enable_bias_correction=request.model_type == "boosting",
            future_step_hours=future_step_hours,
        )

        return {
            "source": source.upper(),
            "symbol": collector.get_symbol(source),
            "name": collector.get_source_name(source),
            "period": predict_period,
            "lookback": resolved_lookback,
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预测黄金失败 {source}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 技术指标 API ====================

@app.post("/api/v1/indicators", response_model=IndicatorResponse, summary="计算技术指标")
async def calculate_indicators(request: IndicatorRequest):
    """计算股票技术指标"""
    try:
        # 获取K线数据
        if request.market == "CN":
            collector = get_a_stock_collector()
        else:
            collector = get_hk_stock_collector()
        
        df = collector.get_daily_kline(
            request.code,
            request.start_date,
            request.end_date
        )
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到数据: {request.code}")
        
        # 计算技术指标
        df_with_indicators = calculate_all_indicators(df)
        
        # 提取指标数据
        indicator_cols = [col for col in df_with_indicators.columns 
                        if col not in ['date', 'code', 'market']]
        
        indicators = {}
        for col in indicator_cols:
            indicators[col] = df_with_indicators[col].tolist()
        
        return IndicatorResponse(
            code=request.code,
            market=request.market,
            indicators=indicators
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"计算技术指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/indicators/{symbol}", summary="获取股票技术指标")
async def get_stock_indicators(
    symbol: str,
    market: str = Query(default="CN", enum=["CN", "HK"]),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """获取股票技术指标（简化接口）"""
    try:
        if market == "CN":
            collector = get_a_stock_collector()
        else:
            collector = get_hk_stock_collector()
        
        df = collector.get_daily_kline(symbol, start_date, end_date)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到数据: {symbol}")
        
        df_with_indicators = calculate_all_indicators(df)
        
        # 返回最近的指标值
        latest = df_with_indicators.iloc[-1].to_dict()
        
        # 格式化日期
        if 'date' in latest:
            latest['date'] = latest['date'].strftime('%Y-%m-%d')
        
        return {
            "code": symbol,
            "market": market,
            "latest": latest
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取技术指标失败 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 启动服务 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
