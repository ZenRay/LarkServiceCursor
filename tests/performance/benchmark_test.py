#!/usr/bin/env python3
"""
Lark Service 性能基准测试脚本

功能:
1. 测试核心组件的性能基准
2. 记录性能指标用于回归测试
3. 生成性能报告

使用:
    python tests/performance/benchmark_test.py
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from lark_service.core.models.token_storage import TokenStorage
from lark_service.core.retry import retry_on_error
from lark_service.utils.logger import setup_logger
from lark_service.utils.masking import mask_email, mask_mobile, mask_token
from lark_service.utils.validators import (
    validate_app_id,
    validate_app_secret,
    validate_open_id,
    validate_url,
)

logger = setup_logger(__name__)


class PerformanceBenchmark:
    """性能基准测试"""

    def __init__(self):
        self.results: list[dict[str, Any]] = []
        self.start_time = datetime.now()

    def benchmark(self, name: str, description: str):
        """性能测试装饰器"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                print(f"\n{'=' * 60}")
                print(f"测试: {name}")
                print(f"说明: {description}")
                print(f"{'=' * 60}")

                iterations = kwargs.get("iterations", 1000)
                print(f"迭代次数: {iterations}")

                # 预热
                for _ in range(min(10, iterations // 10)):
                    func(*args, **kwargs)

                # 正式测试
                start = time.perf_counter()
                for _ in range(iterations):
                    func(*args, **kwargs)
                end = time.perf_counter()

                elapsed = end - start
                avg_time = (elapsed / iterations) * 1000  # 转换为毫秒
                throughput = iterations / elapsed

                result = {
                    "name": name,
                    "description": description,
                    "iterations": iterations,
                    "total_time_s": round(elapsed, 4),
                    "avg_time_ms": round(avg_time, 4),
                    "throughput_ops": round(throughput, 2),
                    "timestamp": datetime.now().isoformat(),
                }

                self.results.append(result)

                print("\n结果:")
                print(f"  总耗时: {elapsed:.4f}s")
                print(f"  平均耗时: {avg_time:.4f}ms")
                print(f"  吞吐量: {throughput:.2f} ops/s")

                # 性能判断
                if avg_time < 1:
                    print("  性能评级: ✅ 优秀 (<1ms)")
                elif avg_time < 10:
                    print("  性能评级: ✅ 良好 (<10ms)")
                elif avg_time < 100:
                    print("  性能评级: ⚠️  一般 (<100ms)")
                else:
                    print("  性能评级: ❌ 较差 (≥100ms)")

                return result

            return wrapper

        return decorator

    def save_results(self, output_file: str):
        """保存测试结果"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "test_date": self.start_time.isoformat(),
            "duration_s": (datetime.now() - self.start_time).total_seconds(),
            "results": self.results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n结果已保存到: {output_file}")


def test_validator_performance(benchmark: PerformanceBenchmark):
    """测试验证器性能"""

    @benchmark.benchmark(
        "输入验证器 - App ID", "测试 validate_app_id() 性能"
    )
    def validate_app_id_bench(iterations=10000):
        validate_app_id("cli_a1b2c3d4e5f6g7h8")

    @benchmark.benchmark(
        "输入验证器 - App Secret", "测试 validate_app_secret() 性能"
    )
    def validate_app_secret_bench(iterations=10000):
        validate_app_secret("1234567890abcdef1234567890abcdef")

    @benchmark.benchmark("输入验证器 - Open ID", "测试 validate_open_id() 性能")
    def validate_open_id_bench(iterations=10000):
        validate_open_id("ou_1234567890abcdef")

    @benchmark.benchmark("输入验证器 - URL", "测试 validate_url() 性能")
    def validate_url_bench(iterations=10000):
        validate_url("https://open.feishu.cn/api/v1/test")

    validate_app_id_bench()
    validate_app_secret_bench()
    validate_open_id_bench()
    validate_url_bench()


def test_masking_performance(benchmark: PerformanceBenchmark):
    """测试数据脱敏性能"""

    @benchmark.benchmark("数据脱敏 - Email", "测试 mask_email() 性能")
    def mask_email_bench(iterations=10000):
        mask_email("user@example.com")

    @benchmark.benchmark("数据脱敏 - Mobile", "测试 mask_mobile() 性能")
    def mask_mobile_bench(iterations=10000):
        mask_mobile("+86-13800138000")

    @benchmark.benchmark("数据脱敏 - Token", "测试 mask_token() 性能")
    def mask_token_bench(iterations=10000):
        mask_token("u-abc123def456ghi789jkl012mno345pqr")

    mask_email_bench()
    mask_mobile_bench()
    mask_token_bench()


def test_token_storage_performance(benchmark: PerformanceBenchmark):
    """测试Token存储性能 (PostgreSQL)"""
    # 注意: 此测试需要PostgreSQL连接
    # 在staging环境中运行时会自动连接
    # 本地测试可能跳过此项
    print("\n⚠️  Token存储测试需要PostgreSQL连接，当前跳过")
    print("   在staging/production环境中运行此测试")


def test_retry_mechanism_performance(benchmark: PerformanceBenchmark):
    """测试重试机制性能"""

    @benchmark.benchmark("重试机制 - 成功场景", "测试 retry_on_error() 性能(无重试)")
    def retry_success_bench(iterations=1000):
        @retry_on_error(max_retries=3)
        def always_success():
            return True

        always_success()

    retry_success_bench()


def test_token_model_performance(benchmark: PerformanceBenchmark):
    """测试Token模型性能"""

    @benchmark.benchmark("Token模型 - 创建", "测试 TokenStorage 对象创建")
    def token_creation_bench(iterations=10000):
        TokenStorage(
            app_id="test_app",
            token_type="tenant_access_token",
            token_value="t-test",
            expires_at=datetime.now().timestamp() + 3600,
        )

    @benchmark.benchmark("Token模型 - 过期检查", "测试 is_expired() 性能")
    def token_is_expired_bench(iterations=10000):
        token = TokenStorage(
            app_id="test_app",
            token_type="tenant_access_token",
            token_value="t-test",
            expires_at=datetime.now().timestamp() + 3600,
        )
        token.is_expired()

    @benchmark.benchmark("Token模型 - 刷新判断", "测试 should_refresh() 性能")
    def token_should_refresh_bench(iterations=10000):
        token = TokenStorage(
            app_id="test_app",
            token_type="tenant_access_token",
            token_value="t-test",
            expires_at=datetime.now().timestamp() + 3600,
        )
        token.should_refresh()

    token_creation_bench()
    token_is_expired_bench()
    token_should_refresh_bench()


def print_summary(benchmark: PerformanceBenchmark):
    """打印性能摘要"""
    print(f"\n{'=' * 60}")
    print("性能基准测试摘要")
    print(f"{'=' * 60}")

    if not benchmark.results:
        print("无测试结果")
        return

    print(f"\n测试项数: {len(benchmark.results)}")
    print(f"测试时长: {(datetime.now() - benchmark.start_time).total_seconds():.2f}s\n")

    # 按类别分组
    categories = {}
    for result in benchmark.results:
        category = result["name"].split(" - ")[0]
        if category not in categories:
            categories[category] = []
        categories[category].append(result)

    # 打印各类别统计
    for category, results in categories.items():
        print(f"\n{category}:")
        for result in results:
            name = result["name"].split(" - ")[1]
            avg_time = result["avg_time_ms"]
            throughput = result["throughput_ops"]

            status = "✅" if avg_time < 10 else "⚠️ " if avg_time < 100 else "❌"
            print(f"  {status} {name:20s} | {avg_time:8.4f}ms | {throughput:10.2f} ops/s")

    # 找出最快和最慢的测试
    sorted_results = sorted(benchmark.results, key=lambda x: x["avg_time_ms"])

    print(f"\n{'=' * 60}")
    print("性能排行")
    print(f"{'=' * 60}")

    print("\n最快的3个测试:")
    for i, result in enumerate(sorted_results[:3], 1):
        print(f"  {i}. {result['name']}: {result['avg_time_ms']:.4f}ms")

    print("\n最慢的3个测试:")
    for i, result in enumerate(sorted_results[-3:][::-1], 1):
        print(f"  {i}. {result['name']}: {result['avg_time_ms']:.4f}ms")


def main():
    """主函数"""
    print("=" * 60)
    print("Lark Service - 性能基准测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version.split()[0]}")
    print("=" * 60)

    benchmark = PerformanceBenchmark()

    try:
        # 运行各项测试
        test_validator_performance(benchmark)
        test_masking_performance(benchmark)
        test_token_model_performance(benchmark)
        test_token_storage_performance(benchmark)
        test_retry_mechanism_performance(benchmark)

        # 打印摘要
        print_summary(benchmark)

        # 保存结果
        output_file = f"tests/performance/benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        benchmark.save_results(output_file)

        print(f"\n{'=' * 60}")
        print("✅ 性能基准测试完成!")
        print(f"{'=' * 60}\n")

    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
