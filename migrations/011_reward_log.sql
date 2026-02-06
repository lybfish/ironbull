-- 011_reward_log.sql
-- 新增奖励余额流水表 fact_reward_log，记录所有 reward_usdt 变动

CREATE TABLE IF NOT EXISTS `fact_reward_log` (
    `id`             BIGINT       NOT NULL AUTO_INCREMENT,
    `user_id`        INT          NOT NULL,
    `change_type`    VARCHAR(30)  NOT NULL COMMENT 'reward_in / withdraw_freeze / withdraw_reject_return',
    `ref_type`       VARCHAR(30)  DEFAULT NULL COMMENT '关联类型: user_reward / user_withdrawal',
    `ref_id`         BIGINT       DEFAULT NULL COMMENT '关联记录ID',
    `amount`         DECIMAL(20,8) NOT NULL COMMENT '正=增加,负=减少',
    `before_balance` DECIMAL(20,8) NOT NULL DEFAULT 0,
    `after_balance`  DECIMAL(20,8) NOT NULL DEFAULT 0,
    `remark`         VARCHAR(255) DEFAULT NULL,
    `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_change_type` (`change_type`),
    KEY `idx_ref` (`ref_type`, `ref_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='奖励余额流水表';
