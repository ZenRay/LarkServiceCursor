# 飞书 Token 刷新机制详解

## 📋 概述

本文档详细说明飞书开放平台的 Token 类型和刷新机制,以及 LarkService 中的正确处理方式。

## 🔑 Token 类型

### 1. App Access Token (应用级访问令牌)

**用途**: 应用级别的 API 调用,不涉及特定用户身份

**获取方式**:
```python
# 使用 app_id + app_secret
POST https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal
{
  "app_id": "cli_xxxxx",
  "app_secret": "yyyyy"
}
```

**刷新机制**:
- ✅ **可以自动刷新**
- 只要 `app_secret` 有效,就能无限次获取新的 Token
- 不需要用户干预
- 不需要 OAuth 授权流程

**有效期**: 默认 2 小时

**LarkService 处理**:
```python
# CredentialPool 会自动管理 App Access Token
# 在 Token 过期前自动刷新
token = await credential_pool.get_app_access_token(app_id)
```

**监控策略**: ❌ **无需监控 App Access Token 过期**
- 系统会自动刷新
- 监控重点应该是 `app_secret` 的有效性(通常不过期,除非手动重新生成)

---

### 2. User Access Token (用户级访问令牌)

**用途**: 代表特定用户身份的 API 调用,访问用户个人数据

**获取方式**:
```python
# 第一步: 用户授权(浏览器重定向)
https://open.feishu.cn/open-apis/authen/v1/authorize?
  app_id=cli_xxxxx&
  redirect_uri=https://your-app.com/callback&
  state=random_state

# 第二步: 使用授权码换取 Token
POST https://open.feishu.cn/open-apis/authen/v1/oidc/access_token
{
  "grant_type": "authorization_code",
  "code": "授权码"
}

# 响应包含:
{
  "access_token": "u-xxxx",      # 访问令牌
  "refresh_token": "ur-yyyy",    # 刷新令牌
  "expires_in": 7200,            # access_token 有效期(秒)
  "refresh_expires_in": 2592000  # refresh_token 有效期(秒,默认 30 天)
}
```

**刷新机制**:
- ✅ **Access Token 可以自动刷新** - 使用 `refresh_token`
- ⚠️ **Refresh Token 过期后需要用户重新授权**
- Refresh Token 默认有效期: 30 天(可配置)

**刷新 Access Token**:
```python
POST https://open.feishu.cn/open-apis/authen/v1/oidc/refresh_access_token
{
  "grant_type": "refresh_token",
  "refresh_token": "ur-yyyy"
}
```

**LarkService 处理**:
```python
# 自动刷新 Access Token
token_info = await credential_pool.get_user_access_token(
    user_id=user_id,
    auto_refresh=True  # 使用 refresh_token 自动刷新
)

# 如果 refresh_token 过期,抛出异常,需要重新授权
```

**监控策略**: ✅ **必须监控 Refresh Token 过期**
```python
from lark_service.services.token_monitor import TokenExpiryMonitor, TokenType

monitor = TokenExpiryMonitor(messaging_client=client)

# 监控 Refresh Token 过期状态
monitor.check_token_expiry(
    app_id="cli_xxxxx",
    token_expires_at=access_token_expires_at,  # Access Token 过期时间
    token_type=TokenType.USER_ACCESS_TOKEN,
    refresh_token_expires_at=refresh_expires_at,  # 🔴 这个才是关键!
    admin_user_id="ou_xxxxx",
)
```

---

## 🚨 常见误区

### ❌ 误区 1: Token 过期就需要重新生成 app_secret

**错误理解**:
> "Token 快过期了,需要去飞书开放平台重新生成 app_secret"

**正确理解**:
- **App Access Token** 过期是正常的(默认 2 小时),会自动刷新
- **User Access Token** 过期也是正常的,可以用 `refresh_token` 自动刷新
- **只有 `app_secret` 本身泄露或手动重置**,才需要重新生成

---

### ❌ 误区 2: 所有 Token 都需要监控过期

**错误理解**:
> "为了防止服务中断,应该监控所有 Token 的过期时间"

**正确理解**:
- **App Access Token**: ❌ 无需监控,系统自动刷新
- **User Access Token**: ❌ 无需监控 Access Token,会自动刷新
- **Refresh Token**: ✅ **必须监控**,过期需要用户重新授权

---

### ❌ 误区 3: Token 刷新失败就是 app_secret 的问题

**错误理解**:
> "401 错误,肯定是 app_secret 过期了,需要重新生成"

**正确理解**:
- **App Token 刷新失败**: 可能是 `app_secret` 错误或网络问题
- **User Token 刷新失败**: 通常是 `refresh_token` 过期,需要用户重新授权
- **区分错误码**:
  - `99991668`: app_secret 无效
  - `99991663`: refresh_token 已过期/无效

---

## 📊 监控和通知策略

### App Access Token

```python
# ❌ 不要这样做
monitor.check_token_expiry(
    app_id="cli_xxxxx",
    token_expires_at=app_token_expires,
    token_type=TokenType.APP_ACCESS_TOKEN,
    admin_user_id="ou_xxxxx",  # 会发送不必要的通知!
)

# ✅ 正确做法: 不监控 App Token,或者监控但不发通知
# TokenExpiryMonitor 已经内置了逻辑:
# - 如果是 APP_ACCESS_TOKEN,自动跳过通知
# - 只记录日志: "App Access Token will auto-refresh"
```

### User Access Token

```python
# ✅ 只监控 Refresh Token
monitor.check_token_expiry(
    app_id="cli_xxxxx",
    token_expires_at=access_token_expires_at,
    token_type=TokenType.USER_ACCESS_TOKEN,
    refresh_token_expires_at=refresh_token_expires_at,  # 关键参数!
    admin_user_id="ou_xxxxx",
)

# 通知内容:
# - 7 天提醒: "Refresh Token 即将过期,请通知用户准备重新授权"
# - 3 天警告: "Refresh Token 即将过期,请立即通知用户重新授权"
# - 已过期: "Refresh Token 已过期,用户需要重新授权"
```

---

## 🔧 LarkService 实现细节

### CredentialPool 自动刷新逻辑

```python
class CredentialPool:
    async def get_app_access_token(self, app_id: str) -> str:
        """
        获取 App Access Token,自动处理刷新.
        """
        token_info = self._cache.get(app_id)

        if not token_info or self._is_expired(token_info):
            # 自动刷新 - 使用 app_id + app_secret
            token_info = await self._refresh_app_token(app_id)
            self._cache.set(app_id, token_info)

        return token_info.access_token

    async def get_user_access_token(
        self,
        user_id: str,
        auto_refresh: bool = True
    ) -> TokenInfo:
        """
        获取 User Access Token,可选自动刷新.
        """
        token_info = self._cache.get(user_id)

        if not token_info:
            raise TokenNotFoundError("User not authorized")

        if self._is_expired(token_info):
            if auto_refresh and token_info.refresh_token:
                # 尝试使用 refresh_token 刷新
                try:
                    token_info = await self._refresh_user_token(
                        token_info.refresh_token
                    )
                    self._cache.set(user_id, token_info)
                except RefreshTokenExpiredError:
                    # Refresh Token 过期,需要重新授权
                    raise ReauthorizationRequiredError(
                        "Refresh token expired, user must re-authorize"
                    )
            else:
                raise TokenExpiredError("Access token expired")

        return token_info
```

### TokenExpiryMonitor 智能通知

```python
class TokenExpiryMonitor:
    def check_token_expiry(
        self,
        app_id: str,
        token_expires_at: datetime,
        token_type: TokenType = TokenType.APP_ACCESS_TOKEN,
        refresh_token_expires_at: datetime | None = None,
        admin_user_id: str | None = None,
    ) -> None:
        """
        智能 Token 过期检查:
        - App Token: 只记录日志,不发通知(会自动刷新)
        - User Token: 监控 refresh_token,临近过期时通知管理员
        """
        if token_type == TokenType.APP_ACCESS_TOKEN:
            # ❌ 不发通知 - App Token 会自动刷新
            logger.debug(f"App Token for {app_id} will auto-refresh")
            return

        if token_type == TokenType.USER_ACCESS_TOKEN:
            if not refresh_token_expires_at:
                logger.warning(
                    f"No refresh_token expiry provided for {app_id}"
                )
                return

            # ✅ 监控 Refresh Token 过期
            days_to_expiry = (refresh_token_expires_at - datetime.utcnow()).days

            if days_to_expiry <= 0:
                self._send_expired_notification(app_id, admin_user_id)
            elif days_to_expiry <= 3:
                self._send_critical_warning(app_id, days_to_expiry, admin_user_id)
            elif days_to_expiry <= 7:
                self._send_warning(app_id, days_to_expiry, admin_user_id)
```

---

## 🎯 最佳实践

### 1. 定期任务配置

```python
# scheduler/tasks.py
async def check_token_expiry_task() -> None:
    """
    定期检查所有应用的 Token 状态.
    """
    db = get_db()
    applications = db.query(Application).all()

    for app in applications:
        if app.auth_type == "app":
            # ❌ 不检查 App Token (会自动刷新)
            continue

        if app.auth_type == "user":
            # ✅ 检查所有用户的 Refresh Token
            users = db.query(UserToken).filter_by(app_id=app.app_id).all()

            for user in users:
                monitor.check_token_expiry(
                    app_id=app.app_id,
                    token_expires_at=user.access_token_expires_at,
                    token_type=TokenType.USER_ACCESS_TOKEN,
                    refresh_token_expires_at=user.refresh_token_expires_at,
                    admin_user_id=app.admin_user_id,
                )

# 每天检查 2 次 (早上 9 点和晚上 9 点)
scheduler.add_cron_job(
    check_token_expiry_task,
    cron_expression="0 9,21 * * *",
    job_id="check_token_expiry",
)
```

### 2. 通知内容模板

#### Refresh Token 7 天预警

```
⚠️ **Refresh Token Expiry Warning**

The refresh token for application `cli_xxxxx` will expire in **7 days**.

**What does this mean?**
After the refresh token expires, users will need to re-authorize the application.

**Action Required:**
1. Notify affected users to prepare for re-authorization
2. Ensure authorization flow is working correctly
3. Consider implementing automatic re-authorization reminders

**Note:** Access tokens will continue to auto-refresh until the refresh token expires.
```

#### Refresh Token 3 天严重警告

```
🚨 **URGENT: Refresh Token Expiring Soon!**

The refresh token for application `cli_xxxxx` will expire in **3 days**!

**Critical Impact:**
Users will need to re-authorize the application after the refresh token expires.
Access tokens can no longer be automatically refreshed.

**Immediate Actions:**
1. **Notify all users** to re-authorize before expiry
2. **Test authorization flow**:
   - Visit: https://open.feishu.cn/app/cli_xxxxx
   - Verify OAuth redirect URLs are correct
   - Test the complete authorization process
3. **Prepare user communications**:
   - Send email/message to affected users
   - Provide clear re-authorization instructions
4. **Monitor re-authorization rate**

**Note:** This is about refresh_token, not app_secret. No need to regenerate app credentials.
```

#### Refresh Token 已过期

```
❌ **Refresh Token Expired**

The refresh token for application `cli_xxxxx` has **EXPIRED**.

**Service Impact:**
- Users can no longer automatically refresh their access tokens
- **User re-authorization is now required**
- Existing access tokens will work until they expire (typically 2 hours)

**Required Actions:**
1. **Enable authorization flow** in your application
2. **Redirect users to re-authorize**:
   - Authorization URL: https://open.feishu.cn/open-apis/authen/v1/authorize
   - Include required parameters: app_id, redirect_uri, state
3. **Handle OAuth callback** to obtain new tokens
4. **Notify affected users** about re-authorization requirement

**Important:** This is NOT an app_secret issue. Users need to go through OAuth authorization again.
```

---

## 📚 参考资料

- [飞书开放平台 - 应用级访问凭证](https://open.feishu.cn/document/server-docs/authentication-management/access-token/app_access_token)
- [飞书开放平台 - 用户身份认证](https://open.feishu.cn/document/server-docs/authentication-management/login-state-management/web-app-sso)
- [飞书开放平台 - Token 刷新](https://open.feishu.cn/document/server-docs/authentication-management/access-token/obtain)

---

## 🤝 感谢

感谢用户指出 Token 监控逻辑中的误区,帮助我们正确理解飞书的 Token 刷新机制!
