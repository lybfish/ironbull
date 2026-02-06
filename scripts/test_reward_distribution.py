#!/usr/bin/env python3
"""
奖励分销逻辑专项测试

测试范围：
  1. 等级配置完整性（dim_level_config S0-S7）
  2. LevelService 等级计算
  3. 直推奖（direct）：邀请人获 network_amount * 25%
  4. 级差奖（level_diff）：市场节点按等级差额获奖
  5. 平级奖（peer）：同等级上级获 network_amount * 10%
  6. 完整闭环：deduct_for_profit → ProfitPool → distribute_for_pool → 各奖励写入
  7. 边界情况：自持不足、无邀请人、路径无市场节点等

使用 DB 事务 rollback，不落库。
运行：PYTHONPATH=. IRONBULL_DB_PASSWORD=root123456 python3 scripts/test_reward_distribution.py
"""

import os
import sys
import traceback
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from libs.core.database import init_database, get_session
from libs.core.logger import setup_logging

setup_logging(level="WARNING", structured=False, service_name="test-reward")
init_database()

# ============================================================
# 测试框架
# ============================================================
results = []


def record(name, passed, detail=""):
    icon = "✅" if passed else "❌"
    results.append((name, passed, detail))
    dt = f"  — {detail}" if detail else ""
    print(f"  {icon} {name}{dt}")


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"{msg}: expected {expected}, got {actual}")


def assert_gt(actual, threshold, msg=""):
    if actual <= threshold:
        raise AssertionError(f"{msg}: expected > {threshold}, got {actual}")


def assert_close(actual, expected, tolerance=Decimal("0.01"), msg=""):
    if abs(Decimal(str(actual)) - Decimal(str(expected))) > tolerance:
        raise AssertionError(f"{msg}: expected ~{expected}, got {actual}")


# ============================================================
# 测试用例
# ============================================================

def test_01_level_config():
    """等级配置完整性"""
    session = get_session()
    try:
        from libs.member.models import LevelConfig
        configs = session.query(LevelConfig).order_by(LevelConfig.level).all()
        assert len(configs) == 8, f"等级配置应有 8 条(S0-S7), 实际 {len(configs)}"
        # S0 diff_rate=0, S7 diff_rate=0.8
        cfg_map = {c.level: c for c in configs}
        assert_eq(cfg_map[0].diff_rate, Decimal("0"), "S0 diff_rate")
        assert_eq(cfg_map[1].diff_rate, Decimal("0.2"), "S1 diff_rate")
        assert_eq(cfg_map[7].diff_rate, Decimal("0.8"), "S7 diff_rate")
        # min_team_perf 递增
        for i in range(1, 8):
            assert cfg_map[i].min_team_perf > cfg_map[i - 1].min_team_perf, \
                f"S{i} min_team_perf 应 > S{i-1}"
        record("01 等级配置完整(S0-S7)", True)
    except Exception as e:
        record("01 等级配置完整", False, str(e))
    finally:
        session.close()


def test_02_level_service_compute():
    """LevelService 等级计算"""
    session = get_session()
    try:
        from libs.member.level_service import LevelService
        svc = LevelService(session)
        # 方法存在且可调用
        assert callable(svc.compute_level)
        assert callable(svc.get_self_hold)
        assert callable(svc.get_team_performance)
        assert callable(svc.refresh_user_level)
        assert svc.get_level_name(0) == "S0"
        assert svc.get_level_name(5) == "S5"
        record("02 LevelService 方法可用", True)
    except Exception as e:
        record("02 LevelService 方法可用", False, str(e))
    finally:
        session.close()


def test_03_direct_reward():
    """直推奖：邀请人自持 >= 1000 时获奖"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.member.repository import MemberRepository
        from libs.reward.service import RewardService, NETWORK_RATE, DIRECT_RATE
        from libs.reward.models import ProfitPool

        repo = MemberRepository(session)

        # 创建测试用户链：inviter(自持充足) → user(产生利润)
        inviter = User(
            tenant_id=1, email="inviter_test@test.com", password_hash="x",
            invite_code="INV001", point_card_self=Decimal("0"),
            member_level=0, is_market_node=0, status=1,
        )
        session.add(inviter)
        session.flush()

        user = User(
            tenant_id=1, email="user_test@test.com", password_hash="x",
            invite_code="USR001", inviter_id=inviter.id,
            inviter_path=str(inviter.id),
            point_card_self=Decimal("0"),
            member_level=0, is_market_node=0, status=1,
        )
        session.add(user)
        session.flush()

        # 给 inviter 绑定一个有余额的交易所账户（模拟自持 >= 1000）
        from sqlalchemy import text
        session.execute(text(
            "INSERT INTO fact_exchange_account (user_id, tenant_id, exchange, api_key, api_secret, account_type, balance, futures_balance, futures_available, status) "
            "VALUES (:uid, 1, 'binance', 'k', 's', 'futures', 2000, 2000, 2000, 1)"
        ), {"uid": inviter.id})
        session.flush()

        # 创建利润池
        pool = ProfitPool(
            user_id=user.id,
            profit_amount=Decimal("1000"),
            deduct_amount=Decimal("300"),
            self_deduct=Decimal("300"),
            gift_deduct=Decimal("0"),
            pool_amount=Decimal("300"),  # 300 USDT 进入利润池
            status=1,
            settle_batch="test_batch_03",
        )
        from libs.reward.repository import RewardRepository
        rr = RewardRepository(session)
        rr.create_profit_pool(pool)

        # 执行分销
        svc = RewardService(session)
        rewards = svc.distribute_for_pool(pool)

        # 验证直推奖
        direct_rewards = [r for r in rewards if r.reward_type == "direct"]
        assert len(direct_rewards) == 1, f"应有 1 条直推奖, 实际 {len(direct_rewards)}"
        dr = direct_rewards[0]
        expected_direct = Decimal("300") * NETWORK_RATE * DIRECT_RATE  # 300 * 0.2 * 0.25 = 15
        assert_close(dr.amount, expected_direct, msg="直推奖金额")
        assert_eq(dr.user_id, inviter.id, "直推奖收益人")
        assert_eq(dr.source_user_id, user.id, "直推奖来源")

        # 验证 inviter 的 reward_usdt 已更新
        session.refresh(inviter)
        assert_close(inviter.reward_usdt, expected_direct, msg="inviter reward_usdt")

        record("03 直推奖计算正确", True,
               f"pool=300, direct={float(dr.amount):.2f} (预期={float(expected_direct):.2f})")

    except Exception as e:
        record("03 直推奖计算", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_04_direct_reward_no_selfhold():
    """直推奖：邀请人自持 < 1000 时不获奖"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.reward.service import RewardService
        from libs.reward.models import ProfitPool
        from libs.reward.repository import RewardRepository

        # inviter 无交易所账户（自持=0）
        inviter = User(
            tenant_id=1, email="inv_nosh@test.com", password_hash="x",
            invite_code="INV002", member_level=0, status=1,
        )
        session.add(inviter)
        session.flush()

        user = User(
            tenant_id=1, email="usr_nosh@test.com", password_hash="x",
            invite_code="USR002", inviter_id=inviter.id,
            inviter_path=str(inviter.id), member_level=0, status=1,
        )
        session.add(user)
        session.flush()

        pool = ProfitPool(
            user_id=user.id, profit_amount=Decimal("500"),
            deduct_amount=Decimal("150"), self_deduct=Decimal("150"),
            gift_deduct=Decimal("0"), pool_amount=Decimal("150"), status=1,
        )
        RewardRepository(session).create_profit_pool(pool)

        rewards = RewardService(session).distribute_for_pool(pool)
        direct_rewards = [r for r in rewards if r.reward_type == "direct"]
        assert len(direct_rewards) == 0, f"自持不足不应有直推奖, 实际 {len(direct_rewards)} 条"
        record("04 自持不足不发直推奖", True)

    except Exception as e:
        record("04 自持不足不发直推奖", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_05_level_diff_reward():
    """级差奖：市场节点按等级差额获奖"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.reward.service import RewardService, NETWORK_RATE
        from libs.reward.models import ProfitPool
        from libs.reward.repository import RewardRepository
        from sqlalchemy import text

        # 构建 3 层邀请链：
        #   node_s3 (S3, diff_rate=0.4, market_node)
        #     → node_s1 (S1, diff_rate=0.2, market_node)
        #       → user (S0, 产生利润)
        node_s3 = User(
            tenant_id=1, email="node_s3@test.com", password_hash="x",
            invite_code="NS3001", member_level=3, is_market_node=1, status=1,
        )
        session.add(node_s3)
        session.flush()

        node_s1 = User(
            tenant_id=1, email="node_s1@test.com", password_hash="x",
            invite_code="NS1001", inviter_id=node_s3.id,
            inviter_path=str(node_s3.id),
            member_level=1, is_market_node=1, status=1,
        )
        session.add(node_s1)
        session.flush()

        user = User(
            tenant_id=1, email="usr_diff@test.com", password_hash="x",
            invite_code="UD001", inviter_id=node_s1.id,
            inviter_path=f"{node_s3.id}/{node_s1.id}",
            member_level=0, is_market_node=0, status=1,
        )
        session.add(user)
        session.flush()

        # 给 node_s1 绑账户（自持 >= 1000），用于直推奖
        session.execute(text(
            "INSERT INTO fact_exchange_account (user_id, tenant_id, exchange, api_key, api_secret, account_type, futures_balance, futures_available, status) "
            "VALUES (:uid, 1, 'binance', 'k', 's', 'futures', 2000, 2000, 1)"
        ), {"uid": node_s1.id})
        session.flush()

        pool = ProfitPool(
            user_id=user.id, profit_amount=Decimal("10000"),
            deduct_amount=Decimal("3000"), self_deduct=Decimal("3000"),
            gift_deduct=Decimal("0"), pool_amount=Decimal("3000"), status=1,
            settle_batch="test_batch_05",
        )
        RewardRepository(session).create_profit_pool(pool)

        rewards = RewardService(session).distribute_for_pool(pool)

        # 分析结果
        network_amount = Decimal("3000") * NETWORK_RATE  # 600
        level_diffs = [r for r in rewards if r.reward_type == "level_diff"]
        directs = [r for r in rewards if r.reward_type == "direct"]

        # node_s1 (S1) 应获级差奖：diff_rate=0.2 - 0(last_rate) = 0.2
        # node_s3 (S3) 应获级差奖：diff_rate=0.4 - 0.2 = 0.2
        assert len(level_diffs) == 2, f"应有 2 条级差奖, 实际 {len(level_diffs)}"

        s1_rewards = [r for r in level_diffs if r.user_id == node_s1.id]
        s3_rewards = [r for r in level_diffs if r.user_id == node_s3.id]

        assert len(s1_rewards) == 1, "S1 应获 1 条级差奖"
        assert len(s3_rewards) == 1, "S3 应获 1 条级差奖"

        # S1: network * 0.2 = 600 * 0.2 = 120
        expected_s1 = network_amount * Decimal("0.2")
        assert_close(s1_rewards[0].amount, expected_s1, msg="S1 级差奖金额")

        # S3: network * (0.4 - 0.2) = 600 * 0.2 = 120
        expected_s3 = network_amount * Decimal("0.2")
        assert_close(s3_rewards[0].amount, expected_s3, msg="S3 级差奖金额")

        record("05 级差奖计算正确", True,
               f"S1={float(s1_rewards[0].amount):.2f}, S3={float(s3_rewards[0].amount):.2f}, "
               f"network={float(network_amount):.2f}")

    except Exception as e:
        record("05 级差奖计算", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_06_peer_reward():
    """平级奖：同等级上级获 network * 10%"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.reward.service import RewardService, NETWORK_RATE, PEER_RATE
        from libs.reward.models import ProfitPool
        from libs.reward.repository import RewardRepository

        # 构建：peer_s2(S2, node) → user(S2)
        # user 和 peer_s2 同级，peer_s2 应获平级奖
        peer_s2 = User(
            tenant_id=1, email="peer_s2@test.com", password_hash="x",
            invite_code="PS2001", member_level=2, is_market_node=1, status=1,
        )
        session.add(peer_s2)
        session.flush()

        user = User(
            tenant_id=1, email="usr_peer@test.com", password_hash="x",
            invite_code="UP001", inviter_id=peer_s2.id,
            inviter_path=str(peer_s2.id),
            member_level=2, is_market_node=0, status=1,
        )
        session.add(user)
        session.flush()

        pool = ProfitPool(
            user_id=user.id, profit_amount=Decimal("5000"),
            deduct_amount=Decimal("1500"), self_deduct=Decimal("1500"),
            gift_deduct=Decimal("0"), pool_amount=Decimal("1500"), status=1,
            settle_batch="test_batch_06",
        )
        RewardRepository(session).create_profit_pool(pool)

        rewards = RewardService(session).distribute_for_pool(pool)
        peers = [r for r in rewards if r.reward_type == "peer"]

        network_amount = Decimal("1500") * NETWORK_RATE  # 300
        expected_peer = network_amount * PEER_RATE  # 300 * 0.1 = 30

        assert len(peers) == 1, f"应有 1 条平级奖, 实际 {len(peers)}"
        assert_close(peers[0].amount, expected_peer, msg="平级奖金额")
        assert_eq(peers[0].user_id, peer_s2.id, "平级奖收益人")

        record("06 平级奖计算正确", True,
               f"peer={float(peers[0].amount):.2f} (预期={float(expected_peer):.2f})")

    except Exception as e:
        record("06 平级奖计算", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_07_no_inviter_no_path():
    """无邀请人、无邀请路径不报错"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.reward.service import RewardService
        from libs.reward.models import ProfitPool
        from libs.reward.repository import RewardRepository

        user = User(
            tenant_id=1, email="solo@test.com", password_hash="x",
            invite_code="SOL001", inviter_id=None, inviter_path=None,
            member_level=0, status=1,
        )
        session.add(user)
        session.flush()

        pool = ProfitPool(
            user_id=user.id, profit_amount=Decimal("100"),
            deduct_amount=Decimal("30"), self_deduct=Decimal("30"),
            gift_deduct=Decimal("0"), pool_amount=Decimal("30"), status=1,
        )
        RewardRepository(session).create_profit_pool(pool)

        rewards = RewardService(session).distribute_for_pool(pool)
        assert len(rewards) == 0, f"无邀请链路应无奖励, 实际 {len(rewards)}"

        # pool 应被标记为已结算
        session.refresh(pool)
        assert_eq(pool.status, 2, "pool.status 应为 2(已结算)")

        record("07 无邀请人不报错", True)

    except Exception as e:
        record("07 无邀请人不报错", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_08_full_chain_deduct_to_distribute():
    """完整闭环：deduct_for_profit → ProfitPool → distribute_for_pool"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.member.repository import MemberRepository
        from libs.pointcard.service import PointCardService
        from libs.reward.models import ProfitPool
        from sqlalchemy import text

        repo = MemberRepository(session)

        # 构建邀请链：inviter → user
        inviter = User(
            tenant_id=1, email="inv_full@test.com", password_hash="x",
            invite_code="IF001", member_level=0, is_market_node=0, status=1,
        )
        session.add(inviter)
        session.flush()

        # inviter 绑交易所账户（自持 >= 1000）
        session.execute(text(
            "INSERT INTO fact_exchange_account (user_id, tenant_id, exchange, api_key, api_secret, account_type, futures_balance, futures_available, status) "
            "VALUES (:uid, 1, 'binance', 'k', 's', 'futures', 5000, 5000, 1)"
        ), {"uid": inviter.id})

        user = User(
            tenant_id=1, email="usr_full@test.com", password_hash="x",
            invite_code="UF001", inviter_id=inviter.id,
            inviter_path=str(inviter.id),
            point_card_self=Decimal("500"), point_card_gift=Decimal("100"),
            member_level=0, is_market_node=0, status=1,
        )
        session.add(user)
        session.flush()

        # 执行盈利扣费
        svc = PointCardService(session)
        success, err, data = svc.deduct_for_profit(user.id, Decimal("1000"))

        assert success, f"deduct_for_profit 应成功: {err}"
        assert data is not None

        # 检查扣费金额: 30% of 1000 = 300
        assert_close(data["deduct_total"], 300, msg="扣费总额")
        # self 扣 300（余额 500 够扣）
        assert_close(data["self_deduct"], 300, msg="self 扣费")
        assert_close(data["gift_deduct"], 0, msg="gift 扣费")
        # pool_amount = self_deduct = 300
        assert_close(data["pool_amount"], 300, msg="利润池金额")

        # 检查用户点卡余额
        session.refresh(user)
        assert_close(user.point_card_self, 200, msg="扣费后 self 余额")  # 500 - 300
        assert_close(user.point_card_gift, 100, msg="扣费后 gift 余额")  # 不动

        # 检查 profit_pool 已创建且已结算 (distribute_for_pool 被立即调用)
        pools = session.query(ProfitPool).filter(ProfitPool.user_id == user.id).all()
        assert len(pools) == 1, f"应有 1 条利润池记录, 实际 {len(pools)}"
        assert_eq(pools[0].status, 2, "利润池应为已结算")

        # 检查 inviter 获得了直推奖
        session.refresh(inviter)
        # direct = 300 * 0.2 * 0.25 = 15
        assert_gt(inviter.reward_usdt, Decimal("0"), "inviter 应获奖")
        assert_close(inviter.reward_usdt, 15, msg="inviter 直推奖金额")

        record("08 完整闭环(扣费→分销)", True,
               f"deduct=300, pool=300, inviter_reward={float(inviter.reward_usdt):.2f}")

    except Exception as e:
        record("08 完整闭环(扣费→分销)", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_09_mixed_self_gift_deduct():
    """self 不够扣时混合扣 self + gift"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.pointcard.service import PointCardService

        user = User(
            tenant_id=1, email="mix_deduct@test.com", password_hash="x",
            invite_code="MX001",
            point_card_self=Decimal("100"), point_card_gift=Decimal("300"),
            member_level=0, status=1,
        )
        session.add(user)
        session.flush()

        # 盈利 1000 → 扣费 300，self 只有 100，还需 gift 200
        svc = PointCardService(session)
        success, err, data = svc.deduct_for_profit(user.id, Decimal("1000"))

        assert success, f"应成功: {err}"
        assert_close(data["self_deduct"], 100, msg="self 全扣")
        assert_close(data["gift_deduct"], 200, msg="gift 补扣 200")
        assert_close(data["pool_amount"], 100, msg="仅 self 部分进利润池")

        session.refresh(user)
        assert_close(user.point_card_self, 0, msg="self 清零")
        assert_close(user.point_card_gift, 100, msg="gift 扣后 100")

        record("09 混合扣费(self+gift)", True,
               f"self_deduct=100, gift_deduct=200, pool=100")

    except Exception as e:
        record("09 混合扣费", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_10_complex_chain():
    """复杂邀请链：S5 → S3 → S1 → user(S0) → 利润，级差逐级吃差"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.reward.service import RewardService, NETWORK_RATE
        from libs.reward.models import ProfitPool
        from libs.reward.repository import RewardRepository

        # 构建 4 层：s5 → s3 → s1 → user
        s5 = User(tenant_id=1, email="s5@t.com", password_hash="x", invite_code="S5X01",
                   member_level=5, is_market_node=1, status=1)
        session.add(s5)
        session.flush()

        s3 = User(tenant_id=1, email="s3@t.com", password_hash="x", invite_code="S3X01",
                   inviter_id=s5.id, inviter_path=str(s5.id),
                   member_level=3, is_market_node=1, status=1)
        session.add(s3)
        session.flush()

        s1 = User(tenant_id=1, email="s1@t.com", password_hash="x", invite_code="S1X01",
                   inviter_id=s3.id, inviter_path=f"{s5.id}/{s3.id}",
                   member_level=1, is_market_node=1, status=1)
        session.add(s1)
        session.flush()

        user = User(tenant_id=1, email="u0@t.com", password_hash="x", invite_code="U0X01",
                    inviter_id=s1.id, inviter_path=f"{s5.id}/{s3.id}/{s1.id}",
                    member_level=0, is_market_node=0, status=1)
        session.add(user)
        session.flush()

        pool = ProfitPool(
            user_id=user.id, profit_amount=Decimal("10000"),
            deduct_amount=Decimal("3000"), self_deduct=Decimal("3000"),
            gift_deduct=Decimal("0"), pool_amount=Decimal("3000"), status=1,
            settle_batch="test_10",
        )
        RewardRepository(session).create_profit_pool(pool)

        rewards = RewardService(session).distribute_for_pool(pool)
        network = Decimal("3000") * NETWORK_RATE  # 600

        level_diffs = {r.user_id: r for r in rewards if r.reward_type == "level_diff"}
        peers = [r for r in rewards if r.reward_type == "peer"]

        # S1(diff_rate=0.2): 得 0.2 - 0 = 0.2, 金额 = 600 * 0.2 = 120
        assert s1.id in level_diffs, "S1 应获级差奖"
        assert_close(level_diffs[s1.id].amount, 120, msg="S1 级差")

        # S3(diff_rate=0.4): 得 0.4 - 0.2 = 0.2, 金额 = 600 * 0.2 = 120
        assert s3.id in level_diffs, "S3 应获级差奖"
        assert_close(level_diffs[s3.id].amount, 120, msg="S3 级差")

        # S5(diff_rate=0.6): 得 0.6 - 0.4 = 0.2, 金额 = 600 * 0.2 = 120
        assert s5.id in level_diffs, "S5 应获级差奖"
        assert_close(level_diffs[s5.id].amount, 120, msg="S5 级差")

        # 无平级奖（source_level=0, 没有同级 market_node）
        assert len(peers) == 0, f"S0 无同级节点, 不应有平级奖, 实际 {len(peers)}"

        total_diff = sum(float(r.amount) for r in level_diffs.values())
        record("10 复杂链路级差(S5→S3→S1→S0)", True,
               f"S1=120, S3=120, S5=120, total_diff={total_diff:.2f}")

    except Exception as e:
        record("10 复杂链路级差", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_11_peer_only_once():
    """平级奖只发一次（第一个同级市场节点）"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.reward.service import RewardService, NETWORK_RATE, PEER_RATE
        from libs.reward.models import ProfitPool
        from libs.reward.repository import RewardRepository

        # 链路：n2_a(S2,node) → n2_b(S2,node) → user(S2)
        # 两个同级节点，只有第一个遇到的（n2_b，从 user 往上找）应获平级奖
        n2_a = User(tenant_id=1, email="n2a@t.com", password_hash="x", invite_code="N2A01",
                    member_level=2, is_market_node=1, status=1)
        session.add(n2_a)
        session.flush()

        n2_b = User(tenant_id=1, email="n2b@t.com", password_hash="x", invite_code="N2B01",
                    inviter_id=n2_a.id, inviter_path=str(n2_a.id),
                    member_level=2, is_market_node=1, status=1)
        session.add(n2_b)
        session.flush()

        user = User(tenant_id=1, email="up2@t.com", password_hash="x", invite_code="UP201",
                    inviter_id=n2_b.id, inviter_path=f"{n2_a.id}/{n2_b.id}",
                    member_level=2, is_market_node=0, status=1)
        session.add(user)
        session.flush()

        pool = ProfitPool(
            user_id=user.id, profit_amount=Decimal("5000"),
            deduct_amount=Decimal("1500"), self_deduct=Decimal("1500"),
            gift_deduct=Decimal("0"), pool_amount=Decimal("1500"), status=1,
        )
        RewardRepository(session).create_profit_pool(pool)

        rewards = RewardService(session).distribute_for_pool(pool)
        peers = [r for r in rewards if r.reward_type == "peer"]

        assert len(peers) == 1, f"平级奖应只发 1 次, 实际 {len(peers)}"
        # 应给 n2_b（从 user 出发，反向遍历路径，第一个遇到的同级节点）
        assert_eq(peers[0].user_id, n2_b.id, "平级奖应给最近的同级节点")

        network = Decimal("1500") * NETWORK_RATE  # 300
        expected_peer = network * PEER_RATE  # 30
        assert_close(peers[0].amount, expected_peer, msg="平级奖金额")

        record("11 平级奖只发一次", True,
               f"peer给n2_b={float(peers[0].amount):.2f}")

    except Exception as e:
        record("11 平级奖只发一次", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_12_skip_non_market_node():
    """级差奖只给 is_market_node=1 的用户"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.reward.service import RewardService
        from libs.reward.models import ProfitPool
        from libs.reward.repository import RewardRepository

        # 链路：s3(node) → normal_s2(非node) → user
        s3 = User(tenant_id=1, email="s3skip@t.com", password_hash="x", invite_code="S3S01",
                  member_level=3, is_market_node=1, status=1)
        session.add(s3)
        session.flush()

        normal = User(tenant_id=1, email="norm@t.com", password_hash="x", invite_code="NRM01",
                     inviter_id=s3.id, inviter_path=str(s3.id),
                     member_level=2, is_market_node=0, status=1)  # 非市场节点
        session.add(normal)
        session.flush()

        user = User(tenant_id=1, email="uskip@t.com", password_hash="x", invite_code="USK01",
                   inviter_id=normal.id, inviter_path=f"{s3.id}/{normal.id}",
                   member_level=0, status=1)
        session.add(user)
        session.flush()

        pool = ProfitPool(
            user_id=user.id, profit_amount=Decimal("2000"),
            deduct_amount=Decimal("600"), self_deduct=Decimal("600"),
            gift_deduct=Decimal("0"), pool_amount=Decimal("600"), status=1,
        )
        RewardRepository(session).create_profit_pool(pool)

        rewards = RewardService(session).distribute_for_pool(pool)
        diffs = [r for r in rewards if r.reward_type == "level_diff"]

        # normal_s2 不是 market_node，应被跳过
        normal_rewards = [r for r in diffs if r.user_id == normal.id]
        assert len(normal_rewards) == 0, "非市场节点不应获级差奖"

        # s3 应获全额差（diff_rate=0.4 - 0 = 0.4）
        s3_rewards = [r for r in diffs if r.user_id == s3.id]
        assert len(s3_rewards) == 1, f"S3 应获级差奖, 实际 {len(s3_rewards)}"

        record("12 非市场节点被跳过", True)

    except Exception as e:
        record("12 非市场节点被跳过", False, str(e))
    finally:
        session.rollback()
        session.close()


def test_13_reward_log_written():
    """分销写入 fact_reward_log 流水"""
    session = get_session()
    try:
        from libs.member.models import User
        from libs.reward.service import RewardService
        from libs.reward.models import ProfitPool, RewardLog
        from libs.reward.repository import RewardRepository
        from sqlalchemy import text

        inviter = User(tenant_id=1, email="invlog@t.com", password_hash="x",
                      invite_code="IL001", member_level=1, is_market_node=1, status=1)
        session.add(inviter)
        session.flush()

        # 给 inviter 绑账户
        session.execute(text(
            "INSERT INTO fact_exchange_account (user_id, tenant_id, exchange, api_key, api_secret, account_type, futures_balance, futures_available, status) "
            "VALUES (:uid, 1, 'binance', 'k', 's', 'futures', 2000, 2000, 1)"
        ), {"uid": inviter.id})

        user = User(tenant_id=1, email="usrlog@t.com", password_hash="x",
                   invite_code="UL001", inviter_id=inviter.id,
                   inviter_path=str(inviter.id), member_level=0, status=1)
        session.add(user)
        session.flush()

        pool = ProfitPool(
            user_id=user.id, profit_amount=Decimal("2000"),
            deduct_amount=Decimal("600"), self_deduct=Decimal("600"),
            gift_deduct=Decimal("0"), pool_amount=Decimal("600"), status=1,
        )
        RewardRepository(session).create_profit_pool(pool)

        RewardService(session).distribute_for_pool(pool)

        # 检查 reward_log 流水
        logs = session.query(RewardLog).filter(RewardLog.user_id == inviter.id).all()
        assert len(logs) >= 1, f"应有 reward_log, 实际 {len(logs)}"
        for log in logs:
            assert log.change_type == "reward_in"
            assert log.amount > 0
            assert log.after_balance > log.before_balance

        record("13 分销写入 reward_log", True, f"{len(logs)} 条流水")

    except Exception as e:
        record("13 分销写入 reward_log", False, str(e))
    finally:
        session.rollback()
        session.close()


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 70)
    print("  IronBull 奖励分销逻辑专项测试")
    print("=" * 70)

    test_01_level_config()
    test_02_level_service_compute()
    test_03_direct_reward()
    test_04_direct_reward_no_selfhold()
    test_05_level_diff_reward()
    test_06_peer_reward()
    test_07_no_inviter_no_path()
    test_08_full_chain_deduct_to_distribute()
    test_09_mixed_self_gift_deduct()
    test_10_complex_chain()
    test_11_peer_only_once()
    test_12_skip_non_market_node()
    test_13_reward_log_written()

    print("\n" + "=" * 70)
    total = len(results)
    passed = sum(1 for _, p, _ in results if p)
    failed = total - passed
    print(f"  汇总: {total} 项, ✅ {passed} 通过, ❌ {failed} 失败")
    print("=" * 70)

    if failed:
        print("\n❌ 失败项:")
        for name, p, detail in results:
            if not p:
                print(f"  {name} — {detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
