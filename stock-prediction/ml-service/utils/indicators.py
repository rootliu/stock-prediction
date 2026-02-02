"""
技术指标计算模块
计算常用股票技术分析指标
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from loguru import logger


class TechnicalIndicators:
    """技术指标计算器"""

    # ==================== 移动平均线 ====================

    @staticmethod
    def MA(close: pd.Series, period: int = 20) -> pd.Series:
        """
        简单移动平均线 (Simple Moving Average)
        Args:
            close: 收盘价序列
            period: 周期
        Returns:
            MA序列
        """
        return close.rolling(window=period).mean()

    @staticmethod
    def EMA(close: pd.Series, period: int = 20) -> pd.Series:
        """
        指数移动平均线 (Exponential Moving Average)
        Args:
            close: 收盘价序列
            period: 周期
        Returns:
            EMA序列
        """
        return close.ewm(span=period, adjust=False).mean()

    @staticmethod
    def SMA(close: pd.Series, period: int = 20, weight: int = 1) -> pd.Series:
        """
        加权移动平均线 (Smoothed Moving Average)
        """
        return close.ewm(alpha=weight / period, adjust=False).mean()

    # ==================== MACD ====================

    @staticmethod
    def MACD(
        close: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD指标 (Moving Average Convergence Divergence)
        Args:
            close: 收盘价序列
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
        Returns:
            (DIF, DEA, MACD柱)
        """
        ema_fast = close.ewm(span=fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=slow_period, adjust=False).mean()
        
        dif = ema_fast - ema_slow  # DIF线
        dea = dif.ewm(span=signal_period, adjust=False).mean()  # DEA线/信号线
        macd = (dif - dea) * 2  # MACD柱状图
        
        return dif, dea, macd

    # ==================== KDJ ====================

    @staticmethod
    def KDJ(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        KDJ随机指标
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            n: RSV周期
            m1: K值平滑周期
            m2: D值平滑周期
        Returns:
            (K, D, J)
        """
        lowest_low = low.rolling(window=n).min()
        highest_high = high.rolling(window=n).max()
        
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        rsv = rsv.fillna(50)
        
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return k, d, j

    # ==================== RSI ====================

    @staticmethod
    def RSI(close: pd.Series, period: int = 14) -> pd.Series:
        """
        相对强弱指数 (Relative Strength Index)
        Args:
            close: 收盘价序列
            period: 周期
        Returns:
            RSI序列 (0-100)
        """
        delta = close.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    # ==================== 布林带 ====================

    @staticmethod
    def BOLL(
        close: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        布林带 (Bollinger Bands)
        Args:
            close: 收盘价序列
            period: 周期
            std_dev: 标准差倍数
        Returns:
            (上轨, 中轨, 下轨)
        """
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        return upper, middle, lower

    # ==================== ATR ====================

    @staticmethod
    def ATR(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        平均真实波幅 (Average True Range)
        """
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(span=period, adjust=False).mean()
        
        return atr

    # ==================== OBV ====================

    @staticmethod
    def OBV(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        能量潮指标 (On Balance Volume)
        """
        direction = np.sign(close.diff())
        direction.iloc[0] = 0
        
        obv = (direction * volume).cumsum()
        return obv

    # ==================== CCI ====================

    @staticmethod
    def CCI(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        顺势指标 (Commodity Channel Index)
        """
        tp = (high + low + close) / 3
        ma = tp.rolling(window=period).mean()
        md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        
        cci = (tp - ma) / (0.015 * md)
        return cci

    # ==================== WR (威廉指标) ====================

    @staticmethod
    def WR(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        威廉指标 (Williams %R)
        返回值范围: -100 到 0
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        
        wr = (highest_high - close) / (highest_high - lowest_low) * -100
        return wr

    # ==================== DMI ====================

    @staticmethod
    def DMI(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        趋向指标 (Directional Movement Index)
        Returns:
            (+DI, -DI, ADX)
        """
        # 计算方向变动
        up_move = high.diff()
        down_move = -low.diff()
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_dm = pd.Series(plus_dm, index=high.index)
        minus_dm = pd.Series(minus_dm, index=high.index)
        
        # 计算ATR
        atr = TechnicalIndicators.ATR(high, low, close, period)
        
        # 计算+DI和-DI
        plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
        minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr
        
        # 计算ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return plus_di, minus_di, adx

    # ==================== BIAS (乖离率) ====================

    @staticmethod
    def BIAS(close: pd.Series, period: int = 6) -> pd.Series:
        """
        乖离率
        """
        ma = close.rolling(window=period).mean()
        bias = (close - ma) / ma * 100
        return bias

    # ==================== PSY (心理线) ====================

    @staticmethod
    def PSY(close: pd.Series, period: int = 12) -> pd.Series:
        """
        心理线指标
        """
        up_days = (close.diff() > 0).astype(int)
        psy = up_days.rolling(window=period).sum() / period * 100
        return psy

    # ==================== 成交量指标 ====================

    @staticmethod
    def VWAP(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        成交量加权平均价格 (Volume Weighted Average Price)
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap

    @staticmethod
    def VR(
        close: pd.Series,
        volume: pd.Series,
        period: int = 26
    ) -> pd.Series:
        """
        成交量比率 (Volume Ratio)
        """
        up_vol = volume.where(close.diff() > 0, 0)
        down_vol = volume.where(close.diff() < 0, 0)
        flat_vol = volume.where(close.diff() == 0, 0)
        
        avs = up_vol.rolling(window=period).sum()
        bvs = down_vol.rolling(window=period).sum()
        cvs = flat_vol.rolling(window=period).sum()
        
        vr = (avs + cvs / 2) / (bvs + cvs / 2) * 100
        return vr


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有技术指标并添加到DataFrame
    Args:
        df: 包含 open, high, low, close, volume 的DataFrame
    Returns:
        添加了技术指标的DataFrame
    """
    ti = TechnicalIndicators()
    
    # 确保必要的列存在
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"缺少必要的列: {col}")
    
    # 复制DataFrame避免修改原数据
    result = df.copy()
    
    # 移动平均线
    result['ma5'] = ti.MA(df['close'], 5)
    result['ma10'] = ti.MA(df['close'], 10)
    result['ma20'] = ti.MA(df['close'], 20)
    result['ma60'] = ti.MA(df['close'], 60)
    result['ema12'] = ti.EMA(df['close'], 12)
    result['ema26'] = ti.EMA(df['close'], 26)
    
    # MACD
    result['dif'], result['dea'], result['macd'] = ti.MACD(df['close'])
    
    # KDJ
    result['k'], result['d'], result['j'] = ti.KDJ(df['high'], df['low'], df['close'])
    
    # RSI
    result['rsi6'] = ti.RSI(df['close'], 6)
    result['rsi12'] = ti.RSI(df['close'], 12)
    result['rsi24'] = ti.RSI(df['close'], 24)
    
    # 布林带
    result['boll_upper'], result['boll_mid'], result['boll_lower'] = ti.BOLL(df['close'])
    
    # ATR
    result['atr'] = ti.ATR(df['high'], df['low'], df['close'])
    
    # OBV
    result['obv'] = ti.OBV(df['close'], df['volume'])
    
    # CCI
    result['cci'] = ti.CCI(df['high'], df['low'], df['close'])
    
    # WR
    result['wr'] = ti.WR(df['high'], df['low'], df['close'])
    
    # BIAS
    result['bias6'] = ti.BIAS(df['close'], 6)
    result['bias12'] = ti.BIAS(df['close'], 12)
    
    # PSY
    result['psy'] = ti.PSY(df['close'])
    
    # VWAP
    result['vwap'] = ti.VWAP(df['high'], df['low'], df['close'], df['volume'])
    
    logger.info(f"计算完成，共 {len(result.columns) - len(df.columns)} 个技术指标")
    return result


# 测试
if __name__ == "__main__":
    # 创建测试数据
    np.random.seed(42)
    n = 100
    dates = pd.date_range('2024-01-01', periods=n)
    
    # 模拟价格数据
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_price = close + np.random.randn(n) * 0.2
    volume = np.random.randint(1000000, 10000000, n)
    
    df = pd.DataFrame({
        'date': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    
    # 计算所有指标
    result = calculate_all_indicators(df)
    print("=== 技术指标计算结果 ===")
    print(result.tail())
    print(f"\n总列数: {len(result.columns)}")
    print(f"指标列: {[col for col in result.columns if col not in df.columns]}")