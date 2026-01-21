# 消息服务

TODO: 待补充完整的消息服务使用指南

## 基本用法

```python
from lark_service.messaging import MessagingClient

messaging_client = MessagingClient(credential_pool=credential_pool)

# 发送文本消息
response = messaging_client.send_text_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    content="Hello, Lark!"
)
```

详细文档开发中...
