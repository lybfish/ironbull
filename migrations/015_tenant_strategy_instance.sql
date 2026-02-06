-- 租户策略实例表：每个租户下「对用户展示」的策略列表，可覆盖杠杆等参数，关联主策略表
-- 用户侧看到的策略 = 该租户的 strategy instance 列表（join dim_strategy 取主策略信息）
-- 可一键从主策略复制参数到实例

CREATE TABLE IF NOT EXISTS `dim_tenant_strategy` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `tenant_id` INT UNSIGNED NOT NULL COMMENT '租户ID',
    `strategy_id` INT UNSIGNED NOT NULL COMMENT '主策略ID dim_strategy.id',
    `display_name` VARCHAR(100) NULL COMMENT '租户侧展示名称，空则用主策略 name',
    `display_description` VARCHAR(500) NULL COMMENT '租户侧展示描述，空则用主策略 description',
    `leverage` INT NULL COMMENT '杠杆倍数覆盖，空则用主策略',
    `amount_usdt` DECIMAL(20,2) NULL COMMENT '单笔金额(USDT)覆盖，空则用主策略',
    `min_capital` DECIMAL(20,2) NULL COMMENT '最低资金覆盖，空则用主策略',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '1=对租户用户展示 0=不展示',
    `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_tenant_strategy` (`tenant_id`, `strategy_id`),
    INDEX `idx_ts_tenant` (`tenant_id`),
    INDEX `idx_ts_strategy` (`strategy_id`),
    INDEX `idx_ts_status` (`status`),
    CONSTRAINT `fk_ts_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `dim_tenant` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ts_strategy` FOREIGN KEY (`strategy_id`) REFERENCES `dim_strategy` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户策略实例（租户下对用户展示的策略及覆盖参数）';
