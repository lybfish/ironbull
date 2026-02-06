-- ============================================================
-- 后台管理员表（dim_admin）
-- 独立于 dim_tenant / dim_user，用于管理后台(admin-web)登录
-- 平台级超管，可查看所有租户数据
-- ============================================================

CREATE TABLE IF NOT EXISTS `dim_admin` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(64) NOT NULL COMMENT '登录用户名',
    `password_hash` VARCHAR(128) NOT NULL COMMENT '密码哈希(MD5)',
    `nickname` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '显示昵称',
    `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '1正常 0禁用',
    `last_login_at` DATETIME NULL COMMENT '最后登录时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='后台管理员表';

-- 初始超管账号（密码 admin123，MD5: 0192023a7bbd73250516f069df18b500）
INSERT INTO `dim_admin` (`username`, `password_hash`, `nickname`, `status`)
VALUES ('admin', '0192023a7bbd73250516f069df18b500', '超级管理员', 1)
ON DUPLICATE KEY UPDATE `username` = `username`;
