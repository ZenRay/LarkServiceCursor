# 错误码文档

本文档列出Lark Service中所有可能的错误码及其含义。

## 系统错误码 (1xxx)

| 错误码 | 名称 | 描述 | 解决方案 |
|--------|------|------|----------|
| 1000 | ConfigError | 配置错误 | 检查环境变量配置 |
| 1001 | DatabaseError | 数据库错误 | 检查数据库连接和配置 |
| 1002 | CacheError | 缓存错误 | 检查Redis连接 |
| 1003 | QueueError | 消息队列错误 | 检查RabbitMQ状态 |

## Token错误码 (2xxx)

| 错误码 | 名称 | 描述 | 解决方案 |
|--------|------|------|----------|
| 2001 | TokenExpired | Token已过期 | 自动刷新或手动刷新 |
| 2002 | TokenRefreshFailed | Token刷新失败 | 检查凭据是否正确 |
| 2003 | TokenNotFound | Token不存在 | 先获取Token |
| 2004 | InvalidCredentials | 凭据无效 | 检查App ID和Secret |

## API错误码 (3xxx)

| 错误码 | 名称 | 描述 | 解决方案 |
|--------|------|------|----------|
| 3001 | APICallFailed | API调用失败 | 查看详细错误信息 |
| 3002 | RateLimitExceeded | 超过速率限制 | 降低请求频率 |
| 3003 | APITimeout | API超时 | 增加超时时间或重试 |
| 3004 | InvalidResponse | 响应格式错误 | 联系技术支持 |

## 飞书API错误码 (99991xxx)

来自飞书开放平台的错误码:

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| 99991400 | app_id参数错误 | 检查App ID配置 |
| 99991401 | app_secret参数错误 | 检查App Secret配置 |
| 99991405 | 请求频率过高 | 实施速率限制 |
| 99991663 | Token已过期 | 刷新Token |
| 99991664 | Token不存在 | 重新获取Token |
| 99991668 | 用户token已过期 | 重新获取user_access_token |

完整的飞书错误码参见: https://open.feishu.cn/document/ukTMukTMukTM/ugjM14COyUjL4ITN

## 业务错误码 (4xxx)

| 错误码 | 名称 | 描述 | 解决方案 |
|--------|------|------|----------|
| 4001 | UserNotFound | 用户不存在 | 检查用户ID |
| 4002 | DepartmentNotFound | 部门不存在 | 检查部门ID |
| 4003 | MessageSendFailed | 消息发送失败 | 检查接收者ID和权限 |
| 4004 | DocumentNotFound | 文档不存在 | 检查文档Token |

## 使用示例

```python
from lark_service.core.exceptions import LarkServiceError

try:
    client.send_message(...)
except LarkServiceError as e:
    print(f"错误码: {e.code}")
    print(f"错误信息: {e.message}")

    if e.code == 2001:  # TokenExpired
        # 自动刷新token
        pass
    elif e.code == 3002:  # RateLimitExceeded
        # 等待后重试
        time.sleep(60)
```
