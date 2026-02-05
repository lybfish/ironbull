-- ============================================================
-- Execution Nodes (子服务器/执行节点)
-- 表：dim_execution_node
-- fact_exchange_account 增加 execution_node_id
-- ============================================================

-- 1. dim_execution_node - 执行节点表
CREATE TABLE IF NOT EXISTS `dim_execution_node` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `node_code` VARCHAR(32) NOT NULL COMMENT '节点唯一码',
    `name` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '节点名称',
    `base_url` VARCHAR(255) NOT NULL COMMENT '节点 base URL 如 http://192.168.1.10:9101',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '1在线 0禁用',
    `last_heartbeat_at` DATETIME NULL COMMENT '最后心跳时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_node_code` (`node_code`),
    INDEX `idx_node_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='执行节点表';


-- 2. fact_exchange_account 增加 execution_node_id（可选，NULL 或 0 表示本机执行）
ALTER TABLE `fact_exchange_account`
    ADD COLUMN `execution_node_id` INT UNSIGNED NULL DEFAULT NULL COMMENT '执行节点ID，空=本机' AFTER `status`,
    ADD INDEX `idx_account_node` (`execution_node_id`);
