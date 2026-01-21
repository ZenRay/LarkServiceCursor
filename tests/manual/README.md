# 手动交互式测试指南

T082 [Phase 8] Create manual test documentation

## 概述

本目录包含手动交互式测试脚本，用于验证 WebSocket 用户授权方案的真实授权流程。

## 前提条件

### 1. 飞书开放平台配置

- ✅ 已创建飞书应用
- ✅ 已获取 `APP_ID` 和 `APP_SECRET`
- ✅ 已配置应用权限（至少包含消息发送权限）
- ✅ 已配置 WebSocket 事件订阅（如果使用 WebSocket 模式）

### 2. 环境配置

创建 `.env` 文件（或使用现有的）：

```bash
# 必需配置
APP_ID=cli_xxxxxxxxxxxxxxxx
APP_SECRET=your_app_secret_here

# 数据库配置（可选，默认使用 SQLite）
DATABASE_URL=postgresql://lark_user:lark_password_123@localhost:5432/lark_service
# 或使用 SQLite 测试
# DATABASE_URL=sqlite:///./test_auth.db
```

### 3. 依赖安装

```bash
# 安装所有依赖
uv pip install -r requirements.txt

# 或使用 pip
pip install -r requirements.txt
```

### 4. 数据库准备

如果使用 PostgreSQL：

```bash
# 启动 Docker Compose 服务
docker-compose up -d postgres

# 运行数据库迁移
alembic upgrade head
```

如果使用 SQLite：

```bash
# 无需额外配置，脚本会自动创建数据库文件
```

### 5. 测试用户准备

- 获取你的飞书 OpenID（格式：`ou_xxxxxxxxxxxxxxxx`）
- 确保测试用户在飞书中可以接收消息

## 运行测试

### 基本用法

```bash
# 从项目根目录运行
python tests/manual/interactive_auth_test.py
```

### 测试模式

#### 模式 1: WebSocket 模式（推荐）

这是完整的端到端测试模式，使用真实的 WebSocket 连接。

```bash
python tests/manual/interactive_auth_test.py
# 当提示时选择 'y' 启用 WebSocket
```

**流程**：
1. 脚本启动 WebSocket 连接
2. 发送授权卡片到你的飞书账号
3. 在飞书中打开卡片，点击"授权"按钮
4. WebSocket 接收授权事件
5. 自动完成 Token 交换和存储
6. 验证 Token 可用

**优点**：
- ✅ 完整的端到端测试
- ✅ 真实的授权流程
- ✅ 自动处理回调事件

**注意事项**：
- 需要稳定的网络连接
- 需要在 120 秒内完成授权
- 需要配置 WebSocket 事件订阅

#### 模式 2: 手动模式

这是简化的测试模式，不使用 WebSocket 连接。

```bash
python tests/manual/interactive_auth_test.py
# 当提示时选择 'n' 禁用 WebSocket
```

**流程**：
1. 发送授权卡片到你的飞书账号
2. 在飞书中打开卡片，点击"授权"按钮
3. 手动输入授权码（从卡片回调中获取）
4. 验证 Token 存储

**优点**：
- ✅ 不需要 WebSocket 配置
- ✅ 适合调试和开发

**注意事项**：
- 需要手动获取授权码
- 功能不完整（Token 交换需要手动实现）

## 测试步骤详解

### Step 1: 初始化数据库

脚本会自动创建数据库表结构。

**预期输出**：
```
[Step 1] Initializing database...
------------------------------------------------------------
✅ Database initialized
```

**故障排查**：
- 检查 `DATABASE_URL` 是否正确
- 检查数据库服务是否运行
- 检查数据库权限

### Step 2: 初始化组件

脚本会创建授权管理器、消息客户端和卡片处理器。

**预期输出**：
```
[Step 2] Initializing components...
------------------------------------------------------------
✅ Components initialized
```

**故障排查**：
- 检查 `APP_ID` 和 `APP_SECRET` 是否正确
- 检查依赖是否安装完整

### Step 3: 启动 WebSocket 连接

如果选择 WebSocket 模式，脚本会建立 WebSocket 长连接。

**预期输出**：
```
[Step 3] Starting WebSocket connection...
------------------------------------------------------------
Enable WebSocket connection? (y/n): y
✅ WebSocket connected
```

**故障排查**：
- 检查网络连接
- 检查 `APP_ID` 和 `APP_SECRET` 是否正确
- 检查飞书开放平台是否配置了 WebSocket 事件订阅
- 查看日志：`logs/websocket.log`

### Step 4: 输入测试用户信息

输入你的飞书 OpenID。

**预期输出**：
```
[Step 4] Enter test user information...
------------------------------------------------------------
Enter your OpenID (ou_xxx): ou_1234567890abcdef
```

**如何获取 OpenID**：
1. 在飞书开放平台控制台
2. 进入"开发调试" → "API 调试"
3. 调用 `/open-apis/contact/v3/users/me` 接口
4. 从响应中获取 `open_id`

### Step 5: 创建授权会话

脚本会创建一个新的授权会话。

**预期输出**：
```
[Step 5] Creating authorization session...
------------------------------------------------------------
✅ Session created: 12345678-1234-1234-1234-123456789abc
ℹ️  Session expires at: 2026-01-20 12:34:56+00:00
```

**故障排查**：
- 检查数据库连接
- 检查 `user_auth_sessions` 表是否存在

### Step 6: 发送授权卡片

脚本会发送授权卡片到你的飞书账号。

**预期输出**：
```
[Step 6] Sending authorization card...
------------------------------------------------------------
✅ Card sent successfully (message_id: om_1234567890abcdef)
ℹ️  📱 Please check Feishu and click 'Authorize' button
```

**故障排查**：
- 检查应用是否有消息发送权限
- 检查 OpenID 是否正确
- 检查飞书消息是否被拦截

### Step 7: 等待授权

**WebSocket 模式**：

脚本会等待 WebSocket 事件（最多 120 秒）。

**预期输出**：
```
[Step 7] Waiting for authorization...
------------------------------------------------------------
ℹ️  Waiting for WebSocket event (max 120 seconds)...
ℹ️  Received card action event
✅ Authorization completed!
ℹ️  User: 张三
ℹ️  Email: zhangsan@example.com
ℹ️  Mobile: +86-13800138000
ℹ️  Token expires: 2026-01-27 12:34:56+00:00
```

**手动模式**：

需要手动输入授权码。

**预期输出**：
```
[Step 7] Waiting for authorization...
------------------------------------------------------------
ℹ️  Manual mode: Enter authorization details
Enter authorization code (from card callback): auth_code_xyz
```

**故障排查**：
- 确保在飞书中点击了"授权"按钮
- 检查 WebSocket 连接是否断开
- 查看数据库：`SELECT * FROM user_auth_sessions WHERE session_id='xxx'`
- 检查飞书应用权限配置

### Step 8: 验证 Token 检索

脚本会验证 Token 是否可以正确检索。

**预期输出**：
```
[Step 8] Verifying token retrieval...
------------------------------------------------------------
✅ Token retrieved successfully
ℹ️  Token (first 20 chars): u-1234567890abcdef...
```

**故障排查**：
- 检查 Token 是否已存储
- 检查 Token 是否已过期
- 查看数据库：`SELECT * FROM user_auth_sessions WHERE user_id='xxx'`

### Step 9: 测试 aPaaS API 调用（可选）

可选步骤，测试使用 Token 调用 aPaaS API。

**预期输出**：
```
[Step 9] Test aPaaS API call (optional)...
------------------------------------------------------------
Test aPaaS API call? (y/n): y
ℹ️  Testing aPaaS API call...
ℹ️  aPaaS API test not implemented in this script
ℹ️  Token is available for use in aPaaS client
```

### Step 10: 清理

脚本会清理资源。

**预期输出**：
```
[Step 10] Cleaning up...
------------------------------------------------------------
✅ WebSocket disconnected
✅ Database session closed

============================================================
  Test Completed
============================================================

ℹ️  Summary:
ℹ️    - Session ID: 12345678-1234-1234-1234-123456789abc
ℹ️    - User ID: ou_1234567890abcdef
ℹ️    - Session State: completed
ℹ️    - Test Time: 2026-01-20 12:34:56.789012+00:00
```

## 常见问题

### Q1: WebSocket 连接失败

**症状**：
```
❌ WebSocket connection failed: Connection refused
```

**解决方案**：
1. 检查网络连接
2. 检查 `APP_ID` 和 `APP_SECRET` 是否正确
3. 检查飞书开放平台是否配置了 WebSocket 事件订阅
4. 尝试使用手动模式

### Q2: 授权超时

**症状**：
```
❌ Timeout: Authorization not completed
```

**解决方案**：
1. 确保在 120 秒内点击了"授权"按钮
2. 检查 WebSocket 连接是否断开
3. 检查飞书消息是否被拦截
4. 查看数据库中的会话状态

### Q3: Token 获取失败

**症状**：
```
❌ Token not found
```

**解决方案**：
1. 检查授权流程是否完成
2. 查看数据库：`SELECT * FROM user_auth_sessions WHERE user_id='xxx'`
3. 检查 Token 是否已过期
4. 重新运行测试

### Q4: 数据库连接失败

**症状**：
```
❌ Database initialization failed: could not connect to server
```

**解决方案**：
1. 检查 PostgreSQL 服务是否运行：`docker-compose ps`
2. 检查 `DATABASE_URL` 是否正确
3. 尝试使用 SQLite：`DATABASE_URL=sqlite:///./test_auth.db`

### Q5: 权限不足

**症状**：
```
❌ Card sending failed: permission denied
```

**解决方案**：
1. 检查飞书应用权限配置
2. 确保应用有消息发送权限
3. 确保应用有用户信息读取权限

## 测试验证清单

完成测试后，请验证以下内容：

- [ ] WebSocket 连接成功建立
- [ ] 授权卡片成功发送到飞书
- [ ] 在飞书中可以看到授权卡片
- [ ] 点击"授权"按钮后，卡片更新为成功状态
- [ ] Token 成功存储到数据库
- [ ] Token 可以正确检索
- [ ] 用户信息（姓名、邮箱、手机号）正确存储
- [ ] 会话状态更新为 "completed"
- [ ] WebSocket 连接正常断开
- [ ] 数据库会话正常关闭

## 数据库验证

测试完成后，可以手动验证数据库中的数据：

```sql
-- 查看所有授权会话
SELECT
    session_id,
    app_id,
    user_id,
    state,
    auth_method,
    user_name,
    email,
    mobile,
    created_at,
    expires_at,
    token_expires_at
FROM user_auth_sessions
ORDER BY created_at DESC
LIMIT 10;

-- 查看特定用户的会话
SELECT * FROM user_auth_sessions
WHERE user_id = 'ou_1234567890abcdef'
ORDER BY created_at DESC;

-- 查看过期的会话
SELECT * FROM user_auth_sessions
WHERE expires_at < NOW()
ORDER BY created_at DESC;

-- 查看 Token 即将过期的会话
SELECT * FROM user_auth_sessions
WHERE token_expires_at < NOW() + INTERVAL '1 day'
AND state = 'completed'
ORDER BY token_expires_at ASC;
```

## 日志查看

测试过程中的日志可以在以下位置查看：

```bash
# WebSocket 日志
tail -f logs/websocket.log

# 应用日志
tail -f logs/app.log

# 授权日志
tail -f logs/auth.log
```

## 性能测试

如果需要进行性能测试，可以修改脚本进行批量测试：

```python
# 在脚本中添加循环
for i in range(100):
    session = auth_manager.create_session(
        app_id=app_id,
        user_id=f"ou_test_user_{i:03d}",
        auth_method="websocket_card"
    )
    # ... 完成授权流程
```

## 安全注意事项

⚠️ **重要**：

1. **不要提交 `.env` 文件**到版本控制系统
2. **不要在日志中记录完整的 Token**
3. **测试完成后清理测试数据**
4. **不要在生产环境运行测试脚本**
5. **定期轮换 `APP_SECRET`**

## 清理测试数据

测试完成后，可以清理测试数据：

```sql
-- 删除测试会话
DELETE FROM user_auth_sessions
WHERE user_id LIKE 'ou_test_%';

-- 或删除所有过期会话
DELETE FROM user_auth_sessions
WHERE expires_at < NOW();
```

## 支持

如果遇到问题，请：

1. 查看本文档的"常见问题"部分
2. 查看日志文件
3. 查看数据库中的数据
4. 查看飞书开放平台的错误日志
5. 联系开发团队

## 参考资料

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [WebSocket 事件订阅](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN)
- [用户身份与授权](https://open.feishu.cn/document/ukTMukTMukTM/uMTNz4yM1MjLzUzM)
- [项目 README](../../README.md)
- [功能规范](../../specs/002-websocket-user-auth/spec.md)
- [快速开始指南](../../specs/002-websocket-user-auth/quickstart.md)

---

**最后更新**: 2026-01-20
**版本**: 1.0.0
**维护者**: LarkService Team
