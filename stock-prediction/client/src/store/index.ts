import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { StockQuote, KLineData, WatchlistItem, MarketType, IndexQuote } from '../types'

// 应用状态接口
interface AppState {
  // 当前市场
  currentMarket: MarketType
  setCurrentMarket: (market: MarketType) => void

  // 当前选中的股票
  currentStock: StockQuote | null
  setCurrentStock: (stock: StockQuote | null) => void

  // K线数据
  klineData: KLineData[]
  setKlineData: (data: KLineData[]) => void

  // 自选股列表
  watchlist: WatchlistItem[]
  addToWatchlist: (item: WatchlistItem) => void
  removeFromWatchlist: (code: string, market: MarketType) => void
  isInWatchlist: (code: string, market: MarketType) => boolean

  // 主要指数
  indexes: {
    sh: IndexQuote | null
    sz: IndexQuote | null
    hsi: IndexQuote | null
  }
  setIndexes: (indexes: { sh: IndexQuote | null; sz: IndexQuote | null; hsi: IndexQuote | null }) => void

  // 加载状态
  loading: boolean
  setLoading: (loading: boolean) => void

  // 侧边栏折叠状态
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // 当前市场
      currentMarket: 'CN',
      setCurrentMarket: (market) => set({ currentMarket: market }),

      // 当前选中的股票
      currentStock: null,
      setCurrentStock: (stock) => set({ currentStock: stock }),

      // K线数据
      klineData: [],
      setKlineData: (data) => set({ klineData: data }),

      // 自选股列表
      watchlist: [],
      addToWatchlist: (item) => {
        const { watchlist, isInWatchlist } = get()
        if (!isInWatchlist(item.code, item.market)) {
          set({ watchlist: [...watchlist, item] })
        }
      },
      removeFromWatchlist: (code, market) => {
        const { watchlist } = get()
        set({
          watchlist: watchlist.filter(
            (item) => !(item.code === code && item.market === market)
          ),
        })
      },
      isInWatchlist: (code, market) => {
        const { watchlist } = get()
        return watchlist.some((item) => item.code === code && item.market === market)
      },

      // 主要指数
      indexes: { sh: null, sz: null, hsi: null },
      setIndexes: (indexes) => set({ indexes }),

      // 加载状态
      loading: false,
      setLoading: (loading) => set({ loading }),

      // 侧边栏折叠状态
      sidebarCollapsed: false,
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
    }),
    {
      name: 'stock-prediction-storage',
      partialize: (state) => ({
        watchlist: state.watchlist,
        currentMarket: state.currentMarket,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
)

// 搜索历史状态
interface SearchState {
  searchHistory: string[]
  addSearchHistory: (keyword: string) => void
  clearSearchHistory: () => void
}

export const useSearchStore = create<SearchState>()(
  persist(
    (set, get) => ({
      searchHistory: [],
      addSearchHistory: (keyword) => {
        const { searchHistory } = get()
        const newHistory = [keyword, ...searchHistory.filter((k) => k !== keyword)].slice(0, 10)
        set({ searchHistory: newHistory })
      },
      clearSearchHistory: () => set({ searchHistory: [] }),
    }),
    {
      name: 'stock-search-history',
    }
  )
)

export default useAppStore