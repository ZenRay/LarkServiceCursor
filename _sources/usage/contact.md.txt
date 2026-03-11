# 通讯录服务

本文档覆盖通讯录模块的核心能力：用户查询、部门查询、群聊查询与分页访问。

## 快速开始

```python
from lark_service.contact import ContactClient

contact_client = ContactClient(credential_pool=credential_pool)
```

## 常用方法参数速查

| 方法 | 关键参数 | 返回值 |
| --- | --- | --- |
| `get_user_by_email()` | `email`, `app_id?` | `User` |
| `get_user_by_mobile()` | `mobile`, `app_id?` | `User` |
| `get_user_by_user_id()` | `user_id`, `app_id?` | `User` |
| `batch_get_users()` | `queries(<=50)`, `app_id?` | `BatchUserResponse` |
| `get_department()` | `department_id`, `app_id?` | `Department` |
| `get_department_members()` | `department_id`, `page_size(1~100)`, `page_token?`, `app_id?` | `(list[DepartmentUser], next_page_token)` |
| `get_chat_group()` | `chat_id`, `app_id?` | `ChatGroup` |
| `get_chat_members()` | `chat_id`, `page_size(1~100)`, `page_token?`, `app_id?` | `(list[ChatMember], next_page_token)` |

## 关键返回字段

| 返回模型 | 关键字段 | 说明 |
| --- | --- | --- |
| `User` | `open_id`, `user_id`, `union_id`, `name`, `email`, `mobile` | 用户标识与基础信息 |
| `BatchUserResponse` | `users`, `not_found`, `total` | 批量查询结果与未命中列表 |
| `Department` | `department_id`, `name`, `parent_department_id`, `member_count` | 部门基础信息 |
| `ChatGroup` | `chat_id`, `name`, `owner_id`, `chat_mode`, `chat_type` | 群聊基础信息 |
| `DepartmentUser` / `ChatMember` | `user_id`（及角色字段） | 成员列表项 |

## 用户查询

### 1) 按邮箱查询

```python
user = contact_client.get_user_by_email(
    email="user@example.com",
    app_id="cli_xxx"
)
print(user.name, user.open_id)
```

### 2) 按手机号查询

```python
user = contact_client.get_user_by_mobile(
    mobile="+8613800138000",
    app_id="cli_xxx"
)
print(user.name, user.open_id)
```

### 3) 按 user_id 查询

```python
user = contact_client.get_user_by_user_id(
    user_id="4d7a3c6g",
    app_id="cli_xxx"
)
print(user.name, user.open_id)
```

> 返回值是 `User` 模型对象，使用属性访问（如 `user.open_id`），不要用下标访问。

## 批量查询用户

```python
from lark_service.contact.models import BatchUserQuery

queries = [
    BatchUserQuery(emails=["user1@example.com"]),
    BatchUserQuery(mobiles=["+8613800138001"]),
    BatchUserQuery(user_ids=["4d7a3c6g"]),
]

result = contact_client.batch_get_users(
    queries=queries,
    app_id="cli_xxx"
)

print(result.total)
for u in result.users:
    print(u.name, u.open_id)
print("not_found:", result.not_found)
```

## 部门能力

### 获取部门信息

```python
dept = contact_client.get_department(
    department_id="od-xxx",
    app_id="cli_xxx"
)
print(dept.name, dept.department_id)
```

### 获取部门成员（分页）

```python
members, next_token = contact_client.get_department_members(
    department_id="od-xxx",
    page_size=50,
    app_id="cli_xxx"
)

print(len(members), next_token)
if next_token:
    members2, _ = contact_client.get_department_members(
        department_id="od-xxx",
        page_size=50,
        page_token=next_token,
        app_id="cli_xxx"
    )
    print("next page:", len(members2))
```

## 群聊能力

### 获取群聊信息

```python
group = contact_client.get_chat_group(
    chat_id="oc_xxx",
    app_id="cli_xxx"
)
print(group.name, group.chat_id)
```

### 获取群成员（分页）

```python
members, next_token = contact_client.get_chat_members(
    chat_id="oc_xxx",
    page_size=50,
    app_id="cli_xxx"
)

print(len(members), next_token)
```

## 缓存能力（可选）

启用缓存后，查询会优先命中缓存，未命中再访问飞书 API。

```python
from datetime import timedelta
from lark_service.contact import ContactCacheManager

cache_manager = ContactCacheManager(db_url=config.get_postgres_url())
cached_client = ContactClient(
    credential_pool=credential_pool,
    cache_manager=cache_manager,
    enable_cache=True,
    cache_ttl=timedelta(hours=24),
)
```

## 常见易错点

- 用户查询返回 `User` 对象，使用 `user.open_id`，不是 `user["open_id"]`
- `batch_get_users` 单次最多 50 个查询条件
- `get_department_members` / `get_chat_members` 的 `page_size` 范围是 1~100
- 群聊相关 ID 使用 `chat_id`（通常是 `oc_xxx`）

## 应用管理

通讯录服务同样支持多应用切换，详见 [应用管理文档](app-management.md)。

更多参考：
- [5 层 app_id 解析优先级](app-management.md)
- [多应用场景](app-management.md)
- [动态切换应用](app-management.md)
- [高级用法](advanced.md)
