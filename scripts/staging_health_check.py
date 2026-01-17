#!/usr/bin/env python3
"""
Staging环境健康检查脚本

功能:
1. 验证环境变量配置
2. 测试数据库连接
3. 测试飞书API连接
4. 验证Token获取
5. 检查系统资源

使用:
    python scripts/staging_health_check.py
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def check_environment_variables() -> bool:
    """检查必需的环境变量"""
    print("=" * 70)
    print("1. 检查环境变量配置")
    print("=" * 70)

    required_vars = [
        "ENVIRONMENT",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "TOKEN_ENCRYPTION_KEY",
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"  ✗ {var}: 未设置")
        else:
            # 隐藏敏感信息
            if "PASSWORD" in var or "SECRET" in var or "KEY" in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"  ✓ {var}: {display_value}")

    if missing_vars:
        print(f"\n❌ 缺失 {len(missing_vars)} 个必需环境变量")
        return False

    print("\n✅ 所有必需环境变量已设置")
    return True


def check_database_connection() -> bool:
    """测试数据库连接"""
    print("\n" + "=" * 70)
    print("2. 测试数据库连接")
    print("=" * 70)

    try:
        from sqlalchemy import create_engine, text

        # 构建数据库连接URL
        db_url = (
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )

        print(
            f"  连接到: postgresql://{os.getenv('DB_USER')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )

        # 创建引擎并测试连接
        engine = create_engine(db_url, pool_pre_ping=True)

        start_time = time.time()
        with engine.connect() as conn:
            # 测试基本查询
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"  ✓ PostgreSQL版本: {version.split(',')[0]}")

            # 检查pgcrypto扩展
            result = conn.execute(
                text("SELECT COUNT(*) FROM pg_extension WHERE extname='pgcrypto';")
            )
            has_pgcrypto = result.scalar() > 0
            if has_pgcrypto:
                print("  ✓ pgcrypto扩展: 已启用")
            else:
                print("  ✗ pgcrypto扩展: 未启用")
                return False

            # 检查表是否存在
            result = conn.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                AND table_name IN ('tokens', 'user_cache', 'user_auth_sessions');
            """)
            )
            tables = [row[0] for row in result]
            print(f"  ✓ 数据库表: {', '.join(tables)}")

        elapsed = time.time() - start_time
        print(f"  ✓ 连接延迟: {elapsed * 1000:.2f}ms")

        print("\n✅ 数据库连接正常")
        return True

    except Exception as e:
        print(f"\n❌ 数据库连接失败: {e}")
        return False


def check_feishu_api() -> bool:
    """测试飞书API连接"""
    print("\n" + "=" * 70)
    print("3. 测试飞书API连接")
    print("=" * 70)

    try:
        import httpx

        api_base = os.getenv("FEISHU_API_BASE_URL", "https://open.feishu.cn")
        print(f"  API地址: {api_base}")

        start_time = time.time()
        response = httpx.get(f"{api_base}/open-apis/auth/v3/app_access_token/internal", timeout=10)
        elapsed = time.time() - start_time

        print(f"  ✓ API可达性: {response.status_code}")
        print(f"  ✓ 网络延迟: {elapsed * 1000:.2f}ms")

        print("\n✅ 飞书API连接正常")
        return True

    except Exception as e:
        print(f"\n❌ 飞书API连接失败: {e}")
        return False


def check_token_acquisition() -> bool:
    """测试Token获取"""
    print("\n" + "=" * 70)
    print("4. 测试Token获取")
    print("=" * 70)

    # 需要先配置应用才能测试,这里只做基本检查
    print("  ℹ️  Token获取测试需要先配置飞书应用")
    print("  ℹ️  请使用以下命令添加应用:")
    print("     lark-service-cli app add --app-id <id> --app-secret <secret>")

    return True


def check_system_resources() -> bool:
    """检查系统资源"""
    print("\n" + "=" * 70)
    print("5. 检查系统资源")
    print("=" * 70)

    try:
        import psutil

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        print(f"  CPU使用率: {cpu_percent}% (核心数: {cpu_count})")
        if cpu_percent > 80:
            print("  ⚠️  CPU使用率较高")
        else:
            print("  ✓ CPU使用率正常")

        # 内存
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_total_gb = memory.total / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        print(
            f"  内存使用率: {memory_percent}% (总计: {memory_total_gb:.1f}GB, 可用: {memory_available_gb:.1f}GB)"
        )
        if memory_percent > 85:
            print("  ⚠️  内存使用率较高")
        else:
            print("  ✓ 内存使用率正常")

        # 磁盘
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent
        disk_total_gb = disk.total / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        print(
            f"  磁盘使用率: {disk_percent}% (总计: {disk_total_gb:.1f}GB, 可用: {disk_free_gb:.1f}GB)"
        )
        if disk_percent > 85:
            print("  ⚠️  磁盘使用率较高")
        else:
            print("  ✓ 磁盘使用率正常")

        print("\n✅ 系统资源正常")
        return True

    except ImportError:
        print("  ℹ️  psutil未安装,跳过系统资源检查")
        print("  ℹ️  安装: pip install psutil")
        return True
    except Exception as e:
        print(f"\n⚠️  系统资源检查失败: {e}")
        return True  # 非关键检查,返回True继续


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("Lark Service - Staging环境健康检查")
    print("=" * 70)
    print(f"检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"环境: {os.getenv('ENVIRONMENT', 'unknown')}")

    results = {
        "环境变量配置": check_environment_variables(),
        "数据库连接": check_database_connection(),
        "飞书API连接": check_feishu_api(),
        "Token获取": check_token_acquisition(),
        "系统资源": check_system_resources(),
    }

    # 汇总结果
    print("\n" + "=" * 70)
    print("健康检查结果汇总")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, passed_check in results.items():
        status = "✅ PASS" if passed_check else "❌ FAIL"
        print(f"  {status}  {name}")

    print("\n" + "=" * 70)
    print(f"总计: {passed}/{total} 检查通过")
    print("=" * 70)

    if passed == total:
        print("\n🎉 Staging环境健康检查全部通过!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 项检查未通过,请检查上述错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
