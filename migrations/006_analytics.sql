-- Analytics Module Migration
-- 创建分析相关的事实表
-- 
-- 表：
-- - fact_performance_snapshot: 绩效快照（每日净值、收益率）
-- - fact_trade_statistics: 交易统计（胜率、盈亏比）
-- - fact_risk_metrics: 风险指标（夏普、回撤、VaR）

-- ============================================================
-- 1. fact_performance_snapshot - 绩效快照表
-- ============================================================

CREATE TABLE IF NOT EXISTS `fact_performance_snapshot` (
    `snapshot_id` VARCHAR(36) NOT NULL COMMENT '快照ID',
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '账户ID',
    `snapshot_date` DATE NOT NULL COMMENT '快照日期',
    
    -- 资金数据
    `balance` DOUBLE NOT NULL DEFAULT 0 COMMENT '账户余额',
    `position_value` DOUBLE NOT NULL DEFAULT 0 COMMENT '持仓市值',
    `total_equity` DOUBLE NOT NULL DEFAULT 0 COMMENT '总权益(余额+持仓)',
    
    -- 收益数据
    `daily_pnl` DOUBLE NOT NULL DEFAULT 0 COMMENT '当日盈亏',
    `daily_return` DOUBLE NOT NULL DEFAULT 0 COMMENT '当日收益率(%)',
    `cumulative_pnl` DOUBLE NOT NULL DEFAULT 0 COMMENT '累计盈亏',
    `cumulative_return` DOUBLE NOT NULL DEFAULT 0 COMMENT '累计收益率(%)',
    
    -- 基准数据
    `benchmark_value` DOUBLE DEFAULT NULL COMMENT '基准净值',
    `benchmark_return` DOUBLE DEFAULT NULL COMMENT '基准当日收益率(%)',
    `excess_return` DOUBLE DEFAULT NULL COMMENT '超额收益率(%)',
    
    -- 净值
    `net_value` DOUBLE NOT NULL DEFAULT 1.0 COMMENT '净值(初始1.0)',
    
    -- 元数据
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    PRIMARY KEY (`snapshot_id`),
    UNIQUE KEY `uk_performance_daily` (`tenant_id`, `account_id`, `snapshot_date`),
    INDEX `idx_performance_tenant_date` (`tenant_id`, `snapshot_date`),
    INDEX `idx_performance_account` (`account_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='绩效快照表（每日记录净值和收益率）';


-- ============================================================
-- 2. fact_trade_statistics - 交易统计表
-- ============================================================

CREATE TABLE IF NOT EXISTS `fact_trade_statistics` (
    `stat_id` VARCHAR(36) NOT NULL COMMENT '统计ID',
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '账户ID',
    
    -- 统计维度
    `period_type` VARCHAR(20) NOT NULL COMMENT '周期类型(daily/weekly/monthly/yearly/all)',
    `period_start` DATE NOT NULL COMMENT '周期开始日期',
    `period_end` DATE NOT NULL COMMENT '周期结束日期',
    
    -- 可选维度
    `strategy_code` VARCHAR(50) DEFAULT NULL COMMENT '策略代码(可选)',
    `symbol` VARCHAR(50) DEFAULT NULL COMMENT '交易对(可选)',
    
    -- 交易次数统计
    `total_trades` INT NOT NULL DEFAULT 0 COMMENT '总交易次数',
    `winning_trades` INT NOT NULL DEFAULT 0 COMMENT '盈利交易次数',
    `losing_trades` INT NOT NULL DEFAULT 0 COMMENT '亏损交易次数',
    `break_even_trades` INT NOT NULL DEFAULT 0 COMMENT '持平交易次数',
    
    -- 胜率
    `win_rate` DOUBLE NOT NULL DEFAULT 0 COMMENT '胜率(%)',
    
    -- 盈亏统计
    `total_profit` DOUBLE NOT NULL DEFAULT 0 COMMENT '总盈利',
    `total_loss` DOUBLE NOT NULL DEFAULT 0 COMMENT '总亏损(绝对值)',
    `net_profit` DOUBLE NOT NULL DEFAULT 0 COMMENT '净利润',
    
    -- 单笔统计
    `avg_profit` DOUBLE NOT NULL DEFAULT 0 COMMENT '平均盈利',
    `avg_loss` DOUBLE NOT NULL DEFAULT 0 COMMENT '平均亏损(绝对值)',
    `max_profit` DOUBLE NOT NULL DEFAULT 0 COMMENT '最大单笔盈利',
    `max_loss` DOUBLE NOT NULL DEFAULT 0 COMMENT '最大单笔亏损',
    
    -- 盈亏比
    `profit_loss_ratio` DOUBLE NOT NULL DEFAULT 0 COMMENT '盈亏比',
    `profit_factor` DOUBLE NOT NULL DEFAULT 0 COMMENT '获利因子',
    
    -- 持仓时间
    `avg_holding_period` DOUBLE NOT NULL DEFAULT 0 COMMENT '平均持仓时间(小时)',
    `max_holding_period` DOUBLE NOT NULL DEFAULT 0 COMMENT '最长持仓时间(小时)',
    
    -- 连续统计
    `max_consecutive_wins` INT NOT NULL DEFAULT 0 COMMENT '最大连胜次数',
    `max_consecutive_losses` INT NOT NULL DEFAULT 0 COMMENT '最大连亏次数',
    
    -- 交易量
    `total_volume` DOUBLE NOT NULL DEFAULT 0 COMMENT '总交易量(USDT)',
    `total_fee` DOUBLE NOT NULL DEFAULT 0 COMMENT '总手续费',
    
    -- 元数据
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`stat_id`),
    UNIQUE KEY `uk_trade_stats_period` (`tenant_id`, `account_id`, `period_type`, `period_start`, `strategy_code`, `symbol`),
    INDEX `idx_trade_stats_period` (`tenant_id`, `period_type`, `period_start`),
    INDEX `idx_trade_stats_strategy` (`strategy_code`),
    INDEX `idx_trade_stats_symbol` (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='交易统计表（按周期汇总）';


-- ============================================================
-- 3. fact_risk_metrics - 风险指标表
-- ============================================================

CREATE TABLE IF NOT EXISTS `fact_risk_metrics` (
    `metric_id` VARCHAR(36) NOT NULL COMMENT '指标ID',
    `tenant_id` INT NOT NULL COMMENT '租户ID',
    `account_id` INT NOT NULL COMMENT '账户ID',
    
    -- 统计周期
    `period_type` VARCHAR(20) NOT NULL COMMENT '周期类型(daily/weekly/monthly/yearly/all)',
    `period_start` DATE NOT NULL COMMENT '周期开始日期',
    `period_end` DATE NOT NULL COMMENT '周期结束日期',
    
    -- 可选维度
    `strategy_code` VARCHAR(50) DEFAULT NULL COMMENT '策略代码(可选)',
    
    -- 收益指标
    `total_return` DOUBLE NOT NULL DEFAULT 0 COMMENT '总收益率(%)',
    `annualized_return` DOUBLE NOT NULL DEFAULT 0 COMMENT '年化收益率(%)',
    
    -- 波动率
    `daily_volatility` DOUBLE NOT NULL DEFAULT 0 COMMENT '日波动率(%)',
    `annualized_volatility` DOUBLE NOT NULL DEFAULT 0 COMMENT '年化波动率(%)',
    
    -- 风险调整收益
    `sharpe_ratio` DOUBLE NOT NULL DEFAULT 0 COMMENT '夏普比率',
    `sortino_ratio` DOUBLE NOT NULL DEFAULT 0 COMMENT '索提诺比率',
    `calmar_ratio` DOUBLE NOT NULL DEFAULT 0 COMMENT '卡玛比率',
    
    -- 回撤指标
    `max_drawdown` DOUBLE NOT NULL DEFAULT 0 COMMENT '最大回撤(%)',
    `max_drawdown_duration` INT NOT NULL DEFAULT 0 COMMENT '最大回撤持续天数',
    `current_drawdown` DOUBLE NOT NULL DEFAULT 0 COMMENT '当前回撤(%)',
    
    -- VaR
    `var_95` DOUBLE DEFAULT NULL COMMENT '95% VaR',
    `var_99` DOUBLE DEFAULT NULL COMMENT '99% VaR',
    `cvar_95` DOUBLE DEFAULT NULL COMMENT '95% CVaR',
    
    -- Beta/Alpha
    `beta` DOUBLE DEFAULT NULL COMMENT 'Beta系数',
    `alpha` DOUBLE DEFAULT NULL COMMENT 'Alpha',
    
    -- 信息比率
    `information_ratio` DOUBLE DEFAULT NULL COMMENT '信息比率',
    `tracking_error` DOUBLE DEFAULT NULL COMMENT '跟踪误差',
    
    -- 元数据
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`metric_id`),
    UNIQUE KEY `uk_risk_metrics_period` (`tenant_id`, `account_id`, `period_type`, `period_start`, `strategy_code`),
    INDEX `idx_risk_metrics_period` (`tenant_id`, `period_type`, `period_start`),
    INDEX `idx_risk_metrics_strategy` (`strategy_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='风险指标表（按周期记录）';


-- ============================================================
-- 完成
-- ============================================================

SELECT 'Analytics migration completed successfully!' AS status;
