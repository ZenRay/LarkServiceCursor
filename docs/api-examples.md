# API使用示例

本文档提供Lark Service API的使用示例代码。

## 快速开始

```python
from lark_service.core.credential_pool import CredentialPool
from lark_service.messaging.client import MessagingClient

# 1. 初始化凭据池
pool = CredentialPool()

# 2. 添加应用凭据
pool.add_application(
    app_id="cli_xxx",
    app_secret="your_secret"
)

# 3. 创建客户端
client = MessagingClient(pool, app_id="cli_xxx")

# 4. 发送消息
client.send_text(
    receive_id="ou_xxx",
    content="Hello from Lark Service!"
)
```

## 消息发送示例

### 发送文本消息

```python
from lark_service.messaging import MessagingClient

client = MessagingClient(pool, "cli_xxx")

# 发送给用户
client.send_text(
    receive_id="ou_123",
    receive_id_type="open_id",
    content="这是一条文本消息"
)

# 发送给群组
client.send_text(
    receive_id="oc_456",
    receive_id_type="chat_id",
    content="群组消息"
)
```

### 发送富文本消息

```python
client.send_post(
    receive_id="ou_123",
    content={
        "zh_cn": {
            "title": "标题",
            "content": [
                [{"tag": "text", "text": "正文内容"}]
            ]
        }
    }
)
```

### 发送卡片消息

```python
from lark_service.cardkit import CardBuilder

card = CardBuilder()\\
    .add_header("通知标题", "blue")\\
    .add_text("这是通知内容")\\
    .add_button("查看详情", "https://example.com")\\
    .build()

client.send_interactive(
    receive_id="ou_123",
    card=card
)
```

## 通讯录操作示例

### 获取用户信息

```python
from lark_service.contact import ContactClient

client = ContactClient(pool, "cli_xxx")

# 获取单个用户
user = client.get_user(user_id="ou_123")
print(f"用户名: {user.name}")
print(f"邮箱: {user.email}")

# 批量获取
users = client.batch_get_users(["ou_123", "ou_456"])
```

### 查询部门信息

```python
# 获取部门信息
dept = client.get_department(dept_id="od_123")

# 获取部门下的用户
users = client.get_department_users(dept_id="od_123")
```

## 云文档操作示例

### 操作电子表格

```python
from lark_service.clouddoc.sheet import SheetClient

client = SheetClient(pool, "cli_xxx")

# 读取数据
data = client.read_range(
    spreadsheet_token="shtxxx",
    range_="Sheet1!A1:C10"
)

# 写入数据
client.write_range(
    spreadsheet_token="shtxxx",
    range_="Sheet1!A1",
    values=[[1, 2, 3], [4, 5, 6]]
)
```

### 操作多维表格

```python
from lark_service.clouddoc.bitable import BitableClient

client = BitableClient(pool, "cli_xxx")

# 创建记录
record = client.create_record(
    app_token="bascxxx",
    table_id="tblxxx",
    fields={"字段1": "值1", "字段2": "值2"}
)

# 查询记录
records = client.list_records(
    app_token="bascxxx",
    table_id="tblxxx",
    filter="CurrentValue.[字段1] = '值1'"
)
```

## 完整应用示例

### 消息通知机器人

```python
import schedule
import time

def send_daily_report():
    """发送每日报告"""
    pool = CredentialPool()
    pool.add_application("cli_xxx", "secret")

    client = MessagingClient(pool, "cli_xxx")

    # 构建报告内容
    report = "今日数据汇总:\\n"
    report += f"- 新用户: 100\\n"
    report += f"- 活跃用户: 500\\n"

    client.send_text(
        receive_id="oc_group_id",
        content=report
    )

# 每天9点发送
schedule.every().day.at("09:00").do(send_daily_report)

while True:
    schedule.run_pending()
    time.sleep(60)
```

更多示例参见: https://github.com/your-org/lark-service/tree/main/examples
