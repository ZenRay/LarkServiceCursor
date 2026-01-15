"""Token 刷新性能测试

测试 Token 刷新操作的性能指标,确保满足基线要求。

性能基线:
- Token 刷新延迟: < 100ms (P95)
- Token 刷新吞吐量: ≥ 100 req/s
- 并发刷新: ≥ 50 concurrent requests
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import SQLiteTokenStorage


@pytest.fixture
def perf_config(tmp_path: Any) -> Config:
    """性能测试配置"""
    db_path = tmp_path / "perf_test.db"
    config = Config()
    config.app_id = "test_app_perf"
    config.app_secret = "test_secret_perf"
    config.database_path = str(db_path)
    config.token_refresh_threshold = 0.8
    config.enable_token_cache = True
    return config


@pytest.fixture
def perf_storage(perf_config: Config) -> SQLiteTokenStorage:
    """性能测试存储"""
    storage = SQLiteTokenStorage(perf_config)
    storage.initialize()
    return storage


@pytest.fixture
def perf_pool(perf_config: Config, perf_storage: SQLiteTokenStorage) -> CredentialPool:
    """性能测试凭证池"""
    return CredentialPool(config=perf_config, storage=perf_storage)


class TestTokenRefreshPerformance:
    """Token 刷新性能测试"""

    @patch("lark_service.core.credential_pool.lark")
    def test_token_refresh_latency_p95(
        self, mock_lark: MagicMock, perf_pool: CredentialPool
    ) -> None:
        """测试 Token 刷新延迟 P95 < 100ms

        性能目标: P95 延迟 < 100ms
        """
        # Mock Lark API
        mock_client = MagicMock()
        mock_lark.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.code = 0
        mock_response.tenant_access_token = "perf_token_123"
        mock_response.expire = 7200
        mock_client.auth.v3.tenant_access_token.internal.return_value = mock_response

        # 预热 (避免首次调用的初始化开销)
        perf_pool.get_tenant_access_token()

        # 性能测试: 100 次刷新
        latencies = []
        num_requests = 100

        for _ in range(num_requests):
            # 清除缓存,强制刷新
            perf_pool._token_cache.clear()

            start = time.perf_counter()
            perf_pool.get_tenant_access_token()
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        # 计算 P95
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]

        # 计算统计数据
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        p50_latency = latencies[int(len(latencies) * 0.50)]
        p99_latency = latencies[int(len(latencies) * 0.99)]

        print(f"\n=== Token 刷新延迟统计 ===")
        print(f"请求数: {num_requests}")
        print(f"平均延迟: {avg_latency:.2f} ms")
        print(f"最小延迟: {min_latency:.2f} ms")
        print(f"最大延迟: {max_latency:.2f} ms")
        print(f"P50 延迟: {p50_latency:.2f} ms")
        print(f"P95 延迟: {p95_latency:.2f} ms")
        print(f"P99 延迟: {p99_latency:.2f} ms")

        # 断言: P95 < 100ms
        assert p95_latency < 100, f"P95 延迟 {p95_latency:.2f}ms 超过 100ms 基线"

    @patch("lark_service.core.credential_pool.lark")
    def test_token_refresh_throughput(
        self, mock_lark: MagicMock, perf_pool: CredentialPool
    ) -> None:
        """测试 Token 刷新吞吐量 ≥ 100 req/s

        性能目标: 吞吐量 ≥ 100 req/s
        """
        # Mock Lark API
        mock_client = MagicMock()
        mock_lark.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.code = 0
        mock_response.tenant_access_token = "perf_token_456"
        mock_response.expire = 7200
        mock_client.auth.v3.tenant_access_token.internal.return_value = mock_response

        # 预热
        perf_pool.get_tenant_access_token()

        # 性能测试: 1 秒内完成的请求数
        num_requests = 200
        start = time.perf_counter()

        for _ in range(num_requests):
            # 清除缓存,强制刷新
            perf_pool._token_cache.clear()
            perf_pool.get_tenant_access_token()

        end = time.perf_counter()
        duration = end - start

        # 计算吞吐量
        throughput = num_requests / duration

        print(f"\n=== Token 刷新吞吐量统计 ===")
        print(f"请求数: {num_requests}")
        print(f"总耗时: {duration:.2f} s")
        print(f"吞吐量: {throughput:.2f} req/s")

        # 断言: 吞吐量 ≥ 100 req/s
        assert throughput >= 100, f"吞吐量 {throughput:.2f} req/s 低于 100 req/s 基线"

    @patch("lark_service.core.credential_pool.lark")
    def test_concurrent_token_refresh(
        self, mock_lark: MagicMock, perf_pool: CredentialPool
    ) -> None:
        """测试并发 Token 刷新 ≥ 50 concurrent requests

        性能目标: 支持 ≥ 50 并发请求
        """
        # Mock Lark API
        mock_client = MagicMock()
        mock_lark.Client.return_value = mock_client

        call_count = [0]

        def mock_get_token(*args: Any, **kwargs: Any) -> MagicMock:
            call_count[0] += 1
            response = MagicMock()
            response.code = 0
            response.tenant_access_token = f"concurrent_token_{call_count[0]}"
            response.expire = 7200
            # 模拟网络延迟
            time.sleep(0.01)
            return response

        mock_client.auth.v3.tenant_access_token.internal.side_effect = mock_get_token

        # 预热
        perf_pool.get_tenant_access_token()

        # 并发测试
        num_concurrent = 50
        start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = []
            for _ in range(num_concurrent):
                # 清除缓存,强制刷新
                perf_pool._token_cache.clear()
                future = executor.submit(perf_pool.get_tenant_access_token)
                futures.append(future)

            # 等待所有请求完成
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"并发请求失败: {e}")

        end = time.perf_counter()
        duration = end - start

        print(f"\n=== 并发 Token 刷新统计 ===")
        print(f"并发数: {num_concurrent}")
        print(f"成功数: {len(results)}")
        print(f"总耗时: {duration:.2f} s")
        print(f"平均延迟: {duration / num_concurrent * 1000:.2f} ms")

        # 断言: 所有请求成功
        assert len(results) == num_concurrent, f"并发请求失败: {len(results)}/{num_concurrent}"

        # 断言: 总耗时合理 (考虑 10ms 网络延迟 + 并发处理)
        # 理论最小耗时: 10ms (网络延迟)
        # 允许最大耗时: 500ms (考虑并发开销)
        assert duration < 0.5, f"并发处理耗时 {duration:.2f}s 超过 0.5s"

    @patch("lark_service.core.credential_pool.lark")
    def test_token_cache_hit_performance(
        self, mock_lark: MagicMock, perf_pool: CredentialPool
    ) -> None:
        """测试 Token 缓存命中性能

        性能目标: 缓存命中延迟 < 1ms
        """
        # Mock Lark API
        mock_client = MagicMock()
        mock_lark.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.code = 0
        mock_response.tenant_access_token = "cached_token_789"
        mock_response.expire = 7200
        mock_client.auth.v3.tenant_access_token.internal.return_value = mock_response

        # 首次获取 Token (缓存 miss)
        perf_pool.get_tenant_access_token()

        # 性能测试: 缓存命中
        num_requests = 1000
        latencies = []

        for _ in range(num_requests):
            start = time.perf_counter()
            perf_pool.get_tenant_access_token()
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        # 计算统计数据
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        print(f"\n=== Token 缓存命中性能统计 ===")
        print(f"请求数: {num_requests}")
        print(f"平均延迟: {avg_latency:.4f} ms")
        print(f"最大延迟: {max_latency:.4f} ms")
        print(f"P95 延迟: {p95_latency:.4f} ms")

        # 断言: P95 < 1ms
        assert p95_latency < 1.0, f"缓存命中 P95 延迟 {p95_latency:.4f}ms 超过 1ms"


class TestTokenStoragePerformance:
    """Token 存储性能测试"""

    def test_token_write_performance(self, perf_storage: SQLiteTokenStorage) -> None:
        """测试 Token 写入性能

        性能目标: 写入延迟 < 10ms (P95)
        """
        num_writes = 100
        latencies = []

        for i in range(num_writes):
            start = time.perf_counter()

            perf_storage.set_token(
                app_id=f"app_{i}",
                token_type="tenant_access_token",
                token_value=f"token_{i}",
                expires_at=datetime.now() + timedelta(hours=2),
            )

            end = time.perf_counter()
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        # 计算统计数据
        latencies.sort()
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = latencies[int(len(latencies) * 0.95)]

        print(f"\n=== Token 写入性能统计 ===")
        print(f"写入数: {num_writes}")
        print(f"平均延迟: {avg_latency:.2f} ms")
        print(f"P95 延迟: {p95_latency:.2f} ms")

        # 断言: P95 < 10ms
        assert p95_latency < 10, f"写入 P95 延迟 {p95_latency:.2f}ms 超过 10ms"

    def test_token_read_performance(self, perf_storage: SQLiteTokenStorage) -> None:
        """测试 Token 读取性能

        性能目标: 读取延迟 < 5ms (P95)
        """
        # 准备测试数据
        app_id = "perf_app_read"
        perf_storage.set_token(
            app_id=app_id,
            token_type="tenant_access_token",
            token_value="read_token_123",
            expires_at=datetime.now() + timedelta(hours=2),
        )

        # 性能测试
        num_reads = 100
        latencies = []

        for _ in range(num_reads):
            start = time.perf_counter()
            perf_storage.get_token(app_id, "tenant_access_token")
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        # 计算统计数据
        latencies.sort()
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = latencies[int(len(latencies) * 0.95)]

        print(f"\n=== Token 读取性能统计 ===")
        print(f"读取数: {num_reads}")
        print(f"平均延迟: {avg_latency:.2f} ms")
        print(f"P95 延迟: {p95_latency:.2f} ms")

        # 断言: P95 < 5ms
        assert p95_latency < 5, f"读取 P95 延迟 {p95_latency:.2f}ms 超过 5ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
