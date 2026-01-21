lark\_service.cardkit package
=============================

卡片服务 (CardKit) 提供了构建飞书交互式卡片的能力,支持预定义模板和自定义构建。

Submodules
----------

lark\_service.cardkit.builder module
------------------------------------

.. automodule:: lark_service.cardkit.builder
   :members:
   :undoc-members:
   :show-inheritance:

lark\_service.cardkit.callback\_handler module
----------------------------------------------

.. automodule:: lark_service.cardkit.callback_handler
   :members:
   :undoc-members:
   :show-inheritance:

lark\_service.cardkit.models module
-----------------------------------

.. automodule:: lark_service.cardkit.models
   :members:
   :undoc-members:
   :show-inheritance:

lark\_service.cardkit.updater module
------------------------------------

.. automodule:: lark_service.cardkit.updater
   :members:
   :undoc-members:
   :show-inheritance:

Module contents
---------------

.. automodule:: lark_service.cardkit
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

快速开始
~~~~~~~~

.. code-block:: python

    from lark_service.cardkit.builder import CardBuilder
    from lark_service.messaging.client import MessagingClient

    # 创建卡片构建器
    builder = CardBuilder()

    # 构建通知卡片
    card = builder.build_notification_card(
        title="系统通知",
        content="您有一条新消息待查看",
        level="info"
    )

    # 发送卡片
    messaging_client = MessagingClient(pool=credential_pool)
    response = messaging_client.send_card_message(
        app_id="cli_xxx",
        receiver_id="ou_xxx",
        card=card
    )

通知卡片
~~~~~~~~

四种通知级别:

.. code-block:: python

    # 信息通知 (蓝色)
    card = builder.build_notification_card(
        title="构建成功",
        content="项目已成功构建",
        level="info"
    )

    # 成功通知 (绿色)
    card = builder.build_notification_card(
        title="部署完成",
        content="✅ 应用已部署到生产环境",
        level="success"
    )

    # 警告通知 (橙色)
    card = builder.build_notification_card(
        title="资源告警",
        content="⚠️ CPU 使用率超过 80%",
        level="warning"
    )

    # 错误通知 (红色)
    card = builder.build_notification_card(
        title="部署失败",
        content="❌ 部署过程中发生错误",
        level="error"
    )

审批卡片
~~~~~~~~

.. code-block:: python

    # 请假申请审批
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

    # 发送给审批人
    response = messaging_client.send_card_message(
        app_id="cli_xxx",
        receiver_id="ou_manager_xxx",
        card=card
    )

表单卡片
~~~~~~~~

.. code-block:: python

    # 反馈表单
    card = builder.build_form_card(
        title="用户反馈",
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
                "placeholder": "请输入您的反馈"
            }
        ],
        submit_action_id="submit_feedback",
        cancel_action_id="cancel_feedback"
    )

自定义卡片
~~~~~~~~~~

.. code-block:: python

    # 使用 build_card 构建自定义卡片
    card = builder.build_card(
        header={
            "title": {"tag": "plain_text", "content": "项目状态"},
            "template": "blue"
        },
        elements=[
            # Markdown 文本
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**进度**: 85%\n**预计完成**: 2026-02-15"
                }
            },
            # 分割线
            {"tag": "hr"},
            # 按钮组
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看详情"},
                        "type": "primary",
                        "action_id": "view_details"
                    }
                ]
            }
        ]
    )

卡片回调处理
~~~~~~~~~~~~

.. code-block:: python

    from lark_service.cardkit.callback_handler import CallbackHandler

    callback_handler = CallbackHandler(
        verification_token="your_verification_token",
        encrypt_key="your_encrypt_key"
    )

    def handle_approve(event: dict) -> dict:
        """处理审批通过"""
        # 执行业务逻辑
        approve_request(event)

        # 返回更新后的卡片
        return {
            "toast": {"type": "success", "content": "已批准"},
            "card": builder.build_notification_card(
                title="审批结果",
                content="✅ 请假申请已批准",
                level="success"
            )
        }

    # 注册处理器
    callback_handler.register_handler("approve_leave", handle_approve)

卡片更新
~~~~~~~~

.. code-block:: python

    from lark_service.cardkit.updater import CardUpdater

    updater = CardUpdater(credential_pool=credential_pool)

    # 更新已发送的卡片
    new_card = builder.build_notification_card(
        title="状态更新",
        content="任务已完成",
        level="success"
    )

    updater.update_card_content(
        app_id="cli_xxx",
        message_id="om_xxx",
        card_content=new_card
    )

See Also
--------

- :doc:`../usage/card` - 卡片服务完整使用指南
- :doc:`lark_service.messaging` - 消息发送服务
- `飞书开放平台 - 消息卡片 <https://open.feishu.cn/document/ukTMukTMukTM/uczM3QjL3MzN04yNzcDN>`_
