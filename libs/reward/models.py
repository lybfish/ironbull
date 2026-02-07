"""
Reward Models - 利润池、奖励流水、提现记录
"""

from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from sqlalchemy.dialects.mysql import DECIMAL

from libs.core.database import Base


class ProfitPool(Base):
    """
    利润池表（fact_profit_pool）
    """
    __tablename__ = "fact_profit_pool"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    profit_amount = Column(DECIMAL(20, 8), nullable=False)
    deduct_amount = Column(DECIMAL(20, 8), nullable=False)
    self_deduct = Column(DECIMAL(20, 8), nullable=False, default=0)
    gift_deduct = Column(DECIMAL(20, 8), nullable=False, default=0)
    pool_amount = Column(DECIMAL(20, 8), nullable=False)
    # --- 分配追踪字段 ---
    tech_amount = Column(DECIMAL(20, 8), nullable=False, default=0, comment="技术团队 10%")
    network_amount = Column(DECIMAL(20, 8), nullable=False, default=0, comment="网体总额 20%")
    platform_amount = Column(DECIMAL(20, 8), nullable=False, default=0, comment="平台留存 70%")
    direct_distributed = Column(DECIMAL(20, 8), nullable=False, default=0, comment="直推已发放")
    diff_distributed = Column(DECIMAL(20, 8), nullable=False, default=0, comment="级差已发放")
    peer_distributed = Column(DECIMAL(20, 8), nullable=False, default=0, comment="平级已发放")
    network_undistributed = Column(DECIMAL(20, 8), nullable=False, default=0, comment="网体未分配(条件不满足)")
    status = Column(Integer, nullable=False, default=1)  # 1待结算 2已结算 3分发失败待重试
    retry_count = Column(Integer, nullable=False, default=0, comment="重试次数")
    last_error = Column(String(500), nullable=True, comment="最后一次失败原因")
    settle_batch = Column(String(50), nullable=True)
    settled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class UserReward(Base):
    """
    奖励流水表（fact_user_reward）
    """
    __tablename__ = "fact_user_reward"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    source_user_id = Column(Integer, nullable=True)
    profit_pool_id = Column(BigInteger, nullable=True)
    reward_type = Column(String(20), nullable=False)  # direct/level_diff/peer/tech_team
    amount = Column(DECIMAL(20, 8), nullable=False)
    rate = Column(DECIMAL(10, 4), nullable=True)
    from_level = Column(Integer, nullable=True)
    to_level = Column(Integer, nullable=True)
    settle_batch = Column(String(50), nullable=True)
    remark = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class RewardLog(Base):
    """
    奖励余额流水表（fact_reward_log）
    记录所有 reward_usdt 变动：奖励发放(+)、提现冻结(-)、提现拒绝退回(+) 等。
    """
    __tablename__ = "fact_reward_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    change_type = Column(String(30), nullable=False)  # reward_in / withdraw_freeze / withdraw_reject_return
    ref_type = Column(String(30), nullable=True)       # user_reward / user_withdrawal
    ref_id = Column(BigInteger, nullable=True)          # 关联 fact_user_reward.id 或 fact_user_withdrawal.id
    amount = Column(DECIMAL(20, 8), nullable=False)     # 正=增加, 负=减少
    before_balance = Column(DECIMAL(20, 8), nullable=False, default=0)
    after_balance = Column(DECIMAL(20, 8), nullable=False, default=0)
    remark = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class UserWithdrawal(Base):
    """
    提现记录表（fact_user_withdrawal）
    """
    __tablename__ = "fact_user_withdrawal"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount = Column(DECIMAL(20, 8), nullable=False)
    fee = Column(DECIMAL(20, 8), nullable=False)
    actual_amount = Column(DECIMAL(20, 8), nullable=False)
    wallet_address = Column(String(128), nullable=False)
    wallet_network = Column(String(20), nullable=False, default="TRC20")
    status = Column(Integer, nullable=False, default=0)  # 0待审核 1已通过 2已拒绝 3已完成
    tx_hash = Column(String(128), nullable=True)
    reject_reason = Column(String(255), nullable=True)
    audit_by = Column(Integer, nullable=True)
    audit_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
