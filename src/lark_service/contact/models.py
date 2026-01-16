"""Contact module data models.

This module defines Pydantic models for contact query operations:
- User: User information (includes open_id, user_id, union_id)
- UserCache: User cache (PostgreSQL storage)
- Department: Department information
- ChatGroup: Chat group information

Reference:
- docs/phase4-spec-enhancements.md (Contact module)
- specs/001-lark-service-core/contracts/contact.yaml
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ==================== User Models ====================


class User(BaseModel):
    """User information.

    Contains three ID types:
    - open_id: Application-scoped user ID (different across apps)
    - user_id: Tenant-scoped user ID (same within tenant)
    - union_id: Global user ID (same across tenants)

    Usage scenarios:
    - open_id: Send messages, authorization, etc.
    - user_id: User management, permission control within tenant
    - union_id: Cross-tenant user identification, cache key (recommended)
    """

    # Three IDs (required)
    open_id: str = Field(
        ...,
        description="Application-scoped user ID",
        pattern=r"^ou_[a-zA-Z0-9]{20,}$",
    )

    user_id: str = Field(
        ...,
        description="Tenant-scoped user ID",
        pattern=r"^[a-zA-Z0-9]{8,}$",
    )

    union_id: str = Field(
        ...,
        description="Global user ID (recommended for cache key)",
        pattern=r"^on_[a-zA-Z0-9]{20,}$",
    )

    # Basic information (required)
    name: str = Field(..., description="User name", max_length=100)

    # Optional information
    avatar: str | None = Field(None, description="Avatar URL")
    email: str | None = Field(None, description="Email address")
    mobile: str | None = Field(None, description="Mobile number")
    department_ids: list[str] | None = Field(None, description="Department ID list")
    employee_no: str | None = Field(None, description="Employee number")
    job_title: str | None = Field(None, description="Job title")
    status: int | None = Field(
        None, description="User status (1: active, 2: inactive, 4: resigned)"
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Validate email format."""
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
        """Validate mobile number format (Chinese mainland)."""
        if v is None:
            return v

        import re

        # Chinese mainland mobile: starts with 1, 11 digits
        mobile_pattern = r"^1[3-9]\d{9}$"
        if not re.match(mobile_pattern, v):
            raise ValueError(f"Invalid mobile format: {v} (expected Chinese mobile number)")

        return v


class UserCache(BaseModel):
    """User cache (PostgreSQL storage).

    Cache strategy:
    - TTL: 24 hours
    - Refresh strategy: Lazy loading (refresh on cache miss)
    - app_id isolation: Different apps use different caches
    - Cache key format: user:{app_id}:{union_id}

    Limits:
    - Max cache capacity: 100,000 entries
    - Batch query: Max 200 users
    - Batch update: Max 1,000 entries
    """

    # Cache key components
    app_id: str = Field(..., description="Application ID")
    union_id: str = Field(..., description="User union_id (cache key)")

    # User information (same as User model)
    open_id: str = Field(..., description="Application-scoped user ID")
    user_id: str = Field(..., description="Tenant-scoped user ID")
    name: str = Field(..., description="User name")
    avatar: str | None = Field(None, description="Avatar URL")
    email: str | None = Field(None, description="Email address")
    mobile: str | None = Field(None, description="Mobile number")
    department_ids: list[str] | None = Field(None, description="Department ID list")
    employee_no: str | None = Field(None, description="Employee number")
    job_title: str | None = Field(None, description="Job title")
    status: int | None = Field(None, description="User status")

    # Cache metadata
    cached_at: datetime = Field(..., description="Cache time")
    expires_at: datetime = Field(..., description="Expiration time (cached_at + 24h)")
    version: int = Field(1, description="Version number (optimistic lock)")

    @property
    def is_expired(self) -> bool:
        """Check if cache is expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def cache_key(self) -> str:
        """Generate cache key."""
        return f"user:{self.app_id}:{self.union_id}"


# ==================== Department Models ====================


class Department(BaseModel):
    """Department information.

    Limits:
    - Max 1,000 users per department
    """

    department_id: str = Field(
        ...,
        description="Department ID (open_department_id)",
        pattern=r"^od-[a-zA-Z0-9]{20,}$",
    )

    name: str = Field(..., description="Department name", max_length=100)

    parent_department_id: str | None = Field(None, description="Parent department ID")

    # Department hierarchy
    department_path: list[str] | None = Field(
        None, description="Department path (from root to current)"
    )

    # Department leader
    leader_user_id: str | None = Field(None, description="Department leader user_id")

    # Member statistics
    member_count: int | None = Field(None, description="Member count", ge=0, le=1000)

    # Metadata
    status: int | None = Field(None, description="Department status (1: active, 0: inactive)")
    order: int | None = Field(None, description="Sort order")


class DepartmentUser(BaseModel):
    """Department member relationship.

    Used when batch getting department members.
    """

    department_id: str = Field(..., description="Department ID")

    user_id: str = Field(..., description="User ID")

    # User role in department
    is_leader: bool = Field(False, description="Is department leader")

    order: int | None = Field(None, description="Sort order")


# ==================== Chat Group Models ====================


class ChatGroup(BaseModel):
    """Chat group information.

    Represents a Feishu chat group.
    """

    chat_id: str = Field(
        ...,
        description="Chat group ID",
        pattern=r"^oc_[a-zA-Z0-9]{20,}$",
    )

    name: str = Field(..., description="Group name", max_length=100)

    description: str | None = Field(None, description="Group description", max_length=500)

    # Group owner
    owner_id: str | None = Field(None, description="Group owner user_id")

    # Group members
    member_count: int | None = Field(None, description="Member count", ge=0)

    # Group settings
    chat_mode: str | None = Field(
        None, description="Chat mode (group: group chat, p2p: direct message)"
    )

    chat_type: str | None = Field(None, description="Chat type (private: private, public: public)")

    # Metadata
    avatar: str | None = Field(None, description="Group avatar URL")
    create_time: datetime | None = Field(None, description="Create time")
    update_time: datetime | None = Field(None, description="Update time")


class ChatMember(BaseModel):
    """Chat group member.

    Used when getting group member list.
    """

    chat_id: str = Field(..., description="Chat group ID")

    user_id: str = Field(..., description="User ID")

    # Member role
    member_role: str | None = Field(
        None, description="Member role (owner: owner, admin: admin, member: member)"
    )

    # Join time
    join_time: datetime | None = Field(None, description="Join time")


# ==================== Batch Operation Models ====================


class BatchUserQuery(BaseModel):
    """Batch user query request.

    Limits:
    - Max 200 users
    """

    emails: list[str] | None = Field(
        None,
        description="Email list",
        max_length=200,
    )

    mobiles: list[str] | None = Field(
        None,
        description="Mobile number list",
        max_length=200,
    )

    user_ids: list[str] | None = Field(
        None,
        description="User ID list",
        max_length=200,
    )

    @field_validator("emails", "mobiles", "user_ids")
    @classmethod
    def validate_at_least_one(cls, v: list[str] | None, info: Any) -> list[str] | None:
        """Validate at least one query method is provided."""
        # This validation is better in model_validator, simplified here
        return v


class BatchUserResponse(BaseModel):
    """Batch user query response."""

    users: list[User] = Field(..., description="User list")

    not_found: list[str] | None = Field(
        None, description="Not found query conditions (email/mobile/user_id)"
    )

    total: int = Field(..., description="Total users found")


# ==================== Cache Statistics Models ====================


class CacheStats(BaseModel):
    """Cache statistics.

    Used for monitoring cache performance.
    """

    app_id: str = Field(..., description="Application ID")

    # Cache capacity
    total_cached: int = Field(..., description="Total cached entries", ge=0)
    max_capacity: int = Field(100000, description="Max capacity")

    # Hit rate statistics
    hit_count: int = Field(0, description="Hit count", ge=0)
    miss_count: int = Field(0, description="Miss count", ge=0)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return self.hit_count / total

    @property
    def usage_rate(self) -> float:
        """Calculate cache usage rate."""
        return self.total_cached / self.max_capacity

    # Statistics time
    stats_time: datetime = Field(..., description="Statistics time")
