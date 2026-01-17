# Docs 清理策略

**日期**: 2026-01-18
**任务**: 清理 `docs/` 目录中不必要和冗余的文档

---

## 📊 文档分类

### ✅ 保留 - 核心文档 (15个)

这些是项目必需的核心文档,需要长期维护:

1. **README.md** - 文档索引
2. **api_reference.md** - API 完整参考
3. **architecture.md** - 系统架构设计
4. **deployment.md** - 部署指南
5. **error-handling-guide.md** - 错误处理指南
6. **security-guide.md** - 安全指南
7. **performance-requirements.md** - 性能要求
8. **rabbitmq-config.md** - RabbitMQ 配置
9. **TESTING-GUIDE.md** - 测试指南 (新)
10. **project-handoff.md** - 项目交接文档
11. **docstring-standard.md** - Docstring 规范
12. **sqlalchemy-2.0-guide.md** - SQLAlchemy 2.0 指南
13. **development-environment.md** - 开发环境配置
14. **git-commit-standards.md** - Git 提交规范
15. **integration-test-guide.md** - 集成测试指南

---

## 🗑️ 删除 - 临时报告/过时文档 (12个)

这些是临时性报告或已过时的文档,应删除或归档:

### 阶段完成报告 (6个) - 归档到 archive/
- **phase3-completion-report.md** - Phase 3 完成报告
- **phase4-completion-report.md** - Phase 4 完成报告
- **phase5-completion-report.md** - Phase 5 完成报告
- **phase5-implementation-handoff.md** - Phase 5 实施交接
- **test-report-2026-01-17.md** - 测试报告 (临时)
- **github-actions-test-failures-report.md** - GitHub Actions 失败报告 (临时)

### 迁移/优化报告 (2个) - 归档到 archive/
- **docker-migration-report.md** - Docker 迁移报告 (已完成)
- **docker-optimization-guide.md** - Docker 优化指南 (可合并到 deployment.md)

### 已被新文档取代 (3个) - 删除
- **testing-strategy.md** - 被 `TESTING-GUIDE.md` 取代
- **integration-test-setup.md** - 被 `integration-test-guide.md` 取代
- **skipped-tests-explanation.md** - 临时说明文档

### 其他 (1个) - 删除
- **env.test.example** - 不是 Markdown 文档,应移到根目录或删除

---

## 🔀 合并 - 冗余内容 (8个)

这些文档内容重复或可以合并:

### Git 相关 (2个) → 合并到 `git-commit-standards.md`
- **git-workflow.md** - Git 工作流 (与 dev-workflow.md 重复)
- **dev-workflow.md** - 开发工作流 (保留,但精简 Git 部分)

### CI/CD 相关 (2个) → 合并为 `ci-cd.md`
- **ci-cd.md** - CI/CD 流程 ✅ 保留
- **ci-security-scanning.md** - 安全扫描详解 (可作为 ci-cd.md 的子章节)

### CloudDoc 相关 (2个) → 合并为 `clouddoc-guide.md`
- **clouddoc-complete-api-guide.md** - CloudDoc API 指南
- **clouddoc-permissions-guide.md** - CloudDoc 权限配置

### 测试相关 (1个) → 合并到 `TESTING-GUIDE.md`
- **apaas-test-guide.md** - aPaaS 测试指南 (特定内容)

### 其他 (1个) → 精简
- **database-timezone-config.md** - 数据库时区配置 (可合并到 deployment.md)

---

## 📝 精简 - 过于详细 (7个)

这些文档内容过于详细,需要精简或拆分:

### 需要精简 (5个)
1. **observability-guide.md** (14K) - 可观测性指南,精简到核心内容
2. **json-logging-guide.md** (6.2K) - JSON 日志指南,合并到 observability-guide.md
3. **team-collaboration.md** (11K) - 团队协作指南,精简到 README 或删除
4. **project-maintenance.md** (7.8K) - 项目维护指南,精简到核心内容
5. **production-env-setup.md** (4.9K) - 生产环境配置,合并到 deployment.md

### 需要归档 (2个)
1. **next-steps-roadmap.md** (14K) - 后续路线图 (归档到 archive/)
2. **technical-debt.md** (2.7K) - 技术债务 (归档到 archive/)

---

## 🔄 重组建议

### 新的文档结构

```
docs/
├── README.md                          ⭐ 文档索引
│
├── 核心文档 (6个)
│   ├── api_reference.md               ⭐ API 完整参考
│   ├── architecture.md                ⭐ 系统架构
│   ├── deployment.md                  ⭐ 部署指南 (整合 production-env-setup, database-timezone-config)
│   ├── security-guide.md              ⭐ 安全指南
│   ├── error-handling-guide.md        ⭐ 错误处理
│   └── performance-requirements.md    ⭐ 性能要求
│
├── 配置与规范 (5个)
│   ├── development-environment.md     ⭐ 开发环境
│   ├── git-commit-standards.md        ⭐ Git 提交规范 (整合 git-workflow, dev-workflow)
│   ├── docstring-standard.md          ⭐ Docstring 规范
│   ├── sqlalchemy-2.0-guide.md        ⭐ SQLAlchemy 2.0
│   └── rabbitmq-config.md             ⭐ RabbitMQ 配置
│
├── 测试文档 (2个)
│   ├── TESTING-GUIDE.md               ⭐ 测试指南 (整合 apaas-test-guide)
│   └── integration-test-guide.md      ⭐ 集成测试
│
├── CI/CD 与可观测 (2个)
│   ├── ci-cd.md                       ⭐ CI/CD 流程 (整合 ci-security-scanning)
│   └── observability-guide.md         ⭐ 可观测性 (整合 json-logging-guide, 精简)
│
├── CloudDoc 专题 (1个)
│   └── clouddoc-guide.md              ⭐ CloudDoc 指南 (合并 complete-api + permissions)
│
├── 项目管理 (2个)
│   ├── project-handoff.md             ⭐ 项目交接
│   └── quick-reference.md             ⭐ 快速参考
│
└── PHASE2-4-STRATEGY.md               ⭐ Phase 2-4 策略 (保留)
```

**总计**: 19个核心文档 (从42个精简到19个)

---

## 🎯 执行计划

### Step 1: 归档历史报告 (8个)
```bash
mkdir -p archive/phase-reports
mv docs/phase3-completion-report.md archive/phase-reports/
mv docs/phase4-completion-report.md archive/phase-reports/
mv docs/phase5-completion-report.md archive/phase-reports/
mv docs/phase5-implementation-handoff.md archive/phase-reports/
mv docs/test-report-2026-01-17.md archive/phase-reports/
mv docs/github-actions-test-failures-report.md archive/phase-reports/
mv docs/docker-migration-report.md archive/phase-reports/
mv docs/next-steps-roadmap.md archive/phase-reports/
mv docs/technical-debt.md archive/phase-reports/
```

### Step 2: 删除冗余文档 (5个)
```bash
rm docs/testing-strategy.md              # 被 TESTING-GUIDE.md 取代
rm docs/integration-test-setup.md        # 被 integration-test-guide.md 取代
rm docs/skipped-tests-explanation.md     # 临时说明
rm docs/env.test.example                 # 不是文档
rm docs/docker-optimization-guide.md     # 内容已整合到 deployment.md
```

### Step 3: 合并文档 (保留主文档,删除被合并文档)
```bash
# 保留 ci-cd.md, 删除 ci-security-scanning.md (内容合并后)
rm docs/ci-security-scanning.md

# 保留 git-commit-standards.md, 删除 git-workflow.md, dev-workflow.md (内容合并后)
rm docs/git-workflow.md
rm docs/dev-workflow.md

# 保留 deployment.md, 删除 production-env-setup.md, database-timezone-config.md (内容合并后)
rm docs/production-env-setup.md
rm docs/database-timezone-config.md

# 保留 observability-guide.md, 删除 json-logging-guide.md (内容合并后)
rm docs/json-logging-guide.md

# 保留 TESTING-GUIDE.md, 删除 apaas-test-guide.md (内容合并后)
rm docs/apaas-test-guide.md

# 创建新的 clouddoc-guide.md (合并 complete-api + permissions)
# 然后删除原文件
rm docs/clouddoc-complete-api-guide.md
rm docs/clouddoc-permissions-guide.md

# 删除团队协作文档 (内容过时或可移到 README)
rm docs/team-collaboration.md
rm docs/project-maintenance.md
```

### Step 4: 更新 docs/README.md
更新文档索引,反映新的文档结构

---

## 📈 清理效果

### 清理前
- 文档数量: 42个
- 总大小: ~430KB
- 问题: 冗余、重复、过时

### 清理后
- 文档数量: 19个 (-55%)
- 总大小: ~250KB (-42%)
- 优势: 结构清晰、易于维护、内容精准

---

## ✅ 验收标准

- [ ] 核心文档完整保留 (19个)
- [ ] 历史报告归档 (9个)
- [ ] 冗余文档删除 (14个)
- [ ] docs/README.md 更新完成
- [ ] 所有引用更新完成
- [ ] Git 提交完成

---

**策略制定**: 2026-01-18
**执行负责**: Ray
**预计耗时**: 1-2小时
