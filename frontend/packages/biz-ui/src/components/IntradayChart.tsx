import { useEffect, useMemo, useRef, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { fetchAPI } from '@panwatch/api'
import { Button } from '@panwatch/base-ui/components/ui/button'

interface IntradayPoint {
  time: string   // "09:30"
  price: number
  volume: number
  avg_price: number
}

interface IntradayResponse {
  symbol: string
  market: string
  points: IntradayPoint[]
}

function getLW() {
  return (window as any)?.LightweightCharts || null
}

/** 判断当前是否在 A 股交易时段内（周一至周五 9:30-15:00 北京时间） */
function isCNTradingTime(): boolean {
  const now = new Date()
  const day = now.getDay()
  if (day === 0 || day === 6) return false
  // 将当前 UTC 时间转为北京时间近似判断
  const cnHour = now.getUTCHours() + 8
  const cnMin = now.getUTCMinutes()
  const totalMin = cnHour * 60 + cnMin
  return totalMin >= 9 * 60 + 30 && totalMin <= 15 * 60
}

export default function IntradayChart(props: { symbol: string; market: string }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [points, setPoints] = useState<IntradayPoint[]>([])
  const containerRef = useRef<HTMLDivElement | null>(null)

  const load = async () => {
    if (!props.symbol) return
    setLoading(true)
    setError('')
    try {
      const res = await fetchAPI<IntradayResponse>(
        `/klines/${encodeURIComponent(props.symbol)}/intraday?market=${encodeURIComponent(props.market)}`
      )
      setPoints(res.points || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载分时数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [props.symbol, props.market])

  // 交易时段自动刷新
  useEffect(() => {
    if (!isCNTradingTime()) return
    const t = setInterval(() => void load(), 30_000)
    return () => clearInterval(t)
  }, [props.symbol, props.market])

  const { priceData, avgData, volumeData, metrics } = useMemo(() => {
    if (!points.length) return { priceData: [], avgData: [], volumeData: [], metrics: null }

    // 将时间字符串转换为从当天 0:00 开始的秒数（lightweight-charts 分钟级时间戳）
    const toTimestamp = (time: string): number => {
      const [h, m] = time.split(':').map(Number)
      return (h || 0) * 3600 + (m || 0) * 60
    }

    const pData = points.map((p) => ({
      time: toTimestamp(p.time) as any,
      value: p.price,
    }))

    const aData = points
      .filter((p) => p.avg_price > 0)
      .map((p) => ({
        time: toTimestamp(p.time) as any,
        value: p.avg_price,
      }))

    const vData = points.map((p) => ({
      time: toTimestamp(p.time) as any,
      value: p.volume,
      color: p.price >= (p.avg_price || p.price) ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.25)',
    }))

    const last = points[points.length - 1]
    const first = points[0]
    const change = first.price ? ((last.price - first.price) / first.price) * 100 : 0

    return {
      priceData: pData,
      avgData: aData,
      volumeData: vData,
      metrics: {
        current: last.price,
        change,
        high: Math.max(...points.map((p) => p.price)),
        low: Math.min(...points.map((p) => p.price)),
        avgPrice: last.avg_price || last.price,
      },
    }
  }, [points])

  useEffect(() => {
    const LW = getLW()
    if (!LW || !containerRef.current || !priceData.length) return

    const container = containerRef.current
    container.innerHTML = ''

    const rootStyle = getComputedStyle(document.documentElement)
    const bg = rootStyle.getPropertyValue('--card').trim()
    const fg = rootStyle.getPropertyValue('--foreground').trim()

    const chart = LW.createChart(container, {
      width: container.clientWidth,
      height: 380,
      layout: {
        background: { color: `hsl(${bg})` },
        textColor: `hsl(${fg} / 0.85)`,
      },
      rightPriceScale: { borderVisible: false, autoScale: true },
      timeScale: {
        borderVisible: false,
        fixRightEdge: true,
        rightOffset: 2,
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: any) => {
          const t = typeof time === 'number' ? time : (time?.timestamp || 0)
          const h = Math.floor(t / 3600)
          const m = Math.floor((t % 3600) / 60)
          return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`
        },
      },
      handleScale: { mouseWheel: true, pinch: true },
      handleScroll: { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true },
      grid: {
        vertLines: { color: 'rgba(148, 163, 184, 0.08)' },
        horzLines: { color: 'rgba(148, 163, 184, 0.08)' },
      },
      crosshair: { mode: 1 },
    })

    // 价格线
    const priceSeries = chart.addLineSeries({
      color: 'rgba(59, 130, 246, 0.9)',
      lineWidth: 1.5,
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
    })
    priceSeries.setData(priceData as any)

    // 均价线
    if (avgData.length) {
      const avgSeries = chart.addLineSeries({
        color: 'rgba(245, 158, 11, 0.7)',
        lineWidth: 1,
        lineStyle: 2,
        priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
      })
      avgSeries.setData(avgData as any)
    }

    // 成交量柱
    const volSeries = chart.addHistogramSeries({
      priceScaleId: 'vol',
      priceFormat: { type: 'volume' },
    })
    volSeries.setData(volumeData as any)
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } })

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: container.clientWidth })
    })
    ro.observe(container)

    return () => {
      ro.disconnect()
      try { chart.remove() } catch { /* ignore */ }
    }
  }, [priceData, avgData, volumeData])

  return (
    <div className="card p-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-3">
        <div className="text-[13px] font-semibold text-foreground">分时图</div>
        <div className="flex items-center gap-2">
          {metrics && (
            <div className="flex items-center gap-3 text-[11px]">
              <span className="text-muted-foreground">
                最新 <span className="font-mono text-foreground">{metrics.current.toFixed(2)}</span>
              </span>
              <span className={metrics.change >= 0 ? 'text-rose-500' : 'text-emerald-500'}>
                <span className="font-mono">{metrics.change >= 0 ? '+' : ''}{metrics.change.toFixed(2)}%</span>
              </span>
              <span className="text-muted-foreground">
                均价 <span className="font-mono text-foreground">{metrics.avgPrice.toFixed(2)}</span>
              </span>
            </div>
          )}
          <Button variant="secondary" size="sm" className="h-8" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="text-[12px] text-rose-600 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2 mb-3">
          {error}
        </div>
      ) : null}

      {loading && !points.length ? (
        <div className="w-full h-[380px] rounded-xl overflow-hidden border border-border/50 animate-pulse">
          <div className="h-full w-full bg-accent/20" />
        </div>
      ) : points.length === 0 ? (
        <div className="w-full h-[380px] flex items-center justify-center text-[12px] text-muted-foreground border border-border/50 rounded-xl">
          {error ? '加载失败' : '暂无分时数据（非交易时段或数据源暂不可用）'}
        </div>
      ) : (
        <div ref={containerRef} className="w-full h-[380px] rounded-xl overflow-hidden border border-border/50" />
      )}
    </div>
  )
}
