# 快速开始 - 用户授权测试

这是一个快速测试用户授权流程的指南。

## 🚀 一键测试（3 步）

### 第 1 步：启动 ngrok（终端 1）

```bash
ngrok http 8000
```

**记下显示的公网 URL**，例如：`https://abc123.ngrok.io`

### 第 2 步：配置飞书（浏览器）

1. 访问 https://open.feishu.cn/app
2. 进入你的应用 → **"事件与回调"** → **"回调配置"**
3. 回调 URL：`https://abc123.ngrok.io/callback`（使用你的 ngrok URL）
4. 勾选事件：`card.action.trigger`
5. **"安全设置"** → **"重定向 URL"** → 添加：`https://open.feishu.cn/`

### 第 3 步：运行测试（终端 2）

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
export PYTHONPATH=/home/ray/Documents/Files/LarkServiceCursor/src:$PYTHONPATH
python test.py
```

**在飞书中操作：**
1. 查看收到的授权卡片
2. 点击"授权"按钮
3. 在浏览器中点击"同意"

✅ 完成！

---

## 📋 环境变量配置

确保 `.env` 文件包含：

```bash
# 必需
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
LARK_VERIFICATION_TOKEN=xxx
LARK_ENCRYPT_KEY=xxx
LARK_CONFIG_ENCRYPTION_KEY=xxx

# 测试用户（二选一）
TEST_OPEN_ID=ou_xxx                    # 推荐
TEST_USER_EMAIL=test@company.com       # 或这个

# 数据库（默认值）
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark_user
POSTGRES_PASSWORD=lark_password_123

# 回调端口（可选，默认 8000）
CALLBACK_SERVER_PORT=8000
```

---

## 🛠️ 前置检查

运行测试前确保：

```bash
# 1. PostgreSQL 已启动
docker compose up -d postgres

# 2. 数据库迁移已完成
alembic upgrade head

# 3. ngrok 已安装
which ngrok  # 应该显示 ngrok 路径
```

---

## ❓ 常见问题

### Q: ngrok 显示 "ERR_NGROK_108"

**A:** 需要配置 authtoken：
```bash
ngrok config add-authtoken YOUR_TOKEN
```
在 https://dashboard.ngrok.com/get-started/your-authtoken 获取 token

### Q: 飞书显示"回调地址不可达"

**A:** 检查：
1. ngrok 是否在运行
2. URL 格式是否正确：`https://xxx.ngrok.io/callback`
3. 测试端点：`curl http://localhost:8000/health`

### Q: 授权超时

**A:** 确认：
1. 已在飞书中点击授权
2. ngrok 收到了请求（查看 http://localhost:4040）
3. 回调服务器正在运行

---

## 📖 详细文档

更多信息请查看：
- [完整测试指南](./docs/manual-testing-guide.md)
- [回调服务器部署](./docs/callback-server-deployment.md)

---

## 🎯 测试成功标志

如果看到以下输出，说明测试成功：

```
✅ 授权成功！

📊 授权信息：
  Session ID: xxx
  状态: completed
  User Access Token: u-8xG4hJ5K2pT3nR7sW9vQ1mL...
  Token 过期时间: 2026-01-22 09:30:45

🎉 授权流程测试成功！
```

**恭喜！用户授权功能已成功运行！** 🎉
