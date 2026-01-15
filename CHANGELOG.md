# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 待发布的新功能

### Changed
- 待发布的变更

### Fixed
- 待发布的 Bug 修复

## [0.1.0] - 2026-01-15

### Added
- Phase 1-2: 基础设施和 Token 管理
  - 配置管理系统 (SQLite + 加密)
  - Token 管理池 (自动刷新 + 持久化)
  - PostgreSQL Token 存储
  - RabbitMQ 消息队列集成
  - CLI 工具 (lark-service-cli)
- SQLAlchemy 2.0 现代语法支持
- 完整的文档体系 (20个文档, 11,000+ 行)
  - 开发指南、架构设计、安全配置
  - Git 工作流、CI/CD、团队协作
  - 测试策略、可观测性、性能需求

### Changed
- 升级 SQLAlchemy 到 2.0 (DeclarativeBase + Mapped[T])
- 优化 Token 刷新逻辑
- 重构数据库连接池

### Fixed
- 修复并发刷新 Token 的竞态条件
- 修复 Mypy 类型检查问题 (7个错误 → 0)
- 修复日志脱敏规则

### Security
- 实现 FR-077~095 安全需求
  - 文件权限管理 (chmod 600)
  - 配置敏感度分类
  - 密钥加密存储和轮换
  - 日志脱敏规则
  - 依赖安全扫描 (Safety)
  - 容器安全扫描 (Trivy)

### Documentation
- 17 个完整文档
- Speckit 工作流集成
- Git 分支策略 (NNN-<描述>)
- 完整的开发者指南

### Quality
- 测试: 140/140 通过 ✅
- 覆盖率: 77.33% ✅
- Mypy: 99.8% 类型安全 ✅
- Ruff: 0 错误 ✅

---

## 版本号规范

版本格式: `vMAJOR.MINOR.PATCH`

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向后兼容的功能新增
- **PATCH**: 向后兼容的 bug 修复

## Phase 与版本对应关系

| Phase | 版本 | 说明 |
|-------|------|------|
| Phase 1-2 | v0.1.0 | 基础设施 + Token 管理 ✅ |
| Phase 3 | v0.2.0 | 消息服务 |
| Phase 4 | v0.3.0 | 文档+通讯录 |
| Phase 5 | v0.4.0 | aPaaS 功能 |
| Stable | v1.0.0 | 生产就绪 |

[Unreleased]: https://github.com/ZenRay/LarkServiceCursor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ZenRay/LarkServiceCursor/releases/tag/v0.1.0
