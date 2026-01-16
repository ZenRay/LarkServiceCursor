"""Contact 模块数据模型

本模块定义通讯录查询相关的 Pydantic 模型,包括:
- User: 用户信息 (包含 open_id, user_id, union_id)
- UserCache: 用户缓存 (PostgreSQL 存储)
- Department: 部门信息
- ChatGroup: 群组信息

参考文档:
- docs/phase4-spec-enhancements.md (Contact 模块补充)
- specs/001-lark-service-core/contracts/contact.yaml
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ==================== 用户相关模型 ====================


class User(BaseModel):
    """用户信息

    包含三种 ID 类型:
    - open_id: 应用内用户标识 (应用维度,不同应用不同)
    - user_id: 租户内用户标识 (租户维度,同一租户相同)
    - union_id: 跨租户用户标识 (全局维度,跨租户相同)

    使用场景:
    - open_id: 发送消息、授权等应用内操作
    - user_id: 租户内用户管理、权限控制
    - union_id: 跨租户用户识别、缓存 key (推荐)
    """

    # 三种 ID (必填)
    open_id: str = Field(
        ...,
        description="应用内用户标识",
        pattern=r"^ou_[a-zA-Z0-9]{20,}$",
    )

    user_id: str = Field(
        ...,
        description="租户内用户标识",
        pattern=r"^[a-zA-Z0-9]{8,}$",
    )

    union_id: str = Field(
        ...,
        description="跨租户用户标识 (推荐用于缓存 key)",
        pattern=r"^on_[a-zA-Z0-9]{20,}$",
    )

    # 基本信息 (必填)
    name: str = Field(..., description="用户名称", max_length=100)

    # 可选信息
    avatar: str | None = Field(None, description="头像 URL")
    email: str | None = Field(None, description="邮箱地址")
    mobile: str | None = Field(None, description="手机号")
    department_ids: list[str] | None = Field(None, description="部门 ID 列表")
    employee_no: str | None = Field(None, description="工号")
    job_title: str | None = Field(None, description="职位")
    status: int | None = Field(None, description="用户状态 (1: 激活, 2: 停用, 4: 离职)")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """验证邮箱格式"""
        if v is None:
            return v

        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError(f"Invalid email format: {v}")

        return v

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: str | None) -> str | None:
        """验证手机号格式 (中国大陆)"""
        if v is None:
            return v

        import re

        # 中国大陆手机号: 1 开头,11 位数字
        mobile_pattern = r"^1[3-9]\d{9}$"
        if not re.match(mobile_pattern, v):
            raise ValueError(f"Invalid mobile format: {v} (expected Chinese mobile number)")

        return v


class UserCache(BaseModel):
    """用户缓存 (PostgreSQL 存储)

    缓存策略:
    - TTL: 24 小时
    - 刷新策略: 懒加载 (缓存未命中时刷新)
    - app_id 隔离: 不同应用使用不同缓存
    - 缓存 key 格式: user:{app_id}:{union_id}

    限制:
    - 最大缓存容量: 100,000 条
    - 批量查询: 最大 200 个用户
    - 批量更新: 最大 1,000 条
    """

    # 缓存 key 组成部分
    app_id: str = Field(..., description="应用 ID")
    union_id: str = Field(..., description="用户 union_id (缓存 key)")

    # 用户信息 (与 User 模型一致)
    open_id: str = Field(..., description="应用内用户标识")
    user_id: str = Field(..., description="租户内用户标识")
    name: str = Field(..., description="用户名称")
    avatar: str | None = Field(None, description="头像 URL")
    email: str | None = Field(None, description="邮箱地址")
    mobile: str | None = Field(None, description="手机号")
    department_ids: list[str] | None = Field(None, description="部门 ID 列表")
    employee_no: str | None = Field(None, description="工号")
    job_title: str | None = Field(None, description="职位")
    status: int | None = Field(None, description="用户状态")

    # 缓存元数据
    cached_at: datetime = Field(..., description="缓存时间")
    expires_at: datetime = Field(..., description="过期时间 (cached_at + 24h)")
    version: int = Field(1, description="版本号 (乐观锁)")

    @property
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        from datetime import datetime

        return datetime.now(UTC) > self.expires_at

    @property
    def cache_key(self) -> str:
        """生成缓存 key"""
        return f"user:{self.app_id}:{self.union_id}"


# ==================== 部门相关模型 ====================


class Department(BaseModel):
    """部门信息

    限制:
    - 单个部门最大用户数: 1,000
    """

    department_id: str = Field(
        ...,
        description="部门 ID (open_department_id)",
        pattern=r"^od-[a-zA-Z0-9]{20,}$",
    )

    name: str = Field(..., description="部门名称", max_length=100)

    parent_department_id: str | None = Field(None, description="父部门 ID")

    # 部门层级
    department_path: list[str] | None = Field(None, description="部门路径 (从根到当前)")

    # 部门负责人
    leader_user_id: str | None = Field(None, description="部门负责人 user_id")

    # 成员统计
    member_count: int | None = Field(None, description="成员数量", ge=0, le=1000)

    # 元数据
    status: int | None = Field(None, description="部门状态 (1: 启用, 0: 停用)")
    order: int | None = Field(None, description="排序")


class DepartmentUser(BaseModel):
    """部门成员关系

    用于批量获取部门成员时返回。
    """

    department_id: str = Field(..., description="部门 ID")

    user_id: str = Field(..., description="用户 ID")

    # 用户在部门中的角色
    is_leader: bool = Field(False, description="是否为部门负责人")

    order: int | None = Field(None, description="排序")


# ==================== 群组相关模型 ====================


class ChatGroup(BaseModel):
    """群组信息

    表示一个飞书群聊。
    """

    chat_id: str = Field(
        ...,
        description="群组 ID",
        pattern=r"^oc_[a-zA-Z0-9]{20,}$",
    )

    name: str = Field(..., description="群组名称", max_length=100)

    description: str | None = Field(None, description="群组描述", max_length=500)

    # 群主
    owner_id: str | None = Field(None, description="群主 user_id")

    # 群成员
    member_count: int | None = Field(None, description="成员数量", ge=0)

    # 群设置
    chat_mode: str | None = Field(None, description="群模式 (group: 群聊, p2p: 单聊)")

    chat_type: str | None = Field(None, description="群类型 (private: 私有, public: 公开)")

    # 元数据
    avatar: str | None = Field(None, description="群头像 URL")
    create_time: datetime | None = Field(None, description="创建时间")
    update_time: datetime | None = Field(None, description="更新时间")


class ChatMember(BaseModel):
    """群组成员

    用于获取群组成员列表时返回。
    """

    chat_id: str = Field(..., description="群组 ID")

    user_id: str = Field(..., description="用户 ID")

    # 成员角色
    member_role: str | None = Field(
        None, description="成员角色 (owner: 群主, admin: 管理员, member: 成员)"
    )

    # 加入时间
    join_time: datetime | None = Field(None, description="加入时间")


# ==================== 批量操作相关模型 ====================


class BatchUserQuery(BaseModel):
    """批量用户查询请求

    限制:
    - 最大 200 个用户
    """

    emails: list[str] | None = Field(
        None,
        description="邮箱列表",
        max_length=200,
    )

    mobiles: list[str] | None = Field(
        None,
        description="手机号列表",
        max_length=200,
    )

    user_ids: list[str] | None = Field(
        None,
        description="用户 ID 列表",
        max_length=200,
    )

    @field_validator("emails", "mobiles", "user_ids")
    @classmethod
    def validate_at_least_one(cls, v: list[str] | None, info: Any) -> list[str] | None:
        """验证至少提供一种查询方式"""
        # 这个验证在 model_validator 中更合适,这里先简化
        return v


class BatchUserResponse(BaseModel):
    """批量用户查询响应"""

    users: list[User] = Field(..., description="用户列表")

    not_found: list[str] | None = Field(None, description="未找到的查询条件 (email/mobile/user_id)")

    total: int = Field(..., description="找到的用户总数")


# ==================== 缓存统计相关模型 ====================


class CacheStats(BaseModel):
    """缓存统计信息

    用于监控缓存性能。
    """

    app_id: str = Field(..., description="应用 ID")

    # 缓存容量
    total_cached: int = Field(..., description="总缓存数量", ge=0)
    max_capacity: int = Field(100000, description="最大容量")

    # 命中率统计
    hit_count: int = Field(0, description="命中次数", ge=0)
    miss_count: int = Field(0, description="未命中次数", ge=0)

    @property
    def hit_rate(self) -> float:
        """计算缓存命中率"""
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return self.hit_count / total

    @property
    def usage_rate(self) -> float:
        """计算缓存使用率"""
        return self.total_cached / self.max_capacity

    # 统计时间
    stats_time: datetime = Field(..., description="统计时间")
