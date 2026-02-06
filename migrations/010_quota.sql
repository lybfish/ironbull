-- 010_quota.sql  配额计费体系
-- dim_quota_plan: 套餐定义
-- fact_api_usage: 每日 API 调用计数（按租户+日期聚合）
-- dim_tenant: 新增 quota_plan_id 关联套餐

-- 1. 套餐表
CREATE TABLE IF NOT EXISTS `dim_quota_plan` (
    `id`                    INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `name`                  VARCHAR(64)  NOT NULL COMMENT '套餐名称（如 Free/Basic/Pro/Enterprise）',
    `code`                  VARCHAR(32)  NOT NULL COMMENT '套餐编码（唯一标识）',
    `api_calls_daily`       INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '每日 API 调用上限（0=不限）',
    `api_calls_monthly`     INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '每月 API 调用上限（0=不限）',
    `max_users`             INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '最大用户数（0=不限）',
    `max_strategies`        INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '最大策略绑定数（0=不限）',
    `max_exchange_accounts` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '最大交易所账户数（0=不限）',
    `price_monthly`         DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '月费（元，0=免费）',
    `description`           VARCHAR(255) NOT NULL DEFAULT '' COMMENT '套餐说明',
    `status`                TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
    `sort_order`            INT NOT NULL DEFAULT 0 COMMENT '排序',
    `created_at`            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='套餐定义表';

-- 2. 预置套餐
INSERT INTO `dim_quota_plan` (`name`, `code`, `api_calls_daily`, `api_calls_monthly`, `max_users`, `max_strategies`, `max_exchange_accounts`, `price_monthly`, `description`, `sort_order`)
VALUES
    ('免费版', 'free',       100,   3000,   5,   2,   2,   0.00,  '基础功能，适合体验', 1),
    ('基础版', 'basic',     1000,  30000,  20,  10,  10,  99.00,  '标准功能，适合小团队', 2),
    ('专业版', 'pro',       5000, 150000,  100, 50,  50, 399.00,  '高级功能，适合专业交易团队', 3),
    ('企业版', 'enterprise',   0,      0,    0,   0,   0,   0.00,  '无限制，联系商务定价', 4)
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- 3. 每日 API 用量统计表
CREATE TABLE IF NOT EXISTS `fact_api_usage` (
    `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `tenant_id`     INT UNSIGNED NOT NULL COMMENT '租户ID',
    `usage_date`    DATE NOT NULL COMMENT '统计日期',
    `api_calls`     INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '当日调用次数',
    `created_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_tenant_date` (`tenant_id`, `usage_date`),
    KEY `idx_date` (`usage_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日API用量统计';

-- 4. dim_tenant 新增 quota_plan_id（默认 free）
ALTER TABLE `dim_tenant`
    ADD COLUMN `quota_plan_id` INT UNSIGNED NULL DEFAULT NULL COMMENT '套餐ID，关联 dim_quota_plan' AFTER `status`;
