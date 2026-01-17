# Lark Service - 项目文档索引

## 📚 核心文档

### 产品与规格
- [项目移交文档](project-handoff.md) - 项目概览、完成功能、待办事项
- [功能规格](../specs/001-lark-service-core/spec.md) - 详细功能需求 (FR-001 至 FR-122)
- [任务列表](../specs/001-lark-service-core/tasks.md) - Phase 1-6 任务详情
- [实施计划](../specs/001-lark-service-core/plan.md) - 技术实施方案

### 架构与设计
- [架构设计](architecture.md) - 系统架构、模块依赖、数据流
- [API合约](../specs/001-lark-service-core/contracts/) - OpenAPI规范
- [错误处理指南](error-handling-guide.md) - 错误处理策略
- [安全指南](security-guide.md) - 安全要求与实施

### 开发指南
- [开发环境配置](development-environment.md) - 环境搭建
- [测试指南](testing-guide.md) - 测试策略与执行
- [Docstring标准](docstring-standard.md) - 文档字符串规范
- [性能要求](performance-requirements.md) - 性能指标与测试

### 部署与运维
- [部署指南](deployment.md) - 部署流程与配置
- [RabbitMQ配置](rabbitmq-config.md) - 消息队列配置

---

## 📊 测试与质量报告

### 测试覆盖率报告
- [当前状态摘要](../CURRENT-STATUS.md) ⭐ - 项目当前状态(60.38%覆盖率)
- [快速启动指南](../QUICK-START-NEXT-CHAT.md) ⭐ - 下次Chat快速开始
- [历史报告归档](../archive/reports-2026-01/) - 详细的阶段性报告

### 检查清单
- [生产就绪检查](../specs/001-lark-service-core/checklists/production-readiness.md) - 生产部署检查项
- [Phase 6 最终报告](../specs/001-lark-service-core/checklists/phase6-final-report.md) - Phase 6完成状态

### 归档报告
所有详细的阶段性报告已归档至 `../archive/reports-2026-01/`:
- 测试覆盖率提升项目报告 (7个)
- 测试覆盖率分析文档 (3个)
- 漏洞修复计划 (已完成)

---

## 🔧 技术文档

### 模块说明
每个模块的详细使用说明参见对应的 `__init__.py` 或模块文档:

- **Core**: Token管理、配置、重试、异常处理
  - `src/lark_service/core/` - 核心功能

- **Messaging**: 消息发送
  - `src/lark_service/messaging/` - 消息服务

- **CloudDoc**: 文档操作
  - `src/lark_service/clouddoc/` - 文档服务

- **Contact**: 通讯录
  - `src/lark_service/contact/` - 联系人服务

- **CardKit**: 交互式卡片
  - `src/lark_service/cardkit/` - 卡片构建与回调

- **aPaaS**: 数据空间
  - `src/lark_service/apaas/` - aPaaS数据操作

---

## 📖 快速开始

### 查看项目概览
```bash
# 项目README
cat README.md

# 项目移交文档
cat docs/project-handoff.md

# 变更日志
cat CHANGELOG.md
```

### 运行测试
```bash
# 激活测试环境
source .venv-test/bin/activate

# 运行所有测试
pytest tests/unit/ -v

# 查看覆盖率
pytest tests/unit/ --cov=src/lark_service --cov-report=term-missing

# 生成HTML报告
pytest tests/unit/ --cov=src/lark_service --cov-report=html
# 查看: htmlcov/index.html
```

### 查看当前状态
```bash
# 项目当前状态
cat CURRENT-STATUS.md

# 快速启动指南
cat QUICK-START-NEXT-CHAT.md

# 查看历史报告
ls archive/reports-2026-01/
```

---

## 📋 项目规范

### 代码规范
参见 [项目宪章](../.specify/memory/constitution.md):
- Python 3.12+
- 代码使用英文,文档使用中文
- 遵循PEP 8
- Ruff格式化
- MyPy类型检查
- Google风格Docstring

### Git提交规范
- 使用 Conventional Commits
- 格式: `<type>(<scope>): <description>`
- 类型: feat, fix, docs, test, refactor, chore

---

## 🔍 相关资源

### 外部文档
- [Lark Open Platform](https://open.feishu.cn/document/)
- [lark-oapi SDK](https://github.com/larksuite/oapi-sdk-python)

### 项目状态
- **当前版本**: v0.1.0
- **整体覆盖率**: 60.38%
- **测试总数**: 377个
- **文档完整度**: 优秀

---

**最后更新**: 2026-01-18
**维护者**: Ray
**状态**: ✅ Phase 1 完成
