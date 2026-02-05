-- ============================================================
-- IronBull Platform Layer Migration
-- 多租户用户体系：租户、会员、点卡、奖励、策略
-- ============================================================
-- 表：dim_tenant, dim_user, fact_account, dim_strategy,
--     dim_strategy_binding, fact_point_card_log, fact_profit_pool,
--     fact_user_reward, fact_user_withdrawal, dim_level_config, fact_api_log
-- ============================================================

-- 1. dim_tenant - 租户/代理商表
CREATE TABLE IF NOT EXISTS `dim_tenant` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL COMMENT '代理商名称',
    `app_key` VARCHAR(64) NOT NULL COMMENT 'API Key',
    `app_secret` VARCHAR(128) NOT NULL COMMENT 'API Secret',
    `root_user_id` INT UNSIGNED NULL COMMENT '根用户ID',
    `point_card_self` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '自充点卡余额',
    `point_card_gift` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '赠送点卡余额',
    `total_users` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '用户总数',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '状态 1正常 0禁用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_tenant_app_key` (`app_key`),
    INDEX `idx_tenant_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户/代理商表';


-- 2. dim_user - 会员表（id 即 member_id）
CREATE TABLE IF NOT EXISTS `dim_user` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `tenant_id` INT UNSIGNED NOT NULL COMMENT '所属代理商',
    `email` VARCHAR(100) NOT NULL COMMENT '邮箱/登录账号',
    `password_hash` VARCHAR(128) NULL COMMENT '密码哈希',
    `is_root` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否根用户 0否 1是',
    `invite_code` VARCHAR(8) NOT NULL COMMENT '邀请码(8位数字)',
    `inviter_id` INT UNSIGNED NULL COMMENT '邀请人ID',
    `inviter_path` VARCHAR(500) NULL COMMENT '邀请链路 如 1/3/6',
    `point_card_self` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '自充点卡余额',
    `point_card_gift` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '赠送点卡余额',
    `member_level` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '会员等级 0-7 S0-S7',
    `is_market_node` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否市场节点 0否 1是',
    `team_performance` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '团队业绩',
    `reward_usdt` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '可用奖励余额',
    `total_reward` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计获得奖励',
    `withdrawn_reward` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '已提现奖励',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '状态 1正常 0禁用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_user_invite_code` (`invite_code`),
    UNIQUE KEY `uk_user_tenant_email` (`tenant_id`, `email`),
    INDEX `idx_user_tenant` (`tenant_id`),
    INDEX `idx_user_inviter` (`inviter_id`),
    INDEX `idx_user_status` (`status`),
    CONSTRAINT `fk_user_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `dim_tenant` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_user_inviter` FOREIGN KEY (`inviter_id`) REFERENCES `dim_user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会员表';


-- 3. fact_exchange_account - 交易所账户表（API 绑定，与 ledger.fact_account 区分）
CREATE TABLE IF NOT EXISTS `fact_exchange_account` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT UNSIGNED NOT NULL COMMENT '所属会员',
    `tenant_id` INT UNSIGNED NOT NULL COMMENT '所属代理商',
    `exchange` VARCHAR(32) NOT NULL COMMENT '交易所 binance/okx/bybit',
    `account_type` VARCHAR(16) NOT NULL DEFAULT 'futures' COMMENT '账户类型',
    `api_key` VARCHAR(255) NOT NULL COMMENT 'API Key',
    `api_secret` VARCHAR(255) NOT NULL COMMENT 'API Secret',
    `passphrase` VARCHAR(255) NULL COMMENT '部分交易所需要 如OKX',
    `balance` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '现货余额',
    `futures_balance` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '合约余额',
    `futures_available` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '合约可用余额',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '1启用 0禁用',
    `last_sync_at` DATETIME NULL COMMENT '最后同步时间',
    `last_sync_error` VARCHAR(255) NULL COMMENT '最后同步错误',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_account_user_exchange` (`user_id`, `exchange`, `account_type`),
    INDEX `idx_account_user` (`user_id`),
    INDEX `idx_account_tenant` (`tenant_id`),
    INDEX `idx_account_exchange` (`exchange`),
    CONSTRAINT `fk_account_user` FOREIGN KEY (`user_id`) REFERENCES `dim_user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_account_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `dim_tenant` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交易所账户表（API绑定）';


-- 4. dim_strategy - 策略目录表
CREATE TABLE IF NOT EXISTS `dim_strategy` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `code` VARCHAR(64) NOT NULL COMMENT '策略代码 与 Signal.strategy_code 对应',
    `name` VARCHAR(100) NOT NULL COMMENT '策略名称',
    `description` VARCHAR(500) NULL COMMENT '策略描述',
    `symbol` VARCHAR(32) NOT NULL COMMENT '交易对',
    `timeframe` VARCHAR(8) NULL COMMENT '时间周期',
    `min_capital` DECIMAL(20,2) NOT NULL DEFAULT 200 COMMENT '最低资金',
    `risk_level` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '风险等级 1低 2中 3高',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
    `config` JSON NULL COMMENT '策略配置参数',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_strategy_code` (`code`),
    INDEX `idx_strategy_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略目录表';


-- 5. dim_strategy_binding - 用户策略订阅表
CREATE TABLE IF NOT EXISTS `dim_strategy_binding` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT UNSIGNED NOT NULL COMMENT '会员ID',
    `account_id` INT UNSIGNED NOT NULL COMMENT '账户ID',
    `strategy_code` VARCHAR(64) NOT NULL COMMENT '策略代码',
    `mode` TINYINT UNSIGNED NOT NULL DEFAULT 2 COMMENT '1单次执行 2循环执行',
    `ratio` INT UNSIGNED NOT NULL DEFAULT 100 COMMENT '跟单比例',
    `total_profit` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计盈亏',
    `total_trades` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '累计交易次数',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_binding_account_strategy` (`account_id`, `strategy_code`),
    INDEX `idx_binding_user` (`user_id`),
    INDEX `idx_binding_strategy` (`strategy_code`),
    CONSTRAINT `fk_binding_user` FOREIGN KEY (`user_id`) REFERENCES `dim_user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_binding_account` FOREIGN KEY (`account_id`) REFERENCES `fact_exchange_account` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户策略订阅表';


-- 6. fact_point_card_log - 点卡流水表
CREATE TABLE IF NOT EXISTS `fact_point_card_log` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `tenant_id` INT UNSIGNED NULL COMMENT '代理商ID(代理商流水时)',
    `user_id` INT UNSIGNED NULL COMMENT '会员ID(会员流水时)',
    `related_user_id` INT UNSIGNED NULL COMMENT '关联会员ID(互转时)',
    `change_type` TINYINT UNSIGNED NOT NULL COMMENT '1充值 2赠送 3转出 4转入 5扣费',
    `source_type` TINYINT UNSIGNED NOT NULL COMMENT '1后台 2代理商分发 3盈利扣费 4用户互转',
    `card_type` TINYINT UNSIGNED NOT NULL COMMENT '1=self 2=gift',
    `amount` DECIMAL(20,8) NOT NULL COMMENT '变更金额 正负',
    `before_self` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '变更前self余额',
    `after_self` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '变更后self余额',
    `before_gift` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '变更前gift余额',
    `after_gift` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '变更后gift余额',
    `remark` VARCHAR(255) NULL COMMENT '备注',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_pcl_tenant` (`tenant_id`),
    INDEX `idx_pcl_user` (`user_id`),
    INDEX `idx_pcl_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='点卡流水表';


-- 7. fact_profit_pool - 利润池表
CREATE TABLE IF NOT EXISTS `fact_profit_pool` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT UNSIGNED NOT NULL COMMENT '产生盈利的会员',
    `profit_amount` DECIMAL(20,8) NOT NULL COMMENT '盈利金额',
    `deduct_amount` DECIMAL(20,8) NOT NULL COMMENT '扣除点卡总额(30%)',
    `self_deduct` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '扣除self部分',
    `gift_deduct` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '扣除gift部分',
    `pool_amount` DECIMAL(20,8) NOT NULL COMMENT '进入利润池金额(仅self)',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '1待结算 2已结算',
    `settle_batch` VARCHAR(50) NULL COMMENT '结算批次号',
    `settled_at` DATETIME NULL COMMENT '结算时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_pp_user` (`user_id`),
    INDEX `idx_pp_status` (`status`),
    CONSTRAINT `fk_pp_user` FOREIGN KEY (`user_id`) REFERENCES `dim_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='利润池表';


-- 8. fact_user_reward - 奖励流水表
CREATE TABLE IF NOT EXISTS `fact_user_reward` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT UNSIGNED NOT NULL COMMENT '获得奖励的会员',
    `source_user_id` INT UNSIGNED NULL COMMENT '贡献利润的会员',
    `profit_pool_id` BIGINT UNSIGNED NULL COMMENT '关联利润池',
    `reward_type` VARCHAR(20) NOT NULL COMMENT 'direct/level_diff/peer/tech_team',
    `amount` DECIMAL(20,8) NOT NULL COMMENT '奖励金额',
    `rate` DECIMAL(10,4) NULL COMMENT '奖励比例',
    `from_level` TINYINT UNSIGNED NULL COMMENT '来源会员等级',
    `to_level` TINYINT UNSIGNED NULL COMMENT '获奖会员等级',
    `settle_batch` VARCHAR(50) NULL COMMENT '结算批次号',
    `remark` VARCHAR(255) NULL COMMENT '备注',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_ur_user` (`user_id`),
    INDEX `idx_ur_source` (`source_user_id`),
    INDEX `idx_ur_type` (`reward_type`),
    CONSTRAINT `fk_ur_user` FOREIGN KEY (`user_id`) REFERENCES `dim_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='奖励流水表';


-- 9. fact_user_withdrawal - 提现记录表
CREATE TABLE IF NOT EXISTS `fact_user_withdrawal` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT UNSIGNED NOT NULL COMMENT '会员ID',
    `amount` DECIMAL(20,8) NOT NULL COMMENT '提现金额',
    `fee` DECIMAL(20,8) NOT NULL COMMENT '手续费(5%)',
    `actual_amount` DECIMAL(20,8) NOT NULL COMMENT '实际到账金额',
    `wallet_address` VARCHAR(128) NOT NULL COMMENT '钱包地址',
    `wallet_network` VARCHAR(20) NOT NULL DEFAULT 'TRC20' COMMENT '网络类型',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '0待审核 1已通过 2已拒绝 3已完成',
    `tx_hash` VARCHAR(128) NULL COMMENT '链上交易哈希',
    `reject_reason` VARCHAR(255) NULL COMMENT '拒绝原因',
    `audit_by` INT UNSIGNED NULL COMMENT '审核人',
    `audit_at` DATETIME NULL COMMENT '审核时间',
    `completed_at` DATETIME NULL COMMENT '完成时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_wd_user` (`user_id`),
    INDEX `idx_wd_status` (`status`),
    CONSTRAINT `fk_wd_user` FOREIGN KEY (`user_id`) REFERENCES `dim_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='提现记录表';


-- 10. dim_level_config - 等级配置表
CREATE TABLE IF NOT EXISTS `dim_level_config` (
    `level` TINYINT UNSIGNED NOT NULL PRIMARY KEY COMMENT '等级 0-7',
    `level_name` VARCHAR(10) NOT NULL COMMENT '等级名称 S0-S7',
    `min_team_perf` DECIMAL(20,2) NOT NULL COMMENT '最低团队业绩',
    `diff_rate` DECIMAL(10,4) NOT NULL COMMENT '级差比例',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='等级配置表';

INSERT INTO `dim_level_config` (`level`, `level_name`, `min_team_perf`, `diff_rate`) VALUES
(0, 'S0', 0, 0.0000),
(1, 'S1', 10000, 0.2000),
(2, 'S2', 50000, 0.3000),
(3, 'S3', 200000, 0.4000),
(4, 'S4', 500000, 0.5000),
(5, 'S5', 1000000, 0.6000),
(6, 'S6', 3000000, 0.7000),
(7, 'S7', 10000000, 0.8000);


-- 11. fact_api_log - API 调用日志表
CREATE TABLE IF NOT EXISTS `fact_api_log` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `tenant_id` INT UNSIGNED NULL COMMENT '代理商ID',
    `endpoint` VARCHAR(128) NOT NULL COMMENT '请求路径',
    `method` VARCHAR(16) NOT NULL COMMENT 'HTTP方法',
    `request_body` TEXT NULL COMMENT '请求体(敏感字段脱敏)',
    `response_code` INT NULL COMMENT '响应code',
    `response_msg` VARCHAR(255) NULL COMMENT '响应msg',
    `ip` VARCHAR(64) NULL COMMENT '客户端IP',
    `duration_ms` INT NULL COMMENT '耗时毫秒',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_apilog_tenant` (`tenant_id`),
    INDEX `idx_apilog_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API调用日志表';


SELECT 'Platform Layer (007) tables created successfully!' AS result;
