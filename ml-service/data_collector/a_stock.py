"""
A股数据采集模块
使用 AKShare 获取中国A股市场数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


class AStockCollector:
    """A股数据采集器"""

    def __init__(self):
        logger.info("初始化A股数据采集器")

    # ==================== 股票列表 ====================

    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股所有股票列表
        返回: DataFrame包含代码、名称等信息
        """
        try:
            # 获取沪深A股列表
            df = ak.stock_zh_a_spot_em()
            df = df[['代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额', 
                     '振幅', '最高', '最低', '今开', '昨收', '量比', '换手率', 
                     '市盈率-动态', '市净率']]
            df.columns = ['code', 'name', 'price', 'pct_change', 'change', 'volume', 
                         'amount', 'amplitude', 'high', 'low', 'open', 'pre_close',
                         'volume_ratio', 'turnover_rate', 'pe_ratio', 'pb_ratio']
            logger.info(f"获取到 {len(df)} 只A股股票")
            return df
        except Exception as e:
            logger.error(f"获取A股列表失败: {e}")
            return pd.DataFrame()

    # ==================== 实时行情 ====================

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取单只股票实时行情
        Args:
            symbol: 股票代码，如 '000001'
        Returns:
            包含实时行情的字典
        """
        try:
            df = ak.stock_zh_a_spot_em()
            stock = df[df['代码'] == symbol]
            if stock.empty:
                logger.warning(f"未找到股票: {symbol}")
                return {}
            
            row = stock.iloc[0]
            return {
                'code': row['代码'],
                'name': row['名称'],
                'price': float(row['最新价']) if pd.notna(row['最新价']) else 0,
                'pct_change': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                'change': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0,
                'volume': int(row['成交量']) if pd.notna(row['成交量']) else 0,
                'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0,
                'high': float(row['最高']) if pd.notna(row['最高']) else 0,
                'low': float(row['最低']) if pd.notna(row['最低']) else 0,
                'open': float(row['今开']) if pd.notna(row['今开']) else 0,
                'pre_close': float(row['昨收']) if pd.notna(row['昨收']) else 0,
                'turnover_rate': float(row['换手率']) if pd.notna(row['换手率']) else 0,
                'pe_ratio': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else 0,
                'pb_ratio': float(row['市净率']) if pd.notna(row['市净率']) else 0,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取实时行情失败 {symbol}: {e}")
            return {}

    def get_batch_realtime_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取多只股票实时行情
        Args:
            symbols: 股票代码列表
        Returns:
            行情列表
        """
        try:
            df = ak.stock_zh_a_spot_em()
            results = []
            for symbol in symbols:
                stock = df[df['代码'] == symbol]
                if not stock.empty:
                    row = stock.iloc[0]
                    results.append({
                        'code': row['代码'],
                        'name': row['名称'],
                        'price': float(row['最新价']) if pd.notna(row['最新价']) else 0,
                        'pct_change': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                        'change': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0,
                        'volume': int(row['成交量']) if pd.notna(row['成交量']) else 0,
                        'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0,
                    })
            return results
        except Exception as e:
            logger.error(f"批量获取实时行情失败: {e}")
            return []

    # ==================== 历史K线 ====================

    def get_daily_kline(
        self, 
        symbol: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"  # qfq: 前复权, hfq: 后复权, "": 不复权
    ) -> pd.DataFrame:
        """
        获取日K线数据
        Args:
            symbol: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            adjust: 复权类型
        Returns:
            K线DataFrame
        """
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date or "20200101",
                end_date=end_date or datetime.now().strftime("%Y%m%d"),
                adjust=adjust
            )
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 
                         'amount', 'amplitude', 'pct_change', 'change', 'turnover_rate']
            df['date'] = pd.to_datetime(df['date'])
            df['code'] = symbol
            logger.info(f"获取 {symbol} 日K线 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取日K线失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_weekly_kline(self, symbol: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取周K线数据"""
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="weekly", adjust=adjust)
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume',
                         'amount', 'amplitude', 'pct_change', 'change', 'turnover_rate']
            df['date'] = pd.to_datetime(df['date'])
            df['code'] = symbol
            return df
        except Exception as e:
            logger.error(f"获取周K线失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_monthly_kline(self, symbol: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取月K线数据"""
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="monthly", adjust=adjust)
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume',
                         'amount', 'amplitude', 'pct_change', 'change', 'turnover_rate']
            df['date'] = pd.to_datetime(df['date'])
            df['code'] = symbol
            return df
        except Exception as e:
            logger.error(f"获取月K线失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_minute_kline(self, symbol: str, period: str = "5") -> pd.DataFrame:
        """
        获取分钟K线数据
        Args:
            symbol: 股票代码
            period: 分钟周期 1, 5, 15, 30, 60
        """
        try:
            df = ak.stock_zh_a_hist_min_em(symbol=symbol, period=period)
            df.columns = ['datetime', 'open', 'close', 'high', 'low', 'volume', 'amount', 'latest']
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['code'] = symbol
            return df
        except Exception as e:
            logger.error(f"获取分钟K线失败 {symbol}: {e}")
            return pd.DataFrame()

    # ==================== 北向资金 ====================

    def get_north_flow_daily(self) -> pd.DataFrame:
        """获取北向资金每日流入数据"""
        try:
            df = ak.stock_hsgt_north_net_flow_in_em()
            logger.info("获取北向资金数据成功")
            return df
        except Exception as e:
            logger.error(f"获取北向资金数据失败: {e}")
            return pd.DataFrame()

    def get_north_flow_realtime(self) -> Dict[str, Any]:
        """获取北向资金实时数据"""
        try:
            # 沪股通
            df_sh = ak.stock_hsgt_north_acc_flow_in_em(symbol="沪股通")
            # 深股通  
            df_sz = ak.stock_hsgt_north_acc_flow_in_em(symbol="深股通")
            
            return {
                'timestamp': datetime.now().isoformat(),
                'hk_sh': df_sh.iloc[-1].to_dict() if not df_sh.empty else {},
                'hk_sz': df_sz.iloc[-1].to_dict() if not df_sz.empty else {}
            }
        except Exception as e:
            logger.error(f"获取北向资金实时数据失败: {e}")
            return {}

    # ==================== 龙虎榜 ====================

    def get_dragon_tiger_list(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取龙虎榜数据
        Args:
            date: 日期 YYYYMMDD，默认最近交易日
        """
        try:
            df = ak.stock_lhb_detail_em(start_date=date, end_date=date)
            logger.info(f"获取龙虎榜数据 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取龙虎榜数据失败: {e}")
            return pd.DataFrame()

    # ==================== 财务数据 ====================

    def get_financial_indicator(self, symbol: str) -> pd.DataFrame:
        """获取主要财务指标"""
        try:
            df = ak.stock_financial_abstract_ths(symbol=symbol)
            return df
        except Exception as e:
            logger.error(f"获取财务指标失败 {symbol}: {e}")
            return pd.DataFrame()

    # ==================== 板块数据 ====================

    def get_sector_list(self) -> pd.DataFrame:
        """获取行业板块列表"""
        try:
            df = ak.stock_board_industry_name_em()
            return df
        except Exception as e:
            logger.error(f"获取行业板块列表失败: {e}")
            return pd.DataFrame()

    def get_sector_stocks(self, sector_name: str) -> pd.DataFrame:
        """获取板块成分股"""
        try:
            df = ak.stock_board_industry_cons_em(symbol=sector_name)
            return df
        except Exception as e:
            logger.error(f"获取板块成分股失败 {sector_name}: {e}")
            return pd.DataFrame()

    def get_sector_flow(self) -> pd.DataFrame:
        """获取板块资金流向"""
        try:
            df = ak.stock_sector_fund_flow_rank(indicator="今日")
            return df
        except Exception as e:
            logger.error(f"获取板块资金流向失败: {e}")
            return pd.DataFrame()

    # ==================== 指数数据 ====================

    def get_index_realtime(self, index_code: str = "000001") -> Dict[str, Any]:
        """
        获取指数实时数据
        常用指数: 000001-上证指数, 399001-深证成指, 399006-创业板指
        """
        try:
            df = ak.stock_zh_index_spot_em()
            index_data = df[df['代码'] == index_code]
            if index_data.empty:
                return {}
            row = index_data.iloc[0]
            return {
                'code': row['代码'],
                'name': row['名称'],
                'price': float(row['最新价']),
                'pct_change': float(row['涨跌幅']),
                'change': float(row['涨跌额']),
                'volume': float(row['成交量']),
                'amount': float(row['成交额']),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取指数实时数据失败 {index_code}: {e}")
            return {}

    def get_index_daily(self, index_code: str = "000001") -> pd.DataFrame:
        """获取指数日K线"""
        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
            df['code'] = index_code
            return df
        except Exception as e:
            logger.error(f"获取指数日K线失败 {index_code}: {e}")
            return pd.DataFrame()


# 单例模式
_collector_instance = None


def get_a_stock_collector() -> AStockCollector:
    """获取A股数据采集器单例"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = AStockCollector()
    return _collector_instance


# 测试
if __name__ == "__main__":
    collector = get_a_stock_collector()
    
    # 测试获取股票列表
    print("=== 获取股票列表 ===")
    stock_list = collector.get_stock_list()
    print(stock_list.head())
    
    # 测试获取实时行情
    print("\n=== 获取平安银行实时行情 ===")
    quote = collector.get_realtime_quote("000001")
    print(quote)
    
    # 测试获取日K线
    print("\n=== 获取平安银行日K线 ===")
    kline = collector.get_daily_kline("000001", "20240101")
    print(kline.tail())
    
    # 测试获取上证指数
    print("\n=== 获取上证指数 ===")
    index = collector.get_index_realtime("000001")
    print(index)