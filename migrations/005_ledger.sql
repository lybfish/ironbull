-- ============================================================
-- Ledger Module - 资金/权益/账务管理
-- 
-- 表结构：
--   1. fact_account - 资金账户表
--   2. fact_transaction - 交易流水表（append-only）
--   3. fact_equity_snapshot - 权益快照表
--
-- 不变量：
--   1. 资金守恒：可用 + 冻结 = 总余额
--   2. 流水可追溯：每笔变动有对应流水
--   3. 费用不遗漏
--   4. 租户隔离
-- ============================================================

-- ------------------------------------------------------------
-- 1. fact_account - 资金账户表
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `fact_account` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    
    -- 账户标识
    `ledger_account_id` VARCHAR(64) NOT NULL COMMENT '账本账户ID',
    
    -- 租户与账户
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '交易账户ID',
    
    -- 币种
    `currency` VARCHAR(16) NOT NULL DEFAULT 'USDT' COMMENT '币种',
    
    -- 余额
    `balance` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '总余额',
    `available` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '可用余额',
    `frozen` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '冻结金额',
    
    -- 盈亏统计
    `total_deposit` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计入金',
    `total_withdraw` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计出金',
    `total_fee` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计手续费',
    `realized_pnl` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计已实现盈亏',
    
    -- 合约专用
    `margin_used` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '已用保证金',
    
    -- 状态
    `status` VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/FROZEN/CLOSED',
    
    -- 时间戳
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_ledger_account_id` (`ledger_account_id`),
    UNIQUE KEY `uq_account_key` (`tenant_id`, `account_id`, `currency`),
    KEY `idx_account_tenant_account` (`tenant_id`, `account_id`),
    KEY `idx_account_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资金账户表';


-- ------------------------------------------------------------
-- 2. fact_transaction - 交易流水表
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `fact_transaction` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    
    -- 流水标识
    `transaction_id` VARCHAR(64) NOT NULL COMMENT '流水ID',
    
    -- 关联账户
    `ledger_account_id` VARCHAR(64) NOT NULL COMMENT '账本账户ID',
    
    -- 租户与账户（冗余存储便于查询）
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '交易账户ID',
    
    -- 币种
    `currency` VARCHAR(16) NOT NULL DEFAULT 'USDT' COMMENT '币种',
    
    -- 交易类型
    `transaction_type` VARCHAR(32) NOT NULL COMMENT '交易类型',
    
    -- 金额
    `amount` DECIMAL(20,8) NOT NULL COMMENT '变动金额（可正可负）',
    `fee` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '手续费',
    
    -- 变动后余额（快照）
    `balance_after` DECIMAL(20,8) NOT NULL COMMENT '变动后总余额',
    `available_after` DECIMAL(20,8) NOT NULL COMMENT '变动后可用',
    `frozen_after` DECIMAL(20,8) NOT NULL COMMENT '变动后冻结',
    
    -- 来源关联
    `source_type` VARCHAR(32) NOT NULL COMMENT '来源类型',
    `source_id` VARCHAR(64) DEFAULT NULL COMMENT '来源ID',
    
    -- 关联标的
    `symbol` VARCHAR(32) DEFAULT NULL COMMENT '交易对',
    
    -- 状态
    `status` VARCHAR(16) NOT NULL DEFAULT 'COMPLETED' COMMENT '状态',
    
    -- 时间戳
    `transaction_at` DATETIME NOT NULL COMMENT '交易时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 备注
    `remark` TEXT DEFAULT NULL COMMENT '备注',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_transaction_id` (`transaction_id`),
    KEY `idx_tx_account` (`ledger_account_id`),
    KEY `idx_tx_tenant_account` (`tenant_id`, `account_id`),
    KEY `idx_tx_type` (`transaction_type`),
    KEY `idx_tx_source` (`source_type`, `source_id`),
    KEY `idx_tx_time` (`transaction_at`),
    KEY `idx_tx_symbol` (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易流水表';


-- ------------------------------------------------------------
-- 3. fact_equity_snapshot - 权益快照表
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `fact_equity_snapshot` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    
    -- 快照标识
    `snapshot_id` VARCHAR(64) NOT NULL COMMENT '快照ID',
    
    -- 关联账户
    `ledger_account_id` VARCHAR(64) NOT NULL COMMENT '账本账户ID',
    
    -- 租户与账户
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '交易账户ID',
    
    -- 币种
    `currency` VARCHAR(16) NOT NULL DEFAULT 'USDT' COMMENT '币种',
    
    -- 权益数据
    `balance` DECIMAL(20,8) NOT NULL COMMENT '现金余额',
    `unrealized_pnl` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '未实现盈亏',
    `equity` DECIMAL(20,8) NOT NULL COMMENT '总权益',
    
    -- 持仓市值
    `position_value` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '持仓市值',
    
    -- 保证金
    `margin_used` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '已用保证金',
    `margin_ratio` DECIMAL(10,4) DEFAULT NULL COMMENT '保证金率',
    
    -- 净值与收益率
    `net_value` DECIMAL(20,8) DEFAULT NULL COMMENT '单位净值',
    `daily_return` DECIMAL(10,6) DEFAULT NULL COMMENT '日收益率',
    `cumulative_return` DECIMAL(10,6) DEFAULT NULL COMMENT '累计收益率',
    
    -- 快照时间
    `snapshot_at` DATETIME NOT NULL COMMENT '快照时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_snapshot_id` (`snapshot_id`),
    UNIQUE KEY `uq_snapshot_account_time` (`ledger_account_id`, `snapshot_at`),
    KEY `idx_snapshot_account` (`ledger_account_id`),
    KEY `idx_snapshot_tenant_account` (`tenant_id`, `account_id`),
    KEY `idx_snapshot_time` (`snapshot_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权益快照表';


-- ============================================================
-- 数据完整性说明
-- ============================================================
--
-- 1. 不变量在应用层强制执行：
--    - balance = available + frozen
--    - 出金/扣款 ≤ 可用余额
--    - 每笔流水必须有 source_type/source_id
--
-- 2. fact_transaction 是 append-only：
--    - 只允许 INSERT，禁止 UPDATE/DELETE
--    - 每笔流水记录变动后的快照状态
--    - 可用于审计和重建账户余额
--
-- 3. 租户隔离：
--    - 所有查询必须包含 tenant_id
--
-- 4. 幂等性：
--    - 通过 source_type + source_id 实现幂等
--    - 同一 fill_id 不会重复入账
-- ============================================================
