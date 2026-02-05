/*
 Navicat Premium Dump SQL

 Source Server         : 127.0.0.1
 Source Server Type    : MySQL
 Source Server Version : 90001 (9.0.1)
 Source Host           : localhost:3306
 Source Schema         : quanttrade

 Target Server Type    : MySQL
 Target Server Version : 90001 (9.0.1)
 File Encoding         : 65001

 Date: 04/02/2026 14:23:04
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for action_log_2026_02
-- ----------------------------
DROP TABLE IF EXISTS `action_log_2026_02`;
CREATE TABLE `action_log_2026_02` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '唯一性标识',
  `username` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '操作人用户名',
  `method` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '请求类型',
  `module` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '模型',
  `url` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '操作页面',
  `param` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '请求参数(JSON格式)',
  `title` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '日志标题',
  `type` tinyint unsigned DEFAULT '0' COMMENT '操作类型：1登录系统 2注销系统 3操作日志',
  `content` varchar(1000) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '内容',
  `ip` varchar(18) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'IP地址',
  `ip_city` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'IP所属城市',
  `os` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '操作系统',
  `browser` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '浏览器',
  `user_agent` varchar(360) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'User-Agent',
  `create_user` int unsigned DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned DEFAULT '0' COMMENT '添加时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识：1正常 0删除',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=COMPACT COMMENT='系统行为日志表';

-- ----------------------------
-- Records of action_log_2026_02
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_account_balance_history
-- ----------------------------
DROP TABLE IF EXISTS `think_account_balance_history`;
CREATE TABLE `think_account_balance_history` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `account_id` int unsigned NOT NULL,
  `member_id` int unsigned DEFAULT '0',
  `balance` decimal(20,4) DEFAULT '0.0000',
  `available` decimal(20,4) DEFAULT '0.0000',
  `create_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_account_time` (`account_id`,`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='账户余额历史表';

-- ----------------------------
-- Records of think_account_balance_history
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_account_snapshot
-- ----------------------------
DROP TABLE IF EXISTS `think_account_snapshot`;
CREATE TABLE `think_account_snapshot` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '账户ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `balance` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总余额',
  `available` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '可用余额',
  `margin` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '已用保证金',
  `unrealized_pnl` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '未实现盈亏',
  `equity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '权益',
  `snapshot_time` int unsigned NOT NULL DEFAULT '0' COMMENT '快照时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_account_time` (`account_id`,`snapshot_time`),
  KEY `idx_member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='账户余额快照表';

-- ----------------------------
-- Records of think_account_snapshot
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_account_statistics
-- ----------------------------
DROP TABLE IF EXISTS `think_account_statistics`;
CREATE TABLE `think_account_statistics` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '账户ID',
  `stat_date` date NOT NULL COMMENT '统计日期',
  `total_profit` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '总收益',
  `total_volume` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '总成交额',
  `win_rate` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '胜率(%)',
  `max_drawdown` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '最大回撤(%)',
  `trade_count` int unsigned NOT NULL DEFAULT '0' COMMENT '交易次数',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_account_date` (`account_id`,`stat_date`) USING BTREE,
  KEY `idx_stat_date` (`stat_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='账户统计表';

-- ----------------------------
-- Records of think_account_statistics
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_action_log_2026_01
-- ----------------------------
DROP TABLE IF EXISTS `think_action_log_2026_01`;
CREATE TABLE `think_action_log_2026_01` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '唯一性标识',
  `username` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作人用户名',
  `method` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '请求类型',
  `module` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '模型',
  `url` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作页面',
  `param` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '请求参数(JSON格式)',
  `title` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '日志标题',
  `type` tinyint unsigned DEFAULT '0' COMMENT '操作类型：1登录系统 2注销系统 3操作日志',
  `content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '内容',
  `ip` varchar(18) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'IP地址',
  `ip_city` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'IP所属城市',
  `os` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作系统',
  `browser` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '浏览器',
  `user_agent` varchar(360) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'User-Agent',
  `create_user` int unsigned DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned DEFAULT '0' COMMENT '添加时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识：1正常 0删除',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统行为日志表';

-- ----------------------------
-- Records of think_action_log_2026_01
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_agent
-- ----------------------------
DROP TABLE IF EXISTS `think_agent`;
CREATE TABLE `think_agent` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `agent_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '代理商编号',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '代理商名称',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '登录用户名',
  `password` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '登录密码',
  `contact` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '联系方式',
  `mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '手机号',
  `telegram_chat_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Telegram Chat ID',
  `wallet_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '钱包地址',
  `level_id` int unsigned NOT NULL DEFAULT '0' COMMENT '等级ID',
  `app_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'API凭证名称',
  `app_secret` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'API密钥',
  `api_status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT 'API状态: 1启用 2禁用',
  `rate` decimal(5,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '分成比例(%)',
  `total_users` int unsigned NOT NULL DEFAULT '0' COMMENT '交易账户数量',
  `total_earnings` decimal(20,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '总收益',
  `type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '类型：1金牌 2普通 3只读',
  `share_ratio` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '分成比例',
  `balance` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '账户余额',
  `frozen_balance` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '冻结余额',
  `point_card_self` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '自充点卡余额',
  `point_card_gift` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '赠送点卡余额',
  `root_member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '根用户ID',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2停用 3待审核',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_agent_no` (`agent_no`) USING BTREE,
  UNIQUE KEY `uk_username` (`username`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_api_status` (`api_status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理商表';

-- ----------------------------
-- Records of think_agent
-- ----------------------------
BEGIN;
INSERT INTO `think_agent` (`id`, `agent_no`, `name`, `username`, `password`, `contact`, `mobile`, `telegram_chat_id`, `wallet_address`, `level_id`, `app_name`, `app_secret`, `api_status`, `rate`, `total_users`, `total_earnings`, `type`, `share_ratio`, `balance`, `frozen_balance`, `point_card_self`, `point_card_gift`, `root_member_id`, `status`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, '', '代理1', 'daili1', '$2y$10$ss80hQB4xs9tUf1by7xKne7s3R3gkhP/XpjuOo0KiprvrMM9mg396', '18600000000', '18600000000', '', '', 0, 'agent_daili1_1769883790', 'c09c72d591b54f223c8f3007c4646de9', 1, 0.00, 4, 0.00000000, 1, 0.30, 0.00, 0.00, 900.00, 450.00, 1, 1, '', 1, 1769883790, 1, 1770128856, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_agent_account
-- ----------------------------
DROP TABLE IF EXISTS `think_agent_account`;
CREATE TABLE `think_agent_account` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `agent_id` int unsigned NOT NULL DEFAULT '0' COMMENT '代理商ID',
  `balance` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '账户余额',
  `frozen_balance` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '冻结余额',
  `total_commission` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '累计佣金',
  `total_withdrawal` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '累计提现',
  `total_income` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '累计收入',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_agent_id` (`agent_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理商账户表';

-- ----------------------------
-- Records of think_agent_account
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_agent_address_change
-- ----------------------------
DROP TABLE IF EXISTS `think_agent_address_change`;
CREATE TABLE `think_agent_address_change` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `agent_id` int unsigned NOT NULL DEFAULT '0' COMMENT '代理商ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '代理商名称',
  `old_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '原收款地址',
  `new_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '新收款地址',
  `reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更原因',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '审核状态：1待审核 2已通过 3已拒绝',
  `apply_time` int unsigned NOT NULL DEFAULT '0' COMMENT '申请时间',
  `audit_time` int unsigned NOT NULL DEFAULT '0' COMMENT '审核时间',
  `audit_user` int unsigned NOT NULL DEFAULT '0' COMMENT '审核人',
  `audit_remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审核备注',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_agent_id` (`agent_id`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理商地址变更审核表';

-- ----------------------------
-- Records of think_agent_address_change
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_agent_api_log
-- ----------------------------
DROP TABLE IF EXISTS `think_agent_api_log`;
CREATE TABLE `think_agent_api_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned DEFAULT NULL,
  `app_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `method` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `params` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `response` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `status` tinyint(1) DEFAULT '1',
  `ip` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT 'IP地址',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_agent_id` (`agent_id`) USING BTREE,
  KEY `idx_agent_created` (`agent_id`) USING BTREE,
  KEY `idx_path` (`path`(191)) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Records of think_agent_api_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_agent_earnings
-- ----------------------------
DROP TABLE IF EXISTS `think_agent_earnings`;
CREATE TABLE `think_agent_earnings` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned NOT NULL,
  `account_id` int unsigned NOT NULL,
  `type` tinyint unsigned NOT NULL DEFAULT '1',
  `amount` decimal(20,8) unsigned NOT NULL DEFAULT '0.00000000',
  `currency` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'USDT',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_agent_id` (`agent_id`) USING BTREE,
  KEY `idx_agent_created` (`agent_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Records of think_agent_earnings
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_agent_level
-- ----------------------------
DROP TABLE IF EXISTS `think_agent_level`;
CREATE TABLE `think_agent_level` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '等级名称',
  `level` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '等级排序',
  `commission_rate` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '佣金分成比例(%)',
  `min_members` int unsigned NOT NULL DEFAULT '0' COMMENT '最少会员数',
  `min_trade_volume` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '最少交易量',
  `icon` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '等级图标',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2禁用',
  `sort` int NOT NULL DEFAULT '0' COMMENT '排序',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_level` (`level`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理商等级表';

-- ----------------------------
-- Records of think_agent_level
-- ----------------------------
BEGIN;
INSERT INTO `think_agent_level` (`id`, `name`, `level`, `commission_rate`, `min_members`, `min_trade_volume`, `icon`, `status`, `sort`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, '普通代理', 1, 20.00, 0, 0.00, NULL, 1, 1, NULL, 0, 0, 0, 0, 1);
INSERT INTO `think_agent_level` (`id`, `name`, `level`, `commission_rate`, `min_members`, `min_trade_volume`, `icon`, `status`, `sort`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, '银牌代理', 2, 30.00, 10, 100000.00, NULL, 1, 2, NULL, 0, 0, 0, 0, 1);
INSERT INTO `think_agent_level` (`id`, `name`, `level`, `commission_rate`, `min_members`, `min_trade_volume`, `icon`, `status`, `sort`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (3, '金牌代理', 3, 40.00, 50, 500000.00, NULL, 1, 3, NULL, 0, 0, 0, 0, 1);
INSERT INTO `think_agent_level` (`id`, `name`, `level`, `commission_rate`, `min_members`, `min_trade_volume`, `icon`, `status`, `sort`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, '钻石代理', 4, 50.00, 100, 2000000.00, NULL, 1, 4, NULL, 0, 0, 0, 0, 1);
INSERT INTO `think_agent_level` (`id`, `name`, `level`, `commission_rate`, `min_members`, `min_trade_volume`, `icon`, `status`, `sort`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (5, '超级代理', 5, 60.00, 500, 10000000.00, NULL, 1, 5, NULL, 0, 0, 0, 0, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_agent_point_card_log
-- ----------------------------
DROP TABLE IF EXISTS `think_agent_point_card_log`;
CREATE TABLE `think_agent_point_card_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `agent_id` int unsigned NOT NULL COMMENT '代理商ID',
  `change_type` tinyint unsigned NOT NULL COMMENT '变更类型：1=后台充值 2=后台赠送 3=分发给用户',
  `source_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '扣除来源：1=自充 2=赠送',
  `amount` decimal(15,2) NOT NULL COMMENT '变更金额',
  `before_self` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '变更前自充余额',
  `after_self` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '变更后自充余额',
  `before_gift` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '变更前赠送余额',
  `after_gift` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '变更后赠送余额',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '关联用户ID（分发时）',
  `to_type` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '充给用户的类型：1=自充 2=赠送',
  `operator_id` int unsigned NOT NULL DEFAULT '0' COMMENT '操作人ID',
  `remark` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_agent_id` (`agent_id`),
  KEY `idx_member_id` (`member_id`),
  KEY `idx_change_type` (`change_type`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理商点卡流水表';

-- ----------------------------
-- Records of think_agent_point_card_log
-- ----------------------------
BEGIN;
INSERT INTO `think_agent_point_card_log` (`id`, `agent_id`, `change_type`, `source_type`, `amount`, `before_self`, `after_self`, `before_gift`, `after_gift`, `member_id`, `to_type`, `operator_id`, `remark`, `create_time`) VALUES (3, 1, 3, 1, -100.00, 1000.00, 900.00, 500.00, 500.00, 7, 1, 0, '分发充值', 1770128850);
INSERT INTO `think_agent_point_card_log` (`id`, `agent_id`, `change_type`, `source_type`, `amount`, `before_self`, `after_self`, `before_gift`, `after_gift`, `member_id`, `to_type`, `operator_id`, `remark`, `create_time`) VALUES (4, 1, 3, 2, -50.00, 900.00, 900.00, 500.00, 450.00, 7, 2, 0, '分发赠送', 1770128850);
COMMIT;

-- ----------------------------
-- Table structure for think_agent_settlement
-- ----------------------------
DROP TABLE IF EXISTS `think_agent_settlement`;
CREATE TABLE `think_agent_settlement` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `settlement_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '结算单号',
  `agent_id` int unsigned NOT NULL DEFAULT '0' COMMENT '代理商ID',
  `amount` decimal(15,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '结算金额',
  `settlement_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '结算类型：1佣金 2返佣 3其他',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1待审核 2已通过 3已拒绝 4已打款',
  `apply_time` int unsigned NOT NULL DEFAULT '0' COMMENT '申请时间',
  `approve_time` int unsigned NOT NULL DEFAULT '0' COMMENT '审核时间',
  `approve_user` int unsigned NOT NULL DEFAULT '0' COMMENT '审核人',
  `bank_info` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '银行信息',
  `transaction_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '交易流水号',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_settlement_no` (`settlement_no`) USING BTREE,
  KEY `idx_agent_id` (`agent_id`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理商结算表';

-- ----------------------------
-- Records of think_agent_settlement
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_alert_rule
-- ----------------------------
DROP TABLE IF EXISTS `think_alert_rule`;
CREATE TABLE `think_alert_rule` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `rule_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则名称',
  `metric_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '指标键',
  `operator` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '>' COMMENT '比较符号',
  `threshold` decimal(15,4) NOT NULL DEFAULT '0.0000' COMMENT '阈值',
  `level` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '告警等级：1低 2中 3高',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2禁用',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_metric_key` (`metric_key`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='告警规则表';

-- ----------------------------
-- Records of think_alert_rule
-- ----------------------------
BEGIN;
INSERT INTO `think_alert_rule` (`id`, `rule_name`, `metric_key`, `operator`, `threshold`, `level`, `status`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, 'CPU使用率告警', 'cpu_usage', '>', 0.8000, 2, 1, 'CPU超过80%告警', 1, 1769169393, 1, 1769169393, 1);
INSERT INTO `think_alert_rule` (`id`, `rule_name`, `metric_key`, `operator`, `threshold`, `level`, `status`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, '内存使用率告警', 'memory_usage', '>', 0.8500, 2, 1, '内存超过85%告警', 1, 1769169393, 1, 1769169393, 1);
INSERT INTO `think_alert_rule` (`id`, `rule_name`, `metric_key`, `operator`, `threshold`, `level`, `status`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (3, '数据库连接占用告警', 'db_conn_usage', '>', 0.9000, 3, 1, '数据库连接超过90%告警', 1, 1769169393, 1, 1769169393, 1);
INSERT INTO `think_alert_rule` (`id`, `rule_name`, `metric_key`, `operator`, `threshold`, `level`, `status`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, '队列延迟告警', 'queue_lag_ms', '>', 500.0000, 2, 1, '队列延迟超过500ms告警', 1, 1769169393, 1, 1769169393, 1);
INSERT INTO `think_alert_rule` (`id`, `rule_name`, `metric_key`, `operator`, `threshold`, `level`, `status`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (5, '订单失败率告警', 'order_fail_rate', '>', 0.0500, 2, 1, '订单失败率超过5%告警', 1, 1769169393, 1, 1769169393, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_announcement
-- ----------------------------
DROP TABLE IF EXISTS `think_announcement`;
CREATE TABLE `think_announcement` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL DEFAULT '' COMMENT '标题',
  `content` text COMMENT '内容',
  `summary` varchar(500) DEFAULT '' COMMENT '摘要',
  `cover` varchar(255) DEFAULT '' COMMENT '封面图',
  `category` varchar(30) DEFAULT 'notice' COMMENT '分类: notice公告 activity活动 update更新 warning警告',
  `is_top` tinyint DEFAULT '0' COMMENT '是否置顶',
  `is_popup` tinyint DEFAULT '0' COMMENT '是否弹窗',
  `popup_once` tinyint DEFAULT '1' COMMENT '弹窗仅显示一次',
  `publish_time` int unsigned DEFAULT '0' COMMENT '发布时间',
  `expire_time` int unsigned DEFAULT '0' COMMENT '过期时间(0=不过期)',
  `view_count` int DEFAULT '0' COMMENT '浏览次数',
  `status` tinyint DEFAULT '0' COMMENT '状态:0草稿 1已发布 2已下架',
  `author_id` int unsigned DEFAULT '0' COMMENT '作者ID',
  `sort` int DEFAULT '0' COMMENT '排序',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_category` (`category`),
  KEY `idx_publish` (`publish_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统公告表';

-- ----------------------------
-- Records of think_announcement
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_api_alert_config
-- ----------------------------
DROP TABLE IF EXISTS `think_api_alert_config`;
CREATE TABLE `think_api_alert_config` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(64) NOT NULL DEFAULT '' COMMENT '告警名称',
  `exchange` varchar(32) NOT NULL DEFAULT '' COMMENT '交易所(空=全部)',
  `api_type` varchar(32) NOT NULL DEFAULT '' COMMENT 'API类型(空=全部)',
  `alert_type` tinyint(1) NOT NULL DEFAULT '1' COMMENT '告警类型:1=响应超时,2=失败率过高,3=连续失败',
  `threshold_value` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '阈值',
  `threshold_unit` varchar(16) NOT NULL DEFAULT '' COMMENT '阈值单位:ms,%,次',
  `notify_telegram` tinyint(1) NOT NULL DEFAULT '1' COMMENT '发送Telegram',
  `notify_email` tinyint(1) NOT NULL DEFAULT '0' COMMENT '发送邮件',
  `cooldown_minutes` int NOT NULL DEFAULT '5' COMMENT '告警冷却分钟',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态:0=禁用,1=启用',
  `last_alert_time` int NOT NULL DEFAULT '0' COMMENT '最后告警时间',
  `trigger_count` int NOT NULL DEFAULT '0' COMMENT '触发次数',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标记',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='API告警配置表';

-- ----------------------------
-- Records of think_api_alert_config
-- ----------------------------
BEGIN;
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (1, '响应超时告警', '', '', 1, 5000.00, 'ms', 1, 0, 5, 1, 0, 0, 1769489390, 1769679243, 0);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (2, '失败率过高告警', '', '', 2, 10.00, '%', 1, 0, 10, 1, 0, 0, 1769489390, 1769489390, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (3, '连续失败告警', '', '', 3, 5.00, '次', 1, 0, 5, 1, 0, 0, 1769489390, 1769489390, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (4, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 1769679243, 7, 1769672109, 1769679243, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (5, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 1769679243, 6, 1769674203, 1769679243, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (6, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 1769679243, 6, 1769674345, 1769679243, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (7, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 1769679243, 6, 1769674423, 1769679243, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (8, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 1769679243, 5, 1769674579, 1769679243, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (9, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 1769679243, 4, 1769675000, 1769679243, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (10, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 1769679243, 3, 1769677982, 1769679243, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (11, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 1769679243, 2, 1769678420, 1769679243, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (12, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 1769679243, 1, 1769678792, 1769679243, 1);
INSERT INTO `think_api_alert_config` (`id`, `name`, `exchange`, `api_type`, `alert_type`, `threshold_value`, `threshold_unit`, `notify_telegram`, `notify_email`, `cooldown_minutes`, `status`, `last_alert_time`, `trigger_count`, `create_time`, `update_time`, `mark`) VALUES (13, '', '', '', 1, 0.00, '', 1, 0, 5, 1, 0, 0, 1769679243, 1769679243, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_api_health_status
-- ----------------------------
DROP TABLE IF EXISTS `think_api_health_status`;
CREATE TABLE `think_api_health_status` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `exchange` varchar(32) NOT NULL DEFAULT '' COMMENT '交易所',
  `api_type` varchar(32) NOT NULL DEFAULT '' COMMENT 'API类型',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态:0=异常,1=正常,2=降级',
  `avg_response_time` int NOT NULL DEFAULT '0' COMMENT '平均响应时间ms',
  `success_rate` decimal(10,2) NOT NULL DEFAULT '100.00' COMMENT '成功率%',
  `total_calls` int NOT NULL DEFAULT '0' COMMENT '总调用次数',
  `failed_calls` int NOT NULL DEFAULT '0' COMMENT '失败次数',
  `last_check_time` int NOT NULL DEFAULT '0' COMMENT '最后检查时间',
  `last_error_time` int NOT NULL DEFAULT '0' COMMENT '最后错误时间',
  `last_error_msg` varchar(500) NOT NULL DEFAULT '' COMMENT '最后错误信息',
  `consecutive_failures` int NOT NULL DEFAULT '0' COMMENT '连续失败次数',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_exchange_type` (`exchange`,`api_type`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='API健康状态表';

-- ----------------------------
-- Records of think_api_health_status
-- ----------------------------
BEGIN;
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (1, 'binance', 'spot', 1, 313, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (2, 'binance', 'futures', 1, 338, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (3, 'binance', 'account', 1, 200, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (4, 'binance', 'market', 1, 175, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (5, 'binance', 'order', 1, 281, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (6, 'okx', 'spot', 1, 398, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (7, 'okx', 'futures', 1, 236, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (8, 'okx', 'account', 1, 279, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (9, 'okx', 'market', 1, 166, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (10, 'okx', 'order', 1, 173, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (11, 'bybit', 'spot', 1, 207, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (12, 'bybit', 'futures', 1, 192, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (13, 'bybit', 'account', 1, 294, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (14, 'bybit', 'market', 1, 185, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (15, 'bybit', 'order', 1, 283, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (16, 'gate', 'spot', 1, 345, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (17, 'gate', 'futures', 1, 278, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (18, 'gate', 'account', 1, 279, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (19, 'gate', 'market', 1, 230, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (20, 'gate', 'order', 1, 311, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (21, 'huobi', 'spot', 1, 279, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (22, 'huobi', 'futures', 1, 356, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (23, 'huobi', 'account', 1, 255, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (24, 'huobi', 'market', 1, 259, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
INSERT INTO `think_api_health_status` (`id`, `exchange`, `api_type`, `status`, `avg_response_time`, `success_rate`, `total_calls`, `failed_calls`, `last_check_time`, `last_error_time`, `last_error_msg`, `consecutive_failures`, `update_time`) VALUES (25, 'huobi', 'order', 1, 235, 100.00, 15, 0, 1769679243, 0, '', 0, 1769679243);
COMMIT;

-- ----------------------------
-- Table structure for think_api_key
-- ----------------------------
DROP TABLE IF EXISTS `think_api_key`;
CREATE TABLE `think_api_key` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned DEFAULT '0' COMMENT '所属用户',
  `name` varchar(100) NOT NULL COMMENT '密钥名称',
  `api_key` varchar(64) NOT NULL COMMENT 'API Key',
  `api_secret` varchar(255) NOT NULL COMMENT 'API Secret (加密)',
  `api_secret_plain` varchar(255) DEFAULT '' COMMENT 'Secret (可解密版本)',
  `permissions` json DEFAULT NULL COMMENT '权限列表',
  `ip_whitelist` varchar(500) DEFAULT '' COMMENT 'IP白名单(逗号分隔)',
  `rate_limit` int DEFAULT '100' COMMENT '每分钟请求限制',
  `expire_at` int unsigned DEFAULT '0' COMMENT '过期时间(0=永不)',
  `last_used_at` int unsigned DEFAULT '0' COMMENT '最后使用时间',
  `total_calls` int unsigned DEFAULT '0' COMMENT '总调用次数',
  `status` tinyint DEFAULT '1' COMMENT '1启用 0禁用',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_api_key` (`api_key`),
  KEY `idx_member` (`member_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='API密钥表';

-- ----------------------------
-- Records of think_api_key
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_api_key_log
-- ----------------------------
DROP TABLE IF EXISTS `think_api_key_log`;
CREATE TABLE `think_api_key_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `key_id` int unsigned NOT NULL COMMENT '密钥ID',
  `action` varchar(50) NOT NULL COMMENT '操作',
  `detail` varchar(500) DEFAULT '' COMMENT '详情',
  `ip` varchar(50) DEFAULT '' COMMENT '请求IP',
  `user_agent` varchar(255) DEFAULT '' COMMENT 'UA',
  `response_code` int DEFAULT '200' COMMENT '响应码',
  `create_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_key_id` (`key_id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='API调用日志表';

-- ----------------------------
-- Records of think_api_key_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_api_monitor_log
-- ----------------------------
DROP TABLE IF EXISTS `think_api_monitor_log`;
CREATE TABLE `think_api_monitor_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `exchange` varchar(32) NOT NULL DEFAULT '' COMMENT '交易所:binance,okx,bybit等',
  `api_type` varchar(32) NOT NULL DEFAULT '' COMMENT 'API类型:spot,futures,account等',
  `api_name` varchar(64) NOT NULL DEFAULT '' COMMENT 'API名称',
  `api_endpoint` varchar(255) NOT NULL DEFAULT '' COMMENT 'API端点',
  `request_method` varchar(10) NOT NULL DEFAULT 'GET' COMMENT '请求方法',
  `request_params` text COMMENT '请求参数(JSON)',
  `response_code` int NOT NULL DEFAULT '0' COMMENT '响应状态码',
  `response_time_ms` int NOT NULL DEFAULT '0' COMMENT '响应时间毫秒',
  `response_size` int NOT NULL DEFAULT '0' COMMENT '响应大小字节',
  `is_success` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否成功:0=失败,1=成功',
  `error_code` varchar(64) NOT NULL DEFAULT '' COMMENT '错误代码',
  `error_msg` varchar(500) NOT NULL DEFAULT '' COMMENT '错误信息',
  `server_id` int NOT NULL DEFAULT '0' COMMENT '服务器ID',
  `member_id` int NOT NULL DEFAULT '0' COMMENT '会员ID(0=系统调用)',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标记',
  PRIMARY KEY (`id`),
  KEY `idx_exchange` (`exchange`),
  KEY `idx_api_type` (`api_type`),
  KEY `idx_is_success` (`is_success`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_response_time` (`response_time_ms`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='API监控日志表';

-- ----------------------------
-- Records of think_api_monitor_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_backtest_equity
-- ----------------------------
DROP TABLE IF EXISTS `think_backtest_equity`;
CREATE TABLE `think_backtest_equity` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` int unsigned NOT NULL COMMENT '回测任务ID',
  `time` int unsigned NOT NULL COMMENT '时间戳',
  `equity` decimal(20,2) NOT NULL COMMENT '权益',
  `price` decimal(20,8) NOT NULL COMMENT '价格',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='回测权益曲线表';

-- ----------------------------
-- Records of think_backtest_equity
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_backtest_result
-- ----------------------------
DROP TABLE IF EXISTS `think_backtest_result`;
CREATE TABLE `think_backtest_result` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `strategy_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略ID',
  `strategy_name` varchar(100) NOT NULL DEFAULT '' COMMENT '策略名称',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `start_date` date NOT NULL COMMENT '开始日期',
  `end_date` date NOT NULL COMMENT '结束日期',
  `initial_capital` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '初始资金',
  `position_size` decimal(5,4) NOT NULL DEFAULT '0.1000' COMMENT '仓位比例',
  `final_capital` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '最终资金',
  `net_profit` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '净盈亏',
  `return_rate` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '收益率%',
  `total_trades` int unsigned NOT NULL DEFAULT '0' COMMENT '总交易次数',
  `win_trades` int unsigned NOT NULL DEFAULT '0' COMMENT '盈利次数',
  `loss_trades` int unsigned NOT NULL DEFAULT '0' COMMENT '亏损次数',
  `win_rate` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '胜率%',
  `profit_factor` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '盈亏比',
  `max_drawdown` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '最大回撤%',
  `trades_data` longtext COMMENT '交易记录JSON',
  `equity_curve` text COMMENT '权益曲线JSON',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识',
  PRIMARY KEY (`id`),
  KEY `idx_strategy_id` (`strategy_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略回测结果';

-- ----------------------------
-- Records of think_backtest_result
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_backtest_task
-- ----------------------------
DROP TABLE IF EXISTS `think_backtest_task`;
CREATE TABLE `think_backtest_task` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(100) NOT NULL COMMENT '回测名称',
  `strategy_id` int unsigned NOT NULL COMMENT '策略ID',
  `symbol` varchar(20) NOT NULL COMMENT '交易对',
  `timeframe` varchar(10) NOT NULL DEFAULT '1h' COMMENT '周期',
  `start_date` date NOT NULL COMMENT '开始日期',
  `end_date` date NOT NULL COMMENT '结束日期',
  `initial_capital` decimal(20,2) NOT NULL DEFAULT '10000.00' COMMENT '初始资金',
  `leverage` int unsigned NOT NULL DEFAULT '1' COMMENT '杠杆倍数',
  `position_size` decimal(5,2) NOT NULL DEFAULT '10.00' COMMENT '仓位比例%',
  `fee_rate` decimal(10,6) NOT NULL DEFAULT '0.000400' COMMENT '手续费率',
  `slippage` decimal(10,6) NOT NULL DEFAULT '0.000100' COMMENT '滑点',
  `config` text COMMENT '策略配置JSON',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态: 1=待执行 2=执行中 3=已完成 4=失败',
  `start_time` int unsigned DEFAULT NULL COMMENT '开始执行时间',
  `end_time` int unsigned DEFAULT NULL COMMENT '结束时间',
  `total_trades` int unsigned DEFAULT '0' COMMENT '总交易数',
  `win_rate` decimal(5,2) DEFAULT '0.00' COMMENT '胜率%',
  `total_pnl` decimal(20,2) DEFAULT '0.00' COMMENT '总盈亏',
  `max_drawdown` decimal(5,2) DEFAULT '0.00' COMMENT '最大回撤%',
  `error_msg` varchar(500) DEFAULT NULL COMMENT '错误信息',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '创建人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标记',
  PRIMARY KEY (`id`),
  KEY `idx_strategy_id` (`strategy_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='回测任务表';

-- ----------------------------
-- Records of think_backtest_task
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_backtest_trade
-- ----------------------------
DROP TABLE IF EXISTS `think_backtest_trade`;
CREATE TABLE `think_backtest_trade` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` int unsigned NOT NULL COMMENT '回测任务ID',
  `trade_type` varchar(10) NOT NULL COMMENT '交易类型: long/short',
  `entry_price` decimal(20,8) NOT NULL COMMENT '入场价',
  `exit_price` decimal(20,8) NOT NULL COMMENT '出场价',
  `quantity` decimal(20,8) NOT NULL COMMENT '数量',
  `entry_time` int unsigned NOT NULL COMMENT '入场时间',
  `exit_time` int unsigned NOT NULL COMMENT '出场时间',
  `pnl` decimal(20,4) NOT NULL COMMENT '盈亏',
  `pnl_percent` decimal(10,2) NOT NULL COMMENT '盈亏比例%',
  `fees` decimal(20,4) NOT NULL DEFAULT '0.0000' COMMENT '手续费',
  `reason` varchar(100) DEFAULT NULL COMMENT '平仓原因',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='回测交易记录表';

-- ----------------------------
-- Records of think_backtest_trade
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_client_config
-- ----------------------------
DROP TABLE IF EXISTS `think_client_config`;
CREATE TABLE `think_client_config` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `client_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '客户端编号',
  `client_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户端名称',
  `api_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'API Key',
  `api_secret` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'API Secret',
  `ip_whitelist` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT 'IP白名单(JSON)',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2禁用',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_client_code` (`client_code`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户端配置表';

-- ----------------------------
-- Records of think_client_config
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_coin_analysis
-- ----------------------------
DROP TABLE IF EXISTS `think_coin_analysis`;
CREATE TABLE `think_coin_analysis` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `symbol` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '币种代码',
  `score` decimal(6,2) NOT NULL DEFAULT '0.00' COMMENT '评分',
  `analysis` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '分析结论',
  `analysis_data` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '分析数据(JSON)',
  `analysis_time` int unsigned NOT NULL DEFAULT '0' COMMENT '分析时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_symbol` (`symbol`) USING BTREE,
  KEY `idx_analysis_time` (`analysis_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='币种分析记录表';

-- ----------------------------
-- Records of think_coin_analysis
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_coin_pool
-- ----------------------------
DROP TABLE IF EXISTS `think_coin_pool`;
CREATE TABLE `think_coin_pool` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `symbol` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '币种代码',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2停用',
  `weight` int unsigned NOT NULL DEFAULT '0' COMMENT '权重',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_symbol` (`symbol`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_weight` (`weight`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='币种池表';

-- ----------------------------
-- Records of think_coin_pool
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_coin_selection
-- ----------------------------
DROP TABLE IF EXISTS `think_coin_selection`;
CREATE TABLE `think_coin_selection` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `symbol` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '币种代码',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '币种名称',
  `level` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'A' COMMENT '等级',
  `score` decimal(6,2) NOT NULL DEFAULT '0.00' COMMENT '评分',
  `reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '推荐理由',
  `is_favorite` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '是否收藏：1是 0否',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_symbol` (`symbol`) USING BTREE,
  KEY `idx_level` (`level`) USING BTREE,
  KEY `idx_score` (`score`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='币种选择表';

-- ----------------------------
-- Records of think_coin_selection
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_company_income
-- ----------------------------
DROP TABLE IF EXISTS `think_company_income`;
CREATE TABLE `think_company_income` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `income_date` date NOT NULL COMMENT '收入日期',
  `income_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '收入类型：1利润分成 2燃料费 3其他',
  `amount` decimal(15,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '收入金额',
  `source` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '收入来源',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_income_date` (`income_date`) USING BTREE,
  KEY `idx_income_type` (`income_type`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='公司收入表';

-- ----------------------------
-- Records of think_company_income
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_cron_job
-- ----------------------------
DROP TABLE IF EXISTS `think_cron_job`;
CREATE TABLE `think_cron_job` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '任务名称',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '任务类型',
  `cron_expression` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT 'CRON表达式',
  `command` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '执行命令',
  `param` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '参数',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态 1启用 2停用',
  `last_run_time` int unsigned NOT NULL DEFAULT '0' COMMENT '上次执行时间',
  `next_run_time` int unsigned NOT NULL DEFAULT '0' COMMENT '下次执行时间',
  `execute_times` int unsigned NOT NULL DEFAULT '0' COMMENT '执行次数',
  `last_result` tinyint(1) NOT NULL DEFAULT '0' COMMENT '上次结果 0失败 1成功',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '备注',
  `sort` int NOT NULL DEFAULT '0' COMMENT '排序',
  `create_user` int NOT NULL DEFAULT '0' COMMENT '创建人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标识',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_type` (`type`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_next_run_time` (`next_run_time`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='定时任务表';

-- ----------------------------
-- Records of think_cron_job
-- ----------------------------
BEGIN;
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, '更新的任务_1769656138', 'sync_balance', '0 */5 * * * *', 'app\\script\\common\\SyncAccount', '', 2, 0, 0, 0, 0, '每5分钟同步一次账户余额', 0, 0, 0, 1, 1769679237, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, '同步订单状态', 'sync_order', '0 */1 * * * *', 'app\\script\\common\\SyncOrders', '', 0, 1769882597, 1769882657, 5, 1, '每1分钟同步一次订单状态', 2, 0, 0, 0, 1769882597, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (3, '处理待执行信号', 'process_signal', '0 */1 * * * *', 'app\\script\\common\\ProcessSignals', '', 0, 1770049130, 1770049190, 6, 1, '每1分钟处理待执行信号', 3, 0, 0, 0, 1770049130, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, '批量跟单同步', 'batch_follow', '0 */1 * * * *', 'app\\script\\common\\BatchFollow', '', 0, 1770049130, 1770049190, 6, 1, '每1分钟执行一次批量跟单', 4, 0, 0, 0, 1770049130, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (5, '清理过期信号', 'clean_signal', '0 0 4 * * *', 'app\\script\\common\\CleanSignals', '', 0, 0, 0, 0, 0, '每天凌晨4点清理过期信号', 5, 0, 0, 0, 0, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (6, '生成日报表', 'daily_report', '0 0 23 * * *', 'app\\script\\common\\DailyReport', '', 0, 0, 0, 0, 0, '每天23点生成日报表', 6, 0, 0, 0, 0, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (7, '订单同步', 'script', '0 */5 * * * *', 'app\\admin\\controller\\Ordersync::scheduledSync', '', 0, 1770049130, 1770049430, 2, 1, 'æ¯5åˆ†é’ŸåŒæ­¥ä¸€æ¬¡è®¢å•çŠ¶æ€', 10, 0, 1769276030, 0, 1770049130, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (8, 'Leader持仓同步', 'sync_leader_positions', '0 */5 * * * *', 'app\\script\\common\\SyncLeaderPositions', '{\"min_delta\": 10}', 0, 1769882309, 1769882609, 1, 1, '', 10, 0, 1769426043, 0, 1769882309, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (9, '策略执行-1分钟周期', 'execute_strategies', '*/60 * * * * *', 'app\\script\\common\\ExecuteStrategies', '{\"timeframe\":\"1m\"}', 0, 1770049130, 1770049190, 6, 1, '执行1分钟周期的策略实例', 100, 0, 1769502525, 0, 1770049130, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (10, '策略执行-5分钟周期', 'execute_strategies', '0 */5 * * * *', 'app\\script\\common\\ExecuteStrategies', '{\"timeframe\":\"5m\"}', 0, 1770049130, 1770049430, 2, 1, '执行5分钟周期的策略实例', 101, 0, 1769502525, 0, 1770049130, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (11, '策略执行-15分钟周期', 'execute_strategies', '0 */15 * * * *', 'app\\script\\common\\ExecuteStrategies', '{\"timeframe\":\"15m\"}', 0, 1770049130, 1770050030, 2, 1, '执行15分钟周期的策略实例', 102, 0, 1769502525, 0, 1770049130, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (12, '策略执行-1小时周期', 'execute_strategies', '0 0 * * * *', 'app\\script\\common\\ExecuteStrategies', '{\"timeframe\":\"1h\"}', 0, 1770049130, 1770052730, 2, 1, '执行1小时周期的策略实例', 103, 0, 1769502525, 0, 1770049130, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (13, '策略执行-4小时周期', 'execute_strategies', '0 0 */4 * * *', 'app\\script\\common\\ExecuteStrategies', '{\"timeframe\":\"4h\"}', 0, 1770051129, 1770054729, 3, 1, '执行4小时周期的策略实例', 104, 0, 1769502525, 0, 1770051129, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (14, '策略执行-日线周期', 'execute_strategies', '0 0 0 * * *', 'app\\script\\common\\ExecuteStrategies', '{\"timeframe\":\"1d\"}', 0, 1770049131, 1770134400, 1, 1, '执行日线周期的策略实例', 105, 0, 1769502525, 0, 1770049131, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (15, '策略执行日报', 'strategy_daily_summary', '0 0 20 * * *', 'app\\script\\common\\StrategyDailySummary', '{}', 0, 0, 1769506456, 0, 0, '每天晚上8点发送策略执行日报', 220, 0, 1769502856, 0, 0, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (16, '信号风控监控', 'script', '* * * * *', 'app\\script\\common\\MonitorSignalRisk', '', 0, 1769882597, 1769886197, 5, 1, '每分钟检查止损止盈触发', 0, 0, 1769821568, 0, 1769882597, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (17, '价格预警检查', 'url', '0 * * * * *', 'app\\admin\\controller\\Pricealert::checkAlerts', NULL, 0, 1770049131, 1770052731, 6, 1, '', 100, 0, 1769881759, 0, 1770049131, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (18, '账户余额快照', 'url', '0 0 * * * *', 'app\\admin\\controller\\Member::snapshotBalance', NULL, 0, 1770049131, 1770052731, 2, 1, '', 101, 0, 1769881759, 0, 1770049131, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (19, '日志清理', 'url', '0 0 3 * * *', 'app\\admin\\controller\\Systemconfig::cleanupLogs', NULL, 0, 0, 0, 0, 0, '', 102, 0, 1769881759, 0, 1769881759, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (20, '全量持仓同步', 'url', '0 */10 * * * *', 'app\\admin\\controller\\Position::syncAll', NULL, 0, 1770049131, 1770049731, 2, 1, '', 103, 0, 1769881759, 0, 1770049131, 0);
INSERT INTO `think_cron_job` (`id`, `name`, `type`, `cron_expression`, `command`, `param`, `status`, `last_run_time`, `next_run_time`, `execute_times`, `last_result`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (21, '账户余额同步', '', '0 0 * * * *', 'app\\script\\common\\SyncAccount', '{}', 0, 0, 0, 0, 0, '', 21, 0, 1769966923, 0, 1769966923, 0);
COMMIT;

-- ----------------------------
-- Table structure for think_cron_log
-- ----------------------------
DROP TABLE IF EXISTS `think_cron_log`;
CREATE TABLE `think_cron_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `job_id` int unsigned NOT NULL DEFAULT '0' COMMENT '任务ID',
  `job_name` varchar(100) NOT NULL DEFAULT '' COMMENT '任务名称',
  `execute_time` int unsigned DEFAULT '0',
  `result` tinyint NOT NULL DEFAULT '0' COMMENT '执行结果：1成功 0失败',
  `output` text COMMENT '执行输出',
  `error` text COMMENT '错误信息',
  `duration` int unsigned NOT NULL DEFAULT '0' COMMENT '执行耗时(ms)',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识',
  PRIMARY KEY (`id`),
  KEY `idx_job_id` (`job_id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='定时任务日志表';

-- ----------------------------
-- Records of think_cron_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_daily_loss_log
-- ----------------------------
DROP TABLE IF EXISTS `think_daily_loss_log`;
CREATE TABLE `think_daily_loss_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `daily_loss` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '当日亏损',
  `max_loss` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '亏损限额',
  `event_type` varchar(20) NOT NULL DEFAULT '' COMMENT '事件类型：lock/unlock/warning',
  `log_date` date NOT NULL COMMENT '日期',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识',
  PRIMARY KEY (`id`),
  KEY `idx_member_id` (`member_id`),
  KEY `idx_log_date` (`log_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='每日亏损日志';

-- ----------------------------
-- Records of think_daily_loss_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_exchange_account
-- ----------------------------
DROP TABLE IF EXISTS `think_exchange_account`;
CREATE TABLE `think_exchange_account` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `exchange` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '交易所',
  `account_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'futures' COMMENT '账户类型(spot/futures/margin)',
  `is_testnet` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否测试网',
  `api_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'API密钥',
  `api_secret` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'API密钥',
  `passphrase` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'API密码短语(部分平台需要)',
  `member_id` int unsigned DEFAULT NULL COMMENT '所属会员ID',
  `server_id` int unsigned DEFAULT NULL COMMENT '分配的服务器ID',
  `balance` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '账户余额',
  `total_equity` decimal(20,8) DEFAULT NULL COMMENT '总权益',
  `available_balance` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '可用余额',
  `frozen_balance` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '冻结余额',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2停用',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '添加时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  `is_test` tinyint(1) NOT NULL DEFAULT '0' COMMENT '测试模式',
  `last_sync_time` int NOT NULL DEFAULT '0' COMMENT '最后同步时间',
  `sync_status` tinyint(1) DEFAULT '0' COMMENT '同步状态：0-未同步 1-同步成功 2-同步失败',
  `sync_error` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '同步错误信息',
  `spot_balance` decimal(20,8) DEFAULT NULL COMMENT '现货USDT余额',
  `spot_available` decimal(20,8) DEFAULT NULL COMMENT '现货可用余额',
  `futures_balance` decimal(20,8) DEFAULT NULL COMMENT '合约钱包余额',
  `futures_available` decimal(20,8) DEFAULT NULL COMMENT '合约可用余额',
  `futures_unrealized` decimal(20,8) DEFAULT NULL COMMENT '合约未实现盈亏',
  `futures_margin` decimal(20,8) DEFAULT NULL COMMENT '合约保证金余额',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_exchange` (`exchange`) USING BTREE,
  KEY `idx_account_type` (`account_type`) USING BTREE,
  KEY `idx_member_id` (`member_id`),
  KEY `idx_server_id` (`server_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='交易账户表';

-- ----------------------------
-- Records of think_exchange_account
-- ----------------------------
BEGIN;
INSERT INTO `think_exchange_account` (`id`, `exchange`, `account_type`, `is_testnet`, `api_key`, `api_secret`, `passphrase`, `member_id`, `server_id`, `balance`, `total_equity`, `available_balance`, `frozen_balance`, `status`, `create_time`, `update_time`, `mark`, `is_test`, `last_sync_time`, `sync_status`, `sync_error`, `spot_balance`, `spot_available`, `futures_balance`, `futures_available`, `futures_unrealized`, `futures_margin`) VALUES (1, 'binance', 'futures', 0, 'x0WJZRj8d4xW5xb6OJvQvthEN5GUF8zEs1Zxx0DIxdv60PMB0C5PoWbQA1c4BIw5', 'LRi9fH3mpBjI4MEaoVTfOoprSnSOwDLwxGU8sxvPL6W6FChbNHXURRMmphrNbUuj', NULL, 1, 1, 1513.84932958, 1513.84932958, 1513.84932958, 0.00000000, 1, 1769957871, 1769957871, 1, 0, 1770132709, 1, '', 463.85963171, 463.85963171, 1049.98969787, 1049.98969787, 0.00000000, 1049.98969787);
INSERT INTO `think_exchange_account` (`id`, `exchange`, `account_type`, `is_testnet`, `api_key`, `api_secret`, `passphrase`, `member_id`, `server_id`, `balance`, `total_equity`, `available_balance`, `frozen_balance`, `status`, `create_time`, `update_time`, `mark`, `is_test`, `last_sync_time`, `sync_status`, `sync_error`, `spot_balance`, `spot_available`, `futures_balance`, `futures_available`, `futures_unrealized`, `futures_margin`) VALUES (2, 'okx', 'futures', 0, 'a3bb26d2-4e83-4e89-bec5-01d1a0239f6a', '170DE37153A6F777515F4477FA2AB02C', 'Test111--', 1, 1, 961.51176324, 961.51176324, 0.00000000, 961.51176324, 1, 1769964107, 0, 1, 0, 1770132709, 1, '', 0.00000000, 0.00000000, 961.51176324, 0.00000000, 0.00000000, 961.51176324);
INSERT INTO `think_exchange_account` (`id`, `exchange`, `account_type`, `is_testnet`, `api_key`, `api_secret`, `passphrase`, `member_id`, `server_id`, `balance`, `total_equity`, `available_balance`, `frozen_balance`, `status`, `create_time`, `update_time`, `mark`, `is_test`, `last_sync_time`, `sync_status`, `sync_error`, `spot_balance`, `spot_available`, `futures_balance`, `futures_available`, `futures_unrealized`, `futures_margin`) VALUES (3, 'gate', 'futures', 0, '0dd1c7ced1366993a889f9de7d0f3cc8', 'fbdc625e3f3788c70361369db9c6cf65466dde5748f4065e9f9d463981e799ad', '', 1, 1, 2095.88200658, 2095.88200658, 4209.33007658, 0.00000000, 1, 1769966263, 0, 1, 0, 1770132709, 1, '', 2095.88200658, 2095.88200658, 0.00000000, 2113.44807000, 0.00000000, 0.00000000);
COMMIT;

-- ----------------------------
-- Table structure for think_follow_daily_stats
-- ----------------------------
DROP TABLE IF EXISTS `think_follow_daily_stats`;
CREATE TABLE `think_follow_daily_stats` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `stat_date` date NOT NULL COMMENT '统计日期',
  `member_id` int NOT NULL DEFAULT '0' COMMENT '会员ID',
  `leader_id` int NOT NULL DEFAULT '0' COMMENT 'Leader ID',
  `relation_id` int NOT NULL DEFAULT '0' COMMENT '跟单关系ID',
  `total_orders` int NOT NULL DEFAULT '0' COMMENT '跟单次数',
  `success_orders` int NOT NULL DEFAULT '0' COMMENT '成功次数',
  `failed_orders` int NOT NULL DEFAULT '0' COMMENT '失败次数',
  `skipped_orders` int NOT NULL DEFAULT '0' COMMENT '跳过次数',
  `total_amount` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '跟单总金额',
  `executed_amount` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '执行总金额',
  `total_profit` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总盈亏',
  `avg_execute_ms` int NOT NULL DEFAULT '0' COMMENT '平均执行耗时ms',
  `avg_slippage` decimal(10,4) NOT NULL DEFAULT '0.0000' COMMENT '平均滑点%',
  `win_rate` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '胜率%',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_date_member_leader` (`stat_date`,`member_id`,`leader_id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_leader` (`leader_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='跟单每日统计表';

-- ----------------------------
-- Records of think_follow_daily_stats
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_follow_execution_log
-- ----------------------------
DROP TABLE IF EXISTS `think_follow_execution_log`;
CREATE TABLE `think_follow_execution_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `signal_id` int NOT NULL DEFAULT '0' COMMENT '信号ID',
  `relation_id` int NOT NULL DEFAULT '0' COMMENT '跟单关系ID',
  `member_id` int NOT NULL DEFAULT '0' COMMENT '跟单者ID',
  `leader_id` int NOT NULL DEFAULT '0' COMMENT 'Leader ID',
  `task_id` varchar(64) NOT NULL DEFAULT '' COMMENT '任务队列ID',
  `order_id` varchar(64) NOT NULL DEFAULT '' COMMENT '交易所订单ID',
  `symbol` varchar(32) NOT NULL DEFAULT '' COMMENT '交易对',
  `side` tinyint(1) NOT NULL DEFAULT '1' COMMENT '方向:1=买入,2=卖出',
  `action` tinyint(1) NOT NULL DEFAULT '1' COMMENT '动作:1=开仓,2=平仓,3=加仓,4=减仓',
  `follow_amount` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '跟单金额',
  `executed_amount` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '实际执行金额',
  `quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '数量',
  `executed_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '实际执行数量',
  `price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '期望价格',
  `executed_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '实际成交价格',
  `slippage` decimal(10,4) NOT NULL DEFAULT '0.0000' COMMENT '滑点百分比',
  `is_partial` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否部分成交:0=否,1=是',
  `fill_percent` decimal(10,2) NOT NULL DEFAULT '100.00' COMMENT '成交比例%',
  `parent_log_id` int NOT NULL DEFAULT '0' COMMENT '父订单日志ID(分拆/补单)',
  `split_index` int NOT NULL DEFAULT '0' COMMENT '分拆序号',
  `split_total` int NOT NULL DEFAULT '1' COMMENT '分拆总数',
  `expected_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '预期价格(用于滑点计算)',
  `market_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '下单时市场价格',
  `price_protect_triggered` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否触发价格保护',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态:1=已入队,2=执行中,3=成功,4=失败,5=跳过,6=重试中,7=已取消',
  `error_code` varchar(32) NOT NULL DEFAULT '' COMMENT '错误代码',
  `error_msg` varchar(500) NOT NULL DEFAULT '' COMMENT '错误信息',
  `error_type` tinyint(1) NOT NULL DEFAULT '0' COMMENT '错误类型:0=无,1=余额不足,2=API限流,3=网络错误,4=价格异常,5=数量异常,6=其他',
  `retry_times` int NOT NULL DEFAULT '0' COMMENT '重试次数',
  `next_retry_time` int NOT NULL DEFAULT '0' COMMENT '下次重试时间',
  `queue_time` int NOT NULL DEFAULT '0' COMMENT '入队时间',
  `start_time` int NOT NULL DEFAULT '0' COMMENT '开始执行时间',
  `end_time` int NOT NULL DEFAULT '0' COMMENT '执行完成时间',
  `queue_wait_ms` int NOT NULL DEFAULT '0' COMMENT '队列等待毫秒',
  `execute_ms` int NOT NULL DEFAULT '0' COMMENT '执行耗时毫秒',
  `total_ms` int NOT NULL DEFAULT '0' COMMENT '总耗时毫秒',
  `server_id` int NOT NULL DEFAULT '0' COMMENT '执行服务器ID',
  `exchange` varchar(32) NOT NULL DEFAULT '' COMMENT '交易所',
  `api_request` text COMMENT 'API请求参数(JSON)',
  `api_response` text COMMENT 'API响应(JSON)',
  `remark` varchar(255) NOT NULL DEFAULT '' COMMENT '备注',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标记:1=有效,0=删除',
  PRIMARY KEY (`id`),
  KEY `idx_signal` (`signal_id`),
  KEY `idx_relation` (`relation_id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_leader` (`leader_id`),
  KEY `idx_task` (`task_id`),
  KEY `idx_status` (`status`),
  KEY `idx_error_type` (`error_type`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_retry` (`status`,`next_retry_time`),
  KEY `idx_parent_log` (`parent_log_id`),
  KEY `idx_partial` (`is_partial`,`fill_percent`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='跟单执行日志表';

-- ----------------------------
-- Records of think_follow_execution_log
-- ----------------------------
BEGIN;
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (6, 6, 1, 1, 0, '', '', 'ETH/USDT', 1, 1, 0.00000000, 0.00000000, 50.00000000, 0.00000000, 2371.14000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '点卡余额不足', 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, NULL, '', 1770059378, 1770059378, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (7, 7, 1, 1, 0, '', '', 'ETH/USDT', 2, 1, 0.00000000, 0.00000000, 50.00000000, 0.00000000, 2371.14000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '点卡余额不足', 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, NULL, '', 1770059378, 1770059378, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (8, 0, 0, 1, 0, '', '', 'ETH/USDT', 2, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770059967, 1770059967, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (9, 0, 0, 1, 0, '', '', 'ETH/USDT', 2, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770059970, 1770059970, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (10, 0, 0, 1, 0, '', '', 'ETH/USDT', 2, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770059971, 1770059971, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (11, 0, 0, 1, 0, '', '', 'ETH/USDT', 2, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770059971, 1770059971, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (12, 0, 0, 1, 0, '', '', 'ETH/USDT', 2, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770059971, 1770059971, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (13, 0, 0, 1, 0, '', '', 'ETH/USDT', 1, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770060145, 1770060145, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (14, 0, 0, 1, 0, '', '', 'ETH/USDT', 1, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770060147, 1770060147, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (15, 0, 0, 1, 0, '', '', 'ETH/USDT', 1, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770060147, 1770060147, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (16, 0, 0, 1, 0, '', '', 'ETH/USDT', 1, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770060147, 1770060147, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (17, 0, 0, 1, 0, '', '', 'ETH/USDT', 1, 1, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 5, '', '\'quantity\'', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770060147, 1770060147, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (18, 6, 0, 1, 0, '', '8389766089888910050', 'ETH/USDT', 1, 1, 0.00000000, 0.00000000, 0.05000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 2, '', '', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770060578, 1770060578, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (19, 7, 0, 1, 0, '', '8389766089889969528', 'ETH/USDT', 2, 1, 0.00000000, 0.00000000, 0.05000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 2, '', '', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770060679, 1770060679, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (20, 7, 0, 1, 0, '', '8389766089891089694', 'ETH/USDT', 2, 1, 0.00000000, 0.00000000, 0.05000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 2, '', '', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770060771, 1770060771, 1);
INSERT INTO `think_follow_execution_log` (`id`, `signal_id`, `relation_id`, `member_id`, `leader_id`, `task_id`, `order_id`, `symbol`, `side`, `action`, `follow_amount`, `executed_amount`, `quantity`, `executed_quantity`, `price`, `executed_price`, `slippage`, `is_partial`, `fill_percent`, `parent_log_id`, `split_index`, `split_total`, `expected_price`, `market_price`, `price_protect_triggered`, `status`, `error_code`, `error_msg`, `error_type`, `retry_times`, `next_retry_time`, `queue_time`, `start_time`, `end_time`, `queue_wait_ms`, `execute_ms`, `total_ms`, `server_id`, `exchange`, `api_request`, `api_response`, `remark`, `create_time`, `update_time`, `mark`) VALUES (21, 6, 0, 1, 0, '', '8389766089891119310', 'ETH/USDT', 1, 1, 0.00000000, 0.00000000, 0.05000000, 0.00000000, 0.00000000, 0.00000000, 0.0000, 0, 100.00, 0, 0, 1, 0.00000000, 0.00000000, 0, 2, '', '', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', NULL, '', '', 1770060773, 1770060773, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_follow_lock
-- ----------------------------
DROP TABLE IF EXISTS `think_follow_lock`;
CREATE TABLE `think_follow_lock` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `lock_key` varchar(128) NOT NULL COMMENT '锁定键',
  `lock_value` varchar(64) NOT NULL DEFAULT '' COMMENT '锁定值',
  `expire_time` int NOT NULL DEFAULT '0' COMMENT '过期时间',
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_lock_key` (`lock_key`),
  KEY `idx_expire` (`expire_time`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='跟单分布式锁表';

-- ----------------------------
-- Records of think_follow_lock
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_follow_order_log
-- ----------------------------
DROP TABLE IF EXISTS `think_follow_order_log`;
CREATE TABLE `think_follow_order_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `ip_address` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '使用的IP地址',
  `signal_id` int unsigned NOT NULL DEFAULT '0' COMMENT '交易信号ID',
  `order_id` int unsigned NOT NULL DEFAULT '0' COMMENT '订单ID',
  `follow_amount` decimal(15,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '跟单金额',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '执行状态：1成功 2失败',
  `error_msg` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '错误信息',
  `execute_time` int unsigned NOT NULL DEFAULT '0' COMMENT '执行耗时（毫秒）',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_signal_id` (`signal_id`) USING BTREE,
  KEY `idx_order_id` (`order_id`) USING BTREE,
  KEY `idx_create_time` (`create_time`) USING BTREE,
  KEY `idx_member_id` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='跟单执行日志表';

-- ----------------------------
-- Records of think_follow_order_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_follow_partial_track
-- ----------------------------
DROP TABLE IF EXISTS `think_follow_partial_track`;
CREATE TABLE `think_follow_partial_track` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `execution_log_id` int NOT NULL COMMENT '执行日志ID',
  `exchange_order_id` varchar(64) NOT NULL DEFAULT '' COMMENT '交易所订单ID',
  `member_id` int NOT NULL DEFAULT '0' COMMENT '会员ID',
  `symbol` varchar(32) NOT NULL DEFAULT '' COMMENT '交易对',
  `side` tinyint(1) NOT NULL DEFAULT '1' COMMENT '方向:1=买,2=卖',
  `original_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '原始数量',
  `filled_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '已成交数量',
  `remaining_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '剩余数量',
  `fill_percent` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '成交比例%',
  `avg_fill_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '平均成交价',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态:1=等待成交,2=部分成交,3=完全成交,4=已取消,5=已补单',
  `retry_count` int NOT NULL DEFAULT '0' COMMENT '补单次数',
  `last_check_time` int NOT NULL DEFAULT '0' COMMENT '最后检查时间',
  `timeout_time` int NOT NULL DEFAULT '0' COMMENT '超时时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标记:1=有效,0=删除',
  PRIMARY KEY (`id`),
  KEY `idx_execution_log` (`execution_log_id`),
  KEY `idx_exchange_order` (`exchange_order_id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_status` (`status`),
  KEY `idx_timeout` (`status`,`timeout_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='部分成交追踪表';

-- ----------------------------
-- Records of think_follow_partial_track
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_follow_relation
-- ----------------------------
DROP TABLE IF EXISTS `think_follow_relation`;
CREATE TABLE `think_follow_relation` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `source_type` varchar(20) COLLATE utf8mb4_general_ci DEFAULT 'leader' COMMENT '来源类型: leader/strategy',
  `leader_id` int unsigned NOT NULL COMMENT '带单者用户ID',
  `leader_account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '带单者交易所账号ID',
  `strategy_instance_id` int unsigned DEFAULT '0' COMMENT '策略实例ID',
  `strategy_name` varchar(100) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '策略名称',
  `follower_id` int unsigned NOT NULL COMMENT '跟单者用户ID',
  `follower_account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '跟单者交易所账号ID',
  `strategy_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略ID',
  `follow_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '跟单类型：1固定比例 2固定金额 3全仓',
  `follow_direction` tinyint(1) NOT NULL DEFAULT '1' COMMENT '跟单方向: 1=同向跟单, 2=反向跟单',
  `close_follow` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否跟随平仓: 1=是, 0=否',
  `slippage_tolerance` decimal(5,2) NOT NULL DEFAULT '1.00' COMMENT '滑点容忍度(%)',
  `follow_ratio` decimal(5,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '跟单比例(%)',
  `follow_amount` decimal(10,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '固定跟单金额',
  `follow_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '固定跟单数量',
  `max_follow_amount` decimal(10,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '最大跟单金额',
  `min_follow_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '最小跟单数量',
  `max_follow_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '最大跟单数量',
  `min_follow_amount` decimal(10,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '最小跟单金额',
  `auto_follow` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '自动跟单：1是 2否',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2停用',
  `sort` smallint unsigned NOT NULL DEFAULT '125' COMMENT '排序',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '添加时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  `stop_loss_enabled` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否启用止损:0=否,1=是',
  `stop_loss_percent` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '止损百分比',
  `take_profit_enabled` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否启用止盈:0=否,1=是',
  `take_profit_percent` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '止盈百分比',
  `slippage_percent` decimal(10,4) NOT NULL DEFAULT '0.5000' COMMENT '允许滑点百分比',
  `slippage_mode` tinyint(1) NOT NULL DEFAULT '1' COMMENT '滑点模式:1=允许并记录,2=超出则取消,3=超出则调整价格',
  `price_protect_enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '价格保护:0=否,1=是',
  `price_protect_percent` decimal(10,4) NOT NULL DEFAULT '1.0000' COMMENT '价格保护阈值%',
  `partial_fill_mode` tinyint(1) NOT NULL DEFAULT '1' COMMENT '部分成交模式:1=接受部分,2=追加补单,3=取消重下',
  `min_fill_percent` decimal(10,2) NOT NULL DEFAULT '80.00' COMMENT '最小成交比例%',
  `fill_timeout_seconds` int NOT NULL DEFAULT '30' COMMENT '成交等待超时(秒)',
  `split_order_enabled` tinyint(1) NOT NULL DEFAULT '0' COMMENT '大单分拆:0=否,1=是',
  `split_threshold_usdt` decimal(20,2) NOT NULL DEFAULT '10000.00' COMMENT '分拆阈值(USDT)',
  `split_max_parts` int NOT NULL DEFAULT '5' COMMENT '最大分拆数量',
  `split_interval_ms` int NOT NULL DEFAULT '500' COMMENT '分拆间隔(毫秒)',
  `max_daily_orders` int NOT NULL DEFAULT '100' COMMENT '单日最大跟单次数',
  `max_daily_amount` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '单日最大跟单金额',
  `retry_enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用失败重试',
  `max_retry_times` int NOT NULL DEFAULT '3' COMMENT '最大重试次数',
  `priority` int NOT NULL DEFAULT '0' COMMENT '执行优先级',
  `delay_seconds` int NOT NULL DEFAULT '0' COMMENT '延迟执行秒数',
  `symbols_whitelist` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '交易对白名单',
  `symbols_blacklist` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '交易对黑名单',
  `total_followed` int NOT NULL DEFAULT '0' COMMENT '累计跟单次数',
  `total_profit` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '累计盈亏',
  `today_orders` int NOT NULL DEFAULT '0' COMMENT '今日跟单次数',
  `today_amount` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '今日跟单金额',
  `today_date` date DEFAULT NULL COMMENT '今日日期',
  `auto_tp_enabled` tinyint unsigned NOT NULL DEFAULT '0',
  `auto_tp_percent` decimal(5,2) NOT NULL DEFAULT '10.00',
  `auto_sl_enabled` tinyint unsigned NOT NULL DEFAULT '0',
  `auto_sl_percent` decimal(5,2) NOT NULL DEFAULT '5.00',
  `delay_enabled` tinyint unsigned NOT NULL DEFAULT '0',
  `delay_random` int unsigned NOT NULL DEFAULT '0',
  `daily_loss_limit` decimal(12,2) NOT NULL DEFAULT '0.00',
  `daily_trade_limit` int unsigned NOT NULL DEFAULT '0',
  `leverage` int NOT NULL DEFAULT '5' COMMENT '跟单杠杆倍数',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_leader_id` (`leader_id`) USING BTREE,
  KEY `idx_follower_id` (`follower_id`) USING BTREE,
  KEY `idx_strategy_id` (`strategy_id`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_leader_account` (`leader_account_id`),
  KEY `idx_follower_account` (`follower_account_id`),
  KEY `idx_strategy_instance` (`strategy_instance_id`),
  KEY `idx_strategy_follow` (`strategy_instance_id`,`status`,`auto_follow`,`mark`),
  KEY `idx_leader_follow` (`leader_account_id`,`status`,`auto_follow`,`mark`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='跟单关系表';

-- ----------------------------
-- Records of think_follow_relation
-- ----------------------------
BEGIN;
INSERT INTO `think_follow_relation` (`id`, `source_type`, `leader_id`, `leader_account_id`, `strategy_instance_id`, `strategy_name`, `follower_id`, `follower_account_id`, `strategy_id`, `follow_type`, `follow_direction`, `close_follow`, `slippage_tolerance`, `follow_ratio`, `follow_amount`, `follow_quantity`, `max_follow_amount`, `min_follow_quantity`, `max_follow_quantity`, `min_follow_amount`, `auto_follow`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`, `stop_loss_enabled`, `stop_loss_percent`, `take_profit_enabled`, `take_profit_percent`, `slippage_percent`, `slippage_mode`, `price_protect_enabled`, `price_protect_percent`, `partial_fill_mode`, `min_fill_percent`, `fill_timeout_seconds`, `split_order_enabled`, `split_threshold_usdt`, `split_max_parts`, `split_interval_ms`, `max_daily_orders`, `max_daily_amount`, `retry_enabled`, `max_retry_times`, `priority`, `delay_seconds`, `symbols_whitelist`, `symbols_blacklist`, `total_followed`, `total_profit`, `today_orders`, `today_amount`, `today_date`, `auto_tp_enabled`, `auto_tp_percent`, `auto_sl_enabled`, `auto_sl_percent`, `delay_enabled`, `delay_random`, `daily_loss_limit`, `daily_trade_limit`, `leverage`) VALUES (1, 'strategy', 0, 0, 7, 'ETH对冲保守-4H', 1, 1, 0, 1, 1, 1, 1.00, 0.10, 15.00, 0.00000000, 50.00, 0.00000000, 0.00000000, 1.00, 1, 1, 125, 1, 1770028455, 1, 1770100593, 0, 0, 0.00, 0, 0.00, 0.5000, 1, 1, 1.0000, 1, 80.00, 30, 0, 10000.00, 5, 500, 100, 0.00000000, 1, 3, 0, 3, '', '', 0, 0.00000000, 0, 0.00000000, '2026-02-02', 0, 10.00, 0, 5.00, 0, 0, 0.00, 0, 5);
INSERT INTO `think_follow_relation` (`id`, `source_type`, `leader_id`, `leader_account_id`, `strategy_instance_id`, `strategy_name`, `follower_id`, `follower_account_id`, `strategy_id`, `follow_type`, `follow_direction`, `close_follow`, `slippage_tolerance`, `follow_ratio`, `follow_amount`, `follow_quantity`, `max_follow_amount`, `min_follow_quantity`, `max_follow_quantity`, `min_follow_amount`, `auto_follow`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`, `stop_loss_enabled`, `stop_loss_percent`, `take_profit_enabled`, `take_profit_percent`, `slippage_percent`, `slippage_mode`, `price_protect_enabled`, `price_protect_percent`, `partial_fill_mode`, `min_fill_percent`, `fill_timeout_seconds`, `split_order_enabled`, `split_threshold_usdt`, `split_max_parts`, `split_interval_ms`, `max_daily_orders`, `max_daily_amount`, `retry_enabled`, `max_retry_times`, `priority`, `delay_seconds`, `symbols_whitelist`, `symbols_blacklist`, `total_followed`, `total_profit`, `today_orders`, `today_amount`, `today_date`, `auto_tp_enabled`, `auto_tp_percent`, `auto_sl_enabled`, `auto_sl_percent`, `delay_enabled`, `delay_random`, `daily_loss_limit`, `daily_trade_limit`, `leverage`) VALUES (2, 'strategy', 0, 0, 1, 'BTC均线金叉-15分钟', 2, 0, 0, 1, 1, 1, 1.00, 50.00, 0.00, 0.00000000, 0.00, 0.00000000, 0.00000000, 0.00, 1, 1, 125, 1, 1770028470, 1, 1770029488, 0, 0, 0.00, 0, 0.00, 0.5000, 1, 1, 1.0000, 1, 80.00, 30, 0, 10000.00, 5, 500, 100, 0.00000000, 1, 3, 0, 0, '', '', 0, 0.00000000, 0, 0.00000000, '2026-02-02', 0, 10.00, 0, 5.00, 0, 0, 0.00, 0, 5);
INSERT INTO `think_follow_relation` (`id`, `source_type`, `leader_id`, `leader_account_id`, `strategy_instance_id`, `strategy_name`, `follower_id`, `follower_account_id`, `strategy_id`, `follow_type`, `follow_direction`, `close_follow`, `slippage_tolerance`, `follow_ratio`, `follow_amount`, `follow_quantity`, `max_follow_amount`, `min_follow_quantity`, `max_follow_quantity`, `min_follow_amount`, `auto_follow`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`, `stop_loss_enabled`, `stop_loss_percent`, `take_profit_enabled`, `take_profit_percent`, `slippage_percent`, `slippage_mode`, `price_protect_enabled`, `price_protect_percent`, `partial_fill_mode`, `min_fill_percent`, `fill_timeout_seconds`, `split_order_enabled`, `split_threshold_usdt`, `split_max_parts`, `split_interval_ms`, `max_daily_orders`, `max_daily_amount`, `retry_enabled`, `max_retry_times`, `priority`, `delay_seconds`, `symbols_whitelist`, `symbols_blacklist`, `total_followed`, `total_profit`, `today_orders`, `today_amount`, `today_date`, `auto_tp_enabled`, `auto_tp_percent`, `auto_sl_enabled`, `auto_sl_percent`, `delay_enabled`, `delay_random`, `daily_loss_limit`, `daily_trade_limit`, `leverage`) VALUES (3, 'leader', 1, 2, 0, '', 1, 3, 0, 1, 1, 1, 1.00, 10.00, 15.00, 0.00000000, 50.00, 0.00000000, 0.00000000, 1.00, 1, 1, 125, 1, 1770033843, 0, 0, 1, 0, 0.00, 0, 0.00, 0.5000, 1, 1, 1.0000, 1, 80.00, 30, 0, 10000.00, 5, 500, 100, 0.00000000, 1, 3, 0, 3, '', '', 0, 0.00000000, 0, 0.00000000, '2026-02-02', 0, 10.00, 0, 5.00, 0, 0, 0.00, 0, 5);
INSERT INTO `think_follow_relation` (`id`, `source_type`, `leader_id`, `leader_account_id`, `strategy_instance_id`, `strategy_name`, `follower_id`, `follower_account_id`, `strategy_id`, `follow_type`, `follow_direction`, `close_follow`, `slippage_tolerance`, `follow_ratio`, `follow_amount`, `follow_quantity`, `max_follow_amount`, `min_follow_quantity`, `max_follow_quantity`, `min_follow_amount`, `auto_follow`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`, `stop_loss_enabled`, `stop_loss_percent`, `take_profit_enabled`, `take_profit_percent`, `slippage_percent`, `slippage_mode`, `price_protect_enabled`, `price_protect_percent`, `partial_fill_mode`, `min_fill_percent`, `fill_timeout_seconds`, `split_order_enabled`, `split_threshold_usdt`, `split_max_parts`, `split_interval_ms`, `max_daily_orders`, `max_daily_amount`, `retry_enabled`, `max_retry_times`, `priority`, `delay_seconds`, `symbols_whitelist`, `symbols_blacklist`, `total_followed`, `total_profit`, `today_orders`, `today_amount`, `today_date`, `auto_tp_enabled`, `auto_tp_percent`, `auto_sl_enabled`, `auto_sl_percent`, `delay_enabled`, `delay_random`, `daily_loss_limit`, `daily_trade_limit`, `leverage`) VALUES (4, '2', 0, 0, 9, '', 1, 1, 3, 1, 1, 1, 0.50, 100.00, 0.00, 0.00000000, 0.00, 0.00000000, 0.00000000, 0.00, 1, 1, 125, 0, 1770095731, 1, 1770099574, 0, 1, 2.00, 1, 3.00, 0.5000, 1, 1, 1.0000, 1, 80.00, 30, 0, 10000.00, 5, 500, 100, 0.00000000, 1, 3, 0, 0, '', '', 0, 0.00000000, 0, 0.00000000, NULL, 0, 10.00, 0, 5.00, 0, 0, 0.00, 0, 5);
COMMIT;

-- ----------------------------
-- Table structure for think_follow_split_order
-- ----------------------------
DROP TABLE IF EXISTS `think_follow_split_order`;
CREATE TABLE `think_follow_split_order` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `parent_log_id` int NOT NULL COMMENT '父执行日志ID',
  `member_id` int NOT NULL DEFAULT '0' COMMENT '会员ID',
  `symbol` varchar(32) NOT NULL DEFAULT '' COMMENT '交易对',
  `side` tinyint(1) NOT NULL DEFAULT '1' COMMENT '方向',
  `total_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总数量',
  `total_amount` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总金额',
  `split_count` int NOT NULL DEFAULT '0' COMMENT '分拆数量',
  `executed_count` int NOT NULL DEFAULT '0' COMMENT '已执行数量',
  `success_count` int NOT NULL DEFAULT '0' COMMENT '成功数量',
  `failed_count` int NOT NULL DEFAULT '0' COMMENT '失败数量',
  `total_filled_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总成交数量',
  `avg_fill_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '平均成交价',
  `total_fee` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总手续费',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态:1=执行中,2=全部成功,3=部分成功,4=全部失败',
  `start_time` int NOT NULL DEFAULT '0' COMMENT '开始时间',
  `end_time` int NOT NULL DEFAULT '0' COMMENT '结束时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标记',
  PRIMARY KEY (`id`),
  KEY `idx_parent_log` (`parent_log_id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='订单分拆记录表';

-- ----------------------------
-- Records of think_follow_split_order
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_follow_strategy
-- ----------------------------
DROP TABLE IF EXISTS `think_follow_strategy`;
CREATE TABLE `think_follow_strategy` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL DEFAULT '' COMMENT '策略名称',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '用户ID',
  `leader_id` int unsigned NOT NULL DEFAULT '0' COMMENT '带单员ID',
  `follow_mode` varchar(20) NOT NULL DEFAULT 'ratio' COMMENT '跟单模式: ratio比例, fixed固定, copy复制',
  `follow_ratio` decimal(10,4) DEFAULT '1.0000' COMMENT '跟单比例(1.0=100%)',
  `fixed_amount` decimal(15,2) DEFAULT '0.00' COMMENT '固定金额',
  `max_position` decimal(15,2) DEFAULT '0.00' COMMENT '最大持仓金额(0=不限)',
  `direction_mode` varchar(20) DEFAULT 'same' COMMENT '方向模式: same同向, reverse反向',
  `delay_enabled` tinyint DEFAULT '0' COMMENT '是否启用延迟',
  `delay_seconds` int DEFAULT '0' COMMENT '延迟秒数',
  `delay_random_max` int DEFAULT '0' COMMENT '随机延迟最大值',
  `leverage_mode` varchar(20) DEFAULT 'same' COMMENT '杠杆模式: same跟随, fixed固定, max最大',
  `fixed_leverage` int DEFAULT '0' COMMENT '固定杠杆倍数',
  `max_leverage` int DEFAULT '20' COMMENT '最大杠杆限制',
  `symbol_whitelist` text COMMENT '交易对白名单(逗号分隔)',
  `symbol_blacklist` text COMMENT '交易对黑名单(逗号分隔)',
  `auto_tp_enabled` tinyint DEFAULT '0' COMMENT '自动止盈',
  `auto_tp_percent` decimal(5,2) DEFAULT '0.00' COMMENT '止盈百分比',
  `auto_sl_enabled` tinyint DEFAULT '0' COMMENT '自动止损',
  `auto_sl_percent` decimal(5,2) DEFAULT '0.00' COMMENT '止损百分比',
  `daily_loss_limit` decimal(15,2) DEFAULT '0.00' COMMENT '日亏损限制(0=不限)',
  `daily_trade_limit` int DEFAULT '0' COMMENT '日交易次数限制(0=不限)',
  `min_trade_amount` decimal(15,2) DEFAULT '0.00' COMMENT '最小交易金额',
  `trade_time_enabled` tinyint DEFAULT '0' COMMENT '是否启用交易时间限制',
  `trade_time_start` time DEFAULT NULL COMMENT '交易开始时间',
  `trade_time_end` time DEFAULT NULL COMMENT '交易结束时间',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态:1启用 0禁用',
  `priority` int DEFAULT '0' COMMENT '优先级(高优先)',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_leader` (`leader_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='跟单策略表';

-- ----------------------------
-- Records of think_follow_strategy
-- ----------------------------
BEGIN;
INSERT INTO `think_follow_strategy` (`id`, `name`, `member_id`, `leader_id`, `follow_mode`, `follow_ratio`, `fixed_amount`, `max_position`, `direction_mode`, `delay_enabled`, `delay_seconds`, `delay_random_max`, `leverage_mode`, `fixed_leverage`, `max_leverage`, `symbol_whitelist`, `symbol_blacklist`, `auto_tp_enabled`, `auto_tp_percent`, `auto_sl_enabled`, `auto_sl_percent`, `daily_loss_limit`, `daily_trade_limit`, `min_trade_amount`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `status`, `priority`, `create_time`, `update_time`, `mark`) VALUES (1, 'updated', 1, 1, 'ratio', 0.8000, 0.00, 0.00, 'same', 0, 0, 0, 'same', 0, 20, '', '', 0, 0.00, 0, 0.00, 0.00, 0, 0.00, 0, NULL, NULL, 1, 0, 1770002569, 1770002725, 1);
INSERT INTO `think_follow_strategy` (`id`, `name`, `member_id`, `leader_id`, `follow_mode`, `follow_ratio`, `fixed_amount`, `max_position`, `direction_mode`, `delay_enabled`, `delay_seconds`, `delay_random_max`, `leverage_mode`, `fixed_leverage`, `max_leverage`, `symbol_whitelist`, `symbol_blacklist`, `auto_tp_enabled`, `auto_tp_percent`, `auto_sl_enabled`, `auto_sl_percent`, `daily_loss_limit`, `daily_trade_limit`, `min_trade_amount`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `status`, `priority`, `create_time`, `update_time`, `mark`) VALUES (2, 'ETH跟单策略', 1, 1, 'ratio', 0.5000, 0.00, 0.00, 'same', 0, 0, 0, 'same', 0, 20, '', '', 0, 0.00, 0, 0.00, 0.00, 0, 0.00, 0, NULL, NULL, 1, 0, 1770002743, 1770002743, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_funding_rate
-- ----------------------------
DROP TABLE IF EXISTS `think_funding_rate`;
CREATE TABLE `think_funding_rate` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `exchange` varchar(50) NOT NULL DEFAULT 'binance' COMMENT '交易所',
  `symbol` varchar(50) NOT NULL COMMENT '交易对',
  `rate` decimal(20,10) NOT NULL DEFAULT '0.0000000000' COMMENT '当前费率',
  `predicted_rate` decimal(20,10) DEFAULT '0.0000000000' COMMENT '预测费率',
  `next_funding_time` int unsigned DEFAULT '0' COMMENT '下次结算时间',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_exchange_symbol` (`exchange`,`symbol`),
  KEY `idx_rate` (`rate`),
  KEY `idx_update_time` (`update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='资金费率表';

-- ----------------------------
-- Records of think_funding_rate
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_funding_rate_alert
-- ----------------------------
DROP TABLE IF EXISTS `think_funding_rate_alert`;
CREATE TABLE `think_funding_rate_alert` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned DEFAULT '0' COMMENT '用户ID',
  `exchange` varchar(50) NOT NULL DEFAULT 'binance',
  `symbol` varchar(50) NOT NULL,
  `alert_type` varchar(20) DEFAULT 'above' COMMENT 'above/below',
  `threshold` decimal(20,10) NOT NULL DEFAULT '0.0000000000' COMMENT '阈值',
  `status` tinyint DEFAULT '1' COMMENT '1启用 0停用',
  `last_triggered` int unsigned DEFAULT '0' COMMENT '上次触发时间',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='资金费率提醒表';

-- ----------------------------
-- Records of think_funding_rate_alert
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_funding_rate_history
-- ----------------------------
DROP TABLE IF EXISTS `think_funding_rate_history`;
CREATE TABLE `think_funding_rate_history` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `exchange` varchar(50) NOT NULL DEFAULT 'binance',
  `symbol` varchar(50) NOT NULL,
  `rate` decimal(20,10) NOT NULL DEFAULT '0.0000000000',
  `funding_time` int unsigned NOT NULL COMMENT '结算时间',
  `create_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_exchange_symbol_time` (`exchange`,`symbol`,`funding_time`),
  KEY `idx_symbol_time` (`symbol`,`funding_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='资金费率历史表';

-- ----------------------------
-- Records of think_funding_rate_history
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_hedge_group
-- ----------------------------
DROP TABLE IF EXISTS `think_hedge_group`;
CREATE TABLE `think_hedge_group` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `symbol` varchar(50) NOT NULL,
  `member_id` int unsigned DEFAULT '0',
  `long_account_id` int unsigned DEFAULT '0',
  `short_account_id` int unsigned DEFAULT '0',
  `long_quantity` decimal(20,8) DEFAULT '0.00000000',
  `short_quantity` decimal(20,8) DEFAULT '0.00000000',
  `net_exposure` decimal(20,8) DEFAULT '0.00000000',
  `total_pnl` decimal(20,4) DEFAULT '0.0000',
  `status` tinyint DEFAULT '1',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='对冲组合表';

-- ----------------------------
-- Records of think_hedge_group
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_indicator_alert
-- ----------------------------
DROP TABLE IF EXISTS `think_indicator_alert`;
CREATE TABLE `think_indicator_alert` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned DEFAULT '0',
  `symbol` varchar(50) NOT NULL,
  `timeframe` varchar(10) DEFAULT '1h',
  `indicator` varchar(20) NOT NULL,
  `alert_condition` varchar(20) DEFAULT 'above',
  `threshold` decimal(20,4) DEFAULT '0.0000',
  `params` json DEFAULT NULL,
  `status` tinyint DEFAULT '1',
  `last_val` decimal(20,4) DEFAULT '0.0000',
  `last_triggered` int unsigned DEFAULT '0',
  `trigger_count` int DEFAULT '0',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指标预警表';

-- ----------------------------
-- Records of think_indicator_alert
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_indicator_alert_log
-- ----------------------------
DROP TABLE IF EXISTS `think_indicator_alert_log`;
CREATE TABLE `think_indicator_alert_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `alert_id` int unsigned NOT NULL,
  `member_id` int unsigned DEFAULT '0',
  `symbol` varchar(50) NOT NULL,
  `indicator` varchar(20) NOT NULL,
  `alert_condition` varchar(20) DEFAULT 'above',
  `threshold` decimal(20,4) DEFAULT '0.0000',
  `actual_value` decimal(20,4) DEFAULT '0.0000',
  `create_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指标预警日志表';

-- ----------------------------
-- Records of think_indicator_alert_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_indicator_cache
-- ----------------------------
DROP TABLE IF EXISTS `think_indicator_cache`;
CREATE TABLE `think_indicator_cache` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `timeframe` varchar(10) NOT NULL DEFAULT '1h' COMMENT '周期',
  `indicator` varchar(30) NOT NULL DEFAULT '' COMMENT '指标名：MA20/EMA5/RSI14/MACD/ATR14',
  `value` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '指标值',
  `extra_values` text COMMENT '额外值JSON（如MACD的signal/hist）',
  `candle_time` int unsigned NOT NULL DEFAULT '0' COMMENT 'K线时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_symbol_tf_ind` (`symbol`,`timeframe`,`indicator`),
  KEY `idx_candle_time` (`candle_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指标缓存表';

-- ----------------------------
-- Records of think_indicator_cache
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_ip_allocation
-- ----------------------------
DROP TABLE IF EXISTS `think_ip_allocation`;
CREATE TABLE `think_ip_allocation` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `ip_id` int unsigned NOT NULL DEFAULT '0' COMMENT 'IP库存ID',
  `ip_address` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'IP地址',
  `agent_id` int unsigned NOT NULL DEFAULT '0' COMMENT '分配的代理商ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '绑定的会员ID',
  `allocation_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '分配类型：1分配 2回收',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1有效 2已回收',
  `allocation_time` int unsigned NOT NULL DEFAULT '0' COMMENT '分配时间',
  `recovery_time` int unsigned NOT NULL DEFAULT '0' COMMENT '回收时间',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_ip_id` (`ip_id`) USING BTREE,
  KEY `idx_agent_id` (`agent_id`) USING BTREE,
  KEY `idx_member_id` (`member_id`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_allocation_time` (`allocation_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='IP分配记录表';

-- ----------------------------
-- Records of think_ip_allocation
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_ip_inventory
-- ----------------------------
DROP TABLE IF EXISTS `think_ip_inventory`;
CREATE TABLE `think_ip_inventory` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `ip_address` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'IP地址',
  `ip_type` tinyint unsigned NOT NULL COMMENT 'IP类型：1EIP 2轻量服务器 3平台IP',
  `ip_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'IP名称',
  `region` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '地域',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1可用 2已分配 3已禁用',
  `agent_id` int unsigned DEFAULT '0' COMMENT '分配的代理商ID',
  `member_id` int unsigned DEFAULT '0' COMMENT '绑定的会员ID',
  `is_primary` tinyint unsigned DEFAULT '0' COMMENT '是否主IP：1是 0否',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_ip_address` (`ip_address`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_agent_id` (`agent_id`) USING BTREE,
  KEY `idx_member_id` (`member_id`) USING BTREE,
  KEY `idx_ip_type` (`ip_type`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='IP库存表';

-- ----------------------------
-- Records of think_ip_inventory
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_klines_unified
-- ----------------------------
DROP TABLE IF EXISTS `think_klines_unified`;
CREATE TABLE `think_klines_unified` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `exchange` varchar(32) NOT NULL COMMENT '交易所 binance/okx',
  `symbol` varchar(32) NOT NULL COMMENT '交易对 BTC/USDT',
  `timeframe` varchar(16) NOT NULL COMMENT '周期 1m/5m/15m/1h/4h/1d',
  `ts` int unsigned NOT NULL COMMENT 'K线时间戳(UTC秒)',
  `open` decimal(20,8) NOT NULL COMMENT '开盘价',
  `high` decimal(20,8) NOT NULL COMMENT '最高价',
  `low` decimal(20,8) NOT NULL COMMENT '最低价',
  `close` decimal(20,8) NOT NULL COMMENT '收盘价',
  `volume` decimal(30,8) NOT NULL DEFAULT '0.00000000' COMMENT '成交量',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_kline` (`exchange`,`symbol`,`timeframe`,`ts`),
  KEY `idx_symbol_tf` (`symbol`,`timeframe`),
  KEY `idx_ts` (`ts`),
  KEY `idx_exchange` (`exchange`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='统一K线数据表';

-- ----------------------------
-- Records of think_klines_unified
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_leader_daily_stats
-- ----------------------------
DROP TABLE IF EXISTS `think_leader_daily_stats`;
CREATE TABLE `think_leader_daily_stats` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `leader_id` int unsigned NOT NULL DEFAULT '0' COMMENT '带单员ID',
  `stat_date` date NOT NULL COMMENT '统计日期',
  `trade_count` int DEFAULT '0' COMMENT '交易次数',
  `win_count` int DEFAULT '0' COMMENT '盈利次数',
  `loss_count` int DEFAULT '0' COMMENT '亏损次数',
  `profit` decimal(20,2) DEFAULT '0.00' COMMENT '当日收益',
  `commission` decimal(20,2) DEFAULT '0.00' COMMENT '当日分成',
  `new_followers` int DEFAULT '0' COMMENT '新增跟随',
  `lost_followers` int DEFAULT '0' COMMENT '取消跟随',
  `follower_profit` decimal(20,2) DEFAULT '0.00' COMMENT '跟随者收益',
  `cumulative_profit` decimal(20,2) DEFAULT '0.00' COMMENT '累计收益',
  `cumulative_rate` decimal(10,2) DEFAULT '0.00' COMMENT '累计收益率(%)',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned DEFAULT '1' COMMENT '标记',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_leader_date` (`leader_id`,`stat_date`),
  KEY `idx_date` (`stat_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='带单员每日绩效表';

-- ----------------------------
-- Records of think_leader_daily_stats
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_leader_info
-- ----------------------------
DROP TABLE IF EXISTS `think_leader_info`;
CREATE TABLE `think_leader_info` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '用户ID',
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '交易所账号ID',
  `exchange` varchar(32) NOT NULL DEFAULT 'binance' COMMENT '交易所名称',
  `account_name` varchar(128) NOT NULL DEFAULT '' COMMENT '账号名称',
  `leader_name` varchar(50) DEFAULT '' COMMENT '带单员名称',
  `avatar` varchar(255) DEFAULT '' COMMENT '头像',
  `description` varchar(500) DEFAULT '' COMMENT '简介',
  `is_verified` tinyint DEFAULT '0' COMMENT '是否认证',
  `verified_time` int unsigned DEFAULT '0' COMMENT '认证时间',
  `level` tinyint DEFAULT '1' COMMENT '等级:1-5',
  `commission_rate` decimal(5,2) DEFAULT '10.00' COMMENT '分成比例(%)',
  `min_follow_amount` decimal(20,2) DEFAULT '100.00' COMMENT '最低跟单金额',
  `max_followers` int DEFAULT '100' COMMENT '最大跟随人数',
  `total_followers` int DEFAULT '0' COMMENT '累计跟随人数',
  `current_followers` int DEFAULT '0' COMMENT '当前跟随人数',
  `total_trades` int DEFAULT '0' COMMENT '累计交易次数',
  `win_trades` int DEFAULT '0' COMMENT '盈利交易次数',
  `total_profit` decimal(20,2) DEFAULT '0.00' COMMENT '累计收益(USDT)',
  `total_commission` decimal(20,2) DEFAULT '0.00' COMMENT '累计分成(USDT)',
  `win_rate` decimal(5,2) DEFAULT '0.00' COMMENT '胜率(%)',
  `avg_profit_rate` decimal(10,2) DEFAULT '0.00' COMMENT '平均收益率(%)',
  `max_drawdown` decimal(10,2) DEFAULT '0.00' COMMENT '最大回撤(%)',
  `sharpe_ratio` decimal(10,4) DEFAULT '0.0000' COMMENT '夏普比率',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态:1启用 0禁用',
  `sort` int DEFAULT '0' COMMENT '排序',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_account` (`account_id`),
  KEY `idx_status` (`status`),
  KEY `idx_level` (`level`),
  KEY `idx_account_id` (`account_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='带单员信息表';

-- ----------------------------
-- Records of think_leader_info
-- ----------------------------
BEGIN;
INSERT INTO `think_leader_info` (`id`, `member_id`, `account_id`, `exchange`, `account_name`, `leader_name`, `avatar`, `description`, `is_verified`, `verified_time`, `level`, `commission_rate`, `min_follow_amount`, `max_followers`, `total_followers`, `current_followers`, `total_trades`, `win_trades`, `total_profit`, `total_commission`, `win_rate`, `avg_profit_rate`, `max_drawdown`, `sharpe_ratio`, `status`, `sort`, `create_time`, `update_time`, `mark`) VALUES (1, 1, 1, 'binance', '', '测试带单员1', '', '', 0, 0, 1, 10.00, 100.00, 100, 0, 0, 0, 0, 0.00, 0.00, 0.00, 0.00, 0.00, 0.0000, 1, 0, 1769527888, 1770027076, 0);
INSERT INTO `think_leader_info` (`id`, `member_id`, `account_id`, `exchange`, `account_name`, `leader_name`, `avatar`, `description`, `is_verified`, `verified_time`, `level`, `commission_rate`, `min_follow_amount`, `max_followers`, `total_followers`, `current_followers`, `total_trades`, `win_trades`, `total_profit`, `total_commission`, `win_rate`, `avg_profit_rate`, `max_drawdown`, `sharpe_ratio`, `status`, `sort`, `create_time`, `update_time`, `mark`) VALUES (7, 1, 2, 'okx', 'okx-a3bb26d2...', '带单之王', '', '', 0, 0, 1, 10.00, 1000.00, 100, 0, 0, 0, 0, 0.00, 0.00, 0.00, 0.00, 0.00, 0.0000, 1, 0, 1770033467, 1770033511, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_leader_settlement
-- ----------------------------
DROP TABLE IF EXISTS `think_leader_settlement`;
CREATE TABLE `think_leader_settlement` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `leader_id` int unsigned NOT NULL DEFAULT '0' COMMENT '带单员ID',
  `settlement_no` varchar(32) NOT NULL DEFAULT '' COMMENT '结算单号',
  `period_start` date NOT NULL COMMENT '周期开始',
  `period_end` date NOT NULL COMMENT '周期结束',
  `total_profit` decimal(20,2) DEFAULT '0.00' COMMENT '周期总收益',
  `follower_profit` decimal(20,2) DEFAULT '0.00' COMMENT '跟随者收益',
  `commission_rate` decimal(5,2) DEFAULT '0.00' COMMENT '分成比例',
  `commission_amount` decimal(20,2) DEFAULT '0.00' COMMENT '分成金额',
  `platform_fee` decimal(20,2) DEFAULT '0.00' COMMENT '平台费用',
  `net_amount` decimal(20,2) DEFAULT '0.00' COMMENT '净收入',
  `status` tinyint DEFAULT '0' COMMENT '状态:0待审核 1已审核 2已发放 3已拒绝',
  `audit_user_id` int DEFAULT '0' COMMENT '审核人',
  `audit_time` int unsigned DEFAULT '0' COMMENT '审核时间',
  `audit_note` varchar(200) DEFAULT '' COMMENT '审核备注',
  `pay_time` int unsigned DEFAULT '0' COMMENT '发放时间',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_no` (`settlement_no`),
  KEY `idx_leader` (`leader_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='分成结算记录表';

-- ----------------------------
-- Records of think_leader_settlement
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_leader_tag
-- ----------------------------
DROP TABLE IF EXISTS `think_leader_tag`;
CREATE TABLE `think_leader_tag` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(50) NOT NULL DEFAULT '' COMMENT '标签名称',
  `code` varchar(30) NOT NULL DEFAULT '' COMMENT '标签代码',
  `category` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '分类：1=风格 2=周期 3=品种 4=特征',
  `color` varchar(20) NOT NULL DEFAULT '#409EFF' COMMENT '标签颜色',
  `icon` varchar(50) NOT NULL DEFAULT '' COMMENT '图标',
  `description` varchar(200) NOT NULL DEFAULT '' COMMENT '描述',
  `sort` int unsigned NOT NULL DEFAULT '125' COMMENT '排序',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1=启用 2=停用',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '删除标记：1=正常 0=删除',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '创建人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_code` (`code`),
  KEY `idx_category` (`category`),
  KEY `idx_status` (`status`),
  KEY `idx_mark` (`mark`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='带单员标签表';

-- ----------------------------
-- Records of think_leader_tag
-- ----------------------------
BEGIN;
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (1, '激进型', 'aggressive', 1, '#F56C6C', '', '高风险高收益，追求快速盈利', 1, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (2, '保守型', 'conservative', 1, '#67C23A', '', '低风险稳健，注重资金安全', 2, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (3, '稳健型', 'steady', 1, '#409EFF', '', '风险适中，追求稳定收益', 3, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (4, '超短线', 'scalping', 2, '#E6A23C', '', '持仓时间极短，快进快出', 1, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (5, '短线', 'short_term', 2, '#F56C6C', '', '日内或隔夜持仓', 2, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (6, '波段', 'swing', 2, '#409EFF', '', '持仓数天到数周', 3, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (7, '长线', 'long_term', 2, '#67C23A', '', '持仓数周到数月', 4, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (8, 'BTC专精', 'btc_focus', 3, '#F7931A', '', '专注比特币交易', 1, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (9, 'ETH专精', 'eth_focus', 3, '#627EEA', '', '专注以太坊交易', 2, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (10, '山寨专精', 'altcoin_focus', 3, '#9B59B6', '', '专注山寨币交易', 3, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (11, '多品种', 'multi_coin', 3, '#1ABC9C', '', '多币种综合交易', 4, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (12, '高胜率', 'high_win_rate', 4, '#67C23A', '', '胜率超过60%', 1, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (13, '高盈亏比', 'high_profit_ratio', 4, '#409EFF', '', '盈亏比超过2:1', 2, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (14, '低回撤', 'low_drawdown', 4, '#67C23A', '', '最大回撤低于20%', 3, 1, 1, 0, 1769502201, 0, 0);
INSERT INTO `think_leader_tag` (`id`, `name`, `code`, `category`, `color`, `icon`, `description`, `sort`, `status`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (15, '高频交易', 'high_frequency', 4, '#E6A23C', '', '交易频率高', 4, 1, 1, 0, 1769502201, 0, 0);
COMMIT;

-- ----------------------------
-- Table structure for think_leader_tag_relation
-- ----------------------------
DROP TABLE IF EXISTS `think_leader_tag_relation`;
CREATE TABLE `think_leader_tag_relation` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `leader_id` int unsigned NOT NULL DEFAULT '0' COMMENT '带单员ID',
  `tag_id` int unsigned NOT NULL DEFAULT '0' COMMENT '标签ID',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_leader_tag` (`leader_id`,`tag_id`),
  KEY `idx_leader_id` (`leader_id`),
  KEY `idx_tag_id` (`tag_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='带单员标签关系表';

-- ----------------------------
-- Records of think_leader_tag_relation
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_lightweight_server
-- ----------------------------
DROP TABLE IF EXISTS `think_lightweight_server`;
CREATE TABLE `think_lightweight_server` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `server_id` varchar(100) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '外部服务器ID（如ECS实例ID）',
  `server_token` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '服务器认证Token',
  `bound_ip` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Token绑定的IP',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '节点名称',
  `region` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '地域',
  `package_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '套餐类型',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1正常 2错误',
  `exchange` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '交易所类型',
  `inventory_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '入库ID',
  `ip_address` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'IP地址',
  `error_msg` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '错误信息',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  `last_heartbeat` int unsigned DEFAULT '0' COMMENT '最后心跳时间',
  `current_load` decimal(5,2) DEFAULT '0.00' COMMENT '当前负载',
  `task_count` int unsigned DEFAULT '0' COMMENT '已处理任务数',
  `member_count` int DEFAULT '0' COMMENT '绑定会员数',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_server_id` (`server_id`) USING BTREE,
  UNIQUE KEY `idx_server_token` (`server_token`),
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_inventory_id` (`inventory_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='轻量服务器表';

-- ----------------------------
-- Records of think_lightweight_server
-- ----------------------------
BEGIN;
INSERT INTO `think_lightweight_server` (`id`, `server_id`, `server_token`, `bound_ip`, `name`, `region`, `package_type`, `status`, `exchange`, `inventory_id`, `ip_address`, `error_msg`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`, `last_heartbeat`, `current_load`, `task_count`, `member_count`) VALUES (1, 'local_server_001', '3729167e6c7470e19e949c97d70a2586', '127.0.0.1', '测试', 'local', 'standard', 1, NULL, NULL, '127.0.0.1', NULL, NULL, 0, 1769653749, 1, 1770132800, 1, 1770132800, 0.00, 0, 0);
INSERT INTO `think_lightweight_server` (`id`, `server_id`, `server_token`, `bound_ip`, `name`, `region`, `package_type`, `status`, `exchange`, `inventory_id`, `ip_address`, `error_msg`, `remark`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`, `last_heartbeat`, `current_load`, `task_count`, `member_count`) VALUES (2, '', NULL, NULL, 'ddd', NULL, NULL, 1, '', NULL, '199.123.192.100', NULL, NULL, 0, 1769959894, 0, 1769960490, 0, 1769960490, 0.00, 0, 0);
COMMIT;

-- ----------------------------
-- Table structure for think_marketplace_leader
-- ----------------------------
DROP TABLE IF EXISTS `think_marketplace_leader`;
CREATE TABLE `think_marketplace_leader` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL,
  `nickname` varchar(100) DEFAULT '',
  `avatar` varchar(255) DEFAULT '',
  `description` text,
  `tags` json DEFAULT NULL,
  `total_pnl` decimal(20,4) DEFAULT '0.0000',
  `win_rate` decimal(10,2) DEFAULT '0.00',
  `total_trades` int DEFAULT '0',
  `follower_count` int DEFAULT '0',
  `aum` decimal(20,4) DEFAULT '0.0000' COMMENT '管理资金',
  `equity_curve` json DEFAULT NULL,
  `status` tinyint DEFAULT '1',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='带单员广场表';

-- ----------------------------
-- Records of think_marketplace_leader
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_marketplace_strategy
-- ----------------------------
DROP TABLE IF EXISTS `think_marketplace_strategy`;
CREATE TABLE `think_marketplace_strategy` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `strategy_id` int unsigned NOT NULL,
  `member_id` int unsigned DEFAULT '0',
  `name` varchar(100) NOT NULL,
  `description` text,
  `category` varchar(50) DEFAULT 'trend',
  `tags` json DEFAULT NULL,
  `params` json DEFAULT NULL,
  `total_pnl` decimal(20,4) DEFAULT '0.0000',
  `win_rate` decimal(10,2) DEFAULT '0.00',
  `total_trades` int DEFAULT '0',
  `monthly_return` decimal(10,2) DEFAULT '0.00',
  `max_drawdown` decimal(10,2) DEFAULT '0.00',
  `sharpe_ratio` decimal(10,2) DEFAULT '0.00',
  `follower_count` int DEFAULT '0',
  `is_public` tinyint DEFAULT '1',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略广场表';

-- ----------------------------
-- Records of think_marketplace_strategy
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_member
-- ----------------------------
DROP TABLE IF EXISTS `think_member`;
CREATE TABLE `think_member` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '用户名/邮箱',
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮箱',
  `password` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '密码',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用 1、启用  2、停用',
  `inviter_id` int unsigned NOT NULL DEFAULT '0' COMMENT '邀请人ID',
  `agent_id` int unsigned DEFAULT NULL COMMENT '所属代理商ID',
  `is_root` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '是否根用户：1是 0否',
  `inviter_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '邀请链路',
  `invite_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '邀请码(纯数字)',
  `point_card_self` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '自充点卡余额',
  `point_card_gift` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '赠送点卡余额',
  `account_balance` decimal(20,8) DEFAULT '0.00000000' COMMENT '账户余额',
  `available_balance` decimal(20,8) DEFAULT '0.00000000' COMMENT '可用余额',
  `create_user` int NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int NOT NULL DEFAULT '0' COMMENT '修改人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned DEFAULT '1' COMMENT '有效标识',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_invite_code` (`invite_code`) USING BTREE,
  KEY `username` (`username`) USING BTREE,
  KEY `idx_mark` (`mark`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_inviter_id` (`inviter_id`) USING BTREE,
  KEY `idx_agent_id` (`agent_id`) USING BTREE,
  KEY `idx_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户表';

-- ----------------------------
-- Records of think_member
-- ----------------------------
BEGIN;
INSERT INTO `think_member` (`id`, `username`, `email`, `password`, `status`, `inviter_id`, `agent_id`, `is_root`, `inviter_path`, `invite_code`, `point_card_self`, `point_card_gift`, `account_balance`, `available_balance`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, '1@1.com', '1@1.com', '626236e665ba2d08eba8064692798f7d', 1, 0, 1, 1, '', '16269445', 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0, 1769884581, 0, 1769884581, 1);
INSERT INTO `think_member` (`id`, `username`, `email`, `password`, `status`, `inviter_id`, `agent_id`, `is_root`, `inviter_path`, `invite_code`, `point_card_self`, `point_card_gift`, `account_balance`, `available_balance`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, '1@1.con', '1@1.con', 'df03227c4629acf52059ee7055c48fe1', 1, 0, 1, 0, '', '93985874', 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0, 1769884993, 0, 1769884993, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_member_loss_limit
-- ----------------------------
DROP TABLE IF EXISTS `think_member_loss_limit`;
CREATE TABLE `think_member_loss_limit` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `daily_loss_limit` decimal(20,2) NOT NULL DEFAULT '500.00' COMMENT '每日亏损限额(USDT)',
  `daily_loss_ratio` decimal(5,4) NOT NULL DEFAULT '0.1000' COMMENT '每日亏损比例',
  `warning_threshold` decimal(5,4) NOT NULL DEFAULT '0.7000' COMMENT '预警阈值',
  `auto_stop_trading` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '自动停止交易',
  `reset_time` varchar(10) NOT NULL DEFAULT '00:00:00' COMMENT '重置时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_member_id` (`member_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='会员亏损限额配置';

-- ----------------------------
-- Records of think_member_loss_limit
-- ----------------------------
BEGIN;
INSERT INTO `think_member_loss_limit` (`id`, `member_id`, `daily_loss_limit`, `daily_loss_ratio`, `warning_threshold`, `auto_stop_trading`, `reset_time`, `create_time`, `update_time`, `mark`) VALUES (1, 1, 500.00, 0.1000, 0.7000, 1, '00:00:00', 1769674548, 1769679222, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_member_server
-- ----------------------------
DROP TABLE IF EXISTS `think_member_server`;
CREATE TABLE `think_member_server` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL,
  `server_id` int unsigned NOT NULL,
  `exchange_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `allocated_by` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'auto',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_member_exchange` (`member_id`,`exchange_type`) USING BTREE,
  KEY `idx_server_id` (`server_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Records of think_member_server
-- ----------------------------
BEGIN;
INSERT INTO `think_member_server` (`id`, `member_id`, `server_id`, `exchange_type`, `allocated_by`, `remark`, `create_time`, `update_time`) VALUES (1, 1, 1, 'binance', 'auto', NULL, 1769961494, 1769961494);
COMMIT;

-- ----------------------------
-- Table structure for think_member_statistics
-- ----------------------------
DROP TABLE IF EXISTS `think_member_statistics`;
CREATE TABLE `think_member_statistics` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `stat_date` date NOT NULL COMMENT '统计日期',
  `total_profit` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '总收益',
  `total_volume` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT '总成交额',
  `win_rate` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '胜率(%)',
  `max_drawdown` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '最大回撤(%)',
  `trade_count` int unsigned NOT NULL DEFAULT '0' COMMENT '交易次数',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_member_date` (`member_id`,`stat_date`) USING BTREE,
  KEY `idx_stat_date` (`stat_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='会员统计表';

-- ----------------------------
-- Records of think_member_statistics
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_member_symbol_limit
-- ----------------------------
DROP TABLE IF EXISTS `think_member_symbol_limit`;
CREATE TABLE `think_member_symbol_limit` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '用户ID',
  `symbol` varchar(30) NOT NULL DEFAULT '' COMMENT '交易对',
  `limit_type` varchar(20) NOT NULL DEFAULT 'blacklist' COMMENT '限制类型: whitelist, blacklist',
  `max_leverage` int DEFAULT '0' COMMENT '最大杠杆(0=使用全局)',
  `max_position_value` decimal(20,2) DEFAULT '0.00' COMMENT '最大持仓(0=使用全局)',
  `reason` varchar(200) DEFAULT '' COMMENT '原因',
  `expire_time` int unsigned DEFAULT '0' COMMENT '过期时间(0=永久)',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态:1启用 0禁用',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_type` (`limit_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户交易对限制表';

-- ----------------------------
-- Records of think_member_symbol_limit
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_member_wallet
-- ----------------------------
DROP TABLE IF EXISTS `think_member_wallet`;
CREATE TABLE `think_member_wallet` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '用户ID',
  `balance` decimal(20,2) DEFAULT '0.00' COMMENT '可用余额',
  `frozen_balance` decimal(20,2) DEFAULT '0.00' COMMENT '冻结余额',
  `total_income` decimal(20,2) DEFAULT '0.00' COMMENT '累计收入',
  `total_withdraw` decimal(20,2) DEFAULT '0.00' COMMENT '累计提现',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态:1正常 0冻结',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_member` (`member_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户钱包表';

-- ----------------------------
-- Records of think_member_wallet
-- ----------------------------
BEGIN;
INSERT INTO `think_member_wallet` (`id`, `member_id`, `balance`, `frozen_balance`, `total_income`, `total_withdraw`, `status`, `create_time`, `update_time`, `mark`) VALUES (1, 1, 0.00, 0.00, 0.00, 0.00, 1, 1769674576, 1769674576, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_menu
-- ----------------------------
DROP TABLE IF EXISTS `think_menu`;
CREATE TABLE `think_menu` (
  `id` int unsigned NOT NULL DEFAULT '0' COMMENT '主键ID',
  `pid` int unsigned NOT NULL DEFAULT '0' COMMENT '父级ID',
  `title` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '菜单标题',
  `icon` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '图标',
  `path` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '菜单路径',
  `component` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '菜单组件',
  `target` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '打开方式：0组件 1内链 2外链',
  `permission` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '权限标识',
  `type` tinyint(1) NOT NULL DEFAULT '0' COMMENT '类型：0菜单 1节点',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态：1正常 2禁用',
  `hide` tinyint unsigned DEFAULT '0' COMMENT '是否可见：0显示 1隐藏',
  `note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `sort` smallint DEFAULT '125' COMMENT '显示顺序',
  `create_user` int NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint(1) NOT NULL DEFAULT '1' COMMENT '有效标识'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Records of think_menu
-- ----------------------------
BEGIN;
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, 0, '仪表盘', 'el-icon-s-home', '/dashboard', '', '_self', '', 0, 1, 0, NULL, 1, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, 0, '交易中心', 'el-icon-s-order', '/trade', '', '_self', '', 0, 1, 0, NULL, 2, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (3, 0, '会员管理', 'el-icon-user-solid', '/member', '', '_self', '', 0, 1, 0, NULL, 3, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, 0, '财务管理', 'el-icon-wallet', '/finance', '', '_self', '', 0, 1, 0, NULL, 4, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (5, 0, '基础设施', 'el-icon-s-platform', '/infrastructure', '', '_self', '', 0, 1, 0, NULL, 5, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (6, 0, '系统管理', 'el-icon-s-tools', '/system', '', '_self', '', 0, 1, 0, NULL, 6, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (7, 0, '数据管理', 'el-icon-s-data', '/data', '', '_self', '', 0, 1, 0, NULL, 7, 0, 1769521315, 0, 0, 0);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (8, 0, '消息管理', 'el-icon-message-solid', '/message', '', '_self', '', 0, 1, 0, NULL, 8, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (101, 1, '工作台', 'el-icon-s-home', '/dashboard/workplace', '/dashboard/workplace', '_self', 'sys:dashboard:workplace', 0, 1, 0, NULL, 1, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (102, 1, '数据分析', 'el-icon-data-analysis', '/dashboard/analysis', '/dashboard/analysis', '_self', 'sys:dashboard:analysis', 0, 1, 0, NULL, 2, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (103, 1, '监控页', 'el-icon-monitor', '/dashboard/monitor', '/dashboard/monitor', '_self', 'sys:dashboard:monitor', 0, 1, 0, NULL, 3, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (104, 1, '交易大屏', 'el-icon-data-board', '/dashboard/trading-screen', '/dashboard/trading-screen/index', '_self', 'sys:dashboard:tradingscreen', 0, 1, 0, NULL, 4, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (201, 2, '订单管理', 'el-icon-s-order', '/trade/order', '/trade/order/index', '_self', 'sys:order:view', 0, 1, 0, NULL, 1, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (202, 2, '持仓管理', 'el-icon-coin', '/trade/position', '/trade/position/index', '_self', 'sys:position:view', 0, 1, 0, NULL, 2, 0, 1769521315, 0, 0, 0);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (203, 2, '历史订单', 'el-icon-time', '/trade/order-history', '/trade/order-history/index', '_self', 'sys:orderhistory:view', 0, 1, 0, NULL, 3, 0, 1769521315, 0, 0, 0);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (204, 2, '订单同步', 'el-icon-refresh', '/trade/order-sync', '/trade/order-sync/index', '_self', 'sys:ordersync:view', 0, 1, 0, NULL, 4, 0, 1769521315, 0, 0, 0);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (210, 2, '跟单管理', 'el-icon-connection', '/trade/copy-trade', '/trade/copy-trade/index', '_self', 'sys:copytrade:view', 0, 1, 0, NULL, 10, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (211, 2, '跟单关系', 'el-icon-share', '/trade/follow-relation', '/trade/follow-relation/index', '_self', 'sys:followrelation:view', 0, 1, 0, NULL, 11, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (212, 2, '跟单执行', 'el-icon-video-play', '/trade/follow-execution', '/trade/follow-execution/index', '_self', 'sys:followexecution:view', 0, 1, 0, NULL, 12, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (213, 2, '跟单记录', 'el-icon-document', '/trade/follow-log', '/trade/follow-log/index', '_self', 'sys:followlog:view', 0, 1, 0, NULL, 13, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (214, 2, '跟单策略', 'el-icon-set-up', '/trade/follow-strategy', '/trade/follow-strategy/index', '_self', 'sys:followstrategy:view', 0, 1, 0, NULL, 14, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (220, 2, 'Leader管理', 'el-icon-data-line', '/trade/leader-dashboard', '/trade/leader-dashboard/index', '_self', 'sys:leaderdashboard:view', 0, 1, 0, NULL, 20, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (221, 2, '带单员绩效', 'el-icon-trophy', '/trade/leader-performance', '/trade/leader-performance/index', '_self', 'sys:leaderperformance:view', 0, 1, 0, NULL, 21, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (222, 2, '带单员标签', 'el-icon-price-tag', '/trade/leader-tag', '/trade/leader-tag/index', '_self', 'sys:leadertag:view', 0, 1, 0, NULL, 22, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (230, 2, '策略中心', 'el-icon-cpu', '/trade/strategy', '/trade/strategy/index', '_self', 'sys:strategy:view', 0, 1, 0, NULL, 30, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (231, 2, '策略实例', 'el-icon-film', '/trade/strategy-instance', '/trade/strategy-instance/index', '_self', 'sys:strategyinstance:view', 0, 1, 0, NULL, 31, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (232, 2, '策略回测', 'el-icon-odometer', '/trade/backtest', '/trade/backtest/index', '_self', 'sys:backtest:view', 0, 1, 0, NULL, 32, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (233, 2, '策略监控', 'el-icon-view', '/trade/strategy-monitor', '/trade/strategy-monitor/index', '_self', 'sys:strategymonitor:view', 0, 1, 0, NULL, 33, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (240, 2, '风控中心', 'el-icon-warning', '/trade/risk-control', '/trade/risk-control/index', '_self', 'sys:riskcontrol:view', 0, 1, 0, NULL, 40, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (241, 2, '风控规则', 'el-icon-s-flag', '/trade/risk-rule', '/trade/risk-rule/index', '_self', 'sys:riskrule:view', 0, 1, 0, NULL, 41, 0, 1769521315, 0, 0, 0);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (242, 2, '风控配置', 'el-icon-setting', '/trade/risk-config', '/trade/risk/config', '_self', 'sys:riskconfig:view', 0, 1, 0, NULL, 42, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (243, 2, '每日亏损限额', 'el-icon-minus', '/trade/daily-loss-limit', '/trade/daily-loss-limit/index', '_self', 'sys:dailylosslimit:view', 0, 1, 0, NULL, 43, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (250, 2, '信号中心', 'el-icon-s-promotion', '/trade/signal', '/trade/signal/index', '_self', 'sys:signal:view', 0, 1, 0, NULL, 50, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (251, 2, '信号分析', 'el-icon-pie-chart', '/trade/signal-analysis', '@/views/trade/signal-analysis/index', '_self', 'sys:signalanalysis:view', 0, 1, 0, NULL, 51, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (252, 2, '信号广播', 'el-icon-s-comment', '/trade/signal-broadcast', '/trade/signal-broadcast/index', '_self', 'sys:signalbroadcast:view', 0, 1, 0, NULL, 52, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (253, 2, '价格预警', 'el-icon-bell', '/trade/price-alert', '/trade/price-alert/index', '_self', 'sys:pricealert:view', 0, 1, 0, NULL, 53, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (254, 2, '持仓预警', 'el-icon-warning-outline', '/trade/position-alert', '/trade/position-alert/index', '_self', 'sys:positionalert:view', 0, 1, 0, NULL, 54, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (260, 2, '收益分析', 'el-icon-s-marketing', '/trade/profit-analysis', '/trade/profit-analysis/index', '_self', 'sys:profitanalysis:view', 0, 1, 0, NULL, 60, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (261, 2, '收益对比', 'el-icon-s-grid', '/trade/profit-compare', '/trade/profit-compare/index', '_self', 'sys:profitcompare:view', 0, 1, 0, NULL, 61, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (262, 2, '订单分析', 'el-icon-document-checked', '/trade/order-analysis', '/trade/order-analysis/index', '_self', 'sys:orderanalysis:view', 0, 1, 0, NULL, 62, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (263, 2, '交易分析', 'el-icon-s-finance', '/trade/account-stats', '/trade/account-stats/index', '_self', 'sys:accountstats:view', 0, 1, 0, NULL, 63, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (270, 2, '交易日历', 'el-icon-date', '/trade/calendar', '/trade/calendar/index', '_self', 'sys:calendar:view', 0, 1, 0, NULL, 70, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (271, 2, '交易对管理', 'el-icon-s-cooperation', '/trade/symbol-manage', '/trade/symbol-manage/index', '_self', 'sys:symbolmanage:view', 0, 1, 0, NULL, 71, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (272, 2, '多账户资产', 'el-icon-bank-card', '/trade/multi-account', '/trade/multi-account/index', '_self', 'sys:multiaccount:view', 0, 1, 0, NULL, 72, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (273, 2, '批量操作', 'el-icon-files', '/trade/batch-operation', '/trade/batch-operation/index', '_self', 'sys:batchoperation:view', 0, 1, 0, NULL, 73, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (274, 2, '智能推荐', 'el-icon-magic-stick', '/trade/ai-recommend', '/trade/ai-recommend/index', '_self', 'sys:airecommend:view', 0, 1, 0, NULL, 74, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (275, 2, '交易所管理', 'el-icon-office-building', '/trade/exchange', '/trade/exchange/index', '_self', 'sys:exchange:view', 0, 1, 0, NULL, 75, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (276, 2, '交易日志', 'el-icon-tickets', '/trade/log', '/trade/log/index', '_self', 'sys:tradelog:view', 0, 1, 0, NULL, 76, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (301, 3, '会员中心', 'el-icon-user', '/member/member', '/member/member/index', '_self', 'sys:member:view', 0, 1, 0, NULL, 1, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (303, 3, '盈利仪表盘', 'el-icon-data-line', '/member/profit-dashboard', '/member/profit-dashboard/index', '_self', 'sys:profitdashboard:view', 0, 1, 0, NULL, 3, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (304, 3, '点卡扣费记录', 'el-icon-document', '/member/point-card-deduction', '/member/point-card-deduction/index', '_self', 'sys:pointcarddeduction:view', 0, 1, 0, NULL, 4, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (305, 3, '低余额用户', 'el-icon-warning', '/member/low-balance', '/member/low-balance/index', '_self', 'sys:lowbalance:view', 0, 1, 0, NULL, 5, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (306, 3, '会员活跃度', 'el-icon-s-custom', '/member/activity', '/member/activity/index', '_self', 'sys:memberactivity:view', 0, 1, 0, NULL, 6, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (307, 3, '服务器分配', 'el-icon-s-platform', '/member/server-allocate', '/member/server-allocate/index', '_self', 'sys:serverallocate:view', 0, 1, 0, NULL, 7, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (308, 3, '提币地址', 'el-icon-map-location', '/member/address', '/member/address/index', '_self', 'sys:memberaddress:view', 0, 1, 0, NULL, 8, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (310, 3, '代理商管理', 'el-icon-s-custom', '/member/agent', '/member/agent/index', '_self', 'sys:agent:view', 0, 1, 0, NULL, 10, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (311, 3, '代理商分成', 'el-icon-money', '/member/agent/earnings-dashboard', '/member/agent/earnings-dashboard', '_self', 'sys:agentearnings:view', 0, 1, 0, NULL, 11, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (401, 4, '结算中心', 'el-icon-s-finance', '/finance/settlement-center', '/finance/settlement-center/index', '_self', 'sys:settlement:view', 0, 1, 0, NULL, 1, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (501, 5, '子服务器管理', 'el-icon-s-platform', '/infrastructure/lightweight-server', '/infrastructure/lightweight-server/index', '_self', 'sys:lightweightserver:view', 0, 1, 0, NULL, 1, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (502, 5, 'IP资源池', 'el-icon-s-grid', '/infrastructure/ip-inventory', '/infrastructure/ip-inventory/index', '_self', 'sys:ipinventory:view', 0, 1, 0, NULL, 2, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (503, 5, '平台地址', 'el-icon-location-information', '/infrastructure/platform-address', '/infrastructure/platform-address/index', '_self', 'sys:platformaddress:view', 0, 1, 0, NULL, 3, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (601, 6, '用户管理', 'el-icon-user', '/system/user', '/system/user/index', '_self', 'sys:user:view', 0, 1, 0, NULL, 1, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (602, 6, '角色管理', 'el-icon-s-check', '/system/role', '/system/role/index', '_self', 'sys:role:view', 0, 1, 0, NULL, 2, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (603, 6, '菜单管理', 'el-icon-menu', '/system/menu', '/system/menu/index', '_self', 'sys:menu:view', 0, 1, 0, NULL, 3, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (604, 6, '系统配置', 'el-icon-setting', '/system/config', '/system/config/index', '_self', 'sys:config:view', 0, 1, 0, NULL, 4, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (605, 6, '定时任务', 'el-icon-alarm-clock', '/system/cronjob', '/system/cronjob/index', '_self', 'sys:cronjob:view', 0, 1, 0, NULL, 5, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (607, 6, '日志中心', 'el-icon-document-copy', '/system/operlog', '/system/operlog/index', '_self', 'sys:operlog:view', 0, 1, 0, NULL, 7, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (608, 6, '登录日志', 'el-icon-s-custom', '/system/loginlog', '/system/loginlog/index', '_self', 'sys:loginlog:view', 0, 1, 0, NULL, 8, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (609, 6, '通知日志', 'el-icon-message', '/system/notify-log', '/system/notify-log/index', '_self', 'sys:notifylog:view', 0, 1, 0, NULL, 9, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (610, 6, '通知模板', 'el-icon-document', '/system/notify-template', '/system/notify-template/index', '_self', 'sys:notifytemplate:view', 0, 1, 0, NULL, 10, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (611, 6, '消息中心', 'el-icon-chat-dot-round', '/system/message-center', '/system/message-center/index', '_self', 'sys:messagecenter:view', 0, 1, 0, NULL, 11, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (612, 6, 'Telegram配置', 'el-icon-chat-line-round', '/system/telegram', '/system/telegram/index', '_self', 'sys:telegram:view', 0, 1, 0, NULL, 12, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (613, 6, '性能监控', 'el-icon-odometer', '/system/performance-monitor', '/system/monitor/performance', '_self', 'sys:performance:view', 0, 1, 0, NULL, 13, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (614, 6, '告警规则', 'el-icon-bell', '/system/alert-rule', '/system/alert-rule/index', '_self', 'sys:alertrule:view', 0, 1, 0, NULL, 14, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (615, 6, '系统健康', 'el-icon-first-aid-kit', '/system/health', '/system/health/index', '_self', 'sys:health:view', 0, 1, 0, NULL, 15, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (616, 6, '紧急操作', 'el-icon-warning', '/system/emergency', '/system/emergency/index', '_self', 'sys:emergency:view', 0, 1, 0, NULL, 16, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (617, 6, '客户端配置', 'el-icon-mobile-phone', '/system/client-config', '/system/client-config/index', '_self', 'sys:clientconfig:view', 0, 1, 0, NULL, 17, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (701, 7, '数据配置', 'el-icon-s-data', '/data/config', '/data/config/index', '_self', 'sys:dataconfig:view', 0, 1, 0, NULL, 1, 0, 1769521315, 0, 0, 0);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (702, 7, '数据字典', 'el-icon-notebook-2', '/data/dictionary', '/data/dictionary/index', '_self', 'sys:dictionary:view', 0, 1, 0, NULL, 2, 0, 1769521315, 0, 0, 0);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (801, 8, '公告管理', 'el-icon-s-comment', '/message/notice', '/message/notice/index', '_self', 'sys:notice:view', 0, 1, 0, NULL, 1, 0, 1769521315, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (900, 2, '预警中心', 'el-icon-warning-outline', '/trade/alert-center', '/trade/alert-center/index', '_self', 'sys:alertcenter:view', 0, 1, 0, NULL, 55, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (901, 2, '指标预警', 'el-icon-data-line', '/trade/indicator-alert', '/trade/indicator-alert/index', '_self', 'sys:indicatoralert:view', 0, 1, 0, NULL, 56, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (902, 2, '爆仓预警', 'el-icon-warning', '/trade/liquidation-alert', '/trade/liquidation-alert/index', '_self', 'sys:liquidationalert:view', 0, 1, 0, NULL, 57, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (910, 2, '持仓管理', 'el-icon-s-grid', '/trade/position-manage', '/trade/position-manage/index', '_self', 'sys:positionmanage:view', 0, 1, 0, NULL, 2, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (911, 2, '持仓变化历史', 'el-icon-time', '/trade/position-change-history', '/trade/position-change-history/index', '_self', 'sys:positionchangehistory:view', 0, 1, 0, NULL, 5, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (912, 2, '持仓快照', 'el-icon-camera', '/trade/position-snapshot', '/trade/position-snapshot/index', '_self', 'sys:positionsnapshot:view', 0, 1, 0, NULL, 6, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (920, 2, '跟单订单日志', 'el-icon-document-copy', '/trade/follow-order-log', '/trade/follow-order-log/index', '_self', 'sys:followorderlog:view', 0, 1, 0, NULL, 15, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (921, 2, '部分跟单', 'el-icon-sort', '/trade/follow-partial', '/trade/follow-partial/index', '_self', 'sys:followpartial:view', 0, 1, 0, NULL, 16, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (922, 2, '拆单跟单', 'el-icon-s-operation', '/trade/follow-split', '/trade/follow-split/index', '_self', 'sys:followsplit:view', 0, 1, 0, NULL, 17, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (930, 2, '策略组合', 'el-icon-connection', '/trade/strategy-combo', '/trade/strategy-combo/index', '_self', 'sys:strategycombo:view', 0, 1, 0, NULL, 34, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (931, 2, '策略对比', 'el-icon-s-data', '/trade/strategy-compare', '/trade/strategy-compare/index', '_self', 'sys:strategycompare:view', 0, 1, 0, NULL, 35, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (932, 2, '策略优化器', 'el-icon-magic-stick', '/trade/strategy-optimizer', '/trade/strategy-optimizer/index', '_self', 'sys:strategyoptimizer:view', 0, 1, 0, NULL, 36, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (933, 2, '策略绩效', 'el-icon-trophy', '/trade/strategy-performance', '/trade/strategy-performance/index', '_self', 'sys:strategyperformance:view', 0, 1, 0, NULL, 37, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (940, 2, '权益分析', 'el-icon-s-finance', '/trade/equity-analysis', '/trade/equity-analysis/index', '_self', 'sys:equityanalysis:view', 0, 1, 0, NULL, 64, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (941, 2, '盈亏报表', 'el-icon-document', '/trade/pnl-report', '/trade/pnl-report/index', '_self', 'sys:pnlreport:view', 0, 1, 0, NULL, 65, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (942, 2, '报表导出', 'el-icon-download', '/trade/report-export', '/trade/report-export/index', '_self', 'sys:reportexport:view', 0, 1, 0, NULL, 66, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (943, 2, '滑点分析', 'el-icon-sort', '/trade/slippage-analysis', '/trade/slippage-analysis/index', '_self', 'sys:slippageanalysis:view', 0, 1, 0, NULL, 67, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (944, 2, '统计', 'el-icon-data-analysis', '/trade/statistics', '/trade/statistics/index', '_self', 'sys:statistics:view', 0, 1, 0, NULL, 68, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (950, 2, '风险动作模板', 'el-icon-document-copy', '/trade/risk-action-template', '/trade/risk-action-template/index', '_self', 'sys:riskactiontemplate:view', 0, 1, 0, NULL, 44, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (951, 2, '风险套餐', 'el-icon-box', '/trade/risk-package', '/trade/risk-package/index', '_self', 'sys:riskpackage:view', 0, 1, 0, NULL, 45, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (960, 2, '资金费率', 'el-icon-money', '/trade/funding-rate', '/trade/funding-rate/index', '_self', 'sys:fundingrate:view', 0, 1, 0, NULL, 77, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (961, 2, '对冲管理', 'el-icon-sort', '/trade/hedge-manage', '/trade/hedge-manage/index', '_self', 'sys:hedgemanage:view', 0, 1, 0, NULL, 78, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (962, 2, '智能止损', 'el-icon-remove-outline', '/trade/smart-stop', '/trade/smart-stop/index', '_self', 'sys:smartstop:view', 0, 1, 0, NULL, 79, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (963, 2, '追踪止损', 'el-icon-bottom', '/trade/trailing-stop', '/trade/trailing-stop/index', '_self', 'sys:trailingstop:view', 0, 1, 0, NULL, 80, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (964, 2, '交易回放', 'el-icon-video-play', '/trade/trade-replay', '/trade/trade-replay/index', '_self', 'sys:tradereplay:view', 0, 1, 0, NULL, 81, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (965, 2, 'API监控', 'el-icon-monitor', '/trade/api-monitor', '/trade/api-monitor/index', '_self', 'sys:apimonitor:view', 0, 1, 0, NULL, 82, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (966, 2, '操作历史', 'el-icon-time', '/trade/operation-history', '/trade/operation-history/index', '_self', 'sys:operationhistory:view', 0, 1, 0, NULL, 83, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (970, 2, '行情监控', 'el-icon-data-line', '/trade/market', '/trade/market/index', '_self', 'sys:market:view', 0, 1, 0, NULL, 84, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (971, 2, '策略市场', 'el-icon-shopping-cart-full', '/trade/marketplace', '/trade/marketplace/index', '_self', 'sys:marketplace:view', 0, 1, 0, NULL, 85, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (973, 2, '交易仪表盘', 'el-icon-odometer', '/trade/dashboard', '/trade/dashboard/index', '_self', 'sys:tradedashboard:view', 0, 1, 0, NULL, 87, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (974, 2, '交易监控', 'el-icon-view', '/trade/monitor', '/trade/monitor/index', '_self', 'sys:trademonitor:view', 0, 1, 0, NULL, 88, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (975, 2, '风险概览', 'el-icon-warning', '/trade/risk', '/trade/risk/index', '_self', 'sys:risk:view', 0, 1, 0, NULL, 46, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (976, 2, '交易日记', 'el-icon-notebook-2', '/trade/journal', '/trade/journal/index', '_self', 'sys:journal:view', 0, 1, 0, NULL, 89, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (977, 2, '定时任务', 'el-icon-alarm-clock', '/trade/cron', '/trade/cron/index', '_self', 'sys:tradecron:view', 0, 1, 0, NULL, 90, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (980, 6, '系统监控', 'el-icon-monitor', '/system/monitor', '/system/monitor/index', '_self', 'sys:systemmonitor:view', 0, 1, 0, NULL, 18, 0, 1769522295, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (990, 2, '财务账本', 'el-icon-wallet', '/trade/finance', '/trade/finance/index', '_self', 'sys:finance:view', 0, 1, 0, NULL, 91, 0, 1769522567, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (991, 2, '模拟交易', 'el-icon-coin', '/trade/paper-trading', '/trade/paper-trading/index', '_self', 'sys:papertrading:view', 0, 1, 0, NULL, 92, 0, 1769522567, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1000, 990, '导出', '', '', '', '_self', 'sys:finance:export', 1, 1, 0, NULL, 1, 0, 1769522567, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1001, 990, '生成结算单', '', '', '', '_self', 'sys:finance:generatesettlement', 1, 1, 0, NULL, 2, 0, 1769522567, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1002, 991, '下单', '', '', '', '_self', 'sys:papertrading:placeorder', 1, 1, 0, NULL, 1, 0, 1769522567, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1003, 991, '重置账户', '', '', '', '_self', 'sys:papertrading:reset', 1, 1, 0, NULL, 2, 0, 1769522567, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1004, 242, '保存配置', '', '', '', '_self', 'sys:riskconfig:save', 1, 1, 0, NULL, 1, 0, 1769522567, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1005, 242, '重置配置', '', '', '', '_self', 'sys:riskconfig:reset', 1, 1, 0, NULL, 2, 0, 1769522567, 0, 0, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1006, 2, '信号风控', 'el-icon-warning-outline', '/trade/signal-risk', '@/views/trade/signal-risk/index', '_self', '', 0, 1, 0, NULL, 22, 0, 1769821546, 0, 1769821546, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1007, 2, '信号仪表板', 'el-icon-data-board', '/trade/signal-dashboard', '@/views/trade/signal-dashboard/index', '_self', '', 0, 1, 0, NULL, 23, 0, 1769821546, 0, 1769821546, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1008, 2, '信号模板', 'el-icon-document', '/trade/signal-template', '@/views/trade/signal-template/index', '_self', '', 0, 1, 0, NULL, 24, 0, 1769821546, 0, 1769821546, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1009, 2, '信号通知', 'el-icon-bell', '/trade/signal-notify', '@/views/trade/signal-notify/index', '_self', '', 0, 1, 0, NULL, 26, 0, 1769821546, 0, 1769821546, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1010, 2, '策略推荐', 'el-icon-magic-stick', '/trade/strategy-recommend', '@/views/trade/strategy-recommend/index', '_self', '', 0, 1, 0, NULL, 27, 0, 1769821546, 0, 1769821546, 1);
INSERT INTO `think_menu` (`id`, `pid`, `title`, `icon`, `path`, `component`, `target`, `permission`, `type`, `status`, `hide`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1011, 2, '策略账户绑定', 'el-icon-connection', '/trade/strategy-account', NULL, NULL, NULL, 0, 1, 0, NULL, 234, 0, 1770102931, 0, 1770102931, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_message
-- ----------------------------
DROP TABLE IF EXISTS `think_message`;
CREATE TABLE `think_message` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL DEFAULT '' COMMENT '标题',
  `content` text COMMENT '内容',
  `sender_id` int unsigned DEFAULT '0' COMMENT '发送者ID(0=系统)',
  `receiver_id` int unsigned NOT NULL DEFAULT '0' COMMENT '接收者ID(0=全部用户)',
  `msg_type` varchar(30) DEFAULT 'system' COMMENT '类型: system系统 trade交易 alert预警 promo推广',
  `related_id` int unsigned DEFAULT '0' COMMENT '关联ID',
  `related_type` varchar(30) DEFAULT '' COMMENT '关联类型',
  `is_read` tinyint DEFAULT '0' COMMENT '是否已读',
  `read_time` int unsigned DEFAULT '0' COMMENT '阅读时间',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_receiver` (`receiver_id`),
  KEY `idx_type` (`msg_type`),
  KEY `idx_read` (`is_read`),
  KEY `idx_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='站内信表';

-- ----------------------------
-- Records of think_message
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_message_template
-- ----------------------------
DROP TABLE IF EXISTS `think_message_template`;
CREATE TABLE `think_message_template` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `code` varchar(50) NOT NULL DEFAULT '' COMMENT '模板编码',
  `name` varchar(100) NOT NULL DEFAULT '' COMMENT '模板名称',
  `title_template` varchar(200) DEFAULT '' COMMENT '标题模板',
  `content_template` text COMMENT '内容模板',
  `msg_type` varchar(30) DEFAULT 'system' COMMENT '消息类型',
  `variables` varchar(500) DEFAULT '' COMMENT '变量说明(JSON)',
  `enable_site` tinyint DEFAULT '1' COMMENT '站内信',
  `enable_email` tinyint DEFAULT '0' COMMENT '邮件',
  `enable_sms` tinyint DEFAULT '0' COMMENT '短信',
  `enable_push` tinyint DEFAULT '0' COMMENT '推送',
  `status` tinyint DEFAULT '1' COMMENT '状态',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='消息模板表';

-- ----------------------------
-- Records of think_message_template
-- ----------------------------
BEGIN;
INSERT INTO `think_message_template` (`id`, `code`, `name`, `title_template`, `content_template`, `msg_type`, `variables`, `enable_site`, `enable_email`, `enable_sms`, `enable_push`, `status`, `create_time`, `update_time`, `mark`) VALUES (1, 'trade_open', '开仓通知', '开仓成功通知', '您已成功开仓 {symbol}，方向: {side}，数量: {qty}，价格: {price}', 'trade', '{\"symbol\":\"交易对\",\"side\":\"方向\",\"qty\":\"数量\",\"price\":\"价格\"}', 1, 0, 0, 0, 1, 1769499672, 1769499672, 0);
INSERT INTO `think_message_template` (`id`, `code`, `name`, `title_template`, `content_template`, `msg_type`, `variables`, `enable_site`, `enable_email`, `enable_sms`, `enable_push`, `status`, `create_time`, `update_time`, `mark`) VALUES (2, 'trade_close', '平仓通知', '平仓成功通知', '您的 {symbol} 仓位已平仓，盈亏: {profit} USDT', 'trade', '{\"symbol\":\"交易对\",\"profit\":\"盈亏\"}', 1, 0, 0, 0, 1, 1769499672, 1769499672, 1);
INSERT INTO `think_message_template` (`id`, `code`, `name`, `title_template`, `content_template`, `msg_type`, `variables`, `enable_site`, `enable_email`, `enable_sms`, `enable_push`, `status`, `create_time`, `update_time`, `mark`) VALUES (3, 'price_alert', '价格预警', '{symbol} 价格预警', '{symbol} 当前价格 {price}，触发您设置的预警条件', 'alert', '{\"symbol\":\"交易对\",\"price\":\"价格\"}', 1, 0, 0, 0, 1, 1769499672, 1769499672, 1);
INSERT INTO `think_message_template` (`id`, `code`, `name`, `title_template`, `content_template`, `msg_type`, `variables`, `enable_site`, `enable_email`, `enable_sms`, `enable_push`, `status`, `create_time`, `update_time`, `mark`) VALUES (4, 'withdraw_success', '提现成功', '提现到账通知', '您申请的 {amount} USDT 提现已到账，请查收', 'system', '{\"amount\":\"金额\"}', 1, 0, 0, 0, 1, 1769499672, 1769499672, 1);
INSERT INTO `think_message_template` (`id`, `code`, `name`, `title_template`, `content_template`, `msg_type`, `variables`, `enable_site`, `enable_email`, `enable_sms`, `enable_push`, `status`, `create_time`, `update_time`, `mark`) VALUES (5, 'follow_profit', '跟单收益', '跟单收益通知', '您跟随 {leader} 的交易已平仓，收益: {profit} USDT', 'trade', '{\"leader\":\"带单员\",\"profit\":\"收益\"}', 1, 0, 0, 0, 1, 1769499672, 1769499672, 1);
INSERT INTO `think_message_template` (`id`, `code`, `name`, `title_template`, `content_template`, `msg_type`, `variables`, `enable_site`, `enable_email`, `enable_sms`, `enable_push`, `status`, `create_time`, `update_time`, `mark`) VALUES (6, 'commission_income', '分成收入', '分成收入通知', '您获得跟单分成 {amount} USDT，来自跟随者 {follower}', 'system', '{\"amount\":\"金额\",\"follower\":\"跟随者\"}', 1, 0, 0, 0, 1, 1769499672, 1769499672, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_notice
-- ----------------------------
DROP TABLE IF EXISTS `think_notice`;
CREATE TABLE `think_notice` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '数据编号',
  `title` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '通知标题',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '通知内容',
  `source` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '通知来源：1云平台',
  `is_top` tinyint unsigned NOT NULL DEFAULT '2' COMMENT '是否置顶：1已置顶 2未置顶',
  `browse` int unsigned NOT NULL DEFAULT '0' COMMENT '阅读量',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '发布状态：1草稿箱 2立即发布 3定时发布',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '添加时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `index_title` (`title`) USING BTREE,
  KEY `idx_mark` (`mark`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_create_time` (`create_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='通知公告表';

-- ----------------------------
-- Records of think_notice
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_notify_log
-- ----------------------------
DROP TABLE IF EXISTS `think_notify_log`;
CREATE TABLE `think_notify_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `channel` varchar(50) DEFAULT 'telegram' COMMENT '渠道',
  `chat_id` varchar(100) DEFAULT '' COMMENT 'Chat ID',
  `message` text COMMENT '消息内容',
  `status` tinyint DEFAULT '1' COMMENT '状态 1成功 0失败',
  `error` varchar(500) DEFAULT '' COMMENT '错误信息',
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint DEFAULT '1' COMMENT '标记',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='通知日志表';

-- ----------------------------
-- Records of think_notify_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_order_batch_relation
-- ----------------------------
DROP TABLE IF EXISTS `think_order_batch_relation`;
CREATE TABLE `think_order_batch_relation` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `batch_id` int unsigned NOT NULL DEFAULT '0' COMMENT '批次ID',
  `order_id` int unsigned NOT NULL DEFAULT '0' COMMENT '订单ID',
  `order_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '订单编号',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1待执行 2执行中 3成功 4失败',
  `error_msg` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '错误信息',
  `execute_time` int unsigned NOT NULL DEFAULT '0' COMMENT '执行时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_batch_id` (`batch_id`) USING BTREE,
  KEY `idx_order_id` (`order_id`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='订单批次关联表';

-- ----------------------------
-- Records of think_order_batch_relation
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_paper_account
-- ----------------------------
DROP TABLE IF EXISTS `think_paper_account`;
CREATE TABLE `think_paper_account` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL,
  `balance` decimal(20,4) DEFAULT '10000.0000',
  `available` decimal(20,4) DEFAULT '10000.0000',
  `initial_balance` decimal(20,4) DEFAULT '10000.0000',
  `total_pnl` decimal(20,4) DEFAULT '0.0000',
  `total_trades` int DEFAULT '0',
  `win_trades` int DEFAULT '0',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模拟盘账户表';

-- ----------------------------
-- Records of think_paper_account
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_paper_order
-- ----------------------------
DROP TABLE IF EXISTS `think_paper_order`;
CREATE TABLE `think_paper_order` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `account_id` int unsigned NOT NULL,
  `member_id` int unsigned DEFAULT '0',
  `symbol` varchar(50) NOT NULL,
  `side` tinyint DEFAULT '1',
  `position_side` varchar(10) DEFAULT 'LONG',
  `quantity` decimal(20,8) DEFAULT '0.00000000',
  `price` decimal(20,8) DEFAULT '0.00000000',
  `leverage` int DEFAULT '1',
  `margin` decimal(20,4) DEFAULT '0.0000',
  `status` tinyint DEFAULT '1',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模拟盘订单表';

-- ----------------------------
-- Records of think_paper_order
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_paper_position
-- ----------------------------
DROP TABLE IF EXISTS `think_paper_position`;
CREATE TABLE `think_paper_position` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `account_id` int unsigned NOT NULL,
  `member_id` int unsigned DEFAULT '0',
  `symbol` varchar(50) NOT NULL,
  `position_side` varchar(10) DEFAULT 'LONG',
  `quantity` decimal(20,8) DEFAULT '0.00000000',
  `entry_price` decimal(20,8) DEFAULT '0.00000000',
  `leverage` int DEFAULT '1',
  `unrealized_pnl` decimal(20,4) DEFAULT '0.0000',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_account` (`account_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模拟盘持仓表';

-- ----------------------------
-- Records of think_paper_position
-- ----------------------------
BEGIN;
INSERT INTO `think_paper_position` (`id`, `account_id`, `member_id`, `symbol`, `position_side`, `quantity`, `entry_price`, `leverage`, `unrealized_pnl`, `create_time`, `update_time`, `mark`) VALUES (1, 1, 1, 'BTC/USDT', 'LONG', 0.50000000, 50000.00000000, 10, 500.0000, 1769653165, 0, 0);
COMMIT;

-- ----------------------------
-- Table structure for think_paper_trade
-- ----------------------------
DROP TABLE IF EXISTS `think_paper_trade`;
CREATE TABLE `think_paper_trade` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `account_id` int unsigned NOT NULL,
  `symbol` varchar(50) NOT NULL,
  `position_side` varchar(10) DEFAULT 'LONG',
  `quantity` decimal(20,8) DEFAULT '0.00000000',
  `entry_price` decimal(20,8) DEFAULT '0.00000000',
  `exit_price` decimal(20,8) DEFAULT '0.00000000',
  `pnl` decimal(20,4) DEFAULT '0.0000',
  `create_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模拟盘交易记录表';

-- ----------------------------
-- Records of think_paper_trade
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_performance_metrics
-- ----------------------------
DROP TABLE IF EXISTS `think_performance_metrics`;
CREATE TABLE `think_performance_metrics` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `metric_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '指标键',
  `metric_value` decimal(15,4) NOT NULL DEFAULT '0.0000' COMMENT '指标值',
  `tags` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '标签(JSON)',
  `record_time` int unsigned NOT NULL DEFAULT '0' COMMENT '记录时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_metric_key` (`metric_key`) USING BTREE,
  KEY `idx_record_time` (`record_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='性能指标表';

-- ----------------------------
-- Records of think_performance_metrics
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_platform_address
-- ----------------------------
DROP TABLE IF EXISTS `think_platform_address`;
CREATE TABLE `think_platform_address` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `chain_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '链类型：BEP20 BSC等',
  `address` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '地址',
  `private_key` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '私钥（加密存储）',
  `private_key_status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '私钥状态：1已加密 2未加密',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2禁用',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_address` (`address`) USING BTREE,
  KEY `idx_chain_type` (`chain_type`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='平台收款地址表';

-- ----------------------------
-- Records of think_platform_address
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_point_card_log
-- ----------------------------
DROP TABLE IF EXISTS `think_point_card_log`;
CREATE TABLE `think_point_card_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `related_member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '关联会员ID(互转对方)',
  `change_type` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '变更类型：1充值 2赠送 3互转转出 4互转转入 5扣减',
  `source_type` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '来源类型：1自充 2赠送',
  `amount` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '变更数量',
  `before_self` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '自充变更前',
  `after_self` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '自充变更后',
  `before_gift` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '赠送变更前',
  `after_gift` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '赠送变更后',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `order_id` int unsigned DEFAULT '0' COMMENT '关联订单ID',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '操作人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_member_id` (`member_id`) USING BTREE,
  KEY `idx_related_member_id` (`related_member_id`) USING BTREE,
  KEY `idx_create_time` (`create_time`) USING BTREE,
  KEY `idx_mark` (`mark`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='点卡流水记录表';

-- ----------------------------
-- Records of think_point_card_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_position
-- ----------------------------
DROP TABLE IF EXISTS `think_position`;
CREATE TABLE `think_position` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '账户ID',
  `leader_id` int unsigned DEFAULT '0' COMMENT '领导者ID',
  `exchange` varchar(50) NOT NULL DEFAULT '' COMMENT '交易所',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `side` tinyint NOT NULL DEFAULT '1' COMMENT '1=买入 2=卖出',
  `position_side` varchar(10) NOT NULL DEFAULT '' COMMENT '持仓方向:LONG/SHORT',
  `quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000',
  `entry_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '入场价格',
  `current_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '当前价格',
  `unrealized_pnl` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '未实现盈亏',
  `realized_pnl` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '已实现盈亏',
  `leverage` int NOT NULL DEFAULT '1' COMMENT '杠杆倍数',
  `margin` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '保证金',
  `liquidation_price` decimal(20,8) DEFAULT NULL COMMENT '强平价',
  `take_profit` decimal(20,8) DEFAULT NULL,
  `stop_loss` decimal(20,8) DEFAULT NULL,
  `position_value` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '持仓价值',
  `position_mode` varchar(20) NOT NULL DEFAULT 'oneway' COMMENT '持仓模式:oneway单向/hedge双向',
  `strategy_id` int unsigned DEFAULT '0' COMMENT '策略ID',
  `open_time` int unsigned NOT NULL DEFAULT '0' COMMENT '开仓时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `close_time` int unsigned DEFAULT '0' COMMENT '平仓时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识:1有效/0无效',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_account` (`account_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_mark` (`mark`),
  KEY `idx_member_side` (`member_id`,`position_side`),
  KEY `idx_symbol_side` (`symbol`,`position_side`),
  KEY `idx_update_time` (`update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='持仓表';

-- ----------------------------
-- Records of think_position
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_position_alert_config
-- ----------------------------
DROP TABLE IF EXISTS `think_position_alert_config`;
CREATE TABLE `think_position_alert_config` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL DEFAULT '' COMMENT '预警名称',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT 'Leader会员ID,0表示全部',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对,空表示全部',
  `alert_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '预警类型:1单次变化金额 2单次变化比例 3累计变化金额',
  `threshold` decimal(20,4) NOT NULL DEFAULT '0.0000' COMMENT '阈值',
  `operator` varchar(10) NOT NULL DEFAULT '>=' COMMENT '比较运算符',
  `change_types` varchar(50) NOT NULL DEFAULT '1,2,3,4' COMMENT '监控的变化类型:1开仓 2加仓 3减仓 4平仓',
  `notify_channels` varchar(50) NOT NULL DEFAULT 'telegram' COMMENT '通知渠道:telegram,email',
  `notify_targets` varchar(255) NOT NULL DEFAULT 'admin' COMMENT '通知目标:admin,member,指定chat_id',
  `cooldown` int unsigned NOT NULL DEFAULT '300' COMMENT '冷却时间(秒),防止重复告警',
  `last_trigger_time` int unsigned NOT NULL DEFAULT '0' COMMENT '上次触发时间',
  `trigger_count` int unsigned NOT NULL DEFAULT '0' COMMENT '累计触发次数',
  `level` tinyint unsigned NOT NULL DEFAULT '2' COMMENT '告警级别:1低 2中 3高 4紧急',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态:1启用 2禁用',
  `remark` varchar(500) NOT NULL DEFAULT '' COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_user` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='持仓预警配置表';

-- ----------------------------
-- Records of think_position_alert_config
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_position_change_history
-- ----------------------------
DROP TABLE IF EXISTS `think_position_change_history`;
CREATE TABLE `think_position_change_history` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT 'Leader会员ID',
  `exchange_account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '交易所账户ID',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `change_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '变化类型:1开仓 2加仓 3减仓 4平仓',
  `side` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '方向:1买入/做多 2卖出/做空',
  `old_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '变化前数量',
  `new_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '变化后数量',
  `change_quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '变化数量(绝对值)',
  `old_value` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '变化前价值(USDT)',
  `new_value` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '变化后价值(USDT)',
  `change_value` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '变化价值(USDT)',
  `price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '变化时价格',
  `signal_id` int unsigned NOT NULL DEFAULT '0' COMMENT '关联信号ID',
  `remark` varchar(500) NOT NULL DEFAULT '' COMMENT '备注(JSON格式存储额外信息)',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '删除标记:1正常 0删除',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_account` (`exchange_account_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_change_type` (`change_type`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_member_symbol` (`member_id`,`symbol`),
  KEY `idx_member_time` (`member_id`,`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='持仓变化历史表';

-- ----------------------------
-- Records of think_position_change_history
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_position_log
-- ----------------------------
DROP TABLE IF EXISTS `think_position_log`;
CREATE TABLE `think_position_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `position_id` int unsigned NOT NULL DEFAULT '0',
  `member_id` int unsigned NOT NULL DEFAULT '0',
  `symbol` varchar(30) DEFAULT '',
  `action` varchar(20) NOT NULL DEFAULT '' COMMENT '操作: set_tp, set_sl, close',
  `before_data` text COMMENT '操作前数据',
  `after_data` text COMMENT '操作后数据',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_position` (`position_id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='持仓操作日志';

-- ----------------------------
-- Records of think_position_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_position_snapshot
-- ----------------------------
DROP TABLE IF EXISTS `think_position_snapshot`;
CREATE TABLE `think_position_snapshot` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `exchange_account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '交易所账户ID',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '持仓数量',
  `price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '价格',
  `notional_value` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '持仓金额',
  `last_sync_time` int unsigned NOT NULL DEFAULT '0' COMMENT '最后同步时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_member_account_symbol` (`member_id`,`exchange_account_id`,`symbol`),
  KEY `idx_member` (`member_id`),
  KEY `idx_account` (`exchange_account_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='持仓快照表';

-- ----------------------------
-- Records of think_position_snapshot
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_price_alert
-- ----------------------------
DROP TABLE IF EXISTS `think_price_alert`;
CREATE TABLE `think_price_alert` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `symbol` varchar(50) NOT NULL COMMENT '交易对',
  `alert_type` varchar(50) NOT NULL COMMENT '预警类型',
  `target_value` decimal(20,8) DEFAULT '0.00000000' COMMENT '目标值',
  `note` varchar(200) DEFAULT '' COMMENT '备注',
  `repeat_alert` tinyint DEFAULT '0' COMMENT '是否重复提醒',
  `repeat_interval` int DEFAULT '3600' COMMENT '重复提醒间隔秒',
  `status` tinyint DEFAULT '1' COMMENT '状态 0禁用 1监控中 2已触发',
  `last_check_time` int unsigned DEFAULT '0' COMMENT '最后检查时间',
  `last_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '最后检查价格',
  `trigger_time` int unsigned DEFAULT '0' COMMENT '触发时间',
  `trigger_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '触发时价格',
  `trigger_count` int DEFAULT '0' COMMENT '触发次数',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='价格预警表';

-- ----------------------------
-- Records of think_price_alert
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_price_alert_log
-- ----------------------------
DROP TABLE IF EXISTS `think_price_alert_log`;
CREATE TABLE `think_price_alert_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `alert_id` int unsigned DEFAULT '0' COMMENT '预警ID',
  `symbol` varchar(50) NOT NULL COMMENT '交易对',
  `alert_type` varchar(50) NOT NULL COMMENT '预警类型',
  `target_value` decimal(20,8) DEFAULT '0.00000000' COMMENT '目标值',
  `trigger_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '触发价格',
  `change_percent` decimal(10,2) DEFAULT '0.00' COMMENT '涨跌幅',
  `create_time` int unsigned DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_alert_id` (`alert_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='价格预警日志表';

-- ----------------------------
-- Records of think_price_alert_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_profit_record
-- ----------------------------
DROP TABLE IF EXISTS `think_profit_record`;
CREATE TABLE `think_profit_record` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT 'Leader会员ID',
  `exchange_account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '交易所账户ID',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `position_change_id` int unsigned NOT NULL DEFAULT '0' COMMENT '关联持仓变化ID',
  `change_type` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '变化类型:1开仓 2加仓 3减仓 4平仓',
  `entry_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '开仓均价',
  `exit_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '平仓价格',
  `quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '交易数量',
  `realized_pnl` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '已实现盈亏(USDT)',
  `fee` decimal(20,4) NOT NULL DEFAULT '0.0000' COMMENT '手续费',
  `net_pnl` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '净盈亏(扣除手续费)',
  `pnl_percent` decimal(10,4) NOT NULL DEFAULT '0.0000' COMMENT '盈亏比例(%)',
  `holding_time` int unsigned NOT NULL DEFAULT '0' COMMENT '持仓时间(秒)',
  `trade_date` date NOT NULL COMMENT '交易日期',
  `remark` varchar(500) NOT NULL DEFAULT '' COMMENT '备注',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_account` (`exchange_account_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_trade_date` (`trade_date`),
  KEY `idx_member_date` (`member_id`,`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='盈亏记录表';

-- ----------------------------
-- Records of think_profit_record
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_push_channel
-- ----------------------------
DROP TABLE IF EXISTS `think_push_channel`;
CREATE TABLE `think_push_channel` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `channel_code` varchar(30) NOT NULL DEFAULT '' COMMENT '渠道代码:telegram,wechat,email,sms',
  `channel_name` varchar(50) NOT NULL DEFAULT '' COMMENT '渠道名称',
  `config` text COMMENT '配置JSON',
  `template` text COMMENT '消息模板',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态:1启用 0禁用',
  `sort` int unsigned DEFAULT '0' COMMENT '排序',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`channel_code`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='推送渠道配置表';

-- ----------------------------
-- Records of think_push_channel
-- ----------------------------
BEGIN;
INSERT INTO `think_push_channel` (`id`, `channel_code`, `channel_name`, `config`, `template`, `status`, `sort`, `create_time`, `update_time`, `mark`) VALUES (1, 'telegram', 'Telegram', '{\"bot_token\":\"\",\"enabled\":true}', '{open_emoji} {signal_type_name}\n\n带单员: {leader_name}\n交易对: {symbol}\n方向: {side_name} {direction_emoji}\n入场价: ${entry_price}\n杠杆: {leverage}x\n仓位: ${amount}\n\n⏰ {time}', 1, 1, 1769495481, 1769679234, 1);
INSERT INTO `think_push_channel` (`id`, `channel_code`, `channel_name`, `config`, `template`, `status`, `sort`, `create_time`, `update_time`, `mark`) VALUES (2, 'wechat', '企业微信', '{\"corpid\":\"\",\"corpsecret\":\"\",\"agentid\":\"\",\"enabled\":false}', '【{signal_type_name}】{leader_name} {symbol} {side_name} 入场${entry_price} 杠杆{leverage}x', 1, 2, 1769495481, 1769495481, 1);
INSERT INTO `think_push_channel` (`id`, `channel_code`, `channel_name`, `config`, `template`, `status`, `sort`, `create_time`, `update_time`, `mark`) VALUES (3, 'email', '邮件', '{\"smtp_host\":\"\",\"smtp_port\":465,\"smtp_user\":\"\",\"smtp_pass\":\"\",\"from_name\":\"交易信号\",\"enabled\":false}', '', 1, 3, 1769495481, 1769495481, 1);
INSERT INTO `think_push_channel` (`id`, `channel_code`, `channel_name`, `config`, `template`, `status`, `sort`, `create_time`, `update_time`, `mark`) VALUES (4, 'websocket', 'WebSocket', '{\"enabled\":true}', '', 1, 4, 1769495481, 1769495481, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_risk_action_template
-- ----------------------------
DROP TABLE IF EXISTS `think_risk_action_template`;
CREATE TABLE `think_risk_action_template` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '模板名称',
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '模板代码',
  `action_type` tinyint(1) NOT NULL DEFAULT '1' COMMENT '动作类型 1限仓 2限价 3强平 4暂停策略 5发送通知',
  `param_json` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '参数JSON',
  `description` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '描述说明',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态 1启用 2停用',
  `sort` int NOT NULL DEFAULT '0' COMMENT '排序',
  `create_user` int NOT NULL DEFAULT '0' COMMENT '创建人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标识',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_code` (`code`) USING BTREE,
  KEY `idx_action_type` (`action_type`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='风控动作模板表';

-- ----------------------------
-- Records of think_risk_action_template
-- ----------------------------
BEGIN;
INSERT INTO `think_risk_action_template` (`id`, `name`, `code`, `action_type`, `param_json`, `description`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, '限仓50%', 'limit_position_50', 1, '{\"position_ratio\": 50}', '当触发风控时，将仓位限制为50%', 1, 1, 0, 0, 0, 1769679249, 0);
INSERT INTO `think_risk_action_template` (`id`, `name`, `code`, `action_type`, `param_json`, `description`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, '限仓30%', 'limit_position_30', 1, '{\"position_ratio\": 30}', '当触发风控时，将仓位限制为30%', 1, 2, 0, 0, 0, 0, 1);
INSERT INTO `think_risk_action_template` (`id`, `name`, `code`, `action_type`, `param_json`, `description`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (3, '限价买入', 'limit_price_buy', 2, '{\"price_offset\": 0.01, \"direction\": \"buy\"}', '买入时限制价格偏移', 1, 3, 0, 0, 0, 0, 1);
INSERT INTO `think_risk_action_template` (`id`, `name`, `code`, `action_type`, `param_json`, `description`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, '限价卖出', 'limit_price_sell', 2, '{\"price_offset\": 0.01, \"direction\": \"sell\"}', '卖出时限制价格偏移', 1, 4, 0, 0, 0, 0, 1);
INSERT INTO `think_risk_action_template` (`id`, `name`, `code`, `action_type`, `param_json`, `description`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (5, '暂停策略', 'pause_strategy', 4, '{\"duration_minutes\": 30}', '触发风控后暂停策略执行30分钟', 1, 5, 0, 0, 0, 0, 1);
INSERT INTO `think_risk_action_template` (`id`, `name`, `code`, `action_type`, `param_json`, `description`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (6, '发送通知', 'send_notification', 5, '{\"channel\": \"all\", \"level\": \"warning\"}', '发送风控通知', 1, 6, 0, 0, 0, 0, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_risk_daily_stat
-- ----------------------------
DROP TABLE IF EXISTS `think_risk_daily_stat`;
CREATE TABLE `think_risk_daily_stat` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `stat_date` date NOT NULL COMMENT '统计日期',
  `instance_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略实例ID(0=全局)',
  `symbol` varchar(20) DEFAULT NULL COMMENT '交易对',
  `total_trades` int unsigned NOT NULL DEFAULT '0' COMMENT '交易次数',
  `win_trades` int unsigned NOT NULL DEFAULT '0' COMMENT '盈利次数',
  `loss_trades` int unsigned NOT NULL DEFAULT '0' COMMENT '亏损次数',
  `total_profit` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总盈利',
  `total_loss` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总亏损',
  `net_pnl` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '净盈亏',
  `max_single_loss` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '最大单笔亏损',
  `consecutive_losses` int unsigned NOT NULL DEFAULT '0' COMMENT '当前连续亏损次数',
  `max_consecutive_losses` int unsigned NOT NULL DEFAULT '0' COMMENT '最大连续亏损次数',
  `risk_events` int unsigned NOT NULL DEFAULT '0' COMMENT '风控事件次数',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_date_instance` (`stat_date`,`instance_id`),
  KEY `idx_instance_id` (`instance_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='风控统计表';

-- ----------------------------
-- Records of think_risk_daily_stat
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_risk_event
-- ----------------------------
DROP TABLE IF EXISTS `think_risk_event`;
CREATE TABLE `think_risk_event` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `rule_id` int unsigned NOT NULL DEFAULT '0' COMMENT '触发的规则ID',
  `rule_name` varchar(100) DEFAULT NULL COMMENT '规则名称(冗余)',
  `rule_type` varchar(30) NOT NULL COMMENT '规则类型',
  `instance_id` int unsigned DEFAULT NULL COMMENT '策略实例ID',
  `instance_name` varchar(100) DEFAULT NULL COMMENT '实例名称(冗余)',
  `symbol` varchar(20) DEFAULT NULL COMMENT '交易对',
  `trigger_value` decimal(20,8) DEFAULT NULL COMMENT '触发值',
  `threshold` decimal(20,8) DEFAULT NULL COMMENT '阈值',
  `action_taken` varchar(20) NOT NULL COMMENT '采取的动作',
  `action_result` tinyint unsigned DEFAULT '1' COMMENT '动作结果: 1=成功 2=失败',
  `signal_id` int unsigned DEFAULT NULL COMMENT '关联的信号ID',
  `description` text COMMENT '详细描述',
  `extra_data` text COMMENT '额外数据JSON',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标记',
  PRIMARY KEY (`id`),
  KEY `idx_rule_id` (`rule_id`),
  KEY `idx_instance_id` (`instance_id`),
  KEY `idx_rule_type` (`rule_type`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='风控事件日志表';

-- ----------------------------
-- Records of think_risk_event
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_risk_rule
-- ----------------------------
DROP TABLE IF EXISTS `think_risk_rule`;
CREATE TABLE `think_risk_rule` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(100) NOT NULL COMMENT '规则名称',
  `rule_type` varchar(30) NOT NULL COMMENT '规则类型: position_limit/daily_loss/consecutive_loss/max_single_loss/trade_frequency',
  `target_type` varchar(20) NOT NULL DEFAULT 'global' COMMENT '目标类型: global/instance/symbol/member',
  `target_id` int unsigned NOT NULL DEFAULT '0' COMMENT '目标ID(instance_id或0表示全局)',
  `target_symbol` varchar(20) DEFAULT NULL COMMENT '目标交易对(target_type=symbol时)',
  `target_member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '目标会员ID',
  `threshold` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '阈值',
  `threshold_unit` varchar(20) DEFAULT 'USDT' COMMENT '阈值单位',
  `time_window` int unsigned DEFAULT '0' COMMENT '时间窗口(秒),0表示不限',
  `action` varchar(20) NOT NULL DEFAULT 'alert' COMMENT '触发动作: alert/pause/stop',
  `priority` int unsigned NOT NULL DEFAULT '100' COMMENT '优先级(越小越先)',
  `description` varchar(500) DEFAULT NULL COMMENT '描述',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态: 1=启用 2=禁用',
  `trigger_count` int unsigned NOT NULL DEFAULT '0' COMMENT '触发次数',
  `last_trigger_time` int unsigned DEFAULT NULL COMMENT '最后触发时间',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '创建人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标记',
  PRIMARY KEY (`id`),
  KEY `idx_rule_type` (`rule_type`),
  KEY `idx_target` (`target_type`,`target_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='风控规则表';

-- ----------------------------
-- Records of think_risk_rule
-- ----------------------------
BEGIN;
INSERT INTO `think_risk_rule` (`id`, `name`, `rule_type`, `target_type`, `target_id`, `target_symbol`, `target_member_id`, `threshold`, `threshold_unit`, `time_window`, `action`, `priority`, `description`, `status`, `trigger_count`, `last_trigger_time`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, '', '', 'global', 0, '', 0, 0.00000000, 'USDT', 0, 'alert', 100, '', 1, 0, NULL, 0, 1769504316, 0, 1769679229, 0);
INSERT INTO `think_risk_rule` (`id`, `name`, `rule_type`, `target_type`, `target_id`, `target_symbol`, `target_member_id`, `threshold`, `threshold_unit`, `time_window`, `action`, `priority`, `description`, `status`, `trigger_count`, `last_trigger_time`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, '连续亏损暂停', 'consecutive_loss', 'global', 0, NULL, 0, 3.00000000, '次', 0, 'pause', 20, '连续亏损3次暂停策略', 1, 0, NULL, 0, 1769504316, 0, 0, 1);
INSERT INTO `think_risk_rule` (`id`, `name`, `rule_type`, `target_type`, `target_id`, `target_symbol`, `target_member_id`, `threshold`, `threshold_unit`, `time_window`, `action`, `priority`, `description`, `status`, `trigger_count`, `last_trigger_time`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (3, '单笔最大亏损', 'max_single_loss', 'global', 0, NULL, 0, 100.00000000, 'USDT', 0, 'alert', 30, '单笔亏损超过100 USDT发送告警', 1, 0, NULL, 0, 1769504316, 0, 0, 1);
INSERT INTO `think_risk_rule` (`id`, `name`, `rule_type`, `target_type`, `target_id`, `target_symbol`, `target_member_id`, `threshold`, `threshold_unit`, `time_window`, `action`, `priority`, `description`, `status`, `trigger_count`, `last_trigger_time`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, '最大持仓限制', 'position_limit', 'global', 0, NULL, 0, 5.00000000, '个', 0, 'alert', 40, '同时持仓超过5个发送告警', 1, 0, NULL, 0, 1769504316, 0, 0, 1);
INSERT INTO `think_risk_rule` (`id`, `name`, `rule_type`, `target_type`, `target_id`, `target_symbol`, `target_member_id`, `threshold`, `threshold_unit`, `time_window`, `action`, `priority`, `description`, `status`, `trigger_count`, `last_trigger_time`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (5, '交易频率限制', 'trade_frequency', 'global', 0, NULL, 0, 20.00000000, '次/小时', 0, 'alert', 50, '每小时交易超过20次发送告警', 1, 0, NULL, 0, 1769504316, 0, 1769537621, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_risk_trigger_log
-- ----------------------------
DROP TABLE IF EXISTS `think_risk_trigger_log`;
CREATE TABLE `think_risk_trigger_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `rule_id` int unsigned DEFAULT '0' COMMENT '规则ID',
  `member_id` int unsigned DEFAULT '0' COMMENT '会员ID',
  `trigger_data` text COMMENT '触发时数据JSON',
  `action_taken` varchar(50) DEFAULT '' COMMENT '执行的动作',
  `create_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_rule_id` (`rule_id`),
  KEY `idx_member_id` (`member_id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='风控触发日志表';

-- ----------------------------
-- Records of think_risk_trigger_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_role
-- ----------------------------
DROP TABLE IF EXISTS `think_role`;
CREATE TABLE `think_role` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色名称',
  `code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色标签',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1正常 2禁用',
  `note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `sort` smallint unsigned NOT NULL DEFAULT '125' COMMENT '排序',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '添加时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `name` (`name`) USING BTREE,
  KEY `idx_mark` (`mark`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统角色表';

-- ----------------------------
-- Records of think_role
-- ----------------------------
BEGIN;
INSERT INTO `think_role` (`id`, `name`, `code`, `status`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, '超级管理员', 'super', 1, '超级管理员拥有绝对权限', 1, 1, 1621998864, 1, 1634197059, 1);
INSERT INTO `think_role` (`id`, `name`, `code`, `status`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, '管理员', 'admin', 1, NULL, 5, 1, 1621998864, 1, 1621998864, 1);
INSERT INTO `think_role` (`id`, `name`, `code`, `status`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (3, '运营', 'yunying', 1, NULL, 10, 1, 1621998864, 1, 1621998864, 1);
INSERT INTO `think_role` (`id`, `name`, `code`, `status`, `note`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, '客服', 'kefu', 1, NULL, 15, 1, 1621998864, 1, 1621998864, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_role_menu
-- ----------------------------
DROP TABLE IF EXISTS `think_role_menu`;
CREATE TABLE `think_role_menu` (
  `role_id` smallint unsigned NOT NULL DEFAULT '0' COMMENT '角色ID',
  `menu_id` smallint unsigned NOT NULL DEFAULT '0' COMMENT '菜单ID',
  PRIMARY KEY (`role_id`,`menu_id`) USING BTREE,
  KEY `idx_role_id` (`role_id`) USING BTREE,
  KEY `idx_menu_id` (`menu_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色菜单关联表';

-- ----------------------------
-- Records of think_role_menu
-- ----------------------------
BEGIN;
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 1);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 2);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 3);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 4);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 5);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 6);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 8);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 101);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 102);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 103);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 104);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 201);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 203);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 204);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 210);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 211);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 212);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 213);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 214);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 220);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 221);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 222);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 230);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 231);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 232);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 233);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 240);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 241);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 242);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 243);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 250);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 251);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 252);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 253);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 254);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 260);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 261);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 262);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 263);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 270);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 271);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 272);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 273);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 274);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 275);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 276);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 301);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 302);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 303);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 304);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 305);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 306);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 307);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 308);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 310);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 311);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 401);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 501);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 502);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 503);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 601);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 602);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 603);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 604);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 605);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 606);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 607);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 608);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 609);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 610);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 611);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 612);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 613);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 614);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 615);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 616);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 617);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 801);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 900);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 901);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 902);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 910);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 911);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 912);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 920);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 921);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 922);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 930);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 931);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 932);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 933);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 940);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 941);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 942);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 943);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 944);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 950);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 951);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 960);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 961);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 962);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 963);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 964);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 965);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 966);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 970);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 971);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 972);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 973);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 974);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 975);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 976);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 977);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 980);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 990);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 991);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 1000);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 1001);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 1002);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 1003);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 1004);
INSERT INTO `think_role_menu` (`role_id`, `menu_id`) VALUES (1, 1005);
COMMIT;

-- ----------------------------
-- Table structure for think_scheduled_report
-- ----------------------------
DROP TABLE IF EXISTS `think_scheduled_report`;
CREATE TABLE `think_scheduled_report` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT '' COMMENT '任务名称',
  `report_type` varchar(50) DEFAULT '' COMMENT '报告类型',
  `template_code` varchar(100) DEFAULT '' COMMENT '模板编码',
  `schedule_type` varchar(20) DEFAULT 'daily' COMMENT '调度类型',
  `schedule_value` varchar(50) DEFAULT '' COMMENT '调度值',
  `chat_ids` varchar(500) DEFAULT '' COMMENT '目标Chat IDs',
  `status` tinyint DEFAULT '1' COMMENT '状态',
  `last_run_time` int unsigned DEFAULT '0' COMMENT '上次执行时间',
  `next_run_time` int unsigned DEFAULT '0' COMMENT '下次执行时间',
  `run_count` int unsigned DEFAULT '0' COMMENT '执行次数',
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint DEFAULT '1' COMMENT '标记',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='定时汇报表';

-- ----------------------------
-- Records of think_scheduled_report
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_settlement
-- ----------------------------
DROP TABLE IF EXISTS `think_settlement`;
CREATE TABLE `think_settlement` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `settlement_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '结算单号',
  `agent_id` int unsigned NOT NULL DEFAULT '0' COMMENT '代理商ID',
  `settlement_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '结算类型：1利润分成 2燃料费分摊',
  `amount` decimal(15,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '结算金额',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1待审核 2已审核 3已打款 4已拒绝',
  `apply_time` int unsigned NOT NULL DEFAULT '0' COMMENT '申请时间',
  `audit_time` int unsigned NOT NULL DEFAULT '0' COMMENT '审核时间',
  `audit_user` int unsigned NOT NULL DEFAULT '0' COMMENT '审核人',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_settlement_no` (`settlement_no`) USING BTREE,
  KEY `idx_agent_id` (`agent_id`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_apply_time` (`apply_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='财务结算表';

-- ----------------------------
-- Records of think_settlement
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_settlement_detail
-- ----------------------------
DROP TABLE IF EXISTS `think_settlement_detail`;
CREATE TABLE `think_settlement_detail` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `settlement_id` int unsigned NOT NULL DEFAULT '0' COMMENT '结算记录ID',
  `settlement_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '结算编号',
  `detail_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '明细类型：1利润分成 2燃料费分摊',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `order_id` int unsigned NOT NULL DEFAULT '0' COMMENT '订单ID',
  `amount` decimal(15,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '金额',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_settlement_id` (`settlement_id`) USING BTREE,
  KEY `idx_member_id` (`member_id`) USING BTREE,
  KEY `idx_order_id` (`order_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='结算明细表';

-- ----------------------------
-- Records of think_settlement_detail
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_settlement_record
-- ----------------------------
DROP TABLE IF EXISTS `think_settlement_record`;
CREATE TABLE `think_settlement_record` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `settlement_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '结算编号',
  `agent_id` int unsigned NOT NULL DEFAULT '0' COMMENT '代理商ID',
  `settlement_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '结算类型：1代理商结算 2会员利润分成',
  `amount` decimal(15,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '结算金额',
  `fuel_fee_amount` decimal(15,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '燃料费金额',
  `profit_amount` decimal(15,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '利润金额',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '审核状态：1待审核 2已通过 3已拒绝',
  `apply_time` int unsigned NOT NULL DEFAULT '0' COMMENT '申请时间',
  `approve_time` int unsigned NOT NULL DEFAULT '0' COMMENT '审核时间',
  `approve_user` int unsigned NOT NULL DEFAULT '0' COMMENT '审核人',
  `reject_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '拒绝原因',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_settlement_no` (`settlement_no`) USING BTREE,
  KEY `idx_agent_id` (`agent_id`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_settlement_type` (`settlement_type`) USING BTREE,
  KEY `idx_apply_time` (`apply_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='结算记录表';

-- ----------------------------
-- Records of think_settlement_record
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_execution_log
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_execution_log`;
CREATE TABLE `think_signal_execution_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `signal_id` int unsigned NOT NULL DEFAULT '0' COMMENT '信号ID',
  `stop_order_id` int unsigned DEFAULT '0' COMMENT '止损订单ID',
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '账户ID',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `action` varchar(50) NOT NULL DEFAULT '' COMMENT '执行动作',
  `side` tinyint NOT NULL DEFAULT '1' COMMENT '1=买入 2=卖出',
  `price` decimal(20,8) DEFAULT '0.00000000' COMMENT '价格',
  `quantity` decimal(20,8) DEFAULT '0.00000000' COMMENT '数量',
  `order_id` varchar(100) DEFAULT '' COMMENT '订单ID',
  `status` varchar(20) NOT NULL DEFAULT 'success' COMMENT '状态: success/failed',
  `error_message` text COMMENT '错误信息',
  `execution_time` int unsigned DEFAULT '0' COMMENT '执行耗时(ms)',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_signal_id` (`signal_id`),
  KEY `idx_account_id` (`account_id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='信号执行日志表';

-- ----------------------------
-- Records of think_signal_execution_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_log
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_log`;
CREATE TABLE `think_signal_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `signal_id` int unsigned NOT NULL DEFAULT '0' COMMENT '信号ID',
  `signal_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '信号编号',
  `strategy_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略ID',
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '账户ID',
  `symbol` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '交易对',
  `side` tinyint(1) NOT NULL DEFAULT '0' COMMENT '方向 1买入 2卖出',
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '执行动作',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态 1成功 0失败',
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '执行信息',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标识',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_signal_id` (`signal_id`) USING BTREE,
  KEY `idx_strategy_id` (`strategy_id`) USING BTREE,
  KEY `idx_account_id` (`account_id`) USING BTREE,
  KEY `idx_create_time` (`create_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='信号执行日志表';

-- ----------------------------
-- Records of think_signal_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_monitor_log
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_monitor_log`;
CREATE TABLE `think_signal_monitor_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `check_time` int unsigned NOT NULL DEFAULT '0' COMMENT '检查时间',
  `total_checked` int unsigned DEFAULT '0' COMMENT '检查订单数',
  `triggered_count` int unsigned DEFAULT '0' COMMENT '触发数量',
  `trailing_updated` int unsigned DEFAULT '0' COMMENT '移动止损更新数',
  `errors` text COMMENT '错误信息JSON',
  `execution_time` int unsigned DEFAULT '0' COMMENT '执行耗时(ms)',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_check_time` (`check_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='信号监控日志表';

-- ----------------------------
-- Records of think_signal_monitor_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_notify_config
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_notify_config`;
CREATE TABLE `think_signal_notify_config` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL DEFAULT '' COMMENT '配置名称',
  `channel` varchar(20) NOT NULL DEFAULT 'telegram' COMMENT '通道: telegram/email/webhook/sms',
  `config` text COMMENT '配置JSON(chat_id/email/url等)',
  `events` varchar(500) DEFAULT '' COMMENT '订阅事件,逗号分隔',
  `symbols` varchar(500) DEFAULT '' COMMENT '过滤交易对,逗号分隔(空为全部)',
  `template` text COMMENT '自定义消息模板',
  `status` tinyint unsigned DEFAULT '1' COMMENT '状态: 0禁用 1启用',
  `user_id` int unsigned DEFAULT '0' COMMENT '用户ID',
  `last_notify_time` int unsigned DEFAULT '0' COMMENT '最后通知时间',
  `notify_count` int unsigned DEFAULT '0' COMMENT '通知次数',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_channel` (`channel`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='信号通知配置表';

-- ----------------------------
-- Records of think_signal_notify_config
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_notify_log
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_notify_log`;
CREATE TABLE `think_signal_notify_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `config_id` int unsigned NOT NULL DEFAULT '0' COMMENT '配置ID',
  `signal_id` int unsigned DEFAULT '0' COMMENT '信号ID',
  `event` varchar(50) NOT NULL DEFAULT '' COMMENT '事件类型',
  `channel` varchar(20) NOT NULL DEFAULT '' COMMENT '通道',
  `recipient` varchar(200) DEFAULT '' COMMENT '接收者',
  `content` text COMMENT '消息内容',
  `status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/sent/failed',
  `error_message` text COMMENT '错误信息',
  `send_time` int unsigned DEFAULT '0' COMMENT '发送时间',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_config_id` (`config_id`),
  KEY `idx_signal_id` (`signal_id`),
  KEY `idx_event` (`event`),
  KEY `idx_status` (`status`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='信号通知日志表';

-- ----------------------------
-- Records of think_signal_notify_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_pending
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_pending`;
CREATE TABLE `think_signal_pending` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `signal_id` int unsigned NOT NULL,
  `server_id` int unsigned NOT NULL,
  `member_id` int unsigned NOT NULL,
  `exchange_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `status` tinyint unsigned NOT NULL DEFAULT '1',
  `execute_time` int unsigned DEFAULT NULL,
  `error_msg` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_server_status` (`server_id`,`status`) USING BTREE,
  KEY `idx_member` (`member_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Records of think_signal_pending
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_push_log
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_push_log`;
CREATE TABLE `think_signal_push_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `signal_id` bigint unsigned NOT NULL DEFAULT '0' COMMENT '信号ID',
  `subscribe_id` int unsigned NOT NULL DEFAULT '0' COMMENT '订阅ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '接收用户ID',
  `leader_id` int unsigned NOT NULL DEFAULT '0' COMMENT '带单员ID',
  `channel` varchar(20) NOT NULL DEFAULT '' COMMENT '推送渠道',
  `signal_type` varchar(20) NOT NULL DEFAULT '' COMMENT '信号类型',
  `symbol` varchar(30) DEFAULT '' COMMENT '交易对',
  `title` varchar(200) DEFAULT '' COMMENT '信号标题',
  `content` text COMMENT '推送内容',
  `status` tinyint NOT NULL DEFAULT '0' COMMENT '状态:0待推送 1成功 2失败',
  `error_msg` varchar(500) DEFAULT '' COMMENT '错误信息',
  `retry_count` tinyint unsigned DEFAULT '0' COMMENT '重试次数',
  `push_time` int unsigned DEFAULT '0' COMMENT '推送时间',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_signal` (`signal_id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_status` (`status`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='信号推送日志表';

-- ----------------------------
-- Records of think_signal_push_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_stop_order
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_stop_order`;
CREATE TABLE `think_signal_stop_order` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `signal_id` int unsigned NOT NULL DEFAULT '0' COMMENT '信号ID',
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '账户ID',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `type` varchar(20) NOT NULL DEFAULT 'stop_loss' COMMENT '类型: stop_loss/take_profit',
  `side` tinyint NOT NULL DEFAULT '1' COMMENT '1=买入 2=卖出',
  `trigger_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '触发价格',
  `quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '数量',
  `entry_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '入场价格',
  `trailing_stop` tinyint unsigned DEFAULT '0' COMMENT '是否移动止损',
  `trailing_distance` decimal(5,2) DEFAULT '0.00' COMMENT '移动止损距离%',
  `highest_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '最高价(多单用)',
  `lowest_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '最低价(空单用)',
  `exchange_order_id` varchar(100) DEFAULT '' COMMENT '交易所订单ID',
  `status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/triggered/cancelled/failed',
  `triggered_at` int unsigned DEFAULT '0' COMMENT '触发时间',
  `triggered_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '实际触发价格',
  `pnl` decimal(20,8) DEFAULT '0.00000000' COMMENT '盈亏',
  `remark` varchar(500) DEFAULT '' COMMENT '备注',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_signal_id` (`signal_id`),
  KEY `idx_account_id` (`account_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='止损止盈订单表';

-- ----------------------------
-- Records of think_signal_stop_order
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_subscribe
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_subscribe`;
CREATE TABLE `think_signal_subscribe` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '订阅用户ID',
  `leader_id` int unsigned NOT NULL DEFAULT '0' COMMENT '带单员ID',
  `channels` varchar(255) NOT NULL DEFAULT '' COMMENT '推送渠道:telegram,wechat,email,websocket',
  `signal_types` varchar(255) NOT NULL DEFAULT 'open,close' COMMENT '信号类型:open,close,tp,sl,add',
  `symbols` varchar(500) DEFAULT '' COMMENT '过滤交易对,空表示全部',
  `min_amount` decimal(15,2) DEFAULT '0.00' COMMENT '最小仓位金额过滤',
  `quiet_start` time DEFAULT NULL COMMENT '免打扰开始时间',
  `quiet_end` time DEFAULT NULL COMMENT '免打扰结束时间',
  `telegram_chat_id` varchar(50) DEFAULT '' COMMENT 'Telegram Chat ID',
  `wechat_userid` varchar(100) DEFAULT '' COMMENT '企业微信用户ID',
  `email` varchar(100) DEFAULT '' COMMENT '邮箱地址',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态:1启用 0禁用',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_leader` (`leader_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='信号订阅表';

-- ----------------------------
-- Records of think_signal_subscribe
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_signal_template
-- ----------------------------
DROP TABLE IF EXISTS `think_signal_template`;
CREATE TABLE `think_signal_template` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL DEFAULT '' COMMENT '模板名称',
  `symbol` varchar(50) DEFAULT '' COMMENT '适用交易对(空为通用)',
  `category` varchar(50) DEFAULT 'default' COMMENT '分类: preset/user/strategy',
  `description` text COMMENT '描述',
  `side` tinyint NOT NULL DEFAULT '1' COMMENT '1=买入 2=卖出',
  `order_type` varchar(20) NOT NULL DEFAULT 'MARKET' COMMENT '订单类型',
  `stop_loss_type` varchar(20) DEFAULT 'percent' COMMENT '止损类型: percent/fixed/atr',
  `stop_loss_value` decimal(20,8) DEFAULT '0.00000000' COMMENT '止损值',
  `take_profit_type` varchar(20) DEFAULT 'percent' COMMENT '止盈类型: percent/fixed/risk_reward',
  `take_profit_value` decimal(20,8) DEFAULT '0.00000000' COMMENT '止盈值',
  `max_loss_percent` decimal(5,2) DEFAULT '0.00' COMMENT '最大亏损百分比',
  `max_loss` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '最大亏损金额',
  `trailing_stop` tinyint unsigned DEFAULT '0' COMMENT '是否移动止损',
  `trailing_distance` decimal(5,2) DEFAULT '0.00' COMMENT '移动止损距离%',
  `position_size_type` varchar(20) DEFAULT 'fixed' COMMENT '仓位类型: fixed/percent/kelly',
  `position_size_value` decimal(20,8) DEFAULT '0.00000000' COMMENT '仓位值',
  `leverage` tinyint unsigned DEFAULT '1' COMMENT '杠杆倍数',
  `extra_config` text COMMENT '额外配置JSON',
  `use_count` int unsigned DEFAULT '0' COMMENT '使用次数',
  `user_id` int unsigned DEFAULT '0' COMMENT '创建用户ID(0为系统)',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_category` (`category`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='信号模板表';

-- ----------------------------
-- Records of think_signal_template
-- ----------------------------
BEGIN;
INSERT INTO `think_signal_template` (`id`, `name`, `symbol`, `category`, `description`, `side`, `order_type`, `stop_loss_type`, `stop_loss_value`, `take_profit_type`, `take_profit_value`, `max_loss_percent`, `max_loss`, `trailing_stop`, `trailing_distance`, `position_size_type`, `position_size_value`, `leverage`, `extra_config`, `use_count`, `user_id`, `create_time`, `update_time`, `mark`) VALUES (1, '保守型 - 1:2风险回报', '', 'preset', '适合新手，止损2%，止盈4%，风险回报1:2', 1, 'MARKET', 'percent', 2.00000000, 'risk_reward', 2.00000000, 1.00, 0.00000000, 0, 0.00, 'fixed', 0.00000000, 1, NULL, 0, 0, 1769821557, 1769821557, 1);
INSERT INTO `think_signal_template` (`id`, `name`, `symbol`, `category`, `description`, `side`, `order_type`, `stop_loss_type`, `stop_loss_value`, `take_profit_type`, `take_profit_value`, `max_loss_percent`, `max_loss`, `trailing_stop`, `trailing_distance`, `position_size_type`, `position_size_value`, `leverage`, `extra_config`, `use_count`, `user_id`, `create_time`, `update_time`, `mark`) VALUES (2, '积极型 - 1:3风险回报', '', 'preset', '追求更高收益，止损1.5%，止盈4.5%', 1, 'MARKET', 'percent', 1.50000000, 'risk_reward', 3.00000000, 2.00, 0.00000000, 0, 0.00, 'fixed', 0.00000000, 1, NULL, 0, 0, 1769821557, 1769821557, 1);
INSERT INTO `think_signal_template` (`id`, `name`, `symbol`, `category`, `description`, `side`, `order_type`, `stop_loss_type`, `stop_loss_value`, `take_profit_type`, `take_profit_value`, `max_loss_percent`, `max_loss`, `trailing_stop`, `trailing_distance`, `position_size_type`, `position_size_value`, `leverage`, `extra_config`, `use_count`, `user_id`, `create_time`, `update_time`, `mark`) VALUES (3, '趋势跟踪 - 移动止损', '', 'preset', '适合趋势行情，开启移动止损锁定利润', 1, 'MARKET', 'percent', 2.00000000, 'percent', 10.00000000, 2.00, 0.00000000, 0, 1.50, 'fixed', 0.00000000, 1, NULL, 0, 0, 1769821557, 1770038098, 1);
INSERT INTO `think_signal_template` (`id`, `name`, `symbol`, `category`, `description`, `side`, `order_type`, `stop_loss_type`, `stop_loss_value`, `take_profit_type`, `take_profit_value`, `max_loss_percent`, `max_loss`, `trailing_stop`, `trailing_distance`, `position_size_type`, `position_size_value`, `leverage`, `extra_config`, `use_count`, `user_id`, `create_time`, `update_time`, `mark`) VALUES (4, '超短线 - 快进快出', '', 'preset', '小止损小止盈，快速进出', 1, 'MARKET', 'percent', 0.50000000, 'risk_reward', 1.50000000, 0.50, 0.00000000, 0, 0.00, 'fixed', 0.00000000, 1, NULL, 0, 0, 1769821557, 1769821557, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_smart_stop_order
-- ----------------------------
DROP TABLE IF EXISTS `think_smart_stop_order`;
CREATE TABLE `think_smart_stop_order` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `position_id` int unsigned DEFAULT '0',
  `member_id` int unsigned DEFAULT '0',
  `symbol` varchar(50) NOT NULL,
  `position_side` varchar(10) DEFAULT 'LONG',
  `entry_price` decimal(20,8) DEFAULT '0.00000000',
  `stop_loss` decimal(20,8) DEFAULT '0.00000000',
  `take_profit` decimal(20,8) DEFAULT '0.00000000',
  `quantity` decimal(20,8) DEFAULT '0.00000000',
  `method` varchar(20) DEFAULT 'atr',
  `multiplier` decimal(10,2) DEFAULT '2.00',
  `status` tinyint DEFAULT '1',
  `triggered_price` decimal(20,8) DEFAULT '0.00000000',
  `triggered_at` int unsigned DEFAULT '0',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_symbol_status` (`symbol`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='智能止损订单表';

-- ----------------------------
-- Records of think_smart_stop_order
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_staff
-- ----------------------------
DROP TABLE IF EXISTS `think_staff`;
CREATE TABLE `think_staff` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `nickname` varchar(50) DEFAULT NULL COMMENT '昵称',
  `password` varchar(255) DEFAULT NULL COMMENT '密码',
  `phone` varchar(20) DEFAULT NULL COMMENT '手机号',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态 0=禁用 1=启用',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  `create_user` int DEFAULT NULL COMMENT '创建人',
  `update_time` int unsigned DEFAULT '0' COMMENT '更新时间',
  `update_user` int DEFAULT NULL COMMENT '更新人',
  `mark` tinyint unsigned DEFAULT '1' COMMENT '有效标识',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='员工表';

-- ----------------------------
-- Records of think_staff
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_stop_loss_log
-- ----------------------------
DROP TABLE IF EXISTS `think_stop_loss_log`;
CREATE TABLE `think_stop_loss_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `order_id` int unsigned NOT NULL DEFAULT '0' COMMENT '订单ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `side` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '方向：1买入/做多 2卖出/做空',
  `trigger_type` varchar(20) NOT NULL DEFAULT '' COMMENT '触发类型：stop_loss/take_profit',
  `entry_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '开仓价',
  `trigger_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '触发价',
  `current_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '当前价',
  `signal_id` int unsigned NOT NULL DEFAULT '0' COMMENT '平仓信号ID',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识',
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_member_id` (`member_id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='止损止盈触发日志';

-- ----------------------------
-- Records of think_stop_loss_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_strategy
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy`;
CREATE TABLE `think_strategy` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '策略名称',
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '策略代码',
  `type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '策略类型：1趋势 2震荡 3套利 4高频',
  `market_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '市场类型：1现货 2合约',
  `contract_mode` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '合约模式：1单向 2多空双开',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '策略描述',
  `config` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '策略配置(JSON)',
  `risk_level` tinyint unsigned NOT NULL DEFAULT '2' COMMENT '风险等级：1低 2中 3高',
  `risk_style` tinyint unsigned NOT NULL DEFAULT '2' COMMENT '风险风格：1激进 2保守',
  `min_amount` decimal(10,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '最小投入金额',
  `max_amount` decimal(10,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '最大投入金额',
  `max_leverage` int unsigned NOT NULL DEFAULT '1' COMMENT '最大杠杆倍数',
  `default_leverage` int unsigned NOT NULL DEFAULT '1' COMMENT '默认杠杆倍数',
  `profit_rate` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '预期收益率(%)',
  `max_drawdown` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '最大回撤(%)',
  `win_rate` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '胜率(%)',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2停用',
  `sort` smallint unsigned NOT NULL DEFAULT '125' COMMENT '排序',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '添加时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_code` (`code`) USING BTREE,
  KEY `idx_name` (`name`) USING BTREE,
  KEY `idx_type` (`type`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_market_type` (`market_type`) USING BTREE,
  KEY `idx_contract_mode` (`contract_mode`) USING BTREE,
  KEY `idx_risk_style` (`risk_style`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='交易策略表';

-- ----------------------------
-- Records of think_strategy
-- ----------------------------
BEGIN;
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, '合约趋势激进', 'TPL_FUTURE_TREND_AGGR_001', 1, 2, 1, '合约趋势类激进策略模板（单向）', '{\n  \"strategy_type\": \"trend_aggressive\",\n  \"ema_fast\": 8,\n  \"ema_slow\": 21,\n  \"rsi_period\": 14,\n  \"atr_multiplier\": 1.5\n}', 3, 1, 200.00, 50000.00, 20, 10, 20.00, 12.00, 55.00, 1, 90, 1, 1769168608, 1, 1769168608, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (3, '合约对冲保守', 'TPL_FUTURE_HEDGE_CONS_001', 2, 2, 2, '合约多空双开保守策略模板', '{\n  \"strategy_type\": \"hedge_conservative\",\n  \"boll_period\": 20,\n  \"boll_std\": 2.0,\n  \"hedge_ratio\": 0.5\n}', 2, 2, 300.00, 150000.00, 5, 3, 10.00, 6.00, 70.00, 1, 80, 1, 1769168608, 1, 1769168608, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, '套利保守', 'TPL_ARB_CONS_001', 3, 2, 2, '跨交易所套利模板（保守）', '{\n  \"strategy_type\": \"arbitrage\",\n  \"spread_threshold\": 0.5,\n  \"lookback\": 20\n}', 1, 2, 1000.00, 500000.00, 3, 2, 6.00, 3.00, 80.00, 1, 70, 1, 1769168608, 1, 1769168608, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (5, '高频激进', 'TPL_HFT_AGGR_001', 4, 2, 1, '高频策略模板（激进）', '{\n  \"strategy_type\": \"hft\",\n  \"profit_target\": 0.15,\n  \"stop_loss\": 0.1,\n  \"rsi_period\": 7,\n  \"ema_period\": 5\n}', 3, 1, 500.00, 200000.00, 10, 8, 18.00, 10.00, 58.00, 1, 60, 1, 1769168608, 1, 1769168608, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (6, 'SMC智能资金分析策略', 'TPL_SMC_ANALYSIS_001', 1, 2, 1, 'Smart Money Concepts - 基于订单块、FVG、结构突破、流动性扫荡等智能资金概念的交易策略', '{\n  \"strategy_type\": \"smc\",\n  \"lookback\": 50\n}', 2, 1, 1000.00, 100000.00, 20, 10, 35.00, 15.00, 68.00, 1, 6, 0, 1769529518, 0, 1769529518, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (7, '均线密集交叉策略', 'TPL_MA_DENSE_001', 1, 2, 1, '基于多条均线的密集、缠绕、金叉死叉、回踩等信号的趋势跟随策略', '{\n  \"strategy_type\": \"ma_dense\",\n  \"ma_periods\": [5, 10, 20, 60],\n  \"ma_type\": \"EMA\"\n}', 1, 2, 500.00, 50000.00, 10, 5, 25.00, 10.00, 72.00, 1, 7, 0, 1769529518, 0, 1769529518, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (8, 'RSI布林带震荡策略', 'TPL_RSI_BOLL_001', 2, 2, 1, '适用于震荡行情，结合RSI超买超卖和布林带上下轨判断反转点，快进快出', '{\n  \"strategy_type\": \"rsi_boll\",\n  \"rsi_period\": 14,\n  \"rsi_overbought\": 70,\n  \"rsi_oversold\": 30,\n  \"boll_period\": 20,\n  \"boll_std\": 2.0\n}', 1, 2, 500.00, 50000.00, 10, 5, 20.00, 8.00, 72.00, 1, 8, 0, 1769530828, 0, 1769530828, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (9, '网格交易策略', 'TPL_GRID_TRADING_001', 2, 2, 1, '在震荡区间内设置网格，低买高卖，适合横盘市场，稳定获利', '{\n  \"strategy_type\": \"grid\",\n  \"grid_count\": 10,\n  \"price_range\": 5.0\n}', 1, 2, 1000.00, 100000.00, 5, 3, 15.00, 10.00, 75.00, 1, 9, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (10, '趋势突破策略', 'TPL_BREAKOUT_001', 1, 2, 1, '捕捉关键阻力位突破，趋势确立后重仓进场，适合单边行情', '{\n  \"strategy_type\": \"breakout\",\n  \"lookback\": 20,\n  \"breakout_threshold\": 1.5,\n  \"volume_confirm\": true\n}', 2, 1, 2000.00, 200000.00, 15, 10, 40.00, 18.00, 65.00, 1, 10, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (11, '动量追踪策略', 'TPL_MOMENTUM_001', 1, 2, 1, '追踪市场动量，快速进出，适合波动剧烈的市场', '{\n  \"strategy_type\": \"momentum\",\n  \"period\": 14,\n  \"threshold\": 5,\n  \"trailing_stop\": 0.8\n}', 3, 1, 1500.00, 150000.00, 20, 12, 50.00, 22.00, 62.00, 1, 11, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (12, '均线金叉策略', 'TPL_MA_CROSS_001', 1, 1, 1, '经典均线金叉死叉策略，稳健可靠，适合现货市场长期持有', '{\n  \"strategy_type\": \"ma_cross\",\n  \"fast_ma\": 5,\n  \"slow_ma\": 20,\n  \"use_ema\": false\n}', 1, 2, 500.00, 80000.00, 1, 1, 22.00, 8.00, 70.00, 1, 12, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (13, '布林带压缩突破', 'TPL_BOLL_SQUEEZE_001', 1, 2, 1, '捕捉布林带压缩后的爆发行情，高胜率突破策略', '{\n  \"strategy_type\": \"boll_squeeze\",\n  \"squeeze_threshold\": 1.5,\n  \"hold_bars\": 10,\n  \"breakout_volume\": 1.8\n}', 2, 1, 1200.00, 120000.00, 12, 8, 35.00, 15.00, 68.00, 1, 13, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (14, '波段交易策略', 'TPL_SWING_TRADE_001', 1, 2, 1, '捕捉中期波段，持仓周期3-7天，适合稳健投资者', '{\n  \"strategy_type\": \"swing\",\n  \"ma_period\": 20,\n  \"swing_target\": 5.0\n}', 1, 2, 1000.00, 100000.00, 8, 5, 28.00, 12.00, 72.00, 1, 14, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (15, '极值反转策略', 'TPL_REVERSAL_001', 2, 2, 1, '在极端行情中寻找反转机会，需要精准把握时机', '{\n  \"strategy_type\": \"reversal\",\n  \"rsi_extreme\": 20,\n  \"divergence_required\": true\n}', 3, 1, 800.00, 80000.00, 10, 6, 32.00, 20.00, 64.00, 1, 15, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (16, '日内剥头皮策略', 'TPL_SCALPING_001', 4, 2, 1, '1-5分钟快进快出，高频交易，单笔利润小但次数多', '{\n  \"strategy_type\": \"scalping\",\n  \"scalp_target\": 0.3,\n  \"stop_loss\": 0.2,\n  \"rsi_threshold\": [30, 70]\n}', 3, 1, 2000.00, 200000.00, 25, 15, 60.00, 25.00, 58.00, 1, 16, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (17, '多时间框架共振', 'TPL_MTF_001', 1, 2, 1, '结合1H/4H/1D多周期信号共振，提高胜率', '{\n  \"strategy_type\": \"mtf\",\n  \"ema_period\": 20\n}', 2, 2, 1500.00, 150000.00, 10, 7, 30.00, 14.00, 70.00, 1, 17, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (18, '支撑阻力突破', 'TPL_SR_BREAK_001', 1, 2, 1, '识别关键支撑阻力位，等待有效突破后进场', '{\n  \"strategy_type\": \"sr_break\",\n  \"lookback\": 50,\n  \"touch_count\": 3,\n  \"volume_spike\": 1.5\n}', 2, 1, 1000.00, 100000.00, 12, 8, 35.00, 16.00, 66.00, 1, 18, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (19, 'MACD背离策略', 'TPL_MACD_DIV_001', 2, 2, 1, '捕捉价格与MACD的背离信号，预判趋势反转', '{\n  \"strategy_type\": \"macd\",\n  \"fast\": 12,\n  \"slow\": 26,\n  \"signal\": 9,\n  \"divergence_bars\": 5\n}', 2, 2, 800.00, 80000.00, 8, 5, 25.00, 12.00, 68.00, 1, 19, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (20, '趋势加仓策略', 'TPL_TREND_ADD_001', 1, 2, 1, '趋势确立后分批加仓，金字塔式建仓，赚取大趋势利润', '{\n  \"strategy_type\": \"trend_add\",\n  \"ema_period\": 20,\n  \"pullback_pct\": 1.0,\n  \"max_add_times\": 3\n}', 2, 1, 2000.00, 200000.00, 15, 10, 45.00, 18.00, 65.00, 1, 20, 0, 1769530908, 0, 1769530908, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (21, '网格多空对冲策略', 'TPL_HEDGE_GRID_001', 2, 2, 2, '在震荡区间内使用网格信号开启多空双开，低买高卖并自动斩仓', '{\n  \"strategy_type\": \"hedge\",\n  \"signal_source\": \"grid\",\n  \"grid_levels\": 10\n}', 2, 2, 1000.00, 100000.00, 20, 10, 25.00, 15.00, 70.00, 1, 21, 0, 1769532965, 0, 1769532965, 1);
INSERT INTO `think_strategy` (`id`, `name`, `code`, `type`, `market_type`, `contract_mode`, `description`, `config`, `risk_level`, `risk_style`, `min_amount`, `max_amount`, `max_leverage`, `default_leverage`, `profit_rate`, `max_drawdown`, `win_rate`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (22, '极值反转对冲策略', 'TPL_HEDGE_REVERSAL_001', 2, 2, 2, '在极值区域开启多空双开，捕捉反转机会并智能斩仓', '{\n  \"strategy_type\": \"reversal_hedge\",\n  \"rsi_extreme_low\": 20,\n  \"boll_std\": 2.5\n}', 3, 1, 800.00, 80000.00, 15, 10, 35.00, 20.00, 65.00, 1, 22, 0, 1769532965, 0, 1769532965, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_account
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_account`;
CREATE TABLE `think_strategy_account` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `strategy_instance_id` int unsigned NOT NULL COMMENT '策略实例ID',
  `account_id` int unsigned NOT NULL COMMENT '交易账户ID',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '所属会员ID',
  `ratio` decimal(5,2) NOT NULL DEFAULT '100.00' COMMENT '执行比例%',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1=启用 0=禁用',
  `total_trades` int unsigned NOT NULL DEFAULT '0' COMMENT '总交易次数',
  `total_profit` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总盈亏',
  `last_trade_time` int unsigned NOT NULL DEFAULT '0' COMMENT '最后交易时间',
  `remark` varchar(200) DEFAULT '' COMMENT '备注',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '软删除标记',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_strategy_account` (`strategy_instance_id`,`account_id`),
  KEY `idx_account` (`account_id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_status` (`status`,`mark`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略账户绑定表';

-- ----------------------------
-- Records of think_strategy_account
-- ----------------------------
BEGIN;
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (1, 7, 1, 1, 10.00, 0, 0, 0.00000000, 0, '', 1770028455, 1770100339, 0);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (2, 9, 1, 1, 100.00, 0, 0, 0.00000000, 0, '', 1770095731, 1770100339, 0);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (3, 10, 1, 1, 100.00, 0, 0, 0.00000000, 0, 'BTC 1H 对冲策略绑定', 1770112991, 1770112991, 0);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (4, 11, 1, 1, 100.00, 1, 0, 0.00000000, 0, 'BTC稳健策略', 1770113163, 1770115480, 0);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (5, 12, 1, 1, 100.00, 1, 0, 0.00000000, 0, 'BTC平衡策略', 1770113163, 1770132616, 0);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (6, 13, 1, 1, 100.00, 1, 0, 0.00000000, 0, 'BTC激进策略', 1770113163, 1770115484, 0);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (7, 14, 1, 1, 100.00, 1, 0, 0.00000000, 0, 'ETH稳健策略', 1770113163, 1770132649, 1);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (8, 15, 1, 1, 100.00, 1, 0, 0.00000000, 0, 'ETH平衡策略', 1770113163, 1770115486, 0);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (9, 16, 1, 1, 90.00, 1, 0, 0.00000000, 0, 'ETH激进策略', 1770113163, 1770119552, 0);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (15, 11, 5, 6, 100.00, 0, 0, 0.00000000, 0, '{\"singleLoop\":0}', 1770128767, 1770132620, 0);
INSERT INTO `think_strategy_account` (`id`, `strategy_instance_id`, `account_id`, `member_id`, `ratio`, `status`, `total_trades`, `total_profit`, `last_trade_time`, `remark`, `create_time`, `update_time`, `mark`) VALUES (16, 11, 6, 8, 100.00, 0, 0, 0.00000000, 0, '{\"singleLoop\":0}', 1770128856, 1770132626, 0);
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_backtest
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_backtest`;
CREATE TABLE `think_strategy_backtest` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL DEFAULT '' COMMENT '回测名称',
  `leader_id` int unsigned DEFAULT '0' COMMENT '带单员ID',
  `leader_name` varchar(100) DEFAULT '' COMMENT '带单员名称',
  `start_date` date NOT NULL COMMENT '开始日期',
  `end_date` date NOT NULL COMMENT '结束日期',
  `config` text COMMENT '配置参数JSON',
  `status` tinyint DEFAULT '0' COMMENT '状态 0待执行 1执行中 2已完成 3失败',
  `result` longtext COMMENT '回测结果JSON',
  `total_trades` int DEFAULT '0' COMMENT '总交易次数',
  `win_rate` decimal(10,2) DEFAULT '0.00' COMMENT '胜率',
  `total_profit` decimal(20,2) DEFAULT '0.00' COMMENT '总收益',
  `profit_rate` decimal(10,2) DEFAULT '0.00' COMMENT '收益率',
  `max_drawdown` decimal(10,2) DEFAULT '0.00' COMMENT '最大回撤',
  `sharpe_ratio` decimal(10,2) DEFAULT '0.00' COMMENT '夏普比率',
  `error_msg` varchar(500) DEFAULT '' COMMENT '错误信息',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_leader` (`leader_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略回测表';

-- ----------------------------
-- Records of think_strategy_backtest
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_combo
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_combo`;
CREATE TABLE `think_strategy_combo` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(100) NOT NULL COMMENT '组合名称',
  `description` varchar(500) DEFAULT NULL COMMENT '描述',
  `mode` tinyint(1) NOT NULL DEFAULT '1' COMMENT '组合模式: 1=共识模式 2=投票模式 3=权重模式',
  `vote_threshold` int unsigned DEFAULT '2' COMMENT '投票模式下的阈值',
  `symbol` varchar(20) NOT NULL COMMENT '交易对',
  `timeframe` varchar(10) NOT NULL DEFAULT '1h' COMMENT '周期',
  `config` text COMMENT '组合配置JSON',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态: 1=启用 2=禁用',
  `total_signals` int unsigned NOT NULL DEFAULT '0' COMMENT '总信号数',
  `success_signals` int unsigned NOT NULL DEFAULT '0' COMMENT '成功信号数',
  `last_signal_time` int unsigned DEFAULT NULL COMMENT '最后信号时间',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '创建人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标记',
  PRIMARY KEY (`id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略组合表';

-- ----------------------------
-- Records of think_strategy_combo
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_combo_item
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_combo_item`;
CREATE TABLE `think_strategy_combo_item` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `combo_id` int unsigned NOT NULL COMMENT '组合ID',
  `instance_id` int unsigned NOT NULL COMMENT '策略实例ID',
  `weight` decimal(5,2) NOT NULL DEFAULT '1.00' COMMENT '权重(0-10)',
  `role` varchar(20) DEFAULT 'signal' COMMENT '角色: signal=信号源 filter=过滤器 confirm=确认器',
  `sort` int unsigned NOT NULL DEFAULT '0' COMMENT '排序',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标记',
  PRIMARY KEY (`id`),
  KEY `idx_combo_id` (`combo_id`),
  KEY `idx_instance_id` (`instance_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略组合项表';

-- ----------------------------
-- Records of think_strategy_combo_item
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_combo_signal
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_combo_signal`;
CREATE TABLE `think_strategy_combo_signal` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `combo_id` int unsigned NOT NULL COMMENT '组合ID',
  `symbol` varchar(20) NOT NULL COMMENT '交易对',
  `signal_type` varchar(20) NOT NULL COMMENT '信号类型',
  `signal_data` text COMMENT '信号详情JSON',
  `source_signals` text COMMENT '来源信号JSON',
  `combined_confidence` int unsigned DEFAULT '0' COMMENT '综合置信度',
  `vote_count` int unsigned DEFAULT '0' COMMENT '投票数',
  `total_weight` decimal(10,2) DEFAULT '0.00' COMMENT '总权重',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态: 1=待处理 2=已执行 3=已忽略',
  `result` tinyint unsigned DEFAULT NULL COMMENT '结果: 1=盈利 2=亏损 3=持平',
  `profit` decimal(20,8) DEFAULT NULL COMMENT '盈亏金额',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标记',
  PRIMARY KEY (`id`),
  KEY `idx_combo_id` (`combo_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略组合信号日志';

-- ----------------------------
-- Records of think_strategy_combo_signal
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_instance
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_instance`;
CREATE TABLE `think_strategy_instance` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `strategy_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略模板ID',
  `name` varchar(100) NOT NULL DEFAULT '' COMMENT '实例名称',
  `alias` varchar(100) DEFAULT NULL COMMENT '策略别名（面向商户/用户）',
  `description` varchar(500) DEFAULT '' COMMENT '策略介绍',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `timeframe` varchar(10) NOT NULL DEFAULT '1h' COMMENT '周期：1m/5m/15m/1h/4h/1d',
  `exchange` varchar(20) NOT NULL DEFAULT 'binance' COMMENT '交易所',
  `mode` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '模式：1=自动交易 2=只发信号',
  `config` text COMMENT '运行时配置JSON（覆盖模板）',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1=运行中 2=暂停 3=停止',
  `last_check_time` int unsigned NOT NULL DEFAULT '0' COMMENT '上次检查时间',
  `last_signal_time` int unsigned NOT NULL DEFAULT '0' COMMENT '上次信号时间',
  `total_signals` int unsigned NOT NULL DEFAULT '0' COMMENT '总信号数',
  `total_trades` int unsigned NOT NULL DEFAULT '0' COMMENT '总交易数',
  `total_profit` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总盈亏',
  `win_count` int unsigned NOT NULL DEFAULT '0' COMMENT '盈利次数',
  `loss_count` int unsigned NOT NULL DEFAULT '0' COMMENT '亏损次数',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '删除标记',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '创建人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_strategy_id` (`strategy_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_status` (`status`),
  KEY `idx_mark` (`mark`),
  KEY `idx_member_id` (`member_id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略运行实例表';

-- ----------------------------
-- Records of think_strategy_instance
-- ----------------------------
BEGIN;
INSERT INTO `think_strategy_instance` (`id`, `strategy_id`, `name`, `alias`, `description`, `symbol`, `timeframe`, `exchange`, `mode`, `config`, `status`, `last_check_time`, `last_signal_time`, `total_signals`, `total_trades`, `total_profit`, `win_count`, `loss_count`, `member_id`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (11, 3, 'BTC对冲-稳健', '磐石稳健-BTC', '稳如磐石，守护财富 | 低风险稳健增值 | 2倍杠杆精准狙击 | 年化收益24-48% | 适合追求长期稳定的智慧投资者', 'BTC/USDT', '1h', 'binance', 1, '{\"leverage\":2,\"position_pct\":25,\"min_capital\":200,\"stop_loss_pct\":1.5,\"take_profit_pct\":3,\"boll_period\":20,\"boll_std\":2,\"hedge_ratio\":1,\"trailing_enabled\":false}', 1, 1770130800, 0, 0, 0, 0.00000000, 0, 0, 0, 1, 0, 1770113148, 0, 1770113148);
INSERT INTO `think_strategy_instance` (`id`, `strategy_id`, `name`, `alias`, `description`, `symbol`, `timeframe`, `exchange`, `mode`, `config`, `status`, `last_check_time`, `last_signal_time`, `total_signals`, `total_trades`, `total_profit`, `win_count`, `loss_count`, `member_id`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (12, 3, 'BTC对冲-平衡', '乾坤均衡-BTC', '攻守兼备，乾坤在握 | 中等风险均衡收益 | 3倍杠杆进可攻退可守 | 年化收益48-84% | 适合追求稳中有升的进取型投资者', 'BTC/USDT', '1h', 'binance', 1, '{\"leverage\":3,\"position_pct\":20,\"min_capital\":200,\"stop_loss_pct\":2,\"take_profit_pct\":4,\"boll_period\":20,\"boll_std\":2,\"hedge_ratio\":1,\"trailing_enabled\":false}', 1, 1770130800, 0, 0, 0, 0.00000000, 0, 0, 0, 1, 0, 1770113148, 0, 1770113148);
INSERT INTO `think_strategy_instance` (`id`, `strategy_id`, `name`, `alias`, `description`, `symbol`, `timeframe`, `exchange`, `mode`, `config`, `status`, `last_check_time`, `last_signal_time`, `total_signals`, `total_trades`, `total_profit`, `win_count`, `loss_count`, `member_id`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (13, 3, 'BTC对冲-激进', '雷霆激进-BTC', '雷霆万钧，势不可挡 | 高收益激进策略 | 5倍杠杆捕捉大行情 | 智能移动止盈 | 年化收益72-144% | 适合风险承受力强的勇者', 'BTC/USDT', '1h', 'binance', 1, '{\"leverage\":5,\"position_pct\":15,\"min_capital\":200,\"stop_loss_pct\":2.5,\"take_profit_pct\":6,\"boll_period\":20,\"boll_std\":2,\"hedge_ratio\":1,\"trailing_enabled\":true,\"trailing_activation_pct\":3,\"trailing_callback_pct\":1}', 1, 1770130800, 0, 0, 0, 0.00000000, 0, 0, 0, 1, 0, 1770113148, 0, 1770113148);
INSERT INTO `think_strategy_instance` (`id`, `strategy_id`, `name`, `alias`, `description`, `symbol`, `timeframe`, `exchange`, `mode`, `config`, `status`, `last_check_time`, `last_signal_time`, `total_signals`, `total_trades`, `total_profit`, `win_count`, `loss_count`, `member_id`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (14, 3, 'ETH对冲-稳健', '守护稳健-ETH', '守护者联盟，ETH稳健首选 | 低风险稳健增值 | 2倍杠杆精准布局 | 年化收益24-48% | 以太坊长期持有者的明智之选', 'ETH/USDT', '1h', 'binance', 1, '{\"leverage\":2,\"position_pct\":25,\"min_capital\":200,\"stop_loss_pct\":2,\"take_profit_pct\":4,\"boll_period\":20,\"boll_std\":2,\"hedge_ratio\":1,\"trailing_enabled\":false}', 1, 1770130800, 1770130800, 2, 0, 0.00000000, 0, 0, 0, 1, 0, 1770113148, 0, 1770113148);
INSERT INTO `think_strategy_instance` (`id`, `strategy_id`, `name`, `alias`, `description`, `symbol`, `timeframe`, `exchange`, `mode`, `config`, `status`, `last_check_time`, `last_signal_time`, `total_signals`, `total_trades`, `total_profit`, `win_count`, `loss_count`, `member_id`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (15, 3, 'ETH对冲-平衡', '天平均衡-ETH', '天平之道，平衡致胜 | 中等风险均衡策略 | 3倍杠杆攻守平衡 | 年化收益48-84% | ETH多空双向获利', 'ETH/USDT', '1h', 'binance', 1, '{\"leverage\":3,\"position_pct\":20,\"min_capital\":200,\"stop_loss_pct\":2.5,\"take_profit_pct\":5,\"boll_period\":20,\"boll_std\":2,\"hedge_ratio\":1,\"trailing_enabled\":false}', 1, 1770130807, 1770130807, 2, 0, 0.00000000, 0, 0, 0, 1, 0, 1770113148, 0, 1770113148);
INSERT INTO `think_strategy_instance` (`id`, `strategy_id`, `name`, `alias`, `description`, `symbol`, `timeframe`, `exchange`, `mode`, `config`, `status`, `last_check_time`, `last_signal_time`, `total_signals`, `total_trades`, `total_profit`, `win_count`, `loss_count`, `member_id`, `mark`, `create_user`, `create_time`, `update_user`, `update_time`) VALUES (16, 3, 'ETH对冲-激进', '风暴激进-ETH', '风暴来袭，收割行情 | 高收益激进策略 | 5倍杠杆全力出击 | 智能追踪止盈 | 年化收益72-144% | 敢于乘风破浪的弄潮儿', 'ETH/USDT', '1h', 'binance', 1, '{\"leverage\":5,\"position_pct\":15,\"min_capital\":200,\"stop_loss_pct\":3,\"take_profit_pct\":8,\"boll_period\":20,\"boll_std\":2,\"hedge_ratio\":1,\"trailing_enabled\":true,\"trailing_activation_pct\":3,\"trailing_callback_pct\":1}', 1, 1770130815, 1770130815, 2, 0, 0.00000000, 0, 0, 0, 1, 0, 1770113148, 0, 1770113148);
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_optimize_task
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_optimize_task`;
CREATE TABLE `think_strategy_optimize_task` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `strategy_id` int unsigned NOT NULL,
  `symbol` varchar(50) NOT NULL,
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `parameters` json DEFAULT NULL,
  `optimize_target` varchar(20) DEFAULT 'sharpe',
  `method` varchar(20) DEFAULT 'grid',
  `total_combinations` int DEFAULT '0',
  `completed_combinations` int DEFAULT '0',
  `best_params` json DEFAULT NULL,
  `best_score` decimal(20,4) DEFAULT '0.0000',
  `results` json DEFAULT NULL,
  `status` tinyint DEFAULT '1',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略优化任务表';

-- ----------------------------
-- Records of think_strategy_optimize_task
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_performance
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_performance`;
CREATE TABLE `think_strategy_performance` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `instance_id` int unsigned NOT NULL COMMENT '策略实例ID',
  `period_type` varchar(10) NOT NULL COMMENT '周期类型: day/week/month',
  `period_date` date NOT NULL COMMENT '周期日期',
  `total_signals` int unsigned NOT NULL DEFAULT '0' COMMENT '总信号数',
  `long_signals` int unsigned NOT NULL DEFAULT '0' COMMENT '做多信号数',
  `short_signals` int unsigned NOT NULL DEFAULT '0' COMMENT '做空信号数',
  `win_count` int unsigned NOT NULL DEFAULT '0' COMMENT '盈利次数',
  `loss_count` int unsigned NOT NULL DEFAULT '0' COMMENT '亏损次数',
  `total_profit` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总盈亏',
  `max_profit` decimal(20,8) DEFAULT '0.00000000' COMMENT '最大单笔盈利',
  `max_loss` decimal(20,8) DEFAULT '0.00000000' COMMENT '最大单笔亏损',
  `win_rate` decimal(5,2) DEFAULT '0.00' COMMENT '胜率',
  `profit_factor` decimal(10,2) DEFAULT '0.00' COMMENT '盈亏比',
  `avg_confidence` decimal(5,2) DEFAULT '0.00' COMMENT '平均置信度',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_instance_period` (`instance_id`,`period_type`,`period_date`),
  KEY `idx_period_date` (`period_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略绩效快照表';

-- ----------------------------
-- Records of think_strategy_performance
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_risk_package
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_risk_package`;
CREATE TABLE `think_strategy_risk_package` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '风控包名称',
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '风控包代码',
  `type` tinyint(1) NOT NULL DEFAULT '1' COMMENT '类型 1激進 2保守',
  `max_position_ratio` decimal(5,2) NOT NULL DEFAULT '50.00' COMMENT '最大仓位比例(%)',
  `max_leverage` int NOT NULL DEFAULT '10' COMMENT '最大杠杆',
  `stop_loss_ratio` decimal(5,2) NOT NULL DEFAULT '5.00' COMMENT '止损比例(%)',
  `take_profit_ratio` decimal(5,2) NOT NULL DEFAULT '10.00' COMMENT '止盈比例(%)',
  `daily_loss_limit` decimal(5,2) NOT NULL DEFAULT '10.00' COMMENT '每日亏损限制(%)',
  `max_orders_per_day` int NOT NULL DEFAULT '10' COMMENT '每日最大订单数',
  `max_order_amount` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '单笔最大金额',
  `min_order_amount` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT '单笔最小金额',
  `cool_down_minutes` int NOT NULL DEFAULT '5' COMMENT '冷却时间(分钟)',
  `config` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '扩展配置(JSON)',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态 1启用 2停用',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '备注',
  `sort` int NOT NULL DEFAULT '0' COMMENT '排序',
  `create_user` int NOT NULL DEFAULT '0' COMMENT '创建人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标识',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_code` (`code`) USING BTREE,
  KEY `idx_type` (`type`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='策略风控包表';

-- ----------------------------
-- Records of think_strategy_risk_package
-- ----------------------------
BEGIN;
INSERT INTO `think_strategy_risk_package` (`id`, `name`, `code`, `type`, `max_position_ratio`, `max_leverage`, `stop_loss_ratio`, `take_profit_ratio`, `daily_loss_limit`, `max_orders_per_day`, `max_order_amount`, `min_order_amount`, `cool_down_minutes`, `config`, `status`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, '激进型风控', 'aggressive', 1, 80.00, 100, 10.00, 30.00, 15.00, 50, 0.00, 0.00, 5, NULL, 1, '', 1, 0, 0, 0, 0, 1);
INSERT INTO `think_strategy_risk_package` (`id`, `name`, `code`, `type`, `max_position_ratio`, `max_leverage`, `stop_loss_ratio`, `take_profit_ratio`, `daily_loss_limit`, `max_orders_per_day`, `max_order_amount`, `min_order_amount`, `cool_down_minutes`, `config`, `status`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (5, '保守型风控', 'conservative', 2, 30.00, 5, 3.00, 8.00, 5.00, 5, 0.00, 0.00, 5, NULL, 1, '', 2, 0, 0, 0, 0, 1);
INSERT INTO `think_strategy_risk_package` (`id`, `name`, `code`, `type`, `max_position_ratio`, `max_leverage`, `stop_loss_ratio`, `take_profit_ratio`, `daily_loss_limit`, `max_orders_per_day`, `max_order_amount`, `min_order_amount`, `cool_down_minutes`, `config`, `status`, `remark`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (6, '平衡型风控', 'balanced', 1, 50.00, 20, 5.00, 15.00, 10.00, 20, 0.00, 0.00, 5, NULL, 1, '', 3, 0, 0, 0, 0, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_signal_log
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_signal_log`;
CREATE TABLE `think_strategy_signal_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `instance_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略实例ID',
  `strategy_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略模板ID',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `timeframe` varchar(10) NOT NULL DEFAULT '' COMMENT '周期',
  `signal_type` varchar(20) NOT NULL DEFAULT '' COMMENT '信号类型：open_long/open_short/close_long/close_short',
  `signal_source` varchar(30) NOT NULL DEFAULT '' COMMENT '信号来源：smc_ob/smc_fvg/ma_cross/ma_retest',
  `entry_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '入场价格',
  `stop_loss` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '止损价格',
  `take_profit` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '止盈价格',
  `confidence` int NOT NULL DEFAULT '0' COMMENT '置信度(1-100)',
  `reason` text COMMENT '信号原因描述',
  `indicators` text COMMENT '指标快照JSON',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1=待处理 2=已执行 3=已忽略 4=已过期',
  `executed_time` int unsigned NOT NULL DEFAULT '0' COMMENT '执行时间',
  `executed_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '执行价格',
  `order_id` varchar(100) NOT NULL DEFAULT '' COMMENT '关联订单ID',
  `pnl` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '盈亏',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `hedge_group_id` varchar(50) DEFAULT '' COMMENT '对冲组ID',
  PRIMARY KEY (`id`),
  KEY `idx_instance_id` (`instance_id`),
  KEY `idx_strategy_id` (`strategy_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_signal_type` (`signal_type`),
  KEY `idx_status` (`status`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略信号日志表';

-- ----------------------------
-- Records of think_strategy_signal_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_subscription
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_subscription`;
CREATE TABLE `think_strategy_subscription` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL,
  `strategy_id` int unsigned NOT NULL,
  `marketplace_id` int unsigned DEFAULT '0',
  `status` tinyint DEFAULT '1',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_member_strategy` (`member_id`,`strategy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略订阅表';

-- ----------------------------
-- Records of think_strategy_subscription
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_strategy_symbol_perf
-- ----------------------------
DROP TABLE IF EXISTS `think_strategy_symbol_perf`;
CREATE TABLE `think_strategy_symbol_perf` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `instance_id` int unsigned NOT NULL COMMENT '策略实例ID',
  `symbol` varchar(20) NOT NULL COMMENT '交易对',
  `total_signals` int unsigned NOT NULL DEFAULT '0' COMMENT '总信号数',
  `win_count` int unsigned NOT NULL DEFAULT '0' COMMENT '盈利次数',
  `loss_count` int unsigned NOT NULL DEFAULT '0' COMMENT '亏损次数',
  `total_profit` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '总盈亏',
  `win_rate` decimal(5,2) DEFAULT '0.00' COMMENT '胜率',
  `avg_profit` decimal(20,8) DEFAULT '0.00000000' COMMENT '平均盈亏',
  `last_signal_time` int unsigned DEFAULT NULL COMMENT '最后信号时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_instance_symbol` (`instance_id`,`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='策略交易对绩效表';

-- ----------------------------
-- Records of think_strategy_symbol_perf
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_symbol_config
-- ----------------------------
DROP TABLE IF EXISTS `think_symbol_config`;
CREATE TABLE `think_symbol_config` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `symbol` varchar(30) NOT NULL DEFAULT '' COMMENT '交易对',
  `exchange` varchar(20) DEFAULT 'binance' COMMENT '交易所',
  `base_asset` varchar(20) DEFAULT '' COMMENT '基础资产',
  `quote_asset` varchar(20) DEFAULT '' COMMENT '计价资产',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态:1启用 0禁用',
  `is_whitelist` tinyint DEFAULT '0' COMMENT '是否白名单(优先交易)',
  `is_blacklist` tinyint DEFAULT '0' COMMENT '是否黑名单(禁止交易)',
  `max_leverage` int DEFAULT '125' COMMENT '最大杠杆',
  `default_leverage` int DEFAULT '20' COMMENT '默认杠杆',
  `max_position_value` decimal(20,2) DEFAULT '0.00' COMMENT '最大持仓金额(0=不限)',
  `max_order_value` decimal(20,2) DEFAULT '0.00' COMMENT '单笔最大金额(0=不限)',
  `min_order_value` decimal(20,2) DEFAULT '10.00' COMMENT '单笔最小金额',
  `price_precision` int DEFAULT '2' COMMENT '价格精度',
  `qty_precision` int DEFAULT '3' COMMENT '数量精度',
  `min_qty` decimal(20,8) DEFAULT '0.00100000' COMMENT '最小数量',
  `maker_fee` decimal(10,6) DEFAULT '0.000200' COMMENT 'Maker费率',
  `taker_fee` decimal(10,6) DEFAULT '0.000500' COMMENT 'Taker费率',
  `risk_level` tinyint DEFAULT '1' COMMENT '风险等级:1低 2中 3高',
  `volatility_limit` decimal(10,2) DEFAULT '0.00' COMMENT '波动率限制(%)(0=不限)',
  `trade_time_enabled` tinyint DEFAULT '0' COMMENT '是否启用交易时间限制',
  `trade_time_start` time DEFAULT NULL COMMENT '交易开始时间',
  `trade_time_end` time DEFAULT NULL COMMENT '交易结束时间',
  `note` varchar(500) DEFAULT '' COMMENT '备注',
  `sort` int DEFAULT '0' COMMENT '排序',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_symbol` (`symbol`,`exchange`),
  KEY `idx_status` (`status`),
  KEY `idx_whitelist` (`is_whitelist`),
  KEY `idx_blacklist` (`is_blacklist`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='交易对配置表';

-- ----------------------------
-- Records of think_symbol_config
-- ----------------------------
BEGIN;
INSERT INTO `think_symbol_config` (`id`, `symbol`, `exchange`, `base_asset`, `quote_asset`, `status`, `is_whitelist`, `is_blacklist`, `max_leverage`, `default_leverage`, `max_position_value`, `max_order_value`, `min_order_value`, `price_precision`, `qty_precision`, `min_qty`, `maker_fee`, `taker_fee`, `risk_level`, `volatility_limit`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `note`, `sort`, `create_time`, `update_time`, `mark`) VALUES (1, 'BTCUSDT', 'binance', 'BTC', 'USDT', 1, 0, 0, 125, 20, 0.00, 0.00, 10.00, 2, 3, 0.00100000, 0.000200, 0.000500, 1, 0.00, 0, NULL, NULL, '', 0, 1769498592, 1769679251, 0);
INSERT INTO `think_symbol_config` (`id`, `symbol`, `exchange`, `base_asset`, `quote_asset`, `status`, `is_whitelist`, `is_blacklist`, `max_leverage`, `default_leverage`, `max_position_value`, `max_order_value`, `min_order_value`, `price_precision`, `qty_precision`, `min_qty`, `maker_fee`, `taker_fee`, `risk_level`, `volatility_limit`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `note`, `sort`, `create_time`, `update_time`, `mark`) VALUES (2, 'ETHUSDT', 'binance', 'ETH', 'USDT', 1, 0, 0, 100, 20, 0.00, 0.00, 10.00, 2, 3, 0.00100000, 0.000200, 0.000500, 1, 0.00, 0, NULL, NULL, '', 0, 1769498592, 1769498592, 1);
INSERT INTO `think_symbol_config` (`id`, `symbol`, `exchange`, `base_asset`, `quote_asset`, `status`, `is_whitelist`, `is_blacklist`, `max_leverage`, `default_leverage`, `max_position_value`, `max_order_value`, `min_order_value`, `price_precision`, `qty_precision`, `min_qty`, `maker_fee`, `taker_fee`, `risk_level`, `volatility_limit`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `note`, `sort`, `create_time`, `update_time`, `mark`) VALUES (3, 'BNBUSDT', 'binance', 'BNB', 'USDT', 1, 0, 0, 75, 10, 0.00, 0.00, 10.00, 2, 2, 0.01000000, 0.000200, 0.000500, 1, 0.00, 0, NULL, NULL, '', 0, 1769498592, 1769498592, 1);
INSERT INTO `think_symbol_config` (`id`, `symbol`, `exchange`, `base_asset`, `quote_asset`, `status`, `is_whitelist`, `is_blacklist`, `max_leverage`, `default_leverage`, `max_position_value`, `max_order_value`, `min_order_value`, `price_precision`, `qty_precision`, `min_qty`, `maker_fee`, `taker_fee`, `risk_level`, `volatility_limit`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `note`, `sort`, `create_time`, `update_time`, `mark`) VALUES (4, 'SOLUSDT', 'binance', 'SOL', 'USDT', 1, 0, 0, 50, 10, 0.00, 0.00, 10.00, 2, 1, 0.10000000, 0.000200, 0.000500, 2, 0.00, 0, NULL, NULL, '', 0, 1769498592, 1769498592, 1);
INSERT INTO `think_symbol_config` (`id`, `symbol`, `exchange`, `base_asset`, `quote_asset`, `status`, `is_whitelist`, `is_blacklist`, `max_leverage`, `default_leverage`, `max_position_value`, `max_order_value`, `min_order_value`, `price_precision`, `qty_precision`, `min_qty`, `maker_fee`, `taker_fee`, `risk_level`, `volatility_limit`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `note`, `sort`, `create_time`, `update_time`, `mark`) VALUES (5, 'XRPUSDT', 'binance', 'XRP', 'USDT', 1, 0, 0, 75, 10, 0.00, 0.00, 10.00, 4, 1, 1.00000000, 0.000200, 0.000500, 2, 0.00, 0, NULL, NULL, '', 0, 1769498592, 1769498592, 1);
INSERT INTO `think_symbol_config` (`id`, `symbol`, `exchange`, `base_asset`, `quote_asset`, `status`, `is_whitelist`, `is_blacklist`, `max_leverage`, `default_leverage`, `max_position_value`, `max_order_value`, `min_order_value`, `price_precision`, `qty_precision`, `min_qty`, `maker_fee`, `taker_fee`, `risk_level`, `volatility_limit`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `note`, `sort`, `create_time`, `update_time`, `mark`) VALUES (6, 'DOGEUSDT', 'binance', 'DOGE', 'USDT', 1, 0, 0, 50, 10, 0.00, 0.00, 10.00, 5, 0, 1.00000000, 0.000200, 0.000500, 3, 0.00, 0, NULL, NULL, '', 0, 1769498592, 1769498592, 1);
INSERT INTO `think_symbol_config` (`id`, `symbol`, `exchange`, `base_asset`, `quote_asset`, `status`, `is_whitelist`, `is_blacklist`, `max_leverage`, `default_leverage`, `max_position_value`, `max_order_value`, `min_order_value`, `price_precision`, `qty_precision`, `min_qty`, `maker_fee`, `taker_fee`, `risk_level`, `volatility_limit`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `note`, `sort`, `create_time`, `update_time`, `mark`) VALUES (7, 'ADAUSDT', 'binance', 'ADA', 'USDT', 1, 0, 0, 50, 10, 0.00, 0.00, 10.00, 4, 0, 1.00000000, 0.000200, 0.000500, 2, 0.00, 0, NULL, NULL, '', 0, 1769498592, 1769498592, 1);
INSERT INTO `think_symbol_config` (`id`, `symbol`, `exchange`, `base_asset`, `quote_asset`, `status`, `is_whitelist`, `is_blacklist`, `max_leverage`, `default_leverage`, `max_position_value`, `max_order_value`, `min_order_value`, `price_precision`, `qty_precision`, `min_qty`, `maker_fee`, `taker_fee`, `risk_level`, `volatility_limit`, `trade_time_enabled`, `trade_time_start`, `trade_time_end`, `note`, `sort`, `create_time`, `update_time`, `mark`) VALUES (8, 'AVAXUSDT', 'binance', 'AVAX', 'USDT', 1, 0, 0, 50, 10, 0.00, 0.00, 10.00, 2, 1, 0.10000000, 0.000200, 0.000500, 2, 0.00, 0, NULL, NULL, '', 0, 1769498592, 1769498592, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_system_alert
-- ----------------------------
DROP TABLE IF EXISTS `think_system_alert`;
CREATE TABLE `think_system_alert` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `type` varchar(50) DEFAULT 'system',
  `level` tinyint DEFAULT '1' COMMENT '1信息 2警告 3错误 4严重',
  `title` varchar(200) NOT NULL,
  `content` text,
  `source` varchar(50) DEFAULT '',
  `source_id` int unsigned DEFAULT '0',
  `member_id` int unsigned DEFAULT '0',
  `is_read` tinyint DEFAULT '0',
  `is_handled` tinyint DEFAULT '0',
  `handle_note` varchar(500) DEFAULT '',
  `handle_time` int unsigned DEFAULT '0',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_type` (`type`),
  KEY `idx_level` (`level`),
  KEY `idx_is_read` (`is_read`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统告警表';

-- ----------------------------
-- Records of think_system_alert
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_system_config
-- ----------------------------
DROP TABLE IF EXISTS `think_system_config`;
CREATE TABLE `think_system_config` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `config_group` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '配置分组',
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '配置键',
  `config_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '配置名称',
  `config_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '配置值',
  `value_type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '值类型：1字符串 2数值 3JSON 4布尔',
  `config_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'text' COMMENT '配置类型',
  `sort` smallint unsigned NOT NULL DEFAULT '125' COMMENT '排序',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2禁用',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `description` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '描述说明',
  `options` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '选项（JSON格式）',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_config_key` (`config_key`) USING BTREE,
  KEY `idx_group` (`config_group`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=224 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统配置扩展表';

-- ----------------------------
-- Records of think_system_config
-- ----------------------------
BEGIN;
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, 'system', 'position_sync', '持仓同步开关', 'test', 4, 'switch', 125, 1, '持仓同步开关：1开启 0关闭', '持仓同步开关：1开启 0关闭', NULL, 1, 1769168330, 1, 1769679227, 0);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, 'system', 'api_base_url', '交易所API基础地址（如需）', '', 1, 'text', 125, 1, '交易所API基础地址（如需）', '交易所API基础地址（如需）', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (10, 'system', 'order_retry_limit', '订单重试次数（默认）', '3', 2, 'number', 125, 1, '订单重试次数（默认）', '订单重试次数（默认）', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (12, 'security', 'two_factor_enabled', '2FA开关', '0', 4, 'switch', 125, 1, '2FA开关：1开启 0关闭', '2FA开关：1开启 0关闭', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (14, 'security', 'login_fail_limit', '登录失败次数限制', '5', 2, 'number', 125, 1, '登录失败次数限制', '登录失败次数限制', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (15, 'telegram', 'bot_token', 'Telegram Bot Token', '', 1, 'text', 125, 1, 'Telegram Bot Token', 'Telegram Bot Token', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (16, 'telegram', 'proxy', 'Telegram Proxy 配置', '', 1, 'text', 125, 1, 'Telegram Proxy 配置', 'Telegram Proxy 配置', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (18, 'follow', 'default_follow_type', '默认跟单类型', 'ratio', 1, 'text', 125, 1, '默认跟单类型：ratio/amount/all', '默认跟单类型：ratio/amount/all', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (19, 'follow', 'default_follow_ratio', '默认跟单比例', '1.0', 2, 'number', 125, 1, '默认跟单比例', '默认跟单比例', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (20, 'follow', 'max_follow_amount', '默认最大跟单金额', '10000', 2, 'number', 125, 1, '默认最大跟单金额', '默认最大跟单金额', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (21, 'trading', 'default_leverage', '默认杠杆倍数', '1', 2, 'number', 125, 1, '默认杠杆倍数', '默认杠杆倍数', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (22, 'trading', 'max_leverage', '最大杠杆倍数（默认）', '20', 2, 'number', 125, 1, '最大杠杆倍数（默认）', '最大杠杆倍数（默认）', NULL, 1, 1769168330, 1, 1769168330, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (25, 'follow_rule', 'min_follow_amount', '最小跟单金额（USDT）', '50', 2, 'number', 125, 1, '最小跟单金额（USDT）', '最小跟单金额（USDT）', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (28, 'follow_rule', 'max_follow_orders_per_day', '单日最大跟单单数', '200', 2, 'number', 125, 1, '单日最大跟单单数', '单日最大跟单单数', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (32, 'risk_account', 'max_drawdown', '账户最大回撤阈值', '0.30', 2, 'number', 125, 1, '账户最大回撤阈值', '账户最大回撤阈值', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (33, 'risk_account', 'max_position_ratio', '账户最大开仓比例', '0.80', 2, 'number', 125, 1, '账户最大开仓比例', '账户最大开仓比例', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (34, 'risk_account', 'max_daily_loss', '账户单日最大亏损比例', '0.20', 2, 'number', 125, 1, '账户单日最大亏损比例', '账户单日最大亏损比例', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (35, 'risk_strategy', 'max_single_loss', '单笔最大亏损比例', '0.05', 2, 'number', 125, 1, '单笔最大亏损比例', '单笔最大亏损比例', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (36, 'risk_strategy', 'max_position', '策略最大仓位比例', '0.50', 2, 'number', 125, 1, '策略最大仓位比例', '策略最大仓位比例', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (37, 'risk_strategy', 'max_consecutive_losses', '最大连续亏损次数', '5', 2, 'number', 125, 1, '最大连续亏损次数', '最大连续亏损次数', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (41, 'settlement', 'cycle', '结算周期', 'daily', 1, 'text', 125, 1, '结算周期：daily/weekly/monthly', '结算周期：daily/weekly/monthly', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (42, 'settlement', 'auto_generate', '自动生成结算单', '1', 4, 'switch', 125, 1, '自动生成结算单：1开启 0关闭', '自动生成结算单：1开启 0关闭', NULL, 1, 1769168668, 1, 1769168668, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (58, 'settlement_rule', 'company_share_ratio_default', '公司分成比例默认值', '0.20', 2, 'number', 125, 1, '公司分成比例默认值', '公司分成比例默认值', NULL, 1, 1769168820, 1, 1769168820, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (65, 'execution', 'max_retry', '下单最大重试次数', '3', 2, 'number', 125, 1, '下单最大重试次数', '下单最大重试次数', NULL, 1, 1769168820, 1, 1769168820, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (71, 'monitor', 'order_fail_rate', '订单失败率告警阈值', '0.05', 2, 'number', 125, 1, '订单失败率告警阈值', '订单失败率告警阈值', NULL, 1, 1769168820, 1, 1769168820, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (72, 'trading_pairs', 'whitelist', '交易对白名单（逗号分隔）', 'BTC/USDT,ETH/USDT', 1, 'text', 125, 1, '交易对白名单（逗号分隔）', '交易对白名单（逗号分隔）', NULL, 1, 1769168891, 1, 1769168891, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (73, 'trading_pairs', 'blacklist', '交易对黑名单（逗号分隔）', '', 1, 'text', 125, 1, '交易对黑名单（逗号分隔）', '交易对黑名单（逗号分隔）', NULL, 1, 1769168891, 1, 1769168891, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (80, 'api_access', 'signature_enabled', '接口签名校验开关', '1', 4, 'switch', 125, 1, '接口签名校验开关', '接口签名校验开关', NULL, 1, 1769168939, 1, 1769168939, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (81, 'api_access', 'ip_whitelist_enabled', '接口IP白名单开关', '0', 4, 'switch', 125, 1, '接口IP白名单开关', '接口IP白名单开关', NULL, 1, 1769168939, 1, 1769168939, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (83, 'api_access', 'nonce_expire_seconds', '签名nonce过期时间（秒）', '300', 2, 'number', 125, 1, '签名nonce过期时间（秒）', '签名nonce过期时间（秒）', NULL, 1, 1769168939, 1, 1769168939, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (93, 'asset_threshold', 'min_balance', '账户最低余额阈值（USDT）', '100', 2, 'number', 125, 1, '账户最低余额阈值（USDT）', '账户最低余额阈值（USDT）', NULL, 1, 1769169137, 1, 1769169137, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (95, 'asset_threshold', 'max_position_value', '单账户最大持仓价值（USDT）', '50000', 2, 'number', 125, 1, '单账户最大持仓价值（USDT）', '单账户最大持仓价值（USDT）', NULL, 1, 1769169137, 1, 1769169137, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (100, 'notify_rule', 'send_admin_on_overdraft', '燃料费透支通知管理员', '1', 4, 'switch', 125, 1, '燃料费透支通知管理员', '燃料费透支通知管理员', NULL, 1, 1769169197, 1, 1769169197, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (108, 'notify_rule', 'send_member_trade_alert', '交易告警通知会员', '1', 4, 'switch', 125, 1, '交易告警通知会员', '交易告警通知会员', NULL, 1, 1769169197, 1, 1769169197, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (109, 'queue', 'driver', '队列驱动', 'redis', 1, 'text', 125, 1, '队列驱动：redis/db', '队列驱动：redis/db', NULL, 1, 1769169338, 1, 1769169338, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (110, 'queue', 'retry_times', '任务重试次数', '3', 2, 'number', 125, 1, '任务重试次数', '任务重试次数', NULL, 1, 1769169338, 1, 1769169338, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (111, 'queue', 'timeout', '任务超时秒数', '60', 2, 'number', 125, 1, '任务超时秒数', '任务超时秒数', NULL, 1, 1769169338, 1, 1769169338, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (116, 'strategy_risk', 'trend_conservative', '趋势-保守风控包', '{\"max_drawdown\":0.08,\"max_position\":0.6,\"stop_loss\":0.05,\"take_profit\":0.15,\"max_consecutive_losses\":4}', 3, 'json', 125, 1, '趋势-保守风控包', '趋势-保守风控包', NULL, 1, 1769169467, 1, 1769169467, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (117, 'strategy_risk', 'trend_aggressive', '趋势-激进风控包', '{\"max_drawdown\":0.15,\"max_position\":0.8,\"stop_loss\":0.08,\"take_profit\":0.25,\"max_consecutive_losses\":6}', 3, 'json', 125, 1, '趋势-激进风控包', '趋势-激进风控包', NULL, 1, 1769169467, 1, 1769169467, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (185, 'monitor', 'task_timeout_seconds', '任务超时阈值(秒)', '60', 2, 'number', 125, 1, '任务超时阈值(秒)', '任务超时阈值(秒)', NULL, 1, 1769228617, 1, 1769228617, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (186, 'monitor', 'export_file_ttl_days', '导出文件保留天数', '7', 2, 'number', 125, 1, '导出文件保留天数', '导出文件保留天数', NULL, 1, 1769230276, 1, 1769230276, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (205, 'strategy', 'signal_notify_enabled', '策略信号通知开关', '1', 1, 'text', 125, 1, '策略信号通知开关', '策略信号通知开关', NULL, 0, 1769502878, 0, 0, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (208, 'basic', '1', '1', '1', 1, 'text', 0, 1, NULL, '1', '', 0, 1769524495, 0, 1769524501, 0);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (209, 'basic', 'site_name', '站点名称', 'QuantTrade', 1, 'text', 0, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (210, 'basic', 'site_logo', '站点Logo', '', 1, 'text', 10, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (211, 'trade', 'auto_close_position', '自动平仓', '1', 1, 'switch', 20, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (212, 'notify', 'telegram_bot_token', 'Telegram Bot Token', '', 1, 'password', 30, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (213, 'notify', 'telegram_chat_id', 'Telegram Chat ID', '', 1, 'text', 40, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (214, 'notify', 'notify_trade_open', '开仓通知', '1', 1, 'switch', 50, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (215, 'notify', 'notify_trade_close', '平仓通知', '1', 1, 'switch', 60, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (216, 'notify', 'notify_risk_alert', '风险预警通知', '1', 1, 'switch', 70, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (217, 'risk', 'risk_check_enabled', '启用风控检查', '1', 1, 'switch', 80, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (218, 'api', 'binance_api_url', 'Binance API URL', 'https://api.binance.com', 1, 'text', 90, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (219, 'api', 'api_timeout', 'API超时(秒)', '30', 1, 'number', 100, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (220, 'api', 'api_retry_times', 'API重试次数', '3', 1, 'number', 110, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (221, 'system', 'log_retention_days', '日志保留天数', '30', 1, 'number', 120, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (222, 'system', 'cache_enabled', '启用缓存', '1', 1, 'switch', 130, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
INSERT INTO `think_system_config` (`id`, `config_group`, `config_key`, `config_name`, `config_value`, `value_type`, `config_type`, `sort`, `status`, `remark`, `description`, `options`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (223, 'system', 'debug_mode', '调试模式', '0', 1, 'switch', 140, 1, NULL, NULL, NULL, 0, 1769672095, 0, 1769672095, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_system_monitor
-- ----------------------------
DROP TABLE IF EXISTS `think_system_monitor`;
CREATE TABLE `think_system_monitor` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '监控类型',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '监控项名称',
  `value` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '当前值',
  `unit` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '单位',
  `threshold` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '阈值',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态 1正常 0异常',
  `last_check_time` int unsigned NOT NULL DEFAULT '0' COMMENT '最后检查时间',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '标识',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_type` (`type`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统监控表';

-- ----------------------------
-- Records of think_system_monitor
-- ----------------------------
BEGIN;
INSERT INTO `think_system_monitor` (`id`, `type`, `name`, `value`, `unit`, `threshold`, `status`, `last_check_time`, `create_time`, `mark`) VALUES (1, 'server', 'CPU使用率', '9.58%', '%', '>80', 1, 1769679240, 1769264085, 1);
INSERT INTO `think_system_monitor` (`id`, `type`, `name`, `value`, `unit`, `threshold`, `status`, `last_check_time`, `create_time`, `mark`) VALUES (2, 'server', '内存使用率', '1.56%', '%', '>85', 1, 1769679240, 1769264085, 1);
INSERT INTO `think_system_monitor` (`id`, `type`, `name`, `value`, `unit`, `threshold`, `status`, `last_check_time`, `create_time`, `mark`) VALUES (3, 'server', '磁盘使用率', '11.73%', '%', '>90', 1, 1769679240, 1769264085, 1);
INSERT INTO `think_system_monitor` (`id`, `type`, `name`, `value`, `unit`, `threshold`, `status`, `last_check_time`, `create_time`, `mark`) VALUES (4, 'database', '数据库连接数', '4', '个', '>100', 1, 1769679240, 1769264085, 1);
INSERT INTO `think_system_monitor` (`id`, `type`, `name`, `value`, `unit`, `threshold`, `status`, `last_check_time`, `create_time`, `mark`) VALUES (5, 'database', '查询QPS', '91', '次/秒', '>1000', 1, 1769679240, 1769264085, 1);
INSERT INTO `think_system_monitor` (`id`, `type`, `name`, `value`, `unit`, `threshold`, `status`, `last_check_time`, `create_time`, `mark`) VALUES (6, 'exchange', 'API调用次数', '2', '次', '>10000', 1, 1769679240, 1769264085, 1);
INSERT INTO `think_system_monitor` (`id`, `type`, `name`, `value`, `unit`, `threshold`, `status`, `last_check_time`, `create_time`, `mark`) VALUES (7, 'queue', '队列待处理数', '0', '个', '>1000', 1, 1769679240, 1769264085, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_task_queue
-- ----------------------------
DROP TABLE IF EXISTS `think_task_queue`;
CREATE TABLE `think_task_queue` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务ID',
  `job_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务类型',
  `payload` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '任务数据(JSON)',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1待处理 2处理中 3成功 4失败',
  `retry_count` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '重试次数',
  `max_retry` tinyint unsigned NOT NULL DEFAULT '3' COMMENT '最大重试次数',
  `next_retry_time` int unsigned NOT NULL DEFAULT '0' COMMENT '下次重试时间',
  `start_time` int unsigned NOT NULL DEFAULT '0' COMMENT '开始处理时间',
  `finish_time` int unsigned NOT NULL DEFAULT '0' COMMENT '完成时间',
  `duration_ms` int unsigned NOT NULL DEFAULT '0' COMMENT '处理耗时(ms)',
  `error_msg` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '错误信息',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_task_id` (`task_id`) USING BTREE,
  KEY `idx_job_type` (`job_type`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_next_retry_time` (`next_retry_time`) USING BTREE,
  KEY `idx_start_time` (`start_time`) USING BTREE,
  KEY `idx_finish_time` (`finish_time`) USING BTREE,
  KEY `idx_create_time` (`create_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='任务队列表';

-- ----------------------------
-- Records of think_task_queue
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_task_queue_stats
-- ----------------------------
DROP TABLE IF EXISTS `think_task_queue_stats`;
CREATE TABLE `think_task_queue_stats` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `job_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务类型',
  `stat_date` date NOT NULL COMMENT '统计日期',
  `total_count` int unsigned NOT NULL DEFAULT '0' COMMENT '任务数量',
  `avg_ms` int unsigned NOT NULL DEFAULT '0' COMMENT '平均耗时(ms)',
  `max_ms` int unsigned NOT NULL DEFAULT '0' COMMENT '最大耗时(ms)',
  `min_ms` int unsigned NOT NULL DEFAULT '0' COMMENT '最小耗时(ms)',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_job_date` (`job_type`,`stat_date`) USING BTREE,
  KEY `idx_stat_date` (`stat_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='任务耗时统计表';

-- ----------------------------
-- Records of think_task_queue_stats
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_telegram_template
-- ----------------------------
DROP TABLE IF EXISTS `think_telegram_template`;
CREATE TABLE `think_telegram_template` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `template_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板代码',
  `template_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板名称',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'system_alert' COMMENT '模板类型',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '模板内容',
  `variables` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '变量说明(JSON)',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2禁用',
  `sort` smallint unsigned NOT NULL DEFAULT '125' COMMENT '排序',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_template_code` (`template_code`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Telegram消息模板表';

-- ----------------------------
-- Records of think_telegram_template
-- ----------------------------
BEGIN;
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, 'FUEL_WARNING_ADMIN', '燃料费警告-管理员', 'system_alert', '【燃料费预警】会员{member_id} 燃料费余额 {fuel_balance} USDT 低于阈值 {threshold} USDT', '{\"member_id\":\"会员ID\",\"fuel_balance\":\"燃料费余额\",\"threshold\":\"阈值\"}', 1, 10, 1, 1769228356, 1, 1769679223, 0);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (2, 'FUEL_WARNING_AGENT', '燃料费警告-代理商', 'system_alert', '【燃料费预警】代理商{agent_id} 会员{member_id} 燃料费余额 {fuel_balance} USDT 低于阈值 {threshold} USDT', '{\"agent_id\":\"代理商ID\",\"member_id\":\"会员ID\",\"fuel_balance\":\"燃料费余额\",\"threshold\":\"阈值\"}', 1, 20, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (3, 'FUEL_WARNING_MEMBER', '燃料费警告-会员', 'system_alert', '【燃料费预警】您的燃料费余额 {fuel_balance} USDT 低于阈值 {threshold} USDT，请及时充值', '{\"fuel_balance\":\"燃料费余额\",\"threshold\":\"阈值\"}', 1, 30, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (4, 'FUEL_OVERDRAFT_ADMIN', '燃料费透支-管理员', 'system_alert', '【燃料费透支】会员{member_id} 已透支，余额 {fuel_balance} USDT', '{\"member_id\":\"会员ID\",\"fuel_balance\":\"燃料费余额\"}', 1, 40, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (5, 'TRADING_PAUSED_ADMIN', '交易暂停-管理员', 'system_alert', '【交易暂停】会员{member_id} 已暂停交易，原因：{reason}', '{\"member_id\":\"会员ID\",\"reason\":\"原因\"}', 1, 50, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (6, 'TRADING_RESUMED_MEMBER', '交易恢复-会员', 'system_alert', '【交易恢复】您的交易已恢复', '{}', 1, 60, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (7, 'DEPOSIT_NOTICE_ADMIN', '充值通知-管理员', 'system_alert', '【充值通知】会员{member_id} 充值 {amount} {symbol}', '{\"member_id\":\"会员ID\",\"amount\":\"充值金额\",\"symbol\":\"币种\"}', 1, 70, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (8, 'DEPOSIT_NOTICE_AGENT', '充值通知-代理商', 'system_alert', '【充值通知】代理商{agent_id} 会员{member_id} 充值 {amount} {symbol}', '{\"agent_id\":\"代理商ID\",\"member_id\":\"会员ID\",\"amount\":\"充值金额\",\"symbol\":\"币种\"}', 1, 80, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (9, 'PROFIT_SHARE_ADMIN', '利润分成-管理员', 'system_alert', '【利润分成】会员{member_id} 本期利润 {profit} USDT，公司分成 {company_share} USDT', '{\"member_id\":\"会员ID\",\"profit\":\"利润\",\"company_share\":\"公司分成\"}', 1, 90, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (10, 'TRADE_INFO_MEMBER', '交易信息-会员', 'system_alert', '【交易信息】{symbol} {side} {quantity} @ {price} 状态：{status}', '{\"symbol\":\"交易对\",\"side\":\"方向\",\"quantity\":\"数量\",\"price\":\"价格\",\"status\":\"状态\"}', 1, 100, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (11, 'TRADE_SUMMARY_MEMBER', '交易摘要-会员', 'system_alert', '【交易摘要】今日交易 {trade_count} 笔，收益 {profit} USDT', '{\"trade_count\":\"交易笔数\",\"profit\":\"收益\"}', 1, 110, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (12, 'TRADE_ALERT_MEMBER', '交易告警-会员', 'system_alert', '【交易告警】{symbol} 触发{alert_type}，当前价格 {price}', '{\"symbol\":\"交易对\",\"alert_type\":\"告警类型\",\"price\":\"价格\"}', 1, 120, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (13, 'TASK_TIMEOUT_ADMIN', '任务超时-管理员', 'system_alert', '【任务超时】任务类型{job_type} 超时数量 {count}，超时时间 {timeout}s', '{\"job_type\":\"任务类型\",\"count\":\"超时数量\",\"timeout\":\"超时时间\"}', 1, 130, 1, 1769228356, 1, 1769228356, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (14, 'EXPORT_DOWNLOAD_ALERT_ADMIN', '导出下载告警-管理员', 'system_alert', '【导出下载告警】{window}分钟内失败{count}次，最近文件:{filename}，原因:{reason}', '{\"window\":\"统计窗口(分钟)\",\"count\":\"失败次数\",\"filename\":\"文件名\",\"reason\":\"原因\"}', 1, 140, 1, 1769230276, 1, 1769230276, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (16, 'STRATEGY_SIGNAL_LONG', '策略做多信号', 'strategy_signal', '🤖 *策略信号通知*\n\n📈 *做多信号*\n━━━━━━━━━━━━━━━\n交易对: `{symbol}`\n周期: `{timeframe}`\n入场价: `{entry_price}`\n止损价: `{stop_loss}`\n止盈价: `{take_profit}`\n置信度: `{confidence}%`\n来源: `{source}`\n━━━━━━━━━━━━━━━\n📝 原因: {reason}\n━━━━━━━━━━━━━━━\n⏰ {time}', 'symbol,timeframe,entry_price,stop_loss,take_profit,confidence,source,reason,time', 1, 200, 0, 1769502796, 0, 0, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (17, 'STRATEGY_SIGNAL_SHORT', '策略做空信号', 'strategy_signal', '🤖 *策略信号通知*\n\n📉 *做空信号*\n━━━━━━━━━━━━━━━\n交易对: `{symbol}`\n周期: `{timeframe}`\n入场价: `{entry_price}`\n止损价: `{stop_loss}`\n止盈价: `{take_profit}`\n置信度: `{confidence}%`\n来源: `{source}`\n━━━━━━━━━━━━━━━\n📝 原因: {reason}\n━━━━━━━━━━━━━━━\n⏰ {time}', 'symbol,timeframe,entry_price,stop_loss,take_profit,confidence,source,reason,time', 1, 201, 0, 1769502796, 0, 0, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (18, 'STRATEGY_SIGNAL_CLOSE', '策略平仓信号', 'strategy_signal', '🤖 *策略信号通知*\n\n🔔 *平仓信号*\n━━━━━━━━━━━━━━━\n交易对: `{symbol}`\n方向: `{direction}`\n周期: `{timeframe}`\n平仓价: `{entry_price}`\n置信度: `{confidence}%`\n来源: `{source}`\n━━━━━━━━━━━━━━━\n📝 原因: {reason}\n━━━━━━━━━━━━━━━\n⏰ {time}', 'symbol,direction,timeframe,entry_price,confidence,source,reason,time', 1, 202, 0, 1769502796, 0, 0, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (19, 'STRATEGY_DAILY_SUMMARY', '策略日报', 'strategy_report', '📊 *策略执行日报*\n\n📅 日期: `{date}`\n━━━━━━━━━━━━━━━\n✅ 执行实例: `{instance_count}` 个\n📡 产生信号: `{signal_count}` 个\n🎯 做多信号: `{long_count}` 个  \n📉 做空信号: `{short_count}` 个\n🔔 平仓信号: `{close_count}` 个\n━━━━━━━━━━━━━━━\n💡 活跃策略:\n{active_strategies}\n━━━━━━━━━━━━━━━\n⏰ 生成时间: {time}', 'date,instance_count,signal_count,long_count,short_count,close_count,active_strategies,time', 1, 210, 0, 1769502796, 0, 0, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (20, 'trade_signal_open', '开仓信号通知', 'trade_signal', '🔔 <b>开仓信号</b>\n\n交易对: {symbol}\n方向: {side}\n价格: {price}\n数量: {quantity}\n带单员: {leader_name}\n\n时间: {time}', NULL, 1, 0, 0, 1769674181, 0, 1769674181, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (21, 'trade_signal_close', '平仓信号通知', 'trade_signal', '✅ <b>平仓信号</b>\n\n交易对: {symbol}\n方向: {side}\n价格: {price}\n数量: {quantity}\n盈亏: {pnl}\n\n时间: {time}', NULL, 1, 0, 0, 1769674181, 0, 1769674181, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (22, 'position_profit_alert', '持仓盈利预警', 'position_alert', '💰 <b>持仓盈利预警</b>\n\n交易对: {symbol}\n方向: {position_side}\n入场价: {entry_price}\n当前价: {current_price}\n盈利: +{pnl} ({pnl_percent}%)\n\n时间: {time}', NULL, 1, 0, 0, 1769674181, 0, 1769674181, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (23, 'position_loss_alert', '持仓亏损预警', 'position_alert', '⚠️ <b>持仓亏损预警</b>\n\n交易对: {symbol}\n方向: {position_side}\n入场价: {entry_price}\n当前价: {current_price}\n亏损: {pnl} ({pnl_percent}%)\n\n时间: {time}', NULL, 1, 0, 0, 1769674181, 0, 1769674181, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (24, 'daily_report', '每日汇报', 'daily_summary', '📊 <b>每日交易汇报</b>\n\n日期: {date}\n当日盈亏: {daily_pnl}\n交易次数: {daily_trades}\n活跃跟单者: {active_followers}\n新信号数: {new_signals}\n\n系统运行正常 ✅', NULL, 1, 0, 0, 1769674181, 0, 1769674181, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (25, 'weekly_report', '每周汇报', 'weekly_summary', '📈 <b>每周交易汇报</b>\n\n周期: {start_date} ~ {end_date}\n总盈亏: {total_pnl}\n胜率: {win_rate}%\n交易次数: {trade_count}\n盈利次数: {profit_count}\n亏损次数: {loss_count}', NULL, 1, 0, 0, 1769674181, 0, 1769674181, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (26, 'system_error', '系统错误告警', 'system_alert', '🚨 <b>系统告警</b>\n\n类型: {alert_type}\n描述: {description}\n服务器: {server}\n\n时间: {time}\n\n请立即处理！', NULL, 1, 0, 0, 1769674181, 0, 1769674181, 1);
INSERT INTO `think_telegram_template` (`id`, `template_code`, `template_name`, `type`, `content`, `variables`, `status`, `sort`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (27, 'risk_warning', '风控预警', 'risk_warning', '⛔ <b>风控预警</b>\n\n会员: {member_name}\n预警类型: {warning_type}\n详情: {detail}\n\n时间: {time}', NULL, 1, 0, 0, 1769674181, 0, 1769674181, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_trade_calendar
-- ----------------------------
DROP TABLE IF EXISTS `think_trade_calendar`;
CREATE TABLE `think_trade_calendar` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL DEFAULT '' COMMENT '事件标题',
  `event_type` varchar(50) DEFAULT 'custom' COMMENT '事件类型',
  `event_date` date NOT NULL COMMENT '事件日期',
  `event_time` varchar(10) DEFAULT '' COMMENT '事件时间 HH:mm',
  `description` text COMMENT '事件描述',
  `importance` tinyint DEFAULT '2' COMMENT '重要程度 1-5',
  `symbol` varchar(50) DEFAULT '' COMMENT '相关币种',
  `source` varchar(100) DEFAULT '' COMMENT '信息来源',
  `source_url` varchar(500) DEFAULT '' COMMENT '来源链接',
  `remind_before` int DEFAULT '0' COMMENT '提前提醒分钟数',
  `is_reminded` tinyint DEFAULT '0' COMMENT '是否已提醒',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_event_date` (`event_date`),
  KEY `idx_event_type` (`event_type`),
  KEY `idx_importance` (`importance`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='交易日历表';

-- ----------------------------
-- Records of think_trade_calendar
-- ----------------------------
BEGIN;
INSERT INTO `think_trade_calendar` (`id`, `title`, `event_type`, `event_date`, `event_time`, `description`, `importance`, `symbol`, `source`, `source_url`, `remind_before`, `is_reminded`, `create_time`, `update_time`, `mark`) VALUES (1, 'FOMC利率决议', 'meeting', '2026-03-18', '03:00', '美联储公开市场委员会利率决议，北京时间凌晨公布', 5, '', 'Federal Reserve', '', 60, 0, 1769672108, 1769679241, 0);
INSERT INTO `think_trade_calendar` (`id`, `title`, `event_type`, `event_date`, `event_time`, `description`, `importance`, `symbol`, `source`, `source_url`, `remind_before`, `is_reminded`, `create_time`, `update_time`, `mark`) VALUES (2, 'FOMC利率决议', 'meeting', '2026-05-06', '03:00', '美联储公开市场委员会利率决议，北京时间凌晨公布', 5, '', 'Federal Reserve', '', 60, 0, 1769672108, 1769672108, 1);
INSERT INTO `think_trade_calendar` (`id`, `title`, `event_type`, `event_date`, `event_time`, `description`, `importance`, `symbol`, `source`, `source_url`, `remind_before`, `is_reminded`, `create_time`, `update_time`, `mark`) VALUES (3, 'FOMC利率决议', 'meeting', '2026-06-17', '03:00', '美联储公开市场委员会利率决议，北京时间凌晨公布', 5, '', 'Federal Reserve', '', 60, 0, 1769672108, 1769672108, 1);
INSERT INTO `think_trade_calendar` (`id`, `title`, `event_type`, `event_date`, `event_time`, `description`, `importance`, `symbol`, `source`, `source_url`, `remind_before`, `is_reminded`, `create_time`, `update_time`, `mark`) VALUES (4, 'FOMC利率决议', 'meeting', '2026-07-29', '03:00', '美联储公开市场委员会利率决议，北京时间凌晨公布', 5, '', 'Federal Reserve', '', 60, 0, 1769672108, 1769672108, 1);
INSERT INTO `think_trade_calendar` (`id`, `title`, `event_type`, `event_date`, `event_time`, `description`, `importance`, `symbol`, `source`, `source_url`, `remind_before`, `is_reminded`, `create_time`, `update_time`, `mark`) VALUES (5, 'FOMC利率决议', 'meeting', '2026-09-16', '03:00', '美联储公开市场委员会利率决议，北京时间凌晨公布', 5, '', 'Federal Reserve', '', 60, 0, 1769672108, 1769672108, 1);
INSERT INTO `think_trade_calendar` (`id`, `title`, `event_type`, `event_date`, `event_time`, `description`, `importance`, `symbol`, `source`, `source_url`, `remind_before`, `is_reminded`, `create_time`, `update_time`, `mark`) VALUES (6, 'FOMC利率决议', 'meeting', '2026-11-04', '03:00', '美联储公开市场委员会利率决议，北京时间凌晨公布', 5, '', 'Federal Reserve', '', 60, 0, 1769672108, 1769672108, 1);
INSERT INTO `think_trade_calendar` (`id`, `title`, `event_type`, `event_date`, `event_time`, `description`, `importance`, `symbol`, `source`, `source_url`, `remind_before`, `is_reminded`, `create_time`, `update_time`, `mark`) VALUES (7, 'FOMC利率决议', 'meeting', '2026-12-16', '03:00', '美联储公开市场委员会利率决议，北京时间凌晨公布', 5, '', 'Federal Reserve', '', 60, 0, 1769672108, 1769672108, 1);
INSERT INTO `think_trade_calendar` (`id`, `title`, `event_type`, `event_date`, `event_time`, `description`, `importance`, `symbol`, `source`, `source_url`, `remind_before`, `is_reminded`, `create_time`, `update_time`, `mark`) VALUES (8, 'FOMC利率决议', 'meeting', '2026-03-18', '03:00', '美联储公开市场委员会利率决议，北京时间凌晨公布', 5, '', 'Federal Reserve', '', 60, 0, 1769674578, 1769674578, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_trade_journal
-- ----------------------------
DROP TABLE IF EXISTS `think_trade_journal`;
CREATE TABLE `think_trade_journal` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned DEFAULT '0',
  `trade_date` date NOT NULL,
  `title` varchar(200) DEFAULT '',
  `content` text,
  `mood` tinyint DEFAULT '3' COMMENT '1-5心情评分',
  `market_condition` varchar(20) DEFAULT 'neutral',
  `trade_ids` json DEFAULT NULL,
  `tags` json DEFAULT NULL,
  `lessons_learned` text,
  `improvements` text,
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_member_date` (`member_id`,`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='交易日记表';

-- ----------------------------
-- Records of think_trade_journal
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_trade_log
-- ----------------------------
DROP TABLE IF EXISTS `think_trade_log`;
CREATE TABLE `think_trade_log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `type` varchar(20) NOT NULL DEFAULT '' COMMENT '日志类型',
  `action` varchar(50) NOT NULL DEFAULT '' COMMENT '操作动作',
  `module` varchar(50) NOT NULL DEFAULT '' COMMENT '模块名称',
  `content` text COMMENT '日志内容',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `username` varchar(50) NOT NULL DEFAULT '' COMMENT '用户名',
  `ip` varchar(50) NOT NULL DEFAULT '' COMMENT 'IP地址',
  `user_agent` varchar(255) NOT NULL DEFAULT '' COMMENT 'UserAgent',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1成功 0失败',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`),
  KEY `idx_type` (`type`),
  KEY `idx_module` (`module`),
  KEY `idx_status` (`status`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_member_id` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='交易日志表';

-- ----------------------------
-- Records of think_trade_log
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_trade_order
-- ----------------------------
DROP TABLE IF EXISTS `think_trade_order`;
CREATE TABLE `think_trade_order` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `order_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '订单号',
  `exchange_order_id` varchar(100) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '交易所订单ID',
  `signal_id` int unsigned DEFAULT NULL COMMENT '交易信号ID',
  `strategy_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略ID',
  `strategy_instance_id` int unsigned DEFAULT '0' COMMENT '策略实例ID',
  `hedge_group_id` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '对冲组ID',
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '账户ID',
  `symbol` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '交易对(如BTC/USDT)',
  `side` tinyint unsigned NOT NULL COMMENT '交易方向：1买入 2卖出',
  `position_side` varchar(10) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '持仓方向 LONG/SHORT',
  `type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '订单类型：1市价 2限价 3止损',
  `price` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '委托价格',
  `realized_pnl` decimal(20,8) DEFAULT '0.00000000' COMMENT '实现盈亏',
  `quantity` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '委托数量',
  `filled_quantity` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '成交数量',
  `filled_amount` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '成交金额',
  `avg_price` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '成交均价',
  `fee` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '手续费',
  `stop_loss` decimal(15,8) unsigned DEFAULT '0.00000000' COMMENT '止损价',
  `take_profit` decimal(15,8) unsigned DEFAULT '0.00000000' COMMENT '止盈价',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '订单状态：1待成交 2部分成交 3已成交 4已取消 5已拒绝',
  `source` tinyint unsigned DEFAULT '1' COMMENT '来源:1手动2策略3跟单4风控',
  `platform_order_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '平台订单ID',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `close_order_id` int unsigned DEFAULT '0' COMMENT '平仓订单ID，0表示未平仓',
  `error_msg` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误信息',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `execute_time` int unsigned DEFAULT NULL COMMENT '执行时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  `member_id` int unsigned DEFAULT NULL COMMENT '会员ID',
  `point_card_deducted` decimal(15,8) DEFAULT '0.00000000' COMMENT '已扣点卡',
  `agent_share` decimal(15,8) DEFAULT '0.00000000' COMMENT '代理商分成',
  `company_share` decimal(15,8) DEFAULT '0.00000000' COMMENT '公司分成',
  `server_id` int unsigned DEFAULT '0' COMMENT '执行服务器ID',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_order_no` (`order_no`) USING BTREE,
  KEY `idx_strategy_id` (`strategy_id`) USING BTREE,
  KEY `idx_account_id` (`account_id`) USING BTREE,
  KEY `idx_symbol` (`symbol`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_create_time` (`create_time`) USING BTREE,
  KEY `idx_account_status_time` (`account_id`,`status`,`create_time`),
  KEY `idx_symbol_status` (`symbol`,`status`),
  KEY `idx_signal_id` (`signal_id`),
  KEY `idx_member_id` (`member_id`),
  KEY `idx_member_time` (`member_id`,`create_time`),
  KEY `idx_hedge_group` (`hedge_group_id`),
  KEY `idx_exchange_order` (`exchange_order_id`),
  KEY `idx_close_order_id` (`close_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='交易订单表';

-- ----------------------------
-- Records of think_trade_order
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_trade_signal
-- ----------------------------
DROP TABLE IF EXISTS `think_trade_signal`;
CREATE TABLE `think_trade_signal` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `signal_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '信号编号',
  `strategy_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略ID',
  `instance_id` int unsigned DEFAULT '0' COMMENT '策略实例ID',
  `leader_id` int unsigned NOT NULL DEFAULT '0' COMMENT '带单者用户ID',
  `symbol` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '交易对',
  `side` tinyint unsigned NOT NULL COMMENT '交易方向：1买入 2卖出',
  `position_side` varchar(20) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '持仓方向: LONG/SHORT',
  `type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '信号类型：1开仓 2平仓 3止损 4止盈',
  `price` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '信号价格',
  `quantity` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '信号数量',
  `leverage` int unsigned DEFAULT '1' COMMENT '杠杆倍数',
  `stop_loss` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '止损价格',
  `take_profit` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '止盈价格',
  `risk_reward_ratio` decimal(5,2) DEFAULT '0.00' COMMENT '风险回报比',
  `hedge_group_id` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '对冲组ID',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '信号状态：1待执行 2执行中 3已执行 4已取消',
  `source` tinyint unsigned DEFAULT '1' COMMENT '来源:1策略2手动3API',
  `execute_time` int unsigned NOT NULL DEFAULT '0' COMMENT '执行时间',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `fail_reason` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '失败原因',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_signal_no` (`signal_no`) USING BTREE,
  KEY `idx_strategy_id` (`strategy_id`) USING BTREE,
  KEY `idx_leader_id` (`leader_id`) USING BTREE,
  KEY `idx_symbol` (`symbol`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_create_time` (`create_time`) USING BTREE,
  KEY `idx_strategy_status_time` (`strategy_id`,`status`,`create_time`),
  KEY `idx_symbol_status_time` (`symbol`,`status`,`create_time`),
  KEY `idx_status_create_time` (`status`,`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='交易信号表';

-- ----------------------------
-- Records of think_trade_signal
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_trading_batch
-- ----------------------------
DROP TABLE IF EXISTS `think_trading_batch`;
CREATE TABLE `think_trading_batch` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `batch_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '批次编号',
  `symbol` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '交易对',
  `side` tinyint unsigned NOT NULL COMMENT '交易方向：1买入 2卖出',
  `leverage` int unsigned NOT NULL DEFAULT '1' COMMENT '杠杆倍数',
  `order_count` int unsigned NOT NULL DEFAULT '0' COMMENT '订单数量',
  `total_amount` decimal(15,2) unsigned NOT NULL DEFAULT '0.00' COMMENT '总开仓金额',
  `success_count` int unsigned NOT NULL DEFAULT '0' COMMENT '成功数量',
  `fail_count` int unsigned NOT NULL DEFAULT '0' COMMENT '失败数量',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1待执行 2执行中 3已完成 4失败',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_batch_no` (`batch_no`) USING BTREE,
  KEY `idx_symbol` (`symbol`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_create_time` (`create_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='交易批次表';

-- ----------------------------
-- Records of think_trading_batch
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_trailing_stop
-- ----------------------------
DROP TABLE IF EXISTS `think_trailing_stop`;
CREATE TABLE `think_trailing_stop` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `position_id` int unsigned DEFAULT '0' COMMENT '关联持仓ID',
  `member_id` int unsigned DEFAULT '0' COMMENT '用户ID',
  `symbol` varchar(50) NOT NULL COMMENT '交易对',
  `position_side` varchar(10) DEFAULT 'LONG' COMMENT 'LONG/SHORT',
  `type` tinyint DEFAULT '1' COMMENT '1追踪止损 2追踪止盈',
  `mode` tinyint DEFAULT '1' COMMENT '1百分比 2固定点数',
  `callback_rate` decimal(10,4) NOT NULL COMMENT '回调率/点数',
  `activation_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '激活价格',
  `quantity` decimal(20,8) DEFAULT '0.00000000' COMMENT '数量',
  `highest_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '最高价',
  `lowest_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '最低价',
  `trigger_price` decimal(20,8) DEFAULT '0.00000000' COMMENT '当前触发价',
  `status` tinyint DEFAULT '1' COMMENT '1激活 2已触发 3已取消 4已过期',
  `triggered_at` int unsigned DEFAULT '0' COMMENT '触发时间',
  `create_time` int unsigned DEFAULT '0',
  `update_time` int unsigned DEFAULT '0',
  `mark` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_member` (`member_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='追踪止盈止损表';

-- ----------------------------
-- Records of think_trailing_stop
-- ----------------------------
BEGIN;
INSERT INTO `think_trailing_stop` (`id`, `position_id`, `member_id`, `symbol`, `position_side`, `type`, `mode`, `callback_rate`, `activation_price`, `quantity`, `highest_price`, `lowest_price`, `trigger_price`, `status`, `triggered_at`, `create_time`, `update_time`, `mark`) VALUES (1, 1, 1, 'BTC/USDT', 'LONG', 1, 1, 2.0000, 0.00000000, 0.10000000, 0.00000000, 0.00000000, 0.00000000, 3, 0, 1769590799, 1769590809, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_user
-- ----------------------------
DROP TABLE IF EXISTS `think_user`;
CREATE TABLE `think_user` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `realname` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '真实姓名',
  `nickname` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '昵称',
  `gender` tinyint unsigned NOT NULL DEFAULT '3' COMMENT '性别:1男 2女 3保密',
  `avatar` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '头像',
  `mobile` char(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '手机号码',
  `email` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮箱地址',
  `birthday` int unsigned DEFAULT '0' COMMENT '出生日期',
  `dept_id` int unsigned NOT NULL DEFAULT '0' COMMENT '部门ID',
  `level_id` smallint unsigned NOT NULL DEFAULT '0' COMMENT '职级ID',
  `position_id` smallint unsigned NOT NULL DEFAULT '0' COMMENT '岗位ID',
  `province_code` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '省份编码',
  `city_code` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '市区编码',
  `district_code` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '区县编码',
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '详细地址',
  `city_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '所属城市',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '登录用户名',
  `password` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '登录密码',
  `salt` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '盐加密',
  `intro` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '个人简介',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1正常 2禁用',
  `note` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `sort` smallint unsigned NOT NULL DEFAULT '125' COMMENT '显示顺序',
  `login_num` smallint unsigned NOT NULL DEFAULT '0' COMMENT '登录次数',
  `login_ip` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '最近登录IP',
  `login_time` int unsigned NOT NULL DEFAULT '0' COMMENT '最近登录时间',
  `create_user` int unsigned NOT NULL DEFAULT '0' COMMENT '添加人',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_user` int unsigned NOT NULL DEFAULT '0' COMMENT '更新人',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_username` (`username`) USING BTREE,
  KEY `realname` (`realname`) USING BTREE,
  KEY `idx_mobile` (`mobile`) USING BTREE,
  KEY `idx_email` (`email`) USING BTREE,
  KEY `idx_mark` (`mark`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_dept_id` (`dept_id`) USING BTREE,
  KEY `idx_mark_status` (`mark`,`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='后台用户管理表';

-- ----------------------------
-- Records of think_user
-- ----------------------------
BEGIN;
INSERT INTO `think_user` (`id`, `realname`, `nickname`, `gender`, `avatar`, `mobile`, `email`, `birthday`, `dept_id`, `level_id`, `position_id`, `province_code`, `city_code`, `district_code`, `address`, `city_name`, `username`, `password`, `salt`, `intro`, `status`, `note`, `sort`, `login_num`, `login_ip`, `login_time`, `create_user`, `create_time`, `update_user`, `update_time`, `mark`) VALUES (1, '系统管理员', '管理员', 1, NULL, NULL, NULL, 0, 1, 1, 1, NULL, NULL, NULL, NULL, NULL, 'admin', '43286a86708820e38c333cdd4c496355', '', '系统默认管理员账号', 1, '默认账号，请及时修改密码', 125, 0, NULL, 0, 1, 1769225444, 1, 1769225444, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_user_role
-- ----------------------------
DROP TABLE IF EXISTS `think_user_role`;
CREATE TABLE `think_user_role` (
  `user_id` int unsigned NOT NULL DEFAULT '0' COMMENT '人员ID',
  `role_id` int unsigned NOT NULL DEFAULT '0' COMMENT '角色ID',
  PRIMARY KEY (`user_id`,`role_id`) USING BTREE,
  KEY `idx_user_id` (`user_id`) USING BTREE,
  KEY `idx_role_id` (`role_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='人员角色表';

-- ----------------------------
-- Records of think_user_role
-- ----------------------------
BEGIN;
INSERT INTO `think_user_role` (`user_id`, `role_id`) VALUES (1, 1);
COMMIT;

-- ----------------------------
-- Table structure for think_wallet_bill
-- ----------------------------
DROP TABLE IF EXISTS `think_wallet_bill`;
CREATE TABLE `think_wallet_bill` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `bill_no` varchar(32) NOT NULL DEFAULT '' COMMENT '账单编号',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '用户ID',
  `amount` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '金额',
  `balance_before` decimal(20,2) DEFAULT '0.00' COMMENT '变动前余额',
  `balance_after` decimal(20,2) DEFAULT '0.00' COMMENT '变动后余额',
  `type` varchar(20) NOT NULL DEFAULT '' COMMENT '类型: income收入 withdraw提现 transfer转账 fee手续费 refund退款',
  `source` varchar(30) DEFAULT '' COMMENT '来源: trade交易 commission分成 reward奖励 recharge充值',
  `related_id` int unsigned DEFAULT '0' COMMENT '关联ID',
  `related_type` varchar(30) DEFAULT '' COMMENT '关联类型',
  `title` varchar(100) DEFAULT '' COMMENT '标题',
  `note` varchar(500) DEFAULT '' COMMENT '备注',
  `status` tinyint DEFAULT '1' COMMENT '状态:1成功 0失败 2处理中',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_no` (`bill_no`),
  KEY `idx_member` (`member_id`),
  KEY `idx_type` (`type`),
  KEY `idx_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='账单明细表';

-- ----------------------------
-- Records of think_wallet_bill
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_withdraw_apply
-- ----------------------------
DROP TABLE IF EXISTS `think_withdraw_apply`;
CREATE TABLE `think_withdraw_apply` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `apply_no` varchar(32) NOT NULL DEFAULT '' COMMENT '申请编号',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '用户ID',
  `amount` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '申请金额',
  `fee` decimal(20,2) DEFAULT '0.00' COMMENT '手续费',
  `actual_amount` decimal(20,2) DEFAULT '0.00' COMMENT '实际到账',
  `withdraw_type` varchar(20) DEFAULT 'usdt' COMMENT '提现类型: usdt bank alipay',
  `chain` varchar(20) DEFAULT '' COMMENT '链: TRC20 ERC20 BEP20',
  `wallet_address` varchar(100) DEFAULT '' COMMENT '钱包地址',
  `bank_name` varchar(50) DEFAULT '' COMMENT '银行名称',
  `bank_account` varchar(50) DEFAULT '' COMMENT '银行账号',
  `bank_holder` varchar(50) DEFAULT '' COMMENT '开户人',
  `alipay_account` varchar(50) DEFAULT '' COMMENT '支付宝账号',
  `alipay_name` varchar(50) DEFAULT '' COMMENT '支付宝姓名',
  `status` tinyint DEFAULT '0' COMMENT '状态:0待审核 1审核通过 2已发放 3已拒绝 4已取消',
  `audit_user_id` int DEFAULT '0' COMMENT '审核人',
  `audit_time` int unsigned DEFAULT '0' COMMENT '审核时间',
  `audit_note` varchar(200) DEFAULT '' COMMENT '审核备注',
  `pay_time` int unsigned DEFAULT '0' COMMENT '发放时间',
  `pay_txid` varchar(100) DEFAULT '' COMMENT '交易哈希/流水号',
  `pay_note` varchar(200) DEFAULT '' COMMENT '发放备注',
  `note` varchar(200) DEFAULT '' COMMENT '申请备注',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_no` (`apply_no`),
  KEY `idx_member` (`member_id`),
  KEY `idx_status` (`status`),
  KEY `idx_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='提现申请表';

-- ----------------------------
-- Records of think_withdraw_apply
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for think_withdraw_config
-- ----------------------------
DROP TABLE IF EXISTS `think_withdraw_config`;
CREATE TABLE `think_withdraw_config` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `config_key` varchar(50) NOT NULL DEFAULT '' COMMENT '配置键',
  `config_value` text COMMENT '配置值',
  `note` varchar(200) DEFAULT '' COMMENT '备注',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_key` (`config_key`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='提现配置表';

-- ----------------------------
-- Records of think_withdraw_config
-- ----------------------------
BEGIN;
INSERT INTO `think_withdraw_config` (`id`, `config_key`, `config_value`, `note`, `create_time`, `update_time`) VALUES (1, 'min_amount', '10', '最低提现金额', 1769499260, 1769499260);
INSERT INTO `think_withdraw_config` (`id`, `config_key`, `config_value`, `note`, `create_time`, `update_time`) VALUES (2, 'max_amount', '50000', '单笔最高提现金额', 1769499260, 1769499260);
INSERT INTO `think_withdraw_config` (`id`, `config_key`, `config_value`, `note`, `create_time`, `update_time`) VALUES (3, 'daily_limit', '100000', '每日提现限额', 1769499260, 1769499260);
INSERT INTO `think_withdraw_config` (`id`, `config_key`, `config_value`, `note`, `create_time`, `update_time`) VALUES (4, 'fee_rate', '0.01', '提现手续费率(1%)', 1769499260, 1769499260);
INSERT INTO `think_withdraw_config` (`id`, `config_key`, `config_value`, `note`, `create_time`, `update_time`) VALUES (5, 'min_fee', '1', '最低手续费', 1769499260, 1769499260);
INSERT INTO `think_withdraw_config` (`id`, `config_key`, `config_value`, `note`, `create_time`, `update_time`) VALUES (6, 'usdt_enabled', '1', '是否启用USDT提现', 1769499260, 1769499260);
INSERT INTO `think_withdraw_config` (`id`, `config_key`, `config_value`, `note`, `create_time`, `update_time`) VALUES (7, 'bank_enabled', '1', '是否启用银行卡提现', 1769499260, 1769499260);
INSERT INTO `think_withdraw_config` (`id`, `config_key`, `config_value`, `note`, `create_time`, `update_time`) VALUES (8, 'alipay_enabled', '0', '是否启用支付宝提现', 1769499260, 1769499260);
COMMIT;

SET FOREIGN_KEY_CHECKS = 1;
