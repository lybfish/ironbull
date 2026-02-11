-- ═══════════════════════════════════════════════════════════════
-- smc_fibo_flex 策略部署脚本
-- 包含：1) 限价挂单追踪表  2) 策略配置插入
-- 
-- 回测数据: ETH 15m 1年
--   胜率 62.4%, PF 2.58, 回撤 6.2%, PnL +$24,472
-- ═══════════════════════════════════════════════════════════════


-- ───────────────────────────────────────────────────────────────
-- 1. 创建限价挂单追踪表 (fact_pending_limit_order)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `fact_pending_limit_order` (
    `id`                      BIGINT AUTO_INCREMENT PRIMARY KEY,
    `pending_key`             VARCHAR(128) NOT NULL COMMENT '唯一键 strategy_code:symbol',
    
    -- 订单信息
    `order_id`                VARCHAR(64)    DEFAULT NULL COMMENT '系统订单号',
    `exchange_order_id`       VARCHAR(128)   DEFAULT NULL COMMENT '交易所订单号',
    `symbol`                  VARCHAR(32)    NOT NULL COMMENT '交易对',
    `side`                    VARCHAR(8)     NOT NULL COMMENT 'BUY/SELL',
    `entry_price`             DECIMAL(20,8)  NOT NULL COMMENT '挂单价格',
    `stop_loss`               DECIMAL(20,8)  DEFAULT NULL COMMENT '止损价',
    `take_profit`             DECIMAL(20,8)  DEFAULT NULL COMMENT '止盈价',
    
    -- 策略 & 账户
    `strategy_code`           VARCHAR(64)    NOT NULL COMMENT '策略代码',
    `account_id`              INT            NOT NULL COMMENT '交易所账户ID',
    `tenant_id`               INT            NOT NULL COMMENT '租户ID',
    `amount_usdt`             DECIMAL(20,2)  DEFAULT NULL COMMENT '下单金额 USDT',
    `leverage`                INT            DEFAULT NULL COMMENT '杠杆倍数',
    
    -- 超时 & 确认参数
    `timeframe`               VARCHAR(8)     NOT NULL DEFAULT '15m' COMMENT 'K线周期',
    `retest_bars`             INT            NOT NULL DEFAULT 20 COMMENT '最大等待K线数',
    `confirm_after_fill`      TINYINT(1)     NOT NULL DEFAULT 0 COMMENT '成交后是否需要确认',
    `post_fill_confirm_bars`  INT            NOT NULL DEFAULT 3 COMMENT '确认等待K线数',
    
    -- 成交信息
    `filled_price`            DECIMAL(20,8)  DEFAULT NULL COMMENT '成交价',
    `filled_qty`              DECIMAL(20,8)  DEFAULT NULL COMMENT '成交数量',
    `filled_at`               DATETIME       DEFAULT NULL COMMENT '成交时间',
    `candles_checked`         INT            NOT NULL DEFAULT 0 COMMENT '已检查确认K线数',
    
    -- 状态: PENDING / FILLED / CONFIRMING / EXPIRED / CANCELLED
    `status`                  VARCHAR(16)    NOT NULL DEFAULT 'PENDING' COMMENT '状态',
    
    -- 时间
    `placed_at`               DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '挂单时间',
    `closed_at`               DATETIME       DEFAULT NULL COMMENT '结束时间',
    `created_at`              DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`              DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 约束 & 索引
    UNIQUE KEY `uq_pending_key` (`pending_key`),
    KEY `idx_pending_strategy_symbol` (`strategy_code`, `symbol`),
    KEY `idx_pending_status` (`status`),
    KEY `idx_pending_account` (`account_id`),
    KEY `idx_pending_exchange_order` (`exchange_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='限价挂单追踪表';


-- ───────────────────────────────────────────────────────────────
-- 2. 插入 smc_fibo_flex 策略到 dim_strategy
-- ───────────────────────────────────────────────────────────────

INSERT INTO `dim_strategy` (
    `code`,
    `name`,
    `description`,
    `symbol`,
    `symbols`,
    `timeframe`,
    `exchange`,
    `market_type`,
    `min_capital`,
    `risk_level`,
    `amount_usdt`,
    `leverage`,
    `capital`,
    `risk_mode`,
    `min_confidence`,
    `cooldown_minutes`,
    `status`,
    `show_to_user`,
    `user_display_name`,
    `user_description`,
    `config`
) VALUES (
    'smc_fibo_flex',                                          -- code: 策略代码（对应 libs/strategies 里的注册名）
    'SMC斐波那契Pro',                                         -- name: 内部名称
    'SMC结构突破 + 斐波那契回踩 限价入场策略，回测胜率62%，PF 2.58',  -- description: 内部描述
    'ETH/USDT',                                               -- symbol: 主交易对
    '["ETH/USDT"]',                                           -- symbols: 监控交易对列表（JSON数组）
    '15m',                                                    -- timeframe: K线周期
    NULL,                                                     -- exchange: 空=跟随账户的交易所
    'future',                                                 -- market_type: 合约
    200.00,                                                   -- min_capital: 最低投入资金
    2,                                                        -- risk_level: 风险等级 1低 2中 3高
    200.00,                                                   -- amount_usdt: 默认单仓下单金额（用户绑定后会被覆盖）
    20,                                                       -- leverage: 默认杠杆
    1000.00,                                                  -- capital: 默认本金
    1,                                                        -- risk_mode: 默认风险档位 1=稳健
    50,                                                       -- min_confidence: 最低置信度
    75,                                                       -- cooldown_minutes: 信号冷却（20根×15分钟÷4≈75分钟，保守设法）
    1,                                                        -- status: 1=启用
    1,                                                        -- show_to_user: 1=对用户展示
    'SMC斐波那契Pro',                                          -- user_display_name: 用户看到的名称
    '基于Smart Money概念的结构突破+斐波那契回踩策略。限价单入场，自动止盈止损。回测年化胜率62%，盈亏比2.58:1，最大回撤6.2%。',
    -- config: 策略算法参数（核心！）
    '{
        "preset_profile": "none",
        "auto_profile": "off",
        "swing": 3,
        "min_rr": 1.5,
        "fibo_levels": [0.5, 0.618, 0.705],
        "stopBufferPct": 1.0,
        "bias": "with_trend",
        "structure": "both",
        "tp_mode": "swing",
        "entry_mode": "limit",
        "require_retest": true,
        "retest_bars": 20,
        "entry_source": "auto",
        "confirm_after_fill": false,
        "signal_cooldown": 20,
        "fibo_fallback": false,
        "require_htf_filter": false,
        "enable_signal_score": false,
        "enable_session_filter": false,
        "amd_entry_mode": "off",
        "use_breaker": false
    }'
)
ON DUPLICATE KEY UPDATE
    `name` = VALUES(`name`),
    `description` = VALUES(`description`),
    `symbol` = VALUES(`symbol`),
    `symbols` = VALUES(`symbols`),
    `timeframe` = VALUES(`timeframe`),
    `market_type` = VALUES(`market_type`),
    `min_capital` = VALUES(`min_capital`),
    `risk_level` = VALUES(`risk_level`),
    `amount_usdt` = VALUES(`amount_usdt`),
    `leverage` = VALUES(`leverage`),
    `capital` = VALUES(`capital`),
    `risk_mode` = VALUES(`risk_mode`),
    `min_confidence` = VALUES(`min_confidence`),
    `cooldown_minutes` = VALUES(`cooldown_minutes`),
    `status` = VALUES(`status`),
    `show_to_user` = VALUES(`show_to_user`),
    `user_display_name` = VALUES(`user_display_name`),
    `user_description` = VALUES(`user_description`),
    `config` = VALUES(`config`),
    `updated_at` = CURRENT_TIMESTAMP;


-- ═══════════════════════════════════════════════════════════════
-- 验证插入结果
-- ═══════════════════════════════════════════════════════════════
SELECT id, code, name, symbol, timeframe, leverage, capital, risk_mode, amount_usdt, 
       cooldown_minutes, status, show_to_user
FROM dim_strategy 
WHERE code = 'smc_fibo_flex';
