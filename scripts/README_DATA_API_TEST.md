# Data-API 全量接口测试

## 运行

```bash
# 在项目根目录
PYTHONPATH=. python3 scripts/test_data_api_all.py
```

## 前置条件

1. **data-api 已启动**（默认 127.0.0.1:8026）
2. **管理员账号**：`dim_admin` 表中存在用户 `admin`，密码 `admin123`
3. **数据库迁移已执行**：
   - `migrations/014_strategy_show_to_user.sql`（dim_strategy 增加 show_to_user 等列）
   - `migrations/015_tenant_strategy_instance.sql`（新建 dim_tenant_strategy 表）

未执行上述迁移时，以下接口会返回 **500**：
- GET/POST /api/strategies、GET /api/strategies/{id}
- GET/POST/PUT/DELETE /api/tenants/{id}/tenant-strategies、copy-from-master

执行迁移示例（按实际库名/账号修改）：

```bash
mysql -u root -p ironbull < migrations/014_strategy_show_to_user.sql
mysql -u root -p ironbull < migrations/015_tenant_strategy_instance.sql
```

## 已修复问题（代码侧）

- **withdrawals**：审核/拒绝提现使用 `admin["admin_id"]`（原误用 `admin["id"]` 导致 500）
- **strategies**：更新策略使用 Pydantic v2 的 `model_dump(exclude_unset=True)`（原 `dict()` 在 Pydantic 2.x 下会 500）
- **tenant_strategies**：同上，PUT 更新实例已兼容 model_dump

修复后需**重启 data-api** 生效。
