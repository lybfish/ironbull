-- ═══════════════════════════════════════════════════════════════
-- smc_fibo_flex 策略部署脚本 (v2 精简版)
-- 包含：
--   1) 限价挂单追踪表
--   2) 加 max_loss_per_trade 字段 (binding + tenant_strategy)
--   3) 清理多余策略，只保留 smc_fibo_flex
--   4) 策略配置更新
--   5) 租户2的展示配置 + 用户绑定
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
-- 2. 新增 max_loss_per_trade 字段
--    用户直接填每单最大亏损金额，替代 capital × risk_pct 间接计算
-- ───────────────────────────────────────────────────────────────

-- 策略绑定表
ALTER TABLE `dim_strategy_binding`
    ADD COLUMN IF NOT EXISTS `max_loss_per_trade` DECIMAL(20,2) DEFAULT NULL
    COMMENT '每单最大亏损(USDT)，设置后优先于 capital×risk_pct' AFTER `risk_mode`;

-- 租户策略实例表
ALTER TABLE `dim_tenant_strategy`
    ADD COLUMN IF NOT EXISTS `max_loss_per_trade` DECIMAL(20,2) DEFAULT NULL
    COMMENT '每单最大亏损(USDT)，设置后优先于 capital×risk_pct' AFTER `risk_mode`;

-- 策略主表
ALTER TABLE `dim_strategy`
    ADD COLUMN IF NOT EXISTS `max_loss_per_trade` DECIMAL(20,2) DEFAULT NULL
    COMMENT '每单最大亏损(USDT)默认值' AFTER `risk_mode`;


-- ───────────────────────────────────────────────────────────────
-- 3. 清理多余策略（只保留 smc_fibo_flex）
-- ───────────────────────────────────────────────────────────────

-- 先删绑定
DELETE FROM `dim_strategy_binding` WHERE `strategy_code` IN ('smc_fibo_flex_balanced', 'smc_fibo_flex_aggressive');

-- 再删租户策略
DELETE ts FROM `dim_tenant_strategy` ts
JOIN `dim_strategy` s ON s.id = ts.strategy_id
WHERE s.code IN ('smc_fibo_flex_balanced', 'smc_fibo_flex_aggressive');

-- 最后删策略本体
DELETE FROM `dim_strategy` WHERE `code` IN ('smc_fibo_flex_balanced', 'smc_fibo_flex_aggressive');


-- ───────────────────────────────────────────────────────────────
-- 4. 更新 smc_fibo_flex 策略配置
-- ───────────────────────────────────────────────────────────────

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

UPDATE `dim_strategy` SET
    `name`              = 'SMC结构策略',
    `risk_level`        = 1,
    `risk_mode`         = NULL,
    `max_loss_per_trade` = 20.00,
    `amount_usdt`       = 200.00,
    `user_display_name` = 'SMC斐波那契 Pro',
    `user_description`  = '基于Smart Money概念的结构突破+斐波那契回踩限价入场策略。以损定仓，用户可直接设置每笔最大亏损金额，系统根据止损距离自动计算仓位。回测胜率62%，盈亏比2.58:1，最大回撤6.2%。',
    `config`            = @smc_config
WHERE `code` = 'smc_fibo_flex';


-- ───────────────────────────────────────────────────────────────
-- 5. 租户2的展示配置
-- ───────────────────────────────────────────────────────────────

-- 清理旧的多余租户策略，只保留 smc_fibo_flex
DELETE ts FROM `dim_tenant_strategy` ts
JOIN `dim_strategy` s ON s.id = ts.strategy_id
WHERE ts.tenant_id = 2 AND s.code = 'smc_fibo_flex';

INSERT INTO `dim_tenant_strategy` (
    `tenant_id`, `strategy_id`, `display_name`, `display_description`,
    `leverage`, `capital`, `risk_mode`, `max_loss_per_trade`, `amount_usdt`, `min_capital`,
    `status`, `sort_order`
)
SELECT
    2,
    s.id,
    'SMC斐波那契 Pro',
    '基于Smart Money概念的结构突破+斐波那契回踩限价入场策略。以损定仓，设置每笔最大亏损即可，系统根据止损距离自动计算仓位。',
    20, 200.00, NULL, 20.00, NULL, 200.00,
    1, 1
FROM `dim_strategy` s WHERE s.code = 'smc_fibo_flex';


-- ───────────────────────────────────────────────────────────────
-- 6. 租户2用户(id=66) 绑定
-- ───────────────────────────────────────────────────────────────

-- 更新已有绑定的 max_loss_per_trade
UPDATE `dim_strategy_binding` SET
    `max_loss_per_trade` = 20.00,
    `capital` = 200.00,
    `risk_mode` = NULL
WHERE user_id = 66 AND strategy_code = 'smc_fibo_flex';

-- 如果不存在则创建
INSERT INTO `dim_strategy_binding` (
    `user_id`, `strategy_code`, `account_id`,
    `capital`, `leverage`, `risk_mode`, `max_loss_per_trade`,
    `status`
)
SELECT
    66,
    'smc_fibo_flex',
    COALESCE((SELECT id FROM `fact_exchange_account` WHERE user_id = 66 LIMIT 1), 0),
    200.00, 20, NULL, 20.00,
    1
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM `dim_strategy_binding` 
    WHERE user_id = 66 AND strategy_code = 'smc_fibo_flex'
);


-- ═══════════════════════════════════════════════════════════════
-- 验证
-- ═══════════════════════════════════════════════════════════════
SELECT id, code, name, risk_level, risk_mode, max_loss_per_trade, amount_usdt, capital, leverage, status
FROM dim_strategy
WHERE code LIKE 'smc_fibo_flex%';

SELECT ts.id, ts.tenant_id, ts.strategy_id, s.code, ts.display_name, ts.max_loss_per_trade, ts.risk_mode, ts.status
FROM dim_tenant_strategy ts
JOIN dim_strategy s ON s.id = ts.strategy_id
WHERE ts.tenant_id = 2;

SELECT id, user_id, strategy_code, capital, leverage, risk_mode, max_loss_per_trade, status
FROM dim_strategy_binding
WHERE user_id = 66;
