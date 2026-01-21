# Quick Start: WebSocket User Authorization

**Time to Complete**: 5 minutes
**Difficulty**: Beginner
**Prerequisites**: Lark Service v0.1.0+ installed

---

## 🎯 What You'll Build

在 5 分钟内,您将:
1. ✅ 配置 WebSocket 用户授权
2. ✅ 发送授权卡片给用户
3. ✅ 用户点击授权,自动获取 `user_access_token`
4. ✅ 使用 Token 调用 aPaaS AI API

---

## 📋 Prerequisites Checklist

- [x] Python 3.12+ installed
- [x] Lark Service v0.1.0+ installed (`pip install lark-service>=0.1.0`)
- [x] Feishu app created ([Create App](https://open.feishu.cn/))
- [x] App credentials (APP_ID, APP_SECRET)
- [x] PostgreSQL database running (or use SQLite for testing)

---

## ⚡ 5-Minute Setup

### Step 1: Configure Environment (30 seconds)

Create `.env` file in your project root:

```bash
# Feishu App Credentials
APP_ID=cli_a1b2c3d4e5f6g7h8      # Replace with your app ID
APP_SECRET=your_app_secret_here   # Replace with your app secret

# Database (PostgreSQL for production)
DATABASE_URL=postgresql://user:pass@localhost:5432/larkservice

# Or use SQLite for testing
# DATABASE_URL=sqlite:///larkservice.db

# Encryption Key (32 bytes, generate with: openssl rand -hex 32)
ENCRYPTION_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef

# WebSocket Config (optional, defaults shown)
WEBSOCKET_MAX_RECONNECT_RETRIES=10
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_FALLBACK_TO_HTTP=true
```

**Generate Encryption Key**:
```bash
openssl rand -hex 32
```

---

### Step 2: Apply Database Migration (30 seconds)

```bash
# Run Alembic migration to create/extend user_auth_sessions table
alembic upgrade head

# Verify table exists
psql $DATABASE_URL -c "\d user_auth_sessions"
```

**Expected Output**:
```
Table "public.user_auth_sessions"
     Column          |  Type   | Nullable | Default
---------------------+---------+----------+---------
 id                  | bigint  | not null |
 session_id          | varchar | not null |
 app_id              | varchar | not null |
 user_id             | varchar | not null |
 open_id             | varchar |          |
 user_name           | varchar |          |
 ...
```

---

### Step 3: Initialize WebSocket Client (1 minute)

Create `app.py`:

```python
import asyncio
import os
from dotenv import load_dotenv

from lark_service.events.websocket_client import LarkWebSocketClient
from lark_service.events.types import WebSocketConfig
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.messaging.client import MessagingClient
from lark_service.core.database import get_db_session

# Load environment variables
load_dotenv()

# Initialize components
db_session = get_db_session()
auth_manager = AuthSessionManager(db_session)
messaging_client = MessagingClient(
    app_id=os.getenv("APP_ID"),
    app_secret=os.getenv("APP_SECRET")
)
card_handler = CardAuthHandler(auth_manager, messaging_client)

# Initialize WebSocket client
ws_config = WebSocketConfig(
    app_id=os.getenv("APP_ID"),
    app_secret=os.getenv("APP_SECRET"),
    max_reconnect_retries=int(os.getenv("WEBSOCKET_MAX_RECONNECT_RETRIES", "10")),
    heartbeat_interval=int(os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30")),
    fallback_to_http_callback=os.getenv("WEBSOCKET_FALLBACK_TO_HTTP", "true").lower() == "true"
)
ws_client = LarkWebSocketClient(ws_config)

# Register card authorization event handler
ws_client.register_handler("card.action.trigger", card_handler.handle_card_auth_event)

async def main():
    """Start WebSocket client and keep running."""
    print("🚀 Starting WebSocket client...")
    await ws_client.connect()
    print("✅ WebSocket connected! Listening for events...")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        await ws_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Step 4: Send Authorization Card (1 minute)

Create `send_auth_card.py`:

```python
import asyncio
import os
import sys
from dotenv import load_dotenv

from lark_service.auth.session_manager import AuthSessionManager
from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.auth.types import AuthCardOptions
from lark_service.messaging.client import MessagingClient
from lark_service.core.database import get_db_session

load_dotenv()

async def send_auth_card_to_user(user_id: str):
    """Send authorization card to a user."""
    db_session = get_db_session()
    auth_manager = AuthSessionManager(db_session)
    messaging_client = MessagingClient(
        app_id=os.getenv("APP_ID"),
        app_secret=os.getenv("APP_SECRET")
    )
    card_handler = CardAuthHandler(auth_manager, messaging_client)

    # Create auth session
    session = auth_manager.create_session(
        app_id=os.getenv("APP_ID"),
        user_id=user_id,
        auth_method="websocket_card"
    )

    # Send authorization card
    options = AuthCardOptions(
        include_detailed_description=True,
        custom_message="请授权以使用 AI 能力"
    )

    message_id = await card_handler.send_auth_card(
        app_id=os.getenv("APP_ID"),
        user_id=user_id,
        session_id=session.session_id,
        options=options
    )

    print(f"✅ Authorization card sent!")
    print(f"   Message ID: {message_id}")
    print(f"   Session ID: {session.session_id}")
    print(f"   Expires in: 10 minutes")
    print(f"\n📱 Please check Feishu and click 'Authorize' button")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_auth_card.py <user_open_id>")
        print("Example: python send_auth_card.py ou_7dab8a3d3cdcc08c560abcd")
        sys.exit(1)

    user_id = sys.argv[1]
    asyncio.run(send_auth_card_to_user(user_id))
```

**Run**:
```bash
# Start WebSocket client in one terminal
python app.py

# In another terminal, send auth card to yourself
python send_auth_card.py ou_YOUR_OPEN_ID
```

---

### Step 5: Test Authorization Flow (2 minutes)

#### 5.1 Send Card

```bash
# Replace with your Feishu OpenID
python send_auth_card.py ou_7dab8a3d3cdcc08c560abcd
```

**Expected Output**:
```
✅ Authorization card sent!
   Message ID: om_7dCz4T1Bx9Ky2Lm3Np4Qr5St6Uv
   Session ID: 550e8400-e29b-41d4-a716-446655440000
   Expires in: 10 minutes

📱 Please check Feishu and click 'Authorize' button
```

#### 5.2 Click "Authorize" in Feishu

1. Open Feishu on your phone/desktop
2. Find the authorization card message
3. Click "授权" (Authorize) button
4. Wait 3-5 seconds

#### 5.3 Verify Authorization

**WebSocket Client Terminal Should Show**:
```
📨 Received card action event
   Session ID: 550e8400-e29b-41d4-a716-446655440000
   OpenID: ou_7dab8a3d3cdcc08c560abcd
   Action: user_auth
🔄 Exchanging authorization code for token...
✅ Authorization completed!
   User: 张三 (zhangsan@example.com)
   Token expires: 2026-01-26 10:05:00
```

**Check Database**:
```bash
psql $DATABASE_URL -c "
SELECT session_id, state, user_name, email, token_expires_at
FROM user_auth_sessions
WHERE session_id = '550e8400-e29b-41d4-a716-446655440000';"
```

**Expected Output**:
```
               session_id                | state    | user_name | email              | token_expires_at
-----------------------------------------+----------+-----------+--------------------+-------------------
 550e8400-e29b-41d4-a716-446655440000    | completed| 张三      | zhangsan@example.com | 2026-01-26 10:05:00
```

---

### Step 6: Use Token for aPaaS API (1 minute)

Create `test_ai_api.py`:

```python
import asyncio
import os
from dotenv import load_dotenv

from lark_service.apaas.client import aPaaSClient
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.core.database import get_db_session

load_dotenv()

async def test_ai_api(user_id: str, prompt: str):
    """Test aPaaS AI API with user_access_token."""
    db_session = get_db_session()
    auth_manager = AuthSessionManager(db_session)

    # Initialize aPaaS client with auth manager
    apaas_client = aPaaSClient(
        app_id=os.getenv("APP_ID"),
        auth_manager=auth_manager
    )

    try:
        # Call AI API (auto-injects user_access_token)
        result = await apaas_client.call_ai_api(
            user_id=user_id,
            prompt=prompt
        )

        print("✅ AI API call successful!")
        print(f"Result: {result}")

    except Exception as e:
        print(f"❌ AI API call failed: {e}")

if __name__ == "__main__":
    user_id = "ou_7dab8a3d3cdcc08c560abcd"  # Replace with your OpenID
    prompt = "你好,请介绍一下飞书"

    asyncio.run(test_ai_api(user_id, prompt))
```

**Run**:
```bash
python test_ai_api.py
```

**Expected Output**:
```
✅ AI API call successful!
Result: {
  "response": "飞书是一款企业协作平台...",
  "usage": {"total_tokens": 150}
}
```

---

## 🎉 Success!

You've completed the 5-minute quickstart! Your system can now:
- ✅ Establish WebSocket connection with Feishu
- ✅ Send authorization cards to users
- ✅ Receive authorization callbacks via WebSocket
- ✅ Automatically exchange authorization codes for tokens
- ✅ Use tokens to call aPaaS AI APIs

---

## 🔧 Troubleshooting

### Issue 1: WebSocket Connection Failed

**Symptoms**:
```
❌ WebSocket connection failed: Connection refused
```

**Solution**:
1. Check APP_ID and APP_SECRET are correct
2. Verify network allows WebSocket connections
3. Check Feishu server status: https://status.feishu.cn

### Issue 2: Authorization Card Not Received

**Symptoms**:
- Card sent successfully (message_id returned)
- User doesn't see the card in Feishu

**Solution**:
1. Verify user_id (OpenID) is correct
2. Check if bot is in the same chat/group as user
3. Check messaging client logs for errors

### Issue 3: Token Exchange Failed

**Symptoms**:
```
❌ Authorization code exchange failed: Invalid authorization code
```

**Solution**:
1. Check if authorization_code is present in event
2. Verify event signature is valid
3. Check if authorization code has expired (5-minute window)
4. Review Feishu API logs

### Issue 4: Database Connection Error

**Symptoms**:
```
❌ Could not connect to database
```

**Solution**:
1. Verify DATABASE_URL is correct
2. Check PostgreSQL is running: `pg_isready`
3. Run migrations: `alembic upgrade head`
4. Check database credentials

---

## 📚 Next Steps

### Learn More

- [WebSocket Client Advanced Configuration](../plan.md#websocket-config)
- [Token Lifecycle Management](../plan.md#token-lifecycle)
- [Security Best Practices](../spec.md#security)
- [Monitoring and Metrics](../plan.md#monitoring)

### Extend Your Implementation

#### 1. Add Token Auto-Refresh

See `plan.md` Phase 7 (User Story 3) for automatic token refresh implementation.

#### 2. Customize Authorization Card

```python
options = AuthCardOptions(
    include_detailed_description=False,  # Use concise version
    auth_card_template_id="tpl_custom_123",  # Your custom template
    custom_message="请授权以解锁更多功能",
    privacy_policy_url="https://example.com/privacy"
)
```

#### 3. Add Monitoring

```python
from lark_service.monitoring.websocket_metrics import (
    websocket_connection_status,
    user_auth_success_rate
)

# After authorization completed
user_auth_success_rate.set(0.95)  # 95% success rate
websocket_connection_status.set(1)  # Connected
```

#### 4. Batch User Information Sync

Enable periodic user info updates in `.env`:

```bash
# Enable async user info sync
USER_INFO_SYNC_ENABLED=true
USER_INFO_SYNC_SCHEDULE="0 2 * * *"  # Daily at 2 AM
```

---

## 🐞 Debug Mode

Enable debug logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("lark_service")
logger.setLevel(logging.DEBUG)
```

**Debug Output Example**:
```
DEBUG:lark_service.events.websocket_client:Connecting to wss://open.feishu.cn/ws...
DEBUG:lark_service.events.websocket_client:WebSocket connected, registering handlers...
DEBUG:lark_service.auth.card_auth_handler:Received card action event for session 550e8400...
DEBUG:lark_service.auth.card_auth_handler:Extracting authorization_code from event...
DEBUG:lark_service.auth.card_auth_handler:Calling Feishu API to exchange token...
DEBUG:lark_service.auth.session_manager:Completing session 550e8400... with token u-7dCz4T***
DEBUG:lark_service.auth.session_manager:Session completed successfully
```

---

## 📖 Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ID` | ✅ | - | Feishu application ID |
| `APP_SECRET` | ✅ | - | Feishu application secret |
| `DATABASE_URL` | ✅ | - | Database connection URL |
| `ENCRYPTION_KEY` | ✅ | - | 32-byte hex key for token encryption |
| `WEBSOCKET_MAX_RECONNECT_RETRIES` | ❌ | 10 | Max reconnection attempts |
| `WEBSOCKET_HEARTBEAT_INTERVAL` | ❌ | 30 | Heartbeat interval (seconds) |
| `WEBSOCKET_FALLBACK_TO_HTTP` | ❌ | true | Enable HTTP callback fallback |
| `USER_INFO_SYNC_ENABLED` | ❌ | false | Enable periodic user info sync |
| `USER_INFO_SYNC_SCHEDULE` | ❌ | "0 2 * * *" | Cron schedule for sync |

### Key Files

```
lark-service/
├── .env                          # Environment configuration
├── app.py                        # WebSocket client main entry
├── send_auth_card.py             # Send auth card utility
├── test_ai_api.py                # Test AI API utility
├── src/lark_service/
│   ├── events/
│   │   ├── websocket_client.py   # WebSocket client implementation
│   │   └── types.py              # WebSocket types and config
│   ├── auth/
│   │   ├── session_manager.py    # Auth session management
│   │   ├── card_auth_handler.py  # Card authorization handler
│   │   ├── exceptions.py         # Auth exceptions
│   │   └── types.py              # Auth types
│   └── apaas/
│       └── client.py             # aPaaS client (with user token support)
└── migrations/
    └── versions/
        └── 20260119_xxx_extend_auth_session.py  # Database migration
```

---

**Quickstart Version**: 1.0.0
**Last Updated**: 2026-01-19
**Estimated Time**: 5 minutes
**Next**: Continue to [tasks.md](./tasks.md) for full implementation guide
