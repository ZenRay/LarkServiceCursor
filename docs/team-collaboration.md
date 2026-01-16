# 团队协作指南

**版本**: 1.0.0
**更新时间**: 2026-01-15

---

## 多开发者配置同步 (CHK055)

### 配置文件管理策略

```
项目配置文件层次:
.env.example        → 提交到 Git (配置模板)
.env.development    → 提交到 Git (开发环境示例)
.env.production     → 不提交 (生产环境)
.env                → 不提交 (个人本地配置)
```

### 配置同步流程

**新成员入职**:
```bash
# 1. Clone 项目
git clone <repo-url>
cd lark-service

# 2. 复制配置模板
cp .env.example .env

# 3. 填充必需配置
# 编辑 .env 文件,设置个人密钥

# 4. 从团队密钥管理服务获取测试密钥
# (可选) 使用团队共享的开发环境密钥
```

**配置变更同步**:
```bash
# 开发者 A 添加新配置
echo "NEW_FEATURE_FLAG=true" >> .env.example

# 提交变更
git add .env.example
git commit -m "feat: add NEW_FEATURE_FLAG config"
git push

# 开发者 B 同步
git pull
# 手动添加到个人 .env 文件
echo "NEW_FEATURE_FLAG=true" >> .env
```

## 第三方库封装 (CHK125)

### 封装策略

**问题**: 直接使用第三方库,版本升级可能破坏代码

**解决**: 封装第三方库,隔离版本变更影响

**示例**:
```python
# ❌ 直接使用 (耦合严重)
from lark_oapi import Client
client = Client.builder().build()

# ✅ 封装后使用
from lark_service.core.lark_client import LarkClient
client = LarkClient(config)
```

### 封装模式

```python
# src/lark_service/core/lark_client.py
from lark_oapi import Client as LarkOapiClient

class LarkClient:
    """Wrapper for lark-oapi SDK.

    隔离 lark-oapi 版本变更的影响。
    """
    def __init__(self, app_id: str, app_secret: str):
        self._client = LarkOapiClient.builder()\\
            .app_id(app_id)\\
            .app_secret(app_secret)\\
            .build()

    def fetch_app_token(self) -> str:
        """Fetch app access token.

        如果 SDK API 变更,仅需修改此方法。
        """
        req = self._client.auth.v3.app_access_token.internal\\
            .create()
        resp = req.do()

        if resp.code != 0:
            raise APIError(f"Failed: {resp.msg}")

        return resp.data.app_access_token
```

---

## 🚀 Speckit 工作流最佳实践

### Speckit 命令使用

本项目使用 Speckit 进行功能规范管理和任务跟踪。

#### 核心命令

| 命令 | 用途 | 使用时机 |
|------|------|---------|
| `/speckit.specify` | 创建功能规范 | 开始新功能开发前 |
| `/speckit.plan` | 生成实施计划 | 完成 spec.md 后 |
| `/speckit.tasks` | 生成任务清单 | 完成 plan.md 后 |
| `/speckit.checklist` | 运行检查清单 | PR 提交前/验收时 |
| `/speckit.analyze` | 分析需求 | 需求不清晰时 |
| `/speckit.clarify` | 澄清需求 | 发现歧义时 |

### 完整开发流程

#### 1. 创建功能分支

```bash
# 方式 1: 自动生成分支名 (推荐)
/speckit.specify "Implement messaging service for group chats"
# 输出:
# BRANCH_NAME: 002-messaging-service
# SPEC_FILE: specs/002-messaging-service/spec.md
# FEATURE_NUM: 002

# 方式 2: 指定短名称
/speckit.specify "Add OAuth2 authentication" --short-name "user-auth"
# 输出: 003-user-auth

# 方式 3: 指定分支号 (用于修复特定编号)
/speckit.specify "Fix token refresh bug" --number 1
# 输出: 001-fix-token-refresh
```

**自动创建内容**:
- ✅ Git 分支: `002-messaging-service`
- ✅ Spec 目录: `specs/002-messaging-service/`
- ✅ 规范文件: `spec.md` (从模板创建)

#### 2. 编写功能规范

编辑 `specs/002-messaging-service/spec.md`:

```markdown
# 功能规范: 消息服务

## 功能概述
实现飞书群消息发送功能...

## 功能需求
- FR-001: 支持文本消息发送
- FR-002: 支持图片消息发送
...

## 成功标准
- SC-001: 消息发送成功率 ≥ 99.9%
- SC-002: API 响应时间 P99 ≤ 2s
...
```

**最佳实践**:
- 使用 FR-XXX 编号功能需求
- 使用 SC-XXX 编号成功标准
- 每个需求有清晰的验收标准
- 包含边界条件和异常处理

#### 3. 生成实施计划

```bash
/speckit.plan
# 分析 spec.md,生成 plan.md
```

**生成内容**:
- 技术方案设计
- 模块划分
- 接口定义
- 数据模型
- 实施步骤

**人工审查**:
- 检查技术方案合理性
- 补充架构图
- 添加技术选型说明

#### 4. 生成任务清单

```bash
/speckit.tasks
# 分析 plan.md,生成 tasks.md
```

**生成内容**:
- 任务分解 (T001, T002...)
- 任务优先级
- 任务依赖关系
- 预估工作量

**人工调整**:
- 分配任务负责人
- 调整优先级
- 补充验收标准

#### 5. 开发功能

```bash
# 正常的 Git 工作流
git add .
git commit -m "feat(messaging): 实现消息发送接口"
git commit -m "test(messaging): 添加消息发送单元测试"
git commit -m "docs(messaging): 更新 API 文档"
```

**提交规范** (Conventional Commits):
- `feat(scope): 描述` - 新功能
- `fix(scope): 描述` - Bug 修复
- `docs(scope): 描述` - 文档
- `test(scope): 描述` - 测试
- `refactor(scope): 描述` - 重构

#### 6. 定期同步

```bash
# 同步 main 分支最新代码
git fetch origin main
git rebase origin/main

# 解决冲突 (如有)
git add .
git rebase --continue

# 推送到远程
git push -f origin 002-messaging-service
```

#### 7. 运行检查清单

```bash
# PR 提交前运行
/speckit.checklist

# 检查内容:
# - 功能需求完成度
# - 测试覆盖率
# - 代码质量
# - 文档完整性
# - 安全合规性
```

#### 8. 创建 Pull Request

在 GitHub 创建 PR: `002-messaging-service → main`

**PR 描述模板**:
```markdown
## 功能分支
002-messaging-service

## Spec 目录
specs/002-messaging-service/

## 变更描述
实现飞书群消息发送功能,支持文本、图片、卡片消息。

## Speckit 文档
- [x] spec.md - 需求规范已完成
- [x] plan.md - 实施计划已完成
- [x] tasks.md - 任务清单已完成
- [x] 检查清单已验证通过

## 测试覆盖率
- 单元测试: 85%
- 集成测试: 60%
- 整体: 80%

## 相关 Issue
Closes #42
```

#### 9. 代码审查

**审查者检查**:
1. 阅读 `specs/002-messaging-service/spec.md`
2. 检查 `plan.md` 技术方案
3. 验证 `tasks.md` 任务完成度
4. Review 代码变更
5. 运行测试
6. 提出修改意见

**开发者响应**:
1. 解决评审意见
2. 更新代码
3. 推送修改
4. 回复评论

#### 10. 合并和清理

```bash
# 审查通过后,维护者合并
git checkout main
git merge --no-ff 002-messaging-service
git push origin main

# 可选: 删除功能分支
git branch -d 002-messaging-service
git push origin --delete 002-messaging-service
```

### 多分支协作

#### 场景 1: 多人开发同一功能

```bash
# 开发者 A: 主功能分支
git checkout -b 002-messaging-service

# 开发者 B: 基于主功能分支开发子功能
git checkout 002-messaging-service
git checkout -b 002-messaging-api-integration

# 开发者 B 完成后,先合并到主功能分支
git checkout 002-messaging-service
git merge 002-messaging-api-integration

# 最后统一合并到 main
git checkout main
git merge 002-messaging-service
```

#### 场景 2: 共享 Spec 的修复分支

```bash
# 主功能已合并,发现 Bug
git checkout -b 001-fix-token-refresh

# 使用相同的 spec 目录
ls specs/001-lark-service-core/

# 修复后直接合并到 main
git checkout main
git merge 001-fix-token-refresh
```

#### 场景 3: 长期功能分支

```bash
# Phase 3 是长期功能 (2周+)
git checkout -b 002-messaging-service

# 定期同步 main
git fetch origin main
git rebase origin/main

# 分阶段提交 PR
# PR 1: 002-messaging-service (基础架构)
# PR 2: 002-messaging-api (API 集成)
# PR 3: 002-messaging-ui (UI 集成)
```

### Speckit 文件管理

#### Spec 目录结构

```
specs/002-messaging-service/
  ├── spec.md              # 功能规范 (必需)
  ├── plan.md              # 实施计划 (必需)
  ├── tasks.md             # 任务清单 (必需)
  ├── checklists/          # 检查清单 (可选)
  │   ├── requirements.md
  │   └── phase-completion.md
  ├── research.md          # 技术调研 (可选)
  ├── data-model.md        # 数据模型 (可选)
  ├── quickstart.md        # 快速开始 (可选)
  └── contracts/           # API 契约 (可选)
      ├── api-spec.yaml
      └── examples/
```

#### 文档更新时机

| 文档 | 创建时机 | 更新时机 |
|------|---------|---------|
| `spec.md` | 功能启动时 | 需求变更时 |
| `plan.md` | spec 完成后 | 技术方案调整时 |
| `tasks.md` | plan 完成后 | 任务变更时 |
| `checklists/` | 功能开发中 | 每次 PR 前 |

#### 文档维护原则

1. **单一真相来源**: Spec 目录是需求和计划的唯一来源
2. **及时更新**: 需求变更立即更新文档
3. **版本控制**: 所有文档纳入 Git 版本控制
4. **可追溯性**: 代码提交关联到 spec 中的需求编号

### 团队协作规范

#### 分支命名约定

| 分支类型 | 命名格式 | 示例 |
|---------|---------|------|
| 主功能 | `NNN-<feature>` | `002-messaging-service` |
| 子功能 | `NNN-<feature>-<sub>` | `002-messaging-api-integration` |
| 修复 | `NNN-fix-<issue>` | `001-fix-token-refresh` |
| 实验性 | `NNN-exp-<name>` | `003-exp-new-api` |

#### 提交消息规范

**格式**: `<type>(<scope>): <subject>`

**类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档
- `style`: 格式 (不影响代码运行)
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**范围**: 功能模块 (如 `messaging`, `auth`, `storage`)

**主题**: 简短描述 (≤ 50 字符)

**示例**:
```bash
feat(messaging): 实现群消息发送接口
fix(token): 修复 Token 刷新竞态条件
docs(api): 更新消息发送 API 文档
test(messaging): 添加消息发送单元测试
refactor(storage): 优化数据库连接池
```

#### 代码审查清单

**审查者检查** (参考 [git-workflow.md](./git-workflow.md)):
- [ ] Spec 文档完整 (spec.md, plan.md, tasks.md)
- [ ] 功能需求全部实现
- [ ] 测试覆盖率达标 (≥ 75%)
- [ ] 代码符合规范 (Ruff, Mypy)
- [ ] Docstring 完整 (Google Style)
- [ ] 无安全漏洞
- [ ] 性能符合要求

---

**维护者**: Lark Service Team
**参考**: [Git 工作流](./git-workflow.md) | [CI/CD 流程](./ci-cd.md)
