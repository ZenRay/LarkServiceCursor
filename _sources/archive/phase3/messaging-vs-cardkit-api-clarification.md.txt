# 飞书消息 API vs 卡片 API 架构说明

**创建日期**: 2026-01-15
**目的**: 澄清飞书消息和卡片两个独立 API 的区别,指导 Phase 3 实施

---

## 🎯 核心区分

根据飞书官方文档,消息和卡片是**两个独立的 API 服务**:

| API | 官方文档 | 用途 | 依赖 Token |
|-----|---------|------|-----------|
| **消息 API (IM v1)** | https://open.feishu.cn/document/server-docs/im-v1/introduction | 发送各类消息到用户/群组 | `app_access_token` 或 `tenant_access_token` |
| **卡片 API (CardKit v1)** | https://open.feishu.cn/document/cardkit-v1/feishu-card-resource-overview | 构建卡片、处理交互回调 | `app_access_token` |

---

## 📦 消息 API (IM v1) 能力

### 支持的消息类型

1. **文本消息** (`text`)
   - API: `POST /im/v1/messages`
   - 参数: `msg_type: "text"`, `content: {"text": "消息内容"}`

2. **富文本消息** (`post`)
   - API: `POST /im/v1/messages`
   - 参数: `msg_type: "post"`, `content: {富文本结构}`

3. **图片消息** (`image`)
   - API: `POST /im/v1/messages`
   - 参数: `msg_type: "image"`, `content: {"image_key": "xxx"}`
   - 需要先调用媒体上传 API 获取 `image_key`

4. **文件消息** (`file`)
   - API: `POST /im/v1/messages`
   - 参数: `msg_type: "file"`, `content: {"file_key": "xxx"}`
   - 需要先调用媒体上传 API 获取 `file_key`

5. **交互式卡片消息** (`interactive`)
   - API: `POST /im/v1/messages`
   - 参数: `msg_type: "interactive"`, `content: {卡片 JSON}`
   - **注意**: 这里是通过**消息 API 发送卡片**,卡片内容由 CardKit 构建

### 消息 API 的其他能力

- 消息撤回: `DELETE /im/v1/messages/{message_id}`
- 消息编辑: `PATCH /im/v1/messages/{message_id}` (仅文本消息)
- 消息回复: `POST /im/v1/messages/{message_id}/reply`
- 批量发送: 循环调用 `POST /im/v1/messages`
- 消息已读状态: `GET /im/v1/messages/{message_id}/read_users`

---

## 🎴 卡片 API (CardKit v1) 能力

### 卡片构建

1. **卡片模板定义**
   - 使用 JSON 定义卡片结构
   - 支持组件: header, div, action, form, hr, image, markdown, note, 等

2. **卡片模板示例**
   ```json
   {
     "config": {
       "wide_screen_mode": true
     },
     "header": {
       "title": {
         "tag": "plain_text",
         "content": "审批通知"
       }
     },
     "elements": [
       {
         "tag": "div",
         "text": {
           "tag": "lark_md",
           "content": "**申请人**: 张三"
         }
       },
       {
         "tag": "action",
         "actions": [
           {
             "tag": "button",
             "text": {
               "tag": "plain_text",
               "content": "同意"
             },
             "type": "primary",
             "value": {
               "action": "approve"
             }
           }
         ]
       }
     ]
   }
   ```

### 卡片交互回调

1. **回调事件订阅**
   - 配置回调 URL: 在飞书开放平台配置
   - 接收事件: `card.action.trigger` (按钮点击)
   - 验证签名: 使用 `Encrypt Key` 验证请求来自飞书

2. **回调请求结构**
   ```json
   {
     "challenge": "xxx",  // 首次验证
     "token": "xxx",      // 验证 token
     "type": "url_verification", // 或 "event_callback"
     "event": {
       "type": "card.action.trigger",
       "token": "xxx",
       "action": {
         "value": {
           "action": "approve"
         },
         "tag": "button"
       },
       "card_id": "xxx",
       "user_id": "xxx",
       "timestamp": "xxx"
     }
   }
   ```

3. **回调响应**
   - 返回新的卡片 JSON 更新原卡片
   - 或返回 `{"code": 0}` 表示处理成功

### 卡片更新

1. **主动更新卡片**
   - API: `PATCH /im/v1/messages/{message_id}`
   - 参数: `content: {新的卡片 JSON}`
   - 用于更新已发送的卡片内容

2. **通过回调更新**
   - 在回调响应中返回新的卡片 JSON
   - 飞书自动更新原卡片

---

## 🔧 Phase 3 架构建议

### 方案 A: 合并在 messaging 模块 (当前方案)

**优点**: 简化用户接口,一个模块完成消息和卡片
**缺点**: 混淆了两个独立的 API,不符合飞书架构

```
messaging/
├── client.py           # 消息发送客户端 (IM API)
├── card_builder.py     # 卡片构建器 (CardKit)
├── callback_handler.py # 卡片回调处理 (CardKit)
└── media_uploader.py   # 媒体上传 (IM API)
```

### 方案 B: 分离 cardkit 模块 ⭐ **推荐**

**优点**: 清晰区分两个 API,架构清晰,易于维护
**缺点**: 增加一个模块

```
messaging/
├── client.py           # 消息发送客户端 (IM API)
│   ├── send_text_message()
│   ├── send_rich_text_message()
│   ├── send_image_message()
│   ├── send_file_message()
│   └── send_card_message()  # ⚠️ 调用 cardkit 构建卡片,用消息 API 发送
├── media_uploader.py   # 媒体上传 (IM API)
└── lifecycle.py        # 消息生命周期管理 (撤回、编辑、回复)

cardkit/
├── builder.py          # 卡片构建器 (CardKit API)
│   ├── CardBuilder
│   ├── build_approval_card()
│   ├── build_notification_card()
│   └── build_form_card()
├── callback_handler.py # 卡片回调处理 (CardKit API)
│   ├── verify_signature()
│   ├── route_callback()
│   └── update_card()
└── updater.py          # 卡片更新 (CardKit API)
    └── update_card_content()
```

### 方案 C: 混合方案 (折中)

保持 messaging 模块,但内部明确区分:

```
messaging/
├── message/            # 消息 API (IM v1)
│   ├── client.py
│   ├── media_uploader.py
│   └── lifecycle.py
└── card/               # 卡片 API (CardKit v1)
    ├── builder.py
    ├── callback_handler.py
    └── updater.py
```

---

## 📝 Phase 3 任务调整建议

### 当前 tasks.md 问题

```markdown
### 交互式卡片
- [ ] T044 实现卡片构建器 src/lark_service/messaging/card_builder.py
- [ ] T045 实现卡片发送 messaging/client.py (send_interactive_card)
- [ ] T046 实现回调处理器 src/lark_service/messaging/callback_handler.py
```

**问题**:
- T044 卡片构建器属于 **CardKit API**
- T045 卡片发送混合了两个 API (构建用 CardKit,发送用 IM API)
- T046 回调处理属于 **CardKit API**

### 建议调整 (方案 B)

#### 保持在 Phase 3:

```markdown
### 消息客户端 (IM API)
- [ ] T041 实现消息客户端 src/lark_service/messaging/client.py
  - send_text_message() - 文本消息
  - send_rich_text_message() - 富文本消息
  - send_image_message() - 图片消息
  - send_file_message() - 文件消息
  - send_card_message(card_json) - 发送卡片消息 (接收 CardKit 构建的 JSON)
- [ ] T042 实现批量发送 messaging/client.py
- [ ] T043 实现消息生命周期管理 messaging/lifecycle.py
  - recall_message() - 撤回
  - edit_message() - 编辑
  - reply_message() - 回复
```

#### 移到新的 Phase 3.5 或 Phase 4:

```markdown
### 卡片服务 (CardKit API)
- [ ] T044 实现卡片构建器 src/lark_service/cardkit/builder.py
  - CardBuilder 类
  - build_approval_card() - 审批卡片
  - build_notification_card() - 通知卡片
  - build_form_card() - 表单卡片
- [ ] T045 实现卡片回调处理器 src/lark_service/cardkit/callback_handler.py
  - verify_signature() - 签名验证
  - route_callback() - 事件路由到 RabbitMQ
  - handle_url_verification() - URL 验证
- [ ] T046 实现卡片更新器 src/lark_service/cardkit/updater.py
  - update_card_content() - 主动更新卡片
```

---

## 🎯 Phase 3 MVP 范围建议

### 最小可行方案 (MVP)

**包含**: 消息 API 的核心功能
- ✅ 文本消息
- ✅ 富文本消息
- ✅ 图片消息
- ✅ 文件消息
- ✅ 批量发送
- ✅ 消息撤回
- ✅ 发送简单卡片消息 (使用预定义 JSON,不包含构建器)

**延后到后续 Phase**:
- ⏸️ 卡片构建器 (CardKit API)
- ⏸️ 卡片交互回调 (CardKit API)
- ⏸️ 卡片更新 (CardKit API)

### 理由

1. **消息 API 是基础**: 文本、图片、文件消息是最常用功能
2. **卡片是增强功能**: 卡片构建和交互较复杂,可以先用简单 JSON
3. **降低 Phase 3 复杂度**: 专注于消息发送核心流程
4. **独立测试**: 消息功能可以独立验证,不依赖卡片回调

---

## 📋 检查清单调整建议

### phase3-messaging.md 需要明确

当前检查清单混合了消息和卡片需求,建议:

#### 选项 1: 重命名检查清单

- 改名为 `phase3-messaging-and-cardkit.md`
- 明确说明包含两个 API 的需求

#### 选项 2: 拆分检查清单 ⭐ **推荐**

- `phase3-messaging.md` - 仅检查消息 API 需求
- `phase3-cardkit.md` - 仅检查卡片 API 需求 (如果 Phase 3 包含卡片)

#### 选项 3: 标注 API 来源

在每个检查项中标注 API 来源:

```markdown
- [ ] CHK001 - [IM API] 是否为所有消息类型(文本、富文本、图片、文件)定义了完整的请求 schema?
- [ ] CHK018 - [CardKit API] 是否定义了卡片 JSON 结构不合法时的错误响应?
- [ ] CHK092 - [CardKit API] 是否定义了卡片构建器的模板类型和参数?
```

---

## ✅ 推荐行动方案

### 立即行动

1. **明确 Phase 3 范围**
   - 决定是否在 Phase 3 包含 CardKit API
   - 建议: Phase 3 仅实现消息 API + 简单卡片发送

2. **更新 tasks.md**
   - 如果仅消息 API: 移除 T044-T046 或标记为 Phase 4
   - 如果包含卡片: 明确标注 `[CardKit API]`

3. **更新 phase3-messaging.md**
   - 选项 A: 添加 API 来源标注
   - 选项 B: 拆分为两个检查清单

4. **更新 spec.md 和 contracts/messaging.yaml**
   - 在 FR-025 中明确说明卡片发送使用消息 API
   - 在 FR-025a 中明确说明回调处理使用 CardKit API

### 参考飞书官方文档

- **消息 API**: https://open.feishu.cn/document/server-docs/im-v1/introduction
- **卡片 API**: https://open.feishu.cn/document/cardkit-v1/feishu-card-resource-overview
- **消息发送**: https://open.feishu.cn/document/server-docs/im-v1/message/create
- **卡片搭建指南**: https://open.feishu.cn/document/cardkit-v1/card-build-guide/card-structure
- **卡片交互回调**: https://open.feishu.cn/document/cardkit-v1/card-callback/card-callback-overview

---

## 📊 总结

| 维度 | 消息 API (IM v1) | 卡片 API (CardKit v1) |
|------|-----------------|---------------------|
| **用途** | 发送各类消息 | 构建和交互卡片 |
| **API 端点** | `/im/v1/messages` | `/cardkit/v1/*` |
| **Token** | app/tenant_access_token | app_access_token |
| **Phase 3 优先级** | ⭐ 高 (MVP 核心) | ⏸️ 中 (可延后) |
| **复杂度** | 中 | 高 (回调、签名验证) |
| **独立性** | 可独立实现 | 依赖消息 API 发送 |

**建议**: Phase 3 专注于**消息 API**,CardKit API 延后到 Phase 3.5 或 Phase 4。
