import { FC, useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { Alert, Radio, Select, Space, Spin, Statistic, Tabs, Tag, Typography, message } from 'antd'
import { goldApi } from '../services/api'
import type {
  GoldCompareResponse,
  GoldMarketsResponse,
  GoldPredictResponse,
  GoldQuote,
  GoldSessionResponse,
  GoldSource,
} from '../types'

const { Text } = Typography

const SOURCE_COLORS: Record<string, string> = {
  SHFE_AU_MAIN: '#f5222d',
  COMEX: '#1677ff',
  LBMA_SPOT: '#13c2c2',
  US_ETF: '#722ed1',
}

const SOURCE_LABELS: Record<string, string> = {
  SHFE_AU_MAIN: '国内 AU 主力',
  COMEX: 'COMEX',
  LBMA_SPOT: 'XAUUSD',
  US_ETF: 'GLD',
}

const GoldTrendChart: FC = () => {
  const [markets, setMarkets] = useState<GoldMarketsResponse | null>(null)
  const [sources, setSources] = useState<GoldSource[]>([])
  const [selectedSource, setSelectedSource] = useState<string>('')
  const [horizon, setHorizon] = useState<number>(5)
  const [sessionPeriod, setSessionPeriod] = useState<'5min' | '15min' | '30min' | '60min'>('5min')

  const [loadingPredict, setLoadingPredict] = useState(false)
  const [loadingCompare, setLoadingCompare] = useState(false)
  const [loadingSession, setLoadingSession] = useState(false)

  const [quote, setQuote] = useState<GoldQuote | null>(null)
  const [predictData, setPredictData] = useState<GoldPredictResponse | null>(null)
  const [compareData, setCompareData] = useState<GoldCompareResponse | null>(null)
  const [sessionData, setSessionData] = useState<GoldSessionResponse | null>(null)

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const [marketRes, sourceRes] = await Promise.all([
          goldApi.getMarkets(),
          goldApi.getSources('ALL'),
        ])
        setMarkets(marketRes)
        setSources(sourceRes.data || [])
        setSelectedSource(marketRes.default_predict_source || sourceRes.data?.[0]?.source || '')
      } catch (error) {
        console.error('初始化黄金模块失败:', error)
        message.error('初始化黄金模块失败')
      }
    }

    bootstrap()
  }, [])

  useEffect(() => {
    if (!selectedSource) return

    const fetchPredictView = async () => {
      setLoadingPredict(true)
      try {
        const [quoteRes, predictRes] = await Promise.all([
          goldApi.getQuote(selectedSource),
          goldApi.predict(selectedSource, horizon, 240),
        ])
        setQuote(quoteRes)
        setPredictData(predictRes)
      } catch (error) {
        console.error('获取黄金预测视图失败:', error)
        message.error('获取黄金预测视图失败')
      } finally {
        setLoadingPredict(false)
      }
    }

    fetchPredictView()
  }, [selectedSource, horizon])

  useEffect(() => {
    const fetchCompareView = async () => {
      setLoadingCompare(true)
      try {
        const res = await goldApi.getCompare('ALL', 'daily', 'ALL')
        setCompareData(res)
      } catch (error) {
        console.error('获取国内国外黄金对比失败:', error)
        message.error('获取国内国外黄金对比失败')
      } finally {
        setLoadingCompare(false)
      }
    }

    fetchCompareView()
  }, [])

  useEffect(() => {
    const fetchSessionView = async () => {
      setLoadingSession(true)
      try {
        const sessionSource = markets?.default_session_source || 'SHFE_AU_MAIN'
        const res = await goldApi.getSession(sessionSource, sessionPeriod, 5)
        setSessionData(res)
      } catch (error) {
        console.error('获取黄金夜盘走势失败:', error)
        message.error('获取黄金夜盘走势失败')
      } finally {
        setLoadingSession(false)
      }
    }

    fetchSessionView()
  }, [markets, sessionPeriod])

  const selectedMeta = sources.find(item => item.source === selectedSource)

  const buildPredictionOption = () => {
    if (!predictData) return {}

    const historyDates = predictData.history.map(item => item.date)
    const predictionDates = predictData.prediction.map(item => item.date)
    const allDates = [...historyDates, ...predictionDates]

    return {
      tooltip: {
        trigger: 'axis',
      },
      legend: {
        top: 8,
        data: ['实际价格', '预测价格'],
      },
      grid: {
        left: '6%',
        right: '4%',
        top: 48,
        bottom: 70,
      },
      xAxis: {
        type: 'category',
        data: allDates,
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        scale: true,
      },
      dataZoom: [
        { type: 'inside', start: 55, end: 100 },
        { type: 'slider', start: 55, end: 100, bottom: 18 },
      ],
      series: [
        {
          name: '实际价格',
          type: 'line',
          data: [
            ...predictData.history.map(item => Number(item.close.toFixed(2))),
            ...predictData.prediction.map(() => null),
          ],
          showSymbol: false,
          lineStyle: { color: '#1677ff', width: 2 },
          itemStyle: { color: '#1677ff' },
        },
        {
          name: '预测价格',
          type: 'line',
          data: [
            ...predictData.history.map(() => null),
            ...predictData.prediction.map(item => Number(item.close.toFixed(2))),
          ],
          showSymbol: true,
          symbolSize: 6,
          lineStyle: { color: '#fa8c16', width: 2, type: 'dashed' },
          itemStyle: { color: '#fa8c16' },
        },
      ],
    }
  }

  const buildCompareOption = () => {
    if (!compareData) return {}

    const dates = compareData.data.map(item => item.date)
    const series = compareData.sources.map(source => {
      let baseValue: number | null = null
      const normalizedData = compareData.data.map(item => {
        const rawValue = item[source]
        if (typeof rawValue !== 'number') {
          return null
        }
        if (baseValue === null) {
          baseValue = rawValue
        }
        return Number(((rawValue / baseValue) * 100).toFixed(2))
      })

      return {
        name: SOURCE_LABELS[source] || source,
        type: 'line',
        data: normalizedData,
        showSymbol: false,
        lineStyle: {
          width: source === 'SHFE_AU_MAIN' ? 3 : 2,
          color: SOURCE_COLORS[source] || '#595959',
        },
        itemStyle: {
          color: SOURCE_COLORS[source] || '#595959',
        },
      }
    })

    return {
      tooltip: {
        trigger: 'axis',
      },
      legend: {
        top: 8,
      },
      grid: {
        left: '6%',
        right: '4%',
        top: 48,
        bottom: 70,
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        name: '归一化指数',
        scale: true,
      },
      dataZoom: [
        { type: 'inside', start: 55, end: 100 },
        { type: 'slider', start: 55, end: 100, bottom: 18 },
      ],
      series,
    }
  }

  const buildSessionOption = () => {
    if (!sessionData) return {}

    const dates = sessionData.data.map(item => item.date)
    const daySeries = sessionData.data.map(item => (item.session === 'DAY' ? item.close : null))
    const nightSeries = sessionData.data.map(item => (item.session === 'NIGHT' ? item.close : null))

    return {
      tooltip: {
        trigger: 'axis',
      },
      legend: {
        top: 8,
        data: ['白盘', '夜盘'],
      },
      grid: {
        left: '6%',
        right: '4%',
        top: 48,
        bottom: 70,
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        scale: true,
      },
      dataZoom: [
        { type: 'inside', start: 60, end: 100 },
        { type: 'slider', start: 60, end: 100, bottom: 18 },
      ],
      series: [
        {
          name: '白盘',
          type: 'line',
          data: daySeries,
          showSymbol: false,
          lineStyle: { color: '#13c2c2', width: 2 },
          itemStyle: { color: '#13c2c2' },
        },
        {
          name: '夜盘',
          type: 'line',
          data: nightSeries,
          showSymbol: false,
          lineStyle: { color: '#fa541c', width: 2 },
          itemStyle: { color: '#fa541c' },
        },
      ],
    }
  }

  const renderChart = (loading: boolean, hasData: boolean, option: object, emptyText: string) => {
    if (loading) {
      return (
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Spin />
        </div>
      )
    }

    if (!hasData) {
      return (
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#8c8c8c',
          }}
        >
          {emptyText}
        </div>
      )
    }

    return <ReactECharts option={option} style={{ height: '100%', width: '100%' }} opts={{ renderer: 'canvas' }} />
  }

  const tabItems = [
    {
      key: 'predict',
      label: '预测走势',
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: 12,
            }}
          >
            <Space wrap>
              <Select
                style={{ width: 280 }}
                value={selectedSource || undefined}
                placeholder="选择黄金数据来源"
                options={sources.map(item => ({
                  value: item.source,
                  label: `${item.market_group === 'DOMESTIC' ? '国内' : '国外'} | ${item.name}`,
                }))}
                onChange={setSelectedSource}
              />
              <Radio.Group
                value={horizon}
                onChange={(e) => setHorizon(e.target.value)}
                optionType="button"
                buttonStyle="solid"
                size="small"
              >
                <Radio.Button value={5}>预测5天</Radio.Button>
                <Radio.Button value={10}>预测10天</Radio.Button>
                <Radio.Button value={20}>预测20天</Radio.Button>
              </Radio.Group>
            </Space>

            {quote && (
              <Space size={20}>
                <Statistic title="最新价格" value={quote.price} precision={2} valueStyle={{ fontSize: 20 }} />
                <Statistic
                  title="涨跌幅"
                  value={quote.pct_change}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: quote.pct_change >= 0 ? '#f5222d' : '#52c41a', fontSize: 18 }}
                />
              </Space>
            )}
          </div>

          {selectedMeta && (
            <Alert
              type="info"
              showIcon
              message={`${selectedMeta.name} | ${selectedMeta.exchange}`}
              description={selectedMeta.description}
            />
          )}

          <div style={{ height: 460 }}>
            {renderChart(loadingPredict, !!predictData, buildPredictionOption(), '暂无黄金预测数据')}
          </div>

          {predictData && (
            <Space size={24} wrap>
              <Tag color={selectedMeta?.market_group === 'DOMESTIC' ? 'red' : 'blue'}>
                {selectedMeta?.market_group === 'DOMESTIC' ? '国内黄金' : '国外黄金'}
              </Tag>
              <Text type="secondary">MAE: {predictData.metrics.mae?.toFixed(4) ?? '--'}</Text>
              <Text type="secondary">MAPE: {predictData.metrics.mape?.toFixed(2) ?? '--'}%</Text>
              <Text type="secondary">模型: {predictData.model.name}</Text>
            </Space>
          )}
        </div>
      ),
    },
    {
      key: 'compare',
      label: '国内/国外',
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Alert
            type="warning"
            showIcon
            message="国内与国外黄金单位不同，这里展示的是归一化走势对比"
            description="所有曲线都按各自起点换算为 100，用于观察联动强弱和趋势同步性，而不是绝对价格。"
          />
          <div style={{ height: 500 }}>
            {renderChart(loadingCompare, !!compareData, buildCompareOption(), '暂无国内国外黄金对比数据')}
          </div>
        </div>
      ),
    },
    {
      key: 'session',
      label: '夜盘走势',
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <Alert
              type="info"
              showIcon
              message="国内黄金白盘 / 夜盘"
              description="当前展示 SHFE 黄金主力连续合约最近 5 天的白盘与夜盘分时走势。"
              style={{ flex: 1 }}
            />
            <Radio.Group
              value={sessionPeriod}
              onChange={(e) => setSessionPeriod(e.target.value)}
              optionType="button"
              buttonStyle="solid"
              size="small"
            >
              <Radio.Button value="5min">5 分钟</Radio.Button>
              <Radio.Button value="15min">15 分钟</Radio.Button>
              <Radio.Button value="30min">30 分钟</Radio.Button>
              <Radio.Button value="60min">60 分钟</Radio.Button>
            </Radio.Group>
          </div>

          <div style={{ height: 500 }}>
            {renderChart(loadingSession, !!sessionData, buildSessionOption(), '暂无黄金白盘/夜盘数据')}
          </div>
        </div>
      ),
    },
  ]

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>黄金市场分析</div>
          <Text type="secondary">覆盖国内、国外与夜盘时段视图</Text>
        </div>
        {markets && (
          <Space wrap>
            {markets.groups.map(group => (
              <Tag key={group.key} color={group.key === 'NIGHT' ? 'orange' : group.key === 'DOMESTIC' ? 'red' : group.key === 'FOREIGN' ? 'blue' : 'default'}>
                {group.label}
              </Tag>
            ))}
          </Space>
        )}
      </div>

      <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: 12 }}>
        <Tabs defaultActiveKey="predict" items={tabItems} />
      </div>
    </div>
  )
}

export default GoldTrendChart
