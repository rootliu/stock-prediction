import { FC, useEffect, useMemo, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { Alert, Radio, Select, Space, Spin, Statistic, Typography, message } from 'antd'
import { goldApi } from '../services/api'
import type { GoldPredictResponse, GoldQuote, GoldSource } from '../types'

const { Text } = Typography

const GoldTrendChart: FC = () => {
  const [sources, setSources] = useState<GoldSource[]>([])
  const [selectedSource, setSelectedSource] = useState<string>('')
  const [horizon, setHorizon] = useState<number>(5)
  const [loading, setLoading] = useState(false)
  const [quote, setQuote] = useState<GoldQuote | null>(null)
  const [predictData, setPredictData] = useState<GoldPredictResponse | null>(null)

  useEffect(() => {
    const fetchSources = async () => {
      try {
        const res = await goldApi.getSources()
        const list = res.data || []
        setSources(list)
        if (list.length > 0) {
          setSelectedSource(list[0].source)
        }
      } catch (error) {
        console.error('获取黄金来源失败:', error)
        message.error('获取黄金来源失败')
      }
    }

    fetchSources()
  }, [])

  useEffect(() => {
    if (!selectedSource) return

    const fetchData = async () => {
      setLoading(true)
      try {
        const [quoteRes, predictRes] = await Promise.all([
          goldApi.getQuote(selectedSource),
          goldApi.predict(selectedSource, horizon, 240),
        ])
        setQuote(quoteRes)
        setPredictData(predictRes)
      } catch (error) {
        console.error('获取黄金走势失败:', error)
        message.error('获取黄金走势失败')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [selectedSource, horizon])

  const chartOption = useMemo(() => {
    if (!predictData) return {}

    const historyDates = predictData.history.map(item => item.date)
    const predictionDates = predictData.prediction.map(item => item.date)
    const allDates = [...historyDates, ...predictionDates]

    const actualSeries = [
      ...predictData.history.map(item => Number(item.close.toFixed(2))),
      ...predictData.prediction.map(() => null),
    ]

    const predictionSeries = [
      ...predictData.history.map(() => null),
      ...predictData.prediction.map(item => Number(item.close.toFixed(2))),
    ]

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
        axisLabel: {
          formatter: '{value}',
        },
      },
      dataZoom: [
        {
          type: 'inside',
          start: 55,
          end: 100,
        },
        {
          type: 'slider',
          start: 55,
          end: 100,
          bottom: 18,
        },
      ],
      series: [
        {
          name: '实际价格',
          type: 'line',
          data: actualSeries,
          showSymbol: false,
          lineStyle: {
            color: '#1677ff',
            width: 2,
          },
          itemStyle: {
            color: '#1677ff',
          },
        },
        {
          name: '预测价格',
          type: 'line',
          data: predictionSeries,
          showSymbol: true,
          symbolSize: 6,
          lineStyle: {
            color: '#fa8c16',
            width: 2,
            type: 'dashed',
          },
          itemStyle: {
            color: '#fa8c16',
          },
        },
      ],
    }
  }, [predictData])

  const selectedMeta = useMemo(
    () => sources.find(item => item.source === selectedSource),
    [sources, selectedSource]
  )

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}>
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
            style={{ width: 240 }}
            value={selectedSource || undefined}
            placeholder="选择黄金数据来源"
            options={sources.map(item => ({ value: item.source, label: `${item.source} (${item.symbol})` }))}
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
            <Statistic
              title="最新价格"
              value={quote.price}
              precision={2}
              valueStyle={{ fontSize: 20 }}
            />
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

      <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: 12 }}>
        {loading ? (
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
        ) : predictData ? (
          <ReactECharts option={chartOption} style={{ height: '100%', width: '100%' }} opts={{ renderer: 'canvas' }} />
        ) : (
          <div
            style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#8c8c8c',
            }}
          >
            暂无黄金走势数据
          </div>
        )}
      </div>

      {predictData && (
        <Space size={24}>
          <Text type="secondary">单位: 日线</Text>
          <Text type="secondary">MAE: {predictData.metrics.mae?.toFixed(4) ?? '--'}</Text>
          <Text type="secondary">MAPE: {predictData.metrics.mape?.toFixed(2) ?? '--'}%</Text>
          <Text type="secondary">模型: {predictData.model.name}</Text>
        </Space>
      )}
    </div>
  )
}

export default GoldTrendChart
