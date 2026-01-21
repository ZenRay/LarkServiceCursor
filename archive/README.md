# Archive Directory

本目录存放项目开发过程中产生的临时文件、测试报告和过时文档。

## 目录结构

- `temp-reports/` - 临时测试报告和覆盖率数据
- `temp-guides/` - 临时测试指南和快速启动文档

## 归档文件

这些文件在项目开发阶段有用，但在生产环境中不需要：

### temp-reports/
- `coverage.xml` - 测试覆盖率报告（CI/CD 生成，可重新生成）
- `PROJECT_SUMMARY.md` - 项目总结（已整合到 CHANGELOG.md）

### temp-guides/
- `QUICK-START-NEXT-CHAT.md` - 会话间快速启动指南（已过时，v0.1.0 完成）
- `QUICK_START_TEST.md` - 快速测试指南（已被 FINAL_TEST_GUIDE.md 替代）

## 保留在根目录的文件

- `CHANGELOG.md` - 正式变更日志（必须保留）
- `CURRENT-STATUS.md` - 当前状态（重要参考）
- `FINAL_TEST_GUIDE.md` - 正式测试指南（v0.2.0 功能）
- `README.md` - 项目主文档（必须保留）
- `requirements.txt` / `requirements-prod.txt` - 依赖管理（必须保留）
- `docker-compose.yml` / `Dockerfile` - 容器配置（必须保留）
- `production.env` - 生产环境配置模板（必须保留）
- `pyproject.toml` - Python 项目配置（必须保留）

最后更新: 2026-01-21
