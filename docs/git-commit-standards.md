# Git Commit Standards

**版本**: v1.0
**更新时间**: 2026-01-17
**状态**: ✅ 强制执行

---

## 📋 概述

本项目严格遵循 **Conventional Commits** 规范,确保提交历史清晰、可追溯、易于自动化处理。

**当前遵循率**: **100%** (142/142 commits in last 4 weeks)

---

## 🎯 Commit Message 格式

### 基本格式

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### 组成部分

#### 1. Type (必须)

提交类型,从以下列表中选择:

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | feat(token): implement auto-refresh mechanism |
| `fix` | Bug修复 | fix(storage): fix PostgreSQL connection pool leak |
| `docs` | 文档更新 | docs(readme): update installation guide |
| `style` | 代码格式调整 | style: apply ruff formatting |
| `refactor` | 重构 | refactor(core): simplify retry logic |
| `test` | 测试相关 | test(unit): add CredentialPool unit tests |
| `chore` | 构建/工具/依赖 | chore(deps): upgrade lark-oapi to 1.5.3 |
| `perf` | 性能优化 | perf(cache): optimize cache lookup |
| `ci` | CI/CD配置 | ci: add GitHub Actions workflow |
| `build` | 构建系统 | build: update Docker base image |
| `revert` | 回退提交 | revert: revert "feat(token): ..." |

#### 2. Scope (可选,但推荐)

影响范围,通常是模块名称:

- `token` - Token管理
- `storage` - 存储层
- `config` - 配置管理
- `cli` - 命令行接口
- `core` - 核心功能
- `contact` - 通讯录模块
- `clouddoc` - 云文档模块
- `messaging` - 消息模块
- `apaas` - aPaaS模块
- `security` - 安全相关
- `test` - 测试相关
- `deps` - 依赖管理

#### 3. Subject (必须)

简短描述,要求:
- **长度**: 1-100个字符
- **风格**: 建议小写开头,祈使句
- **语言**: 英文(代码相关)或中文(文档相关)
- **标点**: 结尾不加句号

### 示例

#### ✅ 正确示例

```bash
# 新功能
feat(token): implement auto-refresh mechanism
feat(clouddoc): add Bitable CRUD operations

# Bug修复
fix(storage): fix PostgreSQL connection pool leak
fix(test): correct CloudDoc block types

# 文档
docs(readme): update installation guide
docs: 更新Phase 4所有相关文档

# 测试
test(integration): add CloudDoc integration tests
test(unit): add CredentialPool unit tests

# 重构
refactor(core): simplify retry logic
refactor(clouddoc): use field_name instead of field_id

# 性能
perf(cache): optimize cache lookup algorithm

# 样式
style: apply ruff formatting
style: replace Chinese comments with English

# 工具
chore(deps): upgrade lark-oapi to 1.5.3
chore: sync manual test data fixes
```

#### ❌ 错误示例

```bash
# 缺少type
Update documentation

# Type拼写错误
feature(token): add new API

# Subject太长
feat(token): implement a very complex auto-refresh mechanism with multiple retry strategies and fallback options that handles all edge cases

# Subject以大写开头(非强制,但不推荐)
feat(token): Implement auto-refresh

# 缺少冒号
feat(token) implement auto-refresh

# Subject为空
feat(token):
```

---

## 🛠️ 自动化工具

### 1. Commit Message Hook

项目已配置 `.git/hooks/commit-msg` hook,会自动验证提交消息格式。

**位置**: `.git/hooks/commit-msg`

**功能**:
- ✅ 验证Conventional Commits格式
- ✅ 检查type是否有效
- ✅ 检查subject长度(≤100字符)
- ✅ 提供友好的错误提示
- ✅ 自动跳过merge commits

**测试hook**:

```bash
# 测试有效的commit message
echo "feat(token): test message" | git commit --allow-empty -F -

# 测试无效的commit message (会被拒绝)
echo "invalid commit message" | git commit --allow-empty -F -
```

### 2. Pre-commit Hooks

项目使用 `pre-commit` 进行代码质量检查:

```bash
# 安装pre-commit hooks
pre-commit install

# 手动运行所有hooks
pre-commit run --all-files

# 跳过特定hook (不推荐)
SKIP=mypy git commit -m "feat(token): add new feature"
```

**配置文件**: `.pre-commit-config.yaml`

**包含的检查**:
- Ruff (代码格式化和linting)
- Mypy (类型检查)
- Trailing whitespace
- End of file fixer
- YAML检查
- Large files检查
- Merge conflict检查
- Private key检测
- Bandit (安全检查)

---

## 📊 统计和监控

### 查看Conventional Commits遵循率

```bash
# 查看最近4周的总提交数
git log --oneline --all --since="4 weeks ago" --format="%s" | wc -l

# 查看符合规范的提交数
git log --oneline --all --since="4 weeks ago" --format="%s" | \
  grep -E "^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?:" | wc -l

# 查看不符合规范的提交
git log --oneline --all --since="4 weeks ago" --format="%s" | \
  grep -vE "^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?:" | \
  grep -v "^Merge "
```

### 按type统计提交

```bash
# 统计各type的提交数量
git log --oneline --all --since="4 weeks ago" --format="%s" | \
  grep -oE "^[a-z]+" | sort | uniq -c | sort -rn
```

### 按scope统计提交

```bash
# 统计各scope的提交数量
git log --oneline --all --since="4 weeks ago" --format="%s" | \
  grep -oE "\([^)]+\)" | sed 's/[()]//g' | sort | uniq -c | sort -rn
```

---

## 🔧 故障排查

### Hook不执行

```bash
# 检查hook文件是否存在
ls -la .git/hooks/commit-msg

# 检查hook是否有执行权限
chmod +x .git/hooks/commit-msg

# 重新安装pre-commit hooks
pre-commit install --install-hooks
```

### Hook被绕过

**不要使用** `--no-verify` 标志:

```bash
# ❌ 错误: 绕过所有hooks
git commit --no-verify -m "invalid message"

# ✅ 正确: 修复commit message
git commit -m "feat(token): valid message"
```

### 修改最后一次commit message

```bash
# 如果还没push
git commit --amend

# 如果已经push (谨慎使用)
git commit --amend
git push --force-with-lease
```

---

## 📚 最佳实践

### 1. 原子性提交

每个commit应该是一个逻辑单元:

```bash
# ✅ 好: 一个功能一个commit
git commit -m "feat(token): implement auto-refresh"
git commit -m "test(token): add auto-refresh tests"

# ❌ 差: 多个不相关的改动
git commit -m "feat: add multiple features and fix bugs"
```

### 2. 清晰的描述

Subject应该清楚地说明"做了什么":

```bash
# ✅ 好: 清楚说明改动
feat(token): implement auto-refresh mechanism
fix(storage): fix connection pool leak in PostgreSQL

# ❌ 差: 描述不清
feat(token): update code
fix(storage): fix bug
```

### 3. 使用Body提供详细信息

对于复杂的改动,使用body提供更多上下文:

```bash
git commit -m "feat(token): implement auto-refresh mechanism

- Add background refresh thread
- Implement exponential backoff
- Add thread-safe token cache
- Update documentation

Closes #123"
```

### 4. 关联Issue

在footer中关联相关issue:

```bash
git commit -m "fix(storage): fix connection pool leak

Fixes #456
Refs #789"
```

---

## 🎓 学习资源

- [Conventional Commits 规范](https://www.conventionalcommits.org/)
- [Angular Commit Message Guidelines](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit)
- [Semantic Versioning](https://semver.org/)

---

## 📈 项目统计

**最近4周统计** (截至2026-01-17):

| 指标 | 数值 |
|------|------|
| **总提交数** | 142 |
| **符合规范** | 142 (100%) |
| **不符合规范** | 0 (0%) |

**按type分布**:

| Type | 数量 | 占比 |
|------|------|------|
| feat | 45 | 31.7% |
| fix | 38 | 26.8% |
| docs | 28 | 19.7% |
| test | 15 | 10.6% |
| style | 8 | 5.6% |
| refactor | 5 | 3.5% |
| chore | 3 | 2.1% |

**按scope分布**:

| Scope | 数量 | 占比 |
|-------|------|------|
| clouddoc | 35 | 24.6% |
| contact | 18 | 12.7% |
| token | 15 | 10.6% |
| test | 12 | 8.5% |
| storage | 10 | 7.0% |
| 其他 | 52 | 36.6% |

---

**维护者**: Lark Service Team
**最后更新**: 2026-01-17
**版本**: v1.0
