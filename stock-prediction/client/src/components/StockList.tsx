import { FC, useState, useEffect } from 'react'
import { List, Space, Empty, Spin, Button } from 'antd'
import { StarOutlined, StarFilled } from '@ant-design/icons'
import { useAppStore } from '../store'
import { stockApi } from '../services/api'
import type { StockQuote } from '../types'

interface StockListProps {
  market: 'CN' | 'HK'
  isWatchlist?: boolean
}

const StockList: FC<StockListProps> = ({ market, isWatchlist = false }) => {
  const { 
    setCurrentStock, 
    watchlist, 
    addToWatchlist, 
    removeFromWatchlist,
    isInWatchlist 
  } = useAppStore()
  
  const [stocks, setStocks] = useState<StockQuote[]>([])
  const [loading, setLoading] = useState(false)

  // 加载股票列表
  useEffect(() => {
    if (isWatchlist) {
      // 如果是自选股，从watchlist获取并刷新数据
      const codes = watchlist
        .filter(item => item.market === market)
        .map(item => item.code)
      
      if (codes.length === 0) {
        setStocks([])
        return
      }

      setLoading(true)
      const api = market === 'CN' 
        ? import('../services/api').then(m => m.aStockApi.getBatchQuotes(codes))
        : import('../services/api').then(m => m.hkStockApi.getBatchQuotes(codes))
      
      api
        .then(res => setStocks(res.data || []))
        .catch(console.error)
        .finally(() => setLoading(false))
    } else {
      // 获取市场股票列表
      setLoading(true)
      stockApi.getList(market, 50)
        .then(res => setStocks(res.data || []))
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [market, isWatchlist, watchlist])

  // 处理点击股票
  const handleStockClick = (stock: StockQuote) => {
    setCurrentStock({
      ...stock,
      market
    })
  }

  // 切换自选
  const handleToggleWatchlist = (stock: StockQuote, e: React.MouseEvent) => {
    e.stopPropagation()
    if (isInWatchlist(stock.code, market)) {
      removeFromWatchlist(stock.code, market)
    } else {
      addToWatchlist({
        code: stock.code,
        name: stock.name,
        market,
        addedAt: new Date().toISOString()
      })
    }
  }

  // 渲染价格颜色
  const getPriceColor = (pctChange: number) => {
    if (pctChange > 0) return '#f5222d'
    if (pctChange < 0) return '#52c41a'
    return '#8c8c8c'
  }

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        height: 200
      }}>
        <Spin />
      </div>
    )
  }

  if (isWatchlist && stocks.length === 0) {
    return (
      <Empty
        description="暂无自选股"
        style={{ marginTop: 40 }}
      />
    )
  }

  return (
    <List
      size="small"
      dataSource={stocks}
      style={{ height: 'calc(100vh - 200px)', overflow: 'auto' }}
      renderItem={(stock) => {
        const inWatchlist = isInWatchlist(stock.code, market)
        const color = getPriceColor(stock.pct_change)

        return (
          <List.Item
            onClick={() => handleStockClick(stock)}
            style={{ 
              cursor: 'pointer',
              padding: '8px 12px',
              transition: 'background 0.3s'
            }}
            className="stock-list-item"
          >
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between',
              alignItems: 'center',
              width: '100%'
            }}>
              <div>
                <div style={{ fontWeight: 500 }}>{stock.name}</div>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>{stock.code}</div>
              </div>
              
              <Space>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ color, fontWeight: 'bold' }}>
                    {stock.price?.toFixed(2)}
                  </div>
                  <div style={{ 
                    fontSize: 12, 
                    color,
                    padding: '1px 4px',
                    background: stock.pct_change > 0 
                      ? 'rgba(245, 34, 45, 0.1)' 
                      : stock.pct_change < 0 
                        ? 'rgba(82, 196, 26, 0.1)' 
                        : 'transparent',
                    borderRadius: 2
                  }}>
                    {stock.pct_change > 0 ? '+' : ''}
                    {stock.pct_change?.toFixed(2)}%
                  </div>
                </div>
                
                <Button
                  type="text"
                  size="small"
                  icon={inWatchlist ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
                  onClick={(e) => handleToggleWatchlist(stock, e)}
                />
              </Space>
            </div>
          </List.Item>
        )
      }}
    />
  )
}

export default StockList
