-- 插入 dim_strategy 策略目录（与 libs/strategies 的 code 对应）
-- 用于 Merchant API GET /merchant/strategies

INSERT INTO `dim_strategy` (`code`, `name`, `description`, `symbol`, `timeframe`, `min_capital`, `risk_level`, `status`, `config`) VALUES
('market_regime', '市场状态-BTC', '多周期市场状态识别，顺势择时', 'BTC/USDT', '1h', 200, 1, 1, NULL),
('ema_cross', '均线交叉-BTC', '双均线金叉死叉，趋势跟踪', 'BTC/USDT', '1h', 200, 2, 1, NULL),
('ma_cross', '均线交叉-BTC', 'MA 金叉死叉策略', 'BTC/USDT', '15m', 200, 2, 1, NULL),
('rsi', 'RSI-BTC', 'RSI 超买超卖反转', 'BTC/USDT', '1h', 200, 2, 1, NULL),
('rsi_boll', 'RSI布林-BTC', 'RSI + 布林带组合', 'BTC/USDT', '1h', 200, 2, 1, NULL),
('macd', 'MACD-BTC', 'MACD 柱状图拐点', 'BTC/USDT', '1h', 200, 2, 1, NULL),
('supertrend', '超级趋势-BTC', 'SuperTrend 趋势跟踪', 'BTC/USDT', '1h', 200, 2, 1, NULL),
('boll_squeeze', '布林收口-BTC', '布林带收口突破', 'BTC/USDT', '1h', 200, 2, 1, NULL),
('keltner', '肯特纳-BTC', 'Keltner 通道策略', 'BTC/USDT', '1h', 200, 2, 1, NULL),
('breakout', '突破-BTC', '支撑阻力突破', 'BTC/USDT', '1h', 200, 3, 1, NULL),
('mean_reversion', '均值回归-BTC', '价格回归均线', 'BTC/USDT', '1h', 200, 2, 1, NULL),
('turtle', '海龟-BTC', '海龟交易法则', 'BTC/USDT', '4h', 200, 3, 1, NULL),
('grid', '网格-BTC', '网格震荡套利', 'BTC/USDT', '1h', 200, 1, 1, NULL),
('momentum', '动量-BTC', '动量突破策略', 'BTC/USDT', '1h', 200, 3, 1, NULL),
('smc', 'SMC-BTC', 'Smart Money 概念', 'BTC/USDT', '1h', 200, 2, 1, NULL),
('smc_fibo', 'SMC斐波那契-BTC', 'SMC + 斐波那契', 'BTC/USDT', '1h', 200, 2, 1, NULL)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `description` = VALUES(`description`),
  `symbol` = VALUES(`symbol`),
  `timeframe` = VALUES(`timeframe`),
  `min_capital` = VALUES(`min_capital`),
  `risk_level` = VALUES(`risk_level`),
  `status` = VALUES(`status`),
  `updated_at` = CURRENT_TIMESTAMP;
