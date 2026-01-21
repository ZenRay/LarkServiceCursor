# Example Events

## Example 1: User Clicks "Authorize" Button (Before Auth)

```yaml
schema: "2.0"
header:
  event_id: "5e3702a84e847582fcf4ea1bdcb8fb2e"
  event_type: "card.action.trigger"
  create_time: "1737292800000"
  token: "abc123def456"
  app_id: "cli_a1b2c3d4e5f6g7h8"
  tenant_key: "2d520a3c7b6e1d06"
event:
  operator:
    open_id: "ou_7dab8a3d3cdcc08c560abcd"
    user_id: "7123456789012345678"
  token: "c-7dCz4T..."
  action:
    tag: "button"
    value:
      action_type: "user_auth"
      session_id: "550e8400-e29b-41d4-a716-446655440000"
      timestamp: 1737292805000
  context:
    open_message_id: "om_7dCz4T1Bx9Ky2Lm3Np4Qr5St6Uv"
    open_chat_id: "oc_7dCz4T1Bx9Ky2Lm3Np4Qr5St6Uv"
    host: "https://applink.feishu.cn"
```

## Example 2: Authorization Callback (With authorization_code)

```yaml
schema: "2.0"
header:
  event_id: "6f4803b95f958693adf5fb2cedcafe3f"
  event_type: "card.action.trigger"
  create_time: "1737292810000"
  token: "abc123def456"
  app_id: "cli_a1b2c3d4e5f6g7h8"
event:
  operator:
    open_id: "ou_7dab8a3d3cdcc08c560abcd"
    user_id: "7123456789012345678"
    union_id: "on_8e89a9c0d4e5f6a7b8c9d0e1"
  action:
    tag: "button"
    value:
      action_type: "user_auth"
      session_id: "550e8400-e29b-41d4-a716-446655440000"
      authorization_code: "auth_7dCz4T1Bx9KyLmNpQrStUvWxYz"  # ← KEY FIELD
      timestamp: 1737292810000
```

## Example 3: User Cancels Authorization

```yaml
schema: "2.0"
header:
  event_id: "7g5914c06g069704beg6gc3dfedcgf4g"
  event_type: "card.action.trigger"
  create_time: "1737292815000"
  token: "abc123def456"
  app_id: "cli_a1b2c3d4e5f6g7h8"
event:
  operator:
    open_id: "ou_7dab8a3d3cdcc08c560abcd"
  action:
    tag: "button"
    value:
      action_type: "user_auth_cancel"
      session_id: "550e8400-e29b-41d4-a716-446655440000"
      timestamp: 1737292815000
```

---

# Validation Rules

## Event Signature Verification

```python
import hashlib
import hmac

def verify_event_signature(
    timestamp: str,
    nonce: str,
    encrypt_key: str,
    body: str,
    signature: str
) -> bool:
    """Verify event signature."""
    message = f"{timestamp}{nonce}{encrypt_key}{body}"
    expected_signature = hmac.new(
        encrypt_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
```

## Field Validation

### session_id
- **Format**: UUID v4
- **Example**: `550e8400-e29b-41d4-a716-446655440000`
- **Validation**: Must match pattern `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`

### open_id
- **Format**: `ou_` prefix + 20-24 alphanumeric characters
- **Example**: `ou_7dab8a3d3cdcc08c560abcd`
- **Validation**: Must match pattern `^ou_[a-zA-Z0-9]{20,24}$`

### authorization_code
- **Format**: `auth_` prefix + 32-64 alphanumeric/dash/underscore characters
- **Example**: `auth_7dCz4T1Bx9KyLmNpQrStUvWxYz`
- **Validation**: Must match pattern `^auth_[a-zA-Z0-9_-]{32,64}$`
- **Presence**: Only present in callback after successful authorization

---

# Error Scenarios

## Scenario 1: Missing authorization_code

**Symptom**: User clicks "Authorize" but `authorization_code` is missing in callback

**Possible Causes**:
- User hasn't completed Feishu authorization flow
- Authorization was denied by user
- Feishu API error

**Handling**:
- Return card update with error message
- Log event for debugging
- Do NOT create/complete auth session

## Scenario 2: Invalid session_id

**Symptom**: `session_id` doesn't exist in database

**Possible Causes**:
- Session expired (> 10 minutes)
- Session already used
- Malicious event

**Handling**:
- Return card update with "Session expired" message
- Log suspicious event
- Ignore event (do not process)

## Scenario 3: Duplicate Events

**Symptom**: Multiple events with same `session_id` and `event_id`

**Possible Causes**:
- Network retry
- Feishu system retry

**Handling**:
- Use `event_id` for idempotency check
- Process only first event
- Return cached response for duplicates

---

# Contract Testing

## Test Cases

### TC-001: Valid Authorization Event
```yaml
Given:
  - Valid P2CardActionTrigger event
  - event.action.value.authorization_code exists
  - event.operator.open_id is valid

When:
  - Event is received via WebSocket

Then:
  - Event passes validation
  - authorization_code is extracted
  - session_id is extracted
  - Event is processed successfully
```

### TC-002: Missing Required Fields
```yaml
Given:
  - P2CardActionTrigger event missing event.operator.open_id

When:
  - Event is received via WebSocket

Then:
  - Event fails validation
  - Error is logged
  - Event is rejected
```

### TC-003: Invalid Signature
```yaml
Given:
  - Valid event payload
  - Invalid X-Lark-Signature header

When:
  - Event is received via WebSocket

Then:
  - Signature verification fails
  - Event is rejected
  - Security alert is logged
```

---

**Contract Version**: 1.0.0
**Status**: ✅ Complete
**Last Updated**: 2026-01-19
**Next Step**: Generate auth session API contract (T003)
