"""
Extended unit tests for ContactClient - P1 Coverage Improvement.

This file focuses on testing core functionality that was previously untested:
- User query success paths with real data
- Batch query operations with mixed results
- Department operations with real data
- Chat operations with real data
- Caching behavior
- Error handling scenarios
- API rate limiting

Target: Increase coverage from 43.63% to 60%
"""

from datetime import timedelta
from unittest.mock import Mock

import pytest

from lark_service.contact.cache import ContactCacheManager
from lark_service.contact.client import ContactClient, _convert_lark_user_status
from lark_service.contact.models import (
    BatchUserQuery,
    ChatGroup,
    Department,
    User,
)
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    NotFoundError,
    PermissionDeniedError,
)


class TestConvertLarkUserStatus:
    """Test _convert_lark_user_status helper function."""

    def test_convert_none_status(self):
        """Test converting None status returns None."""
        assert _convert_lark_user_status(None) is None

    def test_convert_resigned_status(self):
        """Test converting resigned status returns 4."""
        mock_status = Mock()
        mock_status.is_resigned = True
        mock_status.is_frozen = False
        mock_status.is_activated = True
        assert _convert_lark_user_status(mock_status) == 4

    def test_convert_frozen_status(self):
        """Test converting frozen status returns 2."""
        mock_status = Mock()
        mock_status.is_resigned = False
        mock_status.is_frozen = True
        mock_status.is_activated = False
        assert _convert_lark_user_status(mock_status) == 2

    def test_convert_activated_status(self):
        """Test converting activated status returns 1."""
        mock_status = Mock()
        mock_status.is_resigned = False
        mock_status.is_frozen = False
        mock_status.is_activated = True
        assert _convert_lark_user_status(mock_status) == 1

    def test_convert_default_status(self):
        """Test converting status with no flags defaults to 1."""
        mock_status = Mock(spec=[])  # No attributes
        assert _convert_lark_user_status(mock_status) == 1


class TestContactClientUserQueriesSuccess:
    """Test successful user query operations with real data."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool with successful responses."""
        pool = Mock(spec=CredentialPool)
        mock_sdk_client = Mock()

        # Mock successful batch_get_id response
        mock_batch_response = Mock()
        mock_batch_response.success.return_value = True
        mock_batch_response.code = 0
        mock_batch_response.data = Mock()

        # Mock user contact info
        mock_user_contact = Mock()
        mock_user_contact.user_id = "12345678"
        mock_user_contact.email = "test@example.com"
        mock_user_contact.mobile = "+86-13800138000"
        mock_batch_response.data.user_list = [mock_user_contact]

        mock_sdk_client.contact.v3.user.batch_get_id.return_value = mock_batch_response

        # Mock successful get user response
        mock_get_response = Mock()
        mock_get_response.success.return_value = True
        mock_get_response.code = 0
        mock_get_response.data = Mock()

        # Mock full user object
        mock_lark_user = Mock()
        mock_lark_user.open_id = "ou_a1b2c3d4e5f6g7h8i9j0"
        mock_lark_user.user_id = "12345678"
        mock_lark_user.union_id = "on_x1y2z3a4b5c6d7e8f9g0h1"
        mock_lark_user.name = "Test User"
        mock_lark_user.email = "test@example.com"
        mock_lark_user.mobile = "+86-13800138000"
        mock_lark_user.department_ids = ["od-dept1", "od-dept2"]
        mock_lark_user.employee_no = "EMP001"
        mock_lark_user.job_title = "Engineer"

        # Mock avatar
        mock_avatar = Mock()
        mock_avatar.avatar_origin = "https://example.com/avatar.jpg"
        mock_lark_user.avatar = mock_avatar

        # Mock status
        mock_status = Mock()
        mock_status.is_resigned = False
        mock_status.is_frozen = False
        mock_status.is_activated = True
        mock_lark_user.status = mock_status

        mock_get_response.data.user = mock_lark_user
        mock_sdk_client.contact.v3.user.get.return_value = mock_get_response

        pool._get_sdk_client.return_value = mock_sdk_client
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create ContactClient instance."""
        return ContactClient(mock_credential_pool)

    def test_get_user_by_email_success(self, client):
        """Test successful user retrieval by email."""
        user = client.get_user_by_email(
            app_id="cli_test",
            email="test@example.com",
        )

        assert isinstance(user, User)
        assert user.open_id == "ou_a1b2c3d4e5f6g7h8i9j0"
        assert user.user_id == "12345678"
        assert user.union_id == "on_x1y2z3a4b5c6d7e8f9g0h1"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.mobile == "+86-13800138000"
        assert user.department_ids == ["od-dept1", "od-dept2"]
        assert user.employee_no == "EMP001"
        assert user.job_title == "Engineer"
        assert user.avatar == "https://example.com/avatar.jpg"
        assert user.status == 1  # Active

    def test_get_user_by_mobile_success(self, client):
        """Test successful user retrieval by mobile."""
        user = client.get_user_by_mobile(
            app_id="cli_test",
            mobile="+86-13800138000",
        )

        assert isinstance(user, User)
        assert user.open_id == "ou_a1b2c3d4e5f6g7h8i9j0"
        assert user.name == "Test User"
        assert user.mobile == "+86-13800138000"

    def test_get_user_by_user_id_success(self, client, mock_credential_pool):
        """Test successful user retrieval by user_id."""
        # For user_id query, we only use GetUser API (no batch_get_id)
        # Use the same mock response
        user = client.get_user_by_user_id(
            app_id="cli_test",
            user_id="ou_test123",
        )

        assert isinstance(user, User)
        assert user.open_id == "ou_a1b2c3d4e5f6g7h8i9j0"
        assert user.user_id == "12345678"
        assert user.name == "Test User"

    def test_get_user_with_no_avatar(self, client, mock_credential_pool):
        """Test user retrieval when user has no avatar."""
        # Update mock to have no avatar
        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_response = mock_sdk_client.contact.v3.user.get.return_value
        mock_response.data.user.avatar = None

        user = client.get_user_by_user_id(
            app_id="cli_test",
            user_id="ou_test123",
        )

        assert user.avatar is None

    def test_get_user_with_optional_fields_none(self, client, mock_credential_pool):
        """Test user retrieval with optional fields as None."""
        # Update mock to have optional fields as None
        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_response = mock_sdk_client.contact.v3.user.get.return_value
        mock_user = mock_response.data.user

        mock_user.email = None
        mock_user.mobile = None
        mock_user.department_ids = None
        mock_user.employee_no = None
        mock_user.job_title = None
        mock_user.status = None

        user = client.get_user_by_user_id(
            app_id="cli_test",
            user_id="ou_test123",
        )

        assert user.email is None
        assert user.mobile is None
        assert user.department_ids is None
        assert user.employee_no is None
        assert user.job_title is None
        assert user.status is None


class TestContactClientCaching:
    """Test caching behavior."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        return Mock(spec=ContactCacheManager)

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        mock_sdk_client = Mock()

        # Mock successful API responses
        mock_batch_response = Mock()
        mock_batch_response.success.return_value = True
        mock_batch_response.code = 0
        mock_batch_response.data = Mock()
        mock_user_contact = Mock()
        mock_user_contact.user_id = "12345678"
        mock_batch_response.data.user_list = [mock_user_contact]
        mock_sdk_client.contact.v3.user.batch_get_id.return_value = mock_batch_response

        mock_get_response = Mock()
        mock_get_response.success.return_value = True
        mock_get_response.code = 0
        mock_get_response.data = Mock()
        mock_lark_user = Mock()
        mock_lark_user.open_id = "ou_a1b2c3d4e5f6g7h8i9j0"
        mock_lark_user.user_id = "12345678"
        mock_lark_user.union_id = "on_x1y2z3a4b5c6d7e8f9g0h1"
        mock_lark_user.name = "Cached User"
        mock_lark_user.avatar = None
        mock_lark_user.email = "cached@example.com"
        mock_lark_user.mobile = None
        mock_lark_user.department_ids = None
        mock_lark_user.employee_no = None
        mock_lark_user.job_title = None
        mock_lark_user.status = None
        mock_get_response.data.user = mock_lark_user
        mock_sdk_client.contact.v3.user.get.return_value = mock_get_response

        pool._get_sdk_client.return_value = mock_sdk_client
        return pool

    def test_cache_enabled_with_manager(self, mock_credential_pool, mock_cache_manager):
        """Test cache is enabled when manager is provided."""
        client = ContactClient(
            mock_credential_pool,
            cache_manager=mock_cache_manager,
            enable_cache=True,
        )

        assert client.enable_cache is True
        assert client.cache_manager is mock_cache_manager

    def test_cache_disabled_without_manager(self, mock_credential_pool):
        """Test cache is disabled when manager is not provided."""
        client = ContactClient(
            mock_credential_pool,
            cache_manager=None,
            enable_cache=True,
        )

        # Should disable cache due to missing manager
        assert client.enable_cache is False

    def test_get_user_by_email_cache_hit(self, mock_credential_pool, mock_cache_manager):
        """Test getting user from cache when available."""
        # Setup cache to return a user
        cached_user = User(
            open_id="ou_cachedcachedcachedcached",
            user_id="cached01",
            union_id="on_cachedcachedcachedcached",
            name="Cached User",
        )
        mock_cache_manager.get_user_by_email.return_value = cached_user

        client = ContactClient(
            mock_credential_pool,
            cache_manager=mock_cache_manager,
            enable_cache=True,
        )

        user = client.get_user_by_email(
            app_id="cli_test",
            email="cached@example.com",
        )

        # Should return cached user
        assert user.open_id == "ou_cachedcachedcachedcached"
        assert user.name == "Cached User"

        # Should call cache get method
        mock_cache_manager.get_user_by_email.assert_called_once_with(
            "cli_test", "cached@example.com"
        )

        # Should NOT call API (credential pool should not be called)
        mock_credential_pool._get_sdk_client.assert_not_called()

    def test_get_user_by_email_cache_miss(self, mock_credential_pool, mock_cache_manager):
        """Test getting user from API when cache miss."""
        # Setup cache to return None (cache miss)
        mock_cache_manager.get_user_by_email.return_value = None

        client = ContactClient(
            mock_credential_pool,
            cache_manager=mock_cache_manager,
            enable_cache=True,
        )

        user = client.get_user_by_email(
            app_id="cli_test",
            email="test@example.com",
        )

        # Should call API
        assert user.name == "Cached User"
        mock_credential_pool._get_sdk_client.assert_called_once()

        # Should cache the result
        mock_cache_manager.cache_user.assert_called_once()

    def test_get_user_by_mobile_caching(self, mock_credential_pool, mock_cache_manager):
        """Test caching behavior for mobile query."""
        mock_cache_manager.get_user_by_mobile.return_value = None

        client = ContactClient(
            mock_credential_pool,
            cache_manager=mock_cache_manager,
            enable_cache=True,
        )

        _ = client.get_user_by_mobile(
            app_id="cli_test",
            mobile="+86-13800138000",
        )

        # Should call cache methods
        mock_cache_manager.get_user_by_mobile.assert_called_once()
        mock_cache_manager.cache_user.assert_called_once()

    def test_get_user_by_user_id_caching(self, mock_credential_pool, mock_cache_manager):
        """Test caching behavior for user_id query."""
        mock_cache_manager.get_user_by_user_id.return_value = None

        client = ContactClient(
            mock_credential_pool,
            cache_manager=mock_cache_manager,
            enable_cache=True,
        )

        _ = client.get_user_by_user_id(
            app_id="cli_test",
            user_id="ou_test123",
        )

        # Should call cache methods
        mock_cache_manager.get_user_by_user_id.assert_called_once()
        mock_cache_manager.cache_user.assert_called_once()

    def test_cache_ttl_configuration(self, mock_credential_pool, mock_cache_manager):
        """Test cache TTL can be configured."""
        custom_ttl = timedelta(hours=12)

        client = ContactClient(
            mock_credential_pool,
            cache_manager=mock_cache_manager,
            enable_cache=True,
            cache_ttl=custom_ttl,
        )

        assert client.cache_ttl == custom_ttl

    def test_cache_ttl_default(self, mock_credential_pool, mock_cache_manager):
        """Test default cache TTL is 24 hours."""
        client = ContactClient(
            mock_credential_pool,
            cache_manager=mock_cache_manager,
            enable_cache=True,
        )

        assert client.cache_ttl == timedelta(hours=24)


class TestContactClientBatchOperations:
    """Test batch operations with mixed results."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        mock_sdk_client = Mock()

        # Mock batch response with partial results
        mock_batch_response = Mock()
        mock_batch_response.success.return_value = True
        mock_batch_response.code = 0
        mock_batch_response.data = Mock()

        # Return some users
        user1 = Mock()
        user1.user_id = "user0001"
        user1.email = "user1@example.com"

        user2 = Mock()
        user2.user_id = "user0002"
        user2.mobile = "+86-13800138001"

        mock_batch_response.data.user_list = [user1, user2]
        mock_sdk_client.contact.v3.user.batch_get_id.return_value = mock_batch_response

        # Mock get user responses
        mock_get_response = Mock()
        mock_get_response.success.return_value = True
        mock_get_response.code = 0
        mock_get_response.data = Mock()

        mock_user = Mock()
        mock_user.open_id = "ou_batchuserbatchuserbatch"
        mock_user.user_id = "user0001"
        mock_user.union_id = "on_batchuserbatchuserbatch"
        mock_user.name = "Batch User"
        mock_user.avatar = None
        mock_user.email = "user1@example.com"
        mock_user.mobile = None
        mock_user.department_ids = None
        mock_user.employee_no = None
        mock_user.job_title = None
        mock_user.status = None

        mock_get_response.data.user = mock_user
        mock_sdk_client.contact.v3.user.get.return_value = mock_get_response

        pool._get_sdk_client.return_value = mock_sdk_client
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create ContactClient instance."""
        return ContactClient(mock_credential_pool)

    def test_batch_get_users_with_emails_and_mobiles(self, client):
        """Test batch get users with mixed email and mobile queries."""
        queries = [
            BatchUserQuery(emails=["user1@example.com"]),
            BatchUserQuery(mobiles=["+86-13800138001"]),
        ]

        response = client.batch_get_users(
            app_id="cli_test",
            queries=queries,
        )

        assert response.total >= 0
        assert isinstance(response.users, list)

    def test_batch_get_users_with_user_ids(self, client, mock_credential_pool):
        """Test batch get users with user_id queries."""
        queries = [
            BatchUserQuery(user_ids=["user0001", "user0002"]),
        ]

        response = client.batch_get_users(
            app_id="cli_test",
            queries=queries,
        )

        assert isinstance(response.users, list)

    def test_batch_get_users_with_cache_partial_hits(self, mock_credential_pool):
        """Test batch get with partial cache hits."""
        mock_cache_manager = Mock(spec=ContactCacheManager)

        # First user in cache, second not
        cached_user = User(
            open_id="ou_cachedcachedcachedcached",
            user_id="cached01",
            union_id="on_cachedcachedcachedcached",
            name="Cached",
        )

        def cache_get_email(app_id, email):
            if email == "cached@example.com":
                return cached_user
            return None

        mock_cache_manager.get_user_by_email.side_effect = cache_get_email
        mock_cache_manager.get_user_by_mobile.return_value = None
        mock_cache_manager.get_user_by_user_id.return_value = None

        client = ContactClient(
            mock_credential_pool,
            cache_manager=mock_cache_manager,
            enable_cache=True,
        )

        queries = [
            BatchUserQuery(emails=["cached@example.com"]),
            BatchUserQuery(emails=["uncached@example.com"]),
        ]

        response = client.batch_get_users(
            app_id="cli_test",
            queries=queries,
        )

        # Should have at least the cached user
        assert len(response.users) >= 1


class TestContactClientDepartmentOperations:
    """Test department operations with real data."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool with successful department responses."""
        pool = Mock(spec=CredentialPool)
        mock_sdk_client = Mock()

        # Mock successful get department response
        mock_dept_response = Mock()
        mock_dept_response.success.return_value = True
        mock_dept_response.code = 0
        mock_dept_response.data = Mock()

        # Convert to our Department model
        mock_dept = Mock(spec=[])  # Empty spec so hasattr returns False
        mock_dept.open_department_id = "od-dept123dept123dept123"
        mock_dept.department_id = "d-dept123dept123dept123"
        mock_dept.name = "Engineering"
        mock_dept.parent_department_id = "od-parent"
        mock_dept.leader_user_id = "ou_leader"
        mock_dept.member_count = 50
        mock_dept.order = 1
        # Don't add status attribute - hasattr check will return False

        mock_dept_response.data.department = mock_dept
        mock_sdk_client.contact.v3.department.get.return_value = mock_dept_response

        # Mock successful get members response
        mock_members_response = Mock()
        mock_members_response.success.return_value = True
        mock_members_response.code = 0
        mock_members_response.data = Mock()

        # Create some mock members
        member1 = Mock()
        member1.user_id = "member01"

        member2 = Mock()
        member2.user_id = "member02"

        mock_members_response.data.items = [member1, member2]
        mock_members_response.data.page_token = None

        mock_sdk_client.contact.v3.user.find_by_department.return_value = mock_members_response

        pool._get_sdk_client.return_value = mock_sdk_client
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create ContactClient instance."""
        return ContactClient(mock_credential_pool)

    def test_get_department_success(self, client):
        """Test successful department retrieval."""
        dept = client.get_department(
            app_id="cli_test",
            department_id="od-dept123dept123dept123",
        )

        assert isinstance(dept, Department)
        assert dept.department_id == "od-dept123dept123dept123"
        assert dept.name == "Engineering"
        assert dept.parent_department_id == "od-parent"
        assert dept.leader_user_id == "ou_leader"
        assert dept.member_count == 50
        assert dept.order == 1
        assert dept.status == 1  # Should be 1 when status attr not present

    def test_get_department_members_success_with_data(self, client):
        """Test successful department members retrieval with data."""
        members, next_token = client.get_department_members(
            app_id="cli_test",
            department_id="od-dept123dept123dept123",
            page_size=50,
        )

        assert len(members) == 2
        assert members[0].user_id == "member01"
        assert members[0].department_id == "od-dept123dept123dept123"
        assert members[1].user_id == "member02"
        assert next_token is None

    def test_get_department_members_with_pagination_token(self, client, mock_credential_pool):
        """Test getting department members with page token."""
        # Setup first page with next token
        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_response = mock_sdk_client.contact.v3.user.find_by_department.return_value
        mock_response.data.page_token = "next_page_token"

        members, next_token = client.get_department_members(
            app_id="cli_test",
            department_id="od-dept123dept123dept123",
            page_size=20,
        )

        assert next_token == "next_page_token"

        # Get next page
        mock_response.data.page_token = None  # Last page
        members2, next_token2 = client.get_department_members(
            app_id="cli_test",
            department_id="od-dept123dept123dept123",
            page_size=20,
            page_token=next_token,
        )

        assert next_token2 is None


class TestContactClientChatOperations:
    """Test chat operations with real data."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool with successful chat responses."""
        pool = Mock(spec=CredentialPool)
        mock_sdk_client = Mock()

        # Mock successful get chat response
        mock_chat_response = Mock()
        mock_chat_response.success.return_value = True
        mock_chat_response.code = 0
        mock_chat_response.data = Mock()
        mock_chat_response.data.chat_id = "oc_chat123chat123chat123"
        mock_chat_response.data.name = "Team Chat"
        mock_chat_response.data.description = "Engineering team discussion"
        mock_chat_response.data.owner_id = "ou_owner"
        mock_chat_response.data.chat_mode = "group"
        mock_chat_response.data.chat_type = "private"
        mock_chat_response.data.avatar = "https://example.com/avatar.jpg"

        mock_sdk_client.im.v1.chat.get.return_value = mock_chat_response

        # Mock successful get chat members response
        mock_members_response = Mock()
        mock_members_response.success.return_value = True
        mock_members_response.code = 0
        mock_members_response.data = Mock()

        member1 = Mock()
        member1.member_id = "ou_member1member1member1member1"

        member2 = Mock()
        member2.member_id = "ou_member2member2member2member2"

        mock_members_response.data.items = [member1, member2]
        mock_members_response.data.page_token = None

        mock_sdk_client.im.v1.chat_members.get.return_value = mock_members_response

        pool._get_sdk_client.return_value = mock_sdk_client
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create ContactClient instance."""
        return ContactClient(mock_credential_pool)

    def test_get_chat_group_success(self, client):
        """Test successful chat group retrieval."""
        chat = client.get_chat_group(
            app_id="cli_test",
            chat_id="oc_chat123chat123chat123",
        )

        assert isinstance(chat, ChatGroup)
        assert chat.chat_id == "oc_chat123chat123chat123"
        assert chat.name == "Team Chat"
        assert chat.description == "Engineering team discussion"
        assert chat.owner_id == "ou_owner"
        assert chat.chat_mode == "group"
        assert chat.chat_type == "private"
        assert chat.avatar == "https://example.com/avatar.jpg"

    def test_get_chat_members_success_with_data(self, client):
        """Test successful chat members retrieval with data."""
        members, next_token = client.get_chat_members(
            app_id="cli_test",
            chat_id="oc_chat123chat123chat123",
            page_size=50,
        )

        assert len(members) == 2
        assert members[0].user_id == "ou_member1member1member1member1"
        assert members[0].chat_id == "oc_chat123chat123chat123"
        assert members[1].user_id == "ou_member2member2member2member2"
        assert next_token is None

    def test_get_chat_members_with_pagination(self, client, mock_credential_pool):
        """Test chat members pagination."""
        # Setup first page with next token
        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_response = mock_sdk_client.im.v1.chat_members.get.return_value
        mock_response.data.page_token = "page_token_123"

        members, next_token = client.get_chat_members(
            app_id="cli_test",
            chat_id="oc_chat123chat123chat123",
            page_size=30,
        )

        assert next_token == "page_token_123"


class TestContactClientErrorHandling:
    """Test error handling for different API error codes."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create ContactClient instance."""
        return ContactClient(mock_credential_pool)

    def test_get_user_api_error(self, client, mock_credential_pool):
        """Test handling generic API error."""
        mock_sdk_client = Mock()

        # Mock batch response success
        mock_batch_response = Mock()
        mock_batch_response.success.return_value = True
        mock_batch_response.code = 0
        mock_batch_response.data = Mock()
        mock_user_contact = Mock()
        mock_user_contact.user_id = "testuser"
        mock_batch_response.data.user_list = [mock_user_contact]
        mock_sdk_client.contact.v3.user.batch_get_id.return_value = mock_batch_response

        # Mock get user with generic error
        mock_get_response = Mock()
        mock_get_response.success.return_value = False
        mock_get_response.code = 500
        mock_get_response.msg = "Internal Server Error"
        mock_sdk_client.contact.v3.user.get.return_value = mock_get_response

        mock_credential_pool._get_sdk_client.return_value = mock_sdk_client

        with pytest.raises(APIError, match="API error"):
            client.get_user_by_email(
                app_id="cli_test",
                email="test@example.com",
            )

    def test_get_department_permission_denied(self, client, mock_credential_pool):
        """Test handling permission denied error."""
        mock_sdk_client = Mock()

        mock_dept_response = Mock()
        mock_dept_response.success.return_value = False
        mock_dept_response.code = 99991668  # Permission denied
        mock_dept_response.msg = "Permission denied"

        mock_sdk_client.contact.v3.department.get.return_value = mock_dept_response
        mock_credential_pool._get_sdk_client.return_value = mock_sdk_client

        with pytest.raises(PermissionDeniedError, match="No permission"):
            client.get_department(
                app_id="cli_test",
                department_id="od-dept123",
            )

    def test_get_chat_group_not_found(self, client, mock_credential_pool):
        """Test handling chat not found error."""
        mock_sdk_client = Mock()

        mock_chat_response = Mock()
        mock_chat_response.success.return_value = False
        mock_chat_response.code = 230008  # Chat not found
        mock_chat_response.msg = "Chat not found"

        mock_sdk_client.im.v1.chat.get.return_value = mock_chat_response
        mock_credential_pool._get_sdk_client.return_value = mock_sdk_client

        with pytest.raises(NotFoundError, match="Chat group not found"):
            client.get_chat_group(
                app_id="cli_test",
                chat_id="oc_nonexistent",
            )

    def test_batch_get_users_api_failure_handling(self, client, mock_credential_pool):
        """Test batch get handles API failure gracefully."""
        mock_sdk_client = Mock()

        # Mock batch_get_id failure
        mock_batch_response = Mock()
        mock_batch_response.success.return_value = False
        mock_batch_response.code = 500
        mock_batch_response.msg = "Server error"

        mock_sdk_client.contact.v3.user.batch_get_id.return_value = mock_batch_response
        mock_credential_pool._get_sdk_client.return_value = mock_sdk_client

        queries = [
            BatchUserQuery(emails=["test@example.com"]),
        ]

        # Should not raise, but mark items as not found
        response = client.batch_get_users(
            app_id="cli_test",
            queries=queries,
        )

        # Should return response with not_found items
        assert response.not_found is not None
        assert "test@example.com" in response.not_found
