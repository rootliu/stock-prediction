import axios from 'axios'
import type { 
  StockQuote, 
  KLineResponse, 
  IndexQuote, 
  ApiResponse,
  MarketType,
  KLinePeriod,
  AdjustType 
} from '../types'

// API基础配置
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// ==================== A股 API ====================

export const aStockApi = {
  // 获取A股列表
  getList: (limit = 100): Promise<ApiResponse<StockQuote[]>> => 
    api.get(`/a-stock/list?limit=${limit}`),

  // 获取单只股票实时行情
  getQuote: (symbol: string): Promise<StockQuote> => 
    api.get(`/a-stock/quote/${symbol}`),

  // 批量获取股票行情
  getBatchQuotes: (symbols: string[]): Promise<ApiResponse<StockQuote[]>> => 
    api.post('/a-stock/quotes', symbols),

  // 获取K线数据
  getKline: (
    symbol: string, 
    period: KLinePeriod = 'daily',
    startDate?: string,
    endDate?: string,
    adjust: AdjustType = 'qfq'
  ): Promise<KLineResponse> => {
    const params = new URLSearchParams()
    params.append('period', period)
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    params.append('adjust', adjust)
    return api.get(`/a-stock/kline/${symbol}?${params.toString()}`)
  },

  // 获取指数数据
  getIndex: (code = '000001'): Promise<IndexQuote> => 
    api.get(`/a-stock/index/${code}`),

  // 获取北向资金
  getNorthFlow: () => 
    api.get('/a-stock/north-flow'),

  // 获取板块列表
  getSectors: () => 
    api.get('/a-stock/sectors'),
}

// ==================== 港股 API ====================

export const hkStockApi = {
  // 获取港股列表
  getList: (limit = 100): Promise<ApiResponse<StockQuote[]>> => 
    api.get(`/hk-stock/list?limit=${limit}`),

  // 获取单只股票实时行情
  getQuote: (symbol: string): Promise<StockQuote> => 
    api.get(`/hk-stock/quote/${symbol}`),

  // 批量获取股票行情
  getBatchQuotes: (symbols: string[]): Promise<ApiResponse<StockQuote[]>> => 
    api.post('/hk-stock/quotes', symbols),

  // 获取K线数据
  getKline: (
    symbol: string, 
    period: KLinePeriod = 'daily',
    startDate?: string,
    endDate?: string,
    adjust: AdjustType = 'qfq'
  ): Promise<KLineResponse> => {
    const params = new URLSearchParams()
    params.append('period', period)
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    params.append('adjust', adjust)
    return api.get(`/hk-stock/kline/${symbol}?${params.toString()}`)
  },

  // 获取恒生指数
  getHSI: (): Promise<IndexQuote> => 
    api.get('/hk-stock/hsi'),

  // 获取南向资金
  getSouthFlow: () => 
    api.get('/hk-stock/south-flow'),

  // 获取热门港股
  getHotStocks: (count = 20) => 
    api.get(`/hk-stock/hot?count=${count}`),

  // 获取港股通标的
  getGGTStocks: () => 
    api.get('/hk-stock/ggt'),
}

// ==================== 技术指标 API ====================

export const indicatorApi = {
  // 计算技术指标
  calculate: (code: string, market: MarketType = 'CN', startDate?: string, endDate?: string) =>
    api.post('/indicators', { code, market, start_date: startDate, end_date: endDate }),

  // 获取最新指标值
  getLatest: (symbol: string, market: MarketType = 'CN') =>
    api.get(`/indicators/${symbol}?market=${market}`),
}

// ==================== 统一接口 ====================

export const stockApi = {
  // 根据市场类型获取股票列表
  getList: (market: MarketType, limit = 100) => 
    market === 'CN' ? aStockApi.getList(limit) : hkStockApi.getList(limit),

  // 根据市场类型获取股票行情
  getQuote: (symbol: string, market: MarketType) => 
    market === 'CN' ? aStockApi.getQuote(symbol) : hkStockApi.getQuote(symbol),

  // 根据市场类型获取K线
  getKline: (
    symbol: string, 
    market: MarketType,
    period: KLinePeriod = 'daily',
    startDate?: string,
    endDate?: string,
    adjust: AdjustType = 'qfq'
  ) => market === 'CN' 
    ? aStockApi.getKline(symbol, period, startDate, endDate, adjust)
    : hkStockApi.getKline(symbol, period, startDate, endDate, adjust),

  // 获取主要指数
  getMainIndexes: async () => {
    const [sh, sz, hsi] = await Promise.all([
      aStockApi.getIndex('000001').catch(() => null),
      aStockApi.getIndex('399001').catch(() => null),
      hkStockApi.getHSI().catch(() => null),
    ])
    return { sh, sz, hsi }
  },
}

export default api