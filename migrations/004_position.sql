-- ============================================================
-- Position Module - 持仓管理
-- 
-- 表结构：
--   1. fact_position - 当前持仓状态表
--   2. fact_position_change - 持仓变动历史表（append-only）
--
-- 不变量：
--   1. 持仓 = Σ成交
--   2. 可用 + 冻结 = 总持仓
--   3. 卖出 ≤ 可用
--   4. 成本可追溯
--   5. 变动有来源
--   6. 租户隔离
-- ============================================================

-- ------------------------------------------------------------
-- 1. fact_position - 持仓表
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `fact_position` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    
    -- 持仓标识
    `position_id` VARCHAR(64) NOT NULL COMMENT '持仓ID',
    
    -- 租户与账户
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '账户ID',
    
    -- 标的信息
    `symbol` VARCHAR(32) NOT NULL COMMENT '交易对',
    `exchange` VARCHAR(32) NOT NULL COMMENT '交易所',
    `market_type` VARCHAR(16) NOT NULL DEFAULT 'spot' COMMENT '市场类型: spot/future',
    
    -- 持仓方向（合约双向持仓用）
    `position_side` VARCHAR(16) NOT NULL DEFAULT 'NONE' COMMENT '持仓方向: LONG/SHORT/NONE',
    
    -- 持仓数量
    `quantity` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '总持仓数量',
    `available` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '可用数量',
    `frozen` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '冻结数量',
    
    -- 成本与盈亏
    `avg_cost` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '平均成本价',
    `total_cost` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '总成本',
    `realized_pnl` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计已实现盈亏',
    
    -- 合约专用
    `leverage` INT DEFAULT NULL COMMENT '杠杆倍数',
    `margin` DECIMAL(20,8) DEFAULT NULL COMMENT '保证金',
    `liquidation_price` DECIMAL(20,8) DEFAULT NULL COMMENT '强平价格',
    
    -- 状态
    `status` VARCHAR(16) NOT NULL DEFAULT 'OPEN' COMMENT '状态: OPEN/CLOSED/LIQUIDATED',
    
    -- 时间戳
    `opened_at` DATETIME DEFAULT NULL COMMENT '开仓时间',
    `closed_at` DATETIME DEFAULT NULL COMMENT '平仓时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_position_id` (`position_id`),
    UNIQUE KEY `uq_position_key` (`tenant_id`, `account_id`, `symbol`, `exchange`, `position_side`),
    KEY `idx_position_tenant_account` (`tenant_id`, `account_id`),
    KEY `idx_position_symbol` (`symbol`),
    KEY `idx_position_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓表';


-- ------------------------------------------------------------
-- 2. fact_position_change - 持仓变动历史表
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `fact_position_change` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    
    -- 变动标识
    `change_id` VARCHAR(64) NOT NULL COMMENT '变动ID',
    
    -- 关联持仓
    `position_id` VARCHAR(64) NOT NULL COMMENT '关联持仓ID',
    
    -- 租户与账户（冗余存储便于查询）
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '账户ID',
    
    -- 标的信息（冗余存储）
    `symbol` VARCHAR(32) NOT NULL COMMENT '交易对',
    `position_side` VARCHAR(16) NOT NULL DEFAULT 'NONE' COMMENT '持仓方向',
    
    -- 变动类型
    `change_type` VARCHAR(16) NOT NULL COMMENT '变动类型: OPEN/ADD/REDUCE/CLOSE/FREEZE/UNFREEZE/LIQUIDATION/ADJUSTMENT',
    
    -- 变动数量
    `quantity_change` DECIMAL(20,8) NOT NULL COMMENT '数量变化（可正可负）',
    `available_change` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '可用变化',
    `frozen_change` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '冻结变化',
    
    -- 变动后状态（快照）
    `quantity_after` DECIMAL(20,8) NOT NULL COMMENT '变动后总数量',
    `available_after` DECIMAL(20,8) NOT NULL COMMENT '变动后可用',
    `frozen_after` DECIMAL(20,8) NOT NULL COMMENT '变动后冻结',
    `avg_cost_after` DECIMAL(20,8) NOT NULL COMMENT '变动后成本',
    
    -- 成交价格（交易触发时记录）
    `price` DECIMAL(20,8) DEFAULT NULL COMMENT '成交价格',
    
    -- 盈亏（平仓时记录）
    `realized_pnl` DECIMAL(20,8) DEFAULT NULL COMMENT '本次变动实现盈亏',
    
    -- 变动来源（不变量：变动有来源）
    `source_type` VARCHAR(32) NOT NULL COMMENT '来源类型: FILL/ORDER/ADJUSTMENT/LIQUIDATION/TRANSFER/INIT',
    `source_id` VARCHAR(64) DEFAULT NULL COMMENT '来源ID（如 fill_id）',
    
    -- 时间戳
    `changed_at` DATETIME NOT NULL COMMENT '变动时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 备注
    `remark` TEXT DEFAULT NULL COMMENT '备注说明',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_change_id` (`change_id`),
    KEY `idx_change_position` (`position_id`),
    KEY `idx_change_tenant_account` (`tenant_id`, `account_id`),
    KEY `idx_change_symbol` (`symbol`),
    KEY `idx_change_type` (`change_type`),
    KEY `idx_change_source` (`source_type`, `source_id`),
    KEY `idx_change_time` (`changed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓变动历史表';


-- ============================================================
-- 数据完整性说明
-- ============================================================
--
-- 1. 不变量在应用层强制执行：
--    - quantity = available + frozen（可用 + 冻结 = 总持仓）
--    - 卖出数量 ≤ 可用数量
--    - 冻结数量 ≤ 可用数量
--    - 每笔变动必须有 source_type/source_id
--
-- 2. fact_position_change 是 append-only：
--    - 只允许 INSERT，禁止 UPDATE/DELETE
--    - 每笔变动记录变动后的快照状态
--    - 可用于审计和重建持仓
--
-- 3. 租户隔离：
--    - 所有查询必须包含 tenant_id
--    - 唯一键包含 tenant_id
--
-- 4. 成本计算口径：
--    - 使用加权平均法
--    - avg_cost = total_cost / quantity
--    - 减仓不改变成本，只改变数量
-- ============================================================
