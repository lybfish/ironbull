-- ============================================================
-- IronBull v1 Phase 2 - 审计日志表
-- ============================================================

USE ironbull;

-- ============================================================
-- AuditLog - 审计日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 关联ID
    signal_id VARCHAR(64) NULL COMMENT '信号ID',
    task_id VARCHAR(64) NULL COMMENT '执行任务ID',
    account_id INT NULL COMMENT '账户ID',
    member_id INT NULL COMMENT '会员ID',
    
    -- 审计动作
    action VARCHAR(64) NOT NULL COMMENT '动作类型',
    
    -- 状态变更
    status_before VARCHAR(32) NULL COMMENT '变更前状态',
    status_after VARCHAR(32) NULL COMMENT '变更后状态',
    
    -- 来源
    source_service VARCHAR(32) NOT NULL COMMENT '来源服务',
    source_ip VARCHAR(64) NULL COMMENT '来源IP',
    
    -- 详情
    detail TEXT NULL COMMENT '操作详情（JSON）',
    
    -- 错误信息
    success TINYINT DEFAULT 1 COMMENT '是否成功 1=成功 0=失败',
    error_code VARCHAR(32) NULL COMMENT '错误码',
    error_message TEXT NULL COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    
    -- 时间
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duration_ms INT NULL COMMENT '操作耗时(毫秒)',
    
    -- 追踪
    request_id VARCHAR(64) NULL COMMENT '请求追踪ID',
    trace_id VARCHAR(64) NULL COMMENT '链路追踪ID',
    
    -- 索引
    INDEX idx_audit_signal_id (signal_id),
    INDEX idx_audit_task_id (task_id),
    INDEX idx_audit_account_id (account_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_signal_time (signal_id, created_at),
    INDEX idx_audit_task_time (task_id, created_at),
    INDEX idx_audit_action_time (action, created_at),
    INDEX idx_audit_account_time (account_id, created_at),
    INDEX idx_audit_request_id (request_id),
    INDEX idx_audit_success (success)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='审计日志表 - 记录所有关键操作和状态变更';

SELECT 'Audit log table created!' AS result;
