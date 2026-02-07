#!/usr/bin/env python3
"""更新租户策略和策略目录的展示名/描述（参考老版文案风格）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core.database import init_database, get_engine

init_database()
engine = get_engine()

DESC_CONSERVATIVE = (
    "趋势动量 3.0 是一套基于人工智能行情识别的稳健型趋势跟随交易系统，"
    "通过对市场结构的实时分析，动态判断当前处于震荡区间或单边趋势状态，"
    "并据此自适应切换交易模式：\n"
    "在震荡行情中采用双向对冲策略以降低方向性风险；"
    "在趋势行情中执行单向顺势交易，捕捉中长期趋势动量。\n\n"
    "本策略融合趋势跟随模型、多因子量化分析与动态风险控制机制，"
    "对市场波动具备较强适应能力，整体抗波动性不低于 30%。"
    "在资金管理上，建议交易账户总资金规模不少于最大持仓金额的 2 倍，"
    "并采用约 60% 的资金参与策略运行，"
    "以保障在不同市场环境下的稳定执行与风险缓冲。\n\n"
    "趋势动量 3.0 由 Imperial College London（帝国理工学院）"
    "高性能计算研究团队联合资深基金管理团队共同研发，"
    "强调长期可持续性与系统化执行能力，"
    "适用于追求稳健增长、可复利运作的中长期交易者。\n"
    "在严格风控与纪律化执行前提下，"
    "本策略目标实现长期年化收益约 200%，"
    "同时保持风险与收益之间的合理平衡。"
)

DESC_BALANCED = (
    "趋势动量 3.0 均衡版 在稳健版的基础上适度提升了仓位配置比例，"
    "通过更均衡的风险收益比设计，"
    "为具备一定风险承受能力的投资者提供更具弹性的收益空间。\n\n"
    "系统架构与稳健版一脉相承，同样基于人工智能行情识别与多维市场状态分析引擎，"
    "融合趋势跟随模型与动态自适应切换机制，"
    "在震荡与趋势行情中灵活调配交易策略。"
    "均衡版将风险系数提升至 1.5%，"
    "在保留核心风控逻辑的前提下，放大趋势行情中的盈利效率。\n\n"
    "本策略同样融合多因子量化分析与动态风险控制机制，"
    "整体抗波动性约 25%。"
    "建议交易账户总资金规模不少于最大持仓金额的 1.5 倍，"
    "采用约 50% 的资金参与策略运行。\n\n"
    "趋势动量 3.0 均衡版 由 Imperial College London（帝国理工学院）"
    "高性能计算研究团队联合资深基金管理团队共同研发，"
    "适用于追求收益与安全性之间最优平衡的中长期交易者。\n"
    "在严格风控与纪律化执行前提下，"
    "本策略目标实现长期年化收益约 300%。"
)

DESC_AGGRESSIVE = (
    "趋势动量 3.0 激进版 是该系列中进攻性最强的配置方案，"
    "面向追求高收益、具备较高风险承受能力的专业交易者设计。\n\n"
    "在核心策略架构不变的前提下，激进版将风险系数提升至 2%，"
    "通过更大的仓位配置比例，"
    "在趋势行情中实现更高效的资金利用率与收益放大效果。"
    "系统依然采用人工智能驱动的多维市场状态识别引擎，"
    "在震荡行情中以对冲策略控制风险，"
    "在单边趋势中全力捕捉动量收益。\n\n"
    "系统上层通过卷积神经网络（CNN）与注意力机制（Attention），"
    "对多尺度市场微观结构进行建模，形成实时演化的市场状态画像；"
    "并结合订单流不平衡度的时空特征分析，"
    "精准识别多空力量变化与短期失衡窗口。\n\n"
    "在风险控制层面，激进版采用高频动态止损与仓位约束机制，"
    "整体抗波动能力约为 20%。"
    "资金管理建议仅使用账户总资金的 40% 参与策略运行，"
    "以确保整体账户风险可控。\n\n"
    "趋势动量 3.0 激进版 由 Imperial College London（帝国理工学院）"
    "智能算法研究团队与专业跨境交易团队联合研发，"
    "适用于具备明确风险认知与进攻型配置需求的交易者。\n"
    "在严格风控与纪律化执行前提下，"
    "策略目标实现长期年化收益约 400%。"
)

ITEMS = [
    {"ts_id": 9,  "s_id": 1, "dn": "趋势动量(稳健) 3.0", "dd": DESC_CONSERVATIVE},
    {"ts_id": 10, "s_id": 2, "dn": "趋势动量(均衡) 3.0", "dd": DESC_BALANCED},
    {"ts_id": 11, "s_id": 3, "dn": "趋势动量(激进) 3.0", "dd": DESC_AGGRESSIVE},
]

with engine.connect() as conn:
    for item in ITEMS:
        # 更新租户策略
        conn.execute(text(
            "UPDATE dim_tenant_strategy SET display_name=:dn, display_description=:dd WHERE id=:id"
        ), {"id": item["ts_id"], "dn": item["dn"], "dd": item["dd"]})
        print(f"[ok] 租户策略 id={item['ts_id']} -> {item['dn']}")

        # 同步更新策略目录的用户展示字段
        conn.execute(text(
            "UPDATE dim_strategy SET user_display_name=:udn, user_description=:udesc WHERE id=:id"
        ), {"id": item["s_id"], "udn": item["dn"], "udesc": item["dd"]})
        print(f"[ok] 策略目录 id={item['s_id']} -> {item['dn']}")

    conn.commit()
    print("\n=== ALL DONE ===")

    # 验证
    print("\n=== 验证 ===")
    for r in conn.execute(text(
        "SELECT id, display_name, LEFT(display_description, 40) AS dd_preview FROM dim_tenant_strategy ORDER BY sort_order"
    )).fetchall():
        print(f"  租户策略 id={r[0]}: {r[1]} | {r[2]}...")
