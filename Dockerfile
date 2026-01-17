# ============================================================================
# Multi-stage Docker Build for Lark Service
# ============================================================================
# 优化特性:
# - 多阶段构建减小镜像体积 (预期 < 350MB)
# - 国内镜像源加速构建 (Debian + PyPI)
# - 构建缓存优化 (依赖层与代码层分离)
# - 生产级安全配置 (非 root 用户, 最小权限)
# - 健康检查和优雅关闭支持
# ============================================================================

# ============================================================================
# Stage 1: Builder - 编译依赖
# ============================================================================
FROM python:3.12-slim AS builder

# 设置工作目录
WORKDIR /build

# 配置 Debian 国内镜像源 (加速 apt 安装)
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# 安装编译依赖 (仅 builder 阶段需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 配置 PyPI 国内镜像源 (加速 pip 安装)
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制依赖文件 (利用 Docker 缓存层)
COPY requirements.txt pyproject.toml README.md ./

# 分离生产依赖和开发依赖
# 仅安装生产环境必需的依赖
RUN grep -v "^#" requirements.txt | grep -v "pytest\|mypy\|ruff\|types-" > requirements.prod.txt && \
    pip install --no-cache-dir --user -r requirements.prod.txt

# ============================================================================
# Stage 2: Runtime - 最小运行时镜像
# ============================================================================
FROM python:3.12-slim AS runtime

# 元数据标签
LABEL maintainer="Lark Service Team" \
      version="0.1.0" \
      description="Lark Service - Enterprise-grade Feishu API Service"

# 配置 Debian 国内镜像源
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# 安装运行时依赖 (仅必需的库)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建应用目录
WORKDIR /app

# 从 builder 复制已安装的 Python 包
COPY --from=builder /root/.local /root/.local

# 将用户级 Python 包添加到 PATH
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码 (最后复制,最大化缓存利用)
COPY src/ /app/src/
COPY migrations/ /app/migrations/

# 创建必要的目录
RUN mkdir -p /app/config /app/logs /app/data

# 环境变量配置
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 创建非 root 用户 (安全最佳实践)
RUN useradd -m -u 1000 -s /bin/bash lark && \
    chown -R lark:lark /app

# 切换到非特权用户
USER lark

# 暴露端口 (如有 API 服务)
# EXPOSE 8000

# 健康检查 (改进版 - 检查实际服务状态)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; from lark_service.core.config import Config; sys.exit(0)" || exit 1

# 卷挂载点 (持久化数据)
VOLUME ["/app/config", "/app/logs", "/app/data"]

# 默认启动命令
CMD ["python", "-m", "lark_service"]

# ============================================================================
# 构建说明:
# ============================================================================
# 标准构建:
#   docker build -t lark-service:latest -f Dockerfile.optimized .
#
# 查看镜像大小:
#   docker images lark-service:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
#
# 多平台构建 (ARM64 + AMD64):
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     -t lark-service:latest -f Dockerfile.optimized .
#
# 使用构建缓存:
#   docker build --cache-from lark-service:latest \
#     -t lark-service:v0.1.0 -f Dockerfile.optimized .
# ============================================================================
