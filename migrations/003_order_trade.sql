-- Migration: 003_order_trade
-- Description: 创建 Order 和 Fill 表，满足 SaaS 蓝图 OrderTrade 能力域要求
-- Date: 2026-02-05
-- 
-- 设计原则：
-- 1. Order 表支持状态更新（订单生命周期）
-- 2. Fill 表严格 append-only（成交不可逆）
-- 3. 租户隔离（所有查询必须带 tenant_id）
-- 4. 一笔订单可有多笔成交（一对多关系）

-- ============================================================
-- 订单表 (fact_order)
-- ============================================================

CREATE TABLE IF NOT EXISTS `fact_order` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 订单标识
    `order_id` VARCHAR(64) NOT NULL COMMENT '系统订单号',
    `exchange_order_id` VARCHAR(128) DEFAULT NULL COMMENT '交易所订单号',
    
    -- 租户与账户
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '账户ID',
    
    -- 关联信号（可选）
    `signal_id` VARCHAR(64) DEFAULT NULL COMMENT '关联信号ID',
    
    -- 交易标的
    `symbol` VARCHAR(32) NOT NULL COMMENT '交易对',
    `exchange` VARCHAR(32) NOT NULL COMMENT '交易所',
    `market_type` VARCHAR(16) NOT NULL DEFAULT 'spot' COMMENT 'spot/future',
    
    -- 订单参数
    `side` VARCHAR(8) NOT NULL COMMENT 'BUY/SELL',
    `order_type` VARCHAR(32) NOT NULL COMMENT 'MARKET/LIMIT/STOP_MARKET/TAKE_PROFIT_MARKET',
    `quantity` DECIMAL(20,8) NOT NULL COMMENT '委托数量',
    `price` DECIMAL(20,8) DEFAULT NULL COMMENT '委托价格（限价单）',
    
    -- 止损止盈
    `stop_loss` DECIMAL(20,8) DEFAULT NULL COMMENT '止损价',
    `take_profit` DECIMAL(20,8) DEFAULT NULL COMMENT '止盈价',
    
    -- 合约专用
    `position_side` VARCHAR(16) DEFAULT NULL COMMENT 'LONG/SHORT（合约双向持仓）',
    `leverage` INT DEFAULT NULL COMMENT '杠杆倍数',
    
    -- 订单状态
    `status` VARCHAR(16) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/SUBMITTED/OPEN/PARTIAL/FILLED/CANCELLED/REJECTED/EXPIRED/FAILED',
    
    -- 累计成交
    `filled_quantity` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计成交数量',
    `avg_price` DECIMAL(20,8) DEFAULT NULL COMMENT '成交均价',
    `total_fee` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计手续费',
    `fee_currency` VARCHAR(16) DEFAULT NULL COMMENT '手续费币种',
    
    -- 错误信息
    `error_code` VARCHAR(32) DEFAULT NULL COMMENT '错误码',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    
    -- 时间戳
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `submitted_at` DATETIME DEFAULT NULL COMMENT '提交时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 追踪
    `request_id` VARCHAR(64) DEFAULT NULL COMMENT '请求追踪ID',
    
    -- 约束
    UNIQUE KEY `uq_order_id` (`order_id`),
    
    -- 索引
    INDEX `idx_order_exchange_order_id` (`exchange_order_id`),
    INDEX `idx_order_tenant_id` (`tenant_id`),
    INDEX `idx_order_account_id` (`account_id`),
    INDEX `idx_order_signal_id` (`signal_id`),
    INDEX `idx_order_symbol` (`symbol`),
    INDEX `idx_order_status` (`status`),
    INDEX `idx_order_tenant_account` (`tenant_id`, `account_id`),
    INDEX `idx_order_tenant_status` (`tenant_id`, `status`),
    INDEX `idx_order_symbol_time` (`symbol`, `created_at`),
    INDEX `idx_order_request_id` (`request_id`)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='订单表 - 记录每个委托的完整生命周期';


-- ============================================================
-- 成交表 (fact_fill)
-- ============================================================

CREATE TABLE IF NOT EXISTS `fact_fill` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 成交标识
    `fill_id` VARCHAR(64) NOT NULL COMMENT '系统成交ID',
    `exchange_trade_id` VARCHAR(128) DEFAULT NULL COMMENT '交易所成交ID',
    
    -- 关联订单
    `order_id` VARCHAR(64) NOT NULL COMMENT '关联订单ID',
    
    -- 租户与账户（冗余存储便于查询）
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '账户ID',
    
    -- 交易标的（冗余存储）
    `symbol` VARCHAR(32) NOT NULL COMMENT '交易对',
    `side` VARCHAR(8) NOT NULL COMMENT 'BUY/SELL',
    
    -- 成交数据
    `quantity` DECIMAL(20,8) NOT NULL COMMENT '成交数量',
    `price` DECIMAL(20,8) NOT NULL COMMENT '成交价格',
    
    -- 手续费
    `fee` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '手续费',
    `fee_currency` VARCHAR(16) DEFAULT NULL COMMENT '手续费币种',
    
    -- 时间戳
    `filled_at` DATETIME NOT NULL COMMENT '成交时间（交易所时间）',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 追踪
    `request_id` VARCHAR(64) DEFAULT NULL COMMENT '请求追踪ID',
    
    -- 约束
    UNIQUE KEY `uq_fill_id` (`fill_id`),
    UNIQUE KEY `uq_fill_order_exchange` (`order_id`, `exchange_trade_id`),
    
    -- 索引
    INDEX `idx_fill_exchange_trade_id` (`exchange_trade_id`),
    INDEX `idx_fill_order_id` (`order_id`),
    INDEX `idx_fill_tenant_id` (`tenant_id`),
    INDEX `idx_fill_account_id` (`account_id`),
    INDEX `idx_fill_symbol` (`symbol`),
    INDEX `idx_fill_tenant_account` (`tenant_id`, `account_id`),
    INDEX `idx_fill_symbol_time` (`symbol`, `filled_at`),
    INDEX `idx_fill_time` (`filled_at`),
    INDEX `idx_fill_request_id` (`request_id`)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='成交表 - 记录每笔成交流水（append-only）';


-- ============================================================
-- 备注
-- ============================================================
-- 
-- 不变量约束（由应用层保证）：
-- 1. 成交 ≤ 订单：sum(fills.quantity) <= order.quantity
-- 2. 成交不可逆：Fill 表不允许 UPDATE/DELETE
-- 3. 状态机合法：Order.status 只能按规则流转
-- 4. 时间有序：同一订单的 Fill.filled_at 单调递增
-- 5. 关联完整：Fill.order_id 必须存在于 Order 表
-- 6. 租户隔离：所有查询必须带 tenant_id
--
-- 旧表处理：
-- fact_trade 表保留，后续可迁移数据后删除
