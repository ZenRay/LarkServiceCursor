"""
增强的压力测试场景集。

包含多种真实业务场景的压测：
1. Token管理高并发场景
2. API批量调用场景
3. 混合工作负载场景
4. 速率限制压测
"""

import random
import time

from locust import HttpUser, between, events, task
from locust.env import Environment
from locust.stats import stats_history, stats_printer

# 模拟不同用户行为的权重
USER_BEHAVIORS = {
    "heavy_user": 0.2,  # 20%重度用户
    "normal_user": 0.6,  # 60%正常用户
    "light_user": 0.2,  # 20%轻度用户
}


class TokenManagementUser(HttpUser):
    """Token管理高并发场景"""

    wait_time = between(0.1, 0.5)  # 0.1-0.5秒间隔
    weight = 3  # 权重（相对于其他用户类型）

    def on_start(self):
        """用户启动时执行"""
        self.app_id = f"test_app_{random.randint(1, 100)}"

    @task(5)
    def refresh_token(self):
        """Token刷新（高频操作）"""
        with self.client.post(
            "/api/v1/auth/token/refresh",
            json={"app_id": self.app_id, "app_secret": "test_secret"},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(2)
    def get_token(self):
        """获取Token"""
        self.client.get(
            f"/api/v1/auth/token/{self.app_id}",
            name="/api/v1/auth/token/[app_id]",
        )

    @task(1)
    def validate_token(self):
        """验证Token"""
        self.client.post(
            "/api/v1/auth/token/validate",
            json={"token": "t-test_token_value"},
        )


class APIBatchCallUser(HttpUser):
    """API批量调用场景"""

    wait_time = between(1, 3)  # 1-3秒间隔
    weight = 2

    @task(3)
    def send_message_batch(self):
        """批量发送消息"""
        messages = [{"user_id": f"user_{i}", "content": f"Test message {i}"} for i in range(10)]
        self.client.post("/api/v1/messaging/send/batch", json={"messages": messages})

    @task(2)
    def query_bitable_records(self):
        """查询Bitable记录"""
        self.client.post(
            "/api/v1/clouddoc/bitable/query",
            json={
                "app_token": "test_app_token",
                "table_id": "test_table",
                "filter": {"field": "status", "value": "active"},
            },
        )

    @task(1)
    def get_user_info_batch(self):
        """批量获取用户信息"""
        user_ids = [f"ou_{random.randint(1000, 9999)}" for _ in range(5)]
        self.client.post("/api/v1/contact/users/batch", json={"user_ids": user_ids})


class MixedWorkloadUser(HttpUser):
    """混合工作负载场景（模拟真实用户）"""

    wait_time = between(2, 8)  # 2-8秒间隔（更接近人类行为）
    weight = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 根据权重随机分配用户类型
        rand = random.random()
        if rand < USER_BEHAVIORS["heavy_user"]:
            self.user_type = "heavy"
            self.operations_per_session = 20
        elif rand < USER_BEHAVIORS["heavy_user"] + USER_BEHAVIORS["normal_user"]:
            self.user_type = "normal"
            self.operations_per_session = 10
        else:
            self.user_type = "light"
            self.operations_per_session = 3

        self.operations_done = 0

    @task(10)
    def typical_workflow(self):
        """典型工作流程"""
        # 1. 获取Token
        self.client.post(
            "/api/v1/auth/token/get",
            json={"app_id": "test_app", "app_secret": "test_secret"},
            name="/api/v1/auth/token/get (workflow)",
        )

        time.sleep(0.5)

        # 2. 查询用户信息
        self.client.get("/api/v1/contact/user/ou_123456")

        time.sleep(0.5)

        # 3. 发送消息
        self.client.post(
            "/api/v1/messaging/send",
            json={"user_id": "ou_123456", "content": "Hello"},
        )

        self.operations_done += 1

        # 达到操作数后模拟用户离开
        if self.operations_done >= self.operations_per_session:
            self.stop(force=True)

    @task(3)
    def read_document(self):
        """读取文档（低频但重要）"""
        doc_token = f"doc_{random.randint(1, 100)}"
        self.client.get(f"/api/v1/clouddoc/doc/{doc_token}")
        self.operations_done += 1

    @task(1)
    def create_document(self):
        """创建文档（低频但耗时）"""
        self.client.post(
            "/api/v1/clouddoc/doc/create",
            json={"title": "Test Document", "content": "Test content"},
        )
        self.operations_done += 1


class RateLimitStressUser(HttpUser):
    """速率限制压力测试"""

    wait_time = between(0, 0.1)  # 极短间隔，测试限流
    weight = 1

    @task
    def rapid_fire_requests(self):
        """快速连续请求（触发限流）"""
        with self.client.get(
            "/api/v1/health", catch_response=True, name="/api/v1/health (rate-limit)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # 预期的限流响应
                response.success()
                # 记录限流事件
                retry_after = response.headers.get("Retry-After", "unknown")
                print(f"Rate limited - Retry after: {retry_after}s")
            else:
                response.failure(f"Unexpected status: {response.status_code}")


def run_scenario_test(
    scenario_name: str,
    user_class: type,
    num_users: int,
    spawn_rate: int,
    run_time: int,
):
    """
    运行特定场景的压测。

    Args:
        scenario_name: 场景名称
        user_class: 用户类
        num_users: 并发用户数
        spawn_rate: 启动速率（用户/秒）
        run_time: 运行时长（秒）
    """
    print(f"\n{'=' * 80}")
    print(f"压测场景: {scenario_name}")
    print(f"{'=' * 80}")
    print(f"并发用户数: {num_users}")
    print(f"启动速率: {spawn_rate} users/s")
    print(f"运行时长: {run_time}s")
    print(f"{'=' * 80}\n")

    # 创建Locust环境
    env = Environment(user_classes=[user_class])

    # 启动统计输出
    events.init.fire(environment=env, runner=env.create_local_runner())
    stats_printer(env.stats)
    stats_history(env.runner)

    # 开始压测
    env.runner.start(num_users, spawn_rate=spawn_rate)

    # 运行指定时长
    time.sleep(run_time)

    # 停止压测
    env.runner.quit()

    # 打印结果
    print(f"\n{'=' * 80}")
    print(f"场景 {scenario_name} 测试完成")
    print(f"{'=' * 80}")
    print(f"总请求数: {env.stats.total.num_requests}")
    print(f"失败请求数: {env.stats.total.num_failures}")
    print(f"成功率: {(1 - env.stats.total.fail_ratio) * 100:.2f}%")
    print(f"平均响应时间: {env.stats.total.avg_response_time:.2f}ms")
    print(f"P95响应时间: {env.stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99响应时间: {env.stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"TPS: {env.stats.total.total_rps:.2f} req/s\n")

    return env.stats


def main():
    """主函数 - 运行所有压测场景"""
    print("=" * 80)
    print("Lark Service - 增强压力测试场景集")
    print("=" * 80)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 场景1: Token管理高并发
    print("\n【场景1】Token管理高并发测试")
    print("目标: 验证Token刷新在高并发下的性能")
    run_scenario_test(
        scenario_name="Token Management",
        user_class=TokenManagementUser,
        num_users=100,
        spawn_rate=20,
        run_time=60,
    )

    time.sleep(5)  # 间隔5秒

    # 场景2: API批量调用
    print("\n【场景2】API批量调用测试")
    print("目标: 验证批量API调用的吞吐量")
    run_scenario_test(
        scenario_name="API Batch Call",
        user_class=APIBatchCallUser,
        num_users=50,
        spawn_rate=10,
        run_time=90,
    )

    time.sleep(5)

    # 场景3: 混合工作负载
    print("\n【场景3】混合工作负载测试")
    print("目标: 模拟真实用户行为模式")
    run_scenario_test(
        scenario_name="Mixed Workload",
        user_class=MixedWorkloadUser,
        num_users=200,
        spawn_rate=25,
        run_time=120,
    )

    time.sleep(5)

    # 场景4: 速率限制压测
    print("\n【场景4】速率限制压力测试")
    print("目标: 验证限流机制的有效性")
    run_scenario_test(
        scenario_name="Rate Limit Stress",
        user_class=RateLimitStressUser,
        num_users=10,
        spawn_rate=10,
        run_time=30,
    )

    print("\n" + "=" * 80)
    print("✅ 所有压测场景执行完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
