-- 策略目录：区分「内部目录」与「对用户可见」
-- 仅 show_to_user=1 的策略会对 C 端/商户 API 展示；用户展示名称/描述可单独配置

ALTER TABLE `dim_strategy`
    ADD COLUMN `show_to_user` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否对用户/商户展示 0否 1是' AFTER `status`,
    ADD COLUMN `user_display_name` VARCHAR(100) NULL COMMENT '对用户展示的名称，空则用 name' AFTER `show_to_user`,
    ADD COLUMN `user_description` VARCHAR(500) NULL COMMENT '对用户展示的描述，空则用 description' AFTER `user_display_name`;

-- 可选：将当前已启用的策略默认对用户可见（执行后可按需在管理后台关闭）
-- UPDATE `dim_strategy` SET `show_to_user` = 1 WHERE `status` = 1;
