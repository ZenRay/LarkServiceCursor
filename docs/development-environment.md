# 开发环境配置指南

**版本**: 2.0.0  
**更新时间**: 2026-01-15

---

## 🎯 开发环境 vs 生产环境差异 (FR-093, CHK009)

本项目区分**开发环境**和**生产环境**,确保安全性和可维护性。

### 关键差异点

| 维度 | 开发环境 | 生产环境 |
|------|---------|---------|
| **加密密钥** | 测试密钥(`.env.development`) | 生产密钥(环境变量/Vault) |
| **数据库** | 本地 PostgreSQL/SQLite | 生产数据库集群 |
| **日志级别** | `DEBUG` | `INFO` |
| **数据持久化** | 可删除重建 | 必须备份和恢复 |
| **安全扫描** | 可选 | 强制(CI/CD) |
| **依赖管理** | 可以使用 `pip` | 必须使用 `uv` (速度) |
| **错误处理** | 详细堆栈信息 | 简化错误信息 |
| **性能要求** | 无严格要求 | 99.9% 可用性 |

### 环境配置文件

```bash
# 项目根目录结构
.
├── .env.development      # 开发环境配置 (可提交示例)
├── .env.production       # 生产环境配置 (禁止提交)
├── .env.ci               # CI 环境配置
└── .env.example          # 配置模板
```

**开发环境配置示例** (`.env.development`):
```bash
# 开发环境 - 使用弱密钥和本地数据库
LARK_CONFIG_ENCRYPTION_KEY=dev-test-key-for-local-development-only==
LOG_LEVEL=DEBUG
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password_123
```

**生产环境配置** (环境变量注入):
```bash
# 生产环境 - 使用强密钥和生产数据库
export LARK_CONFIG_ENCRYPTION_KEY="<从 Vault 获取>"
export LOG_LEVEL=INFO
export POSTGRES_HOST=prod-db.internal
export POSTGRES_DB=lark_service
export POSTGRES_PASSWORD="<从 Vault 获取>"
```

### 环境检测

代码中可以通过环境变量检测当前环境:

```python
import os

ENV = os.getenv("ENVIRONMENT", "development")  # development/production/ci

if ENV == "production":
    # 生产环境逻辑
    assert os.getenv("LARK_CONFIG_ENCRYPTION_KEY"), "Encryption key required"
else:
    # 开发环境逻辑
    pass
```

---

## 1. 环境管理

### 1.1 Conda 环境管理 (推荐)

本项目使用 **Conda** 进行 Python 环境管理,提供更好的依赖隔离和版本控制。

#### 安装 Conda

如果还没有安装 Conda,请选择以下方式之一:

**Miniconda (推荐,轻量级)**:
```bash
# Linux/Mac
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# 或使用 Homebrew (Mac)
brew install --cask miniconda
```

**Anaconda (完整版)**:
```bash
# 访问 https://www.anaconda.com/download 下载安装包
```

#### 创建项目环境

```bash
# 创建 Python 3.12 环境
conda create -n lark-service python=3.12

# 激活环境
conda activate lark-service

# 验证 Python 版本
python --version  # 应该显示 Python 3.12.x
```

#### 环境管理命令

```bash
# 列出所有环境
conda env list

# 激活环境
conda activate lark-service

# 退出环境
conda deactivate

# 删除环境
conda env remove -n lark-service

# 导出环境配置
conda env export > environment.yml

# 从配置文件创建环境
conda env create -f environment.yml
```

---

## 2. 包管理

### 2.1 uv - 快速 Python 包管理器 (推荐)

本项目使用 **uv** 作为包管理器,它比传统的 `pip` 快 10-100 倍。

#### 安装 uv

```bash
# 在 Conda 环境中安装 uv
conda activate lark-service
pip install uv
```

#### 使用 uv 安装依赖

```bash
# 安装项目依赖
uv pip install -r requirements.txt

# 安装单个包
uv pip install package-name

# 安装开发模式
uv pip install -e .

# 安装开发依赖
uv pip install -e ".[dev]"
```

#### uv 优势

| 特性 | pip | uv | 提升 |
|------|-----|----|----|
| **安装速度** | 慢 | 极快 | 10-100x |
| **依赖解析** | 慢 | 快 | 10x |
| **并行下载** | 否 | 是 | ✅ |
| **缓存机制** | 基础 | 高级 | ✅ |
| **兼容性** | 100% | 100% | ✅ |

### 2.2 pip (备选方案)

如果不使用 uv,也可以使用传统的 pip:

```bash
# 安装依赖
pip install -r requirements.txt

# 安装开发模式
pip install -e .
```

---

## 3. Docker 环境

### 3.1 Docker 版本确认

本项目使用 **Docker Compose V2** (命令为 `docker compose`,不是 `docker-compose`)。

#### 检查 Docker 版本

```bash
# 检查 Docker 版本
docker --version
# 应该显示: Docker version 20.10+ 或更高

# 检查 Docker Compose 版本
docker compose version
# 应该显示: Docker Compose version v2.x.x 或更高
```

#### 如果使用旧版本 docker-compose

如果系统中仍使用旧版本的 `docker-compose` (V1),建议升级到 V2:

```bash
# 卸载旧版本 (如果通过 pip 安装)
pip uninstall docker-compose

# 安装 Docker Desktop (包含 Compose V2)
# 或手动安装 Compose V2 插件
# 参考: https://docs.docker.com/compose/install/
```

#### Docker Compose 命令对比

| 操作 | V1 (旧) | V2 (新,本项目使用) |
|------|---------|-------------------|
| 启动服务 | `docker-compose up` | `docker compose up` |
| 停止服务 | `docker-compose down` | `docker compose down` |
| 查看状态 | `docker-compose ps` | `docker compose ps` |
| 查看日志 | `docker-compose logs` | `docker compose logs` |
| 构建镜像 | `docker-compose build` | `docker compose build` |

**注意**: 本项目所有文档中使用 `docker compose` (V2 命令)。

---

## 4. 完整开发环境设置

### 4.1 首次设置

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/lark-service.git
cd lark-service

# 2. 创建 Conda 环境
conda create -n lark-service python=3.12
conda activate lark-service

# 3. 安装 uv
pip install uv

# 4. 安装项目依赖
uv pip install -r requirements.txt

# 5. 安装开发依赖
uv pip install -e ".[dev]"

# 6. 启动依赖服务
docker compose up -d postgres rabbitmq

# 7. 验证环境
python --version
docker compose ps
```

### 4.2 日常开发流程

```bash
# 1. 激活环境
conda activate lark-service

# 2. 启动依赖服务 (如果未运行)
docker compose up -d

# 3. 运行测试
pytest tests/ -v

# 4. 代码检查
ruff check src/ tests/
mypy src/

# 5. 代码格式化
ruff format src/ tests/

# 6. 完成后停止服务
docker compose down
```

---

## 5. IDE 配置

### 5.1 VS Code / Cursor

**推荐配置** (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.conda/envs/lark-service/bin/python",
  "python.formatting.provider": "none",
  "python.linting.enabled": false,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests",
    "-v"
  ]
}
```

**推荐扩展**:
- Python (Microsoft)
- Ruff (Astral Software)
- Mypy Type Checker
- Docker
- YAML

### 5.2 PyCharm

1. **配置 Conda 解释器**:
   - File → Settings → Project → Python Interpreter
   - Add Interpreter → Conda Environment
   - 选择 `lark-service` 环境

2. **配置 Ruff**:
   - File → Settings → Tools → External Tools
   - 添加 Ruff 作为外部工具

3. **配置 Docker**:
   - File → Settings → Build, Execution, Deployment → Docker
   - 连接到 Docker daemon

---

## 6. 环境变量管理

### 6.1 开发环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
vim .env  # 或使用其他编辑器
```

### 6.2 .env 文件示例

```bash
# PostgreSQL (本地开发)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark
POSTGRES_PASSWORD=dev_password_123

# RabbitMQ (本地开发)
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=lark
RABBITMQ_PASSWORD=dev_password_123

# 加密密钥 (开发环境)
LARK_CONFIG_ENCRYPTION_KEY=$(openssl rand -base64 32)

# 日志级别
LOG_LEVEL=DEBUG
```

### 6.3 环境变量加载

项目使用 `python-dotenv` 自动加载 `.env` 文件:

```python
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()

# 读取环境变量
postgres_host = os.getenv("POSTGRES_HOST", "localhost")
```

---

## 7. 常见问题

### 7.1 Conda 环境问题

**问题**: `conda: command not found`

**解决**:
```bash
# 初始化 Conda
conda init bash  # 或 zsh, fish 等
source ~/.bashrc  # 或 ~/.zshrc
```

### 7.2 uv 安装问题

**问题**: `uv: command not found`

**解决**:
```bash
# 确保在 Conda 环境中
conda activate lark-service

# 重新安装 uv
pip install --upgrade uv
```

### 7.3 Docker Compose 命令问题

**问题**: `docker compose: command not found`

**解决**:
```bash
# 检查是否安装了 Compose V2
docker compose version

# 如果只有 V1,使用旧命令
docker-compose up -d

# 或升级到 Compose V2
# 参考: https://docs.docker.com/compose/install/
```

### 7.4 Python 版本问题

**问题**: Python 版本不是 3.12

**解决**:
```bash
# 删除旧环境
conda env remove -n lark-service

# 创建新环境并指定版本
conda create -n lark-service python=3.12

# 激活并验证
conda activate lark-service
python --version
```

---

## 8. 性能优化建议

### 8.1 使用 uv 加速安装

```bash
# 使用 uv 替代 pip,速度提升 10-100x
uv pip install -r requirements.txt
```

### 8.2 使用 Conda 缓存

```bash
# 配置 Conda 缓存目录
conda config --set pkgs_dirs ~/.conda/pkgs

# 清理缓存 (如果空间不足)
conda clean --all
```

### 8.3 Docker 镜像加速

```bash
# 配置 Docker 镜像加速器 (中国大陆)
# 编辑 /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}

# 重启 Docker
sudo systemctl restart docker
```

---

## 9. 环境检查清单

在开始开发前,请确认以下环境已正确配置:

```bash
# ✅ Conda 环境
conda --version
conda activate lark-service
python --version  # 应该是 3.12.x

# ✅ uv 包管理器
uv --version

# ✅ Docker
docker --version
docker compose version

# ✅ 依赖服务
docker compose ps  # PostgreSQL 和 RabbitMQ 应该是 Up 状态

# ✅ 项目依赖
python -c "import lark_oapi; import pydantic; import sqlalchemy; print('✅ 依赖已安装')"

# ✅ 代码质量工具
ruff --version
mypy --version
pytest --version
```

---

## 10. 总结

### 环境配置要点

| 组件 | 工具 | 版本 | 说明 |
|------|------|------|------|
| **Python 环境** | Conda | Latest | 环境隔离和版本管理 |
| **Python 版本** | Python | 3.12+ | 项目要求 |
| **包管理器** | uv | Latest | 快速安装依赖 (10-100x) |
| **容器化** | Docker | 20.10+ | 依赖服务 |
| **编排工具** | Docker Compose | V2 | 使用 `docker compose` 命令 |
| **ORM** | SQLAlchemy | 2.0+ | 现代类型安全语法 ✅ |

### 技术亮点

- ✅ **SQLAlchemy 2.0**: 使用 `DeclarativeBase` + `Mapped[T]` 类型注解
- ✅ **100% 类型安全**: Mypy 0 个错误,完美的类型推断
- ✅ **76%+ 代码覆盖率**: 78 个测试用例全部通过
- ✅ **现代 Python**: PEP 604 联合类型 (`str | None`)

### 快速开始命令

```bash
# 一键设置开发环境
conda create -n lark-service python=3.12 && \
conda activate lark-service && \
pip install uv && \
uv pip install -r requirements.txt && \
docker compose up -d && \
echo "✅ 开发环境已就绪!"
```

---

**维护者**: Lark Service Team  
**最后更新**: 2026-01-15  
**版本**: 1.0.0
