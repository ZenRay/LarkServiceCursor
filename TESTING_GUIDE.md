# 授权流程测试指南

本指南介绍如何测试飞书用户授权流程。

## 📋 前提条件

1. ✅ PostgreSQL 正在运行（Docker Compose）
2. ✅ `.env` 文件配置正确
3. ✅ 飞书应用配置了回调 URL: `http://localhost:8000/callback`

## 🚀 快速开始

### 方式 1: 两个终端测试（推荐）

**终端 1 - 启动回调服务器:**

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
python start_callback_server.py
```

你应该看到:
```
======================================================================
  飞书 OAuth 回调服务器
======================================================================
📍 服务器地址: http://127.0.0.1:8000
📍 回调端点: http://127.0.0.1:8000/callback
📍 健康检查: http://127.0.0.1:8000/health
✅ 服务组件初始化完成
✅ 回调服务器已启动
======================================================================
  服务器正在运行...
  按 Ctrl+C 停止
======================================================================
```

**终端 2 - 运行测试:**

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
python test_auth_flow.py
```

### 方式 2: 一体化测试（简单但可能有问题）

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
python test_simple.py
```

## 📱 测试流程

1. **启动服务器**（终端 1）
2. **运行测试脚本**（终端 2）
3. **打开飞书**，查看收到的授权卡片
4. **点击"授权"按钮**
5. **浏览器打开授权页面**，点击"同意"
6. **浏览器跳转到** `http://localhost:8000/callback?code=xxx&state=xxx`
7. **回调服务器处理授权**
8. **测试脚本显示成功**

## ✅ 成功的标志

### 回调服务器（终端 1）应该显示:

```
127.0.0.1 - - [21/Jan/2026 18:20:15] "GET /callback?code=xxx&state=xxx HTTP/1.1" 200 -
```

### 测试脚本（终端 2）应该显示:

```
🎉 授权成功！
   OpenID: ou_xxx
   用户名: Test User
   邮箱: test@example.com
   Token: u-xxx...
   过期时间: 2026-01-28 18:20:15
```

## 🔍 故障排查

### 问题 1: 回调服务器无法启动

**症状:** 服务器启动后立即退出或没有输出

**解决:**
```bash
# 检查端口是否被占用
netstat -tlnp | grep 8000
# 或
lsof -i :8000

# 如果被占用，停止占用进程或更改端口
export CALLBACK_PORT=8001
python start_callback_server.py
```

### 问题 2: 浏览器无法访问 localhost:8000

**症状:** 浏览器显示"无法访问此网站"

**原因:** 浏览器和服务器可能不在同一台机器上

**解决:**
1. 使用 ngrok 或其他隧道工具
2. 或者修改服务器监听地址:
```bash
export CALLBACK_HOST=0.0.0.0
python start_callback_server.py
# 然后在飞书配置中使用: http://你的IP:8000/callback
```

### 问题 3: 授权超时

**症状:** 测试脚本显示"授权超时"

**检查清单:**
- [ ] 回调服务器是否正在运行？
- [ ] 浏览器是否成功完成授权？
- [ ] 浏览器是否跳转到了 callback 页面？
- [ ] 回调服务器是否收到了请求？（查看终端 1 的日志）

### 问题 4: 数据库连接失败

**症状:** 服务器启动时报错 "connection refused"

**解决:**
```bash
# 确认 PostgreSQL 正在运行
docker compose ps postgres

# 如果没有运行，启动它
docker compose up -d postgres

# 运行迁移
alembic upgrade head
```

## 🧪 手动测试回调

如果你想手动测试回调处理，可以使用 curl:

```bash
# 模拟一个 OAuth 回调
curl -v "http://localhost:8000/callback?code=test_code_123&state=test_session_id"
```

你应该看到一个 HTML 页面显示"授权成功！"

## 📊 验证结果

测试完成后，你可以查询数据库确认:

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
python -c "
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
db_url = f\"postgresql://{os.getenv('POSTGRES_USER', 'lark_user')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB', 'lark_service')}\"
engine = create_engine(db_url)

with engine.connect() as conn:
    result = conn.execute(text('SELECT session_id, state, open_id, user_name FROM user_auth_sessions ORDER BY created_at DESC LIMIT 5'))
    for row in result:
        print(f'{row[0]}: {row[1]} - {row[2]} ({row[3]})')
"
```

## 📝 环境变量

确保 `.env` 文件包含:

```bash
# 必需
APP_ID=cli_xxx
APP_SECRET=xxx
LARK_CONFIG_ENCRYPTION_KEY=xxx
TEST_USER_EMAIL=your@email.com

# 数据库
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark_user
POSTGRES_PASSWORD=your_password

# 可选（用于签名验证）
LARK_VERIFICATION_TOKEN=xxx
LARK_ENCRYPT_KEY=xxx

# 回调服务器（可选）
CALLBACK_HOST=127.0.0.1
CALLBACK_PORT=8000
```

## 🎯 下一步

测试成功后，你可以:

1. ✅ 实现卡片自动更新功能（需要 `MessagingClient.update_message`）
2. ✅ 添加更多的错误处理
3. ✅ 集成到主应用服务中
4. ✅ 添加更多的自动化测试

---

如有问题，请查看日志文件或联系开发团队。
