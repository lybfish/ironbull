#!/usr/bin/env python3
"""
逐仓开仓 + 平仓 测试：先小额开多，再市价平掉。
确保 ensure_isolated_margin_mode 生效，开平都在逐仓下执行。

用法（主网，默认 Binance）:
  PYTHONPATH=. python3 scripts/test_isolated_open_close.py --real --yes
  PYTHONPATH=. python3 scripts/test_isolated_open_close.py --real --yes --exchange okx
  PYTHONPATH=. python3 scripts/test_isolated_open_close.py --real --yes --exchange gate
  开仓后等一会再平（便于看持仓）: ... --exchange okx --delay 30
  双向单（先开多再开空，再平多平空）: ... --exchange okx --dual --amount 100 --delay 30
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse_env_local_blocks():
    path = os.path.join(ROOT, ".env.local")
    if not os.path.isfile(path):
        return []
    blocks = []
    current = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
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


def _contracts(p):
    x = float(p.get("contracts") or 0)
    return x if x != 0 else abs(float(p.get("size") or 0))


async def _run_dual(exchange: str, api_key: str, api_secret: str, passphrase: str, sandbox: bool, symbol: str, amount_usdt: float, delay_before_close: float):
    """双向单：开多 + 开空，等待后平多、平空。"""
    from libs.trading.live_trader import LiveTrader
    from libs.trading.base import OrderSide, OrderType, OrderStatus

    trader = LiveTrader(
        exchange=exchange,
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase or None,
        sandbox=sandbox,
        market_type="future",
        settlement_service=None,
    )
    try:
        await trader.exchange.load_markets()
        ccxt_sym = trader._ccxt_symbol(symbol)
        await trader.ensure_dual_position_mode()
        print("[1] 设置逐仓...")
        await trader.ensure_isolated_margin_mode(ccxt_sym)
        ticker = await trader.exchange.fetch_ticker(ccxt_sym)
        price = float(ticker.get("last") or ticker.get("close") or 0)
        if price <= 0:
            print("[!] 无法获取价格")
            return
        # 开多
        print("[2] 市价开多 %s 约 %.2f USDT (position_side=LONG)..." % (symbol, amount_usdt))
        res_long = await trader.create_order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            amount_usdt=amount_usdt,
            price=price,
            position_side="LONG",
            trade_type="OPEN",
        )
        if res_long.status not in (OrderStatus.FILLED, OrderStatus.PARTIAL):
            print("    开多未成交: %s" % getattr(res_long, "error_message", res_long.status))
            return
        qty_long = getattr(res_long, "filled_quantity", 0) or 0
        print("    开多成交: qty=%s" % qty_long)
        # 开空
        print("[3] 市价开空 %s 约 %.2f USDT (position_side=SHORT)..." % (symbol, amount_usdt))
        res_short = await trader.create_order(
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            amount_usdt=amount_usdt,
            price=price,
            position_side="SHORT",
            trade_type="OPEN",
        )
        if res_short.status not in (OrderStatus.FILLED, OrderStatus.PARTIAL):
            print("    开空未成交: %s" % getattr(res_short, "error_message", res_short.status))
            return
        qty_short = getattr(res_short, "filled_quantity", 0) or 0
        print("    开空成交: qty=%s" % qty_short)
        if delay_before_close > 0:
            print("    等待 %.0f 秒后再平仓（可查看多空双向持仓）..." % delay_before_close)
            await asyncio.sleep(delay_before_close)
        # 平多
        if qty_long > 0:
            print("[4] 市价平多 LONG qty=%s..." % qty_long)
            r = await trader.create_order(symbol=symbol, side=OrderSide.SELL, order_type=OrderType.MARKET, quantity=qty_long, position_side="LONG", trade_type="CLOSE")
            print("    平多: %s" % ("成交" if r.status in (OrderStatus.FILLED, OrderStatus.PARTIAL) else getattr(r, "error_message", r.status)))
        # 平空
        if qty_short > 0:
            print("[5] 市价平空 SHORT qty=%s..." % qty_short)
            r = await trader.create_order(symbol=symbol, side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=qty_short, position_side="SHORT", trade_type="CLOSE")
            print("    平空: %s" % ("成交" if r.status in (OrderStatus.FILLED, OrderStatus.PARTIAL) else getattr(r, "error_message", r.status)))
        print("双向单测试完成。")
    finally:
        await trader.close()


async def _run_one(exchange: str, api_key: str, api_secret: str, passphrase: str, sandbox: bool, symbol: str, amount_usdt: float, delay_before_close: float = 0, dual: bool = False):
    from libs.trading.live_trader import LiveTrader
    from libs.trading.base import OrderSide, OrderType, OrderStatus

    if dual:
        await _run_dual(exchange, api_key, api_secret, passphrase, sandbox, symbol, amount_usdt, delay_before_close or 15)
        return

    trader = LiveTrader(
        exchange=exchange,
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase or None,
        sandbox=sandbox,
        market_type="future",
        settlement_service=None,
    )
    try:
        await trader.exchange.load_markets()
        ccxt_sym = trader._ccxt_symbol(symbol)
        # 1) 逐仓
        print("[1] 设置逐仓...")
        await trader.ensure_isolated_margin_mode(ccxt_sym)
        # 2) 市价开多
        ticker = await trader.exchange.fetch_ticker(ccxt_sym)
        price = float(ticker.get("last") or ticker.get("close") or 0)
        if price <= 0:
            print("[!] 无法获取价格")
            return
        print("[2] 市价开多 %s 约 %.2f USDT (价≈%.4f)..." % (symbol, amount_usdt, price))
        res_open = await trader.create_order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            amount_usdt=amount_usdt,
            price=price,
            trade_type="OPEN",
        )
        ok = res_open.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        if not ok:
            print("    开仓未成交: %s" % getattr(res_open, "error_message", res_open.status))
            return
        filled_qty = getattr(res_open, "filled_quantity", 0) or 0
        if filled_qty <= 0:
            print("    成交量为 0，跳过平仓")
            return
        print("    开仓成交: qty=%s" % filled_qty)
        if delay_before_close > 0:
            print("    等待 %.0f 秒后再平仓（可在交易所界面查看持仓）..." % delay_before_close)
            await asyncio.sleep(delay_before_close)
        # 3) 查持仓确认方向
        positions = await trader.exchange.fetch_positions()
        open_pos = [p for p in (positions or []) if _contracts(p) != 0 and (p.get("symbol") or "").replace("_", "/") == ccxt_sym.replace("_", "/")]
        side_pos = "long"
        if open_pos:
            side_pos = (open_pos[0].get("side") or "long").lower()
            filled_qty = _contracts(open_pos[0])
        pos_side = "LONG" if side_pos == "long" else "SHORT"
        close_side = OrderSide.SELL if side_pos == "long" else OrderSide.BUY
        # 4) 市价平仓
        print("[3] 市价平仓 %s %s qty=%s..." % (symbol, pos_side, filled_qty))
        res_close = await trader.create_order(
            symbol=symbol,
            side=close_side,
            order_type=OrderType.MARKET,
            quantity=filled_qty,
            position_side=pos_side,
            trade_type="CLOSE",
        )
        ok_close = res_close.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        print("    平仓结果: %s" % ("成交" if ok_close else getattr(res_close, "error_message", res_close.status)))
        print("逐仓开仓+平仓测试完成。")
    finally:
        await trader.close()


def main():
    import argparse
    p = argparse.ArgumentParser(description="逐仓开仓后立即平仓测试")
    p.add_argument("--real", action="store_true", help="主网")
    p.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    p.add_argument("--exchange", type=str, default="binance", help="binance/okx/gate")
    p.add_argument("--symbol", type=str, default="BTC/USDT")
    p.add_argument("--amount", type=float, default=5.0)
    p.add_argument("--delay", type=float, default=0, help="开仓后等待 N 秒再平仓，便于在交易所界面查看持仓")
    p.add_argument("--dual", action="store_true", help="双向单：先开多再开空，等待后平多、平空")
    args = p.parse_args()

    sandbox = not args.real
    blocks = _parse_env_local_blocks()
    by_name = {b["name"]: b for b in blocks}
    ex = args.exchange.strip().lower()
    if ex not in by_name:
        print("未在 .env.local 中找到交易所 %s 的配置" % ex)
        sys.exit(1)
    block = by_name[ex]
    if not block.get("api_key") or not block.get("api_secret"):
        print("该交易所缺少 api_key/api_secret")
        sys.exit(1)
    if args.real and not args.yes:
        try:
            input("主网 %.2f USDT 开平仓测试，按 Enter 继续..." % args.amount)
        except KeyboardInterrupt:
            sys.exit(0)

    asyncio.run(_run_one(
        exchange=ex,
        api_key=block["api_key"],
        api_secret=block["api_secret"],
        passphrase=block.get("passphrase", ""),
        sandbox=sandbox,
        symbol=args.symbol,
        amount_usdt=args.amount,
        delay_before_close=args.delay,
        dual=args.dual,
    ))


if __name__ == "__main__":
    main()
