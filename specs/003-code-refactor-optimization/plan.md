# Implementation Plan: 代码重构与最终产品优化

**Branch**: `003-code-refactor-optimization` | **Date**: 2026-01-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-code-refactor-optimization/spec.md`

## Summary

本特性旨在完成 LarkService 项目的最终产品交付,通过系统性重构优化 `app_id` 管理机制,简化单应用场景使用体验,优雅支持多应用场景,并完成生产环境基础设施(Docker、CI/CD、监控)。技术方案包括:引入 BaseServiceClient 统一 app_id 解析逻辑(5层优先级),提供工厂方法和上下文管理器支持应用切换,实现 API 限流、自动重试、Token UX 优化等稳定性增强功能,最终达到生产级交付标准。

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**:
- lark-oapi (官方 SDK)
- FastAPI (HTTP 服务框架)
- SQLAlchemy (ORM,用于 PostgreSQL)
- APScheduler (定时任务调度)
- Prometheus Client (指标导出)
- pytest + pytest-cov (测试框架)
- ruff + mypy (代码质量工具)

**Storage**:
- SQLite (应用配置管理,轻量级)
- PostgreSQL (Token 持久化,高并发场景)

**Testing**:
- pytest (单元测试和集成测试)
- pytest-cov (测试覆盖率)
- pytest-asyncio (异步测试支持)
- 目标覆盖率: 整体 ≥ 85%, 核心模块 ≥ 90%

**Target Platform**:
- Linux server (Docker 容器化部署)
- 支持 x86_64 和 arm64 架构

**Project Type**: Single project (后端服务)

**Performance Goals**:
- CI/CD 完整流程 < 10 分钟
- Docker 容器启动时间 < 30 秒
- 健康检查响应时间 < 100ms
- API 限流准确率 100%
- Token 刷新成功率 ≥ 98% (飞书 API 可用时)

**Constraints**:
- Docker 镜像大小 < 500MB
- 单应用场景代码行数减少 30% (相比重构前)
- 向后兼容: 现有代码无需修改即可运行
- 线程安全约束: `use_app()` 上下文管理器不支持多线程并发切换

**Scale/Scope**:
- 支持管理 10+ 飞书应用配置
- 支持 100+ 并发 API 请求
- 预计新增代码 ~2000 行 (包括 BaseServiceClient、工厂方法、限流器、重试逻辑等)
- 重构影响文件 ~15 个 (MessagingClient、ContactClient、CloudDocClient、aPaaSClient、CredentialPool 等)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

基于 [constitution.md](../../.specify/memory/constitution.md) v1.2.0 的合规性检查:

### ✅ 合规项 (无违规)

| 原则 | 检查项 | 状态 | 说明 |
|------|--------|------|------|
| **I. 核心技术栈** | 基于 Python + lark-oapi SDK | ✅ PASS | 使用 Python 3.12 + 官方 lark-oapi SDK,无自行实现底层调用 |
| **II. 代码质量** | mypy 99%+ 覆盖率, ruff 格式化, 标准 Docstring | ✅ PASS | 所有新增代码将包含类型注解和标准 Docstring |
| **III. 架构完整性** | DDD, 无循环依赖 | ✅ PASS | BaseServiceClient 作为基类,不引入循环依赖 |
| **IV. 响应一致性** | 标准化响应结构 | ✅ PASS | 保持现有统一错误处理机制 (ConfigError, AuthenticationError) |
| **V. 安全性底线** | 凭证加密,环境变量注入 | ✅ PASS | 使用现有 CredentialPool 加密存储机制 |
| **VI. 环境一致性** | 单目录隔离 | ✅ PASS | 项目结构保持现有 src/、tests/、specs/ 分层 |
| **VII. 零信任安全** | .env 管理,无硬编码 | ✅ PASS | 继续使用 .env 文件管理敏感配置 |
| **VIII. 测试先行** | TDD, 红-绿-重构 | ✅ PASS | 遵循 TDD,测试覆盖率 ≥ 85% |
| **IX. 文档语言** | 代码英文,文档中文 | ✅ PASS | 代码注释/变量使用英文,规范文档使用中文 |
| **X. 文件闭环** | 原地迭代,无冗余 | ✅ PASS | 在现有文件上重构,不创建重复文件 |
| **XI. Git 提交规范** | 格式化,质量检查,Conventional Commits | ✅ PASS | 使用 pre-commit-check.sh,遵循 Conventional Commits |

### 🎯 无需豁免

本计划完全符合宪章所有原则,无需申请复杂性豁免。

**重新评估触发点**: Phase 1 设计完成后,特别关注 BaseServiceClient 的架构完整性和测试覆盖度。

## Project Structure

### Documentation (this feature)

```text
specs/003-code-refactor-optimization/
├── spec.md              # Feature specification (已完成)
├── research.md          # Technical research (已完成)
├── plan.md              # This file (当前文件)
├── data-model.md        # Phase 1 output (待生成)
├── quickstart.md        # Phase 1 output (待生成)
├── contracts/           # Phase 1 output (待生成)
│   ├── base-service-client.md
│   ├── credential-pool.md
│   └── application-manager.md
└── tasks.md             # Phase 2 output (由 /speckit.tasks 生成)
```

### Source Code (repository root)

```text
src/lark_service/
├── core/
│   ├── credential_pool.py      # ✏️ 重构: 添加工厂方法和默认 app_id 管理
│   ├── application_manager.py  # ✏️ 重构: 添加 get_default_app_id()
│   ├── base_service_client.py  # ➕ 新增: 统一 app_id 管理基类
│   ├── rate_limiter.py         # ➕ 新增: API 限流器
│   └── exceptions.py           # ✏️ 增强: 添加详细错误消息
│
├── messaging/
│   └── client.py               # ✏️ 重构: 继承 BaseServiceClient,app_id 可选参数
│
├── contact/
│   └── client.py               # ✏️ 重构: 继承 BaseServiceClient,app_id 可选参数
│
├── clouddoc/
│   ├── bitable/
│   │   └── client.py           # ✏️ 重构: 继承 BaseServiceClient,app_id 可选参数
│   └── doc/
│       └── client.py           # ✏️ 重构: 继承 BaseServiceClient,app_id 可选参数
│
├── apaas/
│   └── client.py               # ✏️ 重构: 继承 BaseServiceClient,实现重试逻辑
│
├── websocket/
│   ├── auth_session_manager.py # ✏️ 增强: 添加 API 限流和 Token 过期检测
│   └── card_auth_handler.py   # ✏️ 增强: 实现 Token 过期 UX
│
└── tasks/
    └── sync_user_info.py       # ➕ 新增: 用户信息同步定时任务

tests/
├── unit/
│   ├── core/
│   │   ├── test_base_service_client.py  # ➕ 新增: BaseServiceClient 单元测试
│   │   ├── test_credential_pool.py      # ✏️ 扩展: 工厂方法和默认 app_id 测试
│   │   └── test_rate_limiter.py         # ➕ 新增: 限流器单元测试
│   └── ...
│
└── integration/
    ├── test_app_switching.py            # ➕ 新增: 应用切换集成测试
    ├── test_token_refresh_retry.py      # ➕ 新增: Token 刷新重试测试
    └── ...

# 生产环境配置
docker/
├── Dockerfile                  # ✏️ 优化: 多阶段构建
└── docker-compose.prod.yml     # ➕ 新增: 生产环境配置

.github/
└── workflows/
    └── ci-cd.yml               # ✏️ 完善: 完整 CI/CD 流程

# 项目文档
CHANGELOG.md                    # ✏️ 更新: 记录 v0.3.0 功能
docs/
├── quickstart.md               # ✏️ 更新: 添加多应用场景示例
└── api/
    └── base-service-client.md  # ➕ 新增: BaseServiceClient API 文档
```

**Structure Decision**:
采用现有的单项目结构 (src/lark_service/)。本次重构主要在核心模块(core/)中新增 BaseServiceClient 基类和相关工具类,各功能域客户端(messaging、contact、clouddoc、apaas)继承该基类以统一 app_id 管理逻辑。新增的生产环境配置(docker、.github)与代码库保持物理隔离,符合环境一致性原则。

## Complexity Tracking

> 本计划无宪章违规,无需填写此章节。

---

## Phase 0: Research (已完成)

### ✅ 研究输出

已完成的研究文档: [research.md](./research.md)

**关键决策**:
1. **app_id 解析优先级**: 方法参数 > 上下文管理器 > 客户端默认 > Pool 默认 > 抛出错误
2. **线程安全策略**: 选择方案 B (文档说明不支持并发切换,推荐工厂方法或显式参数)
3. **应用切换方式**: 提供 4 种方式(工厂方法、上下文管理器、方法参数、客户端默认)
4. **向后兼容策略**: app_id 参数变为可选,保留原有显式传参方式

**解决的技术问题**:
- ✅ 如何在不破坏现有 API 的情况下简化单应用场景?
- ✅ 如何优雅支持多应用场景的切换?
- ✅ 如何确保应用上下文不混淆?
- ✅ 如何处理并发场景的线程安全?

---

## Phase 1: Design & Contracts

### 1.1 Data Model (待生成)

输出文件: `data-model.md`

**核心实体**:
1. **BaseServiceClient** (新增抽象基类)
   - 统一所有服务客户端的 app_id 管理逻辑
   - 提供 _resolve_app_id(), get_current_app_id(), list_available_apps(), use_app() 方法

2. **CredentialPool** (重构增强)
   - 新增工厂方法: create_messaging_client(), create_contact_client() 等
   - 新增默认 app_id 管理: set_default_app_id(), get_default_app_id()

3. **ApplicationManager** (重构增强)
   - 新增智能默认应用选择: get_default_app_id()

4. **RateLimiter** (新增功能实体)
   - 用户请求限流器,滑动窗口算法

5. **ScheduledTask** (新增功能实体)
   - 定时任务配置和调度

### 1.2 API Contracts (待生成)

输出目录: `contracts/`

**核心合约**:
1. **BaseServiceClient Contract** (`base-service-client.md`)
   - _resolve_app_id(app_id: str | None) -> str
   - get_current_app_id() -> str | None
   - list_available_apps() -> list[str]
   - use_app(app_id: str) -> ContextManager

2. **CredentialPool Contract** (`credential-pool.md`)
   - set_default_app_id(app_id: str) -> None
   - get_default_app_id() -> str | None
   - list_app_ids() -> list[str]
   - create_messaging_client(app_id: str | None) -> MessagingClient
   - create_contact_client(app_id: str | None) -> ContactClient
   - create_clouddoc_client(app_id: str | None) -> DocClient

3. **ApplicationManager Contract** (`application-manager.md`)
   - get_default_app_id() -> str | None

### 1.3 Quickstart Guide (待生成)

输出文件: `quickstart.md`

**内容大纲**:
1. 快速开始 - 单应用场景 (3 分钟)
2. 多应用场景 - 工厂方法
3. 多应用场景 - 上下文管理器
4. 应用确认和调试
5. 错误处理最佳实践
6. 并发场景最佳实践

---

## Phase 2: Task Breakdown

由 `/speckit.tasks` 命令生成 `tasks.md`,包括:

**任务分类**:
1. **代码重构任务** (T001-T015)
   - BaseServiceClient 实现及测试
   - 各客户端重构(继承 BaseServiceClient)
   - CredentialPool 工厂方法实现
   - 向后兼容性测试

2. **生产部署任务** (T016-T025)
   - Dockerfile 多阶段构建优化
   - docker-compose.prod.yml 创建
   - GitHub Actions CI/CD 完善
   - 健康检查端点实现

3. **稳定性增强任务** (T026-T035)
   - RateLimiter 实现及测试
   - aPaaS 客户端重试逻辑
   - Token 过期 UX 实现
   - 定时任务调度实现

4. **监控和运维任务** (T036-T045)
   - Prometheus 指标新增
   - Grafana 仪表板更新
   - 日志增强(记录 app_id)

5. **测试和文档任务** (T046-T055)
   - 集成测试扩展
   - 真实飞书账号手动测试
   - API 文档更新
   - CHANGELOG.md 完善

**预计任务数**: 50-60 个任务

---

## Implementation Strategy

### 重构原则

1. **增量重构** (Incremental Refactoring)
   - 每次只重构一个模块,确保其他模块不受影响
   - 重构顺序: CredentialPool → BaseServiceClient → MessagingClient → 其他客户端

2. **测试驱动** (Test-Driven)
   - 先编写失败的单元测试
   - 实现最小可行代码
   - 重构优化,保持测试通过

3. **向后兼容优先** (Backward Compatibility First)
   - 保留所有现有 API 签名
   - 将 app_id 参数设为可选,不移除
   - 现有测试必须 100% 通过

4. **并行开发** (Parallel Development)
   - 核心重构(BaseServiceClient)与基础设施(Docker、CI/CD)可并行
   - 限流/重试/监控等功能可在重构完成后并行开发

### 风险缓解

| 风险 | 缓解措施 | 验证方式 |
|------|---------|---------|
| 重构引入回归 | 运行完整测试套件,覆盖率 ≥ 85% | CI 自动检查 |
| 向后兼容性破坏 | 保留所有现有 API,添加兼容性测试 | 专项兼容性测试套件 |
| 线程安全问题 | 明确文档说明,提供并发最佳实践示例 | 并发场景测试 |
| Docker 镜像过大 | 多阶段构建,仅打包运行时依赖 | CI 检查镜像大小 < 500MB |
| CI/CD 流程过长 | 并行执行测试,使用缓存加速 | CI 总时长 < 10 分钟 |

### 验收标准

基于 spec.md 中定义的 25 个成功标准 (SC-001 ~ SC-025):

**必须达成** (P0):
- SC-001~SC-004: 代码质量
- SC-005~SC-008: 生产就绪度
- SC-021~SC-025: 应用管理能力

**高优先级** (P1):
- SC-009~SC-011: 稳定性
- SC-012~SC-014: 可观测性
- SC-018~SC-020: 测试完整性

**中优先级** (P2):
- SC-015~SC-017: 用户体验 (Token UX)

---

## Next Steps

1. **立即行动**:
   ```bash
   # 生成 Phase 1 设计文档
   # (本命令将在后续步骤中自动完成)
   ```

2. **执行 `/speckit.tasks`**:
   ```bash
   /speckit.tasks
   ```
   生成详细的任务清单,包含任务依赖、检查点和验收标准。

3. **开始实施**:
   ```bash
   /speckit.implement
   ```
   按照任务清单逐步实施,遵循 TDD 和增量重构原则。

---

**Plan Status**: ✅ Phase 0 Complete | ⏳ Phase 1 In Progress | ⏳ Phase 2 Pending
**Last Updated**: 2026-01-21
