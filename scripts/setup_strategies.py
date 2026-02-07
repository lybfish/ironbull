#!/usr/bin/env python3
"""
一次性脚本：重构策略目录、租户策略、策略绑定
- 3个策略：市场状态·稳健/均衡/激进（共享算法配置）
- 3个租户策略实例
- 1个策略绑定（稳健版）
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core.database import init_database, get_engine

init_database()
engine = get_engine()

CONFIG = json.dumps({"atr_mult_sl": 1.2, "atr_mult_tp": 4.5, "adx_range_threshold": 15, "adx_trend_threshold": 35})
SYMBOLS = json.dumps(["BTCUSDT", "ETHUSDT", "SOLUSDT"])

with engine.connect() as conn:
    # === 1. 策略目录 ===
    # id=1: market_regime -> 稳健
    conn.execute(text(
        "UPDATE dim_strategy SET "
        "name='市场状态·稳健', capital=1000, leverage=20, risk_mode=1, amount_usdt=200, "
        "min_confidence=50, cooldown_minutes=60, status=1, "
        "show_to_user=1, user_display_name='市场状态·稳健版', "
        "user_description='基于多维市场状态识别的量化策略，稳健风控(1%)，适合追求稳定收益的投资者' "
        "WHERE id=1"
    ))
    print("[ok] 策略 id=1: market_regime -> 市场状态·稳健 (risk_mode=1, amt=200)")

    # id=2: -> market_regime_balanced 均衡
    conn.execute(text(
        "UPDATE dim_strategy SET "
        "code='market_regime_balanced', name='市场状态·均衡', description='市场状态策略 均衡版', "
        "symbol='BTC/USDT', symbols=:symbols, timeframe='1h', "
        "exchange=NULL, market_type='future', "
        "min_capital=200, risk_level=2, "
        "capital=1000, leverage=20, risk_mode=2, amount_usdt=300, "
        "min_confidence=50, cooldown_minutes=60, "
        "config=:config, status=1, "
        "show_to_user=1, user_display_name='市场状态·均衡版', "
        "user_description='基于多维市场状态识别的量化策略，均衡配置(1.5%)，兼顾收益与风控' "
        "WHERE id=2"
    ), {"symbols": SYMBOLS, "config": CONFIG})
    print("[ok] 策略 id=2: -> market_regime_balanced 市场状态·均衡 (risk_mode=2, amt=300)")

    # id=3: -> market_regime_aggressive 激进
    conn.execute(text(
        "UPDATE dim_strategy SET "
        "code='market_regime_aggressive', name='市场状态·激进', description='市场状态策略 激进版', "
        "symbol='BTC/USDT', symbols=:symbols, timeframe='1h', "
        "exchange=NULL, market_type='future', "
        "min_capital=200, risk_level=3, "
        "capital=1000, leverage=20, risk_mode=3, amount_usdt=400, "
        "min_confidence=50, cooldown_minutes=60, "
        "config=:config, status=1, "
        "show_to_user=1, user_display_name='市场状态·激进版', "
        "user_description='基于多维市场状态识别的量化策略，激进风格(2%)，适合追求高收益的投资者' "
        "WHERE id=3"
    ), {"symbols": SYMBOLS, "config": CONFIG})
    print("[ok] 策略 id=3: -> market_regime_aggressive 市场状态·激进 (risk_mode=3, amt=400)")

    # === 2. 租户策略 ===
    r2 = conn.execute(text("DELETE FROM dim_tenant_strategy")).rowcount
    print(f"[ok] 清空租户策略 {r2} 条")

    ts_rows = [
        (1, 1, "市场状态·稳健版", "基于多维市场状态识别，稳健风控(1%)，适合追求稳定收益的投资者", 1000, 20, 1, 200, 200, 1, 1),
        (1, 2, "市场状态·均衡版", "基于多维市场状态识别，均衡配置(1.5%)，兼顾收益与风控", 1000, 20, 2, 300, 200, 1, 2),
        (1, 3, "市场状态·激进版", "基于多维市场状态识别，激进风格(2%)，适合追求高收益的投资者", 1000, 20, 3, 400, 200, 1, 3),
    ]
    for tid, sid, dn, dd, cap, lev, rm, amt, mc, st, so in ts_rows:
        conn.execute(text(
            "INSERT INTO dim_tenant_strategy "
            "(tenant_id, strategy_id, display_name, display_description, capital, leverage, risk_mode, amount_usdt, min_capital, status, sort_order, created_at, updated_at) "
            "VALUES (:tid, :sid, :dn, :dd, :cap, :lev, :rm, :amt, :mc, :st, :so, NOW(), NOW())"
        ), {"tid": tid, "sid": sid, "dn": dn, "dd": dd, "cap": cap, "lev": lev, "rm": rm, "amt": amt, "mc": mc, "st": st, "so": so})
        print(f"[ok] 租户策略: {dn} (tid={tid}, sid={sid})")

    # === 3. 策略绑定 ===
    r3 = conn.execute(text("DELETE FROM dim_strategy_binding")).rowcount
    print(f"[ok] 清空策略绑定 {r3} 条")

    row = conn.execute(text("SELECT user_id, exchange, execution_node_id FROM fact_exchange_account WHERE id=1")).fetchone()
    if row:
        uid = row[0]
        print(f"[info] account_id=1 user={uid} exchange={row[1]} node={row[2]}")
        conn.execute(text(
            "INSERT INTO dim_strategy_binding "
            "(user_id, account_id, strategy_code, mode, capital, leverage, risk_mode, status, created_at, updated_at) "
            "VALUES (:uid, 1, 'market_regime', 2, 1000, 20, 1, 1, NOW(), NOW())"
        ), {"uid": uid})
        print(f"[ok] 策略绑定: user={uid} acc=1 code=market_regime 稳健 cap=1000 lev=20")

    conn.commit()
    print("\n=== ALL DONE ===")

    # 验证
    print("\n=== 验证 ===")
    for r in conn.execute(text("SELECT id, code, name, status, capital, leverage, risk_mode, amount_usdt FROM dim_strategy ORDER BY id")).fetchall():
        print(f"  策略: id={r[0]} code={r[1]} name={r[2]} status={r[3]} cap={r[4]} lev={r[5]} rm={r[6]} amt={r[7]}")
    for r in conn.execute(text("SELECT id, tenant_id, strategy_id, display_name, risk_mode, amount_usdt, status FROM dim_tenant_strategy ORDER BY sort_order")).fetchall():
        print(f"  租户策略: id={r[0]} tid={r[1]} sid={r[2]} name={r[3]} rm={r[4]} amt={r[5]} st={r[6]}")
    for r in conn.execute(text("SELECT id, user_id, account_id, strategy_code, capital, leverage, risk_mode, status FROM dim_strategy_binding ORDER BY id")).fetchall():
        print(f"  绑定: id={r[0]} uid={r[1]} acc={r[2]} code={r[3]} cap={r[4]} lev={r[5]} rm={r[6]} st={r[7]}")
