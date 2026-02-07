"""
MarketInfoService - 统一市场信息服务

解决的问题：
- 交易对格式不一致（BTCUSDT / BTC/USDT / BTC/USDT:USDT / BTC-USDT / BTC_USDT）
- 合约张数转换散落各处（Gate 1张BTC=0.0001, OKX 1张BTC=0.01, Binance=1）
- 精度、最小下单量、最小金额等各交易所不同
- 没有统一的数据源

设计思路：
1. dim_market_info 表存所有交易所的市场信息（定期从 ccxt 刷新）
2. MarketInfoService 提供统一的查询/转换接口
3. 所有下单、同步、展示都通过此服务获取市场参数

用法：
    from libs.exchange.market_service import MarketInfoService, get_market_service

    svc = get_market_service(session)
    info = svc.get("BTC/USDT", "gate", "swap")
    # info.contract_size → 0.0001
    # info.amount_precision → 0
    # info.price_precision → 2
    # info.min_quantity → 1
    # info.min_cost → 5.0

    # 张数 → 币数量
    coins = svc.contracts_to_coins(21, "BTC/USDT", "gate", "swap")
    # → 0.0021

    # 币数量 → 张数
    contracts = svc.coins_to_contracts(0.0021, "BTC/USDT", "gate", "swap")
    # → 21

    # USDT → 下单数量（自动处理合约/精度/最小值）
    qty = svc.usdt_to_quantity(100, "BTC/USDT", "gate", "swap", price=70000, leverage=20)
    # → 28 (张)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Session

from libs.core.database import Base
from libs.core.logger import get_logger
from libs.exchange.utils import normalize_symbol, to_canonical_symbol, symbol_for_ccxt_futures

log = get_logger("market-service")


# ═══════════════════════════════════════════════════════════════
# 数据库模型
# ═══════════════════════════════════════════════════════════════

class MarketInfo(Base):
    """
    市场信息表 - 统一存储各交易所的交易对参数

    定期从 ccxt load_markets() 刷新，作为整个系统的市场参数唯一数据源。
    """
    __tablename__ = "dim_market_info"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 标识 ──
    canonical_symbol = Column(String(32), nullable=False, comment="规范交易对 (BTC/USDT)")
    exchange = Column(String(32), nullable=False, comment="交易所 (binance/gate/okx)")
    market_type = Column(String(16), nullable=False, default="swap", comment="市场类型 (spot/swap/future)")

    # ── ccxt 符号 ──
    ccxt_symbol = Column(String(64), nullable=True, comment="ccxt 格式 (BTC/USDT:USDT)")
    exchange_symbol = Column(String(64), nullable=True, comment="交易所原生格式 (BTCUSDT / BTC_USDT)")

    # ── 合约 ──
    contract_size = Column(DECIMAL(20, 10), nullable=True, default=1, comment="合约面值 (Gate BTC=0.0001)")
    contract_currency = Column(String(16), nullable=True, comment="合约面值币种 (BTC)")

    # ── 精度 ──
    price_precision = Column(Integer, nullable=True, comment="价格精度位数")
    amount_precision = Column(Integer, nullable=True, comment="数量精度位数")
    cost_precision = Column(Integer, nullable=True, comment="金额精度位数")

    # ── 下单限制 ──
    min_quantity = Column(DECIMAL(20, 10), nullable=True, comment="最小下单数量")
    max_quantity = Column(DECIMAL(20, 10), nullable=True, comment="最大下单数量")
    min_cost = Column(DECIMAL(20, 8), nullable=True, comment="最小下单金额 (USDT)")
    min_price = Column(DECIMAL(20, 10), nullable=True, comment="最小价格")
    max_price = Column(DECIMAL(20, 2), nullable=True, comment="最大价格")
    tick_size = Column(DECIMAL(20, 10), nullable=True, comment="价格最小变动")
    step_size = Column(DECIMAL(20, 10), nullable=True, comment="数量最小变动")

    # ── 元数据 ──
    base_currency = Column(String(16), nullable=True, comment="基础币种 (BTC)")
    quote_currency = Column(String(16), nullable=True, comment="计价币种 (USDT)")
    settle_currency = Column(String(16), nullable=True, comment="结算币种 (USDT)")
    is_active = Column(Integer, nullable=False, default=1, comment="是否活跃")

    # ── 时间 ──
    synced_at = Column(DateTime, nullable=True, comment="最后同步时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        UniqueConstraint("canonical_symbol", "exchange", "market_type", name="uq_market_key"),
        Index("idx_market_exchange", "exchange"),
        Index("idx_market_symbol", "canonical_symbol"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "canonical_symbol": self.canonical_symbol,
            "exchange": self.exchange,
            "market_type": self.market_type,
            "ccxt_symbol": self.ccxt_symbol,
            "exchange_symbol": self.exchange_symbol,
            "contract_size": float(self.contract_size) if self.contract_size else 1,
            "price_precision": self.price_precision,
            "amount_precision": self.amount_precision,
            "min_quantity": float(self.min_quantity) if self.min_quantity else None,
            "max_quantity": float(self.max_quantity) if self.max_quantity else None,
            "min_cost": float(self.min_cost) if self.min_cost else None,
            "tick_size": float(self.tick_size) if self.tick_size else None,
            "step_size": float(self.step_size) if self.step_size else None,
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "is_active": self.is_active,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }


# ═══════════════════════════════════════════════════════════════
# 统一服务
# ═══════════════════════════════════════════════════════════════

class MarketInfoService:
    """
    统一市场信息服务

    提供：
    - 市场参数查询（合约大小、精度、最小下单量等）
    - 张数 ↔ 币数量转换
    - USDT → 下单数量换算
    - 精度处理
    - symbol 规范化
    """

    def __init__(self, session: Session):
        self.session = session

    # ═══════ 查询 ═══════

    def get(
        self,
        symbol: str,
        exchange: str,
        market_type: str = "swap",
    ) -> Optional[MarketInfo]:
        """查询单个市场信息"""
        canonical = normalize_symbol(symbol)
        ex = _normalize_exchange(exchange)
        return self.session.query(MarketInfo).filter(
            MarketInfo.canonical_symbol == canonical,
            MarketInfo.exchange == ex,
            MarketInfo.market_type == market_type,
            MarketInfo.is_active == 1,
        ).first()

    def get_contract_size(
        self,
        symbol: str,
        exchange: str,
        market_type: str = "swap",
    ) -> float:
        """获取合约面值（不存在则返回 1.0）"""
        info = self.get(symbol, exchange, market_type)
        if info and info.contract_size:
            return float(info.contract_size)
        return 1.0

    def list_by_exchange(
        self,
        exchange: str,
        market_type: str = None,
        symbols: List[str] = None,
    ) -> List[MarketInfo]:
        """查询某个交易所的所有市场信息"""
        ex = _normalize_exchange(exchange)
        q = self.session.query(MarketInfo).filter(
            MarketInfo.exchange == ex,
            MarketInfo.is_active == 1,
        )
        if market_type:
            q = q.filter(MarketInfo.market_type == market_type)
        if symbols:
            canonical_symbols = [normalize_symbol(s) for s in symbols]
            q = q.filter(MarketInfo.canonical_symbol.in_(canonical_symbols))
        return q.all()

    # ═══════ 转换 ═══════

    def contracts_to_coins(
        self,
        contracts: float,
        symbol: str,
        exchange: str,
        market_type: str = "swap",
    ) -> float:
        """
        合约张数 → 币数量

        Gate BTC: 21 张 × 0.0001 = 0.0021 BTC
        Binance BTC: 0.004 × 1 = 0.004 BTC (不变)
        """
        cs = self.get_contract_size(symbol, exchange, market_type)
        if cs > 0 and cs != 1:
            return contracts * cs
        return contracts

    def coins_to_contracts(
        self,
        coins: float,
        symbol: str,
        exchange: str,
        market_type: str = "swap",
    ) -> float:
        """
        币数量 → 合约张数

        Gate BTC: 0.0021 / 0.0001 = 21 张
        """
        cs = self.get_contract_size(symbol, exchange, market_type)
        if cs > 0 and cs != 1:
            return coins / cs
        return coins

    def apply_amount_precision(
        self,
        quantity: float,
        symbol: str,
        exchange: str,
        market_type: str = "swap",
    ) -> float:
        """按交易所精度舍入数量"""
        info = self.get(symbol, exchange, market_type)
        if not info or info.amount_precision is None:
            return quantity
        precision = info.amount_precision
        if precision == 0:
            return float(int(quantity))
        factor = 10 ** precision
        return float(int(quantity * factor)) / factor

    def apply_price_precision(
        self,
        price: float,
        symbol: str,
        exchange: str,
        market_type: str = "swap",
    ) -> float:
        """按交易所精度舍入价格"""
        info = self.get(symbol, exchange, market_type)
        if not info or info.price_precision is None:
            return price
        return round(price, info.price_precision)

    def validate_quantity(
        self,
        quantity: float,
        symbol: str,
        exchange: str,
        market_type: str = "swap",
    ) -> Optional[str]:
        """
        校验下单数量是否符合交易所限制。
        返回 None 表示通过，否则返回错误信息。
        """
        info = self.get(symbol, exchange, market_type)
        if not info:
            return None  # 无数据时不阻止

        if info.min_quantity and quantity < float(info.min_quantity):
            return f"{symbol}@{exchange} 下单量 {quantity} < 最小 {info.min_quantity}"
        if info.max_quantity and float(info.max_quantity) > 0 and quantity > float(info.max_quantity):
            return f"{symbol}@{exchange} 下单量 {quantity} > 最大 {info.max_quantity}"
        return None

    def usdt_to_quantity(
        self,
        amount_usdt: float,
        symbol: str,
        exchange: str,
        market_type: str = "swap",
        price: float = 0,
        leverage: int = 1,
    ) -> float:
        """
        USDT 金额 → 交易所下单数量（自动处理合约张数、精度、限制）

        对合约所（Gate/OKX）返回张数，对 Binance 返回币数量。
        """
        if price <= 0 or amount_usdt <= 0:
            raise ValueError(f"invalid price={price} or amount_usdt={amount_usdt}")

        notional = amount_usdt * leverage if leverage > 1 else amount_usdt
        info = self.get(symbol, exchange, market_type)
        cs = float(info.contract_size) if info and info.contract_size else 1.0

        if cs > 0 and cs != 1:
            # 合约所（Gate/OKX）：按张计
            raw_contracts = notional / (price * cs)
            quantity = int(raw_contracts)  # 向下取整
            if quantity < 1:
                cost_per = price * cs
                raise ValueError(
                    f"{symbol}@{exchange} 金额 {amount_usdt} USDT（杠杆{leverage}x={notional}）"
                    f"不足 1 张（1张={cs}，约 {cost_per:.2f} USDT）"
                )
        else:
            # 现货所 / Binance 合约：以币为单位
            quantity = notional / price
            quantity = self.apply_amount_precision(quantity, symbol, exchange, market_type)

        # 校验
        err = self.validate_quantity(quantity, symbol, exchange, market_type)
        if err:
            raise ValueError(err)

        if quantity <= 0:
            raise ValueError(f"{symbol}@{exchange} 计算后数量为 0")

        return quantity

    # ═══════ Symbol 工具 ═══════

    @staticmethod
    def normalize(symbol: str) -> str:
        """统一 symbol → BTC/USDT"""
        return normalize_symbol(symbol)

    @staticmethod
    def to_ccxt(symbol: str, market_type: str = "swap") -> str:
        """统一 symbol → BTC/USDT:USDT（用于 ccxt 合约 API）"""
        canonical = normalize_symbol(symbol)
        if market_type in ("swap", "future"):
            return symbol_for_ccxt_futures(canonical)
        return canonical

    # ═══════ 同步（从 ccxt 刷新到 DB） ═══════

    def sync_from_ccxt(
        self,
        exchange_id: str,
        market_type: str = "swap",
        symbols: List[str] = None,
    ) -> Dict[str, int]:
        """
        从 ccxt load_markets() 刷新市场信息到 dim_market_info。

        Args:
            exchange_id: ccxt 交易所 ID (binanceusdm / gateio / okx)
            market_type: 目标市场类型 (swap / spot)
            symbols: 仅同步指定交易对（canonical 格式），None 同步全部
        Returns:
            {"total": N, "updated": M, "new": K}
        """
        import ccxt

        exchange_name = _normalize_exchange(exchange_id)

        # ccxt 映射
        ccxt_class = {
            "binance": ccxt.binanceusdm if market_type in ("swap", "future") else ccxt.binance,
            "gate": ccxt.gateio,
            "okx": ccxt.okx,
        }.get(exchange_name)

        if not ccxt_class:
            log.warning("unsupported exchange for market sync", exchange=exchange_name)
            return {"total": 0, "updated": 0, "new": 0}

        options = {}
        if exchange_name == "okx":
            options["defaultType"] = "swap" if market_type in ("swap", "future") else "spot"
        elif exchange_name == "gate":
            options["defaultType"] = "swap" if market_type in ("swap", "future") else "spot"

        ex = ccxt_class({"enableRateLimit": True, "options": options})
        ex.load_markets()

        total = 0
        updated = 0
        new = 0
        now = datetime.now()

        for sym, m in ex.markets.items():
            # 只处理目标市场类型
            m_type = m.get("type", "")
            if market_type in ("swap", "future") and m_type != "swap":
                continue
            if market_type == "spot" and m_type != "spot":
                continue

            # 只处理 USDT 结算
            settle = m.get("settle") or m.get("quote")
            if market_type in ("swap", "future") and settle != "USDT":
                continue

            canonical = to_canonical_symbol(sym, market_type)
            if not canonical or "/" not in canonical:
                continue

            # 如果指定了 symbols，过滤
            if symbols and canonical not in symbols:
                continue

            # 提取信息
            limits = m.get("limits", {})
            amount_limits = limits.get("amount", {})
            cost_limits = limits.get("cost", {})
            price_limits = limits.get("price", {})
            precision = m.get("precision", {})

            cs = float(m.get("contractSize") or 1)
            base = m.get("base", "")
            quote = m.get("quote", "USDT")

            # 精度：ccxt 返回的 precision 可能是小数位数（int）或最小步长（float）
            amount_prec = precision.get("amount")
            price_prec = precision.get("price")
            # 如果是 float 步长格式，转为小数位数
            if isinstance(amount_prec, float) and amount_prec < 1:
                amount_prec = len(str(amount_prec).rstrip("0").split(".")[-1])
            if isinstance(price_prec, float) and price_prec < 1:
                price_prec = len(str(price_prec).rstrip("0").split(".")[-1])

            # 交易所原生 symbol
            ex_sym = m.get("id", "")

            # Upsert
            existing = self.session.query(MarketInfo).filter(
                MarketInfo.canonical_symbol == canonical,
                MarketInfo.exchange == exchange_name,
                MarketInfo.market_type == market_type,
            ).first()

            if existing:
                existing.ccxt_symbol = sym
                existing.exchange_symbol = ex_sym
                existing.contract_size = Decimal(str(cs))
                existing.contract_currency = base if cs != 1 else None
                existing.price_precision = int(price_prec) if price_prec is not None else None
                existing.amount_precision = int(amount_prec) if amount_prec is not None else None
                existing.min_quantity = Decimal(str(amount_limits.get("min") or 0)) if amount_limits.get("min") else None
                existing.max_quantity = Decimal(str(amount_limits.get("max") or 0)) if amount_limits.get("max") else None
                existing.min_cost = Decimal(str(cost_limits.get("min") or 0)) if cost_limits.get("min") else None
                existing.min_price = Decimal(str(price_limits.get("min") or 0)) if price_limits.get("min") else None
                existing.max_price = Decimal(str(price_limits.get("max") or 0)) if price_limits.get("max") else None
                existing.base_currency = base
                existing.quote_currency = quote
                existing.settle_currency = settle
                existing.is_active = 1
                existing.synced_at = now
                updated += 1
            else:
                new_info = MarketInfo(
                    canonical_symbol=canonical,
                    exchange=exchange_name,
                    market_type=market_type,
                    ccxt_symbol=sym,
                    exchange_symbol=ex_sym,
                    contract_size=Decimal(str(cs)),
                    contract_currency=base if cs != 1 else None,
                    price_precision=int(price_prec) if price_prec is not None else None,
                    amount_precision=int(amount_prec) if amount_prec is not None else None,
                    min_quantity=Decimal(str(amount_limits.get("min") or 0)) if amount_limits.get("min") else None,
                    max_quantity=Decimal(str(amount_limits.get("max") or 0)) if amount_limits.get("max") else None,
                    min_cost=Decimal(str(cost_limits.get("min") or 0)) if cost_limits.get("min") else None,
                    min_price=Decimal(str(price_limits.get("min") or 0)) if price_limits.get("min") else None,
                    max_price=Decimal(str(price_limits.get("max") or 0)) if price_limits.get("max") else None,
                    base_currency=base,
                    quote_currency=quote,
                    settle_currency=settle,
                    is_active=1,
                    synced_at=now,
                )
                self.session.add(new_info)
                new += 1
            total += 1

        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            log.error("market info sync commit failed", error=str(e))
            raise

        log.info("market info synced",
                 exchange=exchange_name, market_type=market_type,
                 total=total, updated=updated, new=new)

        return {"total": total, "updated": updated, "new": new}


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def _normalize_exchange(exchange: str) -> str:
    """规范化交易所名称"""
    ex = (exchange or "").lower().strip()
    if ex in ("binanceusdm", "binance"):
        return "binance"
    if ex in ("gateio", "gate"):
        return "gate"
    if ex in ("okex", "okx"):
        return "okx"
    return ex


def get_market_service(session: Session) -> MarketInfoService:
    """快捷获取 MarketInfoService 实例"""
    return MarketInfoService(session)


# ═══════════════════════════════════════════════════════════════
# 独立转换函数（不依赖 DB，用于执行节点等场景）
# ═══════════════════════════════════════════════════════════════

def contracts_to_coins_by_size(contracts: float, contract_size: float) -> float:
    """
    合约张数 → 币数量（纯函数，不查 DB）

    用于执行节点等已知 contractSize 的场景。
    """
    if contract_size > 0 and contract_size != 1:
        return contracts * contract_size
    return contracts


def coins_to_contracts_by_size(coins: float, contract_size: float) -> float:
    """币数量 → 合约张数（纯函数）"""
    if contract_size > 0 and contract_size != 1:
        return coins / contract_size
    return coins
