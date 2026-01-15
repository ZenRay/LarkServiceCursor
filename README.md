# Lark Service 核心组件

**Lark Service 企业自建应用核心组件** - 封装飞书 OpenAPI,提供高度复用且透明的接入能力

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Tests](https://img.shields.io/badge/tests-140%20passed-success.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-77.33%25-brightgreen.svg)](htmlcov/)
[![Mypy](https://img.shields.io/badge/mypy-99.8%25-blue.svg)](src/)
[![Security](https://img.shields.io/badge/security-FR--077~095%20compliant-success.svg)](docs/security-guide.md)

## ✨ 核心特性

- 🔐 **透明 Token 管理**: 自动获取、刷新和持久化 Token,开发者无需关心认证细节
- 🚀 **高度复用**: Python 库设计,可被任何 Python 应用导入使用 (Django、Flask、FastAPI、Airflow 等)
- 🎯 **多应用隔离**: 支持多个飞书应用并发使用,Token 和配置完全隔离
- 📦 **模块化设计**: Messaging、CloudDoc、Contact、aPaaS 四大模块,按需使用
- 🔒 **安全第一**: 加密存储敏感信息,支持环境变量和密钥管理
- 🧪 **测试驱动**: 99%+ 代码覆盖率,TDD 开发流程
- 📊 **可观测性**: 结构化日志、请求追踪、性能监控

## 📋 快速开始

### 开发者工作流 (Speckit)

本项目使用 **Speckit** 进行功能开发和规范管理:

```bash
# 1. 创建新功能分支 (自动创建 spec 目录)
/speckit.specify "Implement messaging service for group chats"
# → 创建分支: 002-messaging-service
# → 创建目录: specs/002-messaging-service/

# 2. 生成实施计划和任务清单
/speckit.plan      # 生成 plan.md
/speckit.tasks     # 生成 tasks.md

# 3. 开发功能 (正常 Git 工作流)
git add .
git commit -m "feat(messaging): 实现消息发送接口"
git push -u origin 002-messaging-service

# 4. 创建 PR 并验收
# 在 GitHub 创建 PR: 002-messaging-service → main
/speckit.checklist  # 运行检查清单验证
```

**分支命名规范**: `NNN-<short-description>` (如 `001-lark-service-core`)
**详细说明**: 参考 [Git 工作流文档](docs/git-workflow.md)

### 集成方式

本服务支持两种集成方式,**推荐使用子项目集成方式**以便于开发调试和定制:

#### 方式 1: 子项目集成 (推荐) ⭐

适用于需要频繁调试、深度定制或单体应用的场景。

```bash
# 1. 添加为 Git 子模块
cd your-project
git submodule add https://github.com/your-org/lark-service.git libs/lark-service

# 2. 初始化子模块
git submodule update --init --recursive

# 3. 安装依赖
cd libs/lark-service
uv pip install -r requirements.txt
```

**使用方式**:

```python
import sys
from pathlib import Path

# 添加子项目到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "libs" / "lark-service" / "src"))

from lark_service import LarkServiceClient
```

**优势**:
- ✅ 源码完全可见,便于学习和调试
- ✅ 修改即生效,无需重新安装
- ✅ Git 子模块锁定版本,团队环境一致
- ✅ 可以自由定制和扩展

#### 方式 2: PyPI 包安装 (备选)

适用于生产环境部署、多项目复用或快速集成的场景。

```bash
# 使用 uv 安装 (推荐,速度快 10-100x)
uv pip install lark-service

# 或使用 pip 安装
pip install lark-service

# 或从源码安装
git clone https://github.com/your-org/lark-service.git
cd lark-service
uv pip install -e .
```

**使用方式**:

```python
# 直接导入,无需配置路径
from lark_service import LarkServiceClient
```

**优势**:
- ✅ 标准化,符合 Python 生态最佳实践
- ✅ 依赖自动安装
- ✅ 更新简单: `uv pip install --upgrade lark-service`

> 💡 **选择建议**: 开发阶段使用**子项目集成**,生产部署可选 **PyPI 安装**。详细对比见 [research.md § 8](specs/001-lark-service-core/research.md#8-服务集成方式技术调研)

### 5 分钟上手

详细的快速开始指南请参考: [quickstart.md](specs/001-lark-service-core/quickstart.md)

**1. 启动依赖服务**

```bash
# 启动 PostgreSQL 和 RabbitMQ
docker compose up -d postgres rabbitmq
```

**2. 配置环境变量**

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件,填入数据库配置和加密密钥
```

**3. 添加飞书应用配置**

```bash
# 使用 CLI 添加应用配置
python -m lark_service.cli app add \
  --app-id "cli_your_app_id" \
  --app-secret "your_app_secret" \
  --name "我的飞书应用"
```

**4. 开始使用**

```python
from lark_service.core.credential_pool import CredentialPool
from lark_service.messaging.client import MessagingClient
from lark_service.cardkit.builder import CardBuilder

# 初始化 Token 管理池
credential_pool = CredentialPool()

# 创建消息客户端
messaging_client = MessagingClient(credential_pool)

# 1. 发送文本消息
response = messaging_client.send_text_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_xxxxxxxx",
    content="Hello from Lark Service! 🚀"
)
print(f"消息发送成功! Message ID: {response['message_id']}")

# 2. 发送图片消息 (自动上传)
response = messaging_client.send_image_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_xxxxxxxx",
    image_path="/path/to/image.jpg"
)

# 3. 发送交互式卡片
builder = CardBuilder()
card = builder.build_notification_card(
    title="系统通知",
    content="您有一条新消息",
    level="info",
    action_text="查看详情",
    action_url="https://example.com"
)
response = messaging_client.send_card_message(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_id="ou_xxxxxxxx",
    card_content=card
)

# 4. 批量发送消息
response = messaging_client.send_batch_messages(
    app_id="cli_a1b2c3d4e5f6g7h8",
    receiver_ids=["ou_user1", "ou_user2", "ou_user3"],
    msg_type="text",
    content={"text": "群发消息"}
)
print(f"批量发送完成: {response.success}/{response.total} 成功")
```

## 📚 模块功能

### 🔐 Token 管理 (自动)

- ✅ 自动获取 `app_access_token`、`tenant_access_token`、`user_access_token`
- ✅ Token 过期前自动刷新 (提前 10% 时间窗口)
- ✅ PostgreSQL 持久化存储,服务重启后恢复
- ✅ 并发安全 (线程锁 + 进程锁)
- ✅ 多应用隔离 (按 `app_id` 隔离)

### 💬 Messaging 模块 (Phase 3 ✅)

#### 消息发送
- ✅ **文本消息** - 发送纯文本消息
- ✅ **富文本消息** - 支持格式化 (粗体、斜体、链接、@提及、删除线)
- ✅ **图片消息** - 支持 7 种格式 (JPG, PNG, GIF, BMP, TIFF, WebP, SVG),限制 10MB
- ✅ **文件消息** - 支持视频、音频、文档,限制 30MB
  - 视频: MP4, AVI, MOV, WMV
  - 音频: MP3, WAV, AAC, OGG
  - 文档: PDF, DOCX, XLS, PPTX, TXT
- ✅ **交互式卡片** - 支持审批卡片、通知卡片、表单卡片
- ✅ **批量发送** - 一次发送到最多 200 个接收者

#### 消息生命周期
- ✅ **消息撤回** - 撤回已发送的消息
- ✅ **消息编辑** - 编辑文本消息内容
- ✅ **消息回复** - 回复指定消息

#### 媒体处理
- ✅ **自动上传** - 图片和文件自动上传到飞书
- ✅ **文件验证** - 自动验证文件大小和类型
- ✅ **重试机制** - 上传失败自动重试 (最多 3 次)

### 📄 CloudDoc 模块

- ✅ **Doc 文档**: 创建、读取、更新、权限管理 (可阅读/可编辑/可评论/可管理)
- ✅ **Sheet 电子表格**: 读写、格式化 (样式/合并/列宽/冻结)
- ✅ **多维表格 (Bitable)**: CRUD、批量操作、过滤查询
- ✅ **文档素材**: 上传图片/文件到文档,下载文档素材

### 👥 Contact 模块

- ✅ 通过邮箱/手机号查询用户
- ✅ 获取用户多种 ID (`open_id`、`user_id`、`union_id`)
- ✅ PostgreSQL 本地缓存 (24 小时 TTL)
- ✅ 查询群组和部门信息

### 🤖 aPaaS 模块

- ✅ **数据空间表格**: CRUD 操作 (需要 `user_access_token`)
- ✅ **AI 能力调用**: 30 秒超时
- ✅ **工作流触发**: 自动化流程集成

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                          │
│            (Django / Flask / FastAPI / Airflow)              │
└───────────────────────────┬─────────────────────────────────┘
                            │ import lark_service
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Lark Service Client                         │
├─────────────┬──────────────┬──────────────┬─────────────────┤
│  Messaging  │  CloudDoc    │   Contact    │     aPaaS       │
└─────────────┴──────────────┴──────────────┴─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Token 凭证池 (自动管理)                          │
│  • 懒加载  • 自动刷新  • 并发安全  • 多应用隔离              │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  ┌──────────┐       ┌──────────┐       ┌──────────┐
  │ SQLite   │       │PostgreSQL│       │ RabbitMQ │
  │应用配置  │       │Token存储 │       │消息队列  │
  └──────────┘       └──────────┘       └──────────┘
```

详细架构文档: [docs/architecture.md](docs/architecture.md)

## 🔧 技术栈

### 核心技术

- **Python 3.12+** - 现代 Python 特性
- **SQLAlchemy 2.0** - ORM 与类型安全 (100% mypy 通过) ✅
- **Pydantic v2** - 数据验证与序列化
- **lark-oapi SDK** - 官方飞书 SDK

### 数据存储

- **PostgreSQL** - Token 持久化存储 (pg_crypto 加密)
- **SQLite** - 应用配置管理 (Fernet 加密)
- **RabbitMQ** - 异步消息队列

### 开发工具

- **Ruff** - 代码格式化与检查
- **Mypy** - 静态类型检查 (99%+ 覆盖率)
- **Pytest** - 测试框架 (76%+ 代码覆盖率)
- **Docker Compose** - 本地开发环境

### 核心特性

- ✅ **完整的类型安全** - SQLAlchemy 2.0 现代语法,0 个 mypy 错误
- ✅ **TDD 驱动开发** - 78 个测试用例,100% 通过率
- ✅ **高代码覆盖率** - 76.36% 总体覆盖率,核心逻辑 90%+
- ✅ **生产就绪** - 并发控制、重试策略、错误处理完善

> 📚 **SQLAlchemy 2.0 使用指南**: [docs/sqlalchemy-2.0-guide.md](docs/sqlalchemy-2.0-guide.md)

## 🛠️ 开发

### 环境准备

```bash
# 克隆仓库
git clone https://github.com/your-org/lark-service.git
cd lark-service

# 创建 Conda 环境 (推荐)
conda create -n lark-service python=3.12
conda activate lark-service

# 安装 uv (快速包管理器)
pip install uv

# 使用 uv 安装依赖
uv pip install -r requirements.txt

# 启动依赖服务
docker compose up -d
```

### 代码质量

```bash
# 代码格式化
ruff format src/ tests/

# 代码检查
ruff check src/ tests/

# 类型检查
mypy src/

# 运行测试
pytest tests/ -v --cov=src/lark_service
```

### 数据库迁移

```bash
# 创建迁移脚本
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 📖 文档

- [快速开始](specs/001-lark-service-core/quickstart.md) - 5 分钟上手指南
- [架构设计](docs/architecture.md) - 系统架构和设计决策
- [部署指南](docs/deployment.md) - Docker 部署和生产环境配置
- [API 参考](docs/api_reference.md) - 完整的 API 文档
- [技术规范](specs/001-lark-service-core/spec.md) - 功能需求和验收标准
- [技术调研](specs/001-lark-service-core/research.md) - 技术选型和最佳实践

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议!

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [飞书开放平台](https://open.feishu.cn/) - 提供强大的 OpenAPI
- [lark-oapi-python](https://github.com/larksuite/oapi-sdk-python) - 官方 Python SDK
- 所有贡献者和用户

## 📞 联系方式

- 问题反馈: [GitHub Issues](https://github.com/your-org/lark-service/issues)
- 邮件: support@example.com
- 文档: https://github.com/your-org/lark-service/docs

---

**Made with ❤️ by Lark Service Team**
