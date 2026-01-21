# 手动测试指南 - 用户授权流程

本文档说明如何使用 `test.py` 脚本测试完整的用户授权流程。

## 📋 前置准备

### 1. 环境配置

在 `.env` 文件中配置以下变量：

```bash
# 飞书应用配置
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
LARK_VERIFICATION_TOKEN=xxx
LARK_ENCRYPT_KEY=xxx
LARK_CONFIG_ENCRYPTION_KEY=xxx

# 测试用户配置（二选一）
TEST_OPEN_ID=ou_xxx                    # 直接配置 OpenID（推荐）
TEST_USER_EMAIL=test@company.com       # 或通过邮箱自动获取

# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark_user
POSTGRES_PASSWORD=lark_password_123

# 回调服务器配置
CALLBACK_SERVER_PORT=8000
```

### 2. 启动 PostgreSQL

```bash
docker compose up -d postgres
```

### 3. 运行数据库迁移

```bash
alembic upgrade head
```

### 4. 安装 ngrok（用于内网穿透）

如果没有安装 ngrok：

```bash
# macOS
brew install ngrok

# Linux
# 访问 https://ngrok.com/download 下载

# 配置 ngrok authtoken（首次使用）
ngrok config add-authtoken YOUR_TOKEN
```

---

## 🚀 测试步骤

### 步骤 1：启动 ngrok

在**第一个终端**中启动 ngrok：

```bash
ngrok http 8000
```

ngrok 会显示类似以下内容：

```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

**复制这个公网 URL**（例如 `https://abc123.ngrok.io`）

### 步骤 2：配置飞书开放平台

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 进入你的应用
3. 找到 **"事件与回调"** → **"回调配置"**

#### 配置回调地址

- 回调 URL：`https://abc123.ngrok.io/callback`（使用你的 ngrok URL）
- 点击"保存"，飞书会进行 URL 验证

#### 添加回调事件

- 勾选：`card.action.trigger` (卡片交互)

#### 配置重定向 URL

- 在 **"安全设置"** → **"重定向 URL"** 中添加：
  ```
  https://open.feishu.cn/
  ```

### 步骤 3：运行测试脚本

在**第二个终端**中运行测试：

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
export PYTHONPATH=/home/ray/Documents/Files/LarkServiceCursor/src:$PYTHONPATH
python test.py
```

### 步骤 4：完成授权

测试脚本会：

1. ✅ 初始化所有服务
2. ✅ 启动 HTTP 回调服务器（本地 8000 端口）
3. ✅ 发送授权卡片到你的飞书账号
4. ⏳ 等待你完成授权

**在飞书中操作：**

1. 打开飞书，查看收到的授权卡片
2. 点击"授权"按钮
3. 浏览器会打开飞书授权页面
4. 点击"同意"授权
5. 飞书会通过 HTTP 回调通知服务器

测试脚本会自动检测授权完成并显示结果。

---

## 📊 测试输出示例

### 成功的测试输出

```
======================================================================
  WebSocket 用户授权 - 完整流程测试（带 HTTP 回调）
======================================================================

[步骤 1] 加载环境变量
----------------------------------------------------------------------
✅ APP_ID: cli_a8d27f9bf63...
✅ 加密密钥已加载

[步骤 2] 初始化配置和服务
----------------------------------------------------------------------
✅ 应用配置已添加
✅ Token 存储服务已创建
✅ 凭证池已创建
✅ App Access Token: t-g1041lg0YGCL35FYBXJZIQXEBFHG...

[步骤 3] 获取测试用户 OpenID
----------------------------------------------------------------------
✅ 测试用户 OpenID: ou_f22c565bf4f3ca8b3fa5bd2f20039949

[步骤 4] 初始化数据库
----------------------------------------------------------------------
✅ 数据库已初始化

[步骤 5] 创建授权组件
----------------------------------------------------------------------
✅ 授权会话管理器已创建
✅ 消息客户端已创建
✅ 卡片授权处理器已创建

[步骤 6] 启动 HTTP 回调服务器
----------------------------------------------------------------------
✅ 回调处理器已注册
✅ HTTP 回调服务器已启动: http://127.0.0.1:8000
ℹ️  健康检查: http://127.0.0.1:8000/health
ℹ️  回调端点: http://127.0.0.1:8000/callback

[步骤 7] 飞书开放平台配置
----------------------------------------------------------------------
⚠️  重要：请确保已在飞书开放平台配置以下内容：
...

[步骤 8] 创建授权会话
----------------------------------------------------------------------
✅ 授权会话已创建
ℹ️  Session ID: 971703e2-2816-4f04-a098-e7c18a9cf279
ℹ️  状态: pending

[步骤 9] 发送授权卡片
----------------------------------------------------------------------
✅ 授权卡片已发送
ℹ️  Message ID: om_x100b583d268eb4b8b36b3ec2b4bc4a6

======================================================================
📱 请在飞书中查看并操作：
  1. 点击授权卡片中的'授权'按钮
  2. 在打开的浏览器中点击'同意'
  3. 授权完成后飞书会通过 HTTP 回调通知服务器
======================================================================

[步骤 10] 等待授权完成
----------------------------------------------------------------------
ℹ️  等待用户授权（最多等待 120 秒）...
等待中... (24/120s)
✅ 授权成功！

[步骤 11] 验证授权结果
----------------------------------------------------------------------
✅ 授权完成！

📊 授权信息：
  Session ID: 971703e2-2816-4f04-a098-e7c18a9cf279
  状态: completed
  User Access Token: u-8xG4hJ5K2pT3nR7sW9vQ1mL...
  Token 过期时间: 2026-01-22 09:30:45
  用户姓名: 张三
  用户邮箱: zhangsan@company.com

验证 Token 存储...
✅ Token 已存储到 token_storage 表
ℹ️  Token 类型: user_access_token
ℹ️  过期时间: 2026-01-22 09:30:45

======================================================================
  测试完成
======================================================================
🎉 授权流程测试成功！

📊 最终结果:
  Session ID: 971703e2-2816-4f04-a098-e7c18a9cf279
  Session 状态: completed
  Test OpenID: ou_f22c565bf4f3ca8b3fa5bd2f20039949

清理资源...
✅ HTTP 回调服务器已停止
✅ 清理完成
```

---

## 🔍 故障排查

### 问题 1：ngrok 连接失败

**症状：**
```
ERR_NGROK_108: ngrok returned error 108
```

**解决方案：**
- 检查 ngrok 是否正确安装
- 确认已配置 ngrok authtoken
- 尝试重启 ngrok

### 问题 2：飞书回调验证失败

**症状：**
- 飞书开放平台显示"回调地址不可达"
- URL 验证失败

**解决方案：**
1. 确认 ngrok 正在运行
2. 确认回调 URL 格式正确：`https://xxx.ngrok.io/callback`
3. 检查 HTTP 回调服务器是否已启动：`curl http://localhost:8000/health`

### 问题 3：授权超时

**症状：**
```
❌ 超时：未收到授权响应
```

**可能原因：**
1. 用户未在飞书中点击授权
2. 回调地址配置错误
3. ngrok 断开连接

**解决方案：**
1. 确认已在飞书中点击"授权"按钮
2. 检查 ngrok 控制台是否收到请求
3. 查看回调服务器日志

### 问题 4：签名验证失败

**症状：**
```
Signature verification failed
```

**解决方案：**
- 确认 `.env` 中的 `LARK_ENCRYPT_KEY` 与飞书开放平台一致
- 检查 `LARK_VERIFICATION_TOKEN` 是否正确

### 问题 5：授权码交换失败

**症状：**
```
Failed to exchange authorization code
```

**解决方案：**
- 确认已在飞书开放平台配置 `redirect_uri`: `https://open.feishu.cn/`
- 检查应用权限是否正确

---

## 📝 调试技巧

### 查看 ngrok 请求日志

访问 ngrok 的 Web UI：

```
http://localhost:4040
```

这里可以看到所有通过 ngrok 的 HTTP 请求。

### 查看回调服务器健康状态

```bash
curl http://localhost:8000/health
```

响应：
```json
{
  "status": "ok",
  "message": "Lark Callback Server is running",
  "registered_handlers": ["card_action_trigger"]
}
```

### 手动测试回调端点

```bash
curl -X POST http://localhost:8000/callback \
  -H "Content-Type: application/json" \
  -d '{
    "type": "url_verification",
    "challenge": "test_challenge",
    "token": "your_verification_token"
  }'
```

---

## 🎯 测试检查清单

在运行测试前，确保：

- [ ] PostgreSQL 已启动
- [ ] 数据库迁移已完成
- [ ] `.env` 文件已正确配置
- [ ] ngrok 已安装并启动
- [ ] 飞书开放平台已配置回调地址
- [ ] 飞书开放平台已配置重定向 URL
- [ ] 飞书开放平台已勾选 `card.action.trigger` 事件
- [ ] 测试用户的 OpenID 或邮箱已配置

---

## 📚 相关文档

- [回调服务器部署指南](./callback-server-deployment.md)
- [飞书开放平台文档](https://open.feishu.cn/document/)
- [ngrok 文档](https://ngrok.com/docs)
