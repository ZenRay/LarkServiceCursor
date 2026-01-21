#!/bin/bash
# ============================================================================
# Lark Service - 服务器初始化脚本 (网络优化版)
# ============================================================================
# 特点：针对国内网络优化，使用 GitHub 代理加速 uv 和 Python 的下载速度。
# ============================================================================

set -e
set -u

APP_NAME="lark-service"
APP_USER="lark"
APP_DIR="/opt/lark-service"
PYTHON_VERSION="3.12"

# 代理配置 (国内加速)
GH_PROXY="https://mirror.ghproxy.com/"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本必须以root权限运行"
        exit 1
    fi
}

detect_os() {
    log_info "正在检测操作系统..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    fi
    log_info "✓ 检测到系统: $OS"
}

install_base_tools() {
    log_info "正在预检基础工具 (git, curl, ca-certificates)..."
    MISSING_TOOLS=()
    for tool in git curl ca-certificates; do
        if ! command -v $tool &> /dev/null; then
            MISSING_TOOLS+=($tool)
        fi
    done

    if [ ${#MISSING_TOOLS[@]} -eq 0 ]; then
        log_info "✓ 基础工具已齐全，跳过安装。"
    else
        log_info "正在安装缺失工具: ${MISSING_TOOLS[*]}..."
        case $OS in
            ubuntu|debian)
                apt-get update -qq
                apt-get install -y -qq ${MISSING_TOOLS[*]}
                ;;
            *)
                log_warn "非 Ubuntu/Debian 系统，请手动安装: ${MISSING_TOOLS[*]}"
                ;;
        esac
    fi
}

install_docker() {
    log_info "正在预检 Docker 环境..."
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        log_info "✓ Docker 及 Compose 插件已就绪，跳过安装。"
        return 0
    fi

    log_info "正在安装 Docker (使用国内镜像源)..."
    # 使用阿里云镜像脚本安装
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl start docker
    systemctl enable docker
    log_info "✓ Docker 安装完成。"
}

install_uv_and_python() {
    log_info "正在预检 uv 及隔离 Python 环境 (已启用 GitHub 加速)..."

    # 1. 检查 uv
    if ! command -v uv &> /dev/null; then
        log_info "正在安装 uv (通过代理加速)..."
        # 使用代理下载安装脚本并传递 INSTALLER_URL 环境变量 (如果安装脚本支持)
        # 很多时候直接代理脚本内容即可
        curl -LsSf "${GH_PROXY}https://raw.githubusercontent.com/astral-sh/uv/main/install.sh" | sh

        # 立即加载 PATH
        export PATH="$HOME/.local/bin:$PATH"
        export PATH="$HOME/.cargo/bin:$PATH"
    else
        log_info "✓ uv 已安装。"
    fi

    # 2. 配置加速环境变量
    log_info "配置国内下载加速源..."
    export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
    # 核心：让 uv 通过代理下载 Python 二进制包 (python-build-standalone)
    export UV_PYTHON_INSTALL_MIRROR="${GH_PROXY}https://github.com/indygreg/python-build-standalone/releases/download"

    # 3. 检查 Python 3.12
    if uv python list | grep -q "$PYTHON_VERSION"; then
        log_info "✓ 隔离版 Python $PYTHON_VERSION 已就绪。"
    else
        log_info "正在通过加速通道下载 Python $PYTHON_VERSION (这通常需要 10-30 秒)..."
        uv python install $PYTHON_VERSION
    fi
}

create_app_user() {
    log_info "正在检查应用用户和权限..."
    if ! id "$APP_USER" &>/dev/null; then
        useradd -r -m -s /bin/bash $APP_USER
        log_info "✓ 用户 $APP_USER 创建成功。"
    fi
    if ! id -nG "$APP_USER" | grep -qw "docker"; then
        usermod -aG docker $APP_USER
        log_info "✓ 已将 $APP_USER 添加至 docker 组。"
    fi
}

setup_dirs() {
    log_info "正在检查并配置系统目录..."
    DIRS=("$APP_DIR" "/var/log/lark-service" "/backup/lark-service" "/etc/lark-service")
    for dir in "${DIRS[@]}"; do
        [ ! -d "$dir" ] && mkdir -p "$dir"
    done
    chown -R $APP_USER:$APP_USER "$APP_DIR" "/var/log/lark-service" "/backup/lark-service" "/etc/lark-service"
    chmod 755 "$APP_DIR"
    log_info "✓ 目录权限配置完成。"
}

main() {
    check_root
    detect_os
    install_base_tools
    install_docker
    install_uv_and_python
    create_app_user
    setup_dirs

    log_info "========================================"
    log_info "  服务器初始化完成 (加速通道已启用)！"
    log_info "========================================"
    log_info "后续步骤提示："
    log_info "1. 代码位置: $APP_DIR"
    log_info "2. 执行部署: cd $APP_DIR && bash deploy/scripts/deploy.sh"
}

main "$@"
