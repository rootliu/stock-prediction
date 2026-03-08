// 股票行情
export interface StockQuote {
  code: string
  name: string
  price: number
  pct_change: number
  change: number
  volume: number
  amount: number
  high?: number
  low?: number
  open?: number
  pre_close?: number
  turnover_rate?: number
  pe_ratio?: number
  pb_ratio?: number
  market?: 'CN' | 'HK'
  timestamp?: string
}

// K线数据
export interface KLineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  pct_change?: number
}

// K线响应
export interface KLineResponse {
  code: string
  name?: string
  market: string
  period: string
  data: KLineData[]
}

// 指数行情
export interface IndexQuote {
  code: string
  name: string
  price: number
  pct_change: number
  change: number
  volume?: number
  amount?: number
  timestamp: string
}

// 技术指标
export interface TechnicalIndicators {
  ma5?: number
  ma10?: number
  ma20?: number
  ma60?: number
  ema12?: number
  ema26?: number
  dif?: number
  dea?: number
  macd?: number
  k?: number
  d?: number
  j?: number
  rsi6?: number
  rsi12?: number
  rsi24?: number
  boll_upper?: number
  boll_mid?: number
  boll_lower?: number
  atr?: number
  obv?: number
  cci?: number
  wr?: number
  bias6?: number
  bias12?: number
  psy?: number
  vwap?: number
}

// 股票详情（含技术指标）
export interface StockDetail extends StockQuote {
  kline?: KLineData[]
  indicators?: TechnicalIndicators
}

// 自选股
export interface WatchlistItem {
  code: string
  name: string
  market: 'CN' | 'HK'
  addedAt: string
}

// 市场类型
export type MarketType = 'CN' | 'HK' | 'GOLD'

// K线周期
export type KLinePeriod = 'daily' | 'weekly' | 'monthly' | '5min' | '15min' | '30min' | '60min'

// 复权类型
export type AdjustType = 'qfq' | 'hfq' | ''

// API响应
export interface ApiResponse<T> {
  data: T
  total?: number
  message?: string
}

// 资金流向
export interface FundFlow {
  timestamp: string
  hk_sh?: Record<string, number>
  hk_sz?: Record<string, number>
  sh_hk?: Record<string, number>
  sz_hk?: Record<string, number>
}

// 板块数据
export interface Sector {
  code: string
  name: string
  pct_change: number
  volume: number
  amount: number
  leading_stock?: string
}

// 搜索结果
export interface SearchResult {
  code: string
  name: string
  market: 'CN' | 'HK'
  type: 'stock' | 'index' | 'etf'
}

// 黄金来源
export interface GoldSource {
  source: string
  symbol: string
  name: string
  exchange: string
  description: string
}

// 黄金行情快照
export interface GoldQuote {
  source: string
  symbol: string
  name: string
  price: number
  change: number
  pct_change: number
  high: number
  low: number
  open: number
  volume: number
  timestamp: string
}

// 预测点
export interface PredictionPoint {
  date: string
  close: number
}

// 预测评估指标
export interface PredictionMetrics {
  mae: number | null
  mape: number | null
  train_size: number
  test_size: number
}

// 黄金预测响应
export interface GoldPredictResponse {
  source: string
  symbol: string
  name: string
  history: PredictionPoint[]
  prediction: PredictionPoint[]
  metrics: PredictionMetrics
  model: {
    name: string
    feature_count: number
  }
}
