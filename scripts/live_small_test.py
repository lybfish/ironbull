#!/usr/bin/env python3
"""
小额实盘测试脚本

用 LiveTrader 做一次小额下单 + 可选止盈止损，验证：交易所连接、symbol 规范、精度、双向/全仓逻辑。
默认走测试网（sandbox），加 --real 才走主网小额。

用法：
    # 仅查余额、持仓和未成交委托（不下单）
    python scripts/live_small_test.py --dry-run

    # 仅平仓（市价平掉当前持仓）
    python scripts/live_small_test.py --close

    # 撤销该交易对下所有未成交委托（含止盈止损）
    python scripts/live_small_test.py --cancel-orders

    # 测试网小额下单（默认 5 USDT，BTC/USDT）
    python scripts/live_small_test.py

    # 主网小额（需显式 --real，建议 amount 5~10）
    python scripts/live_small_test.py --real --amount 5

    # 指定交易所、交易对
    python scripts/live_small_test.py --exchange okx --symbol ETH/USDT --amount 5

环境/配置：
    IRONBULL_EXCHANGE_API_KEY / exchange_api_key
    IRONBULL_EXCHANGE_API_SECRET / exchange_api_secret
    IRONBULL_EXCHANGE_PASSPHRASE / exchange_passphrase  # OKX 必填
    IRONBULL_EXCHANGE_NAME / exchange_name              # binance / okx / gate
    IRONBULL_EXCHANGE_SANDBOX / exchange_sandbox        # 默认 true，--real 时脚本会覆盖为 false
"""

import sys
import os
import asyncio
import argparse
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_env_local():
    """加载项目根目录 .env.local 到 os.environ（若存在），便于本地测试。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, ".env.local")
    if not os.path.isfile(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and not k.startswith("#"):
                os.environ[k] = v


_load_env_local()

from libs.core import get_config, get_logger, setup_logging
from libs.trading.live_trader import LiveTrader
from libs.trading.base import OrderSide, OrderType, OrderStatus

setup_logging(service_name="live-small-test")
log = get_logger("live-small-test")


def _parse_args():
    p = argparse.ArgumentParser(description="小额实盘测试：余额→下单→止盈止损→持仓")
    p.add_argument("--dry-run", action="store_true", help="仅查余额和持仓，不下单")
    p.add_argument("--close", action="store_true", help="仅平仓：查当前持仓后市价卖出/买入平仓")
    p.add_argument("--cancel-orders", action="store_true", help="撤销该交易对下所有未成交委托（含止盈止损单）")
    p.add_argument("--sl-tp-only", action="store_true", help="仅测试止盈止损：对当前持仓挂 SL/TP（需先有持仓）")
    p.add_argument("--real", action="store_true", help="主网实盘（默认测试网）")
    p.add_argument("--yes", "-y", action="store_true", help="实盘时跳过确认提示")
    p.add_argument("--amount", type=float, default=5.0, help="下单金额 USDT（默认 5）")
    p.add_argument("--symbol", type=str, default="BTC/USDT", help="交易对（默认 BTC/USDT）")
    p.add_argument("--exchange", type=str, default=None, help="交易所 binance/okx/gate，默认读配置")
    p.add_argument("--no-sl-tp", action="store_true", help="开仓后不下止盈止损单")
    return p.parse_args()


async def _run(
    exchange: str,
    api_key: str,
    api_secret: str,
    passphrase: Optional[str],
    sandbox: bool,
    symbol: str,
    amount_usdt: float,
    dry_run: bool,
    no_sl_tp: bool,
    close_only: bool,
    cancel_orders: bool,
    sl_tp_only: bool,
) -> None:
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
        # 1. 余额
        balances = await trader.get_balance("USDT")
        usdt = balances.get("USDT")
        balance_before = float(usdt.total or 0) if usdt else 0
        available_before = float(usdt.free or 0) if usdt else 0
        print("\n[1] 余额 (USDT): 总额=%.4f  可用=%.4f" % (balance_before, available_before))

        # 2. 当前价（用于下单数量）
        ticker = await trader.exchange.fetch_ticker(trader._ccxt_symbol(symbol))
        price = float(ticker.get("last") or ticker.get("close") or 0)
        if price <= 0:
            print("[!] 无法获取价格，退出")
            return
        print("[2] 当前价 %s = %.4f" % (symbol, price))

        if dry_run:
            positions = await trader.exchange.fetch_positions()
            def _c(p):
                x = float(p.get("contracts") or 0)
                return x if x != 0 else abs(float(p.get("size") or 0))
            open_pos = [p for p in (positions or []) if _c(p) != 0]
            print("[dry-run] 当前持仓数: %s" % len(open_pos))
            if open_pos:
                for p in open_pos[:5]:
                    print("  - %s %s contracts=%s" % (p.get("symbol"), p.get("side"), _c(p)))
            try:
                orders = await trader.exchange.fetch_open_orders(trader._ccxt_symbol(symbol))
                print("[dry-run] 当前未成交委托数: %s" % len(orders or []))
                if orders:
                    for o in (orders or [])[:10]:
                        print("  - id=%s type=%s side=%s amount=%s stopPrice=%s" % (o.get("id"), o.get("type"), o.get("side"), o.get("amount"), o.get("stopPrice")))
            except Exception as e:
                print("[dry-run] 未成交委托: 查询失败 (%s)" % e)
            return

        ccxt_sym = trader._ccxt_symbol(symbol)
        # 先尝试切全仓（无持仓时易成功；有持仓时可能失败，忽略即可）
        await trader.ensure_cross_margin_mode(ccxt_sym)
        positions = await trader.exchange.fetch_positions()
        # 持仓数量：CCXT 多为 contracts，Gate 原始为 size，统一用 _pos_contracts
        def _pos_contracts(p):
            c = p.get("contracts")
            if c is not None and float(c) != 0:
                return float(c)
            s = p.get("size")
            if s is not None and float(s) != 0:
                return abs(float(s))
            return 0
        def _pos_matches_symbol(p, sym, ccxt_s):
            ps = (p.get("symbol") or "").replace("_", "/")
            return ps == ccxt_s or sym.replace("/", "") in ps.replace(":", "")
        open_pos = [p for p in (positions or []) if _pos_contracts(p) != 0 and _pos_matches_symbol(p, symbol, ccxt_sym)]

        # --close：仅平仓（双向持仓必须传 position_side，否则 SELL 会变成开空）
        if close_only:
            if not open_pos:
                print("[close] 当前无 %s 持仓，无需平仓" % symbol)
                return
            for p in open_pos[:1]:
                qty = _pos_contracts(p)
                side_pos = (p.get("side") or "long").lower()
                close_side = OrderSide.SELL if side_pos == "long" else OrderSide.BUY
                # 平多：SELL + positionSide=LONG；平空：BUY + positionSide=SHORT
                pos_side = "LONG" if side_pos == "long" else "SHORT"
                print("[close] 市价平仓 %s 数量=%.6f (原 %s, positionSide=%s)" % (symbol, qty, side_pos, pos_side))
                res = await trader.create_order(
                    symbol=symbol,
                    side=close_side,
                    order_type=OrderType.MARKET,
                    quantity=qty,
                    position_side=pos_side,
                    reduceOnly=True,
                )
                print("    结果: status=%s filled_qty=%s exchange_order_id=%s" % (res.status.value, res.filled_quantity, res.exchange_order_id))
                if res.error_message:
                    print("    错误: %s" % res.error_message)
            return

        # --cancel-orders：撤销该交易对下所有未成交委托（含止盈止损）
        if cancel_orders:
            orders = await trader.exchange.fetch_open_orders(ccxt_sym)
            if not orders:
                print("[cancel-orders] %s 无未成交委托" % symbol)
                return
            print("[cancel-orders] 共 %s 笔未成交委托，逐个撤销" % len(orders))
            for o in orders:
                oid = o.get("id")
                otype = o.get("type") or ""
                stop = o.get("stopPrice")
                if not oid:
                    continue
                try:
                    res = await trader.cancel_order(oid, symbol)
                    if res.status.value == "canceled" or res.error_message is None:
                        print("    已撤: id=%s type=%s stopPrice=%s" % (oid, otype, stop))
                    else:
                        print("    撤单失败 id=%s: %s" % (oid, res.error_message))
                except Exception as e:
                    print("    撤单异常 id=%s: %s" % (oid, e))
            return

        # --sl-tp-only：仅对当前持仓挂止盈止损
        if sl_tp_only:
            if not open_pos:
                print("[sl-tp-only] 当前无 %s 持仓，请先开仓" % symbol)
                return
            p = open_pos[0]
            qty = _pos_contracts(p)
            side_pos = (p.get("side") or "long").lower()
            entry = float(p.get("entryPrice") or p.get("averagePrice") or price)
            sl = round(entry * 0.997, 4)
            tp = round(entry * 1.003, 4)
            close_side = OrderSide.SELL if side_pos == "long" else OrderSide.BUY
            print("[sl-tp-only] 持仓 %s 数量=%.6f 入场≈%.4f，挂 sl=%.4f tp=%.4f" % (side_pos, qty, entry, sl, tp))
            sl_res = await trader.set_stop_loss(symbol, close_side, qty, sl, "LONG" if side_pos == "long" else "SHORT")
            tp_res = await trader.set_take_profit(symbol, close_side, qty, tp, "LONG" if side_pos == "long" else "SHORT")
            if sl_res.error_message:
                print("    止损单失败: %s" % sl_res.error_message)
            elif sl_res.exchange_order_id:
                print("    止损单: %s" % sl_res.exchange_order_id)
            if tp_res.error_message:
                print("    止盈单失败: %s" % tp_res.error_message)
            elif tp_res.exchange_order_id:
                print("    止盈单: %s" % tp_res.exchange_order_id)
            return

        # 3. 下单（Gate / OKX 等合约按「张」计，最小 1 张，需按 contractSize 换算）
        ccxt_sym = trader._ccxt_symbol(symbol)
        await trader.exchange.load_markets()
        m = trader.exchange.market(ccxt_sym)
        contract_size = float(m.get("contractSize") or 0)
        eid = getattr(trader.exchange, "id", "")
        if contract_size > 0 and eid in ("gateio", "okx"):
            quantity = max(1, int(round(amount_usdt / (price * contract_size))))
            print("[3] 市价开多 %s 数量=%s 张 (contractSize=%s, 约 %.2f USDT)" % (symbol, quantity, contract_size, amount_usdt))
        else:
            quantity = round(amount_usdt / price, 6)
            print("[3] 市价开多 %s 数量=%.6f (约 %.2f USDT)" % (symbol, quantity, amount_usdt))
        result = await trader.create_order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=quantity,
            signal_id=None,
        )
        print("    订单结果: status=%s filled_qty=%s filled_price=%s exchange_order_id=%s" % (
            result.status.value, result.filled_quantity, result.filled_price, result.exchange_order_id,
        ))
        if result.error_message:
            print("    错误: %s" % result.error_message)
            return

        ok = result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        filled_qty = result.filled_quantity or 0
        filled_price = result.filled_price or price
        if not ok or filled_qty <= 0:
            print("[!] 未成交或成交为 0，跳过止盈止损")
            return

        # 4. 止盈止损（可选）
        if not no_sl_tp and filled_qty > 0 and filled_price > 0:
            # 测试用：窄幅 0.3% 止盈止损，便于快速触发或手动平
            sl = round(filled_price * 0.997, 4)
            tp = round(filled_price * 1.003, 4)
            print("[4] 设置止盈止损: sl=%.4f tp=%.4f" % (sl, tp))
            try:
                sl_tp = await trader.set_sl_tp(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    quantity=filled_qty,
                    stop_loss=sl,
                    take_profit=tp,
                )
                if sl_tp.get("sl"):
                    r = sl_tp["sl"]
                    if r.error_message:
                        print("    止损单失败: %s" % r.error_message)
                    elif r.exchange_order_id:
                        print("    止损单: %s" % r.exchange_order_id)
                if sl_tp.get("tp"):
                    r = sl_tp["tp"]
                    if r.error_message:
                        print("    止盈单失败: %s" % r.error_message)
                    elif r.exchange_order_id:
                        print("    止盈单: %s" % r.exchange_order_id)
            except Exception as e:
                print("    止盈止损失败: %s" % e)
        else:
            print("[4] 未设置止盈止损 (--no-sl-tp 或未成交)")

        # 5. 再次余额与持仓
        balances2 = await trader.get_balance("USDT")
        usdt2 = balances2.get("USDT")
        balance_after = float(usdt2.total or 0) if usdt2 else 0
        available_after = float(usdt2.free or 0) if usdt2 else 0
        print("[5] 下单后余额: 总额=%.4f  可用=%.4f" % (balance_after, available_after))
        positions = await trader.exchange.fetch_positions()
        open_pos = [p for p in (positions or []) if _pos_contracts(p) != 0]
        print("    当前持仓数: %s" % len(open_pos))
        if open_pos:
            for p in open_pos[:5]:
                print("  - %s %s contracts=%s entry=%s" % (
                    p.get("symbol"), p.get("side"), _pos_contracts(p),
                    p.get("entryPrice") or p.get("averagePrice"),
                ))
        print("\n完成。请到交易所核对订单与持仓。")
    finally:
        await trader.close()


def main():
    args = _parse_args()
    config = get_config()
    exchange = (args.exchange or config.get_str("exchange_name", "binance")).strip().lower()
    api_key = (config.get_str("exchange_api_key") or "").strip()
    api_secret = (config.get_str("exchange_api_secret") or "").strip()
    passphrase = (config.get_str("exchange_passphrase") or "").strip() or None
    sandbox = False if args.real else config.get_bool("exchange_sandbox", True)

    if not api_key or not api_secret:
        print("错误: 未配置 exchange_api_key / exchange_api_secret（或 IRONBULL_EXCHANGE_API_KEY / IRONBULL_EXCHANGE_API_SECRET）")
        sys.exit(1)
    if exchange == "okx" and not passphrase:
        print("错误: OKX 需配置 exchange_passphrase（或 IRONBULL_EXCHANGE_PASSPHRASE）")
        sys.exit(1)

    if args.real and not args.yes:
        print("警告: --real 将使用主网实盘，金额 %.2f USDT" % args.amount)
        try:
            input("按 Enter 继续，Ctrl+C 取消...")
        except KeyboardInterrupt:
            sys.exit(0)
    elif args.real:
        print("主网实盘，金额 %.2f USDT（已用 --yes 跳过确认）" % args.amount)
    else:
        print("使用测试网 (sandbox=True)，金额 %.2f USDT；主网请加 --real" % args.amount)

    asyncio.run(_run(
        exchange=exchange,
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase,
        sandbox=sandbox,
        symbol=(args.symbol or "BTC/USDT").strip(),
        amount_usdt=max(1.0, min(args.amount, 500.0)),
        dry_run=args.dry_run,
        no_sl_tp=args.no_sl_tp,
        close_only=args.close,
        cancel_orders=args.cancel_orders,
        sl_tp_only=args.sl_tp_only,
    ))


if __name__ == "__main__":
    main()
