import type { ReactNode } from 'react'

interface StatTileProps {
  label: string
  value: string | number
  unit?: string
  icon?: ReactNode
  color?: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
}

export default function StatTile({ label, value, unit, icon, color = '#5B9DB8', trend, trendValue }: StatTileProps) {
  const trendColor = trend === 'up' ? '#16a34a' : trend === 'down' ? '#dc2626' : '#9ca3af'
  const trendArrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'
  return (
    <div className="glass-card-sm p-4 flex flex-col gap-2">
      {icon && (
        <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: `${color}15` }}>
          <span style={{ color }}>{icon}</span>
        </div>
      )}
      <div className="flex items-end gap-1">
        <span className="text-3xl font-bold text-gray-900 leading-none">{value}</span>
        {unit && <span className="text-sm text-gray-500 mb-1">{unit}</span>}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 font-medium">{label}</span>
        {trend && trendValue && (
          <span className="text-xs font-semibold" style={{ color: trendColor }}>
            {trendArrow} {trendValue}
          </span>
        )}
      </div>
    </div>
  )
}
