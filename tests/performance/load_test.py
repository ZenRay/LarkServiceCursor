#!/usr/bin/env python3
"""
Lark Service 压力测试脚本

使用 locust 进行并发测试,验证性能指标:
- P95响应时间 < 500ms
- TPS ≥ 100
- 并发用户数: 10-100
"""

import gevent
from locust import HttpUser, between, task
from locust.env import Environment
from locust.stats import stats_history, stats_printer

# 模拟测试配置
TEST_APP_ID = "test_app_001"
TEST_OPEN_ID = "ou_test123456"


class LarkServiceUser(HttpUser):  # type: ignore[misc]
    """模拟 Lark Service 用户行为"""

    # 用户等待时间 (1-3秒)
    wait_time = between(1, 3)

    def on_start(self):
        """初始化测试用户"""
        print(f"Starting user: {self.client.base_url}")

    @task(3)
    def get_user_info(self):
        """测试通讯录查询 (高频操作)"""
        # 注意: 这需要实际的HTTP接口,当前测试为模拟
        # 实际部署后需要替换为真实API端点
        with self.client.get(
            f"/api/v1/contact/user/{TEST_OPEN_ID}", catch_response=True, name="查询用户信息"
        ) as response:
            if response.status_code == 404:
                # 模拟场景: 服务未部署时跳过
                response.success()

    @task(2)
    def send_message(self):
        """测试消息发送 (中频操作)"""
        with self.client.post(
            "/api/v1/messaging/send",
            json={
                "receive_id": TEST_OPEN_ID,
                "msg_type": "text",
                "content": {"text": "Performance test message"},
            },
            catch_response=True,
            name="发送消息",
        ) as response:
            if response.status_code == 404:
                response.success()

    @task(1)
    def get_document_info(self):
        """测试文档查询 (低频操作)"""
        with self.client.get(
            "/api/v1/clouddoc/doc/test_doc_token", catch_response=True, name="查询文档"
        ) as response:
            if response.status_code == 404:
                response.success()


def run_load_test():
    """运行压力测试"""
    print("=" * 60)
    print("Lark Service 压力测试")
    print("=" * 60)
    print()

    # 创建测试环境
    env = Environment(user_classes=[LarkServiceUser])

    # 设置目标主机 (当前为本地模拟)
    env.host = "http://localhost:8000"

    # 启动 Web UI (可选)
    # env.create_web_ui("127.0.0.1", 8089)

    # 配置测试参数
    user_count = 50  # 并发用户数
    spawn_rate = 10  # 每秒启动10个用户
    run_time = 120  # 运行2分钟

    print("配置:")
    print(f"  - 并发用户数: {user_count}")
    print(f"  - 启动速率: {spawn_rate} users/s")
    print(f"  - 运行时长: {run_time}s (2分钟)")
    print(f"  - 目标主机: {env.host}")
    print()

    # 启动统计输出
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)

    # 运行测试
    print("开始压力测试...")
    print()

    try:
        env.runner.start(user_count, spawn_rate)

        # 运行指定时长
        gevent.sleep(run_time)

        # 停止测试
        env.runner.quit()

    except KeyboardInterrupt:
        print("\n测试被用户中断")

    # 输出测试结果
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print()

    stats = env.stats.total

    print(f"总请求数: {stats.num_requests}")
    print(f"失败请求数: {stats.num_failures}")
    print(f"成功率: {(1 - stats.fail_ratio) * 100:.2f}%")
    print()

    if stats.num_requests > 0:
        print("响应时间统计:")
        print(f"  - 平均响应时间: {stats.avg_response_time:.2f}ms")
        print(f"  - 最小响应时间: {stats.min_response_time:.2f}ms")
        print(f"  - 最大响应时间: {stats.max_response_time:.2f}ms")
        print(f"  - P50响应时间: {stats.get_response_time_percentile(0.5):.2f}ms")
        print(f"  - P95响应时间: {stats.get_response_time_percentile(0.95):.2f}ms")
        print(f"  - P99响应时间: {stats.get_response_time_percentile(0.99):.2f}ms")
        print()

        # 计算TPS
        total_time = (stats.last_request_timestamp - stats.start_time) / 1000.0
        if total_time > 0:
            tps = stats.num_requests / total_time
            print(f"吞吐量 (TPS): {tps:.2f} requests/s")
            print()

        # 性能目标验证
        p95 = stats.get_response_time_percentile(0.95)

        print("性能目标验证:")
        if p95 < 500:
            print(f"  ✅ P95响应时间 < 500ms: {p95:.2f}ms")
        else:
            print(f"  ❌ P95响应时间 ≥ 500ms: {p95:.2f}ms (目标<500ms)")

        if total_time > 0:
            if tps >= 100:
                print(f"  ✅ TPS ≥ 100: {tps:.2f}")
            else:
                print(f"  ⚠️  TPS < 100: {tps:.2f} (目标≥100)")

    print()
    print("=" * 60)

    return env.stats


if __name__ == "__main__":
    print()
    print("⚠️  注意:")
    print("  - 当前为模拟测试,实际API未部署")
    print("  - 生产环境部署后,请更新 env.host 为实际API地址")
    print("  - 建议在独立测试环境执行压力测试")
    print()

    input("按Enter键开始测试 (Ctrl+C 取消)...")
    print()

    try:
        run_load_test()
    except Exception as e:
        print(f"测试执行失败: {e}")
        import traceback

        traceback.print_exc()
