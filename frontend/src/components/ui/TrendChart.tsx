import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts'

interface DataPoint {
  value: number
  time?: string
}

interface Props {
  data: DataPoint[]
  color?: string
  height?: number
}

export function TrendChart({ data, color = '#06b6d4', height = 50 }: Props) {
  if (data.length < 2) {
    return <div className="h-[50px] flex items-center justify-center text-text-dim text-xs">No data</div>
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
        <defs>
          <linearGradient id={`grad-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Tooltip
          contentStyle={{ background: '#1a1d27', border: '1px solid #2a2d3e', borderRadius: 6, fontSize: 11 }}
          itemStyle={{ color: color }}
          labelFormatter={() => ''}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#grad-${color.replace('#','')})`}
          dot={false}
          connectNulls={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
