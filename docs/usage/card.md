# 卡片服务

飞书卡片是一种交互式消息形式,可以包含文本、图片、按钮等多种元素,支持用户交互和回调处理。

## 功能特点

- ✅ **预定义模板**: 审批卡片、通知卡片、表单卡片
- ✅ **灵活构建**: 自定义卡片元素和布局
- ✅ **交互回调**: 按钮点击、表单提交等事件处理
- ✅ **卡片更新**: 动态更新已发送的卡片内容
- ✅ **丰富元素**: 文本、图片、按钮、分割线、表单等

## 快速开始

### 基础使用

```python
from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager
from lark_service.core.storage.token_storage import TokenStorageService
from lark_service.messaging.client import MessagingClient
from lark_service.cardkit.builder import CardBuilder

# 初始化
config = Config.load_from_env()
app_manager = ApplicationManager(
    db_path=config.config_db_path,
    encryption_key=config.config_encryption_key
)
token_storage = TokenStorageService(db_path=config.config_db_path)
pool = CredentialPool(config=config, app_manager=app_manager, token_storage=token_storage)
messaging_client = MessagingClient(pool=pool)

# 创建卡片构建器
builder = CardBuilder()

# 构建简单通知卡片
card = builder.build_notification_card(
    title="系统通知",
    content="您有一条新消息待查看",
    level="info"
)

# 发送卡片
response = messaging_client.send_card_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    card=card
)
print(f"✅ 卡片发送成功! message_id: {response['message_id']}")
```

## 预定义卡片模板

### 1. 通知卡片 (Notification Card)

用于发送系统通知、提醒消息等。

```python
# 基础通知
card = builder.build_notification_card(
    title="构建成功",
    content="项目 **LarkService** 已成功构建并部署到生产环境",
    level="success"
)

# 带操作按钮的通知
card = builder.build_notification_card(
    title="代码审查请求",
    content="**@张三** 请求您审查 PR #123",
    level="info",
    action_text="立即查看",
    action_url="https://github.com/org/repo/pull/123"
)

# 警告通知
card = builder.build_notification_card(
    title="系统告警",
    content="服务器 CPU 使用率超过 80%",
    level="warning"
)

# 错误通知
card = builder.build_notification_card(
    title="部署失败",
    content="生产环境部署失败,错误代码: E1001",
    level="error",
    action_text="查看日志",
    action_id="view_logs"
)
```

**参数说明**:
- `level`: 通知级别
  - `"info"` - 蓝色,信息提示
  - `"success"` - 绿色,成功提示
  - `"warning"` - 橙色,警告提示
  - `"error"` - 红色,错误提示

### 2. 审批卡片 (Approval Card)

用于请假申请、报销审批等场景。

```python
# 请假申请卡片
card = builder.build_approval_card(
    title="请假申请",
    applicant="张三",
    fields={
        "类型": "年假",
        "开始日期": "2026-02-01",
        "结束日期": "2026-02-03",
        "天数": "3 天",
        "原因": "家庭旅行"
    },
    approve_action_id="approve_leave",
    reject_action_id="reject_leave",
    note="请审批"
)

# 报销申请卡片
card = builder.build_approval_card(
    title="差旅报销",
    applicant="李四",
    fields={
        "项目": "客户拜访",
        "日期": "2026-01-20",
        "交通费": "¥500",
        "住宿费": "¥800",
        "餐饮费": "¥300",
        "合计": "¥1,600"
    },
    approve_action_id="approve_expense",
    reject_action_id="reject_expense"
)

# 发送给审批人
response = messaging_client.send_card_message(
    app_id="cli_xxx",
    receiver_id="ou_manager_xxx",  # 审批人的 open_id
    card=card
)
```

### 3. 表单卡片 (Form Card)

用于收集用户输入信息。

```python
card = builder.build_form_card(
    title="问卷调查",
    fields=[
        {
            "label": "姓名",
            "name": "name",
            "type": "input",
            "placeholder": "请输入您的姓名"
        },
        {
            "label": "反馈内容",
            "name": "feedback",
            "type": "textarea",
            "placeholder": "请输入您的建议或意见"
        }
    ],
    submit_action_id="submit_survey",
    cancel_action_id="cancel_survey"
)
```

## 自定义卡片构建

### 使用 build_card 方法

```python
# 创建自定义卡片
card = builder.build_card(
    header={
        "title": {
            "tag": "plain_text",
            "content": "项目状态报告"
        },
        "template": "blue"  # 可选: blue, green, red, orange, purple, grey
    },
    elements=[
        # 文本元素
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**项目进度**: 85%\n**预计完成**: 2026-02-15"
            }
        },
        # 分割线
        {
            "tag": "hr"
        },
        # 图片元素
        {
            "tag": "img",
            "img_key": "img_v2_xxx",  # 图片的 key
            "alt": {
                "tag": "plain_text",
                "content": "进度图表"
            }
        },
        # 按钮组
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "查看详情"
                    },
                    "type": "primary",
                    "action_id": "view_details"
                },
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "导出报告"
                    },
                    "type": "default",
                    "action_id": "export_report"
                }
            ]
        }
    ]
)
```

### 常用卡片元素

#### 文本元素 (div)

```python
{
    "tag": "div",
    "text": {
        "tag": "plain_text",  # 或 "lark_md" (支持 Markdown)
        "content": "这是一段文本"
    }
}
```

#### Markdown 文本

```python
{
    "tag": "div",
    "text": {
        "tag": "lark_md",
        "content": """
**粗体文本**
*斜体文本*
[链接](https://example.com)
`代码`
        """
    }
}
```

#### 按钮 (button)

```python
{
    "tag": "action",
    "actions": [
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "按钮文本"},
            "type": "primary",  # primary, default, danger
            "value": {"key": "value"},  # 传递给回调的数据
            "action_id": "button_click",  # 唯一标识符
            "url": "https://example.com"  # 可选,打开 URL
        }
    ]
}
```

#### 分割线 (hr)

```python
{"tag": "hr"}
```

#### 图片 (img)

```python
{
    "tag": "img",
    "img_key": "img_v2_xxx",  # 上传图片后获得的 key
    "alt": {"tag": "plain_text", "content": "图片描述"},
    "mode": "fit_horizontal"  # 或 "crop_center"
}
```

#### 多列布局 (column_set)

```python
{
    "tag": "column_set",
    "flex_mode": "none",
    "background_style": "default",
    "columns": [
        {
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "plain_text", "content": "左列内容"}
                }
            ]
        },
        {
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "plain_text", "content": "右列内容"}
                }
            ]
        }
    ]
}
```

## 卡片交互回调

### 设置回调服务器

```python
from lark_service.cardkit.callback_handler import CardCallbackHandler

# 创建回调处理器
callback_handler = CardCallbackHandler()

# 注册按钮点击回调
@callback_handler.register("approve_leave")
async def handle_approve(action_data: dict) -> dict:
    """处理审批通过"""
    user_id = action_data["user_id"]
    message_id = action_data["message_id"]

    # 执行业务逻辑
    approve_leave_request(action_data["value"])

    # 返回更新后的卡片
    return {
        "toast": {"type": "success", "content": "已批准"},
        "card": builder.build_notification_card(
            title="审批结果",
            content="✅ 请假申请已批准",
            level="success"
        )
    }

@callback_handler.register("reject_leave")
async def handle_reject(action_data: dict) -> dict:
    """处理审批拒绝"""
    return {
        "toast": {"type": "info", "content": "已拒绝"},
        "card": builder.build_notification_card(
            title="审批结果",
            content="❌ 请假申请已拒绝",
            level="error"
        )
    }
```

### 卡片回调数据结构

回调会收到以下数据:

```python
{
    "user_id": "ou_xxx",           # 点击用户的 open_id
    "message_id": "om_xxx",        # 消息 ID
    "open_message_id": "om_xxx",   # 消息 ID
    "action": {
        "value": {"key": "value"}, # 按钮的 value 参数
        "tag": "button",           # 元素类型
        "action_id": "approve"     # action_id
    },
    "token": "xxx"                 # 验证 token
}
```

## 更新卡片

### 使用 CardUpdater

```python
from lark_service.cardkit.updater import CardUpdater

updater = CardUpdater(pool=pool)

# 更新已发送的卡片
new_card = builder.build_notification_card(
    title="状态更新",
    content="任务已完成",
    level="success"
)

updater.update_card(
    app_id="cli_xxx",
    message_id="om_xxx",  # 要更新的消息 ID
    card=new_card
)
```

### 在回调中更新卡片

```python
@callback_handler.register("refresh_status")
async def handle_refresh(action_data: dict) -> dict:
    """刷新卡片状态"""
    # 获取最新数据
    status = get_latest_status()

    # 构建新卡片
    new_card = builder.build_notification_card(
        title="实时状态",
        content=f"当前进度: {status['progress']}%",
        level="info"
    )

    # 返回新卡片 (会自动更新原卡片)
    return {"card": new_card}
```

## 高级用法

### 条件渲染

```python
def build_dynamic_card(user_role: str) -> dict:
    """根据用户角色构建不同的卡片"""
    elements = [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**欢迎使用系统**"}
        }
    ]

    # 管理员额外显示管理按钮
    if user_role == "admin":
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "管理面板"},
                    "type": "primary",
                    "action_id": "admin_panel"
                }
            ]
        })

    return builder.build_card(
        header={"title": {"tag": "plain_text", "content": "系统首页"}},
        elements=elements
    )
```

### 数据绑定

```python
def build_data_card(data: dict) -> dict:
    """从数据构建卡片"""
    elements = []

    for key, value in data.items():
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{key}**: {value}"
            }
        })

    return builder.build_card(
        header={"title": {"tag": "plain_text", "content": "数据展示"}},
        elements=elements
    )

# 使用示例
data = {
    "用户名": "张三",
    "部门": "技术部",
    "职位": "工程师",
    "入职时间": "2025-01-01"
}
card = build_data_card(data)
```

### 卡片链

发送一系列相关的卡片:

```python
# 步骤 1: 发送初始卡片
card1 = builder.build_notification_card(
    title="任务已创建",
    content="任务 #123 已创建,等待处理",
    level="info"
)
response1 = messaging_client.send_card_message(
    app_id="cli_xxx",
    receiver_id="ou_xxx",
    card=card1
)

# 步骤 2: 处理完成后更新
card2 = builder.build_notification_card(
    title="任务进行中",
    content="任务 #123 正在处理中...",
    level="info"
)
updater.update_card(
    app_id="cli_xxx",
    message_id=response1["message_id"],
    card=card2
)

# 步骤 3: 最终完成通知
card3 = builder.build_notification_card(
    title="任务已完成",
    content="✅ 任务 #123 已成功完成",
    level="success"
)
updater.update_card(
    app_id="cli_xxx",
    message_id=response1["message_id"],
    card=card3
)
```

## 最佳实践

### 1. 卡片设计原则

- **简洁明了**: 避免信息过载,突出重点
- **操作明确**: 按钮文字清晰,操作目的明确
- **视觉层次**: 使用标题、分割线组织信息
- **响应及时**: 交互后立即给予反馈

### 2. 错误处理

```python
from lark_service.core.exceptions import LarkAPIError

try:
    response = messaging_client.send_card_message(
        app_id="cli_xxx",
        receiver_id="ou_xxx",
        card=card
    )
except LarkAPIError as e:
    logger.error(f"发送卡片失败: {e}")
    # 发送降级通知(纯文本)
    messaging_client.send_text_message(
        app_id="cli_xxx",
        receiver_id="ou_xxx",
        content="系统通知: 您有一条新消息待查看"
    )
```

### 3. 回调安全验证

```python
from lark_service.cardkit.callback_handler import verify_callback

@callback_handler.register("sensitive_action")
async def handle_sensitive(action_data: dict) -> dict:
    """处理敏感操作"""
    # 验证回调来源
    if not verify_callback(action_data, app_secret):
        return {"toast": {"type": "error", "content": "验证失败"}}

    # 验证用户权限
    user_id = action_data["user_id"]
    if not has_permission(user_id, "sensitive_action"):
        return {"toast": {"type": "error", "content": "权限不足"}}

    # 执行操作
    perform_sensitive_action()
    return {"toast": {"type": "success", "content": "操作成功"}}
```

### 4. 性能优化

```python
# 批量发送卡片
async def send_cards_batch(receiver_ids: list[str], card: dict):
    """批量发送卡片"""
    tasks = [
        messaging_client.send_card_message(
            app_id="cli_xxx",
            receiver_id=receiver_id,
            card=card
        )
        for receiver_id in receiver_ids
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# 使用
receiver_ids = ["ou_1", "ou_2", "ou_3"]
card = builder.build_notification_card(title="群发通知", content="...")
await send_cards_batch(receiver_ids, card)
```

## 故障排查

### 卡片发送失败

1. **检查卡片 JSON 结构**:
   ```python
   import json
   print(json.dumps(card, indent=2, ensure_ascii=False))
   ```

2. **验证权限**:
   - 确保应用有 `im:message` 权限
   - 确保应用有 `im:message.group_msg` (群聊) 权限

3. **检查接收者 ID**:
   ```python
   # 验证 open_id 是否有效
   from lark_service.contact.client import ContactClient
   contact = ContactClient(pool=pool)
   user = contact.get_user(app_id="cli_xxx", user_id="ou_xxx")
   print(f"用户存在: {user.name}")
   ```

### 回调未触发

1. 检查回调 URL 配置
2. 验证 action_id 是否注册
3. 检查网络连通性
4. 查看日志输出

## 相关文档

- 📖 [消息服务](./messaging.md) - 消息发送
- 🔐 [用户授权](./auth.md) - OAuth 授权流程
- 🔍 [API 参考](../api/lark_service.cardkit.rst) - CardKit API 文档
- 📚 [飞书官方文档](https://open.feishu.cn/document/ukTMukTMukTM/uczM3QjL3MzN04yNzcDN) - 消息卡片
