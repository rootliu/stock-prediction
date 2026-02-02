import { FC } from 'react'
import type { IndexQuote } from '../types'

interface IndexBarProps {
  indexes: {
    sh: IndexQuote | null
    sz: IndexQuote | null
    hsi: IndexQuote | null
  }
}

const IndexBar: FC<IndexBarProps> = ({ indexes }) => {
  const renderIndex = (index: IndexQuote | null, name: string) => {
    if (!index) {
      return (
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 8,
          padding: '0 16px'
        }}>
          <span style={{ color: '#8c8c8c' }}>{name}</span>
          <span style={{ color: '#8c8c8c' }}>--</span>
        </div>
      )
    }

    const isUp = index.pct_change >= 0
    const color = isUp ? '#f5222d' : '#52c41a'

    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 8,
        padding: '0 16px',
        cursor: 'pointer',
        transition: 'background 0.3s',
      }}>
        <span style={{ color: '#595959', fontWeight: 500 }}>{index.name}</span>
        <span style={{ color, fontWeight: 'bold' }}>
          {index.price?.toFixed(2)}
        </span>
        <span style={{ 
          color,
          fontSize: 12,
          padding: '2px 6px',
          background: isUp ? 'rgba(245, 34, 45, 0.1)' : 'rgba(82, 196, 26, 0.1)',
          borderRadius: 4
        }}>
          {isUp ? '+' : ''}{index.pct_change?.toFixed(2)}%
        </span>
      </div>
    )
  }

  return (
    <div style={{ 
      background: '#fafafa', 
      borderBottom: '1px solid #f0f0f0',
      display: 'flex',
      alignItems: 'center',
      height: 40,
      overflow: 'hidden'
    }}>
      {renderIndex(indexes.sh, '上证指数')}
      <div style={{ width: 1, height: 20, background: '#e8e8e8' }} />
      {renderIndex(indexes.sz, '深证成指')}
      <div style={{ width: 1, height: 20, background: '#e8e8e8' }} />
      {renderIndex(indexes.hsi, '恒生指数')}
    </div>
  )
}

export default IndexBar