# 开发工作流指南

## 🔍 代码质量检查工作流

### 问题：传统 Git 工作流的痛点

传统工作流：
```bash
git add file.py          # 添加文件
git commit -m "fix"      # 提交 → pre-commit hook 报格式错误 ❌
# 需要修复后重新 add + commit，可能产生循环
```

**痛点**：
- ❌ 在 commit 时才发现格式问题
- ❌ pre-commit hook 自动修改文件导致循环
- ❌ 需要反复 add → commit → 失败 → 修复

---

## ✅ 新的智能工作流

### 核心改进

**3步式流程**：`Format → Add → Check`

```bash
# 使用智能脚本（推荐）
./scripts/git-add-check.sh src/file.py

# 或使用 git alias
git cadd src/file.py
```

**工作原理**：
1. **Step 1**: 自动检测格式问题并 format
2. **Step 2**: 添加文件到 staging area
3. **Step 3**: 运行所有质量检查（ruff-format 现在是 --check 模式）

**优势**：
- ✅ 在 add 前就自动格式化（避免循环）
- ✅ Pre-commit hooks 只检查，不修改
- ✅ 清晰的 3 步流程，易于理解
- ✅ 一次命令完成所有操作

---

## ✅ 推荐方案：使用 `git-add-check.sh`

### 方案 A：使用脚本（推荐）

#### 1. 基本使用

```bash
# 替代 git add，自动运行检查
./scripts/git-add-check.sh src/lark_service/apaas/client.py

# 支持多个文件
./scripts/git-add-check.sh src/file1.py src/file2.py tests/test_file.py

# 使用通配符
./scripts/git-add-check.sh src/lark_service/apaas/*.py
```

#### 2. 工作流演示

```bash
# Step 1: 修改代码
vim src/lark_service/apaas/client.py

# Step 2: 添加并检查
./scripts/git-add-check.sh src/lark_service/apaas/client.py

# 如果检查失败 ❌
# → 修复代码
# → 重新运行脚本
./scripts/git-add-check.sh src/lark_service/apaas/client.py

# 如果检查通过 ✅
# → 直接提交
git commit -m "feat: add new feature"
```

#### 3. 创建快捷别名（可选）

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
# Git add with checks
alias gadd='./scripts/git-add-check.sh'
alias gac='./scripts/git-add-check.sh'
```

重新加载配置：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

使用：
```bash
gadd src/file.py
gac tests/test_file.py
```

---

### 方案 B：使用 Git Alias

#### 1. 设置 alias

```bash
# 全局设置（所有项目生效）
git config --global alias.cadd '!f() { git add "$@" && pre-commit run --files "$@"; }; f'

# 或仅本项目
cd /home/ray/Documents/Files/LarkServiceCursor
git config alias.cadd '!f() { git add "$@" && pre-commit run --files "$@"; }; f'
```

#### 2. 使用

```bash
# 替代 git add
git cadd src/lark_service/apaas/client.py

# 检查失败后，修复并重新运行
git cadd src/lark_service/apaas/client.py

# 检查通过后提交
git commit -m "message"
```

---

### 方案 C：手动检查（最灵活）

```bash
# 1. 正常添加文件
git add src/lark_service/apaas/client.py

# 2. 手动运行检查（只检查 staged 文件）
pre-commit run

# 3. 如果失败，修复后重新运行
# 文件仍然在 staged 状态，不需要重新 add
pre-commit run

# 4. 检查通过后提交
git commit -m "message"
```

---

## 🎯 检查工具说明

### Pre-commit 检查项

当前项目配置了以下检查（`.pre-commit-config.yaml`）：

1. **Ruff** - Python linting
   - 代码风格检查
   - 常见错误检测
   - 导入排序

2. **Ruff Format** - Python formatting
   - 自动代码格式化
   - 统一代码风格

3. **Mypy** - 类型检查
   - 静态类型分析
   - 类型注解验证

4. **Bandit** - 安全扫描
   - 安全漏洞检测
   - 敏感信息检查

5. **其他**
   - 尾随空格清理
   - 文件末尾换行
   - YAML 格式检查
   - 大文件检测
   - 合并冲突检测
   - 私钥检测

### 手动运行特定检查

```bash
# 只运行 ruff
pre-commit run ruff --files src/file.py

# 只运行 mypy
pre-commit run mypy --files src/file.py

# 只运行 ruff-format
pre-commit run ruff-format --files src/file.py

# 运行所有检查（包括未 staged 的文件）
pre-commit run --all-files
```

---

## 🚀 最佳实践

### 1. 开发前检查环境

```bash
# 确保 pre-commit 已安装
pre-commit --version

# 确保 hooks 已安装
pre-commit install
```

### 2. 修改代码后立即检查

```bash
# 推荐：使用脚本
./scripts/git-add-check.sh <modified-files>

# 或者：手动检查
git add <files>
pre-commit run
```

### 3. 提交前最后检查

```bash
# 检查所有 staged 文件
pre-commit run

# 或检查所有文件
pre-commit run --all-files
```

### 4. CI/CD 一致性

本地的 pre-commit 检查与 GitHub Actions CI/CD 使用相同的工具和配置，确保：
- ✅ 本地通过 → CI/CD 也会通过
- ✅ 避免提交后 CI 失败
- ✅ 节省 CI/CD 运行时间

---

## 🛠️ 故障排查

### 问题 1：Pre-commit hook 未生效

```bash
# 重新安装 hooks
pre-commit uninstall
pre-commit install

# 验证安装
ls -la .git/hooks/pre-commit
```

### 问题 2：检查工具版本不一致

```bash
# 更新 pre-commit 配置
pre-commit autoupdate

# 清理缓存
pre-commit clean

# 重新安装
pre-commit install --install-hooks
```

### 问题 3：跳过检查（紧急情况）

```bash
# 跳过 pre-commit hooks（不推荐）
git commit --no-verify -m "message"

# 或使用环境变量
SKIP=ruff,mypy git commit -m "message"
```

⚠️ **注意**：只在紧急情况下跳过检查，记得后续修复！

---

## 📚 相关文档

- Pre-commit 配置: `.pre-commit-config.yaml`
- Git hooks 路径: `.git/hooks/`
- 代码质量标准: `@.specify/memory/constitution.md`
- Ruff 配置: `pyproject.toml` (tool.ruff)
- Mypy 配置: `pyproject.toml` (tool.mypy)
- Bandit 配置: `pyproject.toml` (tool.bandit)

---

## 💡 推荐工作流总结

```bash
# 1. 修改代码
vim src/lark_service/apaas/client.py

# 2. 添加并检查（使用脚本）
./scripts/git-add-check.sh src/lark_service/apaas/client.py

# 3a. 如果检查失败 → 修复后重新运行脚本
# 3b. 如果检查通过 → 提交
git commit -m "feat: implement new feature"

# 4. 推送到远程
git push origin feature-branch
```

**优点**：
- ✅ 在 add 后立即发现问题
- ✅ 文件保持 staged 状态，修复后无需重新 add
- ✅ 与 CI/CD 保持一致
- ✅ 提高代码质量
- ✅ 节省时间
