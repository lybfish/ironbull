-- ============================================================
-- IronBull v1 Facts Layer Migration
-- 事实层表结构（Trade/Ledger/FreezeRecord/SignalEvent）
-- ============================================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS ironbull
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

USE ironbull;

-- ============================================================
-- 1. Trade - 交易记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_trade (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 关联ID
    signal_id VARCHAR(64) NOT NULL COMMENT '信号ID',
    task_id VARCHAR(64) NOT NULL COMMENT '执行任务ID',
    account_id INT NOT NULL COMMENT '账户ID',
    member_id INT NOT NULL COMMENT '会员ID',
    
    -- 交易标的
    symbol VARCHAR(32) NOT NULL COMMENT '交易对',
    canonical_symbol VARCHAR(32) NULL COMMENT '标准化交易对',
    exchange VARCHAR(32) NULL COMMENT '交易所',
    
    -- 交易方向与类型
    side VARCHAR(8) NOT NULL COMMENT 'BUY/SELL',
    trade_type VARCHAR(16) NOT NULL COMMENT 'OPEN/CLOSE/ADD/REDUCE',
    order_type VARCHAR(16) DEFAULT 'MARKET' COMMENT 'MARKET/LIMIT',
    
    -- 价格与数量
    entry_price DECIMAL(20, 8) NULL COMMENT '入场价',
    filled_price DECIMAL(20, 8) NULL COMMENT '成交均价',
    quantity DECIMAL(20, 8) NOT NULL COMMENT '委托数量',
    filled_quantity DECIMAL(20, 8) NULL COMMENT '成交数量',
    
    -- 止损止盈
    stop_loss DECIMAL(20, 8) NULL COMMENT '止损价',
    take_profit DECIMAL(20, 8) NULL COMMENT '止盈价',
    
    -- 成本与手续费
    fee DECIMAL(20, 8) DEFAULT 0 COMMENT '手续费',
    fee_currency VARCHAR(16) NULL COMMENT '手续费币种',
    
    -- 订单ID
    order_id VARCHAR(64) NULL COMMENT '系统订单ID',
    exchange_order_id VARCHAR(128) NULL COMMENT '交易所订单ID',
    
    -- 执行状态
    status VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT 'pending/filled/partial/failed/cancelled',
    error_code VARCHAR(32) NULL COMMENT '错误码',
    error_message TEXT NULL COMMENT '错误信息',
    
    -- 关联策略
    strategy_code VARCHAR(64) NULL COMMENT '策略代码',
    timeframe VARCHAR(8) NULL COMMENT '时间周期',
    
    -- 时间戳
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_at DATETIME NULL COMMENT '执行完成时间',
    
    -- 追踪
    request_id VARCHAR(64) NULL COMMENT '请求追踪ID',
    
    -- 索引
    INDEX idx_trade_signal_id (signal_id),
    INDEX idx_trade_task_id (task_id),
    INDEX idx_trade_account_id (account_id),
    INDEX idx_trade_member_id (member_id),
    INDEX idx_trade_signal_task (signal_id, task_id),
    INDEX idx_trade_account_time (account_id, created_at),
    INDEX idx_trade_symbol_time (symbol, created_at),
    INDEX idx_trade_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='交易记录表 - 记录每次下单执行结果，一个signal_id可对应多条Trade';


-- ============================================================
-- 2. Ledger - 账本流水表
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_ledger (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 关联ID
    account_id INT NOT NULL COMMENT '账户ID',
    member_id INT NOT NULL COMMENT '会员ID',
    trade_id BIGINT NULL COMMENT '关联交易ID',
    signal_id VARCHAR(64) NULL COMMENT '关联信号ID',
    
    -- 流水类型
    ledger_type VARCHAR(32) NOT NULL COMMENT 'TRADE_FEE/TRADE_PNL/FREEZE/UNFREEZE/DEPOSIT/WITHDRAW',
    
    -- 金额
    currency VARCHAR(16) NOT NULL DEFAULT 'USDT' COMMENT '币种',
    amount DECIMAL(20, 8) NOT NULL COMMENT '变动金额（正为入，负为出）',
    balance_before DECIMAL(20, 8) NULL COMMENT '变动前余额',
    balance_after DECIMAL(20, 8) NULL COMMENT '变动后余额',
    
    -- 描述
    description VARCHAR(256) NULL COMMENT '流水描述',
    
    -- 时间
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 追踪
    request_id VARCHAR(64) NULL COMMENT '请求追踪ID',
    
    -- 索引
    INDEX idx_ledger_account_id (account_id),
    INDEX idx_ledger_member_id (member_id),
    INDEX idx_ledger_trade_id (trade_id),
    INDEX idx_ledger_signal_id (signal_id),
    INDEX idx_ledger_account_time (account_id, created_at),
    INDEX idx_ledger_type_time (ledger_type, created_at),
    INDEX idx_ledger_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='账本流水表 - 记录资金变动(手续费/盈亏/冻结/解冻等)，append-only';


-- ============================================================
-- 3. FreezeRecord - 冻结记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_freeze (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 关联ID
    account_id INT NOT NULL COMMENT '账户ID',
    member_id INT NOT NULL COMMENT '会员ID',
    signal_id VARCHAR(64) NULL COMMENT '关联信号ID',
    task_id VARCHAR(64) NULL COMMENT '关联任务ID',
    
    -- 冻结类型
    freeze_type VARCHAR(32) NOT NULL COMMENT 'MARGIN/RISK_CONTROL/MANUAL',
    
    -- 金额
    currency VARCHAR(16) NOT NULL DEFAULT 'USDT' COMMENT '币种',
    amount DECIMAL(20, 8) NOT NULL COMMENT '冻结金额',
    
    -- 状态
    status VARCHAR(16) NOT NULL DEFAULT 'frozen' COMMENT 'frozen/released',
    
    -- 时间
    frozen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at DATETIME NULL COMMENT '解冻时间',
    
    -- 描述
    reason VARCHAR(256) NULL COMMENT '冻结原因',
    
    -- 追踪
    request_id VARCHAR(64) NULL COMMENT '请求追踪ID',
    
    -- 索引
    INDEX idx_freeze_account_id (account_id),
    INDEX idx_freeze_member_id (member_id),
    INDEX idx_freeze_signal_id (signal_id),
    INDEX idx_freeze_task_id (task_id),
    INDEX idx_freeze_account_status (account_id, status),
    INDEX idx_freeze_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='冻结记录表 - 记录保证金/风控冻结，支持frozen/released状态';


-- ============================================================
-- 4. SignalEvent - 信号状态事件表
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_signal_event (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 信号ID（核心索引）
    signal_id VARCHAR(64) NOT NULL COMMENT '信号ID',
    
    -- 关联ID
    task_id VARCHAR(64) NULL COMMENT '执行任务ID',
    account_id INT NULL COMMENT '账户ID',
    
    -- 事件类型与状态
    event_type VARCHAR(32) NOT NULL COMMENT 'CREATED/RISK_CHECK/RISK_PASSED/RISK_REJECTED/DISPATCHED/EXECUTED/FAILED',
    status VARCHAR(16) NOT NULL COMMENT 'pending/passed/rejected/executing/executed/failed',
    
    -- 来源服务
    source_service VARCHAR(32) NOT NULL COMMENT 'signal-hub/risk-control/execution-dispatcher/crypto-node',
    
    -- 事件详情
    detail TEXT NULL COMMENT '事件详情（JSON）',
    error_code VARCHAR(32) NULL COMMENT '错误码',
    error_message TEXT NULL COMMENT '错误信息',
    
    -- 时间
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 追踪
    request_id VARCHAR(64) NULL COMMENT '请求追踪ID',
    
    -- 索引
    INDEX idx_signal_event_signal_id (signal_id),
    INDEX idx_signal_event_account_id (account_id),
    INDEX idx_signal_event_signal_time (signal_id, created_at),
    INDEX idx_signal_event_type_time (event_type, created_at),
    INDEX idx_signal_event_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='信号状态事件表 - 记录信号完整链路(CREATED→RISK→EXECUTED)，用于追踪审计';


-- ============================================================
-- 完成
-- ============================================================
SELECT 'Facts Layer tables created successfully!' AS result;
