# Phase 5 需求范围调整报告

**调整日期**: 2026-01-17
**调整原因**: 根据飞书开放平台文档,aPaaS仅包含数据空间表格操作能力
**参考文档**: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/list

---

## 📋 调整概述

### 调整前 (原需求)

Phase 5 原计划包含三大功能模块:
1. ✅ **数据空间表格操作** - 工作空间表格 CRUD
2. ❌ **AI 能力调用** - invoke_ai_capability, 30秒超时
3. ❌ **工作流触发** - trigger_workflow, get_workflow_status

**问题**: AI能力和工作流触发**不在飞书aPaaS数据平台的能力范畴**内

### 调整后 (修订需求)

Phase 5 仅包含:
1. ✅ **数据空间表格操作** - workspace-table API
   - 列出工作空间下的数据表
   - 查询/创建/更新/删除记录
   - 批量操作
   - 字段定义查询

---

## 🔍 飞书 aPaaS 实际能力范围

根据飞书开放平台文档 (https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1),aPaaS 主要提供以下能力:

### ✅ 支持的功能

| 功能 | API端点 | 说明 |
|------|---------|------|
| 列出数据表 | `GET /apaas/v1/workspaces/{workspace_id}/tables` | 获取工作空间下的表格列表 |
| 列出字段 | `GET /apaas/v1/apps/{app_token}/tables/{table_id}/fields` | 获取表格的字段定义 |
| 查询记录 | `POST /apaas/v1/apps/{app_token}/tables/{table_id}/records/search` | 查询记录,支持过滤和分页 |
| 创建记录 | `POST /apaas/v1/apps/{app_token}/tables/{table_id}/records` | 创建单条记录 |
| 更新记录 | `PUT /apaas/v1/apps/{app_token}/tables/{table_id}/records/{record_id}` | 更新单条记录 |
| 删除记录 | `DELETE /apaas/v1/apps/{app_token}/tables/{table_id}/records/{record_id}` | 删除单条记录 |
| 批量创建 | `POST /apaas/v1/apps/{app_token}/tables/{table_id}/records/batch_create` | 批量创建记录 |
| 批量更新 | `POST /apaas/v1/apps/{app_token}/tables/{table_id}/records/batch_update` | 批量更新记录 |

### 支持的字段类型

- 文本(Text)
- 数字(Number)
- 附件(Attachment)
- 超链接(URL)
- 人员(Person)
- 单选(SingleSelect)
- 多选(MultiSelect)
- 关联字段(Link)
- 日期时间(DateTime)
- 等等

### ❌ 不支持的功能

| 功能 | 说明 | 备注 |
|------|------|------|
| AI 能力调用 | invoke_ai_capability | 不在 aPaaS 数据平台范畴 |
| 工作流触发 | trigger_workflow | 属于流程引擎,不在本次范围 |
| 工作流状态查询 | get_workflow_status | 属于流程引擎,不在本次范围 |
| 字段级权限控制 | - | 仅支持表级权限 |
| 行级权限控制 | - | 仅支持表级权限 |
| 审计日志 | - | API未提供 |
| 历史版本管理 | - | API未提供 |
| 实时事件订阅 | - | API未提供 |

---

## 📝 文档更新清单

### 已更新的文档

#### 1. `specs/001-lark-service-core/spec.md`

**User Story 5 - aPaaS 数据空间集成**:
- ✅ 移除了"AI 能力和工作流"相关的验收场景
- ✅ 添加了能力范围说明
- ✅ 补充了创建记录和批量操作的验收场景
- ✅ 添加了飞书开放平台文档链接

**功能需求 (FR-071 ~ FR-080)**:
- ✅ 移除了 FR-077~FR-080 (AI能力和工作流)
- ✅ 新增了 FR-072-1 (创建记录)
- ✅ 新增了 FR-074-1 (批量操作)
- ✅ 新增了 FR-077~FR-080 (字段类型和数据格式规范)

**数据模型**:
- ✅ 移除了 `Workflow` 模型
- ✅ 移除了 `AICapability` 模型
- ✅ 补充了 `FieldDefinition` 模型的详细说明

#### 2. `specs/001-lark-service-core/tasks.md`

**Phase 5 任务清单**:
- ✅ 移除了 T068 (AI客户端)
- ✅ 移除了 T069 (工作流客户端)
- ✅ 更新了 T066 (模型创建) - 移除 Workflow, AICapability
- ✅ 更新了 T067 (客户端实现) - 详细列出所有方法
- ✅ 更新了 T068~T070 (测试) - 移除 AI 超时测试
- ✅ 更新了预计时间: 从 2-3天 → 2天

#### 3. `specs/001-lark-service-core/checklists/phase5-requirements-quality-v2.md`

**新生成的检查清单**:
- ✅ 移除了所有 AI 和工作流相关的检查项
- ✅ 补充了字段类型支持的检查项
- ✅ 补充了批量操作的检查项
- ✅ 添加了与 Bitable 模块一致性的检查项
- ✅ 检查项总数: 从 161项 → 144项
- ✅ P0 检查项: 从 40项 → 34项

### 需要更新的文档

#### 4. `specs/001-lark-service-core/contracts/apaas.yaml`

**需要调整**:
- [ ] 移除 AI 能力相关的接口定义
- [ ] 移除工作流相关的接口定义
- [ ] 确保所有接口与飞书 aPaaS API 一致
- [ ] 补充字段类型的详细定义
- [ ] 补充批量操作的接口定义

---

## 🎯 调整后的 Phase 5 目标

### 核心目标

实现飞书 aPaaS 数据空间表格的完整 CRUD 操作能力,支持:
1. 工作空间和数据表的查询
2. 记录的创建、查询、更新、删除
3. 批量操作(批量创建、批量更新)
4. 字段定义的查询和解析
5. 分页查询和过滤
6. user_access_token 认证

### 技术要点

1. **认证**: 所有操作需要 user_access_token
2. **分页**: 使用 page_token 机制
3. **字段类型**: 支持文本、数字、附件、人员、单选/多选等
4. **数据格式**: 遵循 ISO 8601 (日期时间)、null (空值)
5. **错误处理**: 映射飞书 API 错误码到内部异常

### 预计工作量

- **模型创建**: 0.5天 (WorkspaceTable, TableRecord, FieldDefinition)
- **客户端实现**: 1天 (8个方法)
- **测试编写**: 0.5天 (单元测试 + 集成测试)
- **总计**: 2天

---

## 📊 需求质量对比

### 调整前 (原需求)

| 维度 | 评分 | 说明 |
|------|------|------|
| 完整性 | ❌ 50% | AI和工作流规范严重缺失 |
| 清晰度 | ❌ 21% | 数据格式规范未定义 |
| 一致性 | ⚠️ 45% | 与飞书API能力不一致 |
| 可实现性 | ❌ 低 | 包含不存在的功能 |

**总体评分**: ❌ **41.0%** (不建议开发)

### 调整后 (修订需求)

| 维度 | 预期评分 | 说明 |
|------|----------|------|
| 完整性 | ✅ 85%+ | 数据空间操作需求完整 |
| 清晰度 | ✅ 80%+ | 接口和数据格式清晰 |
| 一致性 | ✅ 95%+ | 与飞书API完全一致 |
| 可实现性 | ✅ 高 | 所有功能均有API支持 |

**预期总体评分**: ✅ **85%+** (可以开始开发)

---

## ✅ 调整收益

### 1. 需求更加聚焦

- 移除了不存在的功能(AI、工作流)
- 专注于数据空间表格操作
- 需求范围清晰,边界明确

### 2. 降低实现风险

- 所有功能都有飞书API支持
- 不需要猜测或假设API行为
- 可以直接参考飞书官方文档

### 3. 减少工作量

- 从 2-3天 → 2天
- 从 7个任务 → 5个任务
- 从 161个检查项 → 144个检查项

### 4. 提高需求质量

- 从 41.0% → 预期 85%+
- P0 通过率从 32.5% → 预期 90%+
- 可实现性从"低" → "高"

---

## 🚀 下一步行动

### 立即行动

1. ✅ 更新 spec.md - **已完成**
2. ✅ 更新 tasks.md - **已完成**
3. ✅ 生成新的需求检查清单 - **已完成**
4. [ ] 更新 apaas.yaml API契约
5. [ ] 对新需求进行评审

### 短期行动

1. [ ] 补充缺失的需求细节(字段类型、数据格式等)
2. [ ] 重新评审,确保 P0 ≥ 90%
3. [ ] 通过评审后开始 Phase 5 开发

---

## 📌 总结

**调整原因**: 原需求包含了不在飞书 aPaaS 数据平台能力范畴内的功能(AI、工作流)

**调整方案**: 移除 AI 和工作流相关功能,专注于数据空间表格操作

**调整效果**:
- ✅ 需求与飞书API能力完全一致
- ✅ 需求范围清晰,边界明确
- ✅ 降低实现风险和工作量
- ✅ 提高需求质量 (41% → 预期85%+)

**建议**: 先完成 Phase 5 (数据空间集成),如果后续有 AI 和工作流需求,可以作为独立的 Phase 6/7 来规划。

---

**报告人**: Lark Service Team
**报告日期**: 2026-01-17
