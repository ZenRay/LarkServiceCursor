# 超简单测试指南

如果你已经在飞书开放平台配置了 `http://localhost:8000/callback`，直接运行这个测试！

## 🚀 一键测试

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
export PYTHONPATH=/home/ray/Documents/Files/LarkServiceCursor/src:$PYTHONPATH
python test_simple.py
```

就这么简单！ ✅

## 📋 前提条件

### 1. 环境变量配置（.env）

```bash
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
LARK_VERIFICATION_TOKEN=xxx
LARK_ENCRYPT_KEY=xxx
LARK_CONFIG_ENCRYPTION_KEY=xxx

# 测试用户（二选一）
TEST_OPEN_ID=ou_xxx
TEST_USER_EMAIL=test@company.com
```

### 2. 飞书开放平台配置

确保已配置：

1. **回调配置** → 回调 URL：`http://localhost:8000/callback`
2. **订阅事件** → 勾选：`card.action.trigger`
3. **重定向 URL** → 添加：`https://open.feishu.cn/`

### 3. 数据库运行

```bash
docker compose up -d postgres
alembic upgrade head
```

## 📱 测试流程

运行 `python test_simple.py` 后：

1. ✅ 脚本自动启动 HTTP 服务器（localhost:8000）
2. ✅ 自动发送授权卡片到飞书
3. 📱 **你在飞书中点击"授权"按钮**
4. 🌐 **在浏览器中点击"同意"**
5. ✅ 飞书自动回调到 localhost:8000/callback
6. ✅ 脚本自动检测授权完成

## 🎯 成功标志

如果看到：

```
🎉 授权完成！

📊 授权信息：
   Session ID: xxx
   状态: completed
   User Access Token: u-8xG4hJ5K2pT3nR7sW9vQ1mL...
   Token 过期时间: 2026-01-22 09:30:45

✅ Token 已存储到数据库

  测试成功！🎉
```

恭喜！授权功能正常运行！ 🎉

## ⚠️ 常见问题

### Q: 为什么飞书能访问 localhost？

**A:** 飞书客户端在你的本地电脑运行，所以可以访问 localhost。这是最简单的测试方式！

### Q: 授权超时怎么办？

**A:** 确认：
1. 飞书开放平台已配置 `http://localhost:8000/callback`
2. 已勾选 `card.action.trigger` 事件
3. 在飞书中点击了授权按钮

### Q: 健康检查

```bash
# 测试服务器是否运行
curl http://localhost:8000/health

# 应该返回：
# {"status": "ok", ...}
```

## 📚 其他测试方案

如果你需要其他测试方式：

- **使用 ngrok/localtunnel**: 查看 `QUICK_START_TEST.md`
- **详细测试指南**: 查看 `docs/manual-testing-guide.md`
- **无 ngrok 方案**: 查看 `docs/local-testing-without-ngrok.md`

---

**这是最简单的测试方式！** 🚀
