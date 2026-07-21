#!/usr/bin/env python3
"""模拟盘通知系统本地端到端测试脚本。

使用方法:
    1. 先启动服务: python server.py
    2. 运行此脚本: python scripts/test_paper_trading_local.py <username> <password>
"""

import sys
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 10
TOKEN = ""


def _api(method: str, path: str, **kwargs):
    url = f"{BASE_URL}{path}"
    headers = kwargs.pop("headers", {})
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    kwargs.setdefault("timeout", TIMEOUT)
    try:
        resp = getattr(requests, method)(url, headers=headers, **kwargs)
    except requests.Timeout:
        print(f"  {method.upper()} {path} -> TIMEOUT")
        return 0, {"error": "请求超时"}
    except requests.ConnectionError:
        print(f"  {method.upper()} {path} -> CONNECTION ERROR")
        return 0, {"error": "连接失败"}
    print(f"  {method.upper()} {path} -> {resp.status_code}")
    try:
        data = resp.json()
        # 解包统一响应格式 {"code":0, "data": {...}}
        if isinstance(data, dict) and "data" in data and "code" in data:
            data = data["data"]
    except Exception:
        data = resp.text
    return resp.status_code, data


def step(name: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def main():
    global TOKEN

    if len(sys.argv) < 3:
        print(f"用法: python {sys.argv[0]} <username> <password>")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]

    # 0. 连接 & 登录
    step("0. 连接 & 登录")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": username, "password": password},
            timeout=TIMEOUT,
        )
        print(f"  POST /api/auth/login -> {resp.status_code}")
        if resp.status_code == 200:
            body = resp.json()
            # 兼容统一响应包装 {"data": {"token": ...}} 和裸响应 {"token": ...}
            TOKEN = (body.get("data") or body).get("token", "")
            print(f"  登录成功, token 长度: {len(TOKEN)}")
        else:
            print(f"  登录失败: {resp.text}")
            sys.exit(1)
    except requests.ConnectionError:
        print("  无法连接服务，请先运行 python server.py")
        sys.exit(1)
    except requests.Timeout:
        print("  连接超时")
        sys.exit(1)

    # 验证 token
    code, data = _api("get", "/api/paper-trading/account")
    if code == 401:
        print(f"  鉴权失败: {data}")
        sys.exit(1)
    cap = data.get("current_capital", "?") if isinstance(data, dict) else "?"
    print(f"  鉴权通过, 账户资金: {cap}")

    # 1. 重置模拟盘
    step("1. 重置模拟盘账户")
    code, data = _api("post", "/api/paper-trading/account/reset")
    print(f"  结果: {data}")

    # 2. 测试通知渠道连通性
    step("2. 测试通知渠道")
    code, data = _api("post", "/api/paper-trading/notify-test")
    print(f"  结果: {data}")
    if code != 200:
        print("  通知渠道不通，后续通知可能无法发送（请在 Web UI 中配置）")

    # 3. 触发盘前计划
    step("3. 触发盘前计划通知")
    code, data = _api("post", "/api/paper-trading/premarket-plan")
    print(f"  结果: {data}")
    print("  -> 检查通知渠道是否收到盘前计划（验证去重效果）")

    # 4. 触发扫描（自动建仓）
    step("4. 触发扫描")
    code, data = _api("post", "/api/paper-trading/scan", timeout=120)
    print(f"  结果: {data}")
    if isinstance(data, dict):
        opened = data.get("opened", 0)
        closed = data.get("closed", 0)
        print(f"  建仓: {opened}, 平仓: {closed}")
        if opened > 0:
            print("  -> 检查通知渠道是否收到建仓通知")

    # 5. 查看当前持仓
    step("5. 查看当前持仓")
    code, data = _api("get", "/api/paper-trading/positions")
    positions = data if isinstance(data, list) else data.get("positions", [])
    print(f"  持仓数量: {len(positions)}")
    for p in positions[:5]:
        if isinstance(p, dict):
            print(f"    {p.get('stock_name', '')} ({p.get('stock_symbol', '')}) "
                  f"入场价: {p.get('entry_price', 0):.2f}")

    # 6. 手动平仓第一个持仓
    if positions:
        step("6. 手动平仓")
        first = positions[0]
        pos_id = first.get("id") if isinstance(first, dict) else None
        if pos_id:
            code, data = _api("post", f"/api/paper-trading/positions/{pos_id}/close")
            print(f"  结果: {data}")
            print("  -> 检查通知渠道是否收到平仓通知")
    else:
        step("6. 手动平仓（跳过，无持仓）")

    # 7. 查看交易历史
    step("7. 查看交易历史")
    code, data = _api("get", "/api/paper-trading/trades")
    trades = data.get("items", []) if isinstance(data, dict) else data
    print(f"  交易记录数: {len(trades)}")
    for t in trades[:5]:
        if isinstance(t, dict):
            pnl = t.get("pnl", 0)
            sign = "+" if pnl >= 0 else ""
            print(f"    {t.get('stock_name', '')} 盈亏: {sign}{pnl:.2f} ({t.get('exit_reason', '')})")

    # 8. 触发日终摘要
    step("8. 触发日终摘要通知")
    code, data = _api("post", "/api/paper-trading/daily-summary")
    print(f"  结果: {data}")
    print("  -> 检查通知渠道是否收到日终摘要")

    step("测试完成")
    print("  请查看通知渠道确认所有通知是否正确送达。\n")


if __name__ == "__main__":
    main()
