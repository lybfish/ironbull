"""
Live Trader - 真实交易执行器

基于 ccxt 实现真实交易所下单
支持可选的 TradeSettlementService 集成，实现完整交易闭环：
  OrderTrade → Position → Ledger
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Set, TYPE_CHECKING

import ccxt.async_support as ccxt

from libs.core import get_logger, gen_id
from libs.exchange.utils import symbol_for_ccxt_futures, normalize_symbol
from .base import (
    Trader, OrderResult, OrderStatus, OrderSide, OrderType, Balance
)

# 延迟导入避免循环依赖
if TYPE_CHECKING:
    from libs.order_trade import OrderTradeService
    from libs.trading.settlement import TradeSettlementService

logger = get_logger("live-trader")

# ==================== 常量 ====================
# 市价下单占位符（各交易所约定）
OKX_MARKET_PRICE = "-1"          # OKX algo-order 市价
GATE_MARKET_PRICE = "0"          # Gate 条件单市价
GATE_CLOSE_ALL_SIZE = 0          # Gate 0 = 全部平仓

# 默认报价币种
DEFAULT_QUOTE = "USDT"
# 默认结算币种（Gate API）
DEFAULT_SETTLE = "usdt"

# 市价单异步确认：重试次数 / 间隔(秒)
MARKET_ORDER_CONFIRM_RETRIES = 3
MARKET_ORDER_CONFIRM_INTERVAL = 0.5
# 网络瞬时错误重试（仅对 create_order）
NETWORK_RETRIES = 2
NETWORK_RETRY_DELAY = 1.0

# OKX 全仓 closeFraction
OKX_CLOSE_FULL_FRACTION = "1"

# 杠杆 fallback（仅在完全无法查询当前杠杆时使用，应尽量从策略传入）
DEFAULT_LEVERAGE_FALLBACK = 20


class LiveTrader(Trader):
    """
    真实交易执行器
    
    使用 ccxt 连接交易所执行真实订单
    
    支持的交易所：
    - binance
    - okx
    - bybit
    
    使用示例：
        trader = LiveTrader(
            exchange="binance",
            api_key="xxx",
            api_secret="xxx",
        )
        
        result = await trader.market_buy("BTC/USDT", 0.001)
        
        await trader.close()
    """
    
    SUPPORTED_EXCHANGES = ["binance", "binanceusdm", "okx", "bybit", "gate", "huobi"]
    
    def __init__(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,  # OKX 需要
        sandbox: bool = False,              # 是否使用沙盒/测试网
        market_type: str = "future",        # 市场类型: spot / future
        options: Optional[Dict[str, Any]] = None,
        # OrderTrade 集成（可选，旧版兼容）
        order_trade_service: Optional["OrderTradeService"] = None,
        tenant_id: Optional[int] = None,
        account_id: Optional[int] = None,
        # 完整结算集成（推荐）
        settlement_service: Optional["TradeSettlementService"] = None,
    ):
        """
        Args:
            exchange: 交易所名称 (binance/okx/bybit)
            api_key: API Key
            api_secret: API Secret
            passphrase: API Passphrase (OKX 需要)
            sandbox: 是否使用测试网
            market_type: 市场类型 (spot=现货, future=合约)
            options: ccxt 额外选项
            order_trade_service: OrderTradeService 实例（可选，旧版兼容）
            tenant_id: 租户ID
            account_id: 账户ID
            settlement_service: TradeSettlementService 实例（推荐，完整交易闭环）
        """
        self.exchange_name = exchange.lower()
        self.sandbox = sandbox
        self.market_type = market_type
        
        # 结算服务（完整交易闭环：OrderTrade → Position → Ledger）
        self._settlement_service = settlement_service
        
        # OrderTrade 集成（旧版兼容）
        self._order_trade_service = order_trade_service
        self._tenant_id = tenant_id
        self._account_id = account_id
        
        if self.exchange_name not in self.SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported exchange: {exchange}")
        
        # 构建 ccxt 配置
        config = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": options or {},
        }
        
        if passphrase:
            config["password"] = passphrase
        
        # 合约交易配置
        if market_type == "future":
            if self.exchange_name == "binance":
                # Binance USDT 永续合约
                self.exchange_name = "binanceusdm"
                config["options"]["defaultType"] = "future"
            elif self.exchange_name == "okx":
                config["options"]["defaultType"] = "swap"
            elif self.exchange_name == "bybit":
                config["options"]["defaultType"] = "linear"
            elif self.exchange_name == "gate":
                self.exchange_name = "gateio"
                # Gate 永续合约用 swap（future 是交割合约）；统一账户余额走 spot 端点
                config["options"]["defaultType"] = "swap"
        
        # CCXT 类名映射（用户传 gate，CCXT 为 gateio）
        if self.exchange_name == "gate":
            self.exchange_name = "gateio"
        
        # 创建交易所实例
        exchange_class = getattr(ccxt, self.exchange_name)
        self.exchange: ccxt.Exchange = exchange_class(config)
        
        # 启用沙盒模式
        if sandbox:
            self.exchange.set_sandbox_mode(True)
            logger.info("sandbox mode enabled", exchange=exchange)
        
        # 合约持仓模式：None=未检测，True=双向持仓，False=单向持仓（不传 positionSide）
        self._position_mode_dual: Optional[bool] = None
        # 已尝试设为逐仓的 symbol 集合（每 symbol 只尝试一次）
        self._margin_isolated_tried: Set[str] = set()
        
        logger.info("live trader initialized", exchange=exchange, sandbox=sandbox)

    def _ccxt_symbol(self, symbol: str) -> str:
        """下单用 symbol：合约时转为 CCXT 格式 BASE/QUOTE:USDT"""
        if self.market_type == "future" and symbol and ":" not in symbol:
            return symbol_for_ccxt_futures(symbol, DEFAULT_QUOTE)
        return normalize_symbol(symbol, "binance")  # "binance" 仅用于解析为 BASE/QUOTE 标准格式

    def _amount_precision(self, symbol: str, quantity: float):
        """按交易所精度舍入数量，失败则返回原值"""
        try:
            return float(self.exchange.amount_to_precision(symbol, quantity))
        except Exception:
            return quantity

    def _price_precision(self, symbol: str, price: float):
        """按交易所精度舍入价格，失败则返回原值"""
        try:
            return float(self.exchange.price_to_precision(symbol, price))
        except Exception:
            return price

    # ============ 合约张数 ↔ 币数量 转换 ============

    def _get_contract_size(self, symbol: str) -> float:
        """
        获取合约张的大小（contractSize）。
        - Gate BTC/USDT: 0.0001（1张 = 0.0001 BTC）
        - OKX BTC/USDT:  0.01  （1张 = 0.01 BTC）
        - Binance:        1     （以币为单位，contractSize=1）
        markets 必须已加载（load_markets），否则返回 0。
        """
        try:
            ccxt_sym = self._ccxt_symbol(symbol)
            market = self.exchange.markets.get(ccxt_sym, {})
            return float(market.get("contractSize") or 0)
        except Exception:
            return 0

    def _contracts_to_coins(self, contracts: float, symbol: str) -> float:
        """
        将合约张数转为币数量。
        - 如果 contractSize > 0 且 ≠ 1 → contracts × contractSize
        - 否则原样返回（如 Binance 已是币单位）
        使用统一的 contracts_to_coins_by_size 纯函数。
        """
        from libs.exchange.market_service import contracts_to_coins_by_size
        cs = self._get_contract_size(symbol)
        return contracts_to_coins_by_size(contracts, cs)

    # ============ USDT → 数量换算（统一处理 contractSize） ============

    async def usdt_to_quantity(self, symbol: str, amount_usdt: float, price: float) -> float:
        """
        将 USDT 金额转为交易所下单数量，自动处理各交易所差异：
        - Binance：永续合约以币为单位（如 0.001 BTC），直接 amount_usdt / price
        - Gate/OKX：永续合约以"张"为单位，需除以 contractSize（如 OKX BTC 1张=0.01 BTC）
        - 自动校验交易所最小/最大下单量

        Args:
            symbol: 交易对（BTC/USDT）
            amount_usdt: 下单金额（USDT）
            price: 入场价格
        Returns:
            交易所下单数量（币数量或张数）
        Raises:
            ValueError: 金额不足或超限
        """
        if price <= 0:
            raise ValueError(f"invalid price: {price}")
        if amount_usdt <= 0:
            raise ValueError(f"invalid amount_usdt: {amount_usdt}")

        ccxt_sym = self._ccxt_symbol(symbol)
        await self.exchange.load_markets()
        market = self.exchange.market(ccxt_sym)

        contract_size = float(market.get("contractSize") or 0)
        eid = getattr(self.exchange, "id", "")

        # Gate/OKX 合约按张计，需转换
        if contract_size > 0 and eid in ("gateio", "okx") and self.market_type == "future":
            raw_contracts = amount_usdt / (price * contract_size)
            quantity = int(raw_contracts)  # 向下取整（不超出用户预算）
            if quantity < 1:
                cost_per_contract = price * contract_size
                raise ValueError(
                    f"{symbol} 金额 {amount_usdt} USDT 不足 1 张合约"
                    f"（1张={contract_size} {symbol.split('/')[0]}，约 {cost_per_contract:.2f} USDT）"
                )
            logger.debug(
                "usdt_to_quantity (contract)",
                symbol=symbol, amount_usdt=amount_usdt, price=price,
                contract_size=contract_size, quantity=quantity,
            )
        else:
            # Binance 等以币为单位
            quantity = amount_usdt / price
            quantity = self._amount_precision(ccxt_sym, quantity)
            logger.debug(
                "usdt_to_quantity (coin)",
                symbol=symbol, amount_usdt=amount_usdt, price=price, quantity=quantity,
            )

        # 校验最小/最大下单量
        limits = market.get("limits", {})
        amount_limits = limits.get("amount", {})
        cost_limits = limits.get("cost", {})

        min_amount = float(amount_limits.get("min") or 0)
        max_amount = float(amount_limits.get("max") or 0)
        min_cost = float(cost_limits.get("min") or 0)

        if min_amount > 0 and quantity < min_amount:
            raise ValueError(
                f"{symbol} 下单量 {quantity} 低于交易所最小值 {min_amount}"
                f"（约需 {min_amount * price:.2f} USDT）"
            )
        if max_amount > 0 and quantity > max_amount:
            raise ValueError(
                f"{symbol} 下单量 {quantity} 超过交易所最大值 {max_amount}"
            )
        if min_cost > 0 and amount_usdt < min_cost:
            raise ValueError(
                f"{symbol} 下单金额 {amount_usdt} USDT 低于交易所最小名义价值 {min_cost} USDT"
            )

        if quantity <= 0:
            raise ValueError(f"{symbol} 计算后数量为 0（amount_usdt={amount_usdt}, price={price}）")

        return quantity

    # ============ 杠杆设置 ============

    async def ensure_leverage(self, symbol: str, leverage: int) -> None:
        """
        设置合约杠杆倍数。每 symbol 只设置一次（缓存）。
        若交易所已是同一杠杆则跳过；设置失败（如有持仓）则警告继续。

        Args:
            symbol: 交易对（BTC/USDT）
            leverage: 杠杆倍数（如 20）
        """
        if self.market_type != "future" or not symbol or not leverage or leverage < 1:
            return
        ccxt_sym = self._ccxt_symbol(symbol)
        cache_key = f"_lev_{ccxt_sym}"
        if getattr(self, cache_key, None) == leverage:
            return  # 已设置过相同杠杆

        try:
            if self.exchange_name == "gateio":
                # Gate 统一账户：leverage > 0 即逐仓模式，不传 cross_leverage_limit
                contract = self._gate_contract_name(symbol)
                try:
                    await self.exchange.privateFuturesPostSettlePositions({
                        "settle": DEFAULT_SETTLE,
                        "contract": contract,
                        "leverage": str(leverage),
                    })
                except Exception:
                    # Gate 可能不支持或已有持仓，尝试 CCXT 方式
                    try:
                        await self.exchange.set_leverage(leverage, ccxt_sym)
                    except Exception as e2:
                        logger.warning("gate set leverage failed, continue", symbol=ccxt_sym, leverage=leverage, error=str(e2))
                        return
            elif self.exchange_name == "okx":
                # OKX：通过 set-leverage API，需同时传 mgnMode
                await self.exchange.load_markets()
                inst_id = self.exchange.market_id(ccxt_sym)
                params: Dict[str, Any] = {
                    "instId": inst_id,
                    "lever": str(leverage),
                    "mgnMode": "isolated",
                }
                # 双向持仓需要分别设 long 和 short
                if self._position_mode_dual:
                    for ps in ("long", "short"):
                        params["posSide"] = ps
                        try:
                            await self.exchange.privatePostAccountSetLeverage(params)
                        except Exception as e:
                            if "leverage is the same" not in str(e).lower():
                                logger.warning("okx set leverage failed", symbol=ccxt_sym, posSide=ps, error=str(e))
                else:
                    try:
                        await self.exchange.privatePostAccountSetLeverage(params)
                    except Exception as e:
                        if "leverage is the same" not in str(e).lower():
                            logger.warning("okx set leverage failed", symbol=ccxt_sym, error=str(e))
            else:
                # Binance 等：CCXT 统一接口
                await self.exchange.set_leverage(leverage, ccxt_sym)

            setattr(self, cache_key, leverage)
            logger.info("leverage set", exchange=self.exchange_name, symbol=ccxt_sym, leverage=leverage)
        except Exception as e:
            err_str = str(e).lower()
            # "No need to change leverage" / "leverage not modified"
            if "no need" in err_str or "not modified" in err_str or "same" in err_str:
                setattr(self, cache_key, leverage)
                logger.debug("leverage already set", symbol=ccxt_sym, leverage=leverage)
            else:
                logger.warning("set leverage failed, continue", symbol=ccxt_sym, leverage=leverage, error=str(e))

    async def ensure_dual_position_mode(self) -> bool:
        """
        合约账户：尝试设为双向持仓，保证下单可传 positionSide。
        若当前为单向或有持仓无法切换，则返回 False，下单时不传 positionSide（参考 old3）。
        """
        if self.market_type != "future":
            return False
        if self._position_mode_dual is not None:
            return self._position_mode_dual

        # --- OKX：通过 account config 检测并尝试切换 ---
        if self.exchange_name == "okx":
            try:
                cfg_fn = getattr(self.exchange, "privateGetAccountConfig", None)
                if cfg_fn:
                    cfg_result = cfg_fn()
                    cfg_resp = await cfg_result if asyncio.iscoroutine(cfg_result) else cfg_result
                    pos_mode = ""
                    if isinstance(cfg_resp, dict):
                        data_list = cfg_resp.get("data", [])
                        if data_list and isinstance(data_list[0], dict):
                            pos_mode = data_list[0].get("posMode", "")
                    if pos_mode == "long_short_mode":
                        self._position_mode_dual = True
                        logger.info("okx position mode is dual (long_short_mode)")
                        return True
                    # 当前为 net_mode，尝试切换
                    logger.info("okx position mode is net_mode, trying to switch to dual")
                    try:
                        set_fn = getattr(self.exchange, "privatePostAccountSetPositionMode", None)
                        if set_fn:
                            set_result = set_fn({"posMode": "long_short_mode"})
                            if asyncio.iscoroutine(set_result):
                                await set_result
                            self._position_mode_dual = True
                            logger.info("okx position mode switched to long_short_mode")
                            return True
                    except Exception as sw_err:
                        logger.warning("okx switch to dual failed, using net mode", error=str(sw_err))
                self._position_mode_dual = False
                logger.info("okx using net (one-way) position mode")
                return False
            except Exception as e:
                logger.warning("okx ensure_dual failed, assuming net mode", error=str(e))
                self._position_mode_dual = False
                return False

        # --- Gate：必须通过 API 开启双向持仓，否则开空会平掉多仓（单向 net 模式） ---
        if self.exchange_name == "gateio":
            try:
                set_dual_fn = getattr(self.exchange, "set_position_mode", None)
                if not set_dual_fn:
                    logger.warning("gate has no set_position_mode, assuming dual")
                    self._position_mode_dual = True
                    return True
                try:
                    result = set_dual_fn(True, None)
                    if asyncio.iscoroutine(result):
                        await result
                    self._position_mode_dual = True
                    logger.info("gate position mode set to dual (hedge)")
                    return True
                except Exception as sw_err:
                    err_str = str(sw_err).lower()
                    if "already" in err_str or "no need" in err_str or "dual" in err_str:
                        # 已是双向，视为成功
                        self._position_mode_dual = True
                        logger.debug("gate already in dual mode", error=str(sw_err))
                        return True
                    if "position" in err_str or "order" in err_str or "exist" in err_str or "cannot" in err_str:
                        logger.warning("gate cannot switch to dual (has position or orders?), using one-way", error=str(sw_err))
                        self._position_mode_dual = False
                        return False
                    logger.warning("gate set dual mode failed, using one-way", error=str(sw_err))
                    self._position_mode_dual = False
                    return False
            except Exception as e:
                logger.warning("gate ensure_dual failed, assuming dual", error=str(e))
                self._position_mode_dual = True
                return True

        # --- 其他（如 bybit）：默认双向 ---
        if self.exchange_name not in ("binanceusdm",):
            self._position_mode_dual = True
            logger.info("position mode assumed dual", exchange=self.exchange_name)
            return True
        try:
            get_dual = getattr(self.exchange, "fapiPrivateGetPositionSideDual", None)
            set_dual = getattr(self.exchange, "fapiPrivatePostPositionSideDual", None)
            if not get_dual or not set_dual:
                self._position_mode_dual = True
                return True
            get_result = get_dual()
            resp = await get_result if asyncio.iscoroutine(get_result) else get_result
            # Binance 返回 boolean 或字符串 "true"/"false"
            raw = resp.get("dualSidePosition", False) if isinstance(resp, dict) else False
            is_dual = raw is True or (isinstance(raw, str) and raw.strip().lower() == "true")
            if is_dual:
                self._position_mode_dual = True
                logger.info("position mode is dual", exchange=self.exchange_name)
                return True
            # 尝试切换到双向
            try:
                set_result = set_dual({"dualSidePosition": "true"})
                if asyncio.iscoroutine(set_result):
                    await set_result
                self._position_mode_dual = True
                logger.info("position mode switched to dual", exchange=self.exchange_name)
                return True
            except Exception as switch_err:
                err_str = str(switch_err).lower()
                # -4059: 有持仓时无法切换
                if "-4059" in err_str or "position" in err_str:
                    logger.warning("cannot switch to dual (has positions?), using one-way", error=str(switch_err))
                else:
                    logger.warning("switch to dual failed, using one-way", error=str(switch_err))
                self._position_mode_dual = False
                return False
        except Exception as e:
            logger.warning("ensure_dual_position_mode failed, assuming dual", error=str(e))
            self._position_mode_dual = True
            return True

    def _future_position_side(self, side: OrderSide, position_side: Optional[str]) -> Optional[str]:
        """
        合约下单/止盈止损时是否传 positionSide。
        - 单向持仓（_position_mode_dual=False）: 返回 None（不传）
        - 双向持仓: Binance 返回 LONG/SHORT（大写），OKX 返回 long/short（小写）
        """
        if self.market_type != "future" or self._position_mode_dual is False:
            return None
        if position_side and position_side.upper() in ("LONG", "SHORT"):
            val = position_side.upper()
        else:
            val = "LONG" if side == OrderSide.BUY else "SHORT"
        # OKX CCXT 要求 positionSide 为小写：long / short
        if self.exchange_name == "okx":
            return val.lower()
        return val

    async def ensure_isolated_margin_mode(self, symbol: str) -> None:
        """
        合约：确保使用逐仓保证金模式。
        逐仓优势：单笔亏损不影响整个账户余额，风险隔离。

        ★ 重要改进（2026-02）：
        - 仅在 **成功切换或确认已是逐仓** 时缓存，失败不缓存，下次重试。
        - 如果切换失败且不是"已有持仓"等可忽略原因，**抛出异常阻止下单**，
          避免以全仓模式开仓。
        - Gate：通过 privateFuturesPostSettlePositions 设 leverage（>0 即逐仓），
          不再跳过。

        Raises:
            RuntimeError: 当逐仓模式无法设置且不应继续下单时。
        """
        if self.market_type != "future" or not symbol:
            return
        ccxt_sym = self._ccxt_symbol(symbol) if ":" not in symbol else symbol
        # 仅在确认成功后缓存，失败不缓存以允许重试
        if ccxt_sym in self._margin_isolated_tried:
            return

        # --- Gate：优先 CCXT set_margin_mode，失败再试 leverage API ---
        # Gate 统一账户需显式设为逐仓，否则会以全仓开仓
        if self.exchange_name == "gateio":
            set_margin = getattr(self.exchange, "set_margin_mode", None)
            if set_margin:
                try:
                    result = set_margin("isolated", ccxt_sym)
                    if asyncio.iscoroutine(result):
                        await result
                    logger.info("gate margin set to isolated via set_margin_mode", symbol=ccxt_sym)
                    self._margin_isolated_tried.add(ccxt_sym)
                    return
                except Exception as e1:
                    err_str = str(e1).lower()
                    if "no need" in err_str or "already" in err_str or "same" in err_str:
                        logger.debug("gate already isolated margin", symbol=ccxt_sym)
                        self._margin_isolated_tried.add(ccxt_sym)
                        return
                    if "position" in err_str or "exist" in err_str or "cannot switch" in err_str:
                        logger.warning("gate set isolated margin skipped (has position or cannot switch)", symbol=ccxt_sym, error=str(e1))
                        # 不缓存，平仓后下次开仓可再试
                        return
                    logger.warning("gate set_margin_mode failed, try leverage API", symbol=ccxt_sym, error=str(e1))

            try:
                contract = self._gate_contract_name(symbol)
                # 先查当前持仓杠杆/模式（无持仓时接口可能返回空）
                try:
                    positions = await self.exchange.privateFuturesGetSettlePositionsContract({
                        "settle": DEFAULT_SETTLE,
                        "contract": contract,
                    })
                    pos_data = positions if isinstance(positions, dict) else (positions[0] if positions else {})
                    current_leverage = int(pos_data.get("leverage", 0) or 0)
                    current_mode = (pos_data.get("mode") or "").lower()
                    if current_leverage > 0 and current_mode not in ("cross", "cross_margin"):
                        logger.debug("gate already isolated margin (leverage>0)", symbol=ccxt_sym, leverage=current_leverage)
                        self._margin_isolated_tried.add(ccxt_sym)
                        return
                except Exception:
                    pass

                leverage_val = DEFAULT_LEVERAGE_FALLBACK
                await self.exchange.privateFuturesPostSettlePositions({
                    "settle": DEFAULT_SETTLE,
                    "contract": contract,
                    "leverage": str(leverage_val),
                })
                logger.info("gate margin set to isolated via leverage API", symbol=ccxt_sym, leverage=leverage_val)
                self._margin_isolated_tried.add(ccxt_sym)
            except Exception as e:
                err_str = str(e).lower()
                if "position" in err_str or "exist" in err_str:
                    logger.warning("gate set isolated margin skipped (has position)", symbol=ccxt_sym, error=str(e))
                    # 不缓存，平仓后下次可再试
                else:
                    logger.error("gate set isolated margin FAILED", symbol=ccxt_sym, error=str(e))
                    raise RuntimeError(
                        f"无法为 {ccxt_sym} 设置逐仓模式(Gate)，拒绝以全仓模式下单: {e}"
                    )
            return

        # --- OKX：通过 leverage API 设 mgnMode=isolated（需同时传 lever） ---
        if self.exchange_name == "okx":
            try:
                # 先查当前杠杆和保证金模式
                await self.exchange.load_markets()
                inst_id = self.exchange.market_id(ccxt_sym)
                lev_info = await self.exchange.privateGetAccountLeverageInfo({
                    "instId": inst_id,
                    "mgnMode": "isolated",
                })
                data = lev_info.get("data", [])
                if data:
                    current_lever = data[0].get("lever", str(DEFAULT_LEVERAGE_FALLBACK))
                    current_mgn = data[0].get("mgnMode", "")
                    if current_mgn == "isolated":
                        logger.debug("okx already isolated margin", symbol=ccxt_sym, lever=current_lever)
                        self._margin_isolated_tried.add(ccxt_sym)
                        return
                else:
                    current_lever = str(DEFAULT_LEVERAGE_FALLBACK)

                # 设为逐仓，保持原有杠杆
                await self.exchange.privatePostAccountSetLeverage({
                    "instId": inst_id,
                    "mgnMode": "isolated",
                    "lever": str(current_lever),
                })
                logger.info("okx margin set to isolated", symbol=ccxt_sym, lever=current_lever)
                self._margin_isolated_tried.add(ccxt_sym)
            except Exception as e:
                err_str = str(e).lower()
                if "no need" in err_str or "already" in err_str:
                    logger.debug("okx margin already isolated", symbol=ccxt_sym)
                    self._margin_isolated_tried.add(ccxt_sym)
                elif "position" in err_str or "exist" in err_str:
                    # 已有持仓无法切换，缓存但警告
                    logger.warning("okx set isolated margin skipped (has position)", symbol=ccxt_sym, error=str(e))
                    self._margin_isolated_tried.add(ccxt_sym)
                else:
                    logger.error("okx set isolated margin FAILED", symbol=ccxt_sym, error=str(e))
                    raise RuntimeError(
                        f"无法为 {ccxt_sym} 设置逐仓模式(OKX)，拒绝以全仓模式下单: {e}"
                    )
            return

        # --- Binance 及其他：用 CCXT 统一接口 ---
        set_margin = getattr(self.exchange, "set_margin_mode", None)
        if not set_margin:
            logger.warning("exchange has no set_margin_mode method", exchange=self.exchange_name, symbol=ccxt_sym)
            return
        try:
            result = set_margin("isolated", ccxt_sym)
            if asyncio.iscoroutine(result):
                await result
            logger.info("margin mode set to isolated", exchange=self.exchange_name, symbol=ccxt_sym)
            self._margin_isolated_tried.add(ccxt_sym)
        except Exception as e:
            err_str = str(e).lower()
            # Binance -4046: No need to change margin type（已是逐仓）
            if "-4046" in err_str or "no need" in err_str:
                logger.debug("margin already isolated or unchanged", symbol=ccxt_sym)
                self._margin_isolated_tried.add(ccxt_sym)
            elif "-4048" in err_str or "exist" in err_str or "position" in err_str:
                # 已有持仓无法切换 margin type — 可能持仓已是全仓，但无法改变
                # 缓存以避免重复报错，但打 warning
                logger.warning(
                    "cannot switch to isolated: existing position in cross margin",
                    exchange=self.exchange_name, symbol=ccxt_sym, error=str(e),
                )
                self._margin_isolated_tried.add(ccxt_sym)
            else:
                # 未知错误：不缓存，抛异常阻止以全仓模式下单
                logger.error(
                    "set margin to isolated FAILED, refusing to place order in cross margin",
                    exchange=self.exchange_name, symbol=ccxt_sym, error=str(e),
                )
                raise RuntimeError(
                    f"无法为 {ccxt_sym} 设置逐仓模式({self.exchange_name})，拒绝以全仓模式下单: {e}"
                )

    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float = 0,
        price: Optional[float] = None,
        position_side: Optional[str] = None,  # LONG / SHORT (双向持仓模式)
        signal_id: Optional[str] = None,      # 关联信号ID（用于 OrderTrade 记录）
        amount_usdt: Optional[float] = None,  # USDT 金额（优先于 quantity，自动换算张数/币数量）
        leverage: Optional[int] = None,        # 杠杆倍数（从信号/策略传入，下单前自动设置）
        stop_loss: Optional[float] = None,     # 止损价（记录到订单）
        take_profit: Optional[float] = None,   # 止盈价（记录到订单）
        trade_type: Optional[str] = "OPEN",    # 交易类型: OPEN/CLOSE/ADD/REDUCE
        close_reason: Optional[str] = None,    # 平仓原因: SL/TP/SIGNAL/MANUAL/LIQUIDATION
        **kwargs,
    ) -> OrderResult:
        """
        创建订单。symbol 可为规范形式 BTC/USDT 或交易所格式，合约会自动转为 CCXT 格式。

        推荐用法（传 amount_usdt，自动换算数量、校验限制）：
            await trader.create_order(symbol, side, OrderType.MARKET, amount_usdt=100, leverage=20)

        兼容用法（传 quantity，调用方自行换算）：
            await trader.create_order(symbol, side, OrderType.MARKET, quantity=0.001)
        """
        order_id = gen_id("ord_")
        db_order_id = None  # 数据库订单ID（如果使用 OrderTradeService）
        ccxt_sym = self._ccxt_symbol(symbol)

        # 如果传了 amount_usdt，自动获取价格并换算数量（处理 contractSize + 限制校验）
        if amount_usdt and amount_usdt > 0:
            try:
                if price and price > 0:
                    calc_price = price
                else:
                    ticker = await self.exchange.fetch_ticker(ccxt_sym)
                    calc_price = float(ticker.get("last") or ticker.get("close") or 0)
                if calc_price <= 0:
                    return self._error_result(order_id, symbol, side, order_type, 0, price, "NO_PRICE", "cannot get price for quantity calculation")
                quantity = await self.usdt_to_quantity(symbol, amount_usdt, calc_price)
            except ValueError as ve:
                return self._error_result(order_id, symbol, side, order_type, 0, price, "AMOUNT_ERROR", str(ve))

        amount = self._amount_precision(ccxt_sym, quantity)
        if amount <= 0:
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "INVALID_AMOUNT", "amount after precision is 0")
        if price is not None:
            price = self._price_precision(ccxt_sym, price)
        
        try:
            # 合约：先确保持仓模式（尝试双向）、再确保逐仓保证金，最后决定是否传 positionSide
            if self.market_type == "future":
                await self.ensure_dual_position_mode()
                await self.ensure_isolated_margin_mode(ccxt_sym)
                # 设置杠杆（从信号/策略传入）
                if leverage and leverage > 0:
                    await self.ensure_leverage(symbol, leverage)
            
            # 如果启用结算/订单服务，先创建订单记录（订单列表、成交记录依赖此）
            # 注意：quantity 可能是合约张数（Gate/OKX），DB 应存币数量
            coin_quantity = self._contracts_to_coins(quantity, symbol)
            if (self._settlement_service or self._order_trade_service) and self._tenant_id and self._account_id:
                db_order_id = await self._create_order_record(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=coin_quantity,
                    price=price,
                    position_side=position_side,
                    signal_id=signal_id,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    leverage=leverage,
                    trade_type=trade_type,
                    close_reason=close_reason,
                )
                if db_order_id:
                    order_id = db_order_id  # 使用数据库订单ID
            
            # 转换订单类型
            ccxt_type = "market" if order_type == OrderType.MARKET else "limit"
            ccxt_side = side.value
            
            # 合约交易参数：仅双向持仓时传 positionSide（单向时不传，参考 old3）
            params = dict(kwargs)
            pos_side = self._future_position_side(side, position_side)
            if pos_side:
                params["positionSide"] = pos_side
            # ★ 平仓单：多数交易所传 reduceOnly 避免开反向仓；Binance 双向持仓模式不允许传 reduceOnly
            if self.market_type == "future" and (trade_type or "OPEN") == "CLOSE":
                if self.exchange_name == "binanceusdm" and pos_side:
                    # Binance Hedge Mode: API 禁止传 reduceOnly，用 positionSide + side 已能标识平仓
                    params.pop("reduceOnly", None)  # 调用方可能从 kwargs 带入，必须移除
                else:
                    params["reduceOnly"] = True
                # Gate 双向（hedge）模式下不允许 close；单向时仅 reduceOnly 亦可减仓，故 Gate 平仓不传 close
                # （若传 close 且账户已为双向会报：close is not allowed in dual-mode）
            # Binance 非平仓时若误带了 reduceOnly 则移除
            if self.exchange_name == "binanceusdm" and (trade_type or "OPEN") != "CLOSE" and "reduceOnly" in params:
                params.pop("reduceOnly", None)
            # OKX 合约：下单必须传 tdMode=isolated 才会以逐仓成交，否则按账户默认（多为全仓）
            if self.exchange_name == "okx" and self.market_type == "future":
                params["tdMode"] = "isolated"

            logger.info(
                "creating order",
                order_id=order_id,
                symbol=symbol,
                side=ccxt_side,
                type=ccxt_type,
                quantity=quantity,
                price=price,
                params=params,
            )
            
            # 调用 ccxt 下单（网络瞬时错误时有限重试）
            response = None
            for attempt in range(NETWORK_RETRIES + 1):
                try:
                    if order_type == OrderType.MARKET:
                        response = await self.exchange.create_order(
                            symbol=ccxt_sym,
                            type=ccxt_type,
                            side=ccxt_side,
                            amount=amount,
                            params=params,
                        )
                    else:
                        if price is None:
                            raise ValueError("Price is required for limit orders")
                        response = await self.exchange.create_order(
                            symbol=ccxt_sym,
                            type=ccxt_type,
                            side=ccxt_side,
                            amount=amount,
                            price=price,
                            params=params,
                        )
                    break
                except ccxt.NetworkError as e:
                    if attempt < NETWORK_RETRIES:
                        logger.warning(
                            "create_order network error, retrying",
                            attempt=attempt + 1,
                            max_retries=NETWORK_RETRIES,
                            error=str(e),
                        )
                        await asyncio.sleep(NETWORK_RETRY_DELAY)
                    else:
                        raise
            
            # 解析响应（对外仍用原始 symbol）
            result = self._parse_order_response(order_id, symbol, side, order_type, amount, price, response)
            
            # 市价单：若交易所异步返回（filled=0/status=open），短暂等待后重新查询
            if (
                order_type == OrderType.MARKET
                and result.exchange_order_id
                and result.status not in (OrderStatus.FILLED, OrderStatus.PARTIAL)
                and (result.filled_quantity or 0) <= 0
            ):
                for _retry in range(MARKET_ORDER_CONFIRM_RETRIES):
                    await asyncio.sleep(MARKET_ORDER_CONFIRM_INTERVAL)
                    try:
                        fetched = await self.exchange.fetch_order(result.exchange_order_id, ccxt_sym)
                        result = self._parse_order_response(order_id, symbol, side, order_type, amount, price, fetched)
                        if result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL) or (result.filled_quantity or 0) > 0:
                            break
                    except Exception as e:
                        logger.debug("market order confirm retry failed", retry=_retry + 1, error=str(e))
                else:
                    # 所有重试都没确认成交，避免“假成功”：置为未确认并带提示
                    logger.warning(
                        "market order not confirmed after retries",
                        order_id=order_id,
                        exchange_order_id=result.exchange_order_id,
                        status=result.status.value,
                        retries=MARKET_ORDER_CONFIRM_RETRIES,
                    )
                    result = OrderResult(
                        order_id=result.order_id,
                        exchange_order_id=result.exchange_order_id,
                        symbol=result.symbol,
                        side=result.side,
                        order_type=result.order_type,
                        status=OrderStatus.OPEN,
                        requested_quantity=result.requested_quantity,
                        requested_price=result.requested_price,
                        filled_quantity=0.0,
                        filled_price=result.filled_price or 0.0,
                        commission=result.commission,
                        commission_asset=result.commission_asset,
                        error_code="UNCONFIRMED",
                        error_message="订单未在重试期内确认成交，请稍后在交易所查询",
                        raw_response=result.raw_response,
                    )

            # ★ 价格和手续费补偿：如果已成交但价格或手续费为 0，通过 fetch_order_trades 获取真实数据
            if (
                result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
                and (result.filled_quantity or 0) > 0
                and result.exchange_order_id
                and ((result.commission or 0) == 0 or (result.filled_price or 0) == 0)
            ):
                try:
                    await asyncio.sleep(0.5)  # 等待成交记录可查（Gate 可能需要更长时间）
                    trades = await self.exchange.fetch_order_trades(result.exchange_order_id, ccxt_sym)
                    if trades:
                        # 如果原手续费为0，才从成交记录中提取
                        need_fee = (result.commission or 0) == 0
                        total_fee = result.commission or 0.0
                        fee_currency = result.commission_asset or ""
                        total_cost = 0.0
                        total_qty = 0.0
                        
                        for t in trades:
                            # 提取手续费（仅在需要时）
                            if need_fee:
                                t_fee = t.get("fee", {})
                                if t_fee and isinstance(t_fee, dict) and t_fee.get("cost") is not None:
                                    total_fee += abs(float(t_fee["cost"]))
                                    if not fee_currency:
                                        fee_currency = t_fee.get("currency", "")
                            
                            # 检查 info 中的原始手续费字段（所有交易所）
                            if need_fee and total_fee == 0:
                                t_info = t.get("info", {})
                                if isinstance(t_info, dict):
                                    # 通用手续费字段（Binance/OKX/Gate 都支持）
                                    raw_c = (
                                        t_info.get("commission") or      # Binance futures
                                        t_info.get("fee") or             # 通用
                                        t_info.get("fill_fee") or        # Gate 特有
                                        t_info.get("taker_fee") or       # Gate 特有
                                        t_info.get("maker_fee") or       # Gate 特有
                                        t_info.get("feeAmt") or          # OKX 可能
                                        t_info.get("fee_amt") or         # OKX 可能
                                        t_info.get("n")                  # Gate 可能
                                    )
                                    if raw_c is not None:
                                        try:
                                            total_fee += abs(float(raw_c))
                                        except (ValueError, TypeError):
                                            # 尝试字符串转换
                                            try:
                                                total_fee += abs(float(str(raw_c).strip()))
                                            except (ValueError, TypeError):
                                                pass
                                    if not fee_currency:
                                        fee_currency = (
                                            t_info.get("commissionAsset") or      # Binance
                                            t_info.get("feeCurrency") or          # 通用
                                            t_info.get("fee_currency") or         # Gate
                                            t_info.get("feeCcy") or               # OKX 可能
                                            ""
                                        )
                            
                            # 提取价格（用于计算加权平均价）
                            trade_price = t.get("price")
                            trade_qty = t.get("amount") or t.get("quantity")
                            if trade_price and trade_qty:
                                try:
                                    total_cost += float(trade_price) * float(trade_qty)
                                    total_qty += float(trade_qty)
                                except (ValueError, TypeError):
                                    pass
                        
                        # 计算加权平均价（如果原价格为 0）
                        new_filled_price = result.filled_price
                        if (result.filled_price or 0) == 0 and total_qty > 0:
                            new_filled_price = total_cost / total_qty
                        
                        # 更新结果
                        if total_fee > 0 or new_filled_price > 0:
                            result = OrderResult(
                                order_id=result.order_id,
                                exchange_order_id=result.exchange_order_id,
                                symbol=result.symbol,
                                side=result.side,
                                order_type=result.order_type,
                                status=result.status,
                                requested_quantity=result.requested_quantity,
                                requested_price=result.requested_price,
                                filled_quantity=result.filled_quantity,
                                filled_price=new_filled_price if new_filled_price > 0 else result.filled_price,
                                commission=total_fee if total_fee > 0 else result.commission,
                                commission_asset=fee_currency or result.commission_asset,
                                raw_response=result.raw_response,
                            )
                            if total_fee > 0:
                                logger.info("fee fetched from trades", commission=total_fee, currency=fee_currency)
                            if new_filled_price > 0:
                                logger.info("price fetched from trades", filled_price=new_filled_price)
                except Exception as e:
                    logger.debug("fetch_order_trades for price/fee failed (non-critical)", error=str(e))

            logger.info(
                "order created",
                order_id=order_id,
                exchange_order_id=result.exchange_order_id,
                status=result.status.value,
                filled_quantity=result.filled_quantity,
                filled_price=result.filled_price,
                commission=result.commission,
            )
            
            # 更新订单状态并结算（支持 settlement_service 或 order_trade_service）
            # 注意：result.filled_quantity 可能是合约张数，需转为币数量存入 DB
            if (self._settlement_service or self._order_trade_service) and db_order_id:
                from copy import copy as _copy
                db_result = _copy(result)
                db_result.filled_quantity = self._contracts_to_coins(result.filled_quantity, symbol)
                db_result.requested_quantity = coin_quantity
                await self._update_order_after_submit(
                    order_id=db_order_id,
                    exchange_order_id=result.exchange_order_id,
                    result=db_result,
                    position_side=params.get("positionSide", "NONE"),
                )
            
            return result
            
        except ccxt.InsufficientFunds as e:
            logger.error("insufficient funds", order_id=order_id, error=str(e))
            if (self._settlement_service or self._order_trade_service) and db_order_id:
                await self._fail_order_record(db_order_id, "INSUFFICIENT_FUNDS", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "INSUFFICIENT_FUNDS", str(e))
        
        except ccxt.InvalidOrder as e:
            logger.error("invalid order", order_id=order_id, error=str(e))
            if (self._settlement_service or self._order_trade_service) and db_order_id:
                await self._fail_order_record(db_order_id, "INVALID_ORDER", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "INVALID_ORDER", str(e))
        
        except ccxt.OrderNotFound as e:
            logger.error("order not found", order_id=order_id, error=str(e))
            if (self._settlement_service or self._order_trade_service) and db_order_id:
                await self._fail_order_record(db_order_id, "ORDER_NOT_FOUND", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "ORDER_NOT_FOUND", str(e))
        
        except RuntimeError as e:
            # ensure_isolated_margin_mode 等前置检查抛出的逐仓设置失败
            logger.error("pre-order check failed (e.g. margin mode)", order_id=order_id, error=str(e))
            if (self._settlement_service or self._order_trade_service) and db_order_id:
                await self._fail_order_record(db_order_id, "MARGIN_MODE_ERROR", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "MARGIN_MODE_ERROR", str(e))
        
        except ccxt.NetworkError as e:
            logger.error("network error", order_id=order_id, error=str(e))
            if (self._settlement_service or self._order_trade_service) and db_order_id:
                await self._fail_order_record(db_order_id, "NETWORK_ERROR", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "NETWORK_ERROR", str(e))
        
        except ccxt.ExchangeError as e:
            logger.error("exchange error", order_id=order_id, error=str(e))
            if (self._settlement_service or self._order_trade_service) and db_order_id:
                await self._fail_order_record(db_order_id, "EXCHANGE_ERROR", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "EXCHANGE_ERROR", str(e))
        
        except Exception as e:
            logger.error("unexpected error", order_id=order_id, error=str(e))
            if (self._settlement_service or self._order_trade_service) and db_order_id:
                await self._fail_order_record(db_order_id, "UNKNOWN_ERROR", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "UNKNOWN_ERROR", str(e))
    
    # ============ Gate 仓位级止盈止损 ============

    def _gate_contract_name(self, symbol: str) -> str:
        """BTC/USDT → BTC_USDT（Gate 合约名格式）"""
        from libs.exchange.utils import normalize_symbol
        s = normalize_symbol(symbol, "binance")  # 确保 BASE/QUOTE
        return s.replace("/", "_").split(":")[0]

    async def _gate_set_position_sl_tp(
        self,
        symbol: str,
        position_side: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Gate 统一账户：通过 price_orders API 设置仓位级止盈止损。
        显示在仓位页面（非委托单列表）。

        Args:
            symbol: 交易对（BTC/USDT）
            position_side: LONG / SHORT
            stop_loss: 止损触发价
            take_profit: 止盈触发价
        Returns:
            {"sl": OrderResult, "tp": OrderResult}
        """
        contract = self._gate_contract_name(symbol)
        ccxt_sym = self._ccxt_symbol(symbol)
        is_long = position_side.upper() == "LONG"
        order_type = "close-long-position" if is_long else "close-short-position"
        auto_size = "close_long" if is_long else "close_short"
        # 触发价必须按交易所价格精度对齐
        if stop_loss is not None:
            stop_loss = self._price_precision(ccxt_sym, stop_loss)
        if take_profit is not None:
            take_profit = self._price_precision(ccxt_sym, take_profit)
        results: Dict[str, Any] = {}

        for label, trigger_price, rule in [
            ("sl", stop_loss, 2 if is_long else 1),   # 多头止损: price<=trigger; 空头止损: price>=trigger
            ("tp", take_profit, 1 if is_long else 2),  # 多头止盈: price>=trigger; 空头止盈: price<=trigger
        ]:
            if trigger_price is None:
                continue
            order_id = gen_id(f"{label}_")
            try:
                logger.info(
                    f"gate setting position {label}",
                    order_id=order_id,
                    symbol=symbol,
                    position_side=position_side,
                    trigger_price=trigger_price,
                    rule=rule,
                    order_type=order_type,
                )
                res = await self.exchange.privateFuturesPostSettlePriceOrders({
                    "settle": DEFAULT_SETTLE,
                    "initial": {
                        "contract": contract,
                        "size": GATE_CLOSE_ALL_SIZE,
                        "price": GATE_MARKET_PRICE,
                        "tif": "ioc",
                        "auto_size": auto_size,
                    },
                    "trigger": {
                        "strategy_type": 0,
                        "price_type": 0,  # 最新成交价
                        "price": str(trigger_price),
                        "rule": rule,
                    },
                    "order_type": order_type,
                })
                exchange_id = res.get("id") if isinstance(res, dict) else str(res)
                logger.info(f"gate position {label} set", order_id=order_id, exchange_id=exchange_id)
                results[label] = OrderResult(
                    order_id=order_id,
                    exchange_order_id=str(exchange_id),
                    symbol=symbol,
                    side=OrderSide.SELL if is_long else OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    status=OrderStatus.OPEN,
                    requested_quantity=0,
                    requested_price=trigger_price,
                    raw_response=res if isinstance(res, dict) else {"id": res},
                )
            except Exception as e:
                logger.error(f"gate set position {label} failed", order_id=order_id, error=str(e))
                results[label] = self._error_result(
                    order_id, symbol,
                    OrderSide.SELL if is_long else OrderSide.BUY,
                    OrderType.MARKET, 0, trigger_price,
                    f"{label.upper()}_FAILED", str(e),
                )
        return results

    # ============ OKX 仓位级止盈止损 ============

    def _okx_inst_id(self, symbol: str) -> str:
        """BTC/USDT → BTC-USDT-SWAP（OKX 永续合约 instId 格式）"""
        from libs.exchange.utils import normalize_symbol
        s = normalize_symbol(symbol, "binance")  # 确保 BASE/QUOTE
        base_quote = s.split(":")[0]  # 去掉 :USDT
        return base_quote.replace("/", "-") + "-SWAP"

    async def _okx_set_position_sl_tp(
        self,
        symbol: str,
        position_side: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        OKX：通过 algo order API 设置仓位级止盈止损（ordType=conditional）。
        一次请求可同时设 SL + TP，触发一个自动撤另一个。显示在仓位页面。

        Args:
            symbol: 交易对（BTC/USDT）
            position_side: LONG / SHORT
            stop_loss: 止损触发价
            take_profit: 止盈触发价
            quantity: 仓位数量（张数）。双向持仓必传，单向模式可用 closeFraction 代替。
        Returns:
            {"sl": OrderResult, "tp": OrderResult} 或单项
        """
        inst_id = self._okx_inst_id(symbol)
        ccxt_sym = self._ccxt_symbol(symbol)
        is_long = position_side.upper() == "LONG"
        close_side = "sell" if is_long else "buy"

        # 确保已检测持仓模式
        await self.ensure_dual_position_mode()

        # 根据持仓模式决定 posSide
        if self._position_mode_dual:
            pos_side = "long" if is_long else "short"
        else:
            pos_side = "net"

        # 价格精度对齐
        if stop_loss is not None:
            stop_loss = self._price_precision(ccxt_sym, stop_loss)
        if take_profit is not None:
            take_profit = self._price_precision(ccxt_sym, take_profit)

        order_id = gen_id("sltp_")
        results: Dict[str, Any] = {}

        try:
            # OKX oco (One-Cancels-Other): 同时设 SL + TP，触发一个自动撤另一个。
            # closeFraction=1 → 全仓止盈止损，显示在仓位页面（closeOrderAlgo）。
            # 注意：ordType=conditional + closeFraction 只能存 SL 或 TP 其一；oco 可同时包含两者。
            algo_params: Dict[str, Any] = {
                "instId": inst_id,
                "tdMode": "isolated",
                "side": close_side,
                "posSide": pos_side,
                "ordType": "oco",
                "closeFraction": OKX_CLOSE_FULL_FRACTION,
            }
            if stop_loss is not None:
                algo_params["slTriggerPx"] = str(stop_loss)
                algo_params["slOrdPx"] = OKX_MARKET_PRICE
                algo_params["slTriggerPxType"] = "last"
            if take_profit is not None:
                algo_params["tpTriggerPx"] = str(take_profit)
                algo_params["tpOrdPx"] = OKX_MARKET_PRICE
                algo_params["tpTriggerPxType"] = "last"

            logger.info(
                "okx setting position sl/tp",
                order_id=order_id,
                symbol=symbol,
                position_side=position_side,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

            res = await self.exchange.privatePostTradeOrderAlgo(algo_params)

            # OKX 返回 {"code":"0","data":[{"algoId":"xxx","sCode":"0","sMsg":""}],"msg":""}
            data = res.get("data", [{}])
            algo_id = data[0].get("algoId", "") if data else ""
            s_code = data[0].get("sCode", "") if data else ""
            s_msg = data[0].get("sMsg", "") if data else ""

            if s_code == "0" or res.get("code") == "0":
                logger.info("okx position sl/tp set", order_id=order_id, algo_id=algo_id)
                result = OrderResult(
                    order_id=order_id,
                    exchange_order_id=str(algo_id),
                    symbol=symbol,
                    side=OrderSide.SELL if is_long else OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    status=OrderStatus.OPEN,
                    requested_quantity=0,
                    requested_price=stop_loss or take_profit,
                    raw_response=res,
                )
                if stop_loss is not None:
                    results["sl"] = result
                if take_profit is not None:
                    results["tp"] = result
            else:
                err = f"sCode={s_code} sMsg={s_msg}"
                logger.error("okx set position sl/tp failed", order_id=order_id, error=err)
                fail = self._error_result(
                    order_id, symbol,
                    OrderSide.SELL if is_long else OrderSide.BUY,
                    OrderType.MARKET, 0, stop_loss or take_profit,
                    "SLTP_FAILED", err,
                )
                if stop_loss is not None:
                    results["sl"] = fail
                if take_profit is not None:
                    results["tp"] = fail

        except Exception as e:
            logger.error("okx set position sl/tp error", order_id=order_id, error=str(e))
            fail = self._error_result(
                order_id, symbol,
                OrderSide.SELL if is_long else OrderSide.BUY,
                OrderType.MARKET, 0, stop_loss or take_profit,
                "SLTP_FAILED", str(e),
            )
            if stop_loss is not None:
                results["sl"] = fail
            if take_profit is not None:
                results["tp"] = fail

        return results

    # ============ 通用止盈止损 ============

    async def set_stop_loss(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_price: float,
        position_side: Optional[str] = None,
    ) -> OrderResult:
        """
        设置止损单。
        - Gate: 仓位级止损（price_orders API, 显示在仓位页面）
        - OKX: 仓位级止损（algo order API, 显示在仓位页面）
        - Binance: STOP_MARKET 条件委托单（Binance 无仓位级 SL/TP API，网页端也是创建条件单）

        Args:
            symbol: 交易对（规范形式或 CCXT 格式均可）
            side: 平仓方向 (做多持仓用SELL平仓，做空持仓用BUY平仓)
            quantity: 数量
            stop_price: 触发价格
            position_side: 持仓方向 (LONG/SHORT)
        """
        pos_side = (position_side or ("LONG" if side == OrderSide.SELL else "SHORT")).upper()

        # Gate 统一账户：仓位级止损
        if self.exchange_name == "gateio" and self.market_type == "future":
            results = await self._gate_set_position_sl_tp(symbol, pos_side, stop_loss=stop_price)
            return results.get("sl", self._error_result(gen_id("sl_"), symbol, side, OrderType.MARKET, quantity, stop_price, "SL_FAILED", "no result"))

        # OKX：仓位级止损（algo order）
        if self.exchange_name == "okx" and self.market_type == "future":
            results = await self._okx_set_position_sl_tp(symbol, pos_side, stop_loss=stop_price, quantity=quantity)
            return results.get("sl", self._error_result(gen_id("sl_"), symbol, side, OrderType.MARKET, quantity, stop_price, "SL_FAILED", "no result"))

        order_id = gen_id("sl_")
        ccxt_sym = self._ccxt_symbol(symbol)
        amount = self._amount_precision(ccxt_sym, quantity)
        if amount <= 0:
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, stop_price, "INVALID_AMOUNT", "amount after precision is 0")
        stop_price = self._price_precision(ccxt_sym, stop_price)
        
        try:
            if self.market_type == "future":
                await self.ensure_dual_position_mode()
                await self.ensure_isolated_margin_mode(ccxt_sym)
            params: Dict[str, Any] = {
                "stopPrice": stop_price,
            }
            
            if self.market_type == "future":
                pos_side = (position_side or ("LONG" if side == OrderSide.SELL else "SHORT")).upper()
                if self._position_mode_dual and pos_side in ("LONG", "SHORT"):
                    params["positionSide"] = pos_side
                if self.exchange_name == "binanceusdm":
                    params["workingType"] = "MARK_PRICE"
                else:
                    params["reduceOnly"] = True
            else:
                params["reduceOnly"] = True
            
            logger.info(
                "setting stop loss",
                order_id=order_id,
                symbol=symbol,
                side=side.value,
                quantity=amount,
                stop_price=stop_price,
                params=params,
            )
            
            response = await self.exchange.create_order(
                symbol=ccxt_sym, type="STOP_MARKET", side=side.value, amount=amount, params=params,
            )
            
            logger.info("stop loss set", order_id=order_id, exchange_id=response.get("id"))
            
            return OrderResult(
                order_id=order_id,
                exchange_order_id=response.get("id"),
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
                requested_quantity=quantity,
                requested_price=stop_price,
                raw_response=response,
            )
            
        except ccxt.ExchangeError as e:
            logger.error("set stop loss failed (exchange)", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, stop_price, "SL_FAILED", str(e))
        except Exception as e:
            logger.error("set stop loss failed", order_id=order_id, error=str(e), error_type=type(e).__name__)
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, stop_price, "SL_FAILED", str(e))
    
    async def set_take_profit(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        take_profit_price: float,
        position_side: Optional[str] = None,
    ) -> OrderResult:
        """
        设置止盈单。
        - Gate: 仓位级止盈（price_orders API, 显示在仓位页面）
        - OKX: 仓位级止盈（algo order API, 显示在仓位页面）
        - Binance: TAKE_PROFIT_MARKET 条件委托单（Binance 无仓位级 SL/TP API，网页端也是创建条件单）

        Args:
            symbol: 交易对（规范形式或 CCXT 格式均可）
            side: 平仓方向 (做多持仓用SELL平仓，做空持仓用BUY平仓)
            quantity: 数量
            take_profit_price: 触发价格
            position_side: 持仓方向 (LONG/SHORT)
        """
        pos_side = (position_side or ("LONG" if side == OrderSide.SELL else "SHORT")).upper()

        # Gate 统一账户：仓位级止盈
        if self.exchange_name == "gateio" and self.market_type == "future":
            results = await self._gate_set_position_sl_tp(symbol, pos_side, take_profit=take_profit_price)
            return results.get("tp", self._error_result(gen_id("tp_"), symbol, side, OrderType.MARKET, quantity, take_profit_price, "TP_FAILED", "no result"))

        # OKX：仓位级止盈（algo order）
        if self.exchange_name == "okx" and self.market_type == "future":
            results = await self._okx_set_position_sl_tp(symbol, pos_side, take_profit=take_profit_price, quantity=quantity)
            return results.get("tp", self._error_result(gen_id("tp_"), symbol, side, OrderType.MARKET, quantity, take_profit_price, "TP_FAILED", "no result"))

        order_id = gen_id("tp_")
        ccxt_sym = self._ccxt_symbol(symbol)
        amount = self._amount_precision(ccxt_sym, quantity)
        if amount <= 0:
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, take_profit_price, "TP_FAILED", "amount after precision is 0")
        take_profit_price = self._price_precision(ccxt_sym, take_profit_price)
        
        try:
            if self.market_type == "future":
                await self.ensure_dual_position_mode()
                await self.ensure_isolated_margin_mode(ccxt_sym)
            params: Dict[str, Any] = {
                "stopPrice": take_profit_price,
            }
            
            if self.market_type == "future":
                pos_side = (position_side or ("LONG" if side == OrderSide.SELL else "SHORT")).upper()
                if self._position_mode_dual and pos_side in ("LONG", "SHORT"):
                    params["positionSide"] = pos_side
                if self.exchange_name == "binanceusdm":
                    params["workingType"] = "MARK_PRICE"
                else:
                    params["reduceOnly"] = True
            else:
                params["reduceOnly"] = True
            
            logger.info(
                "setting take profit",
                order_id=order_id,
                symbol=symbol,
                side=side.value,
                quantity=amount,
                take_profit_price=take_profit_price,
                params=params,
            )
            
            response = await self.exchange.create_order(
                symbol=ccxt_sym, type="TAKE_PROFIT_MARKET", side=side.value, amount=amount, params=params,
            )
            
            logger.info("take profit set", order_id=order_id, exchange_id=response.get("id"))
            
            return OrderResult(
                order_id=order_id,
                exchange_order_id=response.get("id"),
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
                requested_quantity=quantity,
                requested_price=take_profit_price,
                raw_response=response,
            )
            
        except ccxt.ExchangeError as e:
            logger.error("set take profit failed (exchange)", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, take_profit_price, "TP_FAILED", str(e))
        except Exception as e:
            logger.error("set take profit failed", order_id=order_id, error=str(e), error_type=type(e).__name__)
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, take_profit_price, "TP_FAILED", str(e))
    
    async def set_sl_tp(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        position_side: Optional[str] = None,
    ) -> Dict[str, OrderResult]:
        """
        同时设置止盈止损。
        OKX 支持一次请求同时设 SL+TP（触发一个自动撤另一个）；
        Gate 分两次请求；Binance 等分两次请求。
        
        Args:
            symbol: 交易对
            side: 开仓方向 (BUY=做多, SELL=做空)
            quantity: 数量
            stop_loss: 止损价
            take_profit: 止盈价
            position_side: 持仓方向
            
        Returns:
            {"sl": OrderResult, "tp": OrderResult}
        """
        results = {}
        
        # 持仓方向
        pos_side = position_side or ("LONG" if side == OrderSide.BUY else "SHORT")

        # OKX：一次请求同时设 SL + TP（触发一个自动撤另一个）
        if self.exchange_name == "okx" and self.market_type == "future" and (stop_loss or take_profit):
            return await self._okx_set_position_sl_tp(symbol, pos_side, stop_loss=stop_loss, take_profit=take_profit, quantity=quantity)

        # Gate：分别设 SL 和 TP（各一次请求）
        if self.exchange_name == "gateio" and self.market_type == "future" and (stop_loss or take_profit):
            return await self._gate_set_position_sl_tp(symbol, pos_side, stop_loss=stop_loss, take_profit=take_profit)
        
        # 平仓方向与开仓方向相反
        close_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
        
        if stop_loss:
            results["sl"] = await self.set_stop_loss(
                symbol=symbol,
                side=close_side,
                quantity=quantity,
                stop_price=stop_loss,
                position_side=pos_side,
            )
        
        if take_profit:
            results["tp"] = await self.set_take_profit(
                symbol=symbol,
                side=close_side,
                quantity=quantity,
                take_profit_price=take_profit,
                position_side=pos_side,
            )
        
        return results

    async def cancel_order(self, order_id: str, symbol: str) -> OrderResult:
        """取消订单。symbol 可为规范形式，合约时会转为 CCXT 格式。"""
        try:
            ccxt_sym = self._ccxt_symbol(symbol)
            response = await self.exchange.cancel_order(order_id, ccxt_sym)
            
            return OrderResult(
                order_id=order_id,
                exchange_order_id=response.get("id"),
                symbol=symbol,
                side=OrderSide(response.get("side", "buy")),
                order_type=OrderType.LIMIT,
                status=OrderStatus.CANCELED,
                requested_quantity=response.get("amount", 0),
                requested_price=response.get("price"),
                filled_quantity=response.get("filled", 0),
                filled_price=response.get("average", 0),
                raw_response=response,
            )
            
        except Exception as e:
            logger.error("cancel order failed", order_id=order_id, error=str(e))
            return OrderResult(
                order_id=order_id,
                exchange_order_id=order_id,
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.FAILED,
                requested_quantity=0,
                requested_price=None,
                error_code="CANCEL_FAILED",
                error_message=str(e),
            )
    
    async def cancel_all_open_orders(self, symbol: str) -> Dict[str, Any]:
        """
        取消指定交易对的所有未成交条件委托单（STOP_MARKET / TAKE_PROFIT_MARKET 等）。

        应用场景：持仓已被止损/止盈/手动平仓，但另一侧条件单仍在。
        - Binance: fetch_open_orders → 逐个 cancel（包括 STOP_MARKET, TAKE_PROFIT_MARKET）
        - Gate / OKX: 仓位级 SL/TP 随仓位关闭自动撤销，一般无需手动处理，
          但以防万一也做一次 fetch + cancel。

        Returns:
            {"cancelled": int, "errors": int, "details": [...]}
        """
        ccxt_sym = self._ccxt_symbol(symbol)
        cancelled = 0
        errors = 0
        details = []

        try:
            # 查询所有未成交的委托单（包括条件单）
            open_orders = await self.exchange.fetch_open_orders(ccxt_sym)

            for order in open_orders or []:
                order_id = order.get("id")
                order_type = (order.get("type") or "").upper()
                # 只取消条件/止盈止损类委托单，不取消普通限价单
                conditional_types = {
                    "STOP_MARKET", "TAKE_PROFIT_MARKET",
                    "STOP", "TAKE_PROFIT",
                    "STOP_LOSS", "STOP_LOSS_LIMIT",
                }
                if order_type not in conditional_types:
                    # 如果有 stopPrice 也算条件单
                    if not order.get("stopPrice"):
                        continue

                try:
                    await self.exchange.cancel_order(order_id, ccxt_sym)
                    cancelled += 1
                    details.append({
                        "order_id": order_id,
                        "type": order_type,
                        "side": order.get("side"),
                        "status": "cancelled",
                    })
                    logger.info("cancelled conditional order",
                                symbol=symbol, order_id=order_id, type=order_type)
                except Exception as e:
                    errors += 1
                    details.append({
                        "order_id": order_id,
                        "type": order_type,
                        "status": "error",
                        "error": str(e),
                    })
                    logger.warning("cancel conditional order failed",
                                   symbol=symbol, order_id=order_id, error=str(e))

        except Exception as e:
            logger.error("fetch open orders failed", symbol=symbol, error=str(e))
            return {"cancelled": 0, "errors": 1, "details": [{"error": str(e)}]}

        if cancelled > 0:
            logger.info("conditional orders cleanup done",
                        symbol=symbol, cancelled=cancelled, errors=errors)

        return {"cancelled": cancelled, "errors": errors, "details": details}

    async def get_order(self, order_id: str, symbol: str) -> OrderResult:
        """查询订单。symbol 可为规范形式，合约时会转为 CCXT 格式。"""
        try:
            ccxt_sym = self._ccxt_symbol(symbol)
            response = await self.exchange.fetch_order(order_id, ccxt_sym)
            
            status_map = {
                "open": OrderStatus.OPEN,
                "closed": OrderStatus.FILLED,
                "canceled": OrderStatus.CANCELED,
                "expired": OrderStatus.EXPIRED,
                "rejected": OrderStatus.REJECTED,
            }
            
            return OrderResult(
                order_id=order_id,
                exchange_order_id=response.get("id"),
                symbol=symbol,
                side=OrderSide(response.get("side", "buy")),
                order_type=OrderType.MARKET if response.get("type") == "market" else OrderType.LIMIT,
                status=status_map.get(response.get("status"), OrderStatus.PENDING),
                requested_quantity=response.get("amount", 0),
                requested_price=response.get("price"),
                filled_quantity=response.get("filled", 0),
                filled_price=response.get("average", 0),
                commission=response.get("fee", {}).get("cost", 0) if response.get("fee") else 0,
                commission_asset=response.get("fee", {}).get("currency", "") if response.get("fee") else "",
                raw_response=response,
            )
            
        except Exception as e:
            logger.error("get order failed", order_id=order_id, error=str(e))
            return OrderResult(
                order_id=order_id,
                exchange_order_id=order_id,
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.FAILED,
                requested_quantity=0,
                requested_price=None,
                error_code="QUERY_FAILED",
                error_message=str(e),
            )
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """查询余额。Gate 统一账户通过 spot 端点获取统一余额。"""
        try:
            # Gate 统一账户：swap 端点返回空，需用 spot 端点查统一余额
            params: Dict[str, Any] = {}
            if self.exchange_name == "gateio" and self.market_type == "future":
                params["type"] = "spot"
            response = await self.exchange.fetch_balance(params)
            
            # 从 CCXT info 原始数据中提取合约账户扩展字段
            info = response.get("info") or {}
            # Binance futures: info 是列表 [{"asset":"USDT","walletBalance":...,"unrealizedProfit":...}]
            # 或者是 dict: {"totalUnrealizedProfit":..., "totalMarginBalance":..., ...}
            info_by_asset = {}
            if isinstance(info, list):
                for item in info:
                    a = item.get("asset") or item.get("currency") or ""
                    info_by_asset[a] = item
            elif isinstance(info, dict):
                # Binance futures 有时候在 info 最外层也有汇总字段
                info_by_asset["_global"] = info
                # 有些交易所 info.assets 是列表
                for item in (info.get("assets") or info.get("data") or []):
                    if isinstance(item, dict):
                        a = item.get("asset") or item.get("currency") or ""
                        info_by_asset[a] = item
            
            balances = {}
            for currency, data in response.get("total", {}).items():
                if data and data > 0:
                    free = response.get("free", {}).get(currency, 0) or 0
                    locked = response.get("used", {}).get(currency, 0) or 0
                    total = data
                    
                    if asset and currency != asset:
                        continue
                    
                    # 提取扩展字段
                    raw = info_by_asset.get(currency) or info_by_asset.get("_global") or {}
                    unrealized_pnl = 0
                    margin_used = 0
                    equity = total
                    margin_ratio = 0
                    
                    # Binance futures 字段
                    if raw.get("crossUnPnl") is not None:
                        unrealized_pnl = float(raw["crossUnPnl"])
                    elif raw.get("unrealizedProfit") is not None:
                        unrealized_pnl = float(raw["unrealizedProfit"])
                    elif raw.get("totalUnrealizedProfit") is not None:
                        unrealized_pnl = float(raw["totalUnrealizedProfit"])
                    
                    if raw.get("initialMargin") is not None:
                        margin_used = float(raw["initialMargin"])
                    elif raw.get("totalInitialMargin") is not None:
                        margin_used = float(raw["totalInitialMargin"])
                    elif raw.get("positionInitialMargin") is not None:
                        margin_used = float(raw["positionInitialMargin"])
                    
                    if raw.get("marginBalance") is not None:
                        equity = float(raw["marginBalance"])
                    elif raw.get("totalMarginBalance") is not None:
                        equity = float(raw["totalMarginBalance"])
                    else:
                        equity = total + unrealized_pnl
                    
                    # 保证金使用率 = 占用保证金 / 权益
                    if equity > 0 and margin_used > 0:
                        margin_ratio = margin_used / equity
                    
                    balances[currency] = Balance(
                        asset=currency,
                        free=free,
                        locked=locked,
                        total=total,
                        unrealized_pnl=unrealized_pnl,
                        margin_used=margin_used,
                        margin_ratio=margin_ratio,
                        equity=equity,
                    )
            
            return balances
            
        except Exception as e:
            logger.error("get balance failed", exchange=self.exchange_name, error=str(e))
            raise RuntimeError(f"get_balance failed for {self.exchange_name}: {e}") from e
    
    async def close(self):
        """关闭连接"""
        try:
            await self.exchange.close()
            logger.info("live trader closed", exchange=self.exchange_name)
        except Exception as e:
            logger.warning("close failed", error=str(e))
    
    def _parse_order_response(
        self,
        order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float],
        response: Dict[str, Any],
    ) -> OrderResult:
        """解析订单响应"""
        status_map = {
            "open": OrderStatus.OPEN,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED,
            "expired": OrderStatus.EXPIRED,
            "rejected": OrderStatus.REJECTED,
        }
        
        status = status_map.get(response.get("status"), OrderStatus.PENDING)
        
        # 如果有成交量，可能是部分成交
        filled = response.get("filled", 0) or 0
        if filled > 0 and filled < quantity:
            status = OrderStatus.PARTIAL
        elif filled >= quantity:
            status = OrderStatus.FILLED
        
        # ★ 手续费提取改进：同时处理 fee(单笔) 和 fees(多笔) 两种 CCXT 返回格式
        commission = 0.0
        commission_asset = ""
        # 优先 fee（单笔手续费）
        fee_obj = response.get("fee")
        if fee_obj and isinstance(fee_obj, dict):
            cost = fee_obj.get("cost")
            if cost is not None:
                commission = abs(float(cost))
            commission_asset = fee_obj.get("currency") or ""
        # 若 fee 无数据，检查 fees（某些交易所返回数组）
        if commission == 0:
            fees_list = response.get("fees")
            if fees_list and isinstance(fees_list, list):
                total_fee = 0.0
                for f in fees_list:
                    if isinstance(f, dict) and f.get("cost") is not None:
                        total_fee += abs(float(f["cost"]))
                        if not commission_asset:
                            commission_asset = f.get("currency") or ""
                commission = total_fee
        # 再检查 info 字段（交易所原始响应）中的手续费
        if commission == 0:
            info = response.get("info", {})
            if isinstance(info, dict):
                # Binance futures: commission 字段
                # Gate: fill_fee, taker_fee, maker_fee, fee, total_fee
                raw_comm = (
                    info.get("commission") or 
                    info.get("totalFee") or 
                    info.get("total_fee") or
                    info.get("fee") or
                    info.get("fill_fee") or      # Gate 特有
                    info.get("taker_fee") or     # Gate 特有
                    info.get("maker_fee") or     # Gate 特有
                    info.get("fee_amount") or     # Gate 可能
                    info.get("commission_amount") # Gate 可能
                )
                if raw_comm is not None:
                    try:
                        commission = abs(float(raw_comm))
                    except (ValueError, TypeError):
                        # 尝试字符串转换（Gate 可能返回字符串）
                        try:
                            commission = abs(float(str(raw_comm).strip()))
                        except (ValueError, TypeError):
                            pass
                if not commission_asset:
                    commission_asset = (
                        info.get("commissionAsset") or 
                        info.get("feeCurrency") or 
                        info.get("fee_currency") or  # Gate 特有
                        info.get("fee_currency_code") or  # Gate 可能
                        ""
                    )

        # ★ 增强价格提取（Gate 等交易所可能不返回 average 字段）
        filled_price = response.get("average") or response.get("price") or 0
        if filled_price == 0:
            info = response.get("info", {})
            if isinstance(info, dict):
                # Gate: avgPrice, fill_price, avg_price, average_price, avg_price_str
                raw_price = (
                    info.get("avgPrice") or 
                    info.get("fill_price") or 
                    info.get("avg_price") or
                    info.get("averagePrice") or
                    info.get("average_price") or
                    info.get("avg_price_str") or  # Gate 可能返回字符串
                    info.get("price") or
                    info.get("executed_price") or
                    info.get("exec_price")
                )
                if raw_price is not None:
                    try:
                        filled_price = float(raw_price)
                    except (ValueError, TypeError):
                        # 尝试字符串转换（Gate 可能返回 "50000.5"）
                        try:
                            filled_price = float(str(raw_price).strip())
                        except (ValueError, TypeError):
                            pass

        return OrderResult(
            order_id=order_id,
            exchange_order_id=response.get("id"),
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=status,
            requested_quantity=quantity,
            requested_price=price,
            filled_quantity=filled,
            filled_price=filled_price,
            commission=commission,
            commission_asset=commission_asset,
            raw_response=response,
        )
    
    def _error_result(
        self,
        order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float],
        error_code: str,
        error_message: str,
    ) -> OrderResult:
        """创建错误结果"""
        return OrderResult(
            order_id=order_id,
            exchange_order_id=None,
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=OrderStatus.FAILED,
            requested_quantity=quantity,
            requested_price=price,
            error_code=error_code,
            error_message=error_message,
        )
    
    # ============ OrderTradeService 集成方法 ============
    
    async def _create_order_record(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float],
        position_side: Optional[str],
        signal_id: Optional[str],
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        leverage: Optional[int] = None,
        trade_type: Optional[str] = "OPEN",
        close_reason: Optional[str] = None,
    ) -> Optional[str]:
        """创建订单记录（PENDING 状态）"""
        order_type_str = "MARKET" if order_type == OrderType.MARKET else "LIMIT"
        
        # 优先使用 settlement_service
        if self._settlement_service:
            try:
                order_dto = self._settlement_service.create_order(
                    symbol=symbol,
                    exchange=self.exchange_name,
                    side=side.value.upper(),
                    order_type=order_type_str,
                    quantity=Decimal(str(quantity)),
                    price=Decimal(str(price)) if price else None,
                    signal_id=signal_id,
                    position_side=position_side or "NONE",
                    market_type=self.market_type,
                    stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
                    take_profit=Decimal(str(take_profit)) if take_profit else None,
                    leverage=leverage,
                    trade_type=trade_type or "OPEN",
                    close_reason=close_reason,
                )
                logger.debug("order record created (settlement)", order_id=order_dto.order_id)
                return order_dto.order_id
            except Exception as e:
                logger.error("failed to create order record (settlement)", error=str(e), symbol=symbol, side=side.value)
                return None
        
        # 旧版：使用 order_trade_service
        if not self._order_trade_service:
            return None
        
        try:
            from libs.order_trade import CreateOrderDTO
            
            order_dto = self._order_trade_service.create_order(CreateOrderDTO(
                tenant_id=self._tenant_id,
                account_id=self._account_id,
                symbol=symbol,
                exchange=self.exchange_name,
                side=side.value.upper(),
                order_type=order_type_str,
                quantity=quantity,
                price=price,
                signal_id=signal_id,
                market_type=self.market_type,
                position_side=position_side,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=leverage,
                trade_type=trade_type or "OPEN",
                close_reason=close_reason,
            ))
            
            logger.debug("order record created", order_id=order_dto.order_id)
            return order_dto.order_id
            
        except Exception as e:
            logger.warning("failed to create order record", error=str(e))
            return None
    
    async def _update_order_after_submit(
        self,
        order_id: str,
        exchange_order_id: Optional[str],
        result: OrderResult,
        position_side: Optional[str] = None,
    ) -> None:
        """
        提交后更新订单状态并记录成交
        
        如果配置了 settlement_service，会触发完整的交易闭环：
        OrderTrade → Position → Ledger
        """
        # 优先使用 settlement_service（完整交易闭环）
        if self._settlement_service:
            try:
                # 更新交易所订单号
                if exchange_order_id:
                    self._settlement_service.submit_order(
                        order_id=order_id,
                        exchange_order_id=exchange_order_id,
                    )
                
                # 如果有成交，触发完整结算
                if result.filled_quantity > 0:
                    settlement_result = self._settlement_service.settle_fill(
                        order_id=order_id,
                        symbol=result.symbol,
                        exchange=self.exchange_name,
                        side=result.side.value.upper(),
                        quantity=Decimal(str(result.filled_quantity)),
                        price=Decimal(str(result.filled_price)),
                        fee=Decimal(str(result.commission)) if result.commission else Decimal("0"),
                        fee_currency=result.commission_asset or "USDT",
                        exchange_trade_id=exchange_order_id,
                        filled_at=datetime.now(),
                        position_side=position_side or "NONE",
                        market_type=self.market_type,
                    )
                    
                    if settlement_result.success:
                        logger.info(
                            "settlement completed",
                            order_id=order_id,
                            fill_id=settlement_result.fill_id,
                            position_after=settlement_result.position_quantity_after,
                            balance_after=settlement_result.balance_after,
                            realized_pnl=settlement_result.realized_pnl,
                        )
                    else:
                        logger.warning(
                            "settlement failed",
                            order_id=order_id,
                            error=settlement_result.error,
                        )
                
            except Exception as e:
                logger.error("settlement service error", order_id=order_id, error=str(e))
            return
        
        # 旧版：仅使用 order_trade_service
        if not self._order_trade_service:
            return
        
        try:
            # 更新交易所订单号
            if exchange_order_id:
                self._order_trade_service.submit_order(
                    order_id=order_id,
                    tenant_id=self._tenant_id,
                    exchange_order_id=exchange_order_id,
                    submitted_at=datetime.now(),
                )
            
            # 如果有成交，记录成交
            if result.filled_quantity > 0:
                from libs.order_trade import RecordFillDTO
                
                # 获取订单信息
                order = self._order_trade_service.get_order(order_id, self._tenant_id)
                
                self._order_trade_service.record_fill(RecordFillDTO(
                    order_id=order_id,
                    tenant_id=self._tenant_id,
                    account_id=self._account_id,
                    symbol=result.symbol,
                    side=result.side.value.upper(),
                    quantity=result.filled_quantity,
                    price=result.filled_price,
                    filled_at=datetime.now(),
                    exchange_trade_id=exchange_order_id,
                    fee=result.commission,
                    fee_currency=result.commission_asset,
                ))
                
                logger.debug("fill recorded", order_id=order_id, filled_quantity=result.filled_quantity)
            
        except Exception as e:
            logger.warning("failed to update order record", order_id=order_id, error=str(e))
    
    async def _fail_order_record(
        self,
        order_id: str,
        error_code: str,
        error_message: str,
    ) -> None:
        """标记订单失败"""
        # 优先使用 settlement_service
        if self._settlement_service:
            try:
                self._settlement_service.fail_order(
                    order_id=order_id,
                    error_code=error_code,
                    error_message=error_message,
                )
                logger.debug("order marked as failed (settlement)", order_id=order_id)
            except Exception as e:
                logger.warning("failed to mark order as failed (settlement)", order_id=order_id, error=str(e))
            return
        
        # 旧版：使用 order_trade_service
        if not self._order_trade_service:
            return
        
        try:
            self._order_trade_service.fail_order(
                order_id=order_id,
                tenant_id=self._tenant_id,
                error_code=error_code,
                error_message=error_message,
            )
            logger.debug("order marked as failed", order_id=order_id)
        except Exception as e:
            logger.warning("failed to mark order as failed", order_id=order_id, error=str(e))
