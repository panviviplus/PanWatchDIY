from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from pydantic import BaseModel, Field

from src.collectors.kline_collector import KlineCollector
from src.models.market import MarketCode

router = APIRouter()

# 支持的分钟间隔
_MINUTE_INTERVALS = frozenset({"1m", "5m", "15m", "30m", "60m"})
# 日级别间隔
_DAILY_INTERVALS = frozenset({"1d", "1w", "1m", "d", "w", "m", "week", "month"})


class KlineItem(BaseModel):
    symbol: str = Field(..., description="股票代码")
    market: str = Field(..., description="市场: CN/HK/US")
    days: int | None = Field(default=60, description="K线天数(分钟线时忽略)")
    interval: str | None = Field(default="1d", description="周期: 1d/1w/1m/5m/15m/30m/60m")
    count: int | None = Field(default=None, description="分钟K线根数(默认 240)")


class KlineBatchRequest(BaseModel):
    items: list[KlineItem]


class KlineSummaryItem(BaseModel):
    symbol: str = Field(..., description="股票代码")
    market: str = Field(..., description="市场: CN/HK/US")


class KlineSummaryBatchRequest(BaseModel):
    items: list[KlineSummaryItem]


def _parse_market(market: str) -> MarketCode:
    try:
        return MarketCode(market)
    except ValueError:
        raise HTTPException(400, f"不支持的市场: {market}")


def _serialize_klines(klines) -> list[dict]:
    return [
        {
            "date": k.date,
            "open": k.open,
            "close": k.close,
            "high": k.high,
            "low": k.low,
            "volume": k.volume,
        }
        for k in klines
    ]


def _is_minute_interval(interval: str) -> bool:
    """判断是否是分钟级别的间隔。"""
    iv = (interval or "").strip().lower()
    return iv in _MINUTE_INTERVALS or iv in ("1min", "5min", "15min", "30min", "60min", "1h")


def _aggregate_klines(klines, interval: str) -> list:
    """Aggregate daily klines to week/month."""

    iv = (interval or "1d").lower()
    if iv in ("1d", "day", "d"):
        return klines
    if iv not in ("1w", "1m", "week", "month", "w", "m"):
        return klines

    parsed = []
    for k in klines or []:
        try:
            dt = datetime.strptime(k.date, "%Y-%m-%d")
        except Exception:
            continue
        parsed.append((dt, k))

    parsed.sort(key=lambda x: x[0])
    buckets: dict[str, list] = {}
    for dt, k in parsed:
        if iv in ("1w", "week", "w"):
            y, w, _ = dt.isocalendar()
            key = f"{y:04d}-W{w:02d}"
        else:
            key = f"{dt.year:04d}-{dt.month:02d}"
        buckets.setdefault(key, []).append((dt, k))

    out = []
    for _, items in buckets.items():
        items.sort(key=lambda x: x[0])
        first = items[0][1]
        last = items[-1][1]
        high = max(it[1].high for it in items)
        low = min(it[1].low for it in items)
        vol = sum(it[1].volume for it in items)
        out.append(
            type(first)(
                date=items[-1][0].strftime("%Y-%m-%d"),
                open=first.open,
                close=last.close,
                high=high,
                low=low,
                volume=vol,
            )
        )
    out.sort(key=lambda k: k.date)
    return out


@router.get("/{symbol}")
def get_klines(
    symbol: str,
    market: str = "CN",
    days: int = 60,
    interval: str = "1d",
    count: int = Query(default=240, description="分钟K线根数"),
):
    """获取单只股票K线数据（支持日K/周K/月K及分钟K线 1m/5m/15m/30m/60m）。"""
    market_code = _parse_market(market)
    collector = KlineCollector(market_code)

    # 分钟K线
    if _is_minute_interval(interval):
        klines = collector.get_minute_klines(symbol, interval=interval, count=count)
        return {
            "symbol": symbol,
            "market": market_code.value,
            "count": count,
            "interval": interval,
            "klines": klines,
        }

    # 日级别K线
    klines = collector.get_klines(symbol, days=days)
    klines = _aggregate_klines(klines, interval)
    return {
        "symbol": symbol,
        "market": market_code.value,
        "days": days,
        "interval": interval,
        "klines": _serialize_klines(klines),
    }


@router.get("/{symbol}/intraday")
def get_intraday(symbol: str, market: str = "CN"):
    """获取当日分时数据（分钟级价格 + 均价 + 成交量）。"""
    market_code = _parse_market(market)
    collector = KlineCollector(market_code)
    points = collector.get_intraday(symbol)
    return {
        "symbol": symbol,
        "market": market_code.value,
        "points": points,
    }


@router.post("/batch")
def get_klines_batch(payload: KlineBatchRequest):
    """批量获取K线数据"""
    if not payload.items:
        return []

    results = []
    for item in payload.items:
        market_code = _parse_market(item.market)
        collector = KlineCollector(market_code)
        interval = item.interval or "1d"

        if _is_minute_interval(interval):
            count = item.count or 240
            klines = collector.get_minute_klines(item.symbol, interval=interval, count=count)
            results.append({
                "symbol": item.symbol,
                "market": market_code.value,
                "count": count,
                "interval": interval,
                "klines": klines,
            })
        else:
            days = item.days or 60
            klines = collector.get_klines(item.symbol, days=days)
            klines = _aggregate_klines(klines, interval)
            results.append({
                "symbol": item.symbol,
                "market": market_code.value,
                "days": days,
                "interval": interval,
                "klines": _serialize_klines(klines),
            })

    return results


@router.get("/{symbol}/summary")
def get_kline_summary(symbol: str, market: str = "CN"):
    """获取单只股票K线摘要"""
    market_code = _parse_market(market)
    collector = KlineCollector(market_code)
    summary = collector.get_kline_summary(symbol)
    return {
        "symbol": symbol,
        "market": market_code.value,
        "summary": summary,
    }


@router.post("/summary/batch")
def get_kline_summary_batch(payload: KlineSummaryBatchRequest):
    """批量获取K线摘要"""
    if not payload.items:
        return []

    results = []
    for item in payload.items:
        market_code = _parse_market(item.market)
        collector = KlineCollector(market_code)
        summary = collector.get_kline_summary(item.symbol)
        results.append(
            {
                "symbol": item.symbol,
                "market": market_code.value,
                "summary": summary,
            }
        )

    return results
