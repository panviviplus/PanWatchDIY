import React from 'react'
import { BellRing, TrendingUp, TrendingDown, ShieldAlert, Target, Eye } from 'lucide-react'

export interface ChatActionData {
  action: string
  label: string
  symbol?: string
  market?: string
  price?: number | null
  reason?: string
  params?: Record<string, any>
}

interface ChatActionCardProps {
  action: ChatActionData
  onAction?: (action: ChatActionData) => void
}

const actionIcons: Record<string, React.ComponentType<any>> = {
  create_alert: BellRing,
  add_position: TrendingUp,
  reduce_position: TrendingDown,
  set_stop_loss: ShieldAlert,
  set_target_price: Target,
  watch: Eye,
}

const actionColors: Record<string, string> = {
  create_alert: 'border-amber-500 bg-amber-50 dark:bg-amber-950',
  add_position: 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950',
  reduce_position: 'border-rose-500 bg-rose-50 dark:bg-rose-950',
  set_stop_loss: 'border-orange-500 bg-orange-50 dark:bg-orange-950',
  set_target_price: 'border-sky-500 bg-sky-50 dark:bg-sky-950',
  watch: 'border-violet-500 bg-violet-50 dark:bg-violet-950',
}

export default function ChatActionCard({ action, onAction }: ChatActionCardProps) {
  const Icon = actionIcons[action.action] || Target

  return (
    <div
      className={`my-2 rounded-lg border px-3 py-2 cursor-pointer hover:shadow-sm transition-shadow ${actionColors[action.action] || 'border-gray-300 bg-gray-50'}`}
      onClick={() => onAction?.(action)}
    >
      <div className="flex items-center gap-2 text-sm">
        <Icon className="w-4 h-4 shrink-0" />
        <span className="font-medium">{action.label}</span>
      </div>
      {action.reason && (
        <p className="text-xs text-muted-foreground mt-1">{action.reason}</p>
      )}
      {action.symbol && (
        <p className="text-xs text-muted-foreground mt-0.5">
          {action.symbol}
          {action.price != null && (
            <span> · ¥{typeof action.price === 'number' ? action.price.toFixed(2) : action.price}</span>
          )}
        </p>
      )}
    </div>
  )
}
