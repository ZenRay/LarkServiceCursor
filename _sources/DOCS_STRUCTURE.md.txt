# 文档结构说明

## 📚 核心文档（docs/）

### 快速开始
- `installation.md` - 安装指南
- `quickstart.md` - 快速开始
- `README.md` - 文档总览

### API 参考
- `api/` - API 自动生成文档
- `api-examples.md` - API 使用示例
- `api-rate-limiting-guide.md` - API 限流指南

### 使用指南
- `usage/` - 功能使用指南

### 架构设计
- `architecture.md` - 系统架构
- `architecture/` - 详细架构文档

### 部署运维
- `deployment.md` - 部署指南
- `deployment/` - 部署相关文档
- `monitoring.md` - 监控配置
- `observability-guide.md` - 可观测性
- `grafana-setup-guide.md` - Grafana 设置

### 开发指南
- `development-environment.md` - 开发环境设置
- `TESTING-GUIDE.md` - 测试指南
- `integration-test-guide.md` - 集成测试

### 错误处理
- `error-codes.md` - 错误代码
- `error-handling-guide.md` - 错误处理
- `error-recovery-guide.md` - 错误恢复
- `troubleshooting.md` / `troubleshooting-guide.md` - 故障排查

### 安全
- `security-guide.md` - 安全指南

### 其他
- `quick-reference.md` - 快速参考
- `tracing-guide.md` - 追踪指南
- `features/` - 功能特性文档

## 📦 归档文档（docs/archive/）

### development-reports/
项目开发过程中的总结报告

### test-reports/
历史测试报告（2026-01-18）

### guides/
内部开发指南和配置文档（已归档）

### phase3/, phase4/, phase5/
各开发阶段的需求和实现文档

### reports/
早期项目报告

### completion/
版本完成总结

---

**文档优化说明**：
- ✅ 将 48 个 Markdown 文件精简到 21 个核心文档
- ✅ 将历史报告、内部指南归档到 `archive/` 目录
- ✅ 保留面向用户的核心文档在主目录
- ✅ 减少 Sphinx 构建警告
