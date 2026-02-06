-- 016: ProfitPool 增加分配追踪字段
-- 追踪利润池中每部分资金去向，解决「剩余未分配」不可追踪的问题

ALTER TABLE fact_profit_pool
    ADD COLUMN tech_amount           DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '技术团队 10%' AFTER pool_amount,
    ADD COLUMN network_amount        DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '网体总额 20%' AFTER tech_amount,
    ADD COLUMN platform_amount       DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '平台留存 70%' AFTER network_amount,
    ADD COLUMN direct_distributed    DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '直推已发放' AFTER platform_amount,
    ADD COLUMN diff_distributed      DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '级差已发放' AFTER direct_distributed,
    ADD COLUMN peer_distributed      DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '平级已发放' AFTER diff_distributed,
    ADD COLUMN network_undistributed DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '网体未分配(条件不满足)' AFTER peer_distributed;

-- 回填已结算的记录（status=2 的老数据）
UPDATE fact_profit_pool
SET tech_amount           = pool_amount * 0.10,
    network_amount        = pool_amount * 0.20,
    platform_amount       = pool_amount * 0.70
WHERE status = 2 AND tech_amount = 0;
