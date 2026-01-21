# Tasks: 代码重构与最终产品优化

**Feature Branch**: `003-code-refactor-optimization`
**Created**: 2026-01-21
**Status**: Ready for Implementation

## Overview

本特性通过引入 BaseServiceClient 基类统一 app_id 管理,简化单应用场景,优雅支持多应用场景,并完成生产环境基础设施。任务按照增量交付原则组织,每个 Phase 完成后都可独立验证和部署。

**核心目标**:
- 简化 90% 的单应用场景 API 使用
- 优雅支持 10% 的多应用场景
- 完成生产环境基础设施(Docker、CI/CD、监控)
- 向后兼容:现有代码无需修改

**任务数量**: 4 个 Phase,每个 Phase 聚合多个子任务

---

## Implementation Strategy

### 交付原则

1. **增量重构**: 每个 Phase 独立可测试,完成后立即可用
2. **向后兼容优先**: 保留所有现有 API,app_id 参数变可选而非移除
3. **测试驱动**: TDD 红-绿-重构循环,测试覆盖率 ≥ 85%
4. **并行机会**: Phase 1 完成后,Phase 2-4 的部分任务可并行

### MVP 范围

**Phase 1 + Phase 2** = 核心重构完成,单应用和多应用场景可用

---

## Phase 1: 核心基类与重构 (US1 - 简化单应用场景)

**Phase Goal**: 实现 BaseServiceClient 基类和 app_id 解析机制,完成核心服务客户端重构

**Priority**: P1 (最高优先级)

**Independent Test Criteria**:
- [ ] BaseServiceClient 的 5 层 app_id 解析优先级正确工作
- [ ] MessagingClient 继承 BaseServiceClient 后,单应用场景无需传递 app_id
- [ ] 现有测试 100% 通过(向后兼容验证)
- [ ] 测试覆盖率 ≥ 85%

### Tasks

- [X] T001 [US1] **实现 BaseServiceClient 基类** (`src/lark_service/core/base_service_client.py`)
  - 实现 `__init__(credential_pool, app_id=None)` 初始化方法
  - 实现 `_resolve_app_id(app_id=None)` 解析方法(5层优先级)
  - 实现 `get_current_app_id()` 调试方法
  - 实现 `list_available_apps()` 应用列表方法
  - 实现 `use_app(app_id)` 上下文管理器(支持嵌套)
  - **⚠️ 添加完整 Docstring(符合宪章标准,Sphinx 会自动提取)**
    - 每个方法必须包含: 简要描述、Args、Returns、Raises、Example
    - 使用 `----------` 分隔线
    - Example 部分使用 doctest 格式 (`>>>`)
  - 编写单元测试 `tests/unit/core/test_base_service_client.py` (≥10个测试用例)
  - **📚 重新生成 API 文档**: `cd docs && sphinx-apidoc -f -o api/ ../src/lark_service/`
  - 验证: mypy 0错误, ruff 通过, pytest 100%通过, Sphinx 构建无警告

- [X] T002 [P] [US1] **增强 CredentialPool 和 ApplicationManager** (并行任务)
  - **CredentialPool** (`src/lark_service/core/credential_pool.py`):
    - 添加 `_default_app_id` 属性
    - 实现 `set_default_app_id(app_id)` 方法(包含验证)
    - 实现 `get_default_app_id()` 方法(委托给 ApplicationManager)
    - 实现 `list_app_ids()` 方法
    - 实现工厂方法: `create_messaging_client()`, `create_contact_client()`, `create_clouddoc_client()`, `create_apaas_client()`
    - **⚠️ 所有新增方法添加标准 Docstring (Sphinx 兼容)**
    - 更新单元测试 `tests/unit/core/test_credential_pool.py`
  - **ApplicationManager** (`src/lark_service/core/application_manager.py`):
    - 实现 `get_default_app_id()` 方法(智能选择策略)
    - **⚠️ 添加完整 Docstring,说明选择策略(单应用/多应用/无应用)**
    - 更新单元测试 `tests/unit/core/test_application_manager.py`
  - **📚 重新生成 API 文档**: `sphinx-apidoc -f -o docs/api/ src/lark_service/`
  - 验证: 所有新增方法的单元测试通过, Sphinx 构建无警告

- [X] T003 [US1] **重构服务客户端继承 BaseServiceClient** (依赖 T001, T002) [部分完成]
  - **MessagingClient** (`src/lark_service/messaging/client.py`):
    - 继承 BaseServiceClient
    - 修改所有方法的 `app_id` 参数为可选 `app_id: str | None = None`
    - 使用 `self._resolve_app_id(app_id)` 替换直接使用 app_id
    - 添加日志记录使用的 app_id
    - **⚠️ 更新所有方法的 Docstring,反映 app_id 参数现在是可选的**
    - **⚠️ 在 Docstring 的 Example 部分添加单应用场景示例(不传 app_id)**
  - **ContactClient** (`src/lark_service/contact/client.py`): 同上
  - **CloudDocClient** (`src/lark_service/clouddoc/bitable/client.py`): 同上
  - **DocClient** (`src/lark_service/clouddoc/doc/client.py`): 同上
  - **aPaaSClient** (`src/lark_service/apaas/client.py`): 同上
  - **📚 重新生成 API 文档**: `sphinx-apidoc -f -o docs/api/ src/lark_service/`
  - 验证: 现有单元测试和集成测试 100% 通过(向后兼容), Sphinx 构建无警告

- [X] T004 [US1] **创建应用切换集成测试** (`tests/integration/test_app_switching.py`)
  - 测试单应用场景的 3 种配置方式
  - 测试多应用场景的工厂方法
  - 测试 use_app() 上下文管理器(单层和嵌套)
  - 测试 app_id 解析优先级(5层)
  - 测试错误处理(ConfigError, AuthenticationError)
  - 测试多客户端隔离
  - 验证: 所有集成测试通过

### Checkpoint
- ✅ BaseServiceClient 基类功能完整
- ✅ 所有服务客户端已重构
- ✅ 单应用场景代码行数减少 30%
- ✅ 向后兼容:现有测试 100% 通过
- ✅ 测试覆盖率 ≥ 85%

---

## Phase 2: 生产环境基础设施 (US3 - 完成生产部署配置)

**Phase Goal**: 完成 Docker 优化、CI/CD 完善、监控集成,达到生产就绪标准

**Priority**: P1

**Independent Test Criteria**:
- [X] Docker 镜像大小 < 500MB
- [X] docker-compose up 启动时间 < 30秒,健康检查通过
- [X] GitHub Actions CI/CD 流程完整运行时间 < 10分钟
- [X] Prometheus 指标可访问,Grafana 仪表板显示数据

### Tasks

- [X] T005 [P] [US3] **优化 Docker 配置和创建生产环境编排** (并行任务)
  - **优化 Dockerfile** (`docker/Dockerfile`):
    - 采用多阶段构建(builder stage + runtime stage)
    - Builder stage: 安装所有依赖
    - Runtime stage: 仅复制运行时需要的文件
    - 添加健康检查 HEALTHCHECK 指令
    - 目标镜像大小 < 500MB
  - **创建生产环境配置** (`docker/docker-compose.prod.yml`):
    - 配置 lark-service 主服务(资源限制、重启策略、日志驱动)
    - 配置 PostgreSQL 服务(持久化卷、备份策略)
    - 配置 Redis 服务(可选,用于限流)
    - 配置 Prometheus 服务(指标收集)
    - 配置 Grafana 服务(可视化监控)
    - 配置 nginx 反向代理(可选)
    - 添加 volumes、networks、secrets 配置
  - 验证: `docker-compose -f docker-compose.prod.yml up` 成功启动,健康检查通过

- [X] T006 [P] [US3] **完善 CI/CD 流程和健康检查** (并行任务)
  - **完善 GitHub Actions** (`.github/workflows/ci-cd.yml`):
    - Lint 阶段: ruff format --check, ruff check
    - Type Check 阶段: mypy src/
    - Unit Test 阶段: pytest tests/unit/ --cov=src
    - Integration Test 阶段: pytest tests/integration/
    - Build 阶段: docker build,验证镜像大小
    - Push 阶段: docker push (仅 main/master 分支)
    - 使用缓存加速构建
    - 支持多环境部署(dev, staging, prod)
  - **实现健康检查端点** (`src/lark_service/server/health.py`):
    - GET /health: 返回服务状态、数据库连接、Redis连接(如果有)
    - 响应格式: JSON `{"status": "healthy", "checks": {...}}`
    - 响应时间 < 100ms
  - 验证: 在 GitHub 上触发 CI/CD,完整流程 < 10分钟

- [X] T007 [US3] **集成 Prometheus 和 Grafana 监控** (依赖 T005, T006)
  - **添加 Prometheus 指标导出** (`src/lark_service/monitoring/metrics.py`):
    - 使用 prometheus_client 库
    - 导出现有指标: api_requests_total, api_request_duration_seconds 等
    - 新增指标: auth_rate_limit_triggered_total, token_refresh_retry_total
  - **创建 Grafana 仪表板** (`monitoring/grafana/dashboards/lark-service.json`):
    - 面板: QPS、响应时间、错误率
    - 面板: API 限流趋势
    - 面板: Token 刷新成功率
    - 面板: 系统资源(CPU、内存)
  - **更新 docker-compose.prod.yml**: 确保 Prometheus 和 Grafana 正确配置
  - 验证: 访问 Grafana,查看实时指标

- [X] T008 [US3] **更新用户文档和 CHANGELOG** (依赖 T005, T006, T007)
  - 更新 `CHANGELOG.md`: 添加 v0.3.0 版本记录
    - 新增功能: BaseServiceClient、应用切换、工厂方法
    - 生产就绪: Docker 优化、CI/CD 完善、监控集成
    - 已知限制: use_app() 不支持多线程并发
    - Breaking Changes: 无 (100% 向后兼容)
  - 更新 `README.md`: 添加快速开始链接、生产部署说明

  - **📚 创建新的用户指南** (`docs/usage/app-management.md`):
    - 从 `specs/003-code-refactor-optimization/quickstart.md` 整合内容
    - **所有代码示例必须包含完整的导入语句**:
      ```python
      from lark_service.core.credential_pool import CredentialPool
      from lark_service.messaging.client import MessagingClient
      # ... 完整导入
      ```
    - 快速开始 - 单应用场景 (3 种方式,每种提供完整可运行示例)
    - 多应用场景 - 工厂方法和上下文管理器 (完整示例)
    - 应用确认和调试 (包含完整的错误处理示例)
    - 并发场景最佳实践 (正确/错误对比,完整代码)
    - **所有示例代码必须**:
      - ✅ 包含必要的导入语句
      - ✅ 使用真实的类名和方法名 (不能是伪代码)
      - ✅ 参数类型和返回值准确
      - ✅ 在 T013 任务中逐一验证可运行

  - **📚 补充 `docs/usage/advanced.md`** (当前是空文档):
    - 高级应用管理场景:
      - 动态应用选择 (根据环境变量/配置文件)
      - 应用池管理 (多个 CredentialPool 实例)
      - 自定义应用选择策略
    - 性能优化:
      - app_id 解析性能考虑
      - 客户端实例复用 vs 重新创建
      - 连接池管理
    - 故障排查:
      - 常见的 ConfigError 和 AuthenticationError
      - 如何调试应用混淆问题
      - 日志分析技巧
    - **所有示例必须完整可运行**

  - **📚 更新现有使用指南** (添加应用管理说明):
    - `docs/usage/messaging.md`:
      - 在开头添加"应用管理"小节
      - 示例: 单应用和多应用发送消息
      - 链接到 `app-management.md` 详细说明
    - `docs/usage/contact.md`: 同上
    - `docs/usage/clouddoc.md`: 同上
    - `docs/usage/apaas.md`: 同上
    - **更新所有现有示例**:
      - 添加 app_id 参数说明 (现在是可选的)
      - 提供单应用场景的简化示例
      - 提供多应用场景的对比示例

  - **📚 更新 docs/index.rst**:
    - 在 "使用指南" toctree 中添加 `usage/app-management` (在 auth 之后)
    - 验证 toctree 顺序合理

  - **📚 构建并验证文档**:
    ```bash
    cd docs
    make clean
    make html
    # 检查 _build/html/ 输出
    # 验证: 0 警告, 所有链接正常, 示例代码高亮正确
    ```

  - **📚 逐一验证所有新增示例代码**:
    - 创建临时测试脚本,复制每个示例代码
    - 运行验证语法正确、导入成功、API 调用准确
    - 记录验证结果 (哪些示例已验证,哪些需要调整)

  - 验证: 文档清晰完整,Sphinx 构建 0 警告,**所有示例代码已逐一验证可运行**

### Checkpoint
- ✅ Docker 镜像 < 500MB (已在 CI/CD 中强制检查)
- ✅ docker-compose.yml 包含完整的生产环境服务(PostgreSQL, RabbitMQ, Prometheus, Grafana)
- ✅ GitHub Actions CI/CD 完整流程包含 build, verify, deploy 阶段
- ✅ Prometheus + Grafana 监控配置完整,仪表板已创建
- ✅ CHANGELOG.md 已更新 Phase 2 内容
- ✅ requirements.txt 添加 prometheus-client 依赖

---

## Phase 3: 稳定性增强 (US4 - API 限流和重试机制)

**Phase Goal**: 实现 API 限流、aPaaS 自动重试、定时任务调度

**Priority**: P2

**Independent Test Criteria**:
- [ ] API 限流准确率 100%(限流器单元测试)
- [ ] aPaaS 客户端在 Token 过期时自动重试成功率 ≥ 95%
- [ ] 定时任务按预期调度执行
- [ ] 所有新增代码测试覆盖率 ≥ 85%

### Tasks

- [ ] T009 [P] [US4] **实现 RateLimiter 和 aPaaS 重试逻辑** (并行任务)
  - **实现 RateLimiter** (`src/lark_service/core/rate_limiter.py`):
    - 滑动窗口算法
    - `is_allowed(user_id)` 方法
    - `record_request(user_id)` 方法
    - 配置: window_size=60秒, max_requests=5
    - 编写单元测试 `tests/unit/core/test_rate_limiter.py`
  - **集成限流到 AuthSessionManager** (`src/lark_service/websocket/auth_session_manager.py`):
    - 在用户授权请求处添加限流检查
    - 超限时返回 429 错误
    - 记录限流事件到日志和 Prometheus
  - **实现 aPaaS 自动重试** (`src/lark_service/apaas/client.py`):
    - 实现 `_call_apaas_api_with_retry()` 方法
    - 检测 401 错误时自动刷新 Token
    - 最多重试 3 次,使用指数退避(1s, 2s, 4s)
    - 记录重试事件到日志和 Prometheus
  - 验证: 单元测试通过,集成测试验证限流和重试

- [ ] T010 [P] [US4] **实现定时任务和 Token UX 优化** (并行任务)
  - **实现用户信息同步定时任务** (`src/lark_service/tasks/sync_user_info.py`):
    - 使用 APScheduler
    - 定时策略: 每日凌晨 2 点执行
    - 批量同步用户信息
    - 错误处理和日志记录
  - **实现 Token 过期 UX** (`src/lark_service/websocket/card_auth_handler.py`):
    - 检测 Token 即将过期(< 10% 生命周期或 < 1小时)
    - 自动发送新的授权卡片
    - 防止重复发送(1小时内最多1次)
    - 友好提示消息: "您的授权已过期,请重新授权以继续使用"
  - 验证: 手动测试定时任务触发,模拟 Token 过期场景

### Checkpoint
- ✅ API 限流功能正常,准确率 100%
- ✅ aPaaS 客户端自动重试成功率 ≥ 95%
- ✅ 定时任务按预期调度
- ✅ Token 过期 UX 友好

---

## Phase 4: 测试完整性和手动验证 (US6 - 交叉验证)

**Phase Goal**: 扩展集成测试,完成真实飞书账号手动测试,确保端到端功能正常

**Priority**: P2

**Independent Test Criteria**:
- [ ] Token 刷新重试集成测试通过
- [ ] 真实飞书账号手动测试至少完成 1 次端到端验证
- [ ] 整体测试覆盖率 ≥ 85%
- [ ] 所有 P1/P2 任务完成

### Tasks

- [ ] T011 [US6] **扩展集成测试** (`tests/integration/`)
  - **Token 刷新重试测试** (`test_token_refresh_retry.py`):
    - 模拟 401 错误,验证自动刷新 Token
    - 模拟刷新失败,验证重试逻辑
    - 验证使用缓存 Token 继续服务(如未过期)
  - **限流集成测试** (`test_rate_limiting.py`):
    - 快速连续发送请求,触发限流
    - 验证 429 错误返回
    - 验证滑动窗口算法准确性
  - **并发应用切换测试** (`test_concurrent_app_switching.py`):
    - 验证工厂方法创建的客户端完全隔离
    - 验证显式参数的线程安全性
  - 验证: 所有集成测试通过

- [ ] T012 [US6] **真实飞书账号手动测试** (依赖 T001-T011)
  - 准备测试环境:
    - 申请测试飞书账号和应用
    - 配置测试环境的 .env 文件
    - 部署测试服务到内网或公网
  - **执行端到端测试场景**:
    - 场景 1: 单应用消息发送(Text, Image, Card)
    - 场景 2: 多应用切换(工厂方法和上下文管理器)
    - 场景 3: WebSocket 用户授权流程(卡片授权 → Token 获取)
    - 场景 4: Token 过期自动刷新
    - 场景 5: API 限流触发
    - 场景 6: aPaaS 数据操作(CRUD、SQL 查询)
  - **记录测试结果** (`docs/manual-test-report-003.md`):
    - 测试时间、环境信息
    - 每个场景的测试步骤和结果(成功/失败)
    - 截图或日志证据
    - 发现的问题和解决方案
  - 验证: 至少 90% 的场景测试通过

- [ ] T013 [US6] **最终代码质量检查和文档完善** (依赖 T012)
  - **代码质量检查**:
    - 运行 `ruff format .` 格式化所有代码
    - 运行 `ruff check src/ tests/` 修复所有警告
    - 运行 `mypy src/` 确保 0 错误
    - 运行 `pytest tests/ --cov=src --cov-report=html` 生成覆盖率报告
    - 验证: 覆盖率 ≥ 85%
  - **📚 Docstring 审查和 API 文档最终检查**:
    - **审查所有新增和修改的类/方法的 Docstring**:
      - 格式符合宪章标准 (简要描述、Args、Returns、Raises、Example)
      - Example 部分使用 doctest 格式,代码可运行
      - 英文表述清晰准确
    - **重新生成完整 API 文档**:
      ```bash
      cd docs
      sphinx-apidoc -f -o api/ ../src/lark_service/
      make clean
      make html
      ```
    - **检查生成的 HTML**:
      - 打开 `docs/_build/html/index.html`
      - 导航到新增模块 (BaseServiceClient, CredentialPool, ApplicationManager)
      - 验证所有方法文档清晰完整
      - 验证 Example 代码高亮正确
      - 验证内部链接正常工作
    - **运行 doctest (可选)**:
      ```bash
      python -m doctest src/lark_service/core/base_service_client.py -v
      ```
  - **📚 用户文档最终审查和示例验证**:
    - **逐一验证所有文档示例代码**:
      - 创建测试脚本 `scripts/validate_docs_examples.py`
      - 从以下文档提取所有代码示例:
        - `docs/usage/app-management.md`
        - `docs/usage/advanced.md`
        - `docs/usage/messaging.md` (更新的部分)
        - `docs/usage/contact.md` (更新的部分)
        - `docs/usage/clouddoc.md` (更新的部分)
        - `docs/usage/apaas.md` (更新的部分)
      - **验证每个示例**:
        1. 提取代码块
        2. 检查导入语句完整性
        3. 检查 API 调用准确性 (方法名、参数、返回值)
        4. 运行语法检查 (ast.parse)
        5. 如可能,运行实际代码 (或 mock 测试)
      - **记录验证结果** (`docs/examples-validation-report.md`):
        - 已验证的示例列表
        - 发现的问题和修复
        - 所有示例必须标记为 ✅ 已验证
    - **审查文档完整性**:
      - `docs/usage/app-management.md`: 所有章节完整,示例覆盖所有场景
      - `docs/usage/advanced.md`: 不再是空文档,包含高级场景说明
      - `docs/quickstart.md`: 反映最新 API (如需要更新)
      - `docs/deployment.md`: 包含生产部署完整说明 (Docker、监控、CI/CD)
    - **检查文档准确性**:
      - 所有类名、方法名、参数名与实际代码一致
      - 所有导入路径正确
      - 所有返回值类型准确
      - 所有错误处理示例准确
    - **检查 CHANGELOG.md**:
      - v0.3.0 功能列表完整
      - Breaking Changes 说明准确 (无破坏性变更)
      - Migration Guide 清晰 (可选迁移)
  - **性能验证**:
    - 验证 Docker 镜像大小 < 500MB
    - 验证 CI/CD 流程 < 10分钟
    - 验证健康检查响应 < 100ms
  - 验证: 所有质量门禁通过, Sphinx 构建 0 警告, 所有文档示例可运行

- [ ] T014 [US6] **准备发布和部署** (依赖 T013)
  - **Git 提交和标签**:
    - 确保所有更改已提交(遵循 Conventional Commits)
    - 创建 Git tag: `v0.3.0`
    - 推送到 origin: `git push origin 003-code-refactor-optimization --tags`
  - **合并到主分支**:
    - 创建 Pull Request: `003-code-refactor-optimization` → `main`
    - 等待 CI/CD 通过
    - Code Review(如有团队成员)
    - 合并 PR
  - **生产部署准备**:
    - 更新生产环境 .env 文件
    - 备份当前生产数据库
    - 使用 `docker-compose -f docker-compose.prod.yml up -d` 部署
    - 执行健康检查验证
    - 监控 Grafana 仪表板 24 小时
  - 验证: 生产环境稳定运行

### Checkpoint
- ✅ 所有集成测试通过
- ✅ 真实飞书账号手动测试完成
- ✅ 代码质量门禁 100% 通过
- ✅ 测试覆盖率 ≥ 85%
- ✅ 准备好发布 v0.3.0

---

## Dependencies & Execution Order

### Sequential Dependencies

```
Phase 1 (T001 → T002 → T003 → T004)
    ↓ (T001-T004 完成后)
Phase 2 (T005 ∥ T006 → T007 → T008)
    ↓ (T005-T008 完成后)
Phase 3 (T009 ∥ T010)
    ↓ (T001-T010 完成后)
Phase 4 (T011 → T012 → T013 → T014)
```

### Parallel Execution Opportunities

**Phase 1 内部**:
- T002 可与 T001 的单元测试编写并行

**Phase 2 内部**:
- T005 (Docker) 和 T006 (CI/CD) 可完全并行
- T007 (监控) 和 T008 (文档) 依赖 T005/T006 但可与对方并行

**Phase 3 内部**:
- T009 (限流+重试) 和 T010 (定时任务+Token UX) 可完全并行

**跨 Phase 并行**:
- Phase 2 可在 Phase 1 的 T003 完成后开始(无需等待 T004)
- Phase 3 可在 Phase 1 完成后立即开始(与 Phase 2 并行)

### Critical Path

```
T001 → T002 → T003 → T011 → T012 → T013 → T014
```

最短完成时间约 **3-4 周** (假设并行执行和每任务 2-3 天)

---

## Success Criteria Summary

### Phase 1 Success
- ✅ 单应用场景代码行数减少 30%
- ✅ 多应用场景有 4 种切换方式可用
- ✅ 向后兼容: 现有测试 100% 通过
- ✅ 测试覆盖率 ≥ 85%

### Phase 2 Success
- ✅ Docker 镜像 < 500MB
- ✅ CI/CD 流程 < 10分钟
- ✅ 生产环境一键启动
- ✅ 监控和告警正常工作

### Phase 3 Success
- ✅ API 限流准确率 100%
- ✅ Token 刷新成功率 ≥ 98%
- ✅ 定时任务按预期调度

### Phase 4 Success
- ✅ 真实飞书账号测试通过率 ≥ 90%
- ✅ 整体测试覆盖率 ≥ 85%
- ✅ 生产环境稳定运行

---

## Implementation Notes

### 重构策略

1. **增量重构**: Phase 1 的 T003 按客户端逐个重构,每个客户端重构后立即运行测试
2. **TDD**: 每个任务遵循红-绿-重构循环
3. **向后兼容检查**: 每个 Phase 完成后运行完整测试套件
4. **持续集成**: 每次提交触发 CI,及早发现问题

### 📚 文档管理策略 (重要)

**文档系统**: Sphinx + reStructuredText (.rst)

**关键注意事项**:

1. **Docstring 标准严格遵守**:
   - 所有新增/修改的类和方法必须包含完整 Docstring
   - 格式: 简要描述 + Args + Returns + Raises + Example
   - Example 部分使用 doctest 格式 (`>>>`) ,确保代码可运行
   - 英文表述,清晰准确
   - Sphinx 会自动提取 Docstring 生成 API 文档

2. **API 文档同步更新**:
   - 每完成一个模块重构,立即重新生成 API 文档:
     ```bash
     sphinx-apidoc -f -o docs/api/ src/lark_service/
     ```
   - 检查生成的 `.rst` 文件,确保新增模块被包含

3. **用户文档示例必须可运行**:
   - `docs/usage/app-management.md` 中的所有示例代码必须:
     - 语法正确
     - API 调用准确
     - 导入路径正确
     - 最好提供完整的可运行示例
   - 在 T013 任务中逐一验证所有示例

4. **Sphinx 构建验证**:
   - 每个 Phase 完成后构建文档:
     ```bash
     cd docs
     make clean
     make html
     ```
   - 检查构建输出,确保 **0 警告**
   - 打开 `_build/html/index.html` 验证显示正确

5. **文档与代码同步**:
   - 代码修改 → Docstring 更新 → API 文档重新生成
   - 不允许代码和文档不一致
   - Code Review 时必须检查文档完整性

6. **示例代码质量标准**:
   - **完整的导入语句**: 每个示例必须包含所有必要的导入
     ```python
     # ✅ 正确: 完整导入
     from lark_service.core.credential_pool import CredentialPool
     from lark_service.messaging.client import MessagingClient

     pool = CredentialPool(...)
     client = MessagingClient(pool, app_id="cli_xxx")

     # ❌ 错误: 缺少导入
     pool = CredentialPool(...)  # 从哪里来的?
     ```

   - **真实的 API 调用**: 不能使用伪代码或占位符
     ```python
     # ✅ 正确: 真实方法名和参数
     client.send_text_message(receiver_id="ou_xxx", text="Hello")

     # ❌ 错误: 伪代码
     client.send_message(...)  # 什么参数?
     ```

   - **准确的类型和返回值**:
     ```python
     # ✅ 正确: 准确的返回值
     current = client.get_current_app_id()  # → str | None
     if current:
         print(f"Current app: {current}")

     # ❌ 错误: 不清楚返回值
     current = client.get_current_app_id()
     print(current)  # 可能是 None,会出错吗?
     ```

   - **完整的错误处理**: 示例中的异常处理必须准确
     ```python
     # ✅ 正确: 准确的异常类型
     try:
         client.send_text_message(receiver_id="ou_xxx", text="Hello")
     except ConfigError as e:
         print(f"Configuration error: {e}")

     # ❌ 错误: 错误的异常类型
     except ValueError as e:  # 实际抛出的是 ConfigError
         pass
     ```

7. **示例验证流程** (在 T008 和 T013 任务中执行):

   **步骤 1: 提取所有示例代码**
   - 从所有 `.md` 文档中提取 Python 代码块
   - 记录每个示例的来源 (文件名、行号)

   **步骤 2: 语法验证**
   ```python
   import ast

   def validate_syntax(code: str) -> bool:
       try:
           ast.parse(code)
           return True
       except SyntaxError as e:
           print(f"Syntax error: {e}")
           return False
   ```

   **步骤 3: 导入验证**
   - 检查所有 `from ... import ...` 语句
   - 验证模块路径存在
   - 验证类名/函数名正确

   **步骤 4: API 调用验证**
   - 检查方法名是否存在
   - 检查参数是否正确 (必需参数、可选参数)
   - 检查返回值类型是否准确

   **步骤 5: 记录验证结果**
   ```markdown
   # 示例验证报告

   ## docs/usage/app-management.md
   - ✅ 示例 1 (行 45-52): 单应用场景 - 已验证
   - ✅ 示例 2 (行 67-75): 多应用工厂方法 - 已验证
   - ❌ 示例 3 (行 89-95): 错误处理 - 导入缺失 → 已修复
   - ✅ 示例 3 (行 89-95): 错误处理 - 重新验证通过

   ## 总计
   - 验证通过: 25/25
   - 发现并修复: 3 个问题
   ```

8. **文档补充优先级**:
   - **P0 (必须)**:
     - `docs/usage/app-management.md` (新功能核心文档)
     - 所有 Docstring (API 文档基础)
     - 现有文档的应用管理说明更新
   - **P1 (重要)**:
     - `docs/usage/advanced.md` (高级场景)
     - `docs/deployment.md` (生产部署)
     - CHANGELOG.md (版本记录)
   - **P2 (建议)**:
     - 更多完整的端到端示例
     - 故障排查指南
     - 性能优化技巧

### 风险缓解

| 风险 | 缓解措施 | 负责任务 |
|------|---------|---------|
| 重构引入回归 | 保留现有 API,完整测试套件 | T003, T004 |
| Docker 镜像过大 | 多阶段构建,仅打包运行时依赖 | T005 |
| CI/CD 流程过长 | 并行执行测试,使用缓存 | T006 |
| 限流算法误判 | 成熟的滑动窗口算法,单元测试 | T009 |
| 手动测试受限 | 提前申请测试账号和应用 | T012 |

### 性能目标

| 指标 | 目标 | 验证任务 |
|------|------|---------|
| Docker 镜像大小 | < 500MB | T005 |
| 容器启动时间 | < 30秒 | T005 |
| CI/CD 流程时间 | < 10分钟 | T006 |
| 健康检查响应 | < 100ms | T006 |
| app_id 解析 | < 1μs | T001 |
| 限流检查 | < 10μs | T009 |
| 测试覆盖率 | ≥ 85% | T013 |

---

## Next Steps

1. **立即开始**:
   ```bash
   /speckit.implement
   ```
   按照任务顺序逐步实施,遵循 TDD 原则。

2. **定期检查点**: 每个 Phase 完成后:
   - 运行完整测试套件
   - 更新 CHANGELOG.md
   - 创建 Git commit (Conventional Commits)
   - 推送到远程分支

3. **最终发布**: Phase 4 完成后:
   - 创建 Pull Request
   - Code Review
   - 合并到 main
   - 创建 Git tag v0.3.0
   - 部署到生产环境

---

## 📚 Documentation Checklist (每个 Phase 完成后检查)

### Phase 1 文档检查
- [ ] BaseServiceClient 的所有方法都有完整 Docstring (符合宪章标准)
- [ ] CredentialPool 新增方法都有完整 Docstring
- [ ] ApplicationManager 新增方法都有完整 Docstring
- [ ] 运行 `sphinx-apidoc -f -o docs/api/ src/lark_service/` 成功
- [ ] 运行 `cd docs && make html` 无警告
- [ ] 检查 `docs/_build/html/api/lark_service.core.html` 包含 base_service_client 模块

### Phase 2 文档检查
- [ ] `docs/usage/app-management.md` 创建完成,内容完整
- [ ] `docs/usage/advanced.md` 补充完成,不再是空文档
- [ ] `docs/index.rst` 更新,包含新增的使用指南
- [ ] **所有示例代码质量检查**:
  - [ ] 每个示例都包含完整的导入语句
  - [ ] 使用真实的类名和方法名 (不是伪代码)
  - [ ] 参数类型和返回值准确
  - [ ] 语法正确 (使用 `ast.parse()` 验证)
  - [ ] 导入路径准确 (使用 `importlib` 验证)
- [ ] `docs/usage/messaging.md` 等现有文档更新,添加应用管理说明
- [ ] `CHANGELOG.md` v0.3.0 版本记录完整
- [ ] `README.md` 更新,包含快速开始链接
- [ ] 运行 `cd docs && make html` 无警告
- [ ] 打开 `docs/_build/html/usage/app-management.html` 验证显示正确
- [ ] 打开 `docs/_build/html/usage/advanced.html` 验证内容完整

### Phase 3 文档检查
- [ ] RateLimiter 类有完整 Docstring
- [ ] 定时任务相关函数有完整 Docstring
- [ ] Token UX 相关方法有完整 Docstring
- [ ] 运行 `sphinx-apidoc -f -o docs/api/ src/lark_service/` 成功
- [ ] 运行 `cd docs && make html` 无警告

### Phase 4 文档检查 (最终)
- [ ] 所有新增/修改的类和方法的 Docstring 审查完成
- [ ] 所有 Docstring 的 Example 部分代码可运行
- [ ] 运行 `sphinx-apidoc -f -o docs/api/ src/lark_service/` 成功
- [ ] 运行 `cd docs && make clean && make html` **0 警告**
- [ ] 手动检查 `docs/_build/html/` 输出:
  - [ ] 导航到所有新增模块页面,验证显示正确
  - [ ] 检查示例代码高亮
  - [ ] 验证内部链接正常工作
  - [ ] 检查搜索功能正常
- [ ] **文档示例代码最终验证** (必须):
  - [ ] 运行 `scripts/validate_docs_examples.py` (如已创建)
  - [ ] 或手动逐一验证所有文档中的代码示例
  - [ ] 验证结果记录到 `docs/examples-validation-report.md`
  - [ ] **所有示例必须标记为 ✅ 已验证**
  - [ ] 发现的问题已修复并重新验证
- [ ] **文档完整性检查**:
  - [ ] `docs/usage/app-management.md`: 内容完整,所有示例已验证
  - [ ] `docs/usage/advanced.md`: 内容完整,不再是空文档,所有示例已验证
  - [ ] `docs/usage/messaging.md`: 已更新,示例准确
  - [ ] `docs/usage/contact.md`: 已更新,示例准确
  - [ ] `docs/usage/clouddoc.md`: 已更新,示例准确
  - [ ] `docs/usage/apaas.md`: 已更新,示例准确
  - [ ] `docs/quickstart.md`: 已更新 (如需要),示例准确
  - [ ] `docs/deployment.md`: 包含生产部署完整说明
- [ ] **文档准确性检查**:
  - [ ] 所有类名、方法名与实际代码一致
  - [ ] 所有导入路径正确
  - [ ] 所有参数类型和返回值准确
  - [ ] 所有错误处理示例准确
- [ ] `CHANGELOG.md` 检查完整性和准确性
- [ ] 运行 doctest (可选): `python -m doctest src/lark_service/core/base_service_client.py -v`

### 最终文档交付物
- [ ] API 文档: `docs/_build/html/api/lark_service.core.html` 等
- [ ] 用户指南: `docs/_build/html/usage/app-management.html` (新增)
- [ ] 高级用法: `docs/_build/html/usage/advanced.html` (补充完成)
- [ ] 完整 HTML 文档: `docs/_build/html/index.html`
- [ ] CHANGELOG: v0.3.0 版本记录
- [ ] README: 更新了快速开始和部署说明
- [ ] **示例验证报告**: `docs/examples-validation-report.md` (所有示例 ✅ 已验证)

### 建议: 创建示例验证脚本 (可选,但强烈推荐)

**脚本**: `scripts/validate_docs_examples.py`

**功能**:
1. 扫描 `docs/` 目录下所有 `.md` 文件
2. 提取所有 Python 代码块 (```python ... ```)
3. 对每个代码块执行:
   - 语法验证 (ast.parse)
   - 导入验证 (检查模块路径)
   - API 调用验证 (检查方法名和参数)
4. 生成验证报告 (Markdown 格式)

**使用方法**:
```bash
# 验证所有文档示例
python scripts/validate_docs_examples.py

# 验证特定文档
python scripts/validate_docs_examples.py docs/usage/app-management.md

# 生成详细报告
python scripts/validate_docs_examples.py --verbose --output docs/examples-validation-report.md
```

**示例输出**:
```
Validating docs/usage/app-management.md...
  ✅ Example 1 (lines 45-52): Single app scenario
  ✅ Example 2 (lines 67-75): Factory method
  ❌ Example 3 (lines 89-95): Missing import: ConfigError

Validating docs/usage/advanced.md...
  ✅ Example 1 (lines 23-35): Dynamic app selection
  ✅ Example 2 (lines 48-62): Custom strategy

Summary:
  Total examples: 25
  Passed: 24
  Failed: 1

Failed examples:
  1. docs/usage/app-management.md:89-95 - Missing import
```

**实现建议** (可在 T008 任务中创建):
```python
#!/usr/bin/env python3
"""
Validate code examples in documentation files.
"""
import ast
import re
from pathlib import Path
from typing import List, Tuple

def extract_python_blocks(file_path: Path) -> List[Tuple[int, int, str]]:
    """Extract Python code blocks from Markdown file."""
    content = file_path.read_text()
    pattern = r'```python\n(.*?)```'
    blocks = []
    for match in re.finditer(pattern, content, re.DOTALL):
        code = match.group(1)
        start_line = content[:match.start()].count('\n') + 1
        end_line = start_line + code.count('\n')
        blocks.append((start_line, end_line, code))
    return blocks

def validate_syntax(code: str) -> Tuple[bool, str]:
    """Validate Python syntax."""
    try:
        ast.parse(code)
        return True, "OK"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

def validate_imports(code: str) -> Tuple[bool, str]:
    """Validate import statements."""
    # Check for lark_service imports
    imports = re.findall(r'from (lark_service\.\S+) import', code)
    for module in imports:
        # In real implementation, check if module exists
        pass
    return True, "OK"

def main():
    docs_dir = Path("docs/usage")
    for md_file in docs_dir.glob("*.md"):
        print(f"\nValidating {md_file}...")
        blocks = extract_python_blocks(md_file)
        for start, end, code in blocks:
            valid, msg = validate_syntax(code)
            status = "✅" if valid else "❌"
            print(f"  {status} Lines {start}-{end}: {msg}")

if __name__ == "__main__":
    main()
```

---

**Tasks Status**: ✅ Ready for Implementation
**Total Phases**: 4
**Total Tasks**: 14
**Documentation Tasks**: 贯穿所有 Phase,每个 Phase 完成后检查
**Estimated Duration**: 3-4 weeks (with parallel execution)
**Last Updated**: 2026-01-21
