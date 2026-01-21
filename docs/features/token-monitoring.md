# Token 过期监控 (Token Expiry Monitoring)

本文档介绍 Lark Service 的 Token 过期监控功能,帮助您主动管理 Token 生命周期,避免服务中断。

## 概述

### Token 类型说明

飞书有三种主要的 Token 类型:

1. **App Access Token (应用级 Token)**
   - 适用于**自建应用**(企业内部使用)
   - 通过 `app_id` + `app_secret` 获取
   - **可以自动刷新** - 无需用户干预
   - 默认有效期: 2 小时
   - 刷新机制: SDK 自动管理,无需监控

2. **Tenant Access Token (租户级 Token)**
   - 适用于**商店应用**(ISV 应用,服务多租户)
   - 通过 `app_id` + `app_secret` 获取
   - **可以自动刷新** - 无需用户干预
   - 默认有效期: 2 小时
   - 与 App Token 处理方式完全相同,无需监控

3. **User Access Token (用户级 Token)**
   - 通过 OAuth 授权流程获取
   - 包含 `access_token` 和 `refresh_token`
   - **`access_token` 可自动刷新** - 使用 `refresh_token`
   - **`refresh_token` 过期需要用户重新授权**
   - 这才是需要监控的重点!

### 监控功能

Token 过期监控是一个主动式的 UX 优化功能,专注于监控 **Refresh Token** 的过期状态:

- 🔔 **主动通知**: 在 Refresh Token 过期前发送多级提醒
- 📊 **实时监控**: 通过 Prometheus 和 Grafana 可视化状态
- 📝 **详细指引**: 提供清晰的用户重新授权流程
- 🛡️ **防止服务中断**: 确保用户及时重新授权

## 功能特性

### 多级通知机制

| 通知级别 | 触发时机 | 严重性 | 通知频率 |
|---------|---------|--------|---------|
| 预警 (Warning) | Refresh Token 7 天内过期 | ⚠️ 警告 | 每天一次 |
| 严重警告 (Critical) | Refresh Token 3 天内过期 | 🚨 严重 | 每天一次 |
| 已过期 (Expired) | Refresh Token 已过期 | ❌ 关键 | 每天一次 |

**重要**:
- ✅ App Access Token 会自动刷新,**无需监控和通知**
- ✅ Tenant Access Token 会自动刷新,**无需监控和通知**
- ⚠️ 监控的是 User Access Token 的 **Refresh Token**
- 🔄 Access Token 本身过期不是问题,只要 Refresh Token 有效就能自动刷新

### 通知内容

#### 预警通知 (7 天)

```
⚠️ **Token Expiry Warning**

Your access token for application `cli_abc123` will expire in **7 days**.

**Action Required:**
1. Go to Lark Open Platform
2. Navigate to your application settings
3. Regenerate your app credentials
4. Update the configuration in this service

Need help? Contact your system administrator.
```

#### 严重警告 (3 天)

```
🚨 **URGENT: Token Expiring Soon!**

Your access token for application `cli_abc123` will expire in **3 days**!

**Immediate Action Required:**
Service functionality will be disrupted if the token expires.

**Steps to Renew:**
1. Visit [Lark Open Platform](https://open.feishu.cn/app)
2. Select application `cli_abc123`
3. Navigate to 'Credentials & Basic Info'
4. Regenerate App Secret
5. Update configuration:
   ```bash
   lark-service-cli app update cli_abc123 --app-secret <new_secret>
   ```

Contact your system administrator immediately if you need assistance.
```

#### 已过期通知

```
❌ **Token Expired**

The access token for application `cli_abc123` has **EXPIRED**.

**Service Impact:**
All API calls using this token will fail until renewed.

**Required Actions:**
1. Visit [Lark Open Platform](https://open.feishu.cn/app)
2. Regenerate app credentials for `cli_abc123`
3. Update configuration immediately:
   ```bash
   lark-service-cli app update cli_abc123 \
     --app-id <app_id> \
     --app-secret <new_secret>
   ```
4. Restart the service

**Need Help?**
Contact: your-support-email@example.com
```

## 使用指南

### 启用 Token 监控

Token 监控功能默认启用,作为定时任务的一部分自动运行:

```python
# 在 src/lark_service/scheduler/tasks.py 中
scheduler.add_cron_job(
    check_token_expiry_task,
    cron_expression="0 9,18 * * *",  # 每天 9AM 和 6PM
    job_id="check_token_expiry",
)
```

### 配置监控参数

修改监控阈值:

```python
from lark_service.services.token_monitor import TokenExpiryMonitor, TokenType

monitor = TokenExpiryMonitor(
    messaging_client=client,
    warning_days=7,    # 预警天数(默认 7)
    critical_days=3,   # 严重警告天数(默认 3)
)

# 监控 User Access Token 的 Refresh Token
monitor.check_token_expiry(
    app_id="cli_abc123",
    token_expires_at=access_token_expires_at,  # Access Token 过期时间
    token_type=TokenType.USER_ACCESS_TOKEN,    # 用户级 Token
    refresh_token_expires_at=refresh_expires_at,  # Refresh Token 过期时间(重要!)
    admin_user_id="ou_xxxxx",
)

# App Access Token 不需要监控(会自动跳过通知)
monitor.check_token_expiry(
    app_id="cli_abc123",
    token_expires_at=app_token_expires_at,
    token_type=TokenType.APP_ACCESS_TOKEN,  # 应用级 Token,自动刷新
)

# Tenant Access Token 同样不需要监控(会自动跳过通知)
monitor.check_token_expiry(
    app_id="cli_abc123",
    token_expires_at=tenant_token_expires_at,
    token_type=TokenType.TENANT_ACCESS_TOKEN,  # 租户级 Token,自动刷新
)
```

### 手动检查 Token 状态

使用 Python 代码检查:

```python
from datetime import datetime, timedelta
from lark_service.services.token_monitor import TokenExpiryMonitor
from lark_service.messaging.client import MessagingClient

# 初始化
messaging_client = MessagingClient(...)
monitor = TokenExpiryMonitor(messaging_client)

# 检查 Token
token_expires_at = datetime.utcnow() + timedelta(days=5)
monitor.check_token_expiry(
    app_id="cli_abc123",
    token_expires_at=token_expires_at,
    admin_user_id="ou_xxxxx",  # 飞书用户 ID
)

# 获取过期状态
status = monitor.get_expiry_status(token_expires_at)
print(status)
# {
#     "status": "expiring",
#     "severity": "warning",
#     "days_to_expiry": 5,
#     "hours_to_expiry": 120.0,
#     "expires_at": "2026-01-27T12:00:00"
# }
```

## 监控和可视化

### Prometheus 指标

Token 监控导出以下指标:

```promql
# Token 过期倒计时(天数)
token_days_to_expiry{app_id="cli_abc123"}

# 发送的过期警告总数
token_expiry_warnings_sent_total{app_id="cli_abc123"}
```

### Grafana 面板

访问 `http://localhost:3000` 查看 **Token Expiry Monitoring** 面板:

1. **Token 过期倒计时仪表盘**
   - 显示每个应用的剩余天数
   - 颜色编码:
     * 绿色: > 7 天
     * 黄色: 3-7 天
     * 橙色: 1-3 天
     * 红色: < 1 天 或已过期

2. **Token 状态表格**
   - 列出所有应用及其过期状态
   - 按剩余天数排序

3. **过期时间轴**
   - 显示 Token 过期趋势
   - 帮助预测未来过期情况

4. **警告发送统计**
   - 显示已发送的警告数量
   - 帮助验证通知系统正常工作

### Prometheus 告警

在 `config/prometheus/alerts.yml` 中配置了自动告警:

```yaml
# Token 预警(7 天内过期)
- alert: TokenExpiringSoon
  expr: token_days_to_expiry < 7 and token_days_to_expiry > 3
  labels:
    severity: warning
  annotations:
    summary: "Token expiring in {{ $value }} days"

# Token 严重警告(3 天内过期)
- alert: TokenExpiringCritical
  expr: token_days_to_expiry <= 3 and token_days_to_expiry > 0
  labels:
    severity: critical
  annotations:
    summary: "Token expiring in {{ $value }} days!"

# Token 已过期
- alert: TokenExpired
  expr: token_days_to_expiry <= 0
  labels:
    severity: critical
  annotations:
    summary: "Token has expired!"
```

## Token 续期流程

### 在飞书开放平台续期

1. **登录飞书开放平台**
   - 访问: https://open.feishu.cn/app
   - 使用管理员账号登录

2. **选择应用**
   - 在应用列表中找到对应的应用
   - 点击进入应用详情

3. **重新生成凭证**
   - 导航到 "凭证与基础信息"
   - 点击 "重新生成" App Secret
   - **重要**: 保存新的 App Secret,它只显示一次!

4. **更新服务配置**

   使用 CLI 更新:
   ```bash
   lark-service-cli app update <app_id> \
     --app-secret <new_app_secret>
   ```

   或直接修改环境变量:
   ```bash
   # .env 文件
   LARK_APP_SECRET=new_secret_here
   ```

5. **重启服务** (如果修改了环境变量)
   ```bash
   docker-compose restart lark-service
   ```

### 验证更新

检查新 Token 是否生效:

```bash
# 查看应用配置
lark-service-cli app show <app_id>

# 查看日志
docker logs lark-service 2>&1 | tail -50
```

## API 参考

### TokenExpiryMonitor 类

```python
class TokenExpiryMonitor:
    """Token 过期监控服务"""

    def __init__(
        self,
        messaging_client: MessagingClient,
        warning_days: int = 7,
        critical_days: int = 3,
    ):
        """
        初始化监控器

        Args:
            messaging_client: 消息发送客户端
            warning_days: 预警天数阈值
            critical_days: 严重警告天数阈值
        """
        pass

    def check_token_expiry(
        self,
        app_id: str,
        token_expires_at: datetime,
        admin_user_id: Optional[str] = None,
    ) -> None:
        """
        检查 Token 过期状态并发送通知

        Args:
            app_id: 应用 ID
            token_expires_at: Token 过期时间
            admin_user_id: 管理员用户 ID(可选)
        """
        pass

    def get_expiry_status(
        self,
        token_expires_at: datetime
    ) -> Dict[str, any]:
        """
        获取 Token 过期状态

        Args:
            token_expires_at: Token 过期时间

        Returns:
            {
                "status": "valid|expiring|expiring_soon|expired",
                "severity": "ok|warning|critical",
                "days_to_expiry": int,
                "hours_to_expiry": float,
                "expires_at": str (ISO 8601)
            }
        """
        pass
```

## 最佳实践

### 1. 设置管理员通知

确保每个应用都配置了管理员用户 ID:

```bash
lark-service-cli app update <app_id> \
  --created-by <admin_user_id>
```

### 2. 定期检查监控面板

建议每周查看一次 Grafana 面板,确保:
- 所有 Token 状态正常
- 没有即将过期的 Token
- 通知系统正常工作

### 3. 提前续期

不要等到最后一天才续期:
- 建议在收到 7 天预警时就开始准备
- 在非高峰时段进行续期操作
- 续期后立即测试服务可用性

### 4. 建立续期流程

制定 SOP (Standard Operating Procedure):
1. 收到通知后 24 小时内响应
2. 指定专人负责续期操作
3. 记录续期操作和新的过期时间
4. 续期后验证服务正常

### 5. 配置备用联系方式

除了飞书通知,还可以:
- 配置邮件告警(通过 Alertmanager)
- 设置 PagerDuty/OpsGenie 集成
- 建立值班轮换机制

## 故障排查

### 未收到通知

1. **检查定时任务是否运行**:
   ```bash
   docker logs lark-service 2>&1 | grep "check_token_expiry"
   ```

2. **验证管理员用户 ID 配置**:
   ```bash
   lark-service-cli app show <app_id> | grep created_by
   ```

3. **检查 MessagingClient 配置**:
   - 确认飞书应用有发送消息权限
   - 验证用户 ID 格式正确(以 `ou_` 开头)

### 通知发送失败

查看错误日志:
```bash
docker logs lark-service 2>&1 | grep "Failed to send token expiry"
```

常见原因:
- 网络连接问题
- 飞书 API 限流
- 用户 ID 无效
- 应用权限不足

### Prometheus 指标缺失

1. 检查 Prometheus 是否正在抓取指标:
   ```bash
   curl http://localhost:9091/api/v1/targets
   ```

2. 验证服务端口暴露:
   ```bash
   docker ps | grep lark-service
   ```

3. 检查指标端点:
   ```bash
   curl http://localhost:9090/metrics | grep token_days_to_expiry
   ```

## 参考资料

- [飞书开放平台文档](https://open.feishu.cn/document/home/index)
- [Prometheus 告警配置](https://prometheus.io/docs/alerting/latest/configuration/)
- [Grafana 面板配置](https://grafana.com/docs/grafana/latest/dashboards/)
