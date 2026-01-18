# RabbitMQ 配置需求与最佳实践

**版本**: 1.0.0
**更新时间**: 2026-01-18
**状态**: Production Ready
**适用范围**: Lark Service 企业自建应用核心组件

---

## 📋 需求概述 (FR-122)

RabbitMQ 用于 **异步处理飞书交互式卡片回调事件**,确保回调消息的可靠传递和处理。

### 核心需求

- ✅ **队列持久化**: 确保RabbitMQ重启后消息不丢失
- ✅ **消息持久化**: 确保消息在队列中持久化存储
- ✅ **手动ACK机制**: 确保消息处理成功后才确认
- ✅ **死信队列(DLQ)**: 处理失败的消息自动进入死信队列
- ✅ **连接重试**: 网络故障时自动重连(指数退避策略)

---

## 🔧 RabbitMQ 版本要求

### 最低版本

- **RabbitMQ**: ≥ 3.12.0 (推荐 3.12.x 最新稳定版)
- **Erlang**: ≥ 25.0 (RabbitMQ 3.12.x 要求)

### 版本选择理由

- RabbitMQ 3.12.x 提供了更好的性能和稳定性
- 支持 Quorum Queues (仲裁队列) 提供更高的数据可靠性
- 改进的内存管理和流量控制

### 验证命令

```bash
# 检查 RabbitMQ 版本
rabbitmqctl version

# 检查 Erlang 版本
rabbitmqctl eval 'erlang:system_info(otp_release).'
```

---

## 🏗️ 队列配置

### 1. 队列持久化 (Durable Queues)

**需求**: 队列必须声明为持久化,确保 RabbitMQ 重启后队列不丢失。

**Python 配置示例**:

```python
import pika

# 连接参数
credentials = pika.PlainCredentials('lark_service', 'your_password')
parameters = pika.ConnectionParameters(
    host='localhost',
    port=5672,
    credentials=credentials,
    heartbeat=60,
    blocked_connection_timeout=300
)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# 声明持久化队列
channel.queue_declare(
    queue='lark_card_callbacks',
    durable=True,  # ✅ 队列持久化
    arguments={
        'x-message-ttl': 86400000,  # 消息TTL: 24小时 (毫秒)
        'x-max-length': 10000,       # 队列最大长度
        'x-overflow': 'reject-publish',  # 队列满时拒绝新消息
    }
)
```

**验证**:

```bash
# 查看队列是否持久化
rabbitmqctl list_queues name durable
```

---

### 2. 消息持久化 (Persistent Messages)

**需求**: 所有消息必须标记为持久化(`delivery_mode=2`),确保消息在队列中不丢失。

**Python 配置示例**:

```python
# 发送持久化消息
channel.basic_publish(
    exchange='',
    routing_key='lark_card_callbacks',
    body=message_body,
    properties=pika.BasicProperties(
        delivery_mode=2,  # ✅ 消息持久化 (1=非持久化, 2=持久化)
        content_type='application/json',
        timestamp=int(time.time()),
        message_id=generate_message_id()
    )
)
```

**重要提示**:
- 即使队列持久化,消息也必须显式标记为持久化才不会丢失
- 持久化会略微降低性能,但对于生产环境是必需的

---

### 3. 手动ACK机制 (Manual Acknowledgment)

**需求**: 消费者必须使用手动ACK,确保消息处理成功后才从队列删除。

**Python 配置示例**:

```python
def callback(ch, method, properties, body):
    """处理卡片回调消息"""
    try:
        # 解析消息
        event = json.loads(body)

        # 处理业务逻辑
        process_card_callback(event)

        # ✅ 手动ACK - 处理成功
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Message processed successfully: {method.delivery_tag}")

    except json.JSONDecodeError as e:
        # 消息格式错误,无法重试,拒绝消息(不重新入队)
        ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        logger.error(f"Invalid message format: {e}")

    except Exception as e:
        # 处理失败,拒绝消息并重新入队(最多重试3次)
        retry_count = properties.headers.get('x-retry-count', 0) if properties.headers else 0

        if retry_count < 3:
            # 重新入队,增加重试计数
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
            logger.warning(f"Message processing failed, retry {retry_count + 1}/3: {e}")
        else:
            # 超过重试次数,拒绝消息(进入死信队列)
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            logger.error(f"Message processing failed after 3 retries: {e}")

# 启动消费者 (禁用自动ACK)
channel.basic_consume(
    queue='lark_card_callbacks',
    on_message_callback=callback,
    auto_ack=False  # ✅ 禁用自动ACK,使用手动ACK
)

channel.start_consuming()
```

**ACK 策略**:
- `basic_ack()`: 消息处理成功,从队列删除
- `basic_reject(requeue=True)`: 消息处理失败,重新入队
- `basic_reject(requeue=False)`: 消息处理失败,丢弃或进入死信队列

---

### 4. 死信队列 (Dead Letter Queue)

**需求**: 配置死信队列,处理失败的消息自动进入DLQ,避免消息丢失。

**Python 配置示例**:

```python
# 1. 声明死信交换机
channel.exchange_declare(
    exchange='lark_dlx',
    exchange_type='direct',
    durable=True
)

# 2. 声明死信队列
channel.queue_declare(
    queue='lark_card_callbacks_dlq',
    durable=True
)

# 3. 绑定死信队列到死信交换机
channel.queue_bind(
    queue='lark_card_callbacks_dlq',
    exchange='lark_dlx',
    routing_key='lark_card_callbacks'
)

# 4. 声明主队列并配置死信交换机
channel.queue_declare(
    queue='lark_card_callbacks',
    durable=True,
    arguments={
        'x-dead-letter-exchange': 'lark_dlx',  # ✅ 死信交换机
        'x-dead-letter-routing-key': 'lark_card_callbacks',  # 死信路由键
        'x-message-ttl': 86400000,  # 消息TTL: 24小时
        'x-max-length': 10000,  # 队列最大长度
    }
)
```

**死信触发条件**:
1. 消息被拒绝 (`basic_reject` 或 `basic_nack`) 且 `requeue=False`
2. 消息TTL过期 (`x-message-ttl`)
3. 队列达到最大长度 (`x-max-length`)

**监控死信队列**:

```bash
# 查看死信队列消息数量
rabbitmqctl list_queues name messages

# 消费死信队列进行人工处理
rabbitmq-plugins enable rabbitmq_management
# 访问 http://localhost:15672 查看消息内容
```

---

## 🔄 连接重试策略

**需求**: 网络故障时自动重连,使用指数退避策略避免雪崩。

**Python 配置示例**:

```python
import time
from typing import Callable

def connect_with_retry(
    connection_params: pika.ConnectionParameters,
    max_retries: int = 5,
    base_delay: float = 1.0
) -> pika.BlockingConnection:
    """连接 RabbitMQ 并支持自动重试"""

    for attempt in range(max_retries):
        try:
            connection = pika.BlockingConnection(connection_params)
            logger.info("Connected to RabbitMQ successfully")
            return connection

        except pika.exceptions.AMQPConnectionError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # 指数退避: 1s, 2s, 4s, 8s, 16s
                logger.warning(f"RabbitMQ connection failed, retry {attempt + 1}/{max_retries} in {delay}s: {e}")
                time.sleep(delay)
            else:
                logger.error(f"Failed to connect to RabbitMQ after {max_retries} attempts")
                raise

# 使用示例
connection = connect_with_retry(parameters)
```

**连接参数优化**:

```python
parameters = pika.ConnectionParameters(
    host='localhost',
    port=5672,
    credentials=credentials,
    heartbeat=60,  # 心跳间隔60秒,检测连接状态
    blocked_connection_timeout=300,  # 连接阻塞超时5分钟
    connection_attempts=3,  # SDK内部重试3次
    retry_delay=2,  # SDK重试间隔2秒
    socket_timeout=10  # Socket超时10秒
)
```

---

## 🔒 安全配置

### 1. 用户权限

**最小权限原则**: 为 Lark Service 创建专用用户,仅授予必需权限。

```bash
# 创建用户
rabbitmqctl add_user lark_service 'strong_password_here'

# 授予权限 (configure/write/read 权限仅限特定队列)
rabbitmqctl set_permissions -p / lark_service "^lark_.*" "^lark_.*" "^lark_.*"

# 验证权限
rabbitmqctl list_user_permissions lark_service
```

### 2. 网络安全

- ✅ **生产环境禁用Guest用户**: `rabbitmqctl delete_user guest`
- ✅ **启用TLS加密**: 使用 `amqps://` 协议
- ✅ **限制访问IP**: 配置防火墙仅允许应用服务器访问
- ✅ **使用强密码**: 密码长度 ≥ 16位,包含大小写字母/数字/特殊字符

---

## 📊 监控与告警

### 1. 关键指标监控

| 指标 | 阈值 | 告警级别 |
|------|------|----------|
| 队列消息积压 | > 1000 | WARNING |
| 队列消息积压 | > 5000 | CRITICAL |
| 死信队列消息数 | > 100 | WARNING |
| 消费者数量 | = 0 | CRITICAL |
| 内存使用率 | > 80% | WARNING |
| 磁盘使用率 | > 85% | CRITICAL |

### 2. 监控命令

```bash
# 查看队列状态
rabbitmqctl list_queues name messages messages_ready messages_unacknowledged consumers

# 查看连接状态
rabbitmqctl list_connections name state channels

# 查看资源使用
rabbitmqctl status
```

### 3. Prometheus 监控 (推荐)

```bash
# 启用 Prometheus 插件
rabbitmq-plugins enable rabbitmq_prometheus

# 访问 metrics 端点
curl http://localhost:15692/metrics
```

---

## 🚀 生产部署清单

### 部署前检查

- [ ] ✅ RabbitMQ 版本 ≥ 3.12.0
- [ ] ✅ 队列声明为持久化 (`durable=True`)
- [ ] ✅ 消息标记为持久化 (`delivery_mode=2`)
- [ ] ✅ 消费者使用手动ACK (`auto_ack=False`)
- [ ] ✅ 配置死信队列 (`x-dead-letter-exchange`)
- [ ] ✅ 实现连接重试 (指数退避策略)
- [ ] ✅ 创建专用用户并限制权限
- [ ] ✅ 禁用Guest用户
- [ ] ✅ 配置监控告警
- [ ] ✅ 设置消息TTL (`x-message-ttl`)
- [ ] ✅ 设置队列最大长度 (`x-max-length`)

### 环境变量配置

```bash
# .env 文件
RABBITMQ_HOST=rabbitmq.internal.example.com
RABBITMQ_PORT=5672
RABBITMQ_USER=lark_service
RABBITMQ_PASSWORD=<strong_password>
RABBITMQ_VHOST=/
RABBITMQ_QUEUE_NAME=lark_card_callbacks
RABBITMQ_DLQ_NAME=lark_card_callbacks_dlq
RABBITMQ_HEARTBEAT=60
RABBITMQ_CONNECTION_TIMEOUT=30
```

---

## 📚 参考文档

- [RabbitMQ 官方文档](https://www.rabbitmq.com/documentation.html)
- [RabbitMQ 持久化指南](https://www.rabbitmq.com/persistence-conf.html)
- [RabbitMQ 死信队列](https://www.rabbitmq.com/dlx.html)
- [Pika Python 客户端文档](https://pika.readthedocs.io/)

---

**文档维护**: 本文档应随 RabbitMQ 版本升级和最佳实践变化及时更新。
**最后审核**: 2026-01-18
