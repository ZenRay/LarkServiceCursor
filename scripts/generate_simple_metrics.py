#!/usr/bin/env python3
"""
简化版metrics数据生成脚本 - 仅生成核心指标
"""

import random
import time

from lark_service.monitoring.metrics import MetricsCollector


def main(duration_seconds: int = 120) -> None:
    """生成模拟metrics数据"""
    collector = MetricsCollector()

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         🎭 Metrics 模拟数据生成器（简化版）                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"\n运行时长: {duration_seconds}秒")
    print("Metrics端点: http://localhost:9091/metrics")
    print("Prometheus: http://localhost:9090")
    print("Grafana: http://localhost:3000\n")
    print("生成模拟数据中...\n")

    start_time = time.time()
    iteration = 0

    try:
        while time.time() - start_time < duration_seconds:
            iteration += 1

            # 1. HTTP请求
            methods = ["GET", "POST", "PUT", "DELETE"]
            endpoints = ["/api/v1/token", "/api/v1/users", "/api/v1/messages"]
            statuses = ["200", "201", "400", "500"]

            method = random.choice(methods)
            endpoint = random.choice(endpoints)
            status = random.choices(statuses, weights=[0.7, 0.2, 0.08, 0.02])[0]

            collector.http_requests_total.labels(
                method=method, endpoint=endpoint, status=status
            ).inc()

            duration = random.uniform(0.01, 0.5)
            collector.http_request_duration_seconds.labels(
                method=method, endpoint=endpoint
            ).observe(duration)

            # 2. Token操作
            app_ids = ["app1", "app2", "app3"]
            token_types = ["tenant_access_token", "user_access_token"]

            app_id = random.choice(app_ids)
            token_type = random.choice(token_types)

            if random.random() < 0.8:
                collector.token_cache_hits_total.labels(app_id=app_id, token_type=token_type).inc()
            else:
                collector.token_cache_misses_total.labels(
                    app_id=app_id, token_type=token_type
                ).inc()
                status = "success" if random.random() < 0.95 else "failure"
                collector.token_refreshes_total.labels(
                    app_id=app_id, token_type=token_type, status=status
                ).inc()

            active_count = random.randint(5, 20)
            collector.active_tokens.labels(app_id=app_id, token_type=token_type).set(active_count)

            # 3. API调用
            services = ["messaging", "contact", "bitable", "document"]
            api_methods = ["send_message", "get_user", "create_record", "get_content"]

            service = random.choice(services)
            api_method = random.choice(api_methods)
            status = "success" if random.random() < 0.95 else "failure"

            collector.api_calls_total.labels(
                service=service, method=api_method, status=status
            ).inc()

            api_duration = random.uniform(0.05, 2.0)
            collector.api_call_duration_seconds.labels(service=service, method=api_method).observe(
                api_duration
            )

            # 每10秒打印进度
            if iteration % 10 == 0:
                elapsed = int(time.time() - start_time)
                remaining = duration_seconds - elapsed
                print(f"⏱️  已运行 {elapsed}秒 | 剩余 {remaining}秒 | {iteration} 次迭代")

            time.sleep(1)

        print(f"\n✅ 完成！共生成 {iteration} 次迭代的模拟数据\n")
        print("访问 http://localhost:9090 查看Prometheus")
        print("访问 http://localhost:3000 查看Grafana (admin/admin_local_only)\n")

    except KeyboardInterrupt:
        elapsed = int(time.time() - start_time)
        print(f"\n⏸️  中断 - 已运行 {elapsed}秒，{iteration} 次迭代\n")


if __name__ == "__main__":
    import sys

    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    main(duration)
