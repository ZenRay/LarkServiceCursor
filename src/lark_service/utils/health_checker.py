"""
健康检查工具模块

提供各种组件的健康检查功能。
"""

import os
import time
from typing import Any

import psutil


class HealthChecker:
    """健康检查器"""

    def __init__(self) -> None:
        self.results: dict[str, Any] = {}

    def run_checks(self, checks: list[str], exit_on_error: bool = False) -> dict[str, Any]:
        """
        运行指定的健康检查

        Args:
            checks: 要运行的检查列表
            exit_on_error: 是否在遇到错误时立即退出

        Returns:
            检查结果字典
        """
        results: dict[str, Any] = {
            "timestamp": time.time(),
            "checks": {},
            "overall_status": "healthy",
            "summary": {"total": 0, "passed": 0, "failed": 0, "warnings": 0},
        }

        for check_name in checks:
            check_method = getattr(self, f"check_{check_name}", None)
            if check_method:
                try:
                    result = check_method()
                    results["checks"][check_name] = result
                    results["summary"]["total"] += 1

                    if result["status"] == "healthy":
                        results["summary"]["passed"] += 1
                    elif result["status"] == "degraded":
                        results["summary"]["warnings"] += 1
                        if results["overall_status"] == "healthy":
                            results["overall_status"] = "degraded"
                    else:
                        results["summary"]["failed"] += 1
                        results["overall_status"] = "unhealthy"
                        if exit_on_error:
                            break
                except Exception as e:
                    results["checks"][check_name] = {
                        "status": "error",
                        "message": f"检查执行失败: {str(e)}",
                    }
                    results["summary"]["total"] += 1
                    results["summary"]["failed"] += 1
                    results["overall_status"] = "unhealthy"
                    if exit_on_error:
                        break

        return results

    def check_config(self) -> dict[str, Any]:
        """检查配置"""
        try:
            from lark_service.core.config import Config

            # 尝试加载配置
            _ = Config.from_env()  # type: ignore[attr-defined] # 验证配置可以加载

            # 验证必需的配置项
            required_vars = [
                "POSTGRES_HOST",
                "POSTGRES_DB",
                "POSTGRES_USER",
                "REDIS_HOST",
            ]

            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)

            if missing_vars:
                return {
                    "status": "unhealthy",
                    "message": f"缺少必需的环境变量: {', '.join(missing_vars)}",
                }

            return {"status": "healthy", "message": "配置验证通过"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"配置加载失败: {str(e)}"}

    def check_database(self) -> dict[str, Any]:
        """检查数据库连接"""
        try:
            import psycopg2

            from lark_service.core.config import Config

            config = Config.from_env()  # type: ignore[attr-defined]

            # 测试连接
            conn = psycopg2.connect(
                host=config.postgres_host,
                port=config.postgres_port,
                database=config.postgres_db,
                user=config.postgres_user,
                password=config.postgres_password,
                connect_timeout=5,
            )

            # 执行简单查询
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()

            # 检查连接数
            cursor.execute("SELECT count(*) FROM pg_stat_activity")
            result = cursor.fetchone()
            conn_count = result[0] if result else 0

            cursor.close()
            conn.close()

            if conn_count > 90:
                status = "degraded"
                message = f"数据库连接正常，但连接数较高 ({conn_count})"
            else:
                status = "healthy"
                message = f"数据库连接正常 (活跃连接: {conn_count})"

            return {
                "status": status,
                "message": message,
                "details": {
                    "host": config.postgres_host,
                    "port": config.postgres_port,
                    "database": config.postgres_db,
                    "active_connections": conn_count,
                },
            }
        except Exception as e:
            return {"status": "unhealthy", "message": f"数据库连接失败: {str(e)}"}

    def check_redis(self) -> dict[str, Any]:
        """检查Redis连接"""
        try:
            import redis  # type: ignore[import-untyped]

            from lark_service.core.config import Config

            config = Config.from_env()  # type: ignore[attr-defined]  # type: ignore[attr-defined]

            # 连接Redis
            client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password if hasattr(config, "redis_password") else None,
                socket_connect_timeout=5,
            )

            # 测试连接
            client.ping()

            # 获取info
            info = client.info()
            used_memory_human = info.get("used_memory_human", "N/A")
            connected_clients = info.get("connected_clients", 0)

            return {
                "status": "healthy",
                "message": "Redis连接正常",
                "details": {
                    "host": config.redis_host,
                    "port": config.redis_port,
                    "used_memory": used_memory_human,
                    "connected_clients": connected_clients,
                },
            }
        except Exception as e:
            return {"status": "unhealthy", "message": f"Redis连接失败: {str(e)}"}

    def check_rabbitmq(self) -> dict[str, Any]:
        """检查RabbitMQ连接"""
        try:
            import pika

            from lark_service.core.config import Config

            config = Config.from_env()  # type: ignore[attr-defined]

            # 连接RabbitMQ
            credentials = pika.PlainCredentials(
                config.rabbitmq_user if hasattr(config, "rabbitmq_user") else "guest",
                config.rabbitmq_password if hasattr(config, "rabbitmq_password") else "guest",
            )
            parameters = pika.ConnectionParameters(
                host=config.rabbitmq_host if hasattr(config, "rabbitmq_host") else "localhost",
                port=config.rabbitmq_port if hasattr(config, "rabbitmq_port") else 5672,
                credentials=credentials,
                connection_attempts=3,
                retry_delay=1,
            )

            connection = pika.BlockingConnection(parameters)
            _ = connection.channel()  # 验证可以创建 channel

            # 检查连接
            if connection.is_open:
                connection.close()
                return {"status": "healthy", "message": "RabbitMQ连接正常"}
            else:
                return {"status": "unhealthy", "message": "RabbitMQ连接关闭"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"RabbitMQ连接失败: {str(e)}"}

    def check_api(self) -> dict[str, Any]:
        """检查飞书API连通性"""
        try:
            import requests

            # 测试飞书API连通性
            response = requests.get("https://open.feishu.cn", timeout=10)

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "message": "飞书API连通性正常",
                    "details": {"response_time_ms": int(response.elapsed.total_seconds() * 1000)},
                }
            else:
                return {
                    "status": "degraded",
                    "message": f"飞书API返回异常状态码: {response.status_code}",
                }
        except Exception as e:
            return {"status": "unhealthy", "message": f"飞书API连接失败: {str(e)}"}

    def check_disk(self) -> dict[str, Any]:
        """检查磁盘空间"""
        try:
            disk = psutil.disk_usage("/")

            percent_used = disk.percent

            if percent_used > 90:
                status = "unhealthy"
                message = f"磁盘空间严重不足: {percent_used}% 已使用"
            elif percent_used > 80:
                status = "degraded"
                message = f"磁盘空间不足: {percent_used}% 已使用"
            else:
                status = "healthy"
                message = f"磁盘空间充足: {percent_used}% 已使用"

            return {
                "status": status,
                "message": message,
                "details": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent_used": percent_used,
                },
            }
        except Exception as e:
            return {"status": "error", "message": f"磁盘检查失败: {str(e)}"}

    def check_memory(self) -> dict[str, Any]:
        """检查内存使用"""
        try:
            memory = psutil.virtual_memory()

            percent_used = memory.percent

            if percent_used > 90:
                status = "unhealthy"
                message = f"内存严重不足: {percent_used}% 已使用"
            elif percent_used > 80:
                status = "degraded"
                message = f"内存不足: {percent_used}% 已使用"
            else:
                status = "healthy"
                message = f"内存充足: {percent_used}% 已使用"

            return {
                "status": status,
                "message": message,
                "details": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": percent_used,
                },
            }
        except Exception as e:
            return {"status": "error", "message": f"内存检查失败: {str(e)}"}

    def print_results(self, results: dict[str, Any]) -> None:
        """打印检查结果"""
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║         Lark Service 健康检查报告                            ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print()

        # 总体状态
        status_emoji = {"healthy": "✅", "degraded": "⚠️ ", "unhealthy": "❌", "error": "❌"}

        overall_emoji = status_emoji.get(results["overall_status"], "❓")
        print(f"总体状态: {overall_emoji} {results['overall_status'].upper()}")
        print()

        # 各项检查结果
        print("检查项目:")
        print("─" * 60)

        for check_name, result in results["checks"].items():
            emoji = status_emoji.get(result["status"], "❓")
            print(f"{emoji} {check_name.upper():15s} - {result['message']}")

            if "details" in result:
                for key, value in result["details"].items():
                    print(f"   {key}: {value}")

        print()
        print("─" * 60)

        # 统计摘要
        summary = results["summary"]
        print(
            f"总计: {summary['total']} | "
            f"✅ 通过: {summary['passed']} | "
            f"⚠️  警告: {summary['warnings']} | "
            f"❌ 失败: {summary['failed']}"
        )
        print()
