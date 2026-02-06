-- 012: 统一 member_id → user_id
-- 将事实表中剩余的 member_id 列重命名为 user_id，保持全项目命名一致
-- 注：fact_trade / fact_ledger / fact_freeze 建表时已为 user_id，仅 fact_audit_log 需改

ALTER TABLE fact_audit_log CHANGE COLUMN member_id user_id INT DEFAULT NULL COMMENT '用户ID';
