-- 性能优化：订单/成交列表按租户+账户+时间查询的复合索引
-- 用于 GET /api/orders、GET /api/fills 的 list_orders/list_fills 查询（ORDER BY time DESC）
--
-- 推荐用脚本执行（幂等、可重复跑）：
--   PYTHONPATH=. python3 scripts/run_migration_013.py
--
-- 或手动执行下面 SQL（若索引已存在会报错，可忽略）：

-- fact_order: 按租户+账户+创建时间排序
ALTER TABLE fact_order ADD INDEX idx_order_tenant_account_time (tenant_id, account_id, created_at);

-- fact_fill: 按租户+账户+成交时间排序
ALTER TABLE fact_fill ADD INDEX idx_fill_tenant_account_time (tenant_id, account_id, filled_at);
