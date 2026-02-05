"""
Telegram Bot 通知器

使用方法：
1. 创建 Telegram Bot：与 @BotFather 对话，发送 /newbot
2. 获取 Bot Token
3. 获取 Chat ID：
   - 将 Bot 添加到群组，或直接与 Bot 对话
   - 访问 https://api.telegram.org/bot<TOKEN>/getUpdates
   - 找到 chat.id
4. 配置环境变量或 config/default.yaml:
   - TELEGRAM_BOT_TOKEN=xxx
   - TELEGRAM_CHAT_ID=xxx
"""

import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

from libs.core import get_config, get_logger
from .base import NotifierBase, NotifyResult

log = get_logger("telegram-notifier")


class TelegramNotifier(NotifierBase):
    """Telegram Bot 通知器"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        初始化 Telegram 通知器
        
        Args:
            bot_token: Bot Token，不传则从配置读取
            chat_id: 聊天ID，不传则从配置读取
        """
        config = get_config()
        self.bot_token = bot_token or config.get_str("telegram_bot_token", "")
        self.chat_id = chat_id or config.get_str("telegram_chat_id", "")
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        self.timeout = 10.0
        
        if not self.bot_token:
            log.warning("Telegram Bot Token 未配置")
        if not self.chat_id:
            log.warning("Telegram Chat ID 未配置")
    
    def _request(self, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送 API 请求"""
        url = f"{self.api_base}/{method}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=data)
                return resp.json()
        except Exception as e:
            log.error(f"Telegram API 请求失败: {e}")
            return {"ok": False, "description": str(e)}
    
    def send(self, title: str, content: str, parse_mode: str = "HTML", 
             disable_notification: bool = False) -> NotifyResult:
        """
        发送消息
        
        Args:
            title: 标题
            content: 内容
            parse_mode: 解析模式 (HTML/Markdown/MarkdownV2)
            disable_notification: 是否静默发送
        """
        if not self.bot_token or not self.chat_id:
            return NotifyResult(success=False, error="Telegram 未配置")
        
        # 组合消息
        text = f"<b>{title}</b>\n\n{content}" if title else content
        
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }
        
        result = self._request("sendMessage", data)
        
        if result.get("ok"):
            msg_id = result.get("result", {}).get("message_id")
            log.info(f"Telegram 消息发送成功: {msg_id}")
            return NotifyResult(success=True, message_id=str(msg_id))
        else:
            error = result.get("description", "Unknown error")
            log.error(f"Telegram 消息发送失败: {error}")
            return NotifyResult(success=False, error=error)
    
    def send_signal(self, signal: Dict[str, Any]) -> NotifyResult:
        """
        发送交易信号通知
        
        Args:
            signal: 信号字典，包含：
                - symbol: 交易对
                - side: BUY/SELL
                - entry_price: 入场价
                - stop_loss: 止损价
                - take_profit: 止盈价
                - reason: 信号原因
                - confidence: 置信度
                - indicators: 指标数据
        """
        symbol = signal.get("symbol", "未知")
        side = signal.get("side", "未知")
        entry = signal.get("entry_price", 0)
        sl = signal.get("stop_loss", 0)
        tp = signal.get("take_profit", 0)
        reason = signal.get("reason", "")
        confidence = signal.get("confidence", 0)
        indicators = signal.get("indicators", {})
        
        # 计算盈亏比
        if side == "BUY" and sl and tp and entry:
            risk = entry - sl
            reward = tp - entry
            rr_ratio = reward / risk if risk > 0 else 0
        elif side == "SELL" and sl and tp and entry:
            risk = sl - entry
            reward = entry - tp
            rr_ratio = reward / risk if risk > 0 else 0
        else:
            rr_ratio = 0
        
        # 方向 emoji
        side_emoji = "🟢" if side == "BUY" else "🔴"
        
        # 市场状态
        regime = indicators.get("regime", "unknown")
        regime_text = "📊 震荡" if regime == "ranging" else "📈 趋势" if regime == "trending" else "❓ 未知"
        
        # 格式化消息
        content = f"""
{side_emoji} <b>{side} {symbol}</b>

💰 入场: <code>{entry:,.2f}</code>
🛑 止损: <code>{sl:,.2f}</code>
🎯 止盈: <code>{tp:,.2f}</code>

📊 盈亏比: <b>{rr_ratio:.2f}:1</b>
🎯 置信度: {confidence}%

{regime_text}
📝 {reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return self.send(title="🚨 交易信号", content=content.strip())
    
    def send_alert(self, alert_type: str, message: str, 
                   level: str = "info", **kwargs) -> NotifyResult:
        """
        发送告警通知
        
        Args:
            alert_type: 告警类型 (stop_loss, take_profit, error, warning, etc.)
            message: 告警消息
            level: 告警级别 (info, warning, error, critical)
        """
        # 级别 emoji
        level_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨",
        }.get(level, "ℹ️")
        
        # 类型 emoji
        type_emoji = {
            "stop_loss": "🛑",
            "take_profit": "🎯",
            "error": "❌",
            "position_opened": "📈",
            "position_closed": "📉",
            "drawdown": "📉",
        }.get(alert_type, "📢")
        
        title = f"{level_emoji} {type_emoji} {alert_type.upper()}"
        content = f"{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # critical 级别不静默
        silent = level not in ["error", "critical"]
        
        return self.send(title=title, content=content, disable_notification=silent)
    
    def send_daily_report(self, report: Dict[str, Any]) -> NotifyResult:
        """
        发送每日报告
        
        Args:
            report: 报告数据
                - date: 日期
                - total_trades: 总交易数
                - winning_trades: 盈利交易数
                - losing_trades: 亏损交易数
                - total_pnl: 总盈亏
                - win_rate: 胜率
                - max_drawdown: 最大回撤
        """
        date = report.get("date", datetime.now().strftime("%Y-%m-%d"))
        total = report.get("total_trades", 0)
        wins = report.get("winning_trades", 0)
        losses = report.get("losing_trades", 0)
        pnl = report.get("total_pnl", 0)
        win_rate = report.get("win_rate", 0)
        max_dd = report.get("max_drawdown", 0)
        
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        
        content = f"""
📅 日期: {date}

{pnl_emoji} 总盈亏: <b>{pnl:+,.2f} USDT</b>
📊 交易数: {total} (盈 {wins} / 亏 {losses})
🎯 胜率: {win_rate:.1f}%
📉 最大回撤: {max_dd:.2f}%
"""
        
        return self.send(title="📊 每日报告", content=content.strip())
    
    def test_connection(self) -> NotifyResult:
        """测试连接"""
        return self.send(
            title="🔗 连接测试",
            content="IronBull 交易系统已连接！\n\n"
                    "✅ Telegram 通知配置成功\n"
                    "📡 准备接收交易信号",
        )


# 便捷函数
_default_notifier: Optional[TelegramNotifier] = None


def get_telegram_notifier() -> TelegramNotifier:
    """获取默认 Telegram 通知器（单例）"""
    global _default_notifier
    if _default_notifier is None:
        _default_notifier = TelegramNotifier()
    return _default_notifier


def send_signal(signal: Dict[str, Any]) -> NotifyResult:
    """快捷发送信号"""
    return get_telegram_notifier().send_signal(signal)


def send_alert(alert_type: str, message: str, **kwargs) -> NotifyResult:
    """快捷发送告警"""
    return get_telegram_notifier().send_alert(alert_type, message, **kwargs)
