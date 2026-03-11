# 消息服务

本文档覆盖消息模块的主要发送与生命周期能力，示例均与当前接口签名保持一致。

## 快速开始

```python
from lark_service.messaging import MessagingClient

messaging_client = MessagingClient(credential_pool=credential_pool)

response = messaging_client.send_text_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    content="Hello, Lark!"
)
print(response["message_id"])
```

## 接收者类型说明

- `receive_id_type="open_id"`: 发送给个人（`receiver_id` 示例：`ou_xxx`）
- `receive_id_type="chat_id"`: 发送到群聊（`receiver_id` 示例：`oc_xxx`）
- 默认值是 `open_id`

## 各类消息发送示例

### 1) 文本消息

```python
response = messaging_client.send_text_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    content="系统通知：任务执行成功"
)
```

### 2) 富文本消息（post）

```python
rich_content = {
    "zh_cn": {
        "title": "发布通知",
        "content": [
            [{"tag": "text", "text": "版本已发布，查看 "}, {"tag": "a", "text": "发布说明", "href": "https://example.com/release"}],
            [{"tag": "text", "text": "如有问题请联系管理员"}],
        ],
    }
}

response = messaging_client.send_rich_text_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    content=rich_content
)
```

### 3) 图片消息

```python
# 方式 A: 传本地路径，自动上传
response = messaging_client.send_image_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    image_path="assets/alert.png"
)

# 方式 B: 使用已上传 image_key
response = messaging_client.send_image_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    image_key="img_v2_xxx"
)
```

### 4) 文件消息

```python
# 方式 A: 传本地路径，自动上传
response = messaging_client.send_file_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    file_path="reports/daily-report.pdf"
)

# 方式 B: 使用已上传 file_key
response = messaging_client.send_file_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    file_key="file_v2_xxx"
)
```

### 5) 交互式卡片消息

```python
from lark_service.cardkit.builder import CardBuilder

card = (
    CardBuilder()
    .add_header("服务告警", template="red")
    .add_markdown("**CPU 使用率超过阈值**")
    .add_button("查看监控", url="https://example.com/monitor", button_type="primary")
    .build()
)

response = messaging_client.send_card_message(
    app_id="cli_xxx",
    receiver_id="oc_xxx",              # 群聊示例
    card_content=card,
    receive_id_type="chat_id"
)
```

### 6) 批量发送

```python
batch_result = messaging_client.send_batch_messages(
    app_id="cli_xxx",
    receiver_ids=["ou_user1", "ou_user2", "ou_user3"],
    msg_type="text",
    content={"text": "今晚 22:00 进行系统维护"},
    continue_on_error=True
)

print(batch_result.total, batch_result.success, batch_result.failed)
for item in batch_result.results:
    print(item.receiver_id, item.status, item.message_id, item.error)
```

## 消息生命周期（撤回、编辑、回复）

`MessagingClient` 负责发送；消息生命周期由 `MessageLifecycleManager` 提供。

```python
from lark_service.messaging import MessageLifecycleManager

lifecycle = MessageLifecycleManager(credential_pool=credential_pool)
```

### 撤回消息

```python
result = lifecycle.recall_message(
    app_id="cli_xxx",
    message_id="om_xxx"
)
print(result["success"])
```

### 编辑文本消息

```python
result = lifecycle.edit_message(
    app_id="cli_xxx",
    message_id="om_xxx",
    content="这是编辑后的文本"
)
print(result["success"])
```

### 回复消息

```python
# 文本回复
result = lifecycle.reply_message(
    app_id="cli_xxx",
    message_id="om_xxx",
    msg_type="text",
    content={"text": "已收到，正在处理"}
)
print(result["reply_message_id"])
```

## 常见易错点

- `send_card_message` 参数名是 `card_content`，不是 `card`
- `send_image_message` 必须提供 `image_path` 或 `image_key` 二选一
- `send_file_message` 必须提供 `file_path` 或 `file_key` 二选一
- 批量发送 `msg_type="text"` 时，建议使用 `content={"text": "..."}`
- 生命周期操作需要 `message_id`（通常来自发送响应中的 `message_id`）

## 与卡片更新的关系

卡片发送在消息服务中完成；卡片内容更新不在 `MessagingClient` 中，请使用卡片服务能力（参见 [卡片服务](card.md)）。

## 应用管理

LarkService 支持多应用管理和灵活切换，详细说明见 [应用管理文档](app-management.md)。

更多参考：
- [5 层 app_id 解析优先级](app-management.md)
- [多应用场景](app-management.md)
- [动态切换应用](app-management.md)
- [高级用法](advanced.md)
