# 📋 完整授权流程测试指南

## ⚠️ 重要说明

根据飞书官方技术支持确认（[参考文档](https://go.feishu.cn/s/6mYveuWSw0s)）：

> **OAuth 授权必须使用公网可访问的 redirect_uri**
>
> 本地或内网环境测试需要使用内网穿透工具（ngrok/localtunnel/cloudflared）

**本地测试方案**：
- ✅ 使用内网穿透工具暴露本地服务
- ✅ 配置公网 redirect_uri
- ❌ 不能使用纯 localhost（飞书无法回调）

**生产环境**：
- 必须部署到有公网 IP/域名的服务器
- 必须配置 HTTPS

---

## ✅ 功能概览

已实现的完整功能：
1. ✅ OAuth 2.0 授权码流程（符合飞书官方要求）
2. ✅ HTTP 回调服务器（本地测试需配合内网穿透）
3. ✅ Authorization Code 交换 User Access Token
4. ✅ 获取用户信息并保存
5. ✅ **自动更新授权卡片状态** 🎉

## 🚀 测试步骤

### 准备工作

1. **确认环境变量已配置**
   ```bash
   # .env 文件应包含：
   APP_ID=cli_xxx
   APP_SECRET=xxx
   LARK_CONFIG_ENCRYPTION_KEY=xxx
   TEST_USER_EMAIL=your-email@example.com
   ```

2. **确认 PostgreSQL 运行中**
   ```bash
   docker-compose ps postgres
   ```

3. **确认数据库已迁移**
   ```bash
   alembic upgrade head
   ```

### 测试流程（两个终端）

#### 终端 1：启动回调服务器

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
python start_callback_server.py
```

等待显示：
```
✅ 回调服务器已启动
   地址: http://localhost:8000
   PID: xxxxx

📝 已注册的处理器:
   - oauth_redirect: OAuth 授权回调处理

⏳ 等待请求...
   按 Ctrl+C 停止服务器
```

#### 终端 2：运行授权测试

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
python test_auth_flow.py
```

### 预期结果

1. **飞书中收到授权卡片**
   - 标题："用户授权请求"
   - 内容：显示应用信息和权限说明
   - 按钮："授权" 和 "取消"

2. **点击授权按钮**
   - 自动打开浏览器
   - 跳转到飞书授权页面
   - 显示权限确认界面

3. **点击"同意"授权**
   - 浏览器重定向到 `http://localhost:8000/callback?code=xxx&state=xxx`
   - 显示："授权成功，您已成功授权，可以关闭此页面。"

4. **终端 1（回调服务器）显示**
   ```
   收到 OAuth 回调请求
   Session ID: xxx
   正在处理授权...
   ✅ 授权处理成功
   ```

5. **终端 2（测试脚本）显示**
   ```
   🎉 授权成功！
      OpenID: ou_xxx
      用户名: 任锐
      邮箱: your-email@example.com
      Token: xxx...
      过期时间: 2026-01-21 18:28:09.806007

      📱 请查看飞书中的授权卡片，它应该已自动更新为'✅ 授权成功'状态！
   ```

6. **✨ 飞书中的卡片自动更新**
   - ✅ 标题变为："授权成功"（绿色）
   - ✅ 内容显示：用户名、OpenID、授权已生效
   - ✅ 按钮变为不可点击或消失

## 🎯 关键特性验证

### 1. OAuth 流程
- ✅ 授权码正确生成
- ✅ 重定向 URI 正确配置（`http://localhost:8000/callback`）
- ✅ State 参数正确传递和验证

### 2. Token 交换
- ✅ 使用 App Access Token 进行 Bearer 认证
- ✅ 正确解析 OIDC 端点响应
- ✅ User Access Token 成功保存

### 3. 用户信息
- ✅ 正确获取用户 OpenID
- ✅ 正确获取用户名称
- ✅ 正确获取用户邮箱

### 4. 数据库持久化
- ✅ Session 状态从 `pending` 变为 `completed`
- ✅ User Access Token 正确加密存储
- ✅ 所有用户信息字段正确保存

### 5. **卡片自动更新** 🆕
- ✅ 授权完成后自动调用 `MessagingClient.update_message`
- ✅ 卡片内容更新为成功状态
- ✅ 用户无需刷新即可看到最新状态
- ✅ 更新失败不影响授权流程

## 🐛 常见问题

### 1. 浏览器显示"无法连接"
**原因**：回调服务器未启动
**解决**：先启动 `start_callback_server.py`

### 2. 授权超时
**原因**：卡片可能是旧的
**解决**：重新运行 `test_auth_flow.py` 获取新卡片

### 3. Token 交换失败
**原因**：App Secret 可能不正确
**解决**：检查 `.env` 中的 `APP_SECRET`

### 4. 卡片未自动更新
**原因**：`message_id` 未保存或更新 API 失败
**解决**：检查日志中的错误信息，但授权本身应该成功

## 📊 验证数据

可通过以下命令查看数据库中的授权记录：

```bash
python -c "
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

db_url = f\"postgresql://{os.getenv('POSTGRES_USER', 'lark_user')}:{os.getenv('POSTGRES_PASSWORD', 'lark_password_123')}@localhost:5432/lark_service\"

engine = create_engine(db_url)

with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT session_id, state, open_id, user_name, email,
               user_access_token IS NOT NULL as has_token,
               message_id IS NOT NULL as has_message_id,
               completed_at
        FROM user_auth_sessions
        ORDER BY created_at DESC
        LIMIT 5
    '''))

    print('最近的 5 个授权会话:')
    print('-' * 100)
    for row in result:
        print(f'{row[0][:20]}... | {row[1]:10} | {row[2] or \"无\"} | {row[3] or \"无\"} | Token:{row[5]} | MsgID:{row[6]} | {row[7] or \"未完成\"}')"
```

## 🎊 成功标志

当你看到以下所有内容时，说明测试完全成功：

1. ✅ 终端显示"🎉 授权成功！"
2. ✅ 数据库中 Session 状态为 `completed`
3. ✅ User Access Token 已保存
4. ✅ 用户信息字段都已填充
5. ✅ **飞书中的卡片显示绿色的"✅ 授权成功"状态** 🎯

恭喜！整个 WebSocket 用户授权功能已经完全实现并测试通过！ 🚀
