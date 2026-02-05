#!/usr/bin/env python3
"""
本地交易监控器

功能：
1. 定期运行策略检测信号
2. 自动执行交易（带止盈止损）
3. 监控持仓盈亏
4. 发送 Telegram 通知
5. 支持交易数据持久化（OrderTrade → Position → Ledger）

用法：
    python scripts/local_monitor.py --help
    python scripts/local_monitor.py --symbols ETH/USDT:USDT BTC/USDT:USDT
    python scripts/local_monitor.py --mode auto --interval 60
    python scripts/local_monitor.py --mode auto --no-persist  # 不持久化
"""

import sys
import os
import asyncio
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core import get_config, get_logger
from libs.core.database import get_session
from libs.notify import TelegramNotifier
from libs.trading import AutoTrader, TradeMode, RiskLimits, TradeSettlementService
from libs.trading.live_trader import LiveTrader, OrderSide
from libs.strategies import get_strategy

import ccxt.async_support as ccxt_async

logger = get_logger("local-monitor")


class LocalMonitor:
    """本地交易监控器"""
    
    def __init__(
        self,
        symbols: List[str],
        strategy_name: str = "market_regime",
        timeframe: str = "15m",
        mode: str = "notify",  # notify / confirm / auto
        interval: int = 60,    # 检查间隔（秒）
        persist: bool = True,  # 是否持久化交易数据
    ):
        self.symbols = symbols
        self.strategy_name = strategy_name
        self.timeframe = timeframe
        self.mode = mode
        self.interval = interval
        self.running = False
        self.persist = persist
        
        # 配置
        self.config = get_config()
        
        # 通知器
        self.notifier = TelegramNotifier()
        
        # 交易所客户端
        self.exchange: Optional[ccxt_async.Exchange] = None
        
        # 自动交易器
        self.trader: Optional[AutoTrader] = None
        
        # 策略
        self.strategy = get_strategy(strategy_name)
        
        # 已处理的信号（避免重复）
        self.processed_signals: Dict[str, datetime] = {}
        self.signal_cooldown = 300  # 同一信号冷却时间（秒）
        
        # 结算服务（用于交易持久化）
        self._db_session = None
        self._settlement_service: Optional[TradeSettlementService] = None
        
    async def init(self):
        """初始化"""
        # 创建交易所客户端
        self.exchange = ccxt_async.binanceusdm({
            "apiKey": self.config.get_str("exchange_api_key"),
            "secret": self.config.get_str("exchange_api_secret"),
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })
        
        # 创建结算服务（用于交易持久化）
        settlement_service = None
        if self.persist:
            try:
                self._db_session = get_session()
                tenant_id = self.config.get_int("tenant_id", 1)
                account_id = self.config.get_int("account_id", 1)
                currency = self.config.get_str("account_currency", "USDT")
                
                self._settlement_service = TradeSettlementService(
                    session=self._db_session,
                    tenant_id=tenant_id,
                    account_id=account_id,
                    currency=currency,
                )
                settlement_service = self._settlement_service
                
                logger.info(
                    "settlement service initialized",
                    tenant_id=tenant_id,
                    account_id=account_id,
                    persist=True,
                )
            except Exception as e:
                logger.warning(f"failed to create settlement service, trading will not persist: {e}")
        
        # 创建自动交易器
        mode_map = {
            "notify": TradeMode.NOTIFY_ONLY,
            "confirm": TradeMode.CONFIRM_EACH,
            "auto": TradeMode.AUTO_EXECUTE,
        }
        
        self.trader = AutoTrader(
            exchange=self.config.get_str("exchange_name", "binance"),
            api_key=self.config.get_str("exchange_api_key"),
            api_secret=self.config.get_str("exchange_api_secret"),
            sandbox=self.config.get_bool("exchange_sandbox", False),
            market_type="future",
            mode=mode_map.get(self.mode, TradeMode.NOTIFY_ONLY),
            risk_limits=RiskLimits(
                max_trade_amount=self.config.get_float("auto_trade_max_amount", 200),
                max_daily_trades=self.config.get_int("auto_trade_max_daily", 10),
                max_open_positions=self.config.get_int("auto_trade_max_positions", 5),
                min_confidence=self.config.get_int("auto_trade_min_confidence", 70),
            ),
            # 传入结算服务实现交易持久化
            settlement_service=settlement_service,
        )
        
        if self.mode == "auto":
            self.trader.enable()
        
        logger.info(
            "monitor initialized",
            symbols=self.symbols,
            strategy=self.strategy_name,
            mode=self.mode,
            interval=self.interval,
            persist=self.persist and settlement_service is not None,
        )
        
    async def close(self):
        """关闭"""
        if self.exchange:
            await self.exchange.close()
        
        # 关闭数据库连接
        if self._db_session:
            try:
                self._db_session.close()
            except Exception:
                pass
            
    async def fetch_candles(self, symbol: str, limit: int = 200) -> List[Dict]:
        """获取K线数据"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=limit)
            candles = []
            for item in ohlcv:
                candles.append({
                    "timestamp": item[0],
                    "open": item[1],
                    "high": item[2],
                    "low": item[3],
                    "close": item[4],
                    "volume": item[5],
                })
            return candles
        except Exception as e:
            logger.error("fetch candles failed", symbol=symbol, error=str(e))
            return []
    
    async def fetch_positions(self) -> List[Dict]:
        """获取当前持仓"""
        try:
            positions = await self.exchange.fetch_positions()
            active = [p for p in positions if abs(p.get('contracts', 0)) > 0]
            return active
        except Exception as e:
            logger.error("fetch positions failed", error=str(e))
            return []
    
    async def check_signal(self, symbol: str) -> Optional[Dict]:
        """检查信号"""
        # 获取K线
        candles = await self.fetch_candles(symbol)
        if len(candles) < 100:
            logger.warning("insufficient candles", symbol=symbol, count=len(candles))
            return None
        
        # 获取持仓
        positions = await self.fetch_positions()
        symbol_positions = [p for p in positions if p['symbol'] == symbol]
        
        # 运行策略
        try:
            result = self.strategy.analyze(
                symbol=symbol,
                timeframe=self.timeframe,
                candles=candles,
                positions=symbol_positions,
            )
            
            if result and result.signal_type == "OPEN":
                return {
                    "symbol": symbol,
                    "side": result.side,
                    "entry_price": result.entry_price,
                    "stop_loss": result.stop_loss,
                    "take_profit": result.take_profit,
                    "confidence": result.confidence,
                    "reason": result.reason,
                }
        except Exception as e:
            import traceback
            logger.error("strategy analyze failed", symbol=symbol, error=str(e))
            traceback.print_exc()
        
        return None
    
    def is_signal_duplicate(self, signal: Dict) -> bool:
        """检查信号是否重复"""
        key = f"{signal['symbol']}_{signal['side']}"
        now = datetime.now()
        
        if key in self.processed_signals:
            last_time = self.processed_signals[key]
            if (now - last_time).total_seconds() < self.signal_cooldown:
                return True
        
        self.processed_signals[key] = now
        return False
    
    async def process_signal(self, signal: Dict):
        """处理信号"""
        if self.is_signal_duplicate(signal):
            logger.info("signal duplicate, skipping", symbol=signal['symbol'])
            return
        
        # 打印信号
        side_emoji = "🟢" if signal['side'] == "BUY" else "🔴"
        print(f"\n{'='*50}")
        print(f"{side_emoji} 信号: {signal['side']} {signal['symbol']}")
        print(f"   入场: {signal['entry_price']:.2f}")
        print(f"   止损: {signal['stop_loss']:.2f}")
        print(f"   止盈: {signal['take_profit']:.2f}")
        print(f"   置信度: {signal['confidence']}%")
        print(f"   原因: {signal['reason']}")
        print(f"{'='*50}\n")
        
        if self.mode == "notify":
            # 仅通知
            self.notifier.send_signal(signal)
            
        elif self.mode == "confirm":
            # 需要确认
            self.notifier.send_signal(signal)
            confirm = input("是否执行? (y/n): ").strip().lower()
            if confirm == 'y':
                result = await self.trader.process_signal(signal)
                print(f"执行结果: {result}")
            else:
                print("已取消")
                
        elif self.mode == "auto":
            # 自动执行
            result = await self.trader.process_signal(signal)
            print(f"执行结果: {result}")
    
    async def monitor_positions(self):
        """监控持仓"""
        positions = await self.fetch_positions()
        
        if positions:
            print(f"\n📊 当前持仓 ({len(positions)} 个):")
            for p in positions:
                side = "🟢 多" if p['side'] == 'long' else "🔴 空"
                pnl = p.get('unrealizedPnl', 0)
                pnl_str = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
                pnl_pct = p.get('percentage', 0)
                print(f"   {p['symbol']} | {side} | 数量: {p['contracts']} | 盈亏: {pnl_str} USDT ({pnl_pct:.1f}%)")
    
    async def run_once(self):
        """运行一次检查"""
        print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] 检查信号...")
        
        for symbol in self.symbols:
            signal = await self.check_signal(symbol)
            if signal:
                await self.process_signal(signal)
            else:
                print(f"   {symbol}: 无信号")
        
        await self.monitor_positions()
    
    async def run(self):
        """持续运行"""
        await self.init()
        self.running = True
        
        print(f"""
╔══════════════════════════════════════════════════╗
║          🐂 IronBull 本地监控器                  ║
╠══════════════════════════════════════════════════╣
║  交易对: {', '.join(self.symbols):<38} ║
║  策略:   {self.strategy_name:<38} ║
║  周期:   {self.timeframe:<38} ║
║  模式:   {self.mode:<38} ║
║  间隔:   {self.interval}秒{' ':<34} ║
╠══════════════════════════════════════════════════╣
║  按 Ctrl+C 停止                                  ║
╚══════════════════════════════════════════════════╝
        """)
        
        # 发送启动通知
        self.notifier.send_alert(
            "system",
            f"🚀 本地监控已启动\n\n"
            f"交易对: {', '.join(self.symbols)}\n"
            f"策略: {self.strategy_name}\n"
            f"模式: {self.mode}",
            level="info",
        )
        
        try:
            while self.running:
                await self.run_once()
                print(f"\n💤 等待 {self.interval} 秒...")
                await asyncio.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n\n🛑 正在停止...")
        finally:
            self.running = False
            await self.close()
            print("✅ 监控已停止")


def main():
    parser = argparse.ArgumentParser(description="IronBull 本地交易监控器")
    parser.add_argument(
        "--symbols", "-s",
        nargs="+",
        default=["ETH/USDT:USDT", "BTC/USDT:USDT"],
        help="监控的交易对 (默认: ETH/USDT:USDT BTC/USDT:USDT)",
    )
    parser.add_argument(
        "--strategy",
        default="market_regime",
        help="策略名称 (默认: market_regime)",
    )
    parser.add_argument(
        "--timeframe", "-t",
        default="15m",
        help="K线周期 (默认: 15m)",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["notify", "confirm", "auto"],
        default="notify",
        help="交易模式: notify=仅通知, confirm=确认后执行, auto=自动执行 (默认: notify)",
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="检查间隔秒数 (默认: 60)",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="不持久化交易数据到数据库",
    )
    
    args = parser.parse_args()
    
    monitor = LocalMonitor(
        symbols=args.symbols,
        strategy_name=args.strategy,
        timeframe=args.timeframe,
        mode=args.mode,
        interval=args.interval,
        persist=not args.no_persist,
    )
    
    asyncio.run(monitor.run())


if __name__ == "__main__":
    main()
