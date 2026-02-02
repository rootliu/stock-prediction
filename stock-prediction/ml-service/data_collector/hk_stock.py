"""
港股数据采集模块
使用 AKShare 获取香港股票市场数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger


class HKStockCollector:
    """港股数据采集器"""

    def __init__(self):
        logger.info("初始化港股数据采集器")

    # ==================== 股票列表 ====================

    def get_stock_list(self) -> pd.DataFrame:
        """
        获取港股所有股票列表
        Returns:
            DataFrame包含代码、名称等信息
        """
        try:
            df = ak.stock_hk_spot_em()
            df = df[['代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额',
                     '振幅', '最高', '最低', '今开', '昨收', '换手率']]
            df.columns = ['code', 'name', 'price', 'pct_change', 'change', 'volume',
                         'amount', 'amplitude', 'high', 'low', 'open', 'pre_close', 'turnover_rate']
            logger.info(f"获取到 {len(df)} 只港股")
            return df
        except Exception as e:
            logger.error(f"获取港股列表失败: {e}")
            return pd.DataFrame()

    def get_hk_ggt_stocks(self) -> pd.DataFrame:
        """
        获取港股通标的股票列表
        即可通过沪港通/深港通交易的港股
        """
        try:
            # 获取港股通(沪)成分股
            df_sh = ak.stock_hk_ggt_components_em()
            logger.info(f"获取港股通标的 {len(df_sh)} 只")
            return df_sh
        except Exception as e:
            logger.error(f"获取港股通标的失败: {e}")
            return pd.DataFrame()

    # ==================== 实时行情 ====================

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取单只港股实时行情
        Args:
            symbol: 港股代码，如 '00700' (腾讯)
        Returns:
            包含实时行情的字典
        """
        try:
            df = ak.stock_hk_spot_em()
            stock = df[df['代码'] == symbol]
            if stock.empty:
                logger.warning(f"未找到港股: {symbol}")
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
                'market': 'HK',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取港股实时行情失败 {symbol}: {e}")
            return {}

    def get_batch_realtime_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取多只港股实时行情
        Args:
            symbols: 股票代码列表
        Returns:
            行情列表
        """
        try:
            df = ak.stock_hk_spot_em()
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
                        'market': 'HK'
                    })
            return results
        except Exception as e:
            logger.error(f"批量获取港股实时行情失败: {e}")
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
        获取港股日K线数据
        Args:
            symbol: 股票代码，如 '00700'
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            adjust: 复权类型
        Returns:
            K线DataFrame
        """
        try:
            df = ak.stock_hk_hist(
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
            df['market'] = 'HK'
            logger.info(f"获取港股 {symbol} 日K线 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取港股日K线失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_weekly_kline(self, symbol: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取港股周K线数据"""
        try:
            df = ak.stock_hk_hist(symbol=symbol, period="weekly", adjust=adjust)
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume',
                         'amount', 'amplitude', 'pct_change', 'change', 'turnover_rate']
            df['date'] = pd.to_datetime(df['date'])
            df['code'] = symbol
            df['market'] = 'HK'
            return df
        except Exception as e:
            logger.error(f"获取港股周K线失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_monthly_kline(self, symbol: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取港股月K线数据"""
        try:
            df = ak.stock_hk_hist(symbol=symbol, period="monthly", adjust=adjust)
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume',
                         'amount', 'amplitude', 'pct_change', 'change', 'turnover_rate']
            df['date'] = pd.to_datetime(df['date'])
            df['code'] = symbol
            df['market'] = 'HK'
            return df
        except Exception as e:
            logger.error(f"获取港股月K线失败 {symbol}: {e}")
            return pd.DataFrame()

    # ==================== 南向资金 ====================

    def get_south_flow_daily(self) -> pd.DataFrame:
        """获取南向资金（港股通）每日流入数据"""
        try:
            df = ak.stock_hsgt_south_net_flow_in_em()
            logger.info("获取南向资金数据成功")
            return df
        except Exception as e:
            logger.error(f"获取南向资金数据失败: {e}")
            return pd.DataFrame()

    def get_south_flow_realtime(self) -> Dict[str, Any]:
        """获取南向资金实时数据"""
        try:
            # 港股通(沪)
            df_sh = ak.stock_hsgt_south_acc_flow_in_em(symbol="港股通(沪)")
            # 港股通(深)
            df_sz = ak.stock_hsgt_south_acc_flow_in_em(symbol="港股通(深)")
            
            return {
                'timestamp': datetime.now().isoformat(),
                'sh_hk': df_sh.iloc[-1].to_dict() if not df_sh.empty else {},
                'sz_hk': df_sz.iloc[-1].to_dict() if not df_sz.empty else {}
            }
        except Exception as e:
            logger.error(f"获取南向资金实时数据失败: {e}")
            return {}

    # ==================== 港股指数 ====================

    def get_hsi_realtime(self) -> Dict[str, Any]:
        """获取恒生指数实时数据"""
        try:
            df = ak.stock_hk_index_spot_em()
            hsi = df[df['代码'] == 'HSI']
            if hsi.empty:
                return {}
            row = hsi.iloc[0]
            return {
                'code': 'HSI',
                'name': '恒生指数',
                'price': float(row['最新价']) if pd.notna(row['最新价']) else 0,
                'pct_change': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                'change': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0,
                'high': float(row['最高']) if pd.notna(row['最高']) else 0,
                'low': float(row['最低']) if pd.notna(row['最低']) else 0,
                'open': float(row['今开']) if pd.notna(row['今开']) else 0,
                'pre_close': float(row['昨收']) if pd.notna(row['昨收']) else 0,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取恒生指数失败: {e}")
            return {}

    def get_hk_index_list(self) -> pd.DataFrame:
        """获取港股指数列表"""
        try:
            df = ak.stock_hk_index_spot_em()
            return df
        except Exception as e:
            logger.error(f"获取港股指数列表失败: {e}")
            return pd.DataFrame()

    def get_hsi_daily(self) -> pd.DataFrame:
        """获取恒生指数历史K线"""
        try:
            df = ak.stock_hk_index_daily_em(symbol="HSI")
            df['code'] = 'HSI'
            return df
        except Exception as e:
            logger.error(f"获取恒生指数历史K线失败: {e}")
            return pd.DataFrame()

    # ==================== 港股板块 ====================

    def get_hk_sector_list(self) -> pd.DataFrame:
        """获取港股行业板块列表"""
        try:
            df = ak.stock_hk_board_industry_em()
            return df
        except Exception as e:
            logger.error(f"获取港股行业板块列表失败: {e}")
            return pd.DataFrame()

    # ==================== 热门港股 ====================

    def get_hot_stocks(self, count: int = 20) -> pd.DataFrame:
        """
        获取热门港股排行
        Args:
            count: 返回数量
        """
        try:
            df = ak.stock_hk_spot_em()
            # 按成交额排序
            df_sorted = df.sort_values(by='成交额', ascending=False).head(count)
            return df_sorted
        except Exception as e:
            logger.error(f"获取热门港股失败: {e}")
            return pd.DataFrame()

    def get_top_gainers(self, count: int = 20) -> pd.DataFrame:
        """获取港股涨幅榜"""
        try:
            df = ak.stock_hk_spot_em()
            df_sorted = df.sort_values(by='涨跌幅', ascending=False).head(count)
            return df_sorted
        except Exception as e:
            logger.error(f"获取港股涨幅榜失败: {e}")
            return pd.DataFrame()

    def get_top_losers(self, count: int = 20) -> pd.DataFrame:
        """获取港股跌幅榜"""
        try:
            df = ak.stock_hk_spot_em()
            df_sorted = df.sort_values(by='涨跌幅', ascending=True).head(count)
            return df_sorted
        except Exception as e:
            logger.error(f"获取港股跌幅榜失败: {e}")
            return pd.DataFrame()


# 常用港股代码映射
HK_POPULAR_STOCKS = {
    '00700': '腾讯控股',
    '09988': '阿里巴巴-SW',
    '09618': '京东集团-SW',
    '03690': '美团-W',
    '01810': '小米集团-W',
    '00941': '中国移动',
    '00939': '建设银行',
    '01398': '工商银行',
    '03988': '中国银行',
    '02318': '中国平安',
    '00005': '汇丰控股',
    '00883': '中国海洋石油',
    '02020': '安踏体育',
    '09999': '网易-S',
    '00388': '香港交易所',
    '02269': '药明生物',
    '01024': '快手-W',
    '09888': '百度集团-SW',
    '06862': '海底捞',
    '01211': '比亚迪股份',
}


# 单例模式
_collector_instance = None


def get_hk_stock_collector() -> HKStockCollector:
    """获取港股数据采集器单例"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = HKStockCollector()
    return _collector_instance


# 测试
if __name__ == "__main__":
    collector = get_hk_stock_collector()
    
    # 测试获取股票列表
    print("=== 获取港股列表 ===")
    stock_list = collector.get_stock_list()
    print(stock_list.head())
    
    # 测试获取腾讯实时行情
    print("\n=== 获取腾讯控股实时行情 ===")
    quote = collector.get_realtime_quote("00700")
    print(quote)
    
    # 测试获取腾讯日K线
    print("\n=== 获取腾讯控股日K线 ===")
    kline = collector.get_daily_kline("00700", "20240101")
    print(kline.tail())
    
    # 测试获取恒生指数
    print("\n=== 获取恒生指数 ===")
    hsi = collector.get_hsi_realtime()
    print(hsi)
    
    # 测试获取热门港股
    print("\n=== 获取热门港股 ===")
    hot = collector.get_hot_stocks(10)
    print(hot[['代码', '名称', '最新价', '涨跌幅', '成交额']])