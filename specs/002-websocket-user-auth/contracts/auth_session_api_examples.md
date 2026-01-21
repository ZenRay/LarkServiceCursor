# Usage Examples

## Example 1: Create Session

**Request**:
```http
POST /internal/auth/sessions
Content-Type: application/json

{
  "app_id": "cli_a1b2c3d4e5f6g7h8",
  "user_id": "ou_7dab8a3d3cdcc08c560abcd",
  "auth_method": "websocket_card"
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 12345,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "app_id": "cli_a1b2c3d4e5f6g7h8",
  "user_id": "ou_7dab8a3d3cdcc08c560abcd",
  "open_id": null,
  "auth_method": "websocket_card",
  "state": "pending",
  "created_at": "2026-01-19T10:00:00Z",
  "expires_at": "2026-01-19T10:10:00Z",
  "completed_at": null
}
```

## Example 2: Complete Session

**Request**:
```http
PATCH /internal/auth/sessions/550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "user_access_token": "u-7dCz4T1Bx9KyLmNpQrStUvWxYz",
  "token_expires_at": "2026-01-26T10:05:00Z",
  "user_info": {
    "name": "张三",
    "user_id": "7123456789012345678",
    "open_id": "ou_7dab8a3d3cdcc08c560abcd",
    "union_id": "on_8e89a9c0d4e5f6a7b8c9d0e1",
    "mobile": "+86-13800138000",
    "email": "zhangsan@example.com"
  }
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 12345,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "completed",
  "open_id": "ou_7dab8a3d3cdcc08c560abcd",
  "user_name": "张三",
  "completed_at": "2026-01-19T10:05:00Z"
}
```

## Example 3: Get Active Token

**Request**:
```http
GET /internal/auth/tokens/cli_a1b2c3d4e5f6g7h8/ou_7dab8a3d3cdcc08c560abcd
```

**Response (Token Found)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "user_access_token": "u-7dCz4T1Bx9KyLmNpQrStUvWxYz",
  "token_expires_at": "2026-01-26T10:05:00Z",
  "is_expiring": false
}
```

**Response (No Token)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "user_access_token": null,
  "token_expires_at": null,
  "is_expiring": false
}
```

## Example 4: Send Authorization Card

**Request**:
```http
POST /internal/auth/cards/send
Content-Type: application/json

{
  "app_id": "cli_a1b2c3d4e5f6g7h8",
  "user_id": "ou_7dab8a3d3cdcc08c560abcd",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "options": {
    "include_detailed_description": true,
    "auth_card_template_id": null,
    "custom_message": "请授权以使用 AI 能力"
  }
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message_id": "om_7dCz4T1Bx9Ky2Lm3Np4Qr5St6Uv",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

# Implementation Notes

## Method Mapping

| API Endpoint | Python Method |
|--------------|---------------|
| `POST /internal/auth/sessions` | `AuthSessionManager.create_session()` |
| `GET /internal/auth/sessions/{id}` | `AuthSessionManager.get_session()` |
| `PATCH /internal/auth/sessions/{id}` | `AuthSessionManager.complete_session()` |
| `GET /internal/auth/tokens/{app}/{user}` | `AuthSessionManager.get_active_token()` |
| `POST /internal/auth/tokens/{app}/{user}` | `AuthSessionManager.refresh_token()` |
| `DELETE /internal/auth/sessions/cleanup` | `AuthSessionManager.cleanup_expired_sessions()` |
| `POST /internal/auth/cards/send` | `CardAuthHandler.send_auth_card()` |
| `POST /internal/auth/cards/callback` | `CardAuthHandler.handle_card_auth_event()` |

## Type Signatures (Python)

```python
class AuthSessionManager:
    def create_session(
        self,
        app_id: str,
        user_id: str,
        auth_method: str = "websocket_card"
    ) -> UserAuthSession: ...

    def get_session(self, session_id: str) -> UserAuthSession | None: ...

    def complete_session(
        self,
        session_id: str,
        user_access_token: str,
        token_expires_at: datetime,
        user_info: dict
    ) -> None: ...

    def get_active_token(
        self,
        app_id: str,
        user_id: str
    ) -> str | None: ...

    def refresh_token(
        self,
        app_id: str,
        user_id: str
    ) -> str: ...

    def cleanup_expired_sessions(self) -> int: ...

class CardAuthHandler:
    async def send_auth_card(
        self,
        app_id: str,
        user_id: str,
        session_id: str,
        options: AuthCardOptions | None = None
    ) -> str: ...

    async def handle_card_auth_event(
        self,
        event: P2CardActionTrigger
    ) -> P2CardActionTriggerResponse: ...
```

---

**Contract Version**: 1.0.0
**Status**: ✅ Complete
**Last Updated**: 2026-01-19
**Next Step**: Generate quickstart guide (T004)
