#!/usr/bin/env python3
"""
综合健康检查脚本

用于检查Lark Service系统的各个组件状态。

用法:
    python scripts/health_check.py --all
    python scripts/health_check.py --database --redis --rabbitmq
    python scripts/health_check.py --quick
"""

import argparse

# 添加项目根目录到路径
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(description="Lark Service 健康检查")
    parser.add_argument("--all", action="store_true", help="执行所有检查")
    parser.add_argument("--quick", action="store_true", help="快速检查（仅基础组件）")
    parser.add_argument("--database", action="store_true", help="检查数据库")
    parser.add_argument("--redis", action="store_true", help="检查Redis")
    parser.add_argument("--rabbitmq", action="store_true", help="检查RabbitMQ")
    parser.add_argument("--api", action="store_true", help="检查飞书API连通性")
    parser.add_argument("--config", action="store_true", help="检查配置")
    parser.add_argument("--disk", action="store_true", help="检查磁盘空间")
    parser.add_argument("--memory", action="store_true", help="检查内存")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    parser.add_argument("--exit-on-error", action="store_true", help="遇到错误立即退出")

    args = parser.parse_args()

    # 如果没有指定任何检查，默认执行快速检查
    if not any(
        [
            args.all,
            args.quick,
            args.database,
            args.redis,
            args.rabbitmq,
            args.api,
            args.config,
            args.disk,
            args.memory,
        ]
    ):
        args.quick = True

    # 确定要执行的检查
    checks_to_run = []

    if args.all:
        checks_to_run = ["config", "database", "redis", "rabbitmq", "api", "disk", "memory"]
    elif args.quick:
        checks_to_run = ["config", "database", "redis"]
    else:
        if args.config:
            checks_to_run.append("config")
        if args.database:
            checks_to_run.append("database")
        if args.redis:
            checks_to_run.append("redis")
        if args.rabbitmq:
            checks_to_run.append("rabbitmq")
        if args.api:
            checks_to_run.append("api")
        if args.disk:
            checks_to_run.append("disk")
        if args.memory:
            checks_to_run.append("memory")

    # 执行检查
    from lark_service.utils.health_checker import HealthChecker

    checker = HealthChecker()
    results = checker.run_checks(checks_to_run, exit_on_error=args.exit_on_error)

    # 输出结果
    if args.json:
        import json

        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        checker.print_results(results)

    # 返回状态码
    if results["overall_status"] == "healthy":
        return 0
    elif results["overall_status"] == "degraded":
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
