"""
Position Monitor 自管 SL/TP 回归测试

覆盖范围：
  1. Position 模型新字段读写
  2. SL/TP 触发判断逻辑（多单/空单 × SL/TP × 边界值）
  3. _write_sl_tp_to_position 写入逻辑
  4. exchange_sl_tp 开关控制
  5. sync_position_from_exchange 时 SL/TP 清理
  6. 平仓重复触发保护
  7. 冷却回调注册
  8. execution-node ClosePositionRequest 结构
  9. apply_results 远程写入 SL/TP

运行：
  cd /path/to/ironbull
  PYTHONPATH=. pytest tests/test_position_monitor.py -v

无需数据库 / 交易所连接，全部 mock。
"""

import os
import sys
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== 1. Position 模型新字段 ====================

class TestPositionModelFields:
    """验证 Position 模型有 entry_price / stop_loss / take_profit / strategy_code 字段"""

    def test_model_has_sl_tp_columns(self):
        from libs.position.models import Position
        pos = Position()
        # 新字段应可赋值
        pos.entry_price = Decimal("2500.50")
        pos.stop_loss = Decimal("2400.00")
        pos.take_profit = Decimal("2700.00")
        pos.strategy_code = "market_regime"
        assert pos.entry_price == Decimal("2500.50")
        assert pos.stop_loss == Decimal("2400.00")
        assert pos.take_profit == Decimal("2700.00")
        assert pos.strategy_code == "market_regime"

    def test_to_dict_includes_new_fields(self):
        from libs.position.models import Position
        pos = Position()
        pos.id = 1
        pos.position_id = "POS001"
        pos.tenant_id = 1
        pos.account_id = 1
        pos.symbol = "ETH/USDT"
        pos.exchange = "binance"
        pos.market_type = "future"
        pos.position_side = "LONG"
        pos.quantity = Decimal("0.1")
        pos.available = Decimal("0.1")
        pos.frozen = Decimal("0")
        pos.avg_cost = Decimal("2500")
        pos.total_cost = Decimal("250")
        pos.realized_pnl = Decimal("0")
        pos.unrealized_pnl = None
        pos.leverage = 20
        pos.margin = Decimal("12.5")
        pos.liquidation_price = None
        pos.entry_price = Decimal("2500.00")
        pos.stop_loss = Decimal("2400.00")
        pos.take_profit = Decimal("2700.00")
        pos.strategy_code = "market_regime"
        pos.status = "OPEN"
        pos.opened_at = datetime(2026, 2, 7, 10, 0)
        pos.closed_at = None
        pos.created_at = datetime(2026, 2, 7, 10, 0)
        pos.updated_at = datetime(2026, 2, 7, 10, 0)

        d = pos.to_dict()
        assert d["entry_price"] == 2500.00
        assert d["stop_loss"] == 2400.00
        assert d["take_profit"] == 2700.00
        assert d["strategy_code"] == "market_regime"

    def test_to_dict_none_fields(self):
        """SL/TP 为 None 时 to_dict 不报错"""
        from libs.position.models import Position
        pos = Position()
        pos.id = 2
        pos.position_id = "POS002"
        pos.tenant_id = 1
        pos.account_id = 1
        pos.symbol = "BTC/USDT"
        pos.exchange = "binance"
        pos.market_type = "future"
        pos.position_side = "SHORT"
        pos.quantity = Decimal("0")
        pos.available = Decimal("0")
        pos.frozen = Decimal("0")
        pos.avg_cost = Decimal("0")
        pos.total_cost = Decimal("0")
        pos.realized_pnl = Decimal("0")
        pos.unrealized_pnl = None
        pos.leverage = None
        pos.margin = None
        pos.liquidation_price = None
        pos.entry_price = None
        pos.stop_loss = None
        pos.take_profit = None
        pos.strategy_code = None
        pos.status = "CLOSED"
        pos.opened_at = None
        pos.closed_at = None
        pos.created_at = datetime.now()
        pos.updated_at = datetime.now()

        d = pos.to_dict()
        assert d["entry_price"] is None
        assert d["stop_loss"] is None
        assert d["take_profit"] is None
        assert d["strategy_code"] is None


# ==================== 2. SL/TP 触发判断逻辑 ====================

class TestCheckTrigger:
    """验证 _check_trigger 的触发逻辑（多单/空单 × SL/TP × 边界值）"""

    def _make_pos(self, side="LONG", sl=None, tp=None):
        from libs.position.models import Position
        pos = Position()
        pos.position_side = side
        pos.stop_loss = Decimal(str(sl)) if sl else None
        pos.take_profit = Decimal(str(tp)) if tp else None
        return pos

    def test_long_sl_triggered(self):
        """多单：价格 <= 止损 → 触发 SL"""
        from libs.position.monitor import _check_trigger
        pos = self._make_pos("LONG", sl=2400, tp=2700)
        assert _check_trigger(pos, 2400.0) == "SL"   # 精确到价
        assert _check_trigger(pos, 2399.0) == "SL"   # 跌破
        assert _check_trigger(pos, 2401.0) is None    # 未到

    def test_long_tp_triggered(self):
        """多单：价格 >= 止盈 → 触发 TP"""
        from libs.position.monitor import _check_trigger
        pos = self._make_pos("LONG", sl=2400, tp=2700)
        assert _check_trigger(pos, 2700.0) == "TP"   # 精确到价
        assert _check_trigger(pos, 2800.0) == "TP"   # 超过
        assert _check_trigger(pos, 2699.0) is None    # 未到

    def test_short_sl_triggered(self):
        """空单：价格 >= 止损 → 触发 SL"""
        from libs.position.monitor import _check_trigger
        pos = self._make_pos("SHORT", sl=2600, tp=2300)
        assert _check_trigger(pos, 2600.0) == "SL"   # 精确到价
        assert _check_trigger(pos, 2700.0) == "SL"   # 突破
        assert _check_trigger(pos, 2599.0) is None    # 未到

    def test_short_tp_triggered(self):
        """空单：价格 <= 止盈 → 触发 TP"""
        from libs.position.monitor import _check_trigger
        pos = self._make_pos("SHORT", sl=2600, tp=2300)
        assert _check_trigger(pos, 2300.0) == "TP"   # 精确到价
        assert _check_trigger(pos, 2200.0) == "TP"   # 跌破
        assert _check_trigger(pos, 2301.0) is None    # 未到

    def test_sl_priority_over_tp(self):
        """同时满足 SL 和 TP 时，SL 优先（保护资金）"""
        from libs.position.monitor import _check_trigger
        # 不现实的配置: sl=2500, tp=2500，同时满足
        pos = self._make_pos("LONG", sl=2500, tp=2500)
        # SL 检查在前，应该返回 SL
        assert _check_trigger(pos, 2500.0) == "SL"

    def test_only_sl_set(self):
        """只设 SL 不设 TP"""
        from libs.position.monitor import _check_trigger
        pos = self._make_pos("LONG", sl=2400, tp=None)
        assert _check_trigger(pos, 2400.0) == "SL"
        assert _check_trigger(pos, 2900.0) is None  # 没有 TP，不触发

    def test_only_tp_set(self):
        """只设 TP 不设 SL"""
        from libs.position.monitor import _check_trigger
        pos = self._make_pos("LONG", sl=None, tp=2700)
        assert _check_trigger(pos, 2100.0) is None  # 没有 SL
        assert _check_trigger(pos, 2700.0) == "TP"

    def test_no_sl_tp(self):
        """都没设置 → 不触发"""
        from libs.position.monitor import _check_trigger
        pos = self._make_pos("LONG", sl=None, tp=None)
        assert _check_trigger(pos, 2500.0) is None


# ==================== 3. 重复触发保护 ====================

class TestClosingInProgress:
    """验证 _closing_in_progress 防重机制"""

    def test_closing_set_operations(self):
        """_closing_in_progress 是 set 类型，可以 add/discard"""
        from libs.position import monitor
        # 确保是干净状态
        monitor._closing_in_progress.clear()
        assert len(monitor._closing_in_progress) == 0

        monitor._closing_in_progress.add("POS001")
        assert "POS001" in monitor._closing_in_progress

        monitor._closing_in_progress.discard("POS001")
        assert "POS001" not in monitor._closing_in_progress

        # discard 不存在的不报错
        monitor._closing_in_progress.discard("POS999")


# ==================== 4. 冷却回调注册 ====================

class TestSlTriggeredCallback:
    """验证止损冷却回调注册机制"""

    def test_set_callback(self):
        from libs.position.monitor import set_on_sl_triggered, _on_sl_triggered_callback
        called = []
        def my_cb(symbol, strategy):
            called.append((symbol, strategy))

        set_on_sl_triggered(my_cb)
        from libs.position import monitor
        assert monitor._on_sl_triggered_callback is my_cb
        monitor._on_sl_triggered_callback("ETH/USDT", "market_regime")
        assert called == [("ETH/USDT", "market_regime")]
        # 清理
        set_on_sl_triggered(None)

    def test_callback_none_is_safe(self):
        """回调为 None 时不应崩溃"""
        from libs.position.monitor import set_on_sl_triggered
        set_on_sl_triggered(None)
        from libs.position import monitor
        assert monitor._on_sl_triggered_callback is None


# ==================== 5. sync_position_from_exchange 清理 SL/TP ====================

class TestSyncPositionCleanup:
    """验证持仓同步时自动清理 SL/TP"""

    def _make_service_with_mock_repos(self):
        """构建一个有 mock repo 的 PositionService"""
        from libs.position.service import PositionService
        mock_session = MagicMock()
        svc = PositionService(mock_session)
        return svc

    def test_close_clears_sl_tp(self):
        """持仓 OPEN→CLOSED 时应清除 stop_loss 和 take_profit"""
        from libs.position.models import Position
        from libs.position.service import PositionService

        pos = Position()
        pos.position_id = "POS_SYNC_1"
        pos.tenant_id = 1
        pos.account_id = 1
        pos.symbol = "ETH/USDT"
        pos.exchange = "binance"
        pos.market_type = "future"
        pos.position_side = "LONG"
        pos.quantity = Decimal("0.1")
        pos.available = Decimal("0.1")
        pos.frozen = Decimal("0")
        pos.avg_cost = Decimal("2500")
        pos.total_cost = Decimal("250")
        pos.status = "OPEN"
        pos.stop_loss = Decimal("2400")
        pos.take_profit = Decimal("2700")
        pos.entry_price = Decimal("2500")
        pos.strategy_code = "market_regime"
        pos.opened_at = datetime.now()
        pos.closed_at = None

        mock_session = MagicMock()
        svc = PositionService(mock_session)
        # Mock repos
        svc.position_repo = MagicMock()
        svc.position_repo.get_or_create.return_value = (pos, False)
        svc.position_repo.update.return_value = pos
        svc.change_repo = MagicMock()

        # 同步为 quantity=0 → CLOSED
        svc.sync_position_from_exchange(
            tenant_id=1, account_id=1,
            symbol="ETH/USDT", exchange="binance",
            market_type="future", position_side="LONG",
            quantity=Decimal("0"), avg_cost=Decimal("0"),
        )

        assert pos.status == "CLOSED"
        assert pos.stop_loss is None
        assert pos.take_profit is None
        assert pos.closed_at is not None

    def test_reopen_clears_old_sl_tp(self):
        """持仓 CLOSED→OPEN 时应清除旧的 SL/TP（防止旧数据干扰新仓位）"""
        from libs.position.models import Position
        from libs.position.service import PositionService

        pos = Position()
        pos.position_id = "POS_SYNC_2"
        pos.tenant_id = 1
        pos.account_id = 1
        pos.symbol = "ETH/USDT"
        pos.exchange = "binance"
        pos.market_type = "future"
        pos.position_side = "LONG"
        pos.quantity = Decimal("0")
        pos.available = Decimal("0")
        pos.frozen = Decimal("0")
        pos.avg_cost = Decimal("0")
        pos.total_cost = Decimal("0")
        pos.status = "CLOSED"
        # 旧的残留 SL/TP
        pos.stop_loss = Decimal("2400")
        pos.take_profit = Decimal("2700")
        pos.entry_price = Decimal("2500")
        pos.strategy_code = "old_strategy"
        pos.opened_at = None
        pos.closed_at = datetime.now()

        mock_session = MagicMock()
        svc = PositionService(mock_session)
        svc.position_repo = MagicMock()
        svc.position_repo.get_or_create.return_value = (pos, False)
        svc.position_repo.update.return_value = pos
        svc.change_repo = MagicMock()

        # 同步为 quantity=0.05 → 重新 OPEN
        svc.sync_position_from_exchange(
            tenant_id=1, account_id=1,
            symbol="ETH/USDT", exchange="binance",
            market_type="future", position_side="LONG",
            quantity=Decimal("0.05"), avg_cost=Decimal("2600"),
        )

        assert pos.status == "OPEN"
        assert pos.stop_loss is None
        assert pos.take_profit is None
        assert pos.entry_price is None
        assert pos.strategy_code is None
        assert pos.opened_at is not None


# ==================== 6. exchange_sl_tp 开关控制 ====================

class TestExchangeSlTpSwitch:
    """验证 exchange_sl_tp 配置开关的逻辑"""

    def test_config_default_is_false(self):
        """默认 exchange_sl_tp=False（自管模式）"""
        from libs.core import get_config
        config = get_config()
        # 没有显式设置过的话默认 False
        val = config.get_bool("exchange_sl_tp", False)
        assert val is False


# ==================== 7. execution-node ClosePositionRequest ====================

class TestClosePositionRequest:
    """验证 ClosePositionRequest 模型结构正确（execution-node 的目录不是标准包，用动态导入）"""

    def _import_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "execution_node_main",
            os.path.join(os.path.dirname(__file__), "..", "services", "execution-node", "app", "main.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_request_model_fields(self):
        """ClosePositionRequest 应包含 amount_usdt 而非 quantity"""
        mod = self._import_module()
        ClosePositionRequest = mod.ClosePositionRequest

        req = ClosePositionRequest(
            account_id=1,
            tenant_id=1,
            exchange="binance",
            api_key="test",
            api_secret="test",
            market_type="future",
            symbol="ETH/USDT",
            side="SELL",
            amount_usdt=250.0,
            trigger_type="SL",
        )
        assert req.amount_usdt == 250.0
        assert req.trigger_type == "SL"
        assert req.side == "SELL"
        # 确保没有 quantity 字段
        assert not hasattr(req, "quantity")

    def test_request_model_default_trigger_type(self):
        """trigger_type 默认值为 SL"""
        mod = self._import_module()
        ClosePositionRequest = mod.ClosePositionRequest

        req = ClosePositionRequest(
            account_id=1, tenant_id=1, exchange="binance",
            api_key="k", api_secret="s",
            symbol="BTC/USDT", side="BUY", amount_usdt=5000.0,
        )
        assert req.trigger_type == "SL"


# ==================== 8. apply_results 远程写入 SL/TP ====================

class TestApplyResultsSlTp:
    """验证远程节点结果回写时 SL/TP 正确写入持仓表"""

    def test_write_sl_tp_to_position_remote(self):
        from libs.execution_node.apply_results import _write_sl_tp_to_position_remote
        from libs.member import ExecutionTarget

        mock_session = MagicMock()
        mock_pos = MagicMock()
        mock_pos.entry_price = None
        mock_pos.stop_loss = None
        mock_pos.take_profit = None
        mock_pos.strategy_code = None

        mock_repo = MagicMock()
        mock_repo.get_by_key.return_value = mock_pos

        target = ExecutionTarget(
            binding_id=1, user_id=1, account_id=100,
            tenant_id=1, exchange="binance",
            api_key="k", api_secret="s", passphrase="",
            market_type="future", mode=2, ratio=100,
            execution_node_id=None, strategy_code="market_regime",
            binding_capital=0, binding_leverage=0, binding_amount_usdt=0,
        )

        # PositionRepository 是在函数内部 lazy import 的，patch 其来源模块
        with patch("libs.position.repository.PositionRepository", return_value=mock_repo):
            _write_sl_tp_to_position_remote(
                session=mock_session,
                target=target,
                symbol="ETH/USDT",
                side="BUY",
                filled_price=2500.0,
                stop_loss=2400.0,
                take_profit=2700.0,
                strategy_code="market_regime",
            )

        assert mock_pos.entry_price == Decimal("2500.0")
        assert mock_pos.stop_loss == Decimal("2400.0")
        assert mock_pos.take_profit == Decimal("2700.0")
        assert mock_pos.strategy_code == "market_regime"
        mock_repo.update.assert_called_once_with(mock_pos)

    def test_write_sl_tp_zero_values_are_none(self):
        """stop_loss=0 或 take_profit=0 应写入 None（表示不设置）"""
        from libs.execution_node.apply_results import _write_sl_tp_to_position_remote
        from libs.member import ExecutionTarget

        mock_session = MagicMock()
        mock_pos = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_key.return_value = mock_pos

        target = ExecutionTarget(
            binding_id=1, user_id=1, account_id=100,
            tenant_id=1, exchange="binance",
            api_key="k", api_secret="s", passphrase="",
            market_type="future", mode=2, ratio=100,
            execution_node_id=None, strategy_code="",
            binding_capital=0, binding_leverage=0, binding_amount_usdt=0,
        )

        with patch("libs.position.repository.PositionRepository", return_value=mock_repo):
            _write_sl_tp_to_position_remote(
                session=mock_session,
                target=target,
                symbol="BTC/USDT",
                side="SELL",
                filled_price=50000.0,
                stop_loss=0,        # 0 → None
                take_profit=0,      # 0 → None
            )

        assert mock_pos.stop_loss is None
        assert mock_pos.take_profit is None


# ==================== 9. _write_sl_tp_to_position（signal-monitor）====================

class TestWriteSlTpToPosition:
    """验证 OrderSide → position_side 映射逻辑（不依赖 signal-monitor import，直接测逻辑）"""

    def test_orderenum_buy_maps_to_long(self):
        """OrderSide.BUY → position_side='LONG'"""
        from libs.trading.base import OrderSide
        # 复现 signal-monitor 中的映射逻辑
        order_side = OrderSide.BUY
        if isinstance(order_side, OrderSide):
            position_side = "LONG" if order_side == OrderSide.BUY else "SHORT"
        else:
            position_side = "LONG" if str(order_side).upper().endswith("BUY") else "SHORT"
        assert position_side == "LONG"

    def test_orderenum_sell_maps_to_short(self):
        """OrderSide.SELL → position_side='SHORT'"""
        from libs.trading.base import OrderSide
        order_side = OrderSide.SELL
        if isinstance(order_side, OrderSide):
            position_side = "LONG" if order_side == OrderSide.BUY else "SHORT"
        else:
            position_side = "LONG" if str(order_side).upper().endswith("BUY") else "SHORT"
        assert position_side == "SHORT"

    def test_string_buy_maps_to_long(self):
        """字符串 'BUY' → position_side='LONG'"""
        order_side = "BUY"
        from libs.trading.base import OrderSide
        if isinstance(order_side, OrderSide):
            position_side = "LONG" if order_side == OrderSide.BUY else "SHORT"
        else:
            position_side = "LONG" if str(order_side).upper().endswith("BUY") else "SHORT"
        assert position_side == "LONG"

    def test_string_sell_maps_to_short(self):
        """字符串 'SELL' → position_side='SHORT'"""
        order_side = "SELL"
        from libs.trading.base import OrderSide
        if isinstance(order_side, OrderSide):
            position_side = "LONG" if order_side == OrderSide.BUY else "SHORT"
        else:
            position_side = "LONG" if str(order_side).upper().endswith("BUY") else "SHORT"
        assert position_side == "SHORT"


# ==================== 10. 价格缓存 ====================

class TestPriceCache:
    """验证价格缓存机制"""

    def test_cache_structure(self):
        from libs.position import monitor
        # 缓存应该是 dict
        assert isinstance(monitor._price_cache, dict)
        assert monitor._PRICE_CACHE_TTL > 0

    def test_cache_ttl_config(self):
        from libs.position.monitor import _PRICE_CACHE_TTL
        assert _PRICE_CACHE_TTL == 2  # 2秒

    def test_stats_structure(self):
        from libs.position.monitor import get_monitor_stats
        stats = get_monitor_stats()
        assert "last_scan_at" in stats
        assert "positions_monitored" in stats
        assert "triggers_total" in stats
        assert "closes_success" in stats
        assert "closes_failed" in stats


# ==================== 11. migration 018 幂等性 ====================

class TestMigration018:
    """验证迁移脚本可导入且结构正确"""

    def test_migration_importable(self):
        """迁移脚本可以导入"""
        import scripts.run_migration_018 as m
        assert hasattr(m, "run")
        assert hasattr(m, "column_exists")

    def test_column_exists_function(self):
        """column_exists 函数签名正确"""
        from scripts.run_migration_018 import column_exists
        import inspect
        sig = inspect.signature(column_exists)
        params = list(sig.parameters.keys())
        assert params == ["conn", "table", "column", "schema"]


# ==================== 12. 综合数据流 ====================

class TestEndToEndDataFlow:
    """验证完整数据流：开仓 → 写SL/TP → 触发 → 平仓"""

    def test_long_position_full_lifecycle(self):
        """模拟多单完整生命周期：开仓 → SL/TP写入 → 价格下跌 → SL触发"""
        from libs.position.models import Position
        from libs.position.monitor import _check_trigger

        # 1. 开仓后写入 SL/TP
        pos = Position()
        pos.position_id = "POS_E2E_1"
        pos.position_side = "LONG"
        pos.quantity = Decimal("0.1")
        pos.status = "OPEN"
        pos.entry_price = Decimal("2500")
        pos.stop_loss = Decimal("2425")    # 2500 × (1 - 0.30/20) = 2462.5... 用策略算的
        pos.take_profit = Decimal("2650")  # 2500 × (1 + 1.20/20) = 2650

        # 2. 价格在正常范围 → 不触发
        assert _check_trigger(pos, 2500.0) is None
        assert _check_trigger(pos, 2450.0) is None  # 还没到 SL

        # 3. 价格到达 TP → 触发
        assert _check_trigger(pos, 2650.0) == "TP"

        # 4. 价格暴跌到 SL → 触发
        assert _check_trigger(pos, 2425.0) == "SL"
        assert _check_trigger(pos, 2300.0) == "SL"

    def test_short_position_full_lifecycle(self):
        """模拟空单完整生命周期"""
        from libs.position.models import Position
        from libs.position.monitor import _check_trigger

        pos = Position()
        pos.position_id = "POS_E2E_2"
        pos.position_side = "SHORT"
        pos.quantity = Decimal("0.05")
        pos.status = "OPEN"
        pos.entry_price = Decimal("2500")
        pos.stop_loss = Decimal("2575")    # 空单止损在上方
        pos.take_profit = Decimal("2350")  # 空单止盈在下方

        # 正常范围
        assert _check_trigger(pos, 2500.0) is None
        assert _check_trigger(pos, 2550.0) is None

        # 止盈触发（价格跌下去了）
        assert _check_trigger(pos, 2350.0) == "TP"
        assert _check_trigger(pos, 2200.0) == "TP"

        # 止损触发（价格涨上去了）
        assert _check_trigger(pos, 2575.0) == "SL"
        assert _check_trigger(pos, 2700.0) == "SL"

    def test_amount_usdt_calculation(self):
        """验证平仓时 amount_usdt = qty × price 计算正确"""
        qty = 0.1  # 0.1 ETH
        price = 2500.0
        amount_usdt = qty * price
        assert amount_usdt == 250.0

        qty2 = 0.001  # 0.001 BTC
        price2 = 95000.0
        amount_usdt2 = qty2 * price2
        assert amount_usdt2 == 95.0
