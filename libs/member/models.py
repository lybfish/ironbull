"""
Member Models - 会员、交易所账户、策略绑定、策略目录
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.mysql import DECIMAL
from libs.core.database import Base


class Strategy(Base):
    """
    策略目录表（dim_strategy）
    """
    __tablename__ = "dim_strategy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    symbol = Column(String(32), nullable=False)
    timeframe = Column(String(8), nullable=True)
    min_capital = Column(DECIMAL(20, 2), nullable=False, default=200)
    risk_level = Column(Integer, nullable=False, default=1)
    status = Column(Integer, nullable=False, default=1)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class LevelConfig(Base):
    """
    等级配置表（dim_level_config）S0-S7
    """
    __tablename__ = "dim_level_config"

    level = Column(Integer, primary_key=True)  # 0-7
    level_name = Column(String(10), nullable=False)
    min_team_perf = Column(DECIMAL(20, 2), nullable=False)
    diff_rate = Column(DECIMAL(10, 4), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class User(Base):
    """
    会员/用户表（dim_user），id 即 user_id
    """
    __tablename__ = "dim_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    email = Column(String(100), nullable=False)
    password_hash = Column(String(128), nullable=True)
    is_root = Column(Integer, nullable=False, default=0)
    invite_code = Column(String(8), nullable=False, unique=True, index=True)
    inviter_id = Column(Integer, ForeignKey("dim_user.id"), nullable=True, index=True)
    inviter_path = Column(String(500), nullable=True)
    point_card_self = Column(DECIMAL(20, 8), nullable=False, default=0)
    point_card_gift = Column(DECIMAL(20, 8), nullable=False, default=0)
    member_level = Column(Integer, nullable=False, default=0)
    is_market_node = Column(Integer, nullable=False, default=0)
    team_performance = Column(DECIMAL(20, 8), nullable=False, default=0)
    reward_usdt = Column(DECIMAL(20, 8), nullable=False, default=0)
    total_reward = Column(DECIMAL(20, 8), nullable=False, default=0)
    withdrawn_reward = Column(DECIMAL(20, 8), nullable=False, default=0)
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExchangeAccount(Base):
    """
    交易所账户表（fact_exchange_account），API 绑定
    """
    __tablename__ = "fact_exchange_account"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("dim_user.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    exchange = Column(String(32), nullable=False)
    account_type = Column(String(16), nullable=False, default="futures")
    api_key = Column(String(255), nullable=False)
    api_secret = Column(String(255), nullable=False)
    passphrase = Column(String(255), nullable=True)
    balance = Column(DECIMAL(20, 8), nullable=False, default=0)
    futures_balance = Column(DECIMAL(20, 8), nullable=False, default=0)
    futures_available = Column(DECIMAL(20, 8), nullable=False, default=0)
    status = Column(Integer, nullable=False, default=1)
    execution_node_id = Column(Integer, nullable=True, default=None, index=True, comment="执行节点ID，空=本机")
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_error = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class StrategyBinding(Base):
    """
    用户策略订阅表（dim_strategy_binding）
    """
    __tablename__ = "dim_strategy_binding"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("dim_user.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("fact_exchange_account.id", ondelete="CASCADE"), nullable=False)
    strategy_code = Column(String(64), nullable=False, index=True)
    mode = Column(Integer, nullable=False, default=2)  # 1=单次 2=循环
    ratio = Column(Integer, nullable=False, default=100)
    total_profit = Column(DECIMAL(20, 8), nullable=False, default=0)
    total_trades = Column(Integer, nullable=False, default=0)
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
