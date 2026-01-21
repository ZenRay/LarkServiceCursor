# 真实飞书环境集成验证指南

本文档提供在真实飞书环境中验证 LarkService 各项功能的详细步骤。

## 📋 验证清单

- [ ] 配置真实飞书应用凭据
- [ ] 验证 App Access Token 自动刷新
- [ ] 验证 User Access Token OAuth 流程
- [ ] 验证 Token 过期通知功能
- [ ] 验证 Grafana 仪表板数据显示

---

## 1. 配置真实飞书应用凭据

### 1.1 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击「创建企业自建应用」
3. 填写应用信息:
   - 应用名称: LarkService Test
   - 应用描述: LarkService 集成测试应用
   - 应用图标: 上传图标

### 1.2 获取应用凭证

1. 在应用管理页面,点击「凭证与基础信息」
2. 记录以下信息:
   ```
   App ID: cli_xxxxxxxxxxxxxx
   App Secret: xxxxxxxxxxxxxxxxxxxx
   ```

### 1.3 配置应用权限

进入「权限管理」,添加以下权限:

#### 消息与群组
- `im:message` - 获取与发送单聊、群组消息
- `im:message.group_at_msg` - 获取群组中所有消息
- `im:message.p2p_msg` - 获取用户发给机器人的单聊消息

#### 通讯录
- `contact:user.base:readonly` - 获取用户基本信息
- `contact:user.email:readonly` - 获取用户邮箱
- `contact:user.phone:readonly` - 获取用户手机号

### 1.4 配置环境变量

编辑 `.env` 文件:

```bash
# 飞书应用凭证
LARK_APP_ID=cli_xxxxxxxxxxxxxx
LARK_APP_SECRET=your_app_secret_here

# 配置加密密钥(32字符)
LARK_CONFIG_ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32)[:32])")

# Token 监控管理员
ADMIN_USER_ID=ou_xxxxxxxxxxxx  # 您的飞书 Open ID
```

**获取您的 Open ID**:
1. 在飞书中打开「我」->「设置」
2. 点击「关于」
3. 复制「用户 ID (Open ID)」

### 1.5 重启服务

```bash
docker compose restart lark-service
docker compose logs -f lark-service
```

---

## 2. 验证 App Access Token 自动刷新

### 2.1 启动服务并观察日志

```bash
docker compose logs -f lark-service | grep "token"
```

### 2.2 触发 Token 获取

创建测试脚本 `test_app_token.py`:

```python
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.config import Config

load_dotenv()

async def test_app_token():
    """测试 App Access Token 获取和刷新"""
    config = Config(max_retries=3)
    pool = CredentialPool(config)

    app_id = os.getenv("LARK_APP_ID")
    app_secret = os.getenv("LARK_APP_SECRET")

    print(f"🔐 Testing App Access Token for: {app_id}")

    # 添加应用凭证
    pool.add_app_credential(app_id, app_secret)

    # 获取 Token (如果缓存没有,会自动请求)
    token = await pool.get_app_access_token(app_id)
    print(f"✅ Got App Access Token: {token[:20]}...")

    # 验证 Token 缓存
    cached_token = await pool.get_app_access_token(app_id)
    assert token == cached_token, "Token should be cached"
    print("✅ Token cache working")

    # 检查 Token 过期时间
    expires_at = pool._token_storage.get_token_expires_at(app_id, "app_access_token")
    print(f"📅 Token expires at: {expires_at}")

    print("\n🎉 App Access Token test passed!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_app_token())
```

运行测试:

```bash
docker compose exec lark-service python test_app_token.py
```

### 2.3 验证 Prometheus 指标

```bash
# 查看 Token 刷新次数
curl -s http://localhost:9090/metrics | grep "lark_service_token_refresh_total"

# 查看 Token 缓存命中率
curl -s http://localhost:9090/metrics | grep "lark_service_token_cache"
```

**预期结果**:
- ✅ 成功获取 App Access Token
- ✅ Token 被正确缓存
- ✅ Prometheus 指标正常记录

---

## 3. 验证 User Access Token OAuth 流程

### 3.1 配置 OAuth 回调

1. 在飞书开放平台,进入「安全设置」
2. 添加「重定向 URL」:
   ```
   http://localhost:8000/oauth/callback
   ```

### 3.2 启动 OAuth 授权流程

创建测试脚本 `test_oauth.py`:

```python
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from lark_service.auth.oauth_handler import OAuthHandler

load_dotenv()

def test_oauth_url():
    """生成 OAuth 授权 URL"""
    app_id = os.getenv("LARK_APP_ID")
    redirect_uri = "http://localhost:8000/oauth/callback"

    handler = OAuthHandler(app_id, redirect_uri)
    auth_url = handler.get_authorization_url()

    print("=" * 70)
    print("📱 请在浏览器中打开以下 URL 进行授权:")
    print("=" * 70)
    print(auth_url)
    print("=" * 70)
    print("\n授权后,您将被重定向到回调 URL")
    print("请复制回调 URL 中的 'code' 参数")

if __name__ == "__main__":
    test_oauth_url()
```

运行测试:

```bash
docker compose exec lark-service python test_oauth.py
```

### 3.3 完成授权

1. 在浏览器中打开生成的 URL
2. 登录飞书并授权
3. 复制回调 URL 中的 `code` 参数

### 3.4 交换 User Access Token

创建测试脚本 `test_user_token.py`:

```python
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.config import Config

load_dotenv()

async def test_user_token(code: str):
    """测试 User Access Token 获取"""
    config = Config(max_retries=3)
    pool = CredentialPool(config)

    app_id = os.getenv("LARK_APP_ID")
    app_secret = os.getenv("LARK_APP_SECRET")

    print(f"🔐 Testing User Access Token for: {app_id}")

    # 添加应用凭证
    pool.add_app_credential(app_id, app_secret)

    # 使用授权码交换 Token
    result = await pool.exchange_oauth_token(app_id, code)

    print(f"✅ Got User Access Token: {result['access_token'][:20]}...")
    print(f"✅ Got Refresh Token: {result['refresh_token'][:20]}...")
    print(f"📅 Access Token expires in: {result['expires_in']} seconds")
    print(f"📅 Refresh Token expires in: {result['refresh_expires_in']} seconds")

    print("\n🎉 User Access Token test passed!")

if __name__ == "__main__":
    import asyncio
    import sys

    if len(sys.argv) < 2:
        print("Usage: python test_user_token.py <auth_code>")
        sys.exit(1)

    code = sys.argv[1]
    asyncio.run(test_user_token(code))
```

运行测试:

```bash
docker compose exec lark-service python test_user_token.py YOUR_AUTH_CODE
```

**预期结果**:
- ✅ 成功交换 User Access Token
- ✅ 获取到 Refresh Token
- ✅ Token 过期时间正确

---

## 4. 验证 Token 过期通知功能

### 4.1 手动触发 Token 过期检查

创建测试脚本 `test_token_monitor.py`:

```python
#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from lark_service.services.token_monitor import TokenExpiryMonitor, TokenType
from lark_service.messaging.client import MessagingClient

load_dotenv()

async def test_token_monitor():
    """测试 Token 过期监控"""
    app_id = os.getenv("LARK_APP_ID")
    app_secret = os.getenv("LARK_APP_SECRET")
    admin_user_id = os.getenv("ADMIN_USER_ID")

    print(f"📊 Testing Token Expiry Monitor for: {app_id}")

    # 创建 Messaging Client
    messaging = MessagingClient(app_id, app_secret)

    # 创建 Token Monitor
    monitor = TokenExpiryMonitor(
        messaging_client=messaging,
        warning_threshold_days=30,
        critical_threshold_days=7,
    )

    # 测试1: 30天后过期 (应发送警告)
    print("\n测试1: Token 30 天后过期")
    token_expires_at = datetime.utcnow() + timedelta(days=30)
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=30)

    await monitor.check_token_expiry(
        app_id=app_id,
        token_expires_at=token_expires_at,
        token_type=TokenType.USER_ACCESS_TOKEN,
        refresh_token_expires_at=refresh_token_expires_at,
        admin_user_id=admin_user_id,
    )
    print("✅ 应收到30天警告通知")

    # 测试2: 7天后过期 (应发送严重警告)
    print("\n测试2: Token 7 天后过期")
    token_expires_at = datetime.utcnow() + timedelta(days=7)
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=7)

    await monitor.check_token_expiry(
        app_id=app_id,
        token_expires_at=token_expires_at,
        token_type=TokenType.USER_ACCESS_TOKEN,
        refresh_token_expires_at=refresh_token_expires_at,
        admin_user_id=admin_user_id,
    )
    print("✅ 应收到7天严重警告通知")

    # 测试3: 已过期 (应发送过期通知)
    print("\n测试3: Token 已过期")
    token_expires_at = datetime.utcnow() - timedelta(days=1)
    refresh_token_expires_at = datetime.utcnow() - timedelta(days=1)

    await monitor.check_token_expiry(
        app_id=app_id,
        token_expires_at=token_expires_at,
        token_type=TokenType.USER_ACCESS_TOKEN,
        refresh_token_expires_at=refresh_token_expires_at,
        admin_user_id=admin_user_id,
    )
    print("✅ 应收到过期通知")

    print("\n🎉 Token Monitor test completed!")
    print("请检查飞书中是否收到通知消息")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_token_monitor())
```

运行测试:

```bash
docker compose exec lark-service python test_token_monitor.py
```

### 4.2 检查飞书消息

在飞书中,您应该收到 3 条消息:
1. ⚠️ Token 30天警告
2. 🚨 Token 7天严重警告
3. ❌ Token 已过期

### 4.3 验证 Prometheus 指标

```bash
curl -s http://localhost:9090/metrics | grep "token_expiry_warning"
curl -s http://localhost:9090/metrics | grep "token_days_to_expiry"
```

**预期结果**:
- ✅ 收到 3 条飞书通知
- ✅ Prometheus 指标正确记录
- ✅ 不同级别的通知内容正确

---

## 5. 验证 Grafana 仪表板数据显示

### 5.1 访问 Grafana

1. 打开浏览器: http://localhost:3000
2. 登录: `admin` / `admin`
3. 首次登录后修改密码

### 5.2 导入仪表板

#### 导入系统概览仪表板

1. 点击 `+` -> `Import Dashboard`
2. 上传 `monitoring/grafana/dashboards/lark-service-overview.json`
3. 选择 Prometheus 数据源
4. 点击 `Import`

#### 导入 Token 监控仪表板

重复上述步骤,上传 `lark-service-tokens.json`

#### 导入 Scheduler 任务仪表板

重复上述步骤,上传 `lark-service-scheduler.json`

### 5.3 验证数据显示

#### 系统概览仪表板
- [ ] HTTP 请求总数
- [ ] HTTP 请求耗时 (P50, P95, P99)
- [ ] API 调用统计
- [ ] Rate Limit 命中次数

#### Token 监控仪表板
- [ ] Token 剩余有效天数
- [ ] Token 刷新频率
- [ ] Token 缓存命中率
- [ ] Refresh Token 过期时间

#### Scheduler 任务仪表板
- [ ] 任务执行次数
- [ ] 任务成功率
- [ ] 任务执行耗时
- [ ] 任务失败统计

### 5.4 生成测试数据

如果仪表板显示为空,运行以下命令生成测试数据:

```bash
# 启动 Mock 数据生成器
curl http://localhost:9091/start-mock

# 等待 1 分钟
sleep 60

# 停止 Mock 数据生成器
curl http://localhost:9091/stop-mock
```

刷新 Grafana 仪表板,应该可以看到数据。

**预期结果**:
- ✅ 3 个仪表板成功导入
- ✅ 所有面板显示数据
- ✅ 图表实时更新

---

## 6. 验证定时任务执行

### 6.1 查看 Scheduler 日志

```bash
docker compose logs lark-service | grep -E "(sync_user_info|check_token_expiry|cleanup_expired_tokens|health_check)"
```

### 6.2 验证任务执行频率

```bash
# 查看最近 1 小时的任务执行情况
docker compose logs --since 1h lark-service | grep "Completed scheduled task"
```

### 6.3 查看 Prometheus 指标

```bash
curl -s http://localhost:9090/metrics | grep "scheduled_task"
```

**预期结果**:
- ✅ 任务按预定时间执行
- ✅ 任务执行成功
- ✅ Prometheus 指标正常

---

## 📊 完整验证报告

完成所有验证后,请填写此清单:

### 功能验证结果

| 功能 | 状态 | 备注 |
|------|------|------|
| Docker 服务启动 | ✅ / ❌ |  |
| App Access Token 自动刷新 | ✅ / ❌ |  |
| User Access Token OAuth | ✅ / ❌ |  |
| Token 过期通知 | ✅ / ❌ |  |
| Prometheus 指标采集 | ✅ / ❌ |  |
| Grafana 仪表板显示 | ✅ / ❌ |  |
| 定时任务执行 | ✅ / ❌ |  |

### 性能指标

- HTTP 请求平均响应时间: ___ ms
- Token 刷新成功率: ___ %
- 定时任务成功率: ___ %
- 系统资源占用:
  - CPU: ___ %
  - 内存: ___ MB
  - 磁盘: ___ GB

---

## 🐛 常见问题

### Q1: Token 刷新失败

**可能原因**:
- App ID / App Secret 错误
- 网络连接问题
- 飞书 API 限流

**解决方法**:
```bash
# 检查环境变量
docker compose exec lark-service env | grep LARK

# 测试网络连接
docker compose exec lark-service ping open.feishu.cn

# 查看详细日志
docker compose logs lark-service | grep "ERROR"
```

### Q2: 收不到飞书通知

**可能原因**:
- ADMIN_USER_ID 配置错误
- 应用没有消息权限
- 用户未添加应用

**解决方法**:
1. 确认 ADMIN_USER_ID 正确
2. 在飞书中搜索并添加应用
3. 确认应用有 `im:message` 权限

### Q3: Grafana 无数据

**可能原因**:
- Prometheus 未抓取到指标
- 数据源配置错误
- 时间范围选择错误

**解决方法**:
```bash
# 检查 Prometheus targets
open http://localhost:9091/targets

# 手动生成测试数据
curl http://localhost:9091/start-mock
```

---

## 📝 下一步

完成验证后,您可以:

1. **部署到生产环境**
   - 参考 [生产环境部署指南](PRODUCTION_DEPLOYMENT.md)
   - 配置域名和 HTTPS
   - 设置定时备份

2. **定制功能**
   - 实现具体的业务逻辑
   - 添加更多 API 端点
   - 扩展定时任务

3. **监控告警**
   - 配置 Prometheus AlertManager
   - 集成告警渠道(邮件、飞书、钉钉)
   - 设置告警规则

---

**祝您集成顺利! 🎉**

如有问题,请提交 Issue 或联系技术支持。
