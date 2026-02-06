-- 017: 租户增加奖励分配追踪字段 + 补建已有租户的根账户
-- tech_reward_total: 累计技术团队分配金额
-- undist_reward_total: 累计网体未分配金额（条件不满足归根账户的部分）

ALTER TABLE dim_tenant
    ADD COLUMN tech_reward_total   DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计技术团队分配' AFTER total_users,
    ADD COLUMN undist_reward_total DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '累计网体未分配' AFTER tech_reward_total;
