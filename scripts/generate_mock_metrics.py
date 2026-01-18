#!/usr/bin/env python3
"""
模拟metrics数据生成脚本
用于验证Prometheus和Grafana监控系统

用法:
  python scripts/generate_mock_metrics.py [duration_seconds]

示例:
  python scripts/generate_mock_metrics.py 60  # 运行60秒
"""

import random
import time

from lark_service.monitoring.metrics import MetricsCollector


def simulate_http_requests(collector: MetricsCollector) -> None:
    """模拟HTTP请求"""
    methods = ["GET", "POST", "PUT", "DELETE"]
    endpoints = [
        "/api/v1/token",
        "/api/v1/users",
        "/api/v1/messages",
        "/api/v1/documents",
    ]
    statuses = ["200", "201", "400", "404", "500"]
    weights = [0.7, 0.2, 0.05, 0.03, 0.02]  # 大部分请求成功

    method = random.choice(methods)
    endpoint = random.choice(endpoints)
    status = random.choices(statuses, weights=weights)[0]

    # 记录请求
    collector.http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()

    # 记录延迟
    duration = random.uniform(0.01, 0.5)  # 10ms - 500ms
    collector.http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
        duration
    )


def simulate_token_operations(collector: MetricsCollector) -> None:
    """模拟Token操作"""
    app_ids = ["app1", "app2", "app3"]
    token_types = ["tenant_access_token", "user_access_token"]

    app_id = random.choice(app_ids)
    token_type = random.choice(token_types)

    # 80%缓存命中率
    if random.random() < 0.8:
        collector.token_cache_hits_total.labels(app_id=app_id, token_type=token_type).inc()
    else:
        collector.token_cache_misses_total.labels(app_id=app_id, token_type=token_type).inc()
        # 缓存未命中时需要刷新
        status = "success" if random.random() < 0.95 else "failure"
        collector.token_refreshes_total.labels(
            app_id=app_id, token_type=token_type, status=status
        ).inc()

    # 更新活跃token数量
    active_count = random.randint(5, 20)
    collector.active_tokens.labels(app_id=app_id, token_type=token_type).set(active_count)


def simulate_api_calls(collector: MetricsCollector) -> None:
    """模拟Lark API调用"""
    services = ["messaging", "contact", "bitable", "document"]
    methods = ["send_message", "get_user", "create_record", "get_content"]
    statuses = ["success", "failure"]

    service = random.choice(services)
    method = random.choice(methods)
    status = random.choices(statuses, weights=[0.95, 0.05])[0]

    # 记录API调用
    collector.api_calls_total.labels(service=service, method=method, status=status).inc()

    # 记录延迟
    duration = random.uniform(0.05, 2.0)  # 50ms - 2s
    collector.api_call_duration_seconds.labels(service=service, method=method).observe(duration)

    # 5%失败率
    if status == "failure":
        error_code = random.choice(["99991400", "99991401", "99991663"])
        collector.api_errors_total.labels(
            service=service, method=method, error_code=error_code
        ).inc()


def simulate_database_operations(collector: MetricsCollector) -> None:
    """模拟数据库操作"""
    operations = ["select", "insert", "update", "delete"]
    tables = ["tokens", "user_cache", "user_auth_sessions"]
    statuses = ["success", "failure"]

    operation = random.choice(operations)
    table = random.choice(tables)
    status = random.choices(statuses, weights=[0.98, 0.02])[0]

    collector.db_operations_total.labels(operation=operation, table=table, status=status).inc()

    # 模拟连接池状态
    pool_size = 20
    available = random.randint(5, 15)
    collector.db_connection_pool_size.set(pool_size)
    collector.db_connection_pool_available.set(available)


def simulate_cache_operations(collector: MetricsCollector) -> None:
    """模拟缓存操作"""
    operations = ["get", "set", "delete"]
    cache_types = ["token", "user", "config"]
    statuses = ["hit", "miss"]

    operation = random.choice(operations)
    cache_type = random.choice(cache_types)
    status = random.choice(statuses)

    collector.cache_operations_total.labels(
        operation=operation, cache_type=cache_type, status=status
    ).inc()


def simulate_mq_operations(collector: MetricsCollector) -> None:
    """模拟消息队列操作"""
    queues = ["event_queue", "command_queue", "notification_queue"]
    statuses = ["success", "failure"]

    # 发布消息
    queue = random.choice(queues)
    status = random.choices(statuses, weights=[0.99, 0.01])[0]
    collector.mq_messages_published_total.labels(queue=queue, status=status).inc()

    # 消费消息
    queue = random.choice(queues)
    status = random.choices(statuses, weights=[0.97, 0.03])[0]
    collector.mq_messages_consumed_total.labels(queue=queue, status=status).inc()


def simulate_business_metrics(collector: MetricsCollector) -> None:
    """模拟业务指标"""
    message_types = ["text", "image", "file", "card"]
    doc_types = ["document", "sheet", "bitable"]
    query_types = ["user_info", "department", "contact"]
    statuses = ["success", "failure"]

    # 随机产生业务事件
    if random.random() < 0.3:
        msg_type = random.choice(message_types)
        status = random.choices(statuses, weights=[0.98, 0.02])[0]
        collector.messages_sent_total.labels(message_type=msg_type, status=status).inc()
    if random.random() < 0.1:
        doc_type = random.choice(doc_types)
        status = random.choices(statuses, weights=[0.97, 0.03])[0]
        collector.documents_created_total.labels(doc_type=doc_type, status=status).inc()
    if random.random() < 0.5:
        query_type = random.choice(query_types)
        status = random.choices(statuses, weights=[0.99, 0.01])[0]
        collector.user_queries_total.labels(query_type=query_type, status=status).inc()


def main(duration_seconds: int = 300) -> None:
    """
    主函数 - 生成模拟metrics数据

    Args:
        duration_seconds: 运行时长(秒)，默认300秒(5分钟)
    """
    collector = MetricsCollector()

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║           🎭 Metrics 模拟数据生成器                                   ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print("")
    print(f"运行时长: {duration_seconds}秒")
    print("Metrics端点: http://localhost:9091/metrics")
    print("Prometheus: http://localhost:9090")
    print("Grafana: http://localhost:3000")
    print("")
    print("生成模拟数据中...")
    print("按 Ctrl+C 停止")
    print("════════════════════════════════════════════════════════════════════════")

    start_time = time.time()
    iteration = 0

    try:
        while time.time() - start_time < duration_seconds:
            iteration += 1

            # 每次迭代模拟多个操作
            simulate_http_requests(collector)
            simulate_token_operations(collector)
            simulate_api_calls(collector)
            simulate_database_operations(collector)
            simulate_cache_operations(collector)
            simulate_mq_operations(collector)
            simulate_business_metrics(collector)

            # 每10秒打印一次进度
            if iteration % 10 == 0:
                elapsed = int(time.time() - start_time)
                remaining = duration_seconds - elapsed
                print(
                    f"⏱️  已运行 {elapsed}秒 / {duration_seconds}秒 "
                    f"(剩余 {remaining}秒) - {iteration} 次迭代"
                )

            # 每秒生成1次数据
            time.sleep(1)

        print("")
        print("════════════════════════════════════════════════════════════════════════")
        print(f"✅ 完成！共生成 {iteration} 次迭代的模拟数据")
        print("")
        print("下一步:")
        print("  1. 访问 Prometheus: http://localhost:9090")
        print("     - 查看 Targets: http://localhost:9090/targets")
        print("     - 查询指标: lark_service_http_requests_total")
        print("")
        print("  2. 访问 Grafana: http://localhost:3000")
        print("     - 默认账号: admin / admin_local_only")
        print("     - 查看仪表板")
        print("════════════════════════════════════════════════════════════════════════")

    except KeyboardInterrupt:
        elapsed = int(time.time() - start_time)
        print("\n")
        print("════════════════════════════════════════════════════════════════════════")
        print(f"⏸️  用户中断 - 已运行 {elapsed}秒，{iteration} 次迭代")
        print("════════════════════════════════════════════════════════════════════════")


if __name__ == "__main__":
    import sys

    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    main(duration)
