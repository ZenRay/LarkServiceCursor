# LarkService 文档索引

**最后更新**: 2026-01-17

本文档提供项目文档的快速导航和说明。

---

## 📚 核心文档

### 架构与设计
- **[architecture.md](architecture.md)** - 系统架构设计（核心文档）
- **[technical-debt.md](technical-debt.md)** - 技术债务追踪

### 开发指南
- **[development-environment.md](development-environment.md)** - 开发环境搭建
- **[dev-workflow.md](dev-workflow.md)** - 开发工作流程（包含 git hooks）
- **[quick-reference.md](quick-reference.md)** - 快速参考（代码质量工具）
- **[docstring-standard.md](docstring-standard.md)** - 文档字符串规范
- **[error-handling-guide.md](error-handling-guide.md)** - 错误处理指南

### Git 工作流
- **[git-workflow.md](git-workflow.md)** - Git 工作流程和分支策略
- **[git-commit-standards.md](git-commit-standards.md)** - Git 提交规范

### 测试
- **[testing-strategy.md](testing-strategy.md)** - 测试策略（核心文档）
- **[integration-test-setup.md](integration-test-setup.md)** - 集成测试环境配置
- **[integration-test-guide.md](integration-test-guide.md)** - 集成测试编写指南
- **[apaas-test-guide.md](apaas-test-guide.md)** - aPaaS 模块测试指南
- **[skipped-tests-explanation.md](skipped-tests-explanation.md)** - 跳过测试说明

### 安全
- **[security-guide.md](security-guide.md)** - 安全开发指南（核心文档）
- **[ci-security-scanning.md](ci-security-scanning.md)** - CI 安全扫描配置

### 运维
- **[deployment.md](deployment.md)** - 部署指南
- **[ci-cd.md](ci-cd.md)** - CI/CD 配置
- **[observability-guide.md](observability-guide.md)** - 可观测性指南
- **[json-logging-guide.md](json-logging-guide.md)** - JSON 日志规范

### 性能
- **[performance-requirements.md](performance-requirements.md)** - 性能要求和优化

### 数据库
- **[sqlalchemy-2.0-guide.md](sqlalchemy-2.0-guide.md)** - SQLAlchemy 2.0 迁移指南
- **[database-timezone-config.md](database-timezone-config.md)** - 数据库时区配置

### 团队协作
- **[team-collaboration.md](team-collaboration.md)** - 团队协作规范
- **[project-maintenance.md](project-maintenance.md)** - 项目维护指南

---

## 🚀 当前状态文档

### Phase 5 (aPaaS 功能) - 已完成
- **[phase5-completion-report.md](phase5-completion-report.md)** - Phase 5 完成报告
- **[phase5-implementation-handoff.md](phase5-implementation-handoff.md)** - Phase 5 到 Phase 6 交接文档

### Phase 3/4 完成报告
- **[phase3-completion-report.md](phase3-completion-report.md)** - Phase 3 完成报告
- **[phase4-completion-report.md](phase4-completion-report.md)** - Phase 4 完成报告

### 最新测试报告
- **[test-report-2026-01-17.md](test-report-2026-01-17.md)** - 最新功能测试报告
- **[github-actions-test-failures-report.md](github-actions-test-failures-report.md)** - GitHub Actions 测试修复报告

### CloudDoc API 参考
- **[clouddoc-complete-api-guide.md](clouddoc-complete-api-guide.md)** - CloudDoc 完整 API 指南
- **[clouddoc-permissions-guide.md](clouddoc-permissions-guide.md)** - CloudDoc 权限指南

### 规划文档
- **[next-steps-roadmap.md](next-steps-roadmap.md)** - 后续开发路线图

---

## 📦 配置示例
- **[env.test.example](env.test.example)** - 测试环境配置示例

---

## 🗄️ 归档文档

历史文档和已完成阶段的过程文档已移至 `archive/` 目录：

- **[archive/phase3/](archive/phase3/)** - Phase 3 历史文档
- **[archive/phase4/](archive/phase4/)** - Phase 4 历史文档
- **[archive/phase5/](archive/phase5/)** - Phase 5 中间文档
- **[archive/reports/](archive/reports/)** - 历史报告

详见 [archive/README.md](archive/README.md)

---

## 📖 文档使用指南

### 新人入门
1. 阅读 [architecture.md](architecture.md) 了解系统架构
2. 参考 [development-environment.md](development-environment.md) 搭建开发环境
3. 学习 [dev-workflow.md](dev-workflow.md) 了解开发流程
4. 遵循 [git-commit-standards.md](git-commit-standards.md) 提交代码

### 功能开发
1. 参考 [testing-strategy.md](testing-strategy.md) 编写测试
2. 遵循 [docstring-standard.md](docstring-standard.md) 编写文档
3. 使用 [quick-reference.md](quick-reference.md) 进行代码质量检查
4. 参考相应模块的 API 指南

### 故障排查
1. 查看 [skipped-tests-explanation.md](skipped-tests-explanation.md) 了解跳过的测试
2. 参考 [error-handling-guide.md](error-handling-guide.md) 处理错误
3. 使用 [observability-guide.md](observability-guide.md) 排查问题

### 部署运维
1. 参考 [deployment.md](deployment.md) 进行部署
2. 配置 [ci-cd.md](ci-cd.md) 设置自动化流程
3. 遵循 [security-guide.md](security-guide.md) 确保安全

---

## 📝 文档维护

- **定期更新**: 完成重要功能后更新相关文档
- **归档策略**: 已完成阶段的过程文档移至 `archive/`
- **版本控制**: 所有文档纳入 Git 版本控制
- **审查机制**: 文档变更需经过 Code Review

---

**维护者**: LarkService 开发团队
**联系方式**: 见项目 README.md
