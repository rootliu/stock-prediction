import { FC, useEffect, useState, useRef } from 'react'
import ReactECharts from 'echarts-for-react'
import { Spin, Radio, message } from 'antd'
import { stockApi } from '../services/api'
import type { KLineData, MarketType, KLinePeriod } from '../types'

interface KLineChartProps {
  symbol: string
  market: MarketType
}

const KLineChart: FC<KLineChartProps> = ({ symbol, market }) => {
  const [klineData, setKlineData] = useState<KLineData[]>([])
  const [loading, setLoading] = useState(false)
  const [period, setPeriod] = useState<KLinePeriod>('daily')
  const chartRef = useRef<ReactECharts>(null)

  // 加载K线数据
  useEffect(() => {
    const fetchKline = async () => {
      setLoading(true)
      try {
        const res = await stockApi.getKline(symbol, market, period)
        setKlineData(res.data || [])
      } catch (error) {
        console.error('获取K线失败:', error)
        message.error('获取K线数据失败')
      } finally {
        setLoading(false)
      }
    }
    
    if (symbol) {
      fetchKline()
    }
  }, [symbol, market, period])

  // 生成ECharts配置
  const getOption = () => {
    if (klineData.length === 0) {
      return {}
    }

    const dates = klineData.map(item => item.date)
    const values = klineData.map(item => [item.open, item.close, item.low, item.high])
    const volumes = klineData.map(item => item.volume)

    // 计算MA均线
    const calculateMA = (dayCount: number) => {
      const result = []
      for (let i = 0; i < klineData.length; i++) {
        if (i < dayCount - 1) {
          result.push('-')
        } else {
          let sum = 0
          for (let j = 0; j < dayCount; j++) {
            sum += klineData[i - j].close
          }
          result.push((sum / dayCount).toFixed(2))
        }
      }
      return result
    }

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: (params: any) => {
          const data = klineData[params[0].dataIndex]
          if (!data) return ''
          return `
            <div style="padding: 8px">
              <div style="font-weight: bold; margin-bottom: 8px">${data.date}</div>
              <div>开盘: ${data.open.toFixed(2)}</div>
              <div>收盘: ${data.close.toFixed(2)}</div>
              <div>最高: ${data.high.toFixed(2)}</div>
              <div>最低: ${data.low.toFixed(2)}</div>
              <div>成交量: ${(data.volume / 10000).toFixed(2)}万手</div>
              ${data.pct_change !== undefined ? `<div>涨跌幅: ${data.pct_change.toFixed(2)}%</div>` : ''}
            </div>
          `
        }
      },
      legend: {
        data: ['K线', 'MA5', 'MA10', 'MA20', 'MA60'],
        top: 10,
        selected: {
          'MA60': false
        }
      },
      grid: [
        {
          left: '10%',
          right: '8%',
          top: 50,
          height: '55%'
        },
        {
          left: '10%',
          right: '8%',
          top: '72%',
          height: '16%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        }
      ],
      yAxis: [
        {
          scale: true,
          splitArea: {
            show: true
          }
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 50,
          end: 100
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          top: '90%',
          start: 50,
          end: 100
        }
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: values,
          itemStyle: {
            color: '#f5222d',      // 涨 - 红色
            color0: '#52c41a',     // 跌 - 绿色
            borderColor: '#f5222d',
            borderColor0: '#52c41a'
          }
        },
        {
          name: 'MA5',
          type: 'line',
          data: calculateMA(5),
          smooth: true,
          lineStyle: { opacity: 0.5, width: 1 },
          symbol: 'none'
        },
        {
          name: 'MA10',
          type: 'line',
          data: calculateMA(10),
          smooth: true,
          lineStyle: { opacity: 0.5, width: 1 },
          symbol: 'none'
        },
        {
          name: 'MA20',
          type: 'line',
          data: calculateMA(20),
          smooth: true,
          lineStyle: { opacity: 0.5, width: 1 },
          symbol: 'none'
        },
        {
          name: 'MA60',
          type: 'line',
          data: calculateMA(60),
          smooth: true,
          lineStyle: { opacity: 0.5, width: 1 },
          symbol: 'none'
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes.map((vol, idx) => ({
            value: vol,
            itemStyle: {
              color: klineData[idx].close >= klineData[idx].open ? '#f5222d' : '#52c41a'
            }
          }))
        }
      ]
    }
  }

  const periodOptions = [
    { label: '日K', value: 'daily' },
    { label: '周K', value: 'weekly' },
    { label: '月K', value: 'monthly' },
  ]

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 8 }}>
        <Radio.Group 
          value={period} 
          onChange={(e) => setPeriod(e.target.value)}
          optionType="button"
          buttonStyle="solid"
          size="small"
        >
          {periodOptions.map(opt => (
            <Radio.Button key={opt.value} value={opt.value}>
              {opt.label}
            </Radio.Button>
          ))}
        </Radio.Group>
      </div>

      <div style={{ flex: 1, minHeight: 0 }}>
        {loading ? (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            height: '100%'
          }}>
            <Spin />
          </div>
        ) : klineData.length > 0 ? (
          <ReactECharts
            ref={chartRef}
            option={getOption()}
            style={{ height: '100%', width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
        ) : (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            height: '100%',
            color: '#8c8c8c'
          }}>
            暂无K线数据
          </div>
        )}
      </div>
    </div>
  )
}

export default KLineChart
