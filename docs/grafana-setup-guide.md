# Grafana配置指南

本文档说明如何在Grafana中配置Prometheus数据源和导入Lark Service监控仪表板。

---

## 1. 访问Grafana

Grafana运行在 `http://localhost:3000`

默认登录凭证:
- **用户名**: `admin`
- **密码**: `admin_local_only`

---

## 2. 配置Prometheus数据源

### 步骤 1: 添加数据源

1. 登录Grafana
2. 点击左侧菜单 **Configuration** (⚙️) → **Data Sources**
3. 点击 **Add data source**
4. 选择 **Prometheus**

### 步骤 2: 配置参数

填写以下配置:

| 字段 | 值 |
|------|-----|
| **Name** | `Prometheus-Lark-Service` |
| **HTTP URL** | `http://prometheus:9090` |
| **Access** | `Server (default)` |
| **Scrape interval** | `10s` |

### 步骤 3: 保存并测试

1. 点击 **Save & Test**
2. 应该看到 ✅ **Data source is working**

---

## 3. 导入Lark Service监控仪表板

### 方法 1: 从文件导入

1. 点击左侧菜单 **+** → **Import**
2. 点击 **Upload JSON file**
3. 选择 `staging-simulation/grafana-dashboard.json`
4. 选择数据源: `Prometheus-Lark-Service`
5. 点击 **Import**

### 方法 2: 直接粘贴JSON

1. 点击左侧菜单 **+** → **Import**
2. 复制 `grafana-dashboard.json` 的内容
3. 粘贴到 **Import via panel json** 文本框
4. 点击 **Load**
5. 选择数据源: `Prometheus-Lark-Service`
6. 点击 **Import**

---

## 4. 仪表板内容

导入的仪表板包含以下面板:

### HTTP性能

1. **HTTP请求吞吐量**
   - 显示每秒HTTP请求数
   - 按method、endpoint、status分类

2. **HTTP请求延迟**
   - P50、P95、P99延迟百分位
   - 按method和endpoint分组

### Token管理

3. **Token刷新次数**
   - 每秒token刷新操作数
   - 按app_id、token_type、status分类

4. **Token缓存命中率**
   - 缓存命中率百分比
   - 阈值: <80%红色, 80-95%黄色, >95%绿色

5. **活跃Token数量**
   - 当前活跃的token总数
   - 阈值: <50绿色, 50-100黄色, >100红色

### API调用

6. **API调用吞吐量**
   - 按服务分类的API调用量
   - messaging、clouddoc、contact等

7. **API调用延迟**
   - P95延迟，按服务分类
   - 用于识别慢服务

8. **API错误率**
   - 每秒API错误数
   - 按服务和错误码分类
   - 阈值: <0.1/s黄色, >1/s红色

### 系统资源

9. **数据库连接池**
   - Pool Size vs Available连接
   - 用于检测连接泄漏

### 业务指标

10. **消息发送统计**
    - 过去1小时发送的消息总数

11. **文档创建统计**
    - 过去1小时创建的文档总数

12. **用户查询统计**
    - 过去1小时的用户查询总数

---

## 5. 告警配置（可选）

### 创建告警规则

1. 在仪表板中选择一个面板
2. 点击面板标题 → **Edit**
3. 切换到 **Alert** 标签
4. 点击 **Create Alert**
5. 配置告警条件和通知渠道

### 推荐告警

| 告警名称 | 条件 | 严重性 |
|---------|------|--------|
| HTTP错误率过高 | `rate(lark_service_http_requests_total{status=~"5.."}[5m]) > 0.1` | 🔴 Critical |
| Token缓存命中率过低 | `cache_hit_rate < 80` | 🟡 Warning |
| API调用延迟过高 | `P95 > 5s` | 🟡 Warning |
| 数据库连接池耗尽 | `available_connections < 2` | 🔴 Critical |

---

## 6. 自定义面板

### 添加新面板

1. 打开仪表板
2. 点击右上角 **Add panel**
3. 选择 **Add a new panel**
4. 在 **Query** 中输入PromQL表达式
5. 配置可视化类型
6. 点击 **Apply**

### 常用PromQL查询

```promql
# HTTP请求总数（按状态码）
sum(lark_service_http_requests_total) by (status)

# API调用成功率
sum(rate(lark_service_api_calls_total{status="success"}[5m])) /
sum(rate(lark_service_api_calls_total[5m])) * 100

# Token刷新失败率
sum(rate(lark_service_token_refreshes_total{status="failure"}[5m])) /
sum(rate(lark_service_token_refreshes_total[5m])) * 100

# 消息发送趋势
increase(lark_service_messages_sent_total[1h])
```

---

## 7. 故障排查

### 问题: 仪表板无数据

**检查清单**:

1. **Metrics服务器是否运行？**
   ```bash
   curl http://localhost:9091/health
   ```

2. **Prometheus是否能采集数据？**
   ```bash
   curl 'http://localhost:9090/api/v1/targets' | grep lark-service
   ```

3. **数据源配置是否正确？**
   - 在Grafana中测试数据源连接

4. **查询时间范围是否正确？**
   - 检查仪表板右上角的时间选择器

### 问题: 指标值为0

这是正常的！如果应用没有实际流量，大部分计数器指标会是0。

**生成测试数据**:
```bash
# 运行集成测试生成流量
pytest tests/integration/ -v
```

---

## 8. 相关链接

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Metrics端点**: http://localhost:9091/metrics
- **Health端点**: http://localhost:9091/health

---

**维护者**: Backend Team
**创建日期**: 2026-01-18
**最后更新**: 2026-01-18
