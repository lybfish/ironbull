#!/usr/bin/env python3
"""
实盘闭环验证脚本

在 local_monitor 运行一段时间后执行，检查订单/成交/持仓/资金是否正确落库，
以及分析指标是否可计算。

用法：
    cd /path/to/ironbull
    python scripts/verify_live_loop.py
    python scripts/verify_live_loop.py --tenant 1 --account 1
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core import get_config, get_logger
from libs.core.database import get_session, init_database
from libs.order_trade import OrderTradeService
from libs.order_trade.contracts import OrderFilter, FillFilter
from libs.position import PositionService
from libs.position.contracts import PositionFilter
from libs.ledger import LedgerService
from libs.ledger.contracts import AccountFilter

log = get_logger("verify-live")


def run(tenant_id: int, account_id: int) -> int:
    init_database()
    session = get_session()
    try:
        # 1. fact_order
        order_svc = OrderTradeService(session)
        orders, order_total = order_svc.list_orders(OrderFilter(tenant_id=tenant_id, account_id=account_id, limit=500))
        order_count = len(orders)
        filled_orders = [o for o in orders if o.status == "FILLED"]

        # 2. fact_fill
        fills, fill_total = order_svc.list_fills(FillFilter(tenant_id=tenant_id, account_id=account_id, limit=500))
        fill_count = len(fills)

        # 3. fact_position
        pos_svc = PositionService(session)
        positions = pos_svc.list_positions(
            PositionFilter(tenant_id=tenant_id, account_id=account_id, has_position=True, limit=200)
        )
        position_count = len(positions)

        # 4. fact_account (Ledger)
        ledger_svc = LedgerService(session)
        accounts = ledger_svc.list_accounts(AccountFilter(tenant_id=tenant_id, account_id=account_id, limit=50))
        account_count = len(accounts)
        total_balance = sum(float(a.balance) for a in accounts)
        total_available = sum(float(a.available) for a in accounts)

        # 5. 分析是否可算（有成交即可算统计；绩效需有快照或权益）
        analytics_ok = fill_count > 0  # 有成交即可尝试计算统计/绩效

        # 输出报告
        print("\n" + "=" * 56)
        print("  实盘闭环验证报告")
        print("  tenant_id=%s  account_id=%s" % (tenant_id, account_id))
        print("=" * 56)
        print("  fact_order    订单数: %s  (已成交: %s)" % (order_count, len(filled_orders)))
        print("  fact_fill     成交数: %s" % fill_count)
        print("  fact_position 持仓数: %s (quantity>0)" % position_count)
        print("  fact_account  账户数: %s  总余额: %.4f  总可用: %.4f" % (account_count, total_balance, total_available))
        print("  分析指标可算: %s" % ("是" if analytics_ok else "否（需至少 1 笔成交）"))
        print("=" * 56)

        if order_count > 0:
            o = orders[0]
            print("\n  最新订单样例: order_id=%s symbol=%s side=%s status=%s" % (
                o.order_id, o.symbol, o.side, o.status
            ))
        if fill_count > 0:
            f = fills[0]
            print("  最新成交样例: fill_id=%s symbol=%s side=%s qty=%s price=%s" % (
                f.fill_id, f.symbol, f.side, f.quantity, f.price
            ))
        if position_count > 0:
            p = positions[0]
            print("  持仓样例: symbol=%s side=%s quantity=%s avg_cost=%s" % (
                p.symbol, p.position_side, p.quantity, p.avg_cost
            ))
        print()

        # 判定：数据库可读且结构正确即通过；无数据时仅提示
        if order_count == 0 and fill_count == 0:
            print("  提示: 尚无订单/成交，请先运行 local_monitor 并产生交易。")
            print("  示例: python scripts/local_monitor.py -m auto -i 60")
            return 0
        return 0
    except Exception as e:
        log.error("verify failed: %s", e)
        print("\n  验证失败: %s" % e)
        return 1
    finally:
        session.close()


def main():
    p = argparse.ArgumentParser(description="实盘闭环验证")
    p.add_argument("--tenant", "-t", type=int, default=None, help="租户ID（默认从 config 或 1）")
    p.add_argument("--account", "-a", type=int, default=None, help="账户ID（默认从 config 或 1）")
    args = p.parse_args()
    config = get_config()
    tenant_id = args.tenant if args.tenant is not None else config.get_int("tenant_id", 1)
    account_id = args.account if args.account is not None else config.get_int("account_id", 1)
    return run(tenant_id, account_id)


if __name__ == "__main__":
    sys.exit(main())
