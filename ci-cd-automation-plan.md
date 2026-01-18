# 🚀 GitHub Actions CI/CD 自动化流水线设计方案

**版本**: v1.0.0
**状态**: 方案设计阶段
**更新日期**: 2026-01-19

---

## 1. 总体设计思路
本方案旨在实现从代码提交到生产部署的全自动化闭环。核心原则为：**测试驱动合并、组件逻辑隔离、部署零停机、数据库自迁移。**

---

## 2. CI/CD 流水线阶段划分

### 2.1 CI 持续验证 (提交代码/创建PR时)
*   **代码质量检查**: 运行 `ruff` 格式化检查与 `mypy` 静态类型检查。
*   **自动化测试**:
    *   运行单元测试（使用 Mock，不依赖真实环境）。
    *   强制执行代码覆盖率阈值（建议 ≥ 80%）。
*   **安全扫描**: 扫描代码中的硬编码密钥（TruffleHog）及依赖漏洞扫描（Trivy）。
*   **准入机制**: 通过保护分支规则（Branch Protection），只有 CI 全部通过才允许合并至 `master`。

### 2.2 CD 持续部署 (合并至 master 时)
*   **全量集成测试**: 在部署前，由 Actions 启动临时容器运行针对飞书真实 API 的集成测试。
*   **自动化部署**:
    *   **Staging**: 自动同步代码、构建并运行健康检查。
    *   **Production**: 增加手动审批环节，批准后通过 Ansible 或 SSH 脚本执行生产服务器部署。
*   **自动回滚**: 若健康检查（Health Check）失败，Actions 自动触发部署回滚任务。

---

## 3. 多服务与基础架构管理策略

为了解决多服务共用物理服务器及基础组件的问题，采用 **“基础组件统一化，业务服务解耦化”** 的管理模式。

### 3.1 部署架构：独立 Compose + 外部网络
*   **基础设施 (Infrastructure)**: PostgreSQL、Redis、Prometheus、Grafana 等共享组件由一个独立的仓库或特定的 `docker-compose.infra.yml` 管理。
*   **业务服务 (LarkService)**: 每个业务服务拥有独立的 `docker-compose.yml`。
*   **网络互通**: 业务容器通过 Docker 的 `external network` 连接到基础设施。
    ```yaml
    # 业务服务的 docker-compose.yml 示例
    networks:
      default:
        external: true
        name: infra-shared-network
    ```

---

## 4. 数据库管理与自动化迁移

针对“相同数据库服务器、不同数据库实例”的场景：

*   **隔离机制**:
    *   在 PostgreSQL 中为每个服务创建独立的 **Database** (如 `lark_service_db`, `auth_service_db`)。
    *   为每个服务配置独立的 **DB User**，仅授予其所属 Database 的权限。
*   **自动迁移流程**:
    1.  **环境变量驱动**: Actions 在部署时将目标数据库连接串注入容器。
    2.  **前置迁移任务**: 在业务容器正式启动前，执行一次性迁移任务：
        ```bash
        docker compose run --rm lark-service alembic upgrade head
        ```
    3.  **幂等性保证**: Alembic 通过内部版本表（`alembic_version`）确保在同一个 Database 内只执行缺失的迁移脚本。

---

## 5. 零停机发布与服务隔离方案

### 5.1 服务隔离 (Isolation)
*   **资源限制**: 在 Compose 配置中严格限制 CPU 和内存使用，防止单服务 Bug 拖垮整机。
    ```yaml
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    ```
*   **故障隔离**: 即使主应用崩溃，独立的 Metrics Server 依然可以向 Prometheus 报告异常状态。

### 5.2 零停机发布 (Zero-Downtime)
*   **优雅停机 (Graceful Shutdown)**:
    *   应用需捕获 `SIGTERM` 信号。
    *   收到信号后，停止接收新请求，处理完存量任务后再退出。
*   **健康检查切流**:
    1.  启动新版本容器（Container V2）。
    2.  等待容器内 `/health` 接口返回 200（Ready）。
    3.  通过反向代理（如 Nginx 或 Traefik）将流量平滑引入 V2。
    4.  停止旧版本容器（Container V1）。

---

## 6. 下一步实施建议

1.  **基础设施配置**: 在服务器上配置好 `infra-shared-network` 以及共用的基础镜像环境。
2.  **Secrets 配置**: 在 GitHub 仓库中配置好服务器 SSH 密钥、数据库凭证及飞书应用密钥。
3.  **Workflow 编写**:
    *   编写 `.github/workflows/ci.yml` 实现代码验证逻辑。
    *   编写 `.github/workflows/cd.yml` 调用 `deploy/scripts/` 下的部署脚本。
4.  **优雅停机优化**: 在 Python 应用代码中添加对 `SIGTERM` 信号的处理，确保发布时正在处理的请求不被强行中断。
