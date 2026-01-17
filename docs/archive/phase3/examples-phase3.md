# Phase 3 使用示例 - Messaging & CardKit

**版本**: v0.2.0
**更新日期**: 2026-01-15
**适用范围**: Phase 3 消息与交互式卡片功能

本文档提供 Phase 3 功能的完整使用示例,涵盖常见场景和最佳实践。

---

## 目录

- [快速开始](#快速开始)
- [消息发送场景](#消息发送场景)
- [卡片交互场景](#卡片交互场景)
- [批量操作场景](#批量操作场景)
- [完整应用示例](#完整应用示例)
- [常见问题](#常见问题)

---

## 快速开始

### 基础配置

```python
from lark_service import LarkServiceClient

# 方式 1: 使用配置文件
client = LarkServiceClient(config_path="config.yaml")

# 方式 2: 直接传入配置
client = LarkServiceClient(
    app_id="cli_a1b2c3d4e5f6g7h8",
    app_secret="your_app_secret",
    verification_token="your_verification_token",
    encrypt_key="your_encrypt_key"
)

# 使用客户端
messaging = client.messaging
cardkit = client.cardkit
```

### 配置文件示例 (config.yaml)

```yaml
app_id: cli_a1b2c3d4e5f6g7h8
app_secret: your_app_secret
verification_token: your_verification_token
encrypt_key: your_encrypt_key

# 可选配置
database:
  url: postgresql://user:pass@localhost/lark_service

retry:
  max_attempts: 3
  initial_delay: 1.0
  max_delay: 10.0
```

---

## 消息发送场景

### 场景 1: 工单通知

向用户发送工单处理通知。

```python
from lark_service import LarkServiceClient

client = LarkServiceClient(config_path="config.yaml")

def notify_ticket_assigned(user_id: str, ticket_id: str, ticket_title: str):
    """通知用户有新工单分配"""

    # 发送文本消息
    response = client.messaging.send_text_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=user_id,
        content=f"您有新的工单待处理: {ticket_title} (#{ticket_id})"
    )

    print(f"消息已发送: {response['message_id']}")
    return response

# 使用示例
notify_ticket_assigned(
    user_id="ou_user_123",
    ticket_id="TK-2024-001",
    ticket_title="服务器性能问题"
)
```

### 场景 2: 审批通知 (富文本)

发送格式化的审批通知,包含链接和强调文本。

```python
def notify_approval_result(user_id: str, approval_type: str, approved: bool, approver: str):
    """发送审批结果通知"""

    status = "批准" if approved else "拒绝"
    status_style = ["bold", "underline"]

    content = {
        "zh_cn": {
            "title": f"{approval_type}审批结果",
            "content": [
                [
                    {"tag": "text", "text": "您的"},
                    {"tag": "text", "text": approval_type, "style": ["bold"]},
                    {"tag": "text", "text": "申请已被"},
                    {"tag": "text", "text": status, "style": status_style},
                ],
                [
                    {"tag": "text", "text": f"审批人: {approver}"}
                ],
                [
                    {"tag": "text", "text": "查看详情: "},
                    {
                        "tag": "a",
                        "text": "审批系统",
                        "href": "https://approval.example.com"
                    }
                ]
            ]
        }
    }

    response = client.messaging.send_rich_text_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=user_id,
        content=content
    )

    return response

# 使用示例
notify_approval_result(
    user_id="ou_user_123",
    approval_type="请假",
    approved=True,
    approver="李经理"
)
```

### 场景 3: 发送报表图片

生成报表图片并发送给用户。

```python
import matplotlib.pyplot as plt
import tempfile
from pathlib import Path

def send_sales_report(user_id: str, sales_data: dict):
    """生成销售报表图片并发送"""

    # 生成报表图片
    plt.figure(figsize=(10, 6))
    plt.bar(sales_data.keys(), sales_data.values())
    plt.title("本月销售报表")
    plt.xlabel("日期")
    plt.ylabel("销售额 (元)")

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        plt.savefig(tmp.name)
        image_path = tmp.name

    try:
        # 发送图片消息
        response = client.messaging.send_image_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id=user_id,
            image_path=image_path
        )

        print(f"报表已发送: {response['message_id']}")
        return response

    finally:
        # 清理临时文件
        Path(image_path).unlink(missing_ok=True)

# 使用示例
sales_data = {
    "01-10": 12500,
    "01-11": 15800,
    "01-12": 13200,
    "01-13": 18900,
    "01-14": 16700
}

send_sales_report(
    user_id="ou_manager_456",
    sales_data=sales_data
)
```

### 场景 4: 发送文档附件

向用户发送合同或报告文档。

```python
def send_contract_document(user_id: str, contract_path: str, contract_name: str):
    """发送合同文档"""

    # 先发送文本说明
    client.messaging.send_text_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=user_id,
        content=f"您的{contract_name}已生成,请查收附件"
    )

    # 发送文件
    response = client.messaging.send_file_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=user_id,
        file_path=contract_path
    )

    return response

# 使用示例
send_contract_document(
    user_id="ou_user_789",
    contract_path="/data/contracts/2024/contract_001.pdf",
    contract_name="劳动合同"
)
```

### 场景 5: 消息撤回与编辑

发送消息后进行撤回或编辑。

```python
import time

def send_and_correct_message(user_id: str):
    """发送消息后发现错误,进行更正"""

    # 发送消息
    response = client.messaging.send_text_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=user_id,
        content="会议时间: 下午 3:00"  # 错误的时间
    )

    message_id = response['message_id']

    # 发现错误,等待 2 秒后编辑
    time.sleep(2)

    # 编辑消息
    client.messaging.lifecycle.edit_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        message_id=message_id,
        content="会议时间: 下午 4:00 (已更正)"
    )

    print("消息已更正")

# 或者直接撤回
def send_and_recall_message(user_id: str):
    """发送消息后撤回"""

    response = client.messaging.send_text_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=user_id,
        content="测试消息"
    )

    message_id = response['message_id']

    # 撤回消息
    client.messaging.lifecycle.recall_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        message_id=message_id
    )

    print("消息已撤回")
```

---

## 卡片交互场景

### 场景 6: 请假审批卡片

创建请假审批卡片并处理审批操作。

```python
from lark_service.cardkit import CardBuilder, CallbackHandler, CardUpdater

# 1. 发送审批卡片
def send_leave_approval_card(manager_id: str, applicant: str, leave_info: dict):
    """发送请假审批卡片"""

    builder = CardBuilder()

    card = builder.build_approval_card(
        title="请假申请",
        applicant=applicant,
        fields={
            "类型": leave_info["type"],
            "天数": f"{leave_info['days']}天",
            "开始日期": leave_info["start_date"],
            "结束日期": leave_info["end_date"],
            "理由": leave_info["reason"]
        },
        approve_action_id="approve_leave",
        reject_action_id="reject_leave",
        note="请在 24 小时内审批"
    )

    response = client.messaging.send_card_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=manager_id,
        card_content=card
    )

    return response['message_id']

# 2. 设置回调处理器
handler = CallbackHandler(
    verification_token="your_verification_token",
    encrypt_key="your_encrypt_key"
)

def handle_approve_leave(event):
    """处理批准操作"""
    user_id = event.user_id
    action_value = event.action.get("value", {})

    # 执行审批逻辑
    print(f"用户 {user_id} 批准了请假申请")
    # approve_leave_in_system(action_value)

    # 构建更新后的卡片
    builder = CardBuilder()
    updater = CardUpdater(
        credential_pool=client._credential_pool,
        retry_strategy=client._retry_strategy
    )

    new_card = builder.build_notification_card(
        title="请假申请 - 已批准",
        content="您的请假申请已通过审批",
        level="success"
    )

    return updater.build_update_response(
        card_content=new_card,
        toast_message="审批成功!"
    )

def handle_reject_leave(event):
    """处理拒绝操作"""
    user_id = event.user_id

    print(f"用户 {user_id} 拒绝了请假申请")

    builder = CardBuilder()
    updater = CardUpdater(
        credential_pool=client._credential_pool,
        retry_strategy=client._retry_strategy
    )

    new_card = builder.build_notification_card(
        title="请假申请 - 已拒绝",
        content="您的请假申请未通过审批",
        level="error"
    )

    return updater.build_update_response(
        card_content=new_card,
        toast_message="已拒绝"
    )

# 注册处理器
handler.register_handler("approve_leave", handle_approve_leave)
handler.register_handler("reject_leave", handle_reject_leave)

# 3. Flask 路由处理回调
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/lark/callback', methods=['POST'])
def lark_callback():
    request_data = request.json
    response = handler.handle_callback(request_data)
    return jsonify(response)

# 使用示例
leave_info = {
    "type": "年假",
    "days": 3,
    "start_date": "2026-01-20",
    "end_date": "2026-01-22",
    "reason": "家庭旅行"
}

message_id = send_leave_approval_card(
    manager_id="ou_manager_456",
    applicant="张三",
    leave_info=leave_info
)
```

### 场景 7: 系统告警通知卡片

发送系统告警通知卡片。

```python
def send_alert_notification(admin_ids: list[str], alert_info: dict):
    """发送系统告警通知"""

    builder = CardBuilder()

    # 根据严重程度选择级别
    level_map = {
        "critical": "error",
        "warning": "warning",
        "info": "info"
    }

    card = builder.build_notification_card(
        title=f"系统告警 - {alert_info['service']}",
        content=f"{alert_info['message']}\n\n"
                f"时间: {alert_info['timestamp']}\n"
                f"影响范围: {alert_info['scope']}",
        level=level_map.get(alert_info['severity'], 'warning'),
        action_text="查看详情",
        action_url=alert_info['detail_url']
    )

    # 发送给所有管理员
    for admin_id in admin_ids:
        client.messaging.send_card_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id=admin_id,
            card_content=card
        )

# 使用示例
alert_info = {
    "service": "API Gateway",
    "message": "服务响应时间超过阈值",
    "timestamp": "2026-01-15 14:30:00",
    "scope": "所有用户",
    "severity": "warning",
    "detail_url": "https://monitor.example.com/alerts/12345"
}

send_alert_notification(
    admin_ids=["ou_admin1", "ou_admin2"],
    alert_info=alert_info
)
```

### 场景 8: 反馈表单卡片

创建用户反馈表单卡片。

```python
def send_feedback_form(user_id: str):
    """发送反馈表单卡片"""

    builder = CardBuilder()

    card = builder.build_form_card(
        title="用户反馈",
        fields=[
            {
                "label": "姓名",
                "name": "name",
                "type": "input",
                "placeholder": "请输入您的姓名",
                "required": True
            },
            {
                "label": "反馈类型",
                "name": "type",
                "type": "select",
                "placeholder": "请选择反馈类型",
                "options": ["功能建议", "Bug反馈", "使用问题", "其他"],
                "required": True
            },
            {
                "label": "详细描述",
                "name": "description",
                "type": "textarea",
                "placeholder": "请详细描述您的反馈内容",
                "required": True
            },
            {
                "label": "联系方式",
                "name": "contact",
                "type": "input",
                "placeholder": "邮箱或电话 (可选)",
                "required": False
            }
        ],
        submit_action_id="submit_feedback",
        cancel_action_id="cancel_feedback"
    )

    response = client.messaging.send_card_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=user_id,
        card_content=card
    )

    return response

# 处理表单提交
def handle_submit_feedback(event):
    """处理反馈表单提交"""
    form_data = event.action.get("value", {})

    # 保存反馈到数据库
    save_feedback_to_database(form_data)

    # 构建成功提示卡片
    builder = CardBuilder()
    updater = CardUpdater(
        credential_pool=client._credential_pool,
        retry_strategy=client._retry_strategy
    )

    new_card = builder.build_notification_card(
        title="提交成功",
        content="感谢您的反馈!我们会尽快处理。",
        level="success"
    )

    return updater.build_update_response(
        card_content=new_card,
        toast_message="提交成功!"
    )

def handle_cancel_feedback(event):
    """处理取消操作"""
    builder = CardBuilder()
    updater = CardUpdater(
        credential_pool=client._credential_pool,
        retry_strategy=client._retry_strategy
    )

    new_card = builder.build_notification_card(
        title="已取消",
        content="反馈已取消",
        level="info"
    )

    return updater.build_update_response(
        card_content=new_card
    )

# 注册处理器
handler.register_handler("submit_feedback", handle_submit_feedback)
handler.register_handler("cancel_feedback", handle_cancel_feedback)

# 发送表单
send_feedback_form(user_id="ou_user_123")
```

---

## 批量操作场景

### 场景 9: 批量通知

向多个用户发送相同的通知消息。

```python
def notify_system_maintenance(user_ids: list[str], maintenance_info: dict):
    """批量通知系统维护"""

    content = {
        "text": f"系统维护通知\n\n"
                f"时间: {maintenance_info['start_time']} - {maintenance_info['end_time']}\n"
                f"影响: {maintenance_info['impact']}\n"
                f"请提前保存工作内容。"
    }

    response = client.messaging.send_batch_messages(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_ids=user_ids,
        msg_type="text",
        content=content,
        continue_on_error=True  # 遇到错误继续发送
    )

    # 统计发送结果
    print(f"总计: {response.total}")
    print(f"成功: {response.success}")
    print(f"失败: {response.failed}")

    # 记录失败的用户
    if response.failed > 0:
        failed_users = [
            result.receiver_id
            for result in response.results
            if result.status == "failed"
        ]
        print(f"发送失败的用户: {failed_users}")

    return response

# 使用示例
maintenance_info = {
    "start_time": "2026-01-15 22:00",
    "end_time": "2026-01-15 23:00",
    "impact": "服务暂时不可用"
}

# 从数据库获取所有活跃用户
user_ids = get_active_user_ids()  # 假设返回 1000 个用户

# 批量发送 (自动分批,每批最多 200 个)
for i in range(0, len(user_ids), 200):
    batch = user_ids[i:i+200]
    notify_system_maintenance(batch, maintenance_info)
```

### 场景 10: 批量发送个性化消息

向不同用户发送个性化的消息内容。

```python
def send_personalized_reports(user_reports: dict[str, dict]):
    """批量发送个性化报表

    Args:
        user_reports: {user_id: report_data}
    """

    results = []

    for user_id, report in user_reports.items():
        try:
            content = {
                "zh_cn": {
                    "title": "个人月度报表",
                    "content": [
                        [
                            {"tag": "text", "text": f"姓名: {report['name']}\n"}
                        ],
                        [
                            {"tag": "text", "text": f"本月完成任务: "},
                            {"tag": "text", "text": str(report['tasks_completed']), "style": ["bold"]},
                            {"tag": "text", "text": " 个"}
                        ],
                        [
                            {"tag": "text", "text": f"工作时长: "},
                            {"tag": "text", "text": f"{report['work_hours']} 小时", "style": ["bold"]}
                        ],
                        [
                            {"tag": "text", "text": f"绩效评分: "},
                            {"tag": "text", "text": str(report['score']), "style": ["bold"]}
                        ]
                    ]
                }
            }

            response = client.messaging.send_rich_text_message(
                app_id="cli_a1b2c3d4e5f6g7h8",
                receiver_id=user_id,
                content=content
            )

            results.append({
                "user_id": user_id,
                "status": "success",
                "message_id": response['message_id']
            })

        except Exception as e:
            results.append({
                "user_id": user_id,
                "status": "failed",
                "error": str(e)
            })

    return results

# 使用示例
user_reports = {
    "ou_user1": {
        "name": "张三",
        "tasks_completed": 25,
        "work_hours": 168,
        "score": 95
    },
    "ou_user2": {
        "name": "李四",
        "tasks_completed": 30,
        "work_hours": 172,
        "score": 98
    }
}

results = send_personalized_reports(user_reports)
```

---

## 完整应用示例

### 场景 11: 工单系统集成

完整的工单系统飞书集成示例。

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class TicketStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

@dataclass
class Ticket:
    id: str
    title: str
    description: str
    assignee_id: str
    reporter_id: str
    status: TicketStatus
    created_at: datetime

class TicketNotificationService:
    """工单通知服务"""

    def __init__(self, lark_client):
        self.client = lark_client
        self.app_id = "cli_a1b2c3d4e5f6g7h8"

    def notify_ticket_created(self, ticket: Ticket):
        """通知工单创建"""

        # 通知处理人
        builder = CardBuilder()
        card = builder.build_notification_card(
            title="新工单分配",
            content=f"工单 #{ticket.id}: {ticket.title}\n\n"
                   f"描述: {ticket.description}\n"
                   f"创建时间: {ticket.created_at.strftime('%Y-%m-%d %H:%M')}",
            level="info",
            action_text="查看工单",
            action_url=f"https://tickets.example.com/{ticket.id}"
        )

        self.client.messaging.send_card_message(
            app_id=self.app_id,
            receiver_id=ticket.assignee_id,
            card_content=card
        )

        # 通知报告人
        self.client.messaging.send_text_message(
            app_id=self.app_id,
            receiver_id=ticket.reporter_id,
            content=f"您的工单 #{ticket.id} 已创建,处理人员会尽快处理"
        )

    def notify_ticket_status_changed(self, ticket: Ticket, old_status: TicketStatus):
        """通知工单状态变更"""

        status_messages = {
            TicketStatus.IN_PROGRESS: "正在处理",
            TicketStatus.RESOLVED: "已解决",
            TicketStatus.CLOSED: "已关闭"
        }

        message = status_messages.get(ticket.status, str(ticket.status.value))

        self.client.messaging.send_text_message(
            app_id=self.app_id,
            receiver_id=ticket.reporter_id,
            content=f"工单 #{ticket.id} 状态更新: {message}"
        )

    def notify_ticket_commented(self, ticket: Ticket, commenter_name: str, comment: str):
        """通知工单有新评论"""

        # 通知报告人和处理人
        recipients = [ticket.reporter_id, ticket.assignee_id]

        content = {
            "zh_cn": {
                "title": f"工单 #{ticket.id} 新评论",
                "content": [
                    [
                        {"tag": "text", "text": f"{commenter_name} 添加了评论:\n"}
                    ],
                    [
                        {"tag": "text", "text": comment}
                    ]
                ]
            }
        }

        for recipient_id in recipients:
            self.client.messaging.send_rich_text_message(
                app_id=self.app_id,
                receiver_id=recipient_id,
                content=content
            )

# 使用示例
ticket_service = TicketNotificationService(client)

# 创建工单
ticket = Ticket(
    id="TK-2024-001",
    title="服务器性能问题",
    description="API 响应时间过长",
    assignee_id="ou_engineer_123",
    reporter_id="ou_user_456",
    status=TicketStatus.OPEN,
    created_at=datetime.now()
)

ticket_service.notify_ticket_created(ticket)

# 更新状态
ticket.status = TicketStatus.IN_PROGRESS
ticket_service.notify_ticket_status_changed(ticket, TicketStatus.OPEN)

# 添加评论
ticket_service.notify_ticket_commented(
    ticket=ticket,
    commenter_name="工程师李四",
    comment="已定位问题,正在修复中"
)
```

### 场景 12: 审批流程系统

完整的审批流程飞书集成。

```python
from enum import Enum
from typing import List, Optional

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

@dataclass
class ApprovalRequest:
    id: str
    type: str  # 请假、报销、采购等
    applicant_id: str
    applicant_name: str
    approvers: List[str]  # 审批人列表
    current_approver_index: int
    status: ApprovalStatus
    data: dict
    created_at: datetime

class ApprovalService:
    """审批服务"""

    def __init__(self, lark_client):
        self.client = lark_client
        self.app_id = "cli_a1b2c3d4e5f6g7h8"
        self.handler = CallbackHandler(
            verification_token="your_token",
            encrypt_key="your_key"
        )
        self._register_handlers()

    def _register_handlers(self):
        """注册回调处理器"""
        self.handler.register_handler("approve", self._handle_approve)
        self.handler.register_handler("reject", self._handle_reject)

    def submit_approval(self, request: ApprovalRequest) -> str:
        """提交审批"""

        # 发送审批卡片给第一个审批人
        current_approver = request.approvers[request.current_approver_index]

        builder = CardBuilder()
        card = builder.build_approval_card(
            title=f"{request.type}审批",
            applicant=request.applicant_name,
            fields=request.data,
            approve_action_id=f"approve_{request.id}",
            reject_action_id=f"reject_{request.id}",
            note=f"审批流程: {request.current_approver_index + 1}/{len(request.approvers)}"
        )

        response = self.client.messaging.send_card_message(
            app_id=self.app_id,
            receiver_id=current_approver,
            card_content=card
        )

        # 通知申请人
        self.client.messaging.send_text_message(
            app_id=self.app_id,
            receiver_id=request.applicant_id,
            content=f"您的{request.type}申请已提交,等待审批"
        )

        return response['message_id']

    def _handle_approve(self, event):
        """处理批准操作"""
        request_id = event.action.get("action_id", "").replace("approve_", "")

        # 从数据库加载审批请求
        request = load_approval_request(request_id)

        # 更新审批进度
        request.current_approver_index += 1

        if request.current_approver_index >= len(request.approvers):
            # 所有审批人都已批准
            request.status = ApprovalStatus.APPROVED
            self._notify_approval_completed(request, approved=True)

            # 返回成功卡片
            builder = CardBuilder()
            updater = CardUpdater(
                credential_pool=self.client._credential_pool,
                retry_strategy=self.client._retry_strategy
            )

            card = builder.build_notification_card(
                title=f"{request.type}审批 - 已批准",
                content="审批已完成",
                level="success"
            )

            return updater.build_update_response(
                card_content=card,
                toast_message="审批成功!"
            )
        else:
            # 发送给下一个审批人
            save_approval_request(request)
            self.submit_approval(request)

            # 返回中间状态卡片
            builder = CardBuilder()
            updater = CardUpdater(
                credential_pool=self.client._credential_pool,
                retry_strategy=self.client._retry_strategy
            )

            card = builder.build_notification_card(
                title=f"{request.type}审批 - 已批准",
                content=f"已转交下一级审批人 ({request.current_approver_index + 1}/{len(request.approvers)})",
                level="info"
            )

            return updater.build_update_response(
                card_content=card,
                toast_message="已批准,转交下一级"
            )

    def _handle_reject(self, event):
        """处理拒绝操作"""
        request_id = event.action.get("action_id", "").replace("reject_", "")

        request = load_approval_request(request_id)
        request.status = ApprovalStatus.REJECTED
        save_approval_request(request)

        self._notify_approval_completed(request, approved=False)

        # 返回拒绝卡片
        builder = CardBuilder()
        updater = CardUpdater(
            credential_pool=self.client._credential_pool,
            retry_strategy=self.client._retry_strategy
        )

        card = builder.build_notification_card(
            title=f"{request.type}审批 - 已拒绝",
            content="审批未通过",
            level="error"
        )

        return updater.build_update_response(
            card_content=card,
            toast_message="已拒绝"
        )

    def _notify_approval_completed(self, request: ApprovalRequest, approved: bool):
        """通知审批完成"""
        status = "已批准" if approved else "已拒绝"
        level = "success" if approved else "error"

        builder = CardBuilder()
        card = builder.build_notification_card(
            title=f"{request.type}审批结果",
            content=f"您的{request.type}申请{status}",
            level=level
        )

        self.client.messaging.send_card_message(
            app_id=self.app_id,
            receiver_id=request.applicant_id,
            card_content=card
        )

# 使用示例
approval_service = ApprovalService(client)

# 提交请假申请
leave_request = ApprovalRequest(
    id="APV-2024-001",
    type="请假",
    applicant_id="ou_user_123",
    applicant_name="张三",
    approvers=["ou_manager1", "ou_manager2", "ou_hr"],  # 三级审批
    current_approver_index=0,
    status=ApprovalStatus.PENDING,
    data={
        "类型": "年假",
        "天数": "3天",
        "开始日期": "2026-01-20",
        "结束日期": "2026-01-22",
        "理由": "家庭旅行"
    },
    created_at=datetime.now()
)

message_id = approval_service.submit_approval(leave_request)
```

---

## 常见问题

### Q1: 如何处理消息发送失败?

```python
from lark_service.core.exceptions import RetryableError, InvalidParameterError

try:
    response = client.messaging.send_text_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id="ou_user_123",
        content="Hello"
    )
except InvalidParameterError as e:
    # 参数错误,不应重试
    logger.error(f"参数错误: {e}")
    # 修正参数后重新发送

except RetryableError as e:
    # 可重试错误,已自动重试失败
    logger.warning(f"发送失败 (已重试): {e}")
    # 可以选择稍后重试或记录到失败队列
```

### Q2: 如何复用上传的媒体文件?

```python
# 上传一次
uploader = client.messaging.media_uploader
image_key = uploader.upload_image(
    app_id="cli_a1b2c3d4e5f6g7h8",
    image_path="/path/to/logo.png"
)

# 保存 image_key 到数据库或缓存
cache.set("company_logo", image_key, ttl=86400)

# 复用 image_key 发送给多个用户
for user_id in user_ids:
    client.messaging.send_image_message(
        app_id="cli_a1b2c3d4e5f6g7h8",
        receiver_id=user_id,
        image_key=image_key  # 复用
    )
```

### Q3: 如何实现消息模板?

```python
class MessageTemplates:
    """消息模板"""

    @staticmethod
    def welcome_message(user_name: str) -> dict:
        """欢迎消息模板"""
        return {
            "zh_cn": {
                "title": "欢迎加入",
                "content": [
                    [
                        {"tag": "text", "text": f"你好 {user_name},"},
                        {"tag": "text", "text": "欢迎加入我们的团队!", "style": ["bold"]}
                    ],
                    [
                        {"tag": "text", "text": "请查看 "},
                        {"tag": "a", "text": "新人指南", "href": "https://guide.example.com"}
                    ]
                ]
            }
        }

    @staticmethod
    def task_reminder(task_title: str, due_date: str) -> str:
        """任务提醒模板"""
        return f"任务提醒: {task_title}\n截止日期: {due_date}\n请及时完成"

# 使用模板
client.messaging.send_rich_text_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_new_user",
    content=MessageTemplates.welcome_message("张三")
)
```

### Q4: 如何实现消息队列异步发送?

```python
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379/0')

@app.task
def send_message_async(app_id: str, receiver_id: str, content: str):
    """异步发送消息"""
    client = LarkServiceClient(config_path="config.yaml")

    try:
        response = client.messaging.send_text_message(
            app_id=app_id,
            receiver_id=receiver_id,
            content=content
        )
        return {"status": "success", "message_id": response['message_id']}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# 使用异步任务
send_message_async.delay(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_user_123",
    content="Hello"
)
```

### Q5: 如何实现批量发送的进度追踪?

```python
from tqdm import tqdm

def send_with_progress(user_ids: list[str], message: str):
    """带进度条的批量发送"""

    results = []

    # 使用进度条
    with tqdm(total=len(user_ids), desc="发送消息") as pbar:
        # 分批发送
        batch_size = 200
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i+batch_size]

            response = client.messaging.send_batch_messages(
                app_id="cli_a1b2c3d4e5f6g7h8",
                receiver_ids=batch,
                msg_type="text",
                content={"text": message}
            )

            results.append(response)
            pbar.update(len(batch))

    # 统计总结果
    total_success = sum(r.success for r in results)
    total_failed = sum(r.failed for r in results)

    print(f"\n发送完成: 成功 {total_success}, 失败 {total_failed}")

    return results

# 使用
user_ids = get_all_user_ids()  # 10000 个用户
send_with_progress(user_ids, "系统维护通知")
```

---

## 相关文档

- [API 参考文档](./api-reference-phase3.md)
- [Phase 3 完成报告](./phase3-completion-report.md)
- [错误处理指南](./error-handling-guide.md)
- [测试策略](./testing-strategy.md)

---

**文档版本**: v1.0
**最后更新**: 2026-01-15
**维护者**: Lark Service Team
