import { useState, useEffect } from 'react'
import { Layout, Menu, Input, Tabs, message, Spin } from 'antd'
import {
  StockOutlined,
  LineChartOutlined,
  StarOutlined,
  SearchOutlined,
  GlobalOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons'
import { useAppStore } from './store'
import { stockApi } from './services/api'
import StockList from './components/StockList'
import KLineChart from './components/KLineChart'
import IndexBar from './components/IndexBar'
import type { MarketType } from './types'

const { Header, Sider, Content } = Layout
const { Search } = Input

function App() {
  const { 
    currentMarket, 
    setCurrentMarket,
    currentStock,
    setCurrentStock,
    indexes,
    setIndexes,
    loading,
    setLoading,
    watchlist,
  } = useAppStore()

  const [searchValue, setSearchValue] = useState('')

  // 初始化加载指数数据
  useEffect(() => {
    const fetchIndexes = async () => {
      try {
        const data = await stockApi.getMainIndexes()
        setIndexes(data)
      } catch (error) {
        console.error('获取指数失败:', error)
      }
    }
    fetchIndexes()
    
    // 每30秒刷新一次指数
    const interval = setInterval(fetchIndexes, 30000)
    return () => clearInterval(interval)
  }, [setIndexes])

  // 搜索股票
  const handleSearch = async (value: string) => {
    if (!value.trim()) return
    setLoading(true)
    try {
      // 尝试根据代码直接获取行情
      const quote = await stockApi.getQuote(value.trim(), currentMarket)
      if (quote) {
        setCurrentStock(quote)
        message.success(`找到股票: ${quote.name}`)
      }
    } catch (error) {
      message.error('未找到该股票')
    } finally {
      setLoading(false)
    }
  }

  // 切换市场
  const handleMarketChange = (market: string) => {
    setCurrentMarket(market as MarketType)
    setCurrentStock(null)
  }

  const marketTabs = [
    { key: 'CN', label: 'A股', icon: <RiseOutlined /> },
    { key: 'HK', label: '港股', icon: <GlobalOutlined /> },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 顶部导航 */}
      <Header style={{ 
        background: '#001529', 
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <div style={{ 
            color: '#fff', 
            fontSize: 20, 
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <LineChartOutlined />
            股票预测分析系统
          </div>
          
          {/* 市场切换 */}
          <Tabs
            activeKey={currentMarket}
            onChange={handleMarketChange}
            items={marketTabs}
            style={{ marginBottom: 0 }}
            tabBarStyle={{ marginBottom: 0 }}
          />
        </div>

        {/* 搜索框 */}
        <Search
          placeholder="输入股票代码或名称"
          allowClear
          style={{ width: 300 }}
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onSearch={handleSearch}
          prefix={<SearchOutlined />}
        />
      </Header>

      {/* 指数行情条 */}
      <IndexBar indexes={indexes} />

      <Layout>
        {/* 左侧边栏 - 股票列表 */}
        <Sider
          width={320}
          style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}
        >
          <Tabs
            defaultActiveKey="list"
            style={{ height: '100%' }}
            items={[
              {
                key: 'list',
                label: (
                  <span>
                    <StockOutlined />
                    行情列表
                  </span>
                ),
                children: <StockList market={currentMarket} />,
              },
              {
                key: 'watchlist',
                label: (
                  <span>
                    <StarOutlined />
                    自选股 ({watchlist.length})
                  </span>
                ),
                children: <StockList market={currentMarket} isWatchlist />,
              },
            ]}
          />
        </Sider>

        {/* 主内容区 - K线图 */}
        <Content style={{ padding: 16, background: '#f5f5f5' }}>
          <Spin spinning={loading}>
            {currentStock ? (
              <div style={{ 
                background: '#fff', 
                borderRadius: 8,
                padding: 16,
                height: 'calc(100vh - 180px)'
              }}>
                <div style={{ 
                  marginBottom: 16,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <span style={{ fontSize: 20, fontWeight: 'bold', marginRight: 8 }}>
                      {currentStock.name}
                    </span>
                    <span style={{ color: '#8c8c8c' }}>
                      {currentStock.code}
                    </span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ 
                      fontSize: 24, 
                      fontWeight: 'bold',
                      color: currentStock.pct_change >= 0 ? '#f5222d' : '#52c41a'
                    }}>
                      {currentStock.price?.toFixed(2)}
                    </div>
                    <div style={{ 
                      color: currentStock.pct_change >= 0 ? '#f5222d' : '#52c41a'
                    }}>
                      {currentStock.pct_change >= 0 ? '+' : ''}
                      {currentStock.pct_change?.toFixed(2)}%
                      ({currentStock.change >= 0 ? '+' : ''}{currentStock.change?.toFixed(2)})
                    </div>
                  </div>
                </div>
                <KLineChart 
                  symbol={currentStock.code} 
                  market={currentStock.market || currentMarket}
                />
              </div>
            ) : (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                height: 'calc(100vh - 180px)',
                background: '#fff',
                borderRadius: 8,
                color: '#8c8c8c'
              }}>
                <div style={{ textAlign: 'center' }}>
                  <LineChartOutlined style={{ fontSize: 64, marginBottom: 16 }} />
                  <div style={{ fontSize: 16 }}>请选择一只股票查看详情</div>
                </div>
              </div>
            )}
          </Spin>
        </Content>
      </Layout>
    </Layout>
  )
}

export default App