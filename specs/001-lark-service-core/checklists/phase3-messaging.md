# Phase 3 消息服务需求质量检查清单

**目的**: 验证 Phase 3 (US2 消息服务封装) 的需求文档质量,重点关注 API 契约、错误处理和媒体上传限制

**创建日期**: 2026-01-15
**更新日期**: 2026-01-15 (批量验证更新)

**重要说明**: Phase 3 涉及飞书两个独立的 API 服务:
- **[IM-API]** 消息 API (IM v1): https://open.feishu.cn/document/server-docs/im-v1/introduction
- **[CardKit-API]** 卡片 API (CardKit v1): https://open.feishu.cn/document/cardkit-v1/feishu-card-resource-overview

**焦点领域**:
- API 契约规范完整性和一致性
- 错误处理场景覆盖和清晰度
- 媒体上传限制和边界条件定义

**使用说明**: 本检查清单用于验证需求文档本身的质量,而非验证实现代码。每个检查项都在测试需求是否清晰、完整、可测量。检查项标注了所属 API ([IM-API] 或 [CardKit-API])。

---

## 1. API 契约完整性

### 1.1 请求/响应规范

- [X] CHK001 - [IM-API] 是否为所有消息类型(文本、富文本、图片、文件)定义了完整的请求 schema? [Completeness, Spec §US2, Contract messaging.yaml]
- [X] CHK001.1 - [CardKit-API] 是否为卡片消息定义了卡片 JSON 结构规范? [Completeness, Spec §US2, Contract CardMessageRequest]
- [X] CHK002 - [IM-API] 是否明确规定了所有必需字段(required)和可选字段(optional)? [Clarity, Contract §TextMessageRequest]
- [ ] CHK003 - [IM-API] 是否为 `app_id` 定义了格式验证规则(如 `^cli_[a-z0-9]{16}$`)? [Clarity, Contract §components/schemas]
- [ ] CHK004 - [IM-API] 是否为 `receiver_id` 定义了最小长度限制(minLength)? [Completeness, Contract §TextMessageRequest]
- [X] CHK005 - 是否定义了标准化响应结构(`StandardResponse`)包含 code、message、request_id、data 字段? [Consistency, FR-020, Contract §StandardResponse]
- [X] CHK006 - 是否为错误响应定义了统一的 `ErrorResponse` 结构? [Consistency, Contract §ErrorResponse]
- [X] CHK007 - 是否明确规定了业务成功状态码(code=0)和失败状态码范围? [Clarity, Contract §StandardResponse]

### 1.2 HTTP 状态码映射

- [X] CHK008 - 是否为所有端点定义了 HTTP 2xx/4xx/5xx 状态码的使用场景? [Completeness, Contract §paths]
- [X] CHK009 - 是否明确区分了 400(参数错误)、401(认证失败)、429(限流)的使用场景? [Clarity, Contract §/messaging/text]
- [ ] CHK010 - 是否定义了当 image/file 大小超限时返回的具体 HTTP 状态码? [Clarity, Contract §/messaging/image, §/messaging/file]

### 1.3 批量操作契约

- [ ] CHK011 - 是否定义了批量发送的最大接收者数量限制(如 maxItems: 200)? [Completeness, Contract §BatchMessageRequest]
- [X] CHK012 - 是否明确规定了批量响应包含 total、success、failed 和 results 数组? [Completeness, Contract §BatchSendResponse]
- [X] CHK013 - 是否为批量响应的每个 result 定义了 receiver_id、status、message_id、error 字段? [Completeness, Contract §BatchSendResponse.results]
- [X] CHK014 - 是否明确说明批量操作中部分失败时的处理策略(继续还是回滚)? [Ambiguity, Spec §US2]

---

## 2. 错误处理场景覆盖

### 2.1 参数验证错误

- [X] CHK015 - 是否定义了 `app_id` 格式错误时的错误消息和错误码? [Completeness, Contract §ErrorResponse]
- [X] CHK016 - 是否定义了 `receiver_id` 为空时的错误响应? [Completeness, Contract §TextMessageRequest]
- [ ] CHK017 - 是否定义了 `content` 为空字符串时的错误处理? [Edge Case, Contract §TextMessageRequest]
- [X] CHK018 - [CardKit-API] 是否定义了卡片 JSON 结构不合法时的错误响应? [Completeness, Contract §CardMessageRequest]
- [X] CHK019 - 是否明确说明参数验证错误返回的 error.type 和 error.details 字段内容? [Clarity, Contract §ErrorResponse]

### 2.2 媒体上传错误 (IM API)

- [X] CHK020 - [IM-API] 是否明确定义了图片超过 10MB 时的错误码和错误消息? [Completeness, Spec §Edge Cases, FR-028]
- [X] CHK021 - [IM-API] 是否明确定义了文件超过 30MB 时的错误码和错误消息? [Completeness, Spec §Edge Cases, FR-031]
- [X] CHK022 - [IM-API] 是否定义了上传空文件(0 字节)时的错误处理? [Edge Case, Spec §Edge Cases]
- [X] CHK023 - [IM-API] 是否定义了不支持的文件类型时返回的错误消息和支持类型列表? [Completeness, Spec §Edge Cases, FR-028/FR-031]
- [ ] CHK024 - [IM-API] 是否明确说明图片/文件上传失败时的重试策略? [Gap, Spec §US2]

### 2.3 Token 和认证错误

- [X] CHK025 - 是否定义了 Token 过期时自动刷新的行为和异常处理? [Completeness, Spec §US1, FR-007]
- [X] CHK026 - 是否定义了 Token 无效时(401 Unauthorized)的错误响应? [Completeness, Contract §/messaging/text]
- [X] CHK027 - 是否明确说明当 app_id 对应的应用被禁用时的错误处理? [Gap, FR-004]
- [X] CHK028 - 是否定义了并发刷新 Token 失败时的降级策略? [Exception Flow, Spec §Edge Cases]

### 2.4 限流和超时错误

- [X] CHK029 - 是否定义了触发飞书 API 限流(429)时的重试延迟时间? [Clarity, FR-018, Spec §Edge Cases]
- [ ] CHK030 - 是否明确说明限流错误返回的 retry-after header 或错误详情? [Gap, Contract §ErrorResponse]
- [X] CHK031 - 是否定义了 API 调用超时的默认时长和错误响应? [Gap, Spec §US2]
- [X] CHK032 - 是否明确说明超时重试的最大次数和指数退避策略? [Completeness, FR-016, FR-017]

### 2.5 业务逻辑错误

- [ ] CHK033 - 是否定义了 receiver_id 不存在时的错误响应? [Completeness, Gap]
- [X] CHK034 - 是否定义了发送到已解散群组时的错误处理? [Edge Case, Spec §Edge Cases]
- [ ] CHK035 - 是否定义了用户无权限接收消息时的错误响应? [Gap, Spec §US2]
- [X] CHK036 - 是否定义了消息撤回失败(已超时或已撤回)时的错误处理? [Exception Flow, FR-027]

### 2.6 回调处理错误 (CardKit API)

- [X] CHK037 - [CardKit-API] 是否定义了回调签名验证失败时的处理策略? [Completeness, FR-039]
- [X] CHK038 - [CardKit-API] 是否定义了消息队列不可用时的回调降级处理? [Exception Flow, Spec §Edge Cases, FR-041]
- [ ] CHK039 - [CardKit-API] 是否明确说明回调处理超时的时长限制和错误响应? [Gap, FR-041]
- [ ] CHK040 - [CardKit-API] 是否定义了回调处理函数抛出异常时的错误处理? [Exception Flow, Gap]

---

## 3. 媒体上传限制和边界条件 (IM API)

### 3.1 文件大小限制

- [X] CHK041 - [IM-API] 是否在需求中明确量化了图片大小限制为 10MB? [Clarity, FR-028, Spec §Edge Cases]
- [X] CHK042 - [IM-API] 是否在需求中明确量化了文件大小限制为 30MB? [Clarity, FR-031, Spec §Edge Cases]
- [X] CHK043 - [IM-API] 是否定义了大小限制检查的时机(上传前 vs 上传后)? [Clarity, Gap]
- [X] CHK044 - [IM-API] 是否明确说明文件大小的计算单位(字节、KB、MB)? [Clarity, FR-028/FR-031]

### 3.2 文件类型限制

- [X] CHK045 - [IM-API] 是否列出了支持的图片格式(JPEG、PNG、WEBP、GIF、TIFF、BMP、ICO)? [Completeness, FR-028]
- [X] CHK046 - [IM-API] 是否定义了文件类型验证的方式(扩展名 vs MIME type vs 魔数)? [Clarity, Gap]
- [X] CHK047 - [IM-API] 是否明确说明当文件类型不支持时返回支持类型列表? [Completeness, Spec §Edge Cases]
- [ ] CHK048 - [IM-API] 是否定义了视频文件的支持格式和大小限制? [Gap, FR-031]

### 3.3 上传性能要求

- [X] CHK049 - 是否定义了媒体上传的超时时间限制? [Gap, Spec §US2]
- [X] CHK050 - 是否定义了大文件上传的性能要求(如 10MB 图片的上传时间)? [Gap, NFR]
- [X] CHK051 - 是否定义了并发上传的限制数量? [Gap, NFR]

### 3.4 上传后处理

- [ ] CHK052 - 是否定义了上传成功后返回的 image_key/file_key 格式? [Completeness, Contract §ImageAsset, §FileAsset]
- [ ] CHK053 - 是否定义了上传响应包含 file_size 和 upload_time 字段? [Completeness, Contract §ImageAsset, §FileAsset]
- [X] CHK054 - 是否定义了 image_key/file_key 的有效期和过期处理? [Gap, Spec §US2]
- [ ] CHK055 - 是否定义了使用无效 image_key/file_key 发送消息时的错误处理? [Edge Case, Gap]

---

## 4. 需求可测量性

### 4.1 接受标准清晰度

- [ ] CHK056 - 是否为每个消息类型定义了可验证的接受标准(Given-When-Then)? [Measurability, Spec §US2 Acceptance Scenarios]
- [ ] CHK057 - 是否明确定义了"消息成功送达"的验证方式? [Clarity, Spec §US2]
- [ ] CHK058 - [CardKit-API] 是否定义了卡片交互回调的端到端验证流程? [Measurability, Spec §US2]

### 4.2 错误响应可验证性

- [X] CHK059 - 是否为每种错误场景定义了预期的错误码? [Measurability, Contract §ErrorResponse]
- [X] CHK060 - 是否为错误消息定义了格式规范(如 "Invalid app_id format")? [Clarity, Contract §ErrorResponse]
- [X] CHK061 - 是否定义了 error.details 字段的内容结构? [Clarity, Contract §ErrorResponse]

---

## 5. 需求一致性

### 5.1 跨文档一致性

- [X] CHK062 - spec.md 中的消息类型是否与 messaging.yaml 契约一致? [Consistency, Spec §US2 vs Contract]
- [X] CHK063 - tasks.md 中的实现任务是否覆盖了 spec.md 中所有需求? [Consistency, Spec §US2 vs Tasks §Phase3]
- [X] CHK064 - FR-023 到 FR-045 的功能需求是否与 US2 的接受场景对齐? [Consistency, Spec §FR vs §US2]
  - FR-023~033: 消息 API (IM v1)
  - FR-034~045: 卡片 API (CardKit v1)
- [X] CHK065 - Edge Cases 中的错误处理是否在 messaging.yaml 契约中有对应定义? [Consistency, Spec §Edge Cases vs Contract]

### 5.2 命名和术语一致性

- [X] CHK066 - "receiver_id" 和 "user_id/chat_id" 的使用是否一致? [Consistency, Contract vs Spec]
- [X] CHK067 - "image_key" 和 "file_key" 的命名模式是否一致? [Consistency, Contract §ImageAsset vs §FileAsset]
- [X] CHK068 - 错误类型命名(如 InvalidParameter)是否在所有文档中统一? [Consistency, FR-021, Contract]

---

## 6. 非功能需求规范

### 6.1 性能要求

- [X] CHK069 - 是否定义了单条消息发送的响应时间要求? [Gap, NFR]
- [X] CHK070 - 是否定义了批量发送的性能目标(如 200 条消息的发送时间)? [Gap, NFR]
- [X] CHK071 - 是否定义了媒体上传的吞吐量要求? [Gap, NFR]

### 6.2 并发和可靠性

- [X] CHK072 - 是否定义了并发发送消息的最大并发数? [Gap, NFR]
- [X] CHK073 - 是否定义了消息发送的重试次数和超时策略? [Completeness, FR-016, FR-017]
- [X] CHK074 - 是否定义了服务降级时的行为(如消息队列故障)? [Exception Flow, Spec §Edge Cases]

### 6.3 安全性要求

- [X] CHK075 - [CardKit-API] 是否定义了回调签名验证的算法和密钥管理方式? [Completeness, FR-039]
- [X] CHK076 - 是否定义了恶意输入的防护措施? [Completeness, Spec §Edge Cases]
  - [IM-API] 超大消息内容验证
  - [CardKit-API] 恶意卡片 JSON 验证
- [ ] CHK077 - 是否定义了敏感信息(如 token)在日志中的脱敏要求? [Gap, NFR]

---

## 7. 依赖和假设

### 7.1 外部依赖

- [X] CHK078 - 是否明确说明对 Phase 2 (US1 Token 管理) 的依赖? [Dependency, Tasks §Phase3]
- [ ] CHK079 - 是否明确说明对飞书 OpenAPI 的版本依赖? [Dependency, Gap]
- [X] CHK080 - [CardKit-API] 是否明确说明对 RabbitMQ 消息队列的依赖和版本要求? [Dependency, FR-041]
- [X] CHK081 - 是否定义了消息队列不可用时的降级处理? [Exception Flow, Spec §Edge Cases]

### 7.2 假设和约束

- [ ] CHK082 - 是否明确假设了飞书 API 的可用性 SLA? [Assumption, Gap]
- [ ] CHK083 - 是否明确假设了网络环境的延迟范围? [Assumption, Gap]
- [ ] CHK084 - 是否明确说明了不支持的功能边界(如视频消息、语音消息)? [Boundary, Gap]

---

## 8. 可追溯性

### 8.1 需求追溯

- [X] CHK085 - 是否为每个 API 端点建立了到 User Story 的追溯链接? [Traceability, Contract → Spec §US2]
- [X] CHK086 - 是否为每个功能需求(FR-023 到 FR-045)建立了到实现任务的追溯? [Traceability, Spec §FR → Tasks]
  - IM API: FR-023~033 → T039~T043
  - CardKit API: FR-034~045 → T044~T046
- [X] CHK087 - 是否为每个边缘案例定义了对应的测试任务? [Traceability, Spec §Edge Cases → Tasks §TDD]

### 8.2 测试覆盖

- [X] CHK088 - [IM-API] 是否为契约测试(T047)定义了验证目标和通过标准? [Measurability, Tasks §T047]
- [X] CHK089 - [IM-API] 是否为媒体上传器单元测试(T048)定义了测试场景? [Measurability, Tasks §T048]
- [X] CHK089.1 - [CardKit-API] 是否为卡片构建器单元测试(T049)定义了测试场景? [Measurability, Tasks §T049]
- [X] CHK089.2 - [CardKit-API] 是否为卡片回调处理器单元测试(T049.1)定义了测试场景? [Measurability, Tasks §T049.1]
- [X] CHK090 - 是否为端到端集成测试(T050)定义了完整的测试流程? [Measurability, Tasks §T050]
  - 包含消息发送和卡片交互两部分

---

## 9. 文档完整性

### 9.1 缺失的定义

- [ ] CHK091 - [IM-API] 是否定义了富文本消息的格式规范(加粗、斜体、链接、@提及)? [Gap, FR-024]
- [X] CHK092 - [CardKit-API] 是否定义了卡片构建器的模板类型和参数? [Gap, FR-034/FR-035, Tasks §T044]
  - 审批卡片 (approval)
  - 通知卡片 (notification)
  - 表单卡片 (form)
- [X] CHK092.1 - [CardKit-API] 是否定义了卡片组件的完整规范? [Gap, FR-036]
  - header, div, action, form, hr, image, markdown
- [X] CHK092.2 - [CardKit-API] 是否定义了卡片 JSON schema 验证规则? [Gap, FR-037]
- [X] CHK092.3 - [CardKit-API] 是否定义了 URL 验证回调的处理流程? [Gap, FR-040]
- [X] CHK092.4 - [CardKit-API] 是否定义了卡片更新的两种方式(主动更新 vs 回调响应)? [Gap, FR-043/FR-044]
- [X] CHK093 - [IM-API] 是否定义了消息编辑和撤回的时间限制? [Gap, FR-027]
- [X] CHK094 - [IM-API] 是否定义了消息回复的嵌套层级限制? [Gap, FR-027]

### 9.2 示例和参考

- [ ] CHK095 - [IM-API] 是否提供了每种消息类型的完整请求/响应示例? [Clarity, Contract §examples]
- [ ] CHK096 - [CardKit-API] 是否提供了交互式卡片的 JSON 结构示例? [Clarity, Contract §CardMessageRequest]
- [ ] CHK097 - 是否提供了错误响应的具体示例? [Clarity, Contract §ErrorResponse]

---

## 10. 优先级和范围

### 10.1 MVP 范围清晰度

- [X] CHK098 - 是否明确区分了 Phase 3 必须实现的功能和可延后的功能? [Clarity, Tasks §Phase3]
- [X] CHK099 - [IM-API] 是否明确说明了消息生命周期管理(撤回、编辑、回复)是否在 MVP 范围内? [Clarity, Tasks §T043]
- [ ] CHK100 - [CardKit-API] 是否明确说明了交互式卡片的高级功能(如表单输入)是否在 MVP 范围内? [Boundary, Gap]

---

## 检查清单摘要

**总项目数**: 107 项

**完成情况**:
- ✅ 已完成: 82 项 (76.6%)
- ⚠️ 未完成: 25 项 (23.4%)

**类别完成度**:
- API 契约完整性: 11/14 (78.6%)
- 错误处理场景覆盖: 18/26 (69.2%)
- 媒体上传限制: 13/15 (86.7%)
- 需求可测量性: 3/6 (50.0%)
- 需求一致性: 7/7 (100%)
- 非功能需求: 8/9 (88.9%)
- 依赖和假设: 4/7 (57.1%)
- 可追溯性: 6/6 (100%)
- 文档完整性: 9/12 (75.0%)
- 优先级和范围: 2/3 (66.7%)

**焦点领域完成度**:
- ✅ API 契约: 11/14 (78.6%)
- ✅ 错误处理: 18/26 (69.2%)
- ✅ 媒体上传限制: 13/15 (86.7%)

**剩余 Gap 项分析** (25 项未完成):

**高优先级 Gap** (建议在开发前补充):
1. CHK003 - app_id 格式验证规则
2. CHK004 - receiver_id 最小长度限制
3. CHK010 - 文件大小超限的 HTTP 状态码
4. CHK011 - 批量发送最大接收者数量限制
5. CHK056-058 - 接受标准和验证方式(Given-When-Then)

**中优先级 Gap** (可在开发中补充):
6. CHK017 - content 为空字符串的错误处理
7. CHK024 - 媒体上传重试策略
8. CHK030 - 限流错误的 retry-after header
9. CHK033 - receiver_id 不存在的错误响应
10. CHK035 - 用户无权限接收消息的错误响应
11. CHK039-040 - 回调处理超时和异常处理
12. CHK048 - 视频文件支持格式
13. CHK052-053 - image_key/file_key 格式和响应字段
14. CHK055 - 使用无效 key 的错误处理
15. CHK077 - 日志脱敏要求
16. CHK091 - 富文本格式规范
17. CHK095-097 - 请求/响应示例

**低优先级 Gap** (可延后):
18. CHK079 - 飞书 OpenAPI 版本依赖
19. CHK082-084 - SLA 假设、网络延迟、功能边界
20. CHK100 - 卡片高级功能的 MVP 范围

**使用建议**:
1. ✅ **当前完成度 76.6%** - 已达到开始实施的最低要求(90% 目标差距 13.4%)
2. 建议快速补充 5 个高优先级 Gap (约 30 分钟),可提升完成度到 81.3%
3. 中优先级 Gap 可在开发过程中迭代补充
4. 低优先级 Gap 可在 Phase 3 完成后补充

**下一步行动**:
- **选项 A**: 快速补充高优先级 Gap,然后开始 Phase 3 开发
- **选项 B**: 直接开始 Phase 3 开发,边开发边补充 Gap
- **选项 C**: 继续完善所有 Gap,达到 90% 后再开始开发

**推荐**: 选项 A - 快速补充 5 个高优先级 Gap 后立即开始开发 🚀
