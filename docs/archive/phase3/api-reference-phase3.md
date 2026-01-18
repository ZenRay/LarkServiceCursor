# Phase 3 API 参考文档 - Messaging & CardKit

**版本**: v0.2.0
**更新日期**: 2026-01-15
**适用范围**: Phase 3 消息与交互式卡片功能

---

## 目录

- [Messaging 模块](#messaging-模块)
  - [MessagingClient](#messagingclient)
  - [MessageLifecycleManager](#messagelifecyclemanager)
  - [MediaUploader](#mediauploader)
- [CardKit 模块](#cardkit-模块)
  - [CardBuilder](#cardbuilder)
  - [CallbackHandler](#callbackhandler)
  - [CardUpdater](#cardupdater)
- [数据模型](#数据模型)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

---

## Messaging 模块

### MessagingClient

消息发送客户端,支持发送文本、富文本、图片、文件、卡片消息以及批量发送。

#### 初始化

```python
from lark_service.messaging import MessagingClient
from lark_service.core import CredentialPool, RetryStrategy

# 创建客户端
client = MessagingClient(
    credential_pool=credential_pool,
    retry_strategy=retry_strategy
)
```

**参数**:
- `credential_pool` (CredentialPool): 凭证池实例
- `retry_strategy` (RetryStrategy): 重试策略实例

---

#### send_text_message()

发送文本消息。

```python
def send_text_message(
    self,
    app_id: str,
    receiver_id: str,
    content: str,
    receive_id_type: str = "open_id"
) -> dict[str, Any]
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `receiver_id` (str): 接收者 ID (用户或群组)
- `content` (str): 消息文本内容
- `receive_id_type` (str): 接收者 ID 类型,可选值:
  - `"open_id"` (默认): 应用内用户标识
  - `"user_id"`: 租户内用户标识
  - `"union_id"`: 跨租户用户标识
  - `"email"`: 用户邮箱
  - `"chat_id"`: 群组 ID

**返回值**:
```python
{
    "message_id": "om_abc123...",
    "msg_type": "text",
    "create_time": "1642512345"
}
```

**异常**:
- `InvalidParameterError`: 参数无效 (如 content 为空)
- `RetryableError`: 可重试错误 (网络超时等)
- `ValidationError`: 数据验证失败

**示例**:
```python
# 发送给用户
response = client.send_text_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_test_user_123",
    content="您有新的工单待处理"
)

# 发送给群组
response = client.send_text_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="oc_test_group_456",
    content="系统维护通知",
    receive_id_type="chat_id"
)
```

---

#### send_rich_text_message()

发送富文本消息,支持格式化、链接、@提及等。

```python
def send_rich_text_message(
    self,
    app_id: str,
    receiver_id: str,
    content: dict[str, Any],
    receive_id_type: str = "open_id"
) -> dict[str, Any]
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `receiver_id` (str): 接收者 ID
- `content` (dict): 富文本内容结构
- `receive_id_type` (str): 接收者 ID 类型

**富文本内容结构**:
```python
{
    "zh_cn": {  # 语言代码
        "title": "通知标题",
        "content": [
            [  # 第一段
                {"tag": "text", "text": "普通文本 "},
                {"tag": "text", "text": "加粗文本", "style": ["bold"]},
                {"tag": "a", "text": "链接文本", "href": "https://example.com"},
                {"tag": "at", "user_id": "ou_xxx"}  # @提及用户
            ],
            [  # 第二段
                {"tag": "text", "text": "第二段内容"}
            ]
        ]
    }
}
```

**支持的标签**:
- `text`: 文本,支持样式: `bold`, `italic`, `underline`, `lineThrough`
- `a`: 链接
- `at`: @提及用户
- `img`: 图片 (需要 image_key)

**示例**:
```python
content = {
    "zh_cn": {
        "title": "审批通知",
        "content": [
            [
                {"tag": "text", "text": "您的请假申请已被 "},
                {"tag": "text", "text": "批准", "style": ["bold"]},
                {"tag": "text", "text": ",详情请查看 "},
                {"tag": "a", "text": "审批系统", "href": "https://approval.example.com"}
            ]
        ]
    }
}

response = client.send_rich_text_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_test_user_123",
    content=content
)
```

---

#### send_image_message()

发送图片消息,支持自动上传或使用已有 image_key。

```python
def send_image_message(
    self,
    app_id: str,
    receiver_id: str,
    image_path: str | None = None,
    image_key: str | None = None,
    receive_id_type: str = "open_id"
) -> dict[str, Any]
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `receiver_id` (str): 接收者 ID
- `image_path` (str, optional): 本地图片路径 (自动上传)
- `image_key` (str, optional): 已上传的图片 key
- `receive_id_type` (str): 接收者 ID 类型

**注意**: `image_path` 和 `image_key` 必须提供其中之一。

**支持的图片格式**:
- JPG/JPEG
- PNG
- GIF
- BMP
- WEBP

**大小限制**: 10 MB

**示例**:
```python
# 方式 1: 自动上传本地图片
response = client.send_image_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_test_user_123",
    image_path="/path/to/report.png"
)

# 方式 2: 使用已上传的 image_key
response = client.send_image_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_test_user_123",
    image_key="img_v2_abc123..."
)
```

---

#### send_file_message()

发送文件消息,支持自动上传或使用已有 file_key。

```python
def send_file_message(
    self,
    app_id: str,
    receiver_id: str,
    file_path: str | None = None,
    file_key: str | None = None,
    receive_id_type: str = "open_id"
) -> dict[str, Any]
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `receiver_id` (str): 接收者 ID
- `file_path` (str, optional): 本地文件路径 (自动上传)
- `file_key` (str, optional): 已上传的文件 key
- `receive_id_type` (str): 接收者 ID 类型

**支持的文件类型**:
- 文档: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
- 压缩包: ZIP, RAR, 7Z
- 视频: MP4, AVI, MOV, WMV
- 音频: MP3, WAV, AAC

**大小限制**: 30 MB

**示例**:
```python
# 发送本地文件
response = client.send_file_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_test_user_123",
    file_path="/path/to/document.pdf"
)
```

---

#### send_card_message()

发送交互式卡片消息。

```python
def send_card_message(
    self,
    app_id: str,
    receiver_id: str,
    card_content: dict[str, Any],
    receive_id_type: str = "open_id"
) -> dict[str, Any]
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `receiver_id` (str): 接收者 ID
- `card_content` (dict): 卡片内容 (使用 CardBuilder 构建)
- `receive_id_type` (str): 接收者 ID 类型

**示例**:
```python
from lark_service.cardkit import CardBuilder

# 构建卡片
builder = CardBuilder()
card = builder.build_notification_card(
    title="系统通知",
    content="服务器将于今晚 22:00 进行维护",
    level="warning"
)

# 发送卡片
response = client.send_card_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_test_user_123",
    card_content=card
)
```

---

#### send_batch_messages()

批量发送相同消息给多个接收者。

```python
def send_batch_messages(
    self,
    app_id: str,
    receiver_ids: list[str],
    msg_type: str,
    content: dict[str, Any] | str,
    receive_id_type: str = "open_id",
    continue_on_error: bool = True
) -> BatchSendResponse
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `receiver_ids` (list[str]): 接收者 ID 列表 (最多 200 个)
- `msg_type` (str): 消息类型 (`"text"`, `"post"`, `"image"`, `"file"`, `"interactive"`)
- `content` (dict | str): 消息内容
- `receive_id_type` (str): 接收者 ID 类型
- `continue_on_error` (bool): 遇到错误是否继续发送其他消息

**返回值**:
```python
BatchSendResponse(
    total=100,           # 总数
    success=98,          # 成功数
    failed=2,            # 失败数
    results=[            # 详细结果
        BatchSendResult(
            receiver_id="ou_user1",
            status="success",
            message_id="om_abc123...",
            error=None
        ),
        BatchSendResult(
            receiver_id="ou_user2",
            status="failed",
            message_id=None,
            error="User not found"
        )
    ]
)
```

**示例**:
```python
# 批量发送文本消息
receiver_ids = ["ou_user1", "ou_user2", "ou_user3"]

response = client.send_batch_messages(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_ids=receiver_ids,
    msg_type="text",
    content={"text": "系统维护通知"},
    continue_on_error=True
)

print(f"成功: {response.success}/{response.total}")
print(f"失败: {response.failed}/{response.total}")

# 检查失败的消息
for result in response.results:
    if result.status == "failed":
        print(f"发送失败: {result.receiver_id}, 原因: {result.error}")
```

---

### MessageLifecycleManager

消息生命周期管理,支持撤回、编辑、回复消息。

#### 初始化

```python
from lark_service.messaging import MessageLifecycleManager

manager = MessageLifecycleManager(
    credential_pool=credential_pool,
    retry_strategy=retry_strategy
)
```

---

#### recall_message()

撤回已发送的消息。

```python
def recall_message(
    self,
    app_id: str,
    message_id: str
) -> dict[str, Any]
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `message_id` (str): 消息 ID

**返回值**:
```python
{
    "success": True,
    "message_id": "om_abc123..."
}
```

**注意**: 只能撤回自己发送的消息,且有时间限制 (通常 24 小时内)。

**示例**:
```python
# 撤回消息
result = manager.recall_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    message_id="om_abc123..."
)
```

---

#### edit_message()

编辑已发送的文本消息。

```python
def edit_message(
    self,
    app_id: str,
    message_id: str,
    content: str
) -> dict[str, Any]
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `message_id` (str): 消息 ID
- `content` (str): 新的消息内容

**返回值**:
```python
{
    "success": True,
    "message_id": "om_abc123..."
}
```

**限制**: 仅支持编辑文本消息 (`msg_type="text"`)。

**示例**:
```python
# 编辑消息
result = manager.edit_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    message_id="om_abc123...",
    content="更新后的消息内容"
)
```

---

#### reply_message()

回复指定消息。

```python
def reply_message(
    self,
    app_id: str,
    message_id: str,
    msg_type: str,
    content: dict[str, Any] | str
) -> dict[str, Any]
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `message_id` (str): 要回复的消息 ID
- `msg_type` (str): 回复消息的类型
- `content` (dict | str): 回复消息的内容

**返回值**:
```python
{
    "reply_message_id": "om_reply_456...",
    "original_message_id": "om_abc123..."
}
```

**示例**:
```python
# 回复文本消息
result = manager.reply_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    message_id="om_abc123...",
    msg_type="text",
    content={"text": "已收到,正在处理"}
)
```

---

### MediaUploader

媒体文件上传器,支持图片和文件上传。

#### 初始化

```python
from lark_service.messaging import MediaUploader

uploader = MediaUploader(
    credential_pool=credential_pool,
    retry_strategy=retry_strategy
)
```

---

#### upload_image()

上传图片文件。

```python
def upload_image(
    self,
    app_id: str,
    image_path: str
) -> str
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `image_path` (str): 本地图片路径

**返回值**: `image_key` (str)

**示例**:
```python
# 上传图片
image_key = uploader.upload_image(
    app_id="cli_a1b2c3d4e5f6g7h8",
    image_path="/path/to/image.png"
)

# 使用 image_key 发送消息
client.send_image_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_test_user_123",
    image_key=image_key
)
```

---

#### upload_file()

上传文件。

```python
def upload_file(
    self,
    app_id: str,
    file_path: str
) -> str
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `file_path` (str): 本地文件路径

**返回值**: `file_key` (str)

**示例**:
```python
# 上传文件
file_key = uploader.upload_file(
    app_id="cli_a1b2c3d4e5f6g7h8",
    file_path="/path/to/document.pdf"
)
```

---

## CardKit 模块

### CardBuilder

交互式卡片构建器,提供模板方法快速构建常见卡片。

#### 初始化

```python
from lark_service.cardkit import CardBuilder

builder = CardBuilder()
```

---

#### build_card()

通用卡片构建方法。

```python
def build_card(
    self,
    header: dict[str, Any],
    elements: list[dict[str, Any]],
    config: dict[str, Any] | None = None
) -> dict[str, Any]
```

**参数**:
- `header` (dict): 卡片头部配置
- `elements` (list): 卡片元素列表
- `config` (dict, optional): 卡片配置

**示例**:
```python
card = builder.build_card(
    header={
        "title": {
            "tag": "plain_text",
            "content": "自定义卡片"
        }
    },
    elements=[
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "卡片内容"
            }
        }
    ]
)
```

---

#### build_approval_card()

构建审批卡片。

```python
def build_approval_card(
    self,
    title: str,
    applicant: str,
    fields: dict[str, str],
    approve_action_id: str,
    reject_action_id: str,
    note: str | None = None
) -> dict[str, Any]
```

**参数**:
- `title` (str): 卡片标题
- `applicant` (str): 申请人
- `fields` (dict): 申请信息字段 (key: 字段名, value: 字段值)
- `approve_action_id` (str): 批准按钮的 action_id
- `reject_action_id` (str): 拒绝按钮的 action_id
- `note` (str, optional): 备注信息

**示例**:
```python
card = builder.build_approval_card(
    title="请假申请",
    applicant="张三",
    fields={
        "类型": "年假",
        "天数": "3天",
        "开始日期": "2026-01-20",
        "结束日期": "2026-01-22",
        "理由": "家庭旅行"
    },
    approve_action_id="approve_leave",
    reject_action_id="reject_leave",
    note="请在 24 小时内审批"
)
```

---

#### build_notification_card()

构建通知卡片。

```python
def build_notification_card(
    self,
    title: str,
    content: str,
    level: str = "info",
    action_text: str | None = None,
    action_url: str | None = None
) -> dict[str, Any]
```

**参数**:
- `title` (str): 通知标题
- `content` (str): 通知内容
- `level` (str): 通知级别 (`"info"`, `"warning"`, `"error"`, `"success"`)
- `action_text` (str, optional): 操作按钮文本
- `action_url` (str, optional): 操作按钮链接

**示例**:
```python
card = builder.build_notification_card(
    title="系统维护通知",
    content="服务器将于今晚 22:00-23:00 进行维护,期间服务可能不可用",
    level="warning",
    action_text="查看详情",
    action_url="https://status.example.com"
)
```

---

#### build_form_card()

构建表单卡片。

```python
def build_form_card(
    self,
    title: str,
    fields: list[dict[str, Any]],
    submit_action_id: str,
    cancel_action_id: str | None = None
) -> dict[str, Any]
```

**参数**:
- `title` (str): 表单标题
- `fields` (list): 表单字段列表
- `submit_action_id` (str): 提交按钮的 action_id
- `cancel_action_id` (str, optional): 取消按钮的 action_id

**字段结构**:
```python
{
    "label": "字段标签",
    "name": "字段名称",
    "type": "input",  # input, textarea, select
    "placeholder": "提示文本",
    "required": True,
    "options": ["选项1", "选项2"]  # 仅 select 类型需要
}
```

**示例**:
```python
card = builder.build_form_card(
    title="反馈表单",
    fields=[
        {
            "label": "姓名",
            "name": "name",
            "type": "input",
            "placeholder": "请输入姓名",
            "required": True
        },
        {
            "label": "反馈类型",
            "name": "type",
            "type": "select",
            "placeholder": "请选择类型",
            "options": ["功能建议", "Bug反馈", "其他"],
            "required": True
        },
        {
            "label": "详细描述",
            "name": "description",
            "type": "textarea",
            "placeholder": "请详细描述您的反馈",
            "required": True
        }
    ],
    submit_action_id="submit_feedback",
    cancel_action_id="cancel_feedback"
)
```

---

### CallbackHandler

卡片交互回调处理器,处理用户点击卡片按钮等交互事件。

#### 初始化

```python
from lark_service.cardkit import CallbackHandler

handler = CallbackHandler(
    verification_token="your_verification_token",
    encrypt_key="your_encrypt_key"
)
```

**参数**:
- `verification_token` (str): 飞书应用的 Verification Token
- `encrypt_key` (str): 飞书应用的 Encrypt Key

---

#### handle_callback()

处理回调请求的主入口。

```python
def handle_callback(
    self,
    request_data: dict[str, Any]
) -> dict[str, Any]
```

**参数**:
- `request_data` (dict): 飞书回调请求数据

**返回值**: 响应数据 (dict)

**示例**:
```python
# Flask 示例
@app.route('/lark/callback', methods=['POST'])
def lark_callback():
    request_data = request.json
    response = handler.handle_callback(request_data)
    return jsonify(response)
```

---

#### register_handler()

注册 action_id 对应的处理函数。

```python
def register_handler(
    self,
    action_id: str,
    handler_func: Callable[[CallbackEvent], dict[str, Any]]
) -> None
```

**参数**:
- `action_id` (str): 卡片按钮的 action_id
- `handler_func` (callable): 处理函数,接收 CallbackEvent,返回响应 dict

**示例**:
```python
# 注册审批处理器
def handle_approve(event: CallbackEvent) -> dict[str, Any]:
    user_id = event.user_id
    action_value = event.action.get("value", {})

    # 执行审批逻辑
    approve_request(action_value)

    # 返回更新后的卡片
    from lark_service.cardkit import CardBuilder, CardUpdater

    builder = CardBuilder()
    updater = CardUpdater(credential_pool, retry_strategy)

    new_card = builder.build_notification_card(
        title="审批结果",
        content="申请已批准",
        level="success"
    )

    return updater.build_update_response(
        card_content=new_card,
        toast_message="审批成功!"
    )

# 注册处理器
handler.register_handler("approve_action", handle_approve)
handler.register_handler("reject_action", handle_reject)
```

---

#### verify_signature()

验证回调请求的签名。

```python
def verify_signature(
    self,
    timestamp: str,
    nonce: str,
    body: str,
    signature: str
) -> bool
```

**参数**:
- `timestamp` (str): 请求时间戳
- `nonce` (str): 随机数
- `body` (str): 请求体 (JSON 字符串)
- `signature` (str): 签名

**返回值**: 签名是否有效 (bool)

---

### CardUpdater

卡片更新器,支持主动更新卡片内容或构建回调响应。

#### 初始化

```python
from lark_service.cardkit import CardUpdater

updater = CardUpdater(
    credential_pool=credential_pool,
    retry_strategy=retry_strategy
)
```

---

#### update_card_content()

主动更新已发送的卡片内容。

```python
def update_card_content(
    self,
    app_id: str,
    message_id: str,
    card_content: dict[str, Any]
) -> dict[str, Any]
```

**参数**:
- `app_id` (str): 飞书应用 ID
- `message_id` (str): 卡片消息 ID
- `card_content` (dict): 新的卡片内容

**返回值**:
```python
{
    "success": True,
    "message_id": "om_abc123..."
}
```

**示例**:
```python
# 构建新卡片
builder = CardBuilder()
new_card = builder.build_notification_card(
    title="更新通知",
    content="卡片内容已更新",
    level="success"
)

# 更新卡片
result = updater.update_card_content(
    app_id="cli_a1b2c3d4e5f6g7h8",
    message_id="om_abc123...",
    card_content=new_card
)
```

---

#### build_update_response()

构建卡片更新响应 (用于回调处理)。

```python
def build_update_response(
    self,
    card_content: dict[str, Any],
    toast_message: str | None = None
) -> dict[str, Any]
```

**参数**:
- `card_content` (dict): 新的卡片内容
- `toast_message` (str, optional): Toast 提示消息

**返回值**: 回调响应数据 (dict)

**示例**:
```python
# 在回调处理器中使用
def handle_submit(event: CallbackEvent) -> dict[str, Any]:
    # 处理表单提交
    form_data = event.action.get("value", {})
    process_form(form_data)

    # 构建成功卡片
    new_card = builder.build_notification_card(
        title="提交成功",
        content="感谢您的反馈!",
        level="success"
    )

    # 返回更新响应
    return updater.build_update_response(
        card_content=new_card,
        toast_message="提交成功!"
    )
```

---

## 数据模型

### Message

消息数据模型。

```python
from lark_service.messaging.models import Message, MessageType

message = Message(
    msg_type=MessageType.TEXT,
    content={"text": "Hello"},
    receive_id="ou_test_user_123",
    receive_id_type="open_id"
)
```

**字段**:
- `msg_type` (MessageType): 消息类型枚举
- `content` (dict | str): 消息内容
- `receive_id` (str): 接收者 ID
- `receive_id_type` (str): 接收者 ID 类型

---

### MessageType

消息类型枚举。

```python
from lark_service.messaging.models import MessageType

MessageType.TEXT          # 文本消息
MessageType.POST          # 富文本消息
MessageType.IMAGE         # 图片消息
MessageType.FILE          # 文件消息
MessageType.INTERACTIVE   # 交互式卡片消息
```

---

### ImageAsset

图片资源模型。

```python
from lark_service.messaging.models import ImageAsset

image = ImageAsset(
    image_key="img_v2_abc123...",
    size=1024000,  # 字节
    width=1920,
    height=1080
)
```

---

### FileAsset

文件资源模型。

```python
from lark_service.messaging.models import FileAsset

file = FileAsset(
    file_key="file_v2_xyz789...",
    file_name="document.pdf",
    file_type="pdf",
    size=2048000  # 字节
)
```

---

### BatchSendResponse

批量发送响应模型。

```python
from lark_service.messaging.models import BatchSendResponse, BatchSendResult

response = BatchSendResponse(
    total=100,
    success=98,
    failed=2,
    results=[...]
)
```

---

### CardConfig

卡片配置模型。

```python
from lark_service.cardkit.models import CardConfig

card = CardConfig(
    header={"title": {"tag": "plain_text", "content": "标题"}},
    elements=[...],
    config={"wide_screen_mode": True}
)
```

---

### CallbackEvent

回调事件模型。

```python
from lark_service.cardkit.models import CallbackEvent

event = CallbackEvent(
    event_type="card.action.trigger",
    user_id="ou_test_user_123",
    action={"action_id": "approve", "value": {...}},
    card_id="om_abc123...",
    app_id="cli_a1b2c3d4e5f6g7h8"
)
```

---

## 错误处理

### 异常类型

```python
from lark_service.core.exceptions import (
    InvalidParameterError,  # 参数无效
    RetryableError,         # 可重试错误
    ValidationError,        # 数据验证失败
    RequestTimeoutError     # 请求超时
)
```

### 错误处理示例

```python
from lark_service.core.exceptions import InvalidParameterError, RetryableError

try:
    response = client.send_text_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id="ou_test_user_123",
        content="Hello"
    )
except InvalidParameterError as e:
    # 参数错误,不应重试
    logger.error(f"参数错误: {e}")

except RetryableError as e:
    # 可重试错误,已自动重试失败
    logger.warning(f"发送失败 (已重试): {e}")

except Exception as e:
    # 其他未知错误
    logger.exception(f"未知错误: {e}")
```

---

## 最佳实践

### 1. 使用上下文管理器

```python
from lark_service import LarkServiceClient

with LarkServiceClient(config_path="config.yaml") as client:
    # 自动管理资源
    response = client.messaging.send_text_message(...)
```

### 2. 批量发送优化

```python
# 推荐: 使用批量发送 API
response = client.send_batch_messages(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_ids=user_ids,
    msg_type="text",
    content={"text": "通知"}
)

# 不推荐: 循环单独发送
for user_id in user_ids:
    client.send_text_message(...)  # 性能差
```

### 3. 错误处理策略

```python
# 批量发送时处理部分失败
response = client.send_batch_messages(
    receiver_ids=user_ids,
    msg_type="text",
    content={"text": "通知"},
    continue_on_error=True  # 遇到错误继续发送
)

# 记录失败的接收者
failed_users = [
    result.receiver_id
    for result in response.results
    if result.status == "failed"
]

if failed_users:
    logger.warning(f"发送失败的用户: {failed_users}")
```

### 4. 卡片交互处理

```python
# 注册多个处理器
handler.register_handler("approve", handle_approve)
handler.register_handler("reject", handle_reject)
handler.register_handler("submit", handle_submit)

# 使用装饰器模式 (如果支持)
@handler.action("approve")
def handle_approve(event: CallbackEvent):
    # 处理逻辑
    return response
```

### 5. 媒体文件管理

```python
# 复用上传的媒体文件
image_key = uploader.upload_image(
    app_id="cli_a1b2c3d4e5f6g7h8",
    image_path="/path/to/logo.png"
)

# 发送给多个用户 (无需重复上传)
for user_id in user_ids:
    client.send_image_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=user_id,
        image_key=image_key  # 复用 image_key
    )
```

### 6. 日志记录

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 所有 API 调用会自动记录日志
client.send_text_message(...)
# 日志输出: 2026-01-15 10:30:00 - lark_service.messaging.client - INFO - Sending text message to ou_test_user_123
```

### 7. 性能监控

```python
import time

start_time = time.time()

response = client.send_batch_messages(
    receiver_ids=user_ids,
    msg_type="text",
    content={"text": "通知"}
)

elapsed = time.time() - start_time
logger.info(f"批量发送 {response.total} 条消息耗时: {elapsed:.2f}s")
logger.info(f"成功率: {response.success / response.total * 100:.1f}%")
```

---

## 相关文档

- [Phase 3 完成报告](./phase3-completion-report.md)
- [使用示例](./examples-phase3.md)
- [错误处理指南](./error-handling-guide.md)
- [测试策略](./testing-strategy.md)
- [架构设计](./architecture.md)

---

**文档版本**: v1.0
**最后更新**: 2026-01-15
**维护者**: Lark Service Team
