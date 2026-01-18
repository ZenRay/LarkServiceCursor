# Lark Service - 项目文档索引

**文档总数**: 19个核心文档
**最后整理**: 2026-01-18
**维护者**: Ray

---

## 🎯 快速导航

| 角色 | 推荐文档 |
|------|---------|
| **新手** | [项目交接](project-handoff.md) → [快速参考](quick-reference.md) → [API参考](api_reference.md) |
| **开发者** | [开发环境](development-environment.md) → [测试指南](TESTING-GUIDE.md) → [Git规范](git-commit-standards.md) |
| **运维人员** | [部署指南](deployment.md) → [安全指南](security-guide.md) → [可观测性](observability-guide.md) |
| **架构师** | [架构设计](architecture.md) → [性能要求](performance-requirements.md) → [SQLAlchemy 2.0](sqlalchemy-2.0-guide.md) |

---

## 📚 核心文档 (19个)

### 1. 产品与规格 (4个)
- [项目移交文档](project-handoff.md) ⭐ - 项目概览、完成功能、质量指标
- [功能规格](../specs/001-lark-service-core/spec.md) - 详细功能需求 (FR-001 至 FR-122)
- [任务列表](../specs/001-lark-service-core/tasks.md) - Phase 1-6 任务详情
- [快速参考](quick-reference.md) - 常用命令与API速查

### 2. 架构与API (3个)
- [架构设计](architecture.md) ⭐ - 系统架构、模块依赖、数据流、Token管理
- [API参考](api_reference.md) ⭐ - 完整API文档、使用示例、最佳实践
- [错误处理指南](error-handling-guide.md) - 错误处理策略、重试机制

### 3. 开发指南 (5个)
- [开发环境配置](development-environment.md) - 环境搭建、依赖安装
- [测试指南](TESTING-GUIDE.md) ⭐ - 测试策略、覆盖率要求、CI集成
- [集成测试指南](integration-test-guide.md) - E2E测试、环境配置
- [Git提交规范](git-commit-standards.md) - Conventional Commits、Pre-commit hooks
- [Docstring标准](docstring-standard.md) - Google风格文档字符串规范

### 4. 部署与配置 (4个)
- [部署指南](deployment.md) ⭐ - 部署流程、环境变量、数据库备份
- [RabbitMQ配置](rabbitmq-config.md) - 消息队列生产配置、持久化、DLQ
- [安全指南](security-guide.md) - 加密、密钥管理、容器安全
- [性能要求](performance-requirements.md) - 性能指标、压力测试

### 5. 技术专题 (3个)
- [SQLAlchemy 2.0指南](sqlalchemy-2.0-guide.md) - ORM使用、最佳实践
- [可观测性指南](observability-guide.md) - 日志、监控、追踪
- [CI/CD流程](ci-cd.md) - GitHub Actions、安全扫描、质量门禁

---

## 📊 项目状态与报告

### 当前状态
- [当前状态摘要](../CURRENT-STATUS.md) ⭐⭐⭐ - 项目当前状态 (60.38%覆盖率)
- [快速启动指南](../QUICK-START-NEXT-CHAT.md) ⭐⭐⭐ - 下次Chat快速开始
- [Phase 2-4 策略](PHASE2-4-STRATEGY.md) - 渐进式测试覆盖率提升策略

### 检查清单
- [生产就绪检查](../specs/001-lark-service-core/checklists/production-readiness.md) - 生产部署217项检查
- [Phase 6 最终报告](../specs/001-lark-service-core/checklists/phase6-final-report.md) - Phase 6完成状态

### 历史归档
所有阶段性报告已归档至相应目录:
- `../archive/reports-2026-01/` - 测试覆盖率提升项目 (11个报告)
- `../archive/temp-reports/` - 临时分析文件 (15个文件)
- `archive/phase-reports/` - 阶段完成报告 (9个报告)

---

## 🔧 模块使用说明

每个模块的详细文档参见:

### Core 核心模块
- **Token管理**: `CredentialPool` - 自动获取、刷新、缓存
- **配置管理**: `Config` - 环境变量、加密密钥
- **存储服务**: SQLite (应用配置) + PostgreSQL (Token缓存)
- **重试策略**: 指数退避、并发控制
- **文档**: [architecture.md](architecture.md) § Token管理架构

### Messaging 消息模块
- **消息发送**: 文本、富文本、图片、文件、卡片
- **批量操作**: 批量发送、性能优化
- **文档**: [api_reference.md](api_reference.md) § Messaging

### CloudDoc 云文档模块
- **文档操作**: 创建、读取、更新、权限管理
- **Bitable**: 多维表格CRUD、结构化查询
- **Sheet**: 电子表格读写、批量更新
- **文档**: [api_reference.md](api_reference.md) § CloudDoc

### Contact 通讯录模块
- **用户查询**: 邮箱、ID、批量查询
- **部门管理**: 部门树、用户列表
- **缓存机制**: 24小时TTL、自动过期清理
- **文档**: [api_reference.md](api_reference.md) § Contact

### CardKit 卡片模块
- **卡片构建**: 通知卡片、审批卡片、表单卡片
- **回调处理**: 签名验证、事件路由
- **文档**: [api_reference.md](api_reference.md) § CardKit

### aPaaS 数据空间模块
- **表格操作**: 列表、字段查询、记录CRUD
- **SQL查询**: 执行SQL、批量操作
- **文档**: [api_reference.md](api_reference.md) § aPaaS

---

## 📖 快速开始

### 1. 查看项目概览
```bash
# 项目当前状态 (最重要)
cat CURRENT-STATUS.md

# 快速启动指南
cat QUICK-START-NEXT-CHAT.md

# 项目README
cat README.md

# 变更日志
cat CHANGELOG.md
```

### 2. 本地开发
```bash
# 激活测试环境
source .venv-test/bin/activate

# 安装依赖
uv pip install -r requirements.txt

# 运行测试
pytest tests/unit/ -v

# 查看覆盖率
pytest tests/unit/ --cov=src/lark_service --cov-report=html
# 浏览器打开: htmlcov/index.html
```

### 3. 代码质量检查
```bash
# 格式化代码
ruff format src/ tests/

# Linting
ruff check src/ tests/ --fix

# 类型检查
mypy src/ --strict

# Pre-commit检查
pre-commit run --all-files
```

### 4. Git工作流
```bash
# 修改代码
vim src/lark_service/module/file.py

# 添加并检查
git add src/lark_service/module/file.py
pre-commit run

# 提交 (Conventional Commits)
git commit -m "feat(module): add new feature"

# 推送
git push origin 001-lark-service-core
```

---

## 📋 项目规范

### 代码规范
参见 [项目宪章](../.specify/memory/constitution.md):
- **语言**: Python 3.12+
- **代码**: 英文注释与命名
- **文档**: 中文说明文档
- **格式**: Ruff自动格式化
- **类型**: MyPy严格检查
- **测试**: Pytest + 60%覆盖率
- **Docstring**: Google风格

### Git规范
- **提交格式**: Conventional Commits
- **格式**: `<type>(<scope>): <description>`
- **类型**: feat, fix, docs, test, refactor, chore, perf
- **详见**: [git-commit-standards.md](git-commit-standards.md)

### 质量门禁
- ✅ Ruff检查通过 (0错误)
- ✅ MyPy检查通过 (严格模式)
- ✅ 测试覆盖率 ≥ 60%
- ✅ 所有测试通过 (100%)
- ✅ 安全扫描无高危漏洞

---

## 🔍 相关资源

### 官方文档
- [飞书开放平台](https://open.feishu.cn/document/) - 飞书API文档
- [lark-oapi SDK](https://github.com/larksuite/oapi-sdk-python) - 官方Python SDK

### 项目链接
- **规格文档**: `specs/001-lark-service-core/`
- **测试用例**: `tests/unit/`, `tests/integration/`
- **源代码**: `src/lark_service/`
- **配置示例**: `.env.example`, `docker-compose.yml`

### 项目指标
- **版本**: v0.1.0
- **整体覆盖率**: 60.38%
- **测试总数**: 377个 (374 passed, 3 skipped)
- **文档数量**: 19个核心文档
- **代码质量**: ✅ Ruff + MyPy 严格模式

---

## 📞 获取帮助

### 问题排查
1. 查看 [错误处理指南](error-handling-guide.md)
2. 查看 [常见问题](quick-reference.md) § 故障排查
3. 查看 [项目交接文档](project-handoff.md) § 故障排查

### 文档导航
- **新手**: 从 `CURRENT-STATUS.md` 开始
- **开发**: 参考 `api_reference.md` 和 `TESTING-GUIDE.md`
- **部署**: 参考 `deployment.md` 和 `security-guide.md`
- **架构**: 参考 `architecture.md` 和 `performance-requirements.md`

---

**最后更新**: 2026-01-18
**文档整理**: 42个 → 19个 (-55%)
**维护者**: Ray
**状态**: ✅ 文档结构优化完成
