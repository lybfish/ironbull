#!/usr/bin/env python3
"""
本地测试：按 .env.local 里配置的多个交易所，逐个连接并平掉该账户下所有合约持仓。
不提交、不提交密钥。

用法：
    cd /path/to/ironbull
    PYTHONPATH=. python3 scripts/close_all_exchanges_local.py
    PYTHONPATH=. python3 scripts/close_all_exchanges_local.py --real   # 主网
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse_env_local_blocks():
    """解析 .env.local，按每个 IRONBULL_EXCHANGE_NAME 拆成多组配置。支持行首 # 注释掉的配置（便于一次测多所）。"""
    path = os.path.join(ROOT, ".env.local")
    if not os.path.isfile(path):
        return []
    blocks = []
    current = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        # 支持 "# IRONBULL_EXCHANGE_NAME=binance" 这种注释掉的多组配置
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k == "IRONBULL_EXCHANGE_NAME":
            if current and current.get("name"):
                blocks.append(dict(current))
            current = {"name": v.lower(), "api_key": "", "api_secret": "", "passphrase": ""}
        elif k == "IRONBULL_EXCHANGE_API_KEY":
            current["api_key"] = v
        elif k == "IRONBULL_EXCHANGE_API_SECRET":
            current["api_secret"] = v
        elif k == "IRONBULL_EXCHANGE_PASSPHRASE":
            current["passphrase"] = v
    if current and current.get("name"):
        blocks.append(dict(current))
    return blocks


def _load_env_local_for_block(block):
    """把一组配置写回 os.environ，供 get_config() 使用。"""
    os.environ["IRONBULL_EXCHANGE_NAME"] = block["name"]
    os.environ["IRONBULL_EXCHANGE_API_KEY"] = block.get("api_key", "")
    os.environ["IRONBULL_EXCHANGE_API_SECRET"] = block.get("api_secret", "")
    os.environ["IRONBULL_EXCHANGE_PASSPHRASE"] = block.get("passphrase", "")


async def _close_all_for_exchange(block: dict, sandbox: bool) -> None:
    """对一个交易所：拉取所有持仓并市价全平。"""
    from libs.trading.live_trader import LiveTrader
    from libs.trading.base import OrderSide, OrderType

    name = block["name"]
    api_key = block.get("api_key") or ""
    api_secret = block.get("api_secret") or ""
    passphrase = block.get("passphrase") or ""

    if not api_key or not api_secret:
        print("[%s] 跳过：无 api_key/api_secret" % name)
        return

    print("\n========== %s ==========" % name.upper())
    trader = LiveTrader(
        exchange=name,
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase or None,
        sandbox=sandbox,
        market_type="future",
        settlement_service=None,
    )
    try:
        await trader.exchange.load_markets()
        positions = await trader.exchange.fetch_positions()
    except Exception as e:
        print("[%s] 连接/拉持仓失败: %s" % (name, e))
        try:
            await trader.close()
        except Exception:
            pass
        return

    def _pos_contracts(p):
        c = p.get("contracts")
        if c is not None and float(c) != 0:
            return float(c)
        s = p.get("size")
        if s is not None and float(s) != 0:
            return abs(float(s))
        return 0

    open_pos = [p for p in (positions or []) if _pos_contracts(p) != 0]
    if not open_pos:
        print("[%s] 当前无持仓" % name)
        try:
            await trader.close()
        except Exception:
            pass
        return

    print("[%s] 共 %s 个持仓，逐个平仓" % (name, len(open_pos)))
    for p in open_pos:
        sym = p.get("symbol") or ""
        qty = _pos_contracts(p)
        side_pos = (p.get("side") or "long").lower()
        pos_side = "LONG" if side_pos == "long" else "SHORT"
        close_side = OrderSide.SELL if side_pos == "long" else OrderSide.BUY
        # CCXT symbol 可能是 ETH/USDT:USDT，LiveTrader 接受
        try:
            res = await trader.create_order(
                symbol=sym,
                side=close_side,
                order_type=OrderType.MARKET,
                quantity=qty,
                position_side=pos_side,
                trade_type="CLOSE",
            )
            st = getattr(res, "status", None)
            st_str = st.value if hasattr(st, "value") else str(st)
            print("  平仓 %s %s qty=%s -> status=%s" % (sym, pos_side, qty, st_str))
            if getattr(res, "error_message", None):
                print("    错误: %s" % res.error_message)
        except Exception as e:
            print("  平仓 %s %s qty=%s 异常: %s" % (sym, pos_side, qty, e))

    try:
        await trader.close()
    except Exception:
        pass
    print("[%s] 完成" % name.upper())


async def main():
    import argparse
    p = argparse.ArgumentParser(description="按 .env.local 多交易所全平仓")
    p.add_argument("--real", action="store_true", help="主网（默认测试网）")
    args = p.parse_args()
    sandbox = not args.real
    print("模式: %s" % ("主网" if not sandbox else "测试网"))

    blocks = _parse_env_local_blocks()
    if not blocks:
        print(".env.local 未找到任何 IRONBULL_EXCHANGE_NAME 配置")
        return

    print("解析到 %s 个交易所配置" % len(blocks))
    for b in blocks:
        print("  - %s" % b.get("name", "?"))

    for block in blocks:
        _load_env_local_for_block(block)
        await _close_all_for_exchange(block, sandbox)

    print("\n全部完成。")


if __name__ == "__main__":
    asyncio.run(main())
