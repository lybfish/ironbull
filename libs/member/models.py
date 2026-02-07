"""
Member Models - 会员、交易所账户、策略绑定、策略目录
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.mysql import DECIMAL
from libs.core.database import Base


class Strategy(Base):
    """
    策略目录表（dim_strategy）

    每行 = 一个策略定义，包含该策略的所有运行参数。
    信号监控启动时从此表读取 status=1 的策略并循环检测。
    """
    __tablename__ = "dim_strategy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # ---- 交易标的 ----
    symbol = Column(String(32), nullable=False, comment="主交易对（向后兼容）")
    symbols = Column(JSON, nullable=True, comment="监控交易对列表 JSON 数组，如 [\"BTCUSDT\",\"ETHUSDT\"]；为空则用 symbol 单值")
    timeframe = Column(String(8), nullable=True, comment="K 线周期，如 1h / 4h / 1d")

    # ---- 交易所 & 市场 ----
    exchange = Column(String(32), nullable=True, default=None, comment="指定交易所（binance/okx/gateio），空=跟随账户")
    market_type = Column(String(16), nullable=False, default="future", comment="市场类型：spot / future")

    # ---- 仓位 & 风控 ----
    min_capital = Column(DECIMAL(20, 2), nullable=False, default=200)
    risk_level = Column(Integer, nullable=False, default=1)
    amount_usdt = Column(DECIMAL(20, 2), nullable=False, default=100, comment="单仓下单金额(USDT)，执行时按此金额下单")
    leverage = Column(Integer, nullable=False, default=20, comment="杠杆倍数，下单前自动设置到交易所")

    # ---- 信号过滤 ----
    min_confidence = Column(Integer, nullable=False, default=50, comment="最低置信度（0-100），低于此值不执行")
    cooldown_minutes = Column(Integer, nullable=False, default=60, comment="同一交易对信号冷却时间（分钟）")

    # ---- 通用 ----
    status = Column(Integer, nullable=False, default=1)
    config = Column(JSON, nullable=True, comment="策略算法参数（如 atr_mult_sl、atr_mult_tp 等）")
    # ---- 对用户可见（商户/C 端只看到 show_to_user=1，展示用 user_display_name / user_description） ----
    show_to_user = Column(Integer, nullable=False, default=0, comment="是否对用户/商户展示 0否 1是")
    user_display_name = Column(String(100), nullable=True, comment="对用户展示的名称，空则用 name")
    user_description = Column(Text, nullable=True, comment="对用户展示的描述，空则用 description")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # ---- 便捷方法 ----
    def get_symbols(self):
        """返回策略监控的交易对列表"""
        if self.symbols and isinstance(self.symbols, list) and len(self.symbols) > 0:
            return self.symbols
        if self.symbol:
            return [self.symbol]
        return []

    def get_config(self):
        """返回策略算法参数 dict，保证不为 None"""
        return self.config if isinstance(self.config, dict) else {}


class LevelConfig(Base):
    """
    等级配置表（dim_level_config）S0-S7
    """
    __tablename__ = "dim_level_config"

    level = Column(Integer, primary_key=True)  # 0-7
    level_name = Column(String(10), nullable=False)
    min_team_perf = Column(DECIMAL(20, 2), nullable=False)
    diff_rate = Column(DECIMAL(10, 4), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


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
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


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
    execution_node_id = Column(Integer, nullable=True, default=None, index=True, comment="执行节点ID，空/0=未绑定不执行，>0=绑定到对应节点")
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_error = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class TenantStrategy(Base):
    """
    租户策略实例表（dim_tenant_strategy）
    每个租户下「对用户展示」的策略列表，关联主策略；杠杆、单笔金额等可在此覆盖，空则用主策略。
    用户侧看到的策略 = 该租户的实例列表（join dim_strategy 取主策略信息）。
    """
    __tablename__ = "dim_tenant_strategy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("dim_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(Integer, ForeignKey("dim_strategy.id", ondelete="CASCADE"), nullable=False, index=True)
    display_name = Column(String(100), nullable=True, comment="租户侧展示名称，空则用主策略 name")
    display_description = Column(Text, nullable=True, comment="租户侧展示描述，空则用主策略 description")
    leverage = Column(Integer, nullable=True, comment="杠杆倍数覆盖，空则用主策略")
    amount_usdt = Column(DECIMAL(20, 2), nullable=True, comment="单笔金额(USDT)覆盖，空则用主策略")
    min_capital = Column(DECIMAL(20, 2), nullable=True, comment="最低资金覆盖，空则用主策略")
    status = Column(Integer, nullable=False, default=1, comment="1=对租户用户展示 0=不展示")
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class StrategyBinding(Base):
    """
    用户策略订阅表（dim_strategy_binding）

    用户绑定策略时设置三项：
    - capital: 本金 / 最大仓位（USDT）
    - leverage: 杠杆倍数（默认20）
    - risk_mode: 风险档位 1=稳健(1%) 2=均衡(1.5%) 3=激进(2%)

    下单金额计算：
      risk_pct = {1: 0.01, 2: 0.015, 3: 0.02}[risk_mode]
      margin = capital × risk_pct
      amount_usdt = margin × leverage
    """
    __tablename__ = "dim_strategy_binding"

    # 风险模式 → risk_pct 映射
    RISK_MODE_MAP = {1: 0.01, 2: 0.015, 3: 0.02}
    RISK_MODE_LABELS = {1: "稳健", 2: "均衡", 3: "激进"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("dim_user.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("fact_exchange_account.id", ondelete="CASCADE"), nullable=False)
    strategy_code = Column(String(64), nullable=False, index=True)
    mode = Column(Integer, nullable=False, default=2)  # 1=单次 2=循环
    ratio = Column(Integer, nullable=False, default=100)

    # ── 用户自定义仓位参数 ──
    capital = Column(DECIMAL(20, 2), nullable=True, comment="本金/最大仓位(USDT)")
    leverage = Column(Integer, nullable=True, default=20, comment="杠杆倍数")
    risk_mode = Column(Integer, nullable=True, default=1, comment="风险档位: 1=稳健(1%) 2=均衡(1.5%) 3=激进(2%)")

    total_profit = Column(DECIMAL(20, 8), nullable=False, default=0)
    total_trades = Column(Integer, nullable=False, default=0)
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    @property
    def risk_pct(self) -> float:
        """当前风险比例"""
        return self.RISK_MODE_MAP.get(self.risk_mode or 1, 0.01)

    @property
    def amount_usdt(self) -> float:
        """计算下单金额: capital × risk_pct × leverage"""
        cap = float(self.capital or 0)
        lev = int(self.leverage or 20)
        if cap <= 0:
            return 0
        return round(cap * self.risk_pct * lev, 2)
