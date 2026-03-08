"""
数据采集模块
"""

from .a_stock import AStockCollector, get_a_stock_collector
from .hk_stock import HKStockCollector, get_hk_stock_collector
from .gold_market import GoldMarketCollector, get_gold_market_collector

__all__ = [
    'AStockCollector',
    'get_a_stock_collector',
    'HKStockCollector',
    'get_hk_stock_collector',
    'GoldMarketCollector',
    'get_gold_market_collector',
]
