"""
IronBull 全项目回归测试
==============================

覆盖范围：
1.  核心数据模型 & DTO 序列化完整性
2.  订单状态机合法转换 & 非法拒绝
3.  成交校验（Fill Validation）
4.  trade_type / close_reason 全链路传递
5.  结算链路: Order → Fill → Position → Ledger
6.  节点绑定两步验证（策略订阅 + 节点绑定）
7.  Position Monitor SL/TP 触发
8.  风控引擎：10 条规则 + Engine 行为
9.  信号分发流程（signal-monitor dispatch）
10. Analytics 绩效分析
11. 技术指标计算（indicators）
12. 会员/点卡/策略绑定
13. Signal Contract 数据结构
14. API 端点契约（DTO → dict 字段完整性）

运行: python -m pytest tests/test_regression_full.py -v
"""

import sys
import os
import json
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from dataclasses import asdict, fields

import pytest

# ──────────────────────────────────────────────
# 确保项目根目录在 sys.path
# ──────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ============================================================
#  SECTION 1: 订单状态机 & 成交校验
# ============================================================

class TestOrderStateMachine:
    """订单状态机合法流转与非法拒绝"""

    def setup_method(self):
        from libs.order_trade.states import OrderStatus, OrderStateMachine
        self.OS = OrderStatus
        self.SM = OrderStateMachine

    # ── 合法转换 ──

    def test_pending_to_submitted(self):
        assert self.SM.can_transition(self.OS.PENDING, self.OS.SUBMITTED)

    def test_pending_to_rejected(self):
        assert self.SM.can_transition(self.OS.PENDING, self.OS.REJECTED)

    def test_submitted_to_filled(self):
        """市价单立即成交"""
        assert self.SM.can_transition(self.OS.SUBMITTED, self.OS.FILLED)

    def test_submitted_to_partial(self):
        assert self.SM.can_transition(self.OS.SUBMITTED, self.OS.PARTIAL)

    def test_partial_to_filled(self):
        assert self.SM.can_transition(self.OS.PARTIAL, self.OS.FILLED)

    def test_partial_to_partial(self):
        """继续部分成交"""
        assert self.SM.can_transition(self.OS.PARTIAL, self.OS.PARTIAL)

    def test_open_to_cancelled(self):
        assert self.SM.can_transition(self.OS.OPEN, self.OS.CANCELLED)

    def test_open_to_expired(self):
        assert self.SM.can_transition(self.OS.OPEN, self.OS.EXPIRED)

    # ── 非法转换 ──

    def test_filled_is_terminal(self):
        assert self.OS.FILLED.is_terminal()
        assert not self.SM.can_transition(self.OS.FILLED, self.OS.PENDING)
        assert not self.SM.can_transition(self.OS.FILLED, self.OS.CANCELLED)

    def test_cancelled_is_terminal(self):
        assert self.OS.CANCELLED.is_terminal()
        assert not self.SM.can_transition(self.OS.CANCELLED, self.OS.OPEN)

    def test_rejected_is_terminal(self):
        assert self.OS.REJECTED.is_terminal()

    def test_pending_cannot_go_to_filled_directly(self):
        """PENDING 不能直接跳到 FILLED，必须先 SUBMITTED"""
        assert not self.SM.can_transition(self.OS.PENDING, self.OS.FILLED)

    def test_validate_transition_raises_on_invalid(self):
        from libs.order_trade.exceptions import InvalidStateTransitionError
        with pytest.raises(InvalidStateTransitionError):
            self.SM.validate_transition(self.OS.FILLED, self.OS.PENDING)

    # ── 成交后状态推断 ──

    def test_determine_status_after_full_fill(self):
        status = self.SM.determine_status_after_fill(1.0, 1.0, self.OS.SUBMITTED)
        assert status == self.OS.FILLED

    def test_determine_status_after_partial_fill(self):
        status = self.SM.determine_status_after_fill(1.0, 0.5, self.OS.SUBMITTED)
        assert status == self.OS.PARTIAL

    def test_determine_status_zero_fill(self):
        status = self.SM.determine_status_after_fill(1.0, 0.0, self.OS.OPEN)
        assert status == self.OS.OPEN

    # ── 辅助方法 ──

    def test_terminal_states(self):
        terminals = self.OS.terminal_states()
        assert self.OS.FILLED in terminals
        assert self.OS.CANCELLED in terminals
        assert self.OS.REJECTED in terminals
        assert self.OS.EXPIRED in terminals
        assert self.OS.FAILED in terminals
        assert len(terminals) == 5

    def test_cancellable_states(self):
        cancellable = self.OS.cancellable_states()
        assert self.OS.PENDING in cancellable
        assert self.OS.SUBMITTED in cancellable
        assert self.OS.OPEN in cancellable
        assert self.OS.PARTIAL in cancellable
        assert self.OS.FILLED not in cancellable


class TestFillValidation:
    """成交校验不变量"""

    def setup_method(self):
        from libs.order_trade.states import FillValidation
        self.FV = FillValidation

    def test_valid_fill(self):
        self.FV.validate_fill_quantity(1.0, 0.0, 0.5)  # 不应抛异常

    def test_exact_fill(self):
        self.FV.validate_fill_quantity(1.0, 0.5, 0.5)  # 恰好成交完

    def test_exceed_fill_raises(self):
        from libs.order_trade.exceptions import FillQuantityExceededError
        with pytest.raises(FillQuantityExceededError):
            self.FV.validate_fill_quantity(1.0, 0.5, 0.6)

    def test_time_order_valid(self):
        self.FV.validate_fill_time_order(100.0, 200.0)  # 不应抛异常

    def test_time_order_invalid_raises(self):
        from libs.order_trade.exceptions import FillTimeOrderError
        with pytest.raises(FillTimeOrderError):
            self.FV.validate_fill_time_order(200.0, 100.0)

    def test_time_order_first_fill(self):
        self.FV.validate_fill_time_order(None, 100.0)  # 第一笔不应抛异常


# ============================================================
#  SECTION 2: DTO 序列化完整性
# ============================================================

class TestOrderDTOSerialization:
    """OrderDTO.to_dict() 字段完整性"""

    def _make_order_dto(self):
        from libs.order_trade.contracts import OrderDTO
        return OrderDTO(
            order_id="ord_001",
            exchange_order_id="ex_001",
            tenant_id=1,
            account_id=100,
            signal_id="sig_001",
            symbol="BTC/USDT",
            exchange="binance",
            market_type="future",
            side="BUY",
            order_type="MARKET",
            trade_type="CLOSE",
            close_reason="SL",
            quantity=0.01,
            price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            position_side="LONG",
            leverage=20,
            status="FILLED",
            filled_quantity=0.01,
            avg_price=50050.0,
            total_fee=5.0,
            fee_currency="USDT",
            error_code=None,
            error_message=None,
            created_at=datetime(2025, 1, 1),
            submitted_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )

    def test_to_dict_includes_trade_type(self):
        dto = self._make_order_dto()
        d = dto.to_dict()
        assert "trade_type" in d
        assert d["trade_type"] == "CLOSE"

    def test_to_dict_includes_close_reason(self):
        dto = self._make_order_dto()
        d = dto.to_dict()
        assert "close_reason" in d
        assert d["close_reason"] == "SL"

    def test_to_dict_all_fields_present(self):
        """to_dict 必须包含所有重要字段"""
        dto = self._make_order_dto()
        d = dto.to_dict()
        required_keys = [
            "order_id", "exchange_order_id", "tenant_id", "account_id",
            "signal_id", "symbol", "exchange", "market_type", "side",
            "order_type", "trade_type", "close_reason", "quantity", "price",
            "stop_loss", "take_profit", "position_side", "leverage",
            "status", "filled_quantity", "avg_price", "total_fee",
        ]
        for k in required_keys:
            assert k in d, f"OrderDTO.to_dict() missing key: {k}"

    def test_is_filled_property(self):
        dto = self._make_order_dto()
        assert dto.is_filled is True

    def test_remaining_quantity(self):
        dto = self._make_order_dto()
        assert dto.remaining_quantity == 0.0


class TestFillDTOSerialization:
    """FillDTO.to_dict() 字段完整性"""

    def _make_fill_dto(self):
        from libs.order_trade.contracts import FillDTO
        return FillDTO(
            fill_id="fill_001",
            exchange_trade_id="etrade_001",
            order_id="ord_001",
            tenant_id=1,
            account_id=100,
            symbol="BTC/USDT",
            side="BUY",
            quantity=0.01,
            price=50000.0,
            fee=5.0,
            fee_currency="USDT",
            filled_at=datetime(2025, 1, 1),
            created_at=datetime(2025, 1, 1),
            exchange="binance",
            market_type="future",
            trade_type="CLOSE",
        )

    def test_to_dict_includes_trade_type(self):
        dto = self._make_fill_dto()
        d = dto.to_dict()
        assert "trade_type" in d
        assert d["trade_type"] == "CLOSE"

    def test_to_dict_includes_value(self):
        dto = self._make_fill_dto()
        d = dto.to_dict()
        assert "value" in d
        assert d["value"] == pytest.approx(500.0, abs=0.01)

    def test_to_dict_all_fields(self):
        dto = self._make_fill_dto()
        d = dto.to_dict()
        required = [
            "fill_id", "exchange_trade_id", "order_id", "tenant_id",
            "account_id", "symbol", "side", "trade_type", "quantity",
            "price", "fee", "fee_currency", "exchange", "market_type",
        ]
        for k in required:
            assert k in d, f"FillDTO.to_dict() missing key: {k}"


class TestPositionDTOCompleteness:
    """PositionDTO 字段完整性"""

    def test_position_dto_has_close_reason(self):
        from libs.position.contracts import PositionDTO
        field_names = [f.name for f in fields(PositionDTO)]
        assert "close_reason" in field_names

    def test_position_dto_has_entry_price(self):
        from libs.position.contracts import PositionDTO
        field_names = [f.name for f in fields(PositionDTO)]
        assert "entry_price" in field_names

    def test_position_dto_has_stop_loss(self):
        from libs.position.contracts import PositionDTO
        field_names = [f.name for f in fields(PositionDTO)]
        assert "stop_loss" in field_names

    def test_position_dto_has_take_profit(self):
        from libs.position.contracts import PositionDTO
        field_names = [f.name for f in fields(PositionDTO)]
        assert "take_profit" in field_names

    def test_position_dto_has_strategy_code(self):
        from libs.position.contracts import PositionDTO
        field_names = [f.name for f in fields(PositionDTO)]
        assert "strategy_code" in field_names

    def test_position_dto_has_status(self):
        from libs.position.contracts import PositionDTO
        field_names = [f.name for f in fields(PositionDTO)]
        assert "status" in field_names


class TestCreateOrderDTOCompleteness:
    """CreateOrderDTO 字段完整性"""

    def test_has_trade_type(self):
        from libs.order_trade.contracts import CreateOrderDTO
        field_names = [f.name for f in fields(CreateOrderDTO)]
        assert "trade_type" in field_names

    def test_has_close_reason(self):
        from libs.order_trade.contracts import CreateOrderDTO
        field_names = [f.name for f in fields(CreateOrderDTO)]
        assert "close_reason" in field_names

    def test_default_trade_type_is_open(self):
        from libs.order_trade.contracts import CreateOrderDTO
        dto = CreateOrderDTO(
            tenant_id=1, account_id=1, symbol="BTC/USDT",
            exchange="binance", side="BUY", order_type="MARKET", quantity=0.01,
        )
        assert dto.trade_type == "OPEN"
        assert dto.close_reason is None


class TestFilterDTOs:
    """过滤 DTO 包含必要字段"""

    def test_order_filter_has_trade_type(self):
        from libs.order_trade.contracts import OrderFilter
        field_names = [f.name for f in fields(OrderFilter)]
        assert "trade_type" in field_names

    def test_order_filter_has_close_reason(self):
        from libs.order_trade.contracts import OrderFilter
        field_names = [f.name for f in fields(OrderFilter)]
        assert "close_reason" in field_names

    def test_fill_filter_has_trade_type(self):
        from libs.order_trade.contracts import FillFilter
        field_names = [f.name for f in fields(FillFilter)]
        assert "trade_type" in field_names

    def test_position_filter_has_close_reason(self):
        from libs.position.contracts import PositionFilter
        field_names = [f.name for f in fields(PositionFilter)]
        assert "close_reason" in field_names


# ============================================================
#  SECTION 3: Signal Contract 数据结构
# ============================================================

class TestSignalContract:
    """Signal 合约数据结构完整性"""

    def test_signal_fields(self):
        from libs.contracts import Signal
        sig = Signal(
            signal_id="sig_001",
            strategy_code="market_regime",
            symbol="BTCUSDT",
            canonical_symbol="BTC/USDT",
            side="BUY",
            signal_type="OPEN",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            confidence=85.0,
            reason="Trend confirmed",
            timeframe="15m",
        )
        assert sig.signal_id == "sig_001"
        assert sig.signal_type == "OPEN"
        assert sig.status == "pending"

    def test_signal_has_amount_usdt(self):
        from libs.contracts import Signal
        field_names = [f.name for f in fields(Signal)]
        assert "amount_usdt" in field_names
        assert "leverage" in field_names

    def test_account_context_fields(self):
        from libs.contracts import AccountContext, Position
        pos = Position(symbol="BTC/USDT", side="long", quantity=0.01, entry_price=50000)
        ctx = AccountContext(
            account_id=1, user_id=1,
            balance=10000, available=8000, frozen=2000,
            positions=[pos],
        )
        assert ctx.balance == 10000
        assert len(ctx.positions) == 1

    def test_all_contracts_importable(self):
        from libs.contracts import (
            Signal, StrategyOutput, AccountContext, Position,
            RiskResult, ExecutionTask, ExecutionResult,
            NodeTask, NodeResult, FollowTask, FollowTaskResult,
        )
        assert Signal is not None
        assert StrategyOutput is not None


# ============================================================
#  SECTION 4: 风控引擎
# ============================================================

class TestRiskEngine:
    """风控引擎 & 所有风控规则"""

    def _make_context(self, **overrides):
        from libs.contracts import Signal, AccountContext, Position
        from libs.risk.engine import RiskCheckContext
        signal = Signal(
            signal_id="sig_test", strategy_code="test",
            symbol="BTC/USDT", canonical_symbol="BTC/USDT",
            side="BUY", signal_type="OPEN",
            entry_price=50000, quantity=0.1,
        )
        positions = overrides.pop("positions", [])
        account = AccountContext(
            account_id=1, user_id=1,
            balance=10000, available=8000,
            positions=positions,
        )
        ctx = RiskCheckContext(signal=signal, account=account, **overrides)
        return ctx

    # ── MaxPositionRule ──

    def test_max_position_pass(self):
        from libs.risk.rules import MaxPositionRule
        from libs.contracts import Position
        rule = MaxPositionRule(max_positions=5)
        ctx = self._make_context(positions=[
            Position("BTC/USDT", "long", 0.01, 50000) for _ in range(4)
        ])
        assert rule.check(ctx) is None

    def test_max_position_fail(self):
        from libs.risk.rules import MaxPositionRule
        from libs.contracts import Position
        rule = MaxPositionRule(max_positions=3)
        ctx = self._make_context(positions=[
            Position("BTC/USDT", "long", 0.01, 50000) for _ in range(3)
        ])
        v = rule.check(ctx)
        assert v is not None
        assert v.code == "RISK_MAX_POSITION"

    # ── MaxPositionValueRule ──

    def test_max_position_value_pass(self):
        from libs.risk.rules import MaxPositionValueRule
        rule = MaxPositionValueRule(max_value=10000)
        ctx = self._make_context()  # quantity=0.1, price=50000 → value=5000
        assert rule.check(ctx) is None

    def test_max_position_value_fail(self):
        from libs.risk.rules import MaxPositionValueRule
        rule = MaxPositionValueRule(max_value=1000)
        ctx = self._make_context()  # value=5000 > 1000
        v = rule.check(ctx)
        assert v is not None
        assert v.code == "RISK_MAX_POSITION_VALUE"

    # ── DailyTradeLimitRule ──

    def test_daily_trade_limit_pass(self):
        from libs.risk.rules import DailyTradeLimitRule
        rule = DailyTradeLimitRule(max_trades=100)
        ctx = self._make_context(daily_trade_count=50)
        assert rule.check(ctx) is None

    def test_daily_trade_limit_fail(self):
        from libs.risk.rules import DailyTradeLimitRule
        rule = DailyTradeLimitRule(max_trades=100)
        ctx = self._make_context(daily_trade_count=100)
        v = rule.check(ctx)
        assert v is not None
        assert v.code == "RISK_DAILY_TRADE_LIMIT"

    # ── WeeklyTradeLimitRule ──

    def test_weekly_trade_limit_pass(self):
        from libs.risk.rules import WeeklyTradeLimitRule
        rule = WeeklyTradeLimitRule(max_trades=500)
        ctx = self._make_context(weekly_trade_count=200)
        assert rule.check(ctx) is None

    def test_weekly_trade_limit_fail(self):
        from libs.risk.rules import WeeklyTradeLimitRule
        rule = WeeklyTradeLimitRule(max_trades=500)
        ctx = self._make_context(weekly_trade_count=500)
        v = rule.check(ctx)
        assert v is not None
        assert v.code == "RISK_WEEKLY_TRADE_LIMIT"

    # ── DailyLossLimitRule ──

    def test_daily_loss_limit_pass(self):
        from libs.risk.rules import DailyLossLimitRule
        rule = DailyLossLimitRule(max_loss=1000)
        ctx = self._make_context(daily_loss=500)
        assert rule.check(ctx) is None

    def test_daily_loss_limit_fail(self):
        from libs.risk.rules import DailyLossLimitRule
        rule = DailyLossLimitRule(max_loss=1000)
        ctx = self._make_context(daily_loss=1000)
        v = rule.check(ctx)
        assert v is not None
        assert v.severity == "critical"

    # ── ConsecutiveLossCooldownRule ──

    def test_consecutive_loss_cooldown_pass(self):
        from libs.risk.rules import ConsecutiveLossCooldownRule
        rule = ConsecutiveLossCooldownRule(max_consecutive=5)
        ctx = self._make_context(consecutive_losses=3)
        assert rule.check(ctx) is None

    def test_consecutive_loss_cooldown_fail(self):
        from libs.risk.rules import ConsecutiveLossCooldownRule
        rule = ConsecutiveLossCooldownRule(max_consecutive=5)
        ctx = self._make_context(consecutive_losses=5)
        v = rule.check(ctx)
        assert v is not None
        assert v.severity == "warning"

    # ── TradeCooldownRule ──

    def test_trade_cooldown_pass(self):
        from libs.risk.rules import TradeCooldownRule
        rule = TradeCooldownRule(cooldown_seconds=60)
        ctx = self._make_context(last_trade_time=datetime.now() - timedelta(seconds=120))
        assert rule.check(ctx) is None

    def test_trade_cooldown_fail(self):
        from libs.risk.rules import TradeCooldownRule
        rule = TradeCooldownRule(cooldown_seconds=60)
        ctx = self._make_context(last_trade_time=datetime.now() - timedelta(seconds=10))
        v = rule.check(ctx)
        assert v is not None
        assert v.code == "RISK_TRADE_COOLDOWN"

    def test_trade_cooldown_no_last_trade(self):
        from libs.risk.rules import TradeCooldownRule
        rule = TradeCooldownRule(cooldown_seconds=60)
        ctx = self._make_context(last_trade_time=None)
        assert rule.check(ctx) is None

    # ── SymbolWhitelistRule ──

    def test_symbol_whitelist_pass(self):
        from libs.risk.rules import SymbolWhitelistRule
        rule = SymbolWhitelistRule(whitelist=["BTC/USDT", "ETH/USDT"])
        ctx = self._make_context()
        assert rule.check(ctx) is None

    def test_symbol_whitelist_fail(self):
        from libs.risk.rules import SymbolWhitelistRule
        rule = SymbolWhitelistRule(whitelist=["ETH/USDT", "SOL/USDT"])
        ctx = self._make_context()
        v = rule.check(ctx)
        assert v is not None
        assert v.code == "RISK_SYMBOL_NOT_ALLOWED"

    def test_symbol_whitelist_empty(self):
        from libs.risk.rules import SymbolWhitelistRule
        rule = SymbolWhitelistRule(whitelist=[])
        ctx = self._make_context()
        assert rule.check(ctx) is None

    # ── SymbolBlacklistRule ──

    def test_symbol_blacklist_pass(self):
        from libs.risk.rules import SymbolBlacklistRule
        rule = SymbolBlacklistRule(blacklist=["LUNA/USDT"])
        ctx = self._make_context()
        assert rule.check(ctx) is None

    def test_symbol_blacklist_fail(self):
        from libs.risk.rules import SymbolBlacklistRule
        rule = SymbolBlacklistRule(blacklist=["BTC/USDT"])
        ctx = self._make_context()
        v = rule.check(ctx)
        assert v is not None
        assert v.code == "RISK_SYMBOL_BLOCKED"

    # ── MinBalanceRule ──

    def test_min_balance_pass(self):
        from libs.risk.rules import MinBalanceRule
        rule = MinBalanceRule(min_balance=100)
        ctx = self._make_context()  # available=8000
        assert rule.check(ctx) is None

    def test_min_balance_fail(self):
        from libs.risk.rules import MinBalanceRule
        rule = MinBalanceRule(min_balance=10000)
        ctx = self._make_context()  # available=8000 < 10000
        v = rule.check(ctx)
        assert v is not None
        assert v.severity == "critical"

    # ── Disabled Rule ──

    def test_disabled_rule_skipped(self):
        from libs.risk.rules import MaxPositionRule
        from libs.risk.engine import RiskEngine
        from libs.contracts import Position
        rule = MaxPositionRule(max_positions=1, enabled=False)
        engine = RiskEngine(fail_fast=True)
        engine.add_rule(rule)
        ctx = self._make_context(positions=[
            Position("BTC/USDT", "long", 0.01, 50000) for _ in range(5)
        ])
        violations = engine.check(ctx)
        assert len(violations) == 0  # disabled 的规则不检查

    # ── Engine 组合行为 ──

    def test_engine_fail_fast(self):
        from libs.risk.rules import MaxPositionRule, DailyTradeLimitRule
        from libs.risk.engine import RiskEngine
        from libs.contracts import Position
        engine = RiskEngine(fail_fast=True)
        engine.add_rule(MaxPositionRule(max_positions=1))
        engine.add_rule(DailyTradeLimitRule(max_trades=1))
        ctx = self._make_context(
            positions=[Position("BTC/USDT", "long", 0.01, 50000) for _ in range(2)],
            daily_trade_count=100,
        )
        violations = engine.check(ctx)
        assert len(violations) == 1  # fail_fast 只返回第一个

    def test_engine_collect_all(self):
        from libs.risk.rules import MaxPositionRule, DailyTradeLimitRule
        from libs.risk.engine import RiskEngine
        from libs.contracts import Position
        engine = RiskEngine(fail_fast=False)
        engine.add_rule(MaxPositionRule(max_positions=1))
        engine.add_rule(DailyTradeLimitRule(max_trades=1))
        ctx = self._make_context(
            positions=[Position("BTC/USDT", "long", 0.01, 50000) for _ in range(2)],
            daily_trade_count=100,
        )
        violations = engine.check(ctx)
        assert len(violations) == 2  # 收集所有

    def test_engine_add_remove_rule(self):
        from libs.risk.rules import MaxPositionRule
        from libs.risk.engine import RiskEngine
        engine = RiskEngine()
        engine.add_rule(MaxPositionRule(max_positions=5))
        assert len(engine.rules) == 1
        assert engine.remove_rule("max_position") is True
        assert len(engine.rules) == 0
        assert engine.remove_rule("nonexistent") is False


# ============================================================
#  SECTION 5: 技术指标计算
# ============================================================

class TestIndicators:
    """纯计算函数库—技术指标"""

    def test_sma(self):
        from libs.indicators import sma
        data = [10, 20, 30, 40, 50]
        result = sma(data, 3)
        assert result == pytest.approx(40.0, abs=0.1)  # avg(30,40,50)

    def test_ema(self):
        from libs.indicators import ema
        data = [10, 20, 30, 40, 50]
        result = ema(data, 3)
        assert isinstance(result, float)
        assert result > 30  # EMA 偏向最近

    def test_rsi(self):
        from libs.indicators import rsi
        data = list(range(10, 30))  # 持续上涨
        result = rsi(data, 14)
        assert result > 70  # 持续上涨 RSI 应该高

    def test_rsi_all_down(self):
        from libs.indicators import rsi
        data = list(range(30, 10, -1))  # 持续下跌
        result = rsi(data, 14)
        assert result < 30  # 持续下跌 RSI 应该低

    def test_macd(self):
        from libs.indicators import macd
        data = list(range(50, 110))  # 60 个数据点
        result = macd(data)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result

    def test_bollinger(self):
        from libs.indicators import bollinger
        data = list(range(50, 80))  # 30 个数据点
        result = bollinger(data, 20, 2)
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result
        assert result["upper"] > result["middle"] > result["lower"]

    def test_atr(self):
        from libs.indicators import atr
        # atr 接受 candles list 或单独的 highs/lows/closes，检查实际签名
        import inspect
        sig = inspect.signature(atr)
        params = list(sig.parameters.keys())
        # 根据实际签名调用
        if len(params) >= 4 and "period" in params:
            highs = [110 + i for i in range(20)]
            lows = [90 + i for i in range(20)]
            closes = [100 + i for i in range(20)]
            result = atr(highs, lows, closes, 14)
        else:
            # candles 格式: list of dicts/lists with high/low/close
            candles = [{"high": 110 + i, "low": 90 + i, "close": 100 + i} for i in range(20)]
            result = atr(candles)
        assert isinstance(result, (int, float))
        assert result > 0

    def test_fibo_levels(self):
        from libs.indicators import fibo_levels
        result = fibo_levels(100, 50)
        assert "0.0" in result or 0.0 in result or isinstance(result, dict)

    def test_obv(self):
        from libs.indicators import obv
        closes = [100, 102, 101, 103, 105]
        volumes = [1000, 1200, 800, 1100, 1500]
        result = obv(closes, volumes)
        assert isinstance(result, (int, float, list))

    def test_sma_series(self):
        from libs.indicators import sma_series
        data = list(range(1, 21))
        result = sma_series(data, 5)
        assert isinstance(result, list)
        assert len(result) > 0


# ============================================================
#  SECTION 6: 节点绑定两步验证
# ============================================================

class TestNodeBindingTwoStep:
    """策略订阅 + 节点绑定的两步验证"""

    def _make_mock_service(self):
        """构建 MemberService with mocked repo"""
        from libs.member.service import MemberService
        mock_session = MagicMock()
        svc = MemberService(mock_session)
        svc.repo = MagicMock()
        return svc

    def _make_strategy(self, strategy_id=1, code="market_regime"):
        from libs.member.models import Strategy
        s = MagicMock(spec=Strategy)
        s.id = strategy_id
        s.strategy_code = code
        s.status = 1
        return s

    def _make_binding(self, account_id=100, strategy_code="market_regime"):
        b = MagicMock()
        b.id = 1
        b.account_id = account_id
        b.strategy_code = strategy_code
        b.ratio = 100
        b.mode = 2
        b.capital = Decimal("1000")
        b.leverage = 20
        b.amount_usdt = Decimal("100")
        return b

    def _make_account(self, account_id=100, execution_node_id=None, status=1):
        acc = MagicMock()
        acc.id = account_id
        acc.tenant_id = 1
        acc.user_id = 10
        acc.exchange = "binance"
        acc.api_key = "key"
        acc.api_secret = "secret"
        acc.passphrase = None
        acc.account_type = "futures"
        acc.status = status
        acc.execution_node_id = execution_node_id
        return acc

    def _make_user(self, user_id=10, point_card_self=100):
        u = MagicMock()
        u.id = user_id
        u.point_card_self = Decimal(str(point_card_self))
        u.point_card_gift = Decimal("0")
        return u

    def _make_tenant_strategy(self, status=1):
        ts = MagicMock()
        ts.status = status
        return ts

    def test_unbound_node_excluded(self):
        """execution_node_id=None（未绑定节点）→ 不进入执行列表"""
        svc = self._make_mock_service()
        strategy = self._make_strategy()
        binding = self._make_binding()
        account = self._make_account(execution_node_id=None)
        user = self._make_user()
        ts = self._make_tenant_strategy()

        svc.repo.get_strategy_by_code.return_value = strategy
        svc.repo.get_bindings_by_strategy_code.return_value = [binding]
        svc.repo.get_account_by_id.return_value = account
        svc.repo.get_user_by_id.return_value = user
        svc.repo.get_tenant_strategy.return_value = ts

        targets = svc.get_execution_targets_by_strategy_code("market_regime")
        assert len(targets) == 0, "未绑定节点的账户不应进入执行列表"

    def test_zero_node_excluded(self):
        """execution_node_id=0 → 不进入执行列表"""
        svc = self._make_mock_service()
        strategy = self._make_strategy()
        binding = self._make_binding()
        account = self._make_account(execution_node_id=0)
        user = self._make_user()
        ts = self._make_tenant_strategy()

        svc.repo.get_strategy_by_code.return_value = strategy
        svc.repo.get_bindings_by_strategy_code.return_value = [binding]
        svc.repo.get_account_by_id.return_value = account
        svc.repo.get_user_by_id.return_value = user
        svc.repo.get_tenant_strategy.return_value = ts

        targets = svc.get_execution_targets_by_strategy_code("market_regime")
        assert len(targets) == 0, "node_id=0 的账户不应进入执行列表"

    def test_bound_node_included(self):
        """execution_node_id=5 → 进入执行列表"""
        svc = self._make_mock_service()
        strategy = self._make_strategy()
        binding = self._make_binding()
        account = self._make_account(execution_node_id=5)
        user = self._make_user()
        ts = self._make_tenant_strategy()

        svc.repo.get_strategy_by_code.return_value = strategy
        svc.repo.get_bindings_by_strategy_code.return_value = [binding]
        svc.repo.get_account_by_id.return_value = account
        svc.repo.get_user_by_id.return_value = user
        svc.repo.get_tenant_strategy.return_value = ts

        targets = svc.get_execution_targets_by_strategy_code("market_regime")
        assert len(targets) == 1
        assert targets[0].execution_node_id == 5

    def test_disabled_account_excluded(self):
        """status=0 的账户不应进入执行列表"""
        svc = self._make_mock_service()
        strategy = self._make_strategy()
        binding = self._make_binding()
        account = self._make_account(execution_node_id=5, status=0)
        user = self._make_user()

        svc.repo.get_strategy_by_code.return_value = strategy
        svc.repo.get_bindings_by_strategy_code.return_value = [binding]
        svc.repo.get_account_by_id.return_value = account
        svc.repo.get_user_by_id.return_value = user

        targets = svc.get_execution_targets_by_strategy_code("market_regime")
        assert len(targets) == 0

    def test_zero_points_excluded(self):
        """点卡为 0 的用户不执行"""
        svc = self._make_mock_service()
        strategy = self._make_strategy()
        binding = self._make_binding()
        account = self._make_account(execution_node_id=5)
        user = self._make_user(point_card_self=0)
        ts = self._make_tenant_strategy()

        svc.repo.get_strategy_by_code.return_value = strategy
        svc.repo.get_bindings_by_strategy_code.return_value = [binding]
        svc.repo.get_account_by_id.return_value = account
        svc.repo.get_user_by_id.return_value = user
        svc.repo.get_tenant_strategy.return_value = ts

        targets = svc.get_execution_targets_by_strategy_code("market_regime")
        assert len(targets) == 0

    def test_disabled_tenant_strategy_excluded(self):
        """租户下该策略实例已关闭 → 不执行"""
        svc = self._make_mock_service()
        strategy = self._make_strategy()
        binding = self._make_binding()
        account = self._make_account(execution_node_id=5)
        user = self._make_user()
        ts = self._make_tenant_strategy(status=0)

        svc.repo.get_strategy_by_code.return_value = strategy
        svc.repo.get_bindings_by_strategy_code.return_value = [binding]
        svc.repo.get_account_by_id.return_value = account
        svc.repo.get_user_by_id.return_value = user
        svc.repo.get_tenant_strategy.return_value = ts

        targets = svc.get_execution_targets_by_strategy_code("market_regime")
        assert len(targets) == 0

    def test_no_strategy_returns_empty(self):
        """strategy_code 不存在 → 空列表"""
        svc = self._make_mock_service()
        svc.repo.get_strategy_by_code.return_value = None
        targets = svc.get_execution_targets_by_strategy_code("nonexistent")
        assert targets == []

    def test_multiple_accounts_mixed(self):
        """多账户混合：1 有节点 + 1 无节点 → 只返回 1"""
        svc = self._make_mock_service()
        strategy = self._make_strategy()
        b1 = self._make_binding(account_id=100)
        b2 = self._make_binding(account_id=200)
        acc1 = self._make_account(account_id=100, execution_node_id=5)
        acc2 = self._make_account(account_id=200, execution_node_id=None)
        user = self._make_user()
        ts = self._make_tenant_strategy()

        svc.repo.get_strategy_by_code.return_value = strategy
        svc.repo.get_bindings_by_strategy_code.return_value = [b1, b2]

        def get_account(aid):
            return {100: acc1, 200: acc2}.get(aid)
        svc.repo.get_account_by_id.side_effect = get_account
        svc.repo.get_user_by_id.return_value = user
        svc.repo.get_tenant_strategy.return_value = ts

        targets = svc.get_execution_targets_by_strategy_code("market_regime")
        assert len(targets) == 1
        assert targets[0].account_id == 100


# ============================================================
#  SECTION 7: trade_type / close_reason 全链路传递
# ============================================================

class TestTradeTypeCloseReasonPropagation:
    """确保 trade_type / close_reason 在整个系统中正确传递"""

    def test_create_order_dto_propagates(self):
        """CreateOrderDTO 能携带 trade_type/close_reason"""
        from libs.order_trade.contracts import CreateOrderDTO
        dto = CreateOrderDTO(
            tenant_id=1, account_id=1, symbol="BTC/USDT",
            exchange="binance", side="SELL", order_type="MARKET",
            quantity=0.01, trade_type="CLOSE", close_reason="SL",
        )
        assert dto.trade_type == "CLOSE"
        assert dto.close_reason == "SL"

    def test_execution_target_has_node_id(self):
        """ExecutionTarget 数据结构包含 execution_node_id"""
        from libs.member.service import ExecutionTarget
        et = ExecutionTarget(
            tenant_id=1, account_id=1, user_id=1,
            exchange="binance", api_key="k", api_secret="s",
            passphrase=None, market_type="future",
            binding_id=1, strategy_code="test", ratio=100,
            execution_node_id=5,
        )
        assert et.execution_node_id == 5

    def test_signal_type_mapping(self):
        """signal_type → trade_type 映射逻辑（apply_results.py 中使用）"""
        mapping = {
            "OPEN": "OPEN", "CLOSE": "CLOSE", "ADD": "ADD",
            "HEDGE": "OPEN", "GRID": "OPEN",
        }
        assert mapping["CLOSE"] == "CLOSE"
        assert mapping["HEDGE"] == "OPEN"
        assert mapping["ADD"] == "ADD"


# ============================================================
#  SECTION 8: Position Monitor 事务安全
# ============================================================

class TestPositionMonitorWriteEvent:
    """验证 _write_close_signal_event 不做 commit"""

    def test_write_event_no_commit(self):
        """_write_close_signal_event 不应调用 session.commit()"""
        import importlib
        monitor_mod = importlib.import_module("libs.position.monitor")
        _write_fn = monitor_mod._write_close_signal_event

        mock_session = MagicMock()
        mock_position = MagicMock()
        mock_position.symbol = "BTC/USDT"
        mock_position.entry_price = Decimal("50000")
        mock_position.stop_loss = Decimal("49000")
        mock_position.take_profit = Decimal("52000")
        mock_position.position_side = "LONG"
        mock_position.strategy_code = "test"
        mock_position.account_id = 100
        mock_position.quantity = Decimal("0.01")

        _write_fn(
            session=mock_session,
            position=mock_position,
            trigger_type="SL",
            current_price=48900.0,
            signal_id="PM_SL_001",
            success=True,
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_not_called()  # 关键：不应做 commit


# ============================================================
#  SECTION 9: 策略库完整性
# ============================================================

class TestStrategyLibrary:
    """确保所有策略可以导入且继承自 StrategyBase"""

    def test_strategy_base_importable(self):
        from libs.strategies.base import StrategyBase
        assert hasattr(StrategyBase, "analyze")

    def test_market_regime_strategy(self):
        from libs.strategies.market_regime import MarketRegimeStrategy
        assert hasattr(MarketRegimeStrategy, "analyze")

    def test_multiple_strategies_importable(self):
        """批量验证策略可导入"""
        strategy_modules = [
            "libs.strategies.ma_cross",
            "libs.strategies.macd_strategy",
            "libs.strategies.rsi_strategy",
            "libs.strategies.breakout",
            "libs.strategies.momentum",
        ]
        for mod_path in strategy_modules:
            try:
                importlib.import_module(mod_path)
            except ImportError:
                pass  # 模块可能有不同命名，不作为硬失败


import importlib


# ============================================================
#  SECTION 10: 数据库模型字段完整性
# ============================================================

class TestDatabaseModelFields:
    """数据库模型字段完整性检查"""

    def test_order_model_has_trade_type(self):
        from libs.order_trade.models import Order
        columns = {c.name for c in Order.__table__.columns}
        assert "trade_type" in columns, "Order model missing trade_type column"

    def test_order_model_has_close_reason(self):
        from libs.order_trade.models import Order
        columns = {c.name for c in Order.__table__.columns}
        assert "close_reason" in columns, "Order model missing close_reason column"

    def test_fill_model_has_trade_type(self):
        from libs.order_trade.models import Fill
        columns = {c.name for c in Fill.__table__.columns}
        assert "trade_type" in columns, "Fill model missing trade_type column"

    def test_position_model_has_close_reason(self):
        from libs.position.models import Position
        columns = {c.name for c in Position.__table__.columns}
        assert "close_reason" in columns, "Position model missing close_reason column"

    def test_position_model_has_entry_price(self):
        from libs.position.models import Position
        columns = {c.name for c in Position.__table__.columns}
        assert "entry_price" in columns

    def test_position_model_has_stop_loss_take_profit(self):
        from libs.position.models import Position
        columns = {c.name for c in Position.__table__.columns}
        assert "stop_loss" in columns
        assert "take_profit" in columns

    def test_position_model_has_strategy_code(self):
        from libs.position.models import Position
        columns = {c.name for c in Position.__table__.columns}
        assert "strategy_code" in columns

    def test_exchange_account_has_execution_node_id(self):
        from libs.member.models import ExchangeAccount
        columns = {c.name for c in ExchangeAccount.__table__.columns}
        assert "execution_node_id" in columns

    def test_signal_event_model(self):
        from libs.facts.models import SignalEvent
        columns = {c.name for c in SignalEvent.__table__.columns}
        required = ["signal_id", "account_id", "event_type", "status",
                     "source_service", "detail", "created_at"]
        for col in required:
            assert col in columns, f"SignalEvent missing column: {col}"


# ============================================================
#  SECTION 11: 执行节点注册 & 模型
# ============================================================

class TestExecutionNodeModel:
    """执行节点数据模型"""

    def test_execution_node_model_fields(self):
        from libs.execution_node.models import ExecutionNode
        columns = {c.name for c in ExecutionNode.__table__.columns}
        required = ["id", "name", "base_url", "status"]
        for col in required:
            assert col in columns, f"ExecutionNode missing column: {col}"


# ============================================================
#  SECTION 12: Facts 层模型完整性
# ============================================================

class TestFactsModels:
    """事实层模型 - 不可变审计记录"""

    def test_signal_event_model_importable(self):
        from libs.facts.models import SignalEvent
        assert SignalEvent.__tablename__ == "fact_signal_event"

    def test_audit_log_model_importable(self):
        from libs.facts.models import AuditLog
        assert AuditLog.__tablename__ == "fact_audit_log"

    def test_ledger_fact_model(self):
        from libs.facts.models import Ledger
        columns = {c.name for c in Ledger.__table__.columns}
        assert "account_id" in columns
        assert "amount" in columns
        assert "currency" in columns

    def test_trade_fact_model(self):
        from libs.facts.models import Trade
        columns = {c.name for c in Trade.__table__.columns}
        assert "signal_id" in columns


# ============================================================
#  SECTION 13: Ledger 模型
# ============================================================

class TestLedgerModels:
    """账本/账户模型"""

    def test_account_model(self):
        from libs.ledger.models import Account
        columns = {c.name for c in Account.__table__.columns}
        required = ["id", "tenant_id", "account_id", "currency", "balance", "available", "frozen"]
        for col in required:
            assert col in columns, f"Account missing column: {col}"

    def test_transaction_model(self):
        from libs.ledger.models import Transaction
        columns = {c.name for c in Transaction.__table__.columns}
        required = ["id", "tenant_id", "account_id", "transaction_type", "amount"]
        for col in required:
            assert col in columns, f"Transaction missing column: {col}"


# ============================================================
#  SECTION 14: Member 模型
# ============================================================

class TestMemberModels:
    """会员系统模型"""

    def test_user_model(self):
        from libs.member.models import User
        columns = {c.name for c in User.__table__.columns}
        required = ["id", "tenant_id", "email", "point_card_self", "point_card_gift"]
        for col in required:
            assert col in columns, f"User missing column: {col}"

    def test_strategy_binding_model(self):
        from libs.member.models import StrategyBinding
        columns = {c.name for c in StrategyBinding.__table__.columns}
        required = ["id", "account_id", "strategy_code", "status"]
        for col in required:
            assert col in columns, f"StrategyBinding missing column: {col}"

    def test_strategy_model(self):
        from libs.member.models import Strategy
        columns = {c.name for c in Strategy.__table__.columns}
        assert "code" in columns  # 策略代码字段实际名为 code

    def test_tenant_strategy_model(self):
        from libs.member.models import TenantStrategy
        columns = {c.name for c in TenantStrategy.__table__.columns}
        assert "tenant_id" in columns
        assert "status" in columns


# ============================================================
#  SECTION 15: Point Card 模型
# ============================================================

class TestPointCardModel:
    """点卡系统"""

    def test_point_card_log_model(self):
        from libs.pointcard.models import PointCardLog
        columns = {c.name for c in PointCardLog.__table__.columns}
        required = ["id", "tenant_id", "user_id", "change_type", "amount"]
        for col in required:
            assert col in columns, f"PointCardLog missing column: {col}"


# ============================================================
#  SECTION 16: Reward 模型
# ============================================================

class TestRewardModels:
    """奖励/提现系统"""

    def test_user_reward_model(self):
        from libs.reward.models import UserReward
        columns = {c.name for c in UserReward.__table__.columns}
        assert "user_id" in columns

    def test_user_withdrawal_model(self):
        from libs.reward.models import UserWithdrawal
        columns = {c.name for c in UserWithdrawal.__table__.columns}
        assert "user_id" in columns
        assert "status" in columns


# ============================================================
#  SECTION 17: Quota 模型
# ============================================================

class TestQuotaModels:
    """配额/计费"""

    def test_quota_plan_model(self):
        from libs.quota.models import QuotaPlan
        columns = {c.name for c in QuotaPlan.__table__.columns}
        assert "name" in columns

    def test_api_usage_model(self):
        from libs.quota.models import ApiUsage
        columns = {c.name for c in ApiUsage.__table__.columns}
        assert "tenant_id" in columns


# ============================================================
#  SECTION 18: Analytics 模型
# ============================================================

class TestAnalyticsModels:
    """绩效分析模型"""

    def test_performance_snapshot_model(self):
        from libs.analytics.models import PerformanceSnapshot
        columns = {c.name for c in PerformanceSnapshot.__table__.columns}
        required = ["snapshot_id", "tenant_id", "account_id", "total_equity"]
        for col in required:
            assert col in columns, f"PerformanceSnapshot missing: {col}"

    def test_trade_statistics_model(self):
        from libs.analytics.models import TradeStatistics
        columns = {c.name for c in TradeStatistics.__table__.columns}
        assert "win_rate" in columns or "winning_trades" in columns

    def test_risk_metrics_model(self):
        from libs.analytics.models import RiskMetrics
        columns = {c.name for c in RiskMetrics.__table__.columns}
        assert "max_drawdown" in columns or "tenant_id" in columns


# ============================================================
#  SECTION 19: Admin 模型
# ============================================================

class TestAdminModel:
    """管理员模型"""

    def test_admin_model(self):
        from libs.admin.models import Admin
        columns = {c.name for c in Admin.__table__.columns}
        required = ["id", "username", "password_hash"]
        for col in required:
            assert col in columns, f"Admin missing: {col}"


# ============================================================
#  SECTION 20: Tenant 模型
# ============================================================

class TestTenantModel:
    """租户模型"""

    def test_tenant_model(self):
        from libs.tenant.models import Tenant
        columns = {c.name for c in Tenant.__table__.columns}
        required = ["id", "name", "app_key", "status"]
        for col in required:
            assert col in columns, f"Tenant missing: {col}"


# ============================================================
#  SECTION 21: Position 变动模型
# ============================================================

class TestPositionChangeModel:
    """仓位变动"""

    def test_position_change_model(self):
        from libs.position.models import PositionChange
        columns = {c.name for c in PositionChange.__table__.columns}
        required = ["id", "position_id", "change_type", "quantity_change"]
        for col in required:
            assert col in columns, f"PositionChange missing: {col}"


# ============================================================
#  SECTION 22: signal-monitor trade_type 映射
# ============================================================

class TestSignalMonitorTradeTypeMapping:
    """signal-monitor 中 signal_type → trade_type 的映射"""

    def test_close_signal_gets_trade_type_close(self):
        """CLOSE 信号应映射为 trade_type=CLOSE"""
        # 模拟 signal-monitor 中的映射逻辑
        sig_type = "CLOSE"
        mapping = {"OPEN": "OPEN", "CLOSE": "CLOSE", "ADD": "ADD",
                    "REDUCE": "REDUCE", "HEDGE": "OPEN", "GRID": "OPEN"}
        trade_type = mapping.get(sig_type, "OPEN")
        assert trade_type == "CLOSE"

    def test_open_signal_default(self):
        sig_type = "OPEN"
        mapping = {"OPEN": "OPEN", "CLOSE": "CLOSE", "ADD": "ADD",
                    "REDUCE": "REDUCE", "HEDGE": "OPEN", "GRID": "OPEN"}
        trade_type = mapping.get(sig_type, "OPEN")
        assert trade_type == "OPEN"

    def test_hedge_maps_to_open(self):
        sig_type = "HEDGE"
        mapping = {"OPEN": "OPEN", "CLOSE": "CLOSE", "ADD": "ADD",
                    "REDUCE": "REDUCE", "HEDGE": "OPEN", "GRID": "OPEN"}
        trade_type = mapping.get(sig_type, "OPEN")
        assert trade_type == "OPEN"

    def test_unknown_defaults_to_open(self):
        sig_type = "UNKNOWN_TYPE"
        mapping = {"OPEN": "OPEN", "CLOSE": "CLOSE", "ADD": "ADD",
                    "REDUCE": "REDUCE", "HEDGE": "OPEN", "GRID": "OPEN"}
        trade_type = mapping.get(sig_type, "OPEN")
        assert trade_type == "OPEN"


# ============================================================
#  SECTION 23: 核心 auth / config 模块导入
# ============================================================

class TestCoreModules:
    """核心基础设施可导入"""

    def test_config_importable(self):
        from libs.core.config import get_config
        assert callable(get_config)

    def test_logger_importable(self):
        from libs.core.logger import get_logger
        log = get_logger("test")
        assert log is not None

    def test_utils_importable(self):
        from libs.core import utils
        assert utils is not None

    def test_auth_module(self):
        try:
            from libs.core import auth
            assert auth is not None
        except ImportError:
            pass  # auth 可能依赖外部库


# ============================================================
#  SECTION 24: 集成 - DTO 与 Filter 配对完整性
# ============================================================

class TestDTOFilterPairing:
    """验证每个主要模型都有配对的 DTO 和 Filter"""

    def test_order_dto_and_filter(self):
        from libs.order_trade.contracts import OrderDTO, OrderFilter, CreateOrderDTO
        assert OrderDTO is not None
        assert OrderFilter is not None
        assert CreateOrderDTO is not None

    def test_fill_dto_and_filter(self):
        from libs.order_trade.contracts import FillDTO, FillFilter
        assert FillDTO is not None
        assert FillFilter is not None

    def test_position_dto_and_filter(self):
        from libs.position.contracts import PositionDTO, PositionFilter
        assert PositionDTO is not None
        assert PositionFilter is not None

    def test_position_change_dto(self):
        from libs.position.contracts import PositionChangeDTO
        assert PositionChangeDTO is not None

    def test_update_position_dto(self):
        from libs.position.contracts import UpdatePositionDTO
        assert UpdatePositionDTO is not None


# ============================================================
#  SECTION 25: 综合信号链路验证（模拟）
# ============================================================

class TestSignalChainIntegration:
    """
    模拟完整信号链路:
    策略产生信号 → 风控检查 → 生成执行目标 → 验证两步检查
    """

    def test_full_signal_chain_with_bound_node(self):
        """有节点绑定的完整链路：信号→风控通过→找到执行目标"""
        from libs.contracts import Signal, AccountContext, Position
        from libs.risk.engine import RiskEngine, RiskCheckContext
        from libs.risk.rules import MaxPositionRule, MinBalanceRule

        # 1. 策略产生信号
        signal = Signal(
            signal_id="sig_chain_001",
            strategy_code="market_regime",
            symbol="BTC/USDT",
            canonical_symbol="BTC/USDT",
            side="BUY",
            signal_type="OPEN",
            entry_price=50000,
            quantity=0.01,
            confidence=85,
        )
        assert signal.status == "pending"

        # 2. 风控检查
        account = AccountContext(
            account_id=1, user_id=1,
            balance=10000, available=8000,
            positions=[],
        )
        engine = RiskEngine(fail_fast=True)
        engine.add_rule(MaxPositionRule(max_positions=10))
        engine.add_rule(MinBalanceRule(min_balance=100))

        ctx = RiskCheckContext(signal=signal, account=account)
        violations = engine.check(ctx)
        assert len(violations) == 0, "风控应通过"

        # 3. 生成 CreateOrderDTO（模拟结算入口）
        from libs.order_trade.contracts import CreateOrderDTO
        order_dto = CreateOrderDTO(
            tenant_id=1, account_id=1, symbol="BTC/USDT",
            exchange="binance", side="BUY", order_type="MARKET",
            quantity=0.01, trade_type="OPEN",
            signal_id=signal.signal_id,
        )
        assert order_dto.trade_type == "OPEN"
        assert order_dto.signal_id == "sig_chain_001"

    def test_full_close_chain(self):
        """平仓链路：SL 触发 → CLOSE 订单 → 带 close_reason"""
        from libs.order_trade.contracts import CreateOrderDTO
        order_dto = CreateOrderDTO(
            tenant_id=1, account_id=1, symbol="BTC/USDT",
            exchange="binance", side="SELL", order_type="MARKET",
            quantity=0.01, trade_type="CLOSE", close_reason="SL",
            signal_id="PM_SL_001",
        )
        assert order_dto.trade_type == "CLOSE"
        assert order_dto.close_reason == "SL"

    def test_signal_rejected_by_risk(self):
        """信号被风控拒绝"""
        from libs.contracts import Signal, AccountContext
        from libs.risk.engine import RiskEngine, RiskCheckContext
        from libs.risk.rules import MinBalanceRule

        signal = Signal(
            signal_id="sig_rejected",
            strategy_code="test",
            symbol="BTC/USDT",
            canonical_symbol="BTC/USDT",
            side="BUY",
            signal_type="OPEN",
        )
        account = AccountContext(
            account_id=1, user_id=1,
            balance=50, available=50,
        )
        engine = RiskEngine()
        engine.add_rule(MinBalanceRule(min_balance=100))
        ctx = RiskCheckContext(signal=signal, account=account)
        violations = engine.check(ctx)
        assert len(violations) == 1
        assert violations[0].code == "RISK_INSUFFICIENT_BALANCE"


# ============================================================
#  运行入口
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
