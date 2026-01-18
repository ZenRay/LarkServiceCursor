#!/usr/bin/env python3
"""
环境变量配置验证脚本

功能:
1. 验证必需的环境变量是否存在
2. 验证环境变量格式是否正确
3. 检查密钥是否为示例值

使用:
    python scripts/validate_env.py [env_file]

示例:
    python scripts/validate_env.py .env.staging
"""

import re
import sys
from pathlib import Path

# 必需的环境变量及其验证规则
REQUIRED_ENV_VARS = {
    "ENVIRONMENT": {
        "required": True,
        "pattern": r"^(development|staging|production)$",
        "description": "环境标识",
    },
    "DB_HOST": {
        "required": True,
        "description": "数据库主机地址",
    },
    "DB_PORT": {
        "required": True,
        "pattern": r"^\d{1,5}$",
        "description": "数据库端口",
    },
    "DB_NAME": {
        "required": True,
        "description": "数据库名称",
    },
    "DB_USER": {
        "required": True,
        "description": "数据库用户名",
    },
    "DB_PASSWORD": {
        "required": True,
        "sensitive": True,
        "min_length": 12,
        "description": "数据库密码",
    },
    "TOKEN_ENCRYPTION_KEY": {
        "required": True,
        "sensitive": True,
        "pattern": r"^[A-Za-z0-9+/=_-]{32,}$",
        "description": "Token加密密钥 (Fernet key)",
    },
    "LOG_LEVEL": {
        "required": False,
        "pattern": r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        "default": "INFO",
        "description": "日志级别",
    },
    "LOG_FORMAT": {
        "required": False,
        "pattern": r"^(json|text)$",
        "default": "json",
        "description": "日志格式",
    },
}

# 示例值/不安全的值 (不应该在配置文件中使用)
EXAMPLE_VALUES = [
    "<REPLACE_WITH_",
    "example.com",
    "password123",
    "secret123",
    "your-",
    "my-",
]


def load_env_file(file_path: Path) -> dict[str, str]:
    """加载环境变量文件"""
    env_vars = {}

    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)

    with open(file_path, encoding="utf-8") as f:
        for _line_num, line in enumerate(f, 1):
            line = line.strip()

            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue

            # 解析 KEY=VALUE
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # 移除引号
                if (
                    value.startswith('"')
                    and value.endswith('"')
                    or value.startswith("'")
                    and value.endswith("'")
                ):
                    value = value[1:-1]

                env_vars[key] = value

    return env_vars


def validate_env_vars(env_vars: dict[str, str]) -> tuple[list[str], list[str]]:
    """验证环境变量"""
    errors = []
    warnings = []

    print("=" * 70)
    print("环境变量验证")
    print("=" * 70)

    # 检查必需变量
    for var_name, config in REQUIRED_ENV_VARS.items():
        value = env_vars.get(var_name)

        # 检查是否存在
        if config.get("required") and not value:
            errors.append(f"缺失必需变量: {var_name} - {config['description']}")
            print(f"  ✗ {var_name}: 缺失 (必需)")
            continue

        if not value:
            # 可选变量未设置
            default = config.get("default")
            if default:
                print(f"  ○ {var_name}: 未设置 (将使用默认值: {default})")
            continue

        # 显示值 (隐藏敏感信息)
        if config.get("sensitive"):
            display_value = f"{value[:8]}..." if len(value) > 8 else "***"
        else:
            display_value = value if len(value) < 50 else f"{value[:47]}..."

        # 检查格式
        pattern = config.get("pattern")
        if pattern and not re.match(pattern, value):
            errors.append(f"格式错误: {var_name} (期望: {pattern}, 实际: {value})")
            print(f"  ✗ {var_name}: {display_value} (格式错误)")
            continue

        # 检查最小长度
        min_length = config.get("min_length")
        if min_length and len(value) < min_length:
            errors.append(f"长度不足: {var_name} (期望 >= {min_length}, 实际: {len(value)})")
            print(f"  ✗ {var_name}: {display_value} (长度不足: {len(value)} < {min_length})")
            continue

        # 检查是否为示例值
        is_example = any(example in value for example in EXAMPLE_VALUES)
        if is_example:
            errors.append(f"使用了示例值: {var_name} (请替换为实际值)")
            print(f"  ✗ {var_name}: {display_value} (示例值,需替换)")
            continue

        print(f"  ✓ {var_name}: {display_value}")

    # 检查常见错误
    if env_vars.get("ENVIRONMENT") == "production":
        if "test" in env_vars.get("DB_NAME", "").lower():
            warnings.append("生产环境使用了测试数据库名称")
        if "staging" in env_vars.get("DB_NAME", "").lower():
            warnings.append("生产环境使用了staging数据库名称")

    return errors, warnings


def main():
    """主函数"""
    # 获取环境文件路径
    if len(sys.argv) > 1:
        env_file = Path(sys.argv[1])
    else:
        print("用法: python scripts/validate_env.py <env_file>")
        print("示例: python scripts/validate_env.py .env.staging")
        sys.exit(1)

    print(f"\n验证环境配置: {env_file}\n")

    # 加载环境变量
    env_vars = load_env_file(env_file)
    print(f"加载了 {len(env_vars)} 个环境变量\n")

    # 验证环境变量
    errors, warnings = validate_env_vars(env_vars)

    # 显示结果
    print("\n" + "=" * 70)
    print("验证结果")
    print("=" * 70)

    if errors:
        print(f"\n❌ 发现 {len(errors)} 个错误:\n")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 个警告:\n")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

    if not errors and not warnings:
        print("\n✅ 所有环境变量验证通过!")
        print("\n下一步:")
        print(f"  1. 加载环境变量: export $(cat {env_file} | grep -v '^#' | xargs)")
        print("  2. 运行健康检查: python scripts/staging_health_check.py")
        return 0
    elif not errors:
        print(f"\n✅ 环境变量验证通过 (有 {len(warnings)} 个警告)")
        return 0
    else:
        print("\n❌ 环境变量验证失败,请修复上述错误")
        return 1


if __name__ == "__main__":
    sys.exit(main())
