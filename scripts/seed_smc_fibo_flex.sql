-- ═══════════════════════════════════════════════════════════════
-- smc_fibo_flex 三档策略部署脚本
-- 包含：
--   1) 限价挂单追踪表
--   2) 策略配置（稳健/均衡/激进三档，与 market_regime 模式一致）
--   3) 租户2的策略展示配置 (dim_tenant_strategy)
--   4) 租户2用户绑定稳健档 (dim_strategy_binding)
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
-- 2. smc_fibo_flex 三档策略 → dim_strategy
--    命名规则与 market_regime 一致: 名称·风格
-- ───────────────────────────────────────────────────────────────

-- 共用策略配置（JSON）
SET @smc_config = '{
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
    "risk_based_sizing": true,
    "fibo_fallback": false,
    "require_htf_filter": false,
    "enable_signal_score": false,
    "enable_session_filter": false,
    "amd_entry_mode": "off",
    "use_breaker": false
}';

-- 2a. 稳健档 (原 smc_fibo_flex，更新名称)
UPDATE `dim_strategy` SET
    `name`              = 'SMC结构·稳健',
    `risk_level`        = 1,
    `risk_mode`         = 1,
    `amount_usdt`       = 200.00,
    `user_display_name` = 'SMC斐波那契(稳健) Pro',
    `user_description`  = '基于Smart Money概念的结构突破+斐波那契回踩限价入场策略。采用1%风险系数，以损定仓自动控制每笔亏损。回测胜率62%，盈亏比2.58:1，最大回撤6.2%。适合追求稳健增长的中长期交易者。'
WHERE `code` = 'smc_fibo_flex';

-- 2b. 均衡档 (新增)
INSERT INTO `dim_strategy` (
    `code`, `name`, `description`,
    `symbol`, `symbols`, `timeframe`, `exchange`, `market_type`,
    `min_capital`, `risk_level`, `amount_usdt`, `leverage`, `capital`, `risk_mode`,
    `min_confidence`, `cooldown_minutes`, `status`, `show_to_user`,
    `user_display_name`, `user_description`, `config`
) VALUES (
    'smc_fibo_flex_balanced',
    'SMC结构·均衡',
    'SMC结构突破 + 斐波那契回踩 限价入场策略（均衡版），风险系数1.5%',
    'ETHUSDT', '["ETHUSDT"]', '15m', NULL, 'future',
    200.00, 2, 300.00, 20, 1000.00, 2,
    50, 75, 1, 1,
    'SMC斐波那契(均衡) Pro',
    'SMC斐波那契均衡版在稳健版基础上将风险系数提升至1.5%，通过更均衡的风险收益比设计，提供更具弹性的收益空间。限价单入场，以损定仓自动控制每笔亏损。回测胜率62%，盈亏比2.58:1。适合具备一定风险承受能力的投资者。',
    @smc_config
)
ON DUPLICATE KEY UPDATE
    `name` = VALUES(`name`),
    `description` = VALUES(`description`),
    `risk_level` = VALUES(`risk_level`),
    `amount_usdt` = VALUES(`amount_usdt`),
    `risk_mode` = VALUES(`risk_mode`),
    `user_display_name` = VALUES(`user_display_name`),
    `user_description` = VALUES(`user_description`),
    `config` = VALUES(`config`),
    `updated_at` = CURRENT_TIMESTAMP;

-- 2c. 激进档 (新增)
INSERT INTO `dim_strategy` (
    `code`, `name`, `description`,
    `symbol`, `symbols`, `timeframe`, `exchange`, `market_type`,
    `min_capital`, `risk_level`, `amount_usdt`, `leverage`, `capital`, `risk_mode`,
    `min_confidence`, `cooldown_minutes`, `status`, `show_to_user`,
    `user_display_name`, `user_description`, `config`
) VALUES (
    'smc_fibo_flex_aggressive',
    'SMC结构·激进',
    'SMC结构突破 + 斐波那契回踩 限价入场策略（激进版），风险系数2%',
    'ETHUSDT', '["ETHUSDT"]', '15m', NULL, 'future',
    200.00, 3, 400.00, 20, 1000.00, 3,
    50, 75, 1, 1,
    'SMC斐波那契(激进) Pro',
    'SMC斐波那契激进版将风险系数提升至2%，面向追求高收益、具备较高风险承受能力的专业交易者。限价单入场，以损定仓自动控制每笔亏损，配合动态止损与仓位约束机制。回测胜率62%，盈亏比2.58:1。',
    @smc_config
)
ON DUPLICATE KEY UPDATE
    `name` = VALUES(`name`),
    `description` = VALUES(`description`),
    `risk_level` = VALUES(`risk_level`),
    `amount_usdt` = VALUES(`amount_usdt`),
    `risk_mode` = VALUES(`risk_mode`),
    `user_display_name` = VALUES(`user_display_name`),
    `user_description` = VALUES(`user_description`),
    `config` = VALUES(`config`),
    `updated_at` = CURRENT_TIMESTAMP;


-- ───────────────────────────────────────────────────────────────
-- 3. 租户2的策略展示配置 (dim_tenant_strategy)
-- ───────────────────────────────────────────────────────────────

-- 先获取策略 ID（使用子查询）
INSERT INTO `dim_tenant_strategy` (
    `tenant_id`, `strategy_id`, `display_name`, `display_description`,
    `leverage`, `capital`, `risk_mode`, `amount_usdt`, `min_capital`,
    `status`, `sort_order`
)
SELECT
    2,
    s.id,
    'SMC斐波那契(稳健) Pro',
    '基于Smart Money概念的结构突破+斐波那契回踩限价入场策略。采用1%风险系数，以损定仓自动控制每笔亏损。回测胜率62%，盈亏比2.58:1，最大回撤6.2%。适合追求稳健增长的中长期交易者。',
    20, 1000.00, 1, 200.00, 200.00,
    1, 1
FROM `dim_strategy` s WHERE s.code = 'smc_fibo_flex'
ON DUPLICATE KEY UPDATE
    `display_name` = VALUES(`display_name`),
    `display_description` = VALUES(`display_description`),
    `updated_at` = CURRENT_TIMESTAMP;

INSERT INTO `dim_tenant_strategy` (
    `tenant_id`, `strategy_id`, `display_name`, `display_description`,
    `leverage`, `capital`, `risk_mode`, `amount_usdt`, `min_capital`,
    `status`, `sort_order`
)
SELECT
    2,
    s.id,
    'SMC斐波那契(均衡) Pro',
    'SMC斐波那契均衡版在稳健版基础上将风险系数提升至1.5%，提供更具弹性的收益空间。限价单入场，以损定仓自动控制每笔亏损。适合具备一定风险承受能力的投资者。',
    20, 1000.00, 2, 300.00, 200.00,
    1, 2
FROM `dim_strategy` s WHERE s.code = 'smc_fibo_flex_balanced'
ON DUPLICATE KEY UPDATE
    `display_name` = VALUES(`display_name`),
    `display_description` = VALUES(`display_description`),
    `updated_at` = CURRENT_TIMESTAMP;

INSERT INTO `dim_tenant_strategy` (
    `tenant_id`, `strategy_id`, `display_name`, `display_description`,
    `leverage`, `capital`, `risk_mode`, `amount_usdt`, `min_capital`,
    `status`, `sort_order`
)
SELECT
    2,
    s.id,
    'SMC斐波那契(激进) Pro',
    'SMC斐波那契激进版将风险系数提升至2%，面向追求高收益的专业交易者。限价单入场，以损定仓自动控制每笔亏损，配合动态止损与仓位约束机制。',
    20, 1000.00, 3, 400.00, 200.00,
    1, 3
FROM `dim_strategy` s WHERE s.code = 'smc_fibo_flex_aggressive'
ON DUPLICATE KEY UPDATE
    `display_name` = VALUES(`display_name`),
    `display_description` = VALUES(`display_description`),
    `updated_at` = CURRENT_TIMESTAMP;


-- ───────────────────────────────────────────────────────────────
-- 4. 租户2用户(id=66) 绑定稳健档
--    注意：需要该用户先有交易所账户才能实际执行交易
--    这里先建 binding，account_id 可后续补充
-- ───────────────────────────────────────────────────────────────
INSERT INTO `dim_strategy_binding` (
    `user_id`, `strategy_code`, `account_id`,
    `capital`, `leverage`, `risk_mode`, `amount_usdt`,
    `status`
)
SELECT
    66,
    'smc_fibo_flex',
    COALESCE((SELECT id FROM `fact_exchange_account` WHERE user_id = 66 LIMIT 1), 0),
    1000.00, 20, 1, 200.00,
    1
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM `dim_strategy_binding` 
    WHERE user_id = 66 AND strategy_code = 'smc_fibo_flex'
);


-- ═══════════════════════════════════════════════════════════════
-- 验证
-- ═══════════════════════════════════════════════════════════════
SELECT id, code, name, risk_level, risk_mode, amount_usdt, capital, leverage, status
FROM dim_strategy
WHERE code LIKE 'smc_fibo_flex%'
ORDER BY risk_level;

SELECT ts.id, ts.tenant_id, ts.strategy_id, s.code, ts.display_name, ts.risk_mode, ts.status
FROM dim_tenant_strategy ts
JOIN dim_strategy s ON s.id = ts.strategy_id
WHERE ts.tenant_id = 2
ORDER BY ts.sort_order;

SELECT id, user_id, strategy_code, capital, leverage, risk_mode, status
FROM dim_strategy_binding
WHERE user_id = 66;
