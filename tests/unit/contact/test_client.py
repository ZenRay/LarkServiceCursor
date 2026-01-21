"""
Unit tests for ContactClient.

Tests user queries, department queries, chat queries, and batch operations.
"""

from unittest.mock import Mock

import pytest

from lark_service.contact.client import ContactClient
from lark_service.contact.models import BatchUserQuery, BatchUserResponse
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError, NotFoundError


class TestContactClientValidation:
    """Test ContactClient validation logic."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create ContactClient instance."""
        return ContactClient(mock_credential_pool)

    def test_get_user_by_email_invalid(self, client):
        """Test get user by email fails with invalid email."""
        # Test empty email
        with pytest.raises(InvalidParameterError, match="Invalid email"):
            client.get_user_by_email(
                app_id="cli_test1234567890ab",
                email="",
            )

        # Test email without @
        with pytest.raises(InvalidParameterError, match="Invalid email"):
            client.get_user_by_email(
                app_id="cli_test1234567890ab",
                email="invalid_email",
            )

    def test_get_user_by_mobile_empty(self, client):
        """Test get user by mobile fails with empty mobile."""
        with pytest.raises(InvalidParameterError, match="Mobile cannot be empty"):
            client.get_user_by_mobile(
                app_id="cli_test1234567890ab",
                mobile="",
            )

    def test_get_user_by_user_id_empty(self, client):
        """Test get user by user_id fails with empty user_id."""
        with pytest.raises(InvalidParameterError, match="User ID cannot be empty"):
            client.get_user_by_user_id(
                app_id="cli_test1234567890ab",
                user_id="",
            )

    def test_batch_get_users_empty(self, client):
        """Test batch get users fails with empty queries."""
        with pytest.raises(InvalidParameterError, match="Queries cannot be empty"):
            client.batch_get_users(
                app_id="cli_test1234567890ab",
                queries=[],
            )

    def test_batch_get_users_too_many(self, client):
        """Test batch get users fails with more than 50 queries."""
        queries = [BatchUserQuery(email=f"user{i}@example.com") for i in range(51)]
        with pytest.raises(InvalidParameterError, match="Too many queries"):
            client.batch_get_users(
                app_id="cli_test1234567890ab",
                queries=queries,
            )

    def test_get_department_empty_id(self, client):
        """Test get department fails with empty department_id."""
        with pytest.raises(InvalidParameterError, match="Department ID cannot be empty"):
            client.get_department(
                app_id="cli_test1234567890ab",
                department_id="",
            )

    def test_get_department_members_empty_id(self, client):
        """Test get department members fails with empty department_id."""
        with pytest.raises(InvalidParameterError, match="Department ID cannot be empty"):
            client.get_department_members(
                app_id="cli_test1234567890ab",
                department_id="",
            )

    def test_get_department_members_invalid_page_size(self, client):
        """Test get department members fails with invalid page size."""
        # Test page_size < 1
        with pytest.raises(InvalidParameterError, match="Invalid page_size"):
            client.get_department_members(
                app_id="cli_test1234567890ab",
                department_id="od-xxx",
                page_size=0,
            )

        # Test page_size > 100
        with pytest.raises(InvalidParameterError, match="Invalid page_size"):
            client.get_department_members(
                app_id="cli_test1234567890ab",
                department_id="od-xxx",
                page_size=101,
            )

    def test_get_chat_group_empty_id(self, client):
        """Test get chat group fails with empty chat_id."""
        with pytest.raises(InvalidParameterError, match="Chat ID cannot be empty"):
            client.get_chat_group(
                app_id="cli_test1234567890ab",
                chat_id="",
            )

    def test_get_chat_members_empty_id(self, client):
        """Test get chat members fails with empty chat_id."""
        with pytest.raises(InvalidParameterError, match="Chat ID cannot be empty"):
            client.get_chat_members(
                app_id="cli_test1234567890ab",
                chat_id="",
            )

    def test_get_chat_members_invalid_page_size(self, client):
        """Test get chat members fails with invalid page size."""
        # Test page_size < 1
        with pytest.raises(InvalidParameterError, match="Invalid page_size"):
            client.get_chat_members(
                app_id="cli_test1234567890ab",
                chat_id="oc_xxx",
                page_size=0,
            )

        # Test page_size > 100
        with pytest.raises(InvalidParameterError, match="Invalid page_size"):
            client.get_chat_members(
                app_id="cli_test1234567890ab",
                chat_id="oc_xxx",
                page_size=101,
            )


class TestContactClientUserQueries:
    """Test ContactClient user query operations."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)

        # Mock SDK client
        mock_sdk_client = Mock()

        # Mock batch_get_id response (empty user list = not found)
        mock_batch_response = Mock()
        mock_batch_response.code = 0
        mock_batch_response.data = Mock()
        mock_batch_response.data.user_list = []

        mock_sdk_client.contact.v3.user.batch_get_id.return_value = mock_batch_response

        # Mock get user response (not found)
        mock_get_response = Mock()
        mock_get_response.code = 99991663  # User not found
        mock_get_response.msg = "User not found"
        mock_get_response.success.return_value = False  # Important: mark as failed

        mock_sdk_client.contact.v3.user.get.return_value = mock_get_response

        pool._get_sdk_client.return_value = mock_sdk_client
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create ContactClient instance."""
        return ContactClient(mock_credential_pool)

    def test_get_user_by_email_not_found(self, client):
        """Test get user by email raises NotFoundError when user not found."""
        with pytest.raises(NotFoundError, match="User not found"):
            client.get_user_by_email(
                app_id="cli_test1234567890ab",
                email="nonexistent@example.com",
            )

    def test_get_user_by_mobile_not_found(self, client):
        """Test get user by mobile raises NotFoundError when user not found."""
        with pytest.raises(NotFoundError, match="User not found"):
            client.get_user_by_mobile(
                app_id="cli_test1234567890ab",
                mobile="+86-13800138000",
            )

    def test_get_user_by_user_id_not_found(self, client):
        """Test get user by user_id raises NotFoundError when user not found."""
        with pytest.raises(NotFoundError, match="User not found"):
            client.get_user_by_user_id(
                app_id="cli_test1234567890ab",
                user_id="nonexistent_id",
            )

    def test_batch_get_users_success(self, client, mock_credential_pool):
        """Test batch get users succeeds."""
        # Mock batch_get_id response with empty results
        mock_batch_response = Mock()
        mock_batch_response.code = 0
        mock_batch_response.data = Mock()
        mock_batch_response.data.user_list = []

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.contact.v3.user.batch_get_id.return_value = mock_batch_response

        queries = [
            BatchUserQuery(email="user1@example.com"),
            BatchUserQuery(mobile="+86-13800138000"),
            BatchUserQuery(user_id="4d7a3c6g"),
        ]

        response = client.batch_get_users(
            app_id="cli_test1234567890ab",
            queries=queries,
        )

        assert isinstance(response, BatchUserResponse)
        assert isinstance(response.users, list)
        assert response.total == 0

    def test_batch_get_users_max_limit(self, client):
        """Test batch get users with maximum 50 queries."""
        queries = [BatchUserQuery(email=f"user{i}@example.com") for i in range(50)]

        response = client.batch_get_users(
            app_id="cli_test1234567890ab",
            queries=queries,
        )

        assert isinstance(response, BatchUserResponse)


class TestContactClientDepartmentQueries:
    """Test ContactClient department query operations."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)

        # Mock SDK client
        mock_sdk_client = Mock()

        # Mock get department response (not found)
        mock_dept_response = Mock()
        mock_dept_response.code = 230002  # Department not found (correct code)
        mock_dept_response.msg = "Department not found"
        mock_dept_response.success.return_value = False  # Mark as failed

        mock_sdk_client.contact.v3.department.get.return_value = mock_dept_response

        # Mock get department members response (empty list)
        mock_members_response = Mock()
        mock_members_response.code = 0
        mock_members_response.success.return_value = True  # Mark as success
        mock_members_response.data = Mock()
        mock_members_response.data.items = []  # Empty list
        mock_members_response.data.has_more = False
        mock_members_response.data.page_token = None

        # Use correct API: find_by_department, not children
        mock_sdk_client.contact.v3.user.find_by_department.return_value = mock_members_response

        pool._get_sdk_client.return_value = mock_sdk_client
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create ContactClient instance."""
        return ContactClient(mock_credential_pool)

    def test_get_department_not_found(self, client):
        """Test get department raises NotFoundError when department not found."""
        with pytest.raises(NotFoundError, match="Department not found"):
            client.get_department(
                app_id="cli_test1234567890ab",
                department_id="od-nonexistent",
            )

    def test_get_department_members_success(self, client, mock_credential_pool):
        """Test get department members succeeds."""
        # Mock successful response with empty list
        mock_response = Mock()
        mock_response.code = 0
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.items = []
        mock_response.data.has_more = False
        mock_response.data.page_token = None

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.contact.v3.user.find_by_department.return_value = mock_response

        members, next_token = client.get_department_members(
            app_id="cli_test1234567890ab",
            department_id="od-xxx",
            page_size=50,
        )

        assert isinstance(members, list)
        assert next_token is None

    def test_get_department_members_pagination(self, client, mock_credential_pool):
        """Test get department members with pagination."""
        # Mock first page response
        mock_response1 = Mock()
        mock_response1.code = 0
        mock_response1.success.return_value = True
        mock_response1.data = Mock()
        mock_response1.data.items = []
        mock_response1.data.has_more = False
        mock_response1.data.page_token = None

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.contact.v3.user.find_by_department.return_value = mock_response1

        # First page
        members, next_token = client.get_department_members(
            app_id="cli_test1234567890ab",
            department_id="od-xxx",
            page_size=20,
        )

        assert isinstance(members, list)

        # Second page (if next_token exists)
        if next_token:
            members2, next_token2 = client.get_department_members(
                app_id="cli_test1234567890ab",
                department_id="od-xxx",
                page_size=20,
                page_token=next_token,
            )
            assert isinstance(members2, list)


class TestContactClientChatQueries:
    """Test ContactClient chat query operations."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)

        # Mock SDK client
        mock_sdk_client = Mock()

        # Mock get chat response (not found)
        mock_chat_response = Mock()
        mock_chat_response.code = 230008  # Chat not found (correct code)
        mock_chat_response.msg = "Chat group not found"
        mock_chat_response.success.return_value = False  # Mark as failed

        mock_sdk_client.im.v1.chat.get.return_value = mock_chat_response

        # Mock get chat members response (empty list)
        mock_members_response = Mock()
        mock_members_response.code = 0
        mock_members_response.data = Mock()
        mock_members_response.data.items = []
        mock_members_response.data.has_more = False
        mock_members_response.data.page_token = None

        mock_sdk_client.im.v1.chat_members.get.return_value = mock_members_response

        pool._get_sdk_client.return_value = mock_sdk_client
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create ContactClient instance."""
        return ContactClient(mock_credential_pool)

    def test_get_chat_group_not_found(self, client):
        """Test get chat group raises NotFoundError when group not found."""
        with pytest.raises(NotFoundError, match="Chat group not found"):
            client.get_chat_group(
                app_id="cli_test1234567890ab",
                chat_id="oc-nonexistent",
            )

    def test_get_chat_members_success(self, client, mock_credential_pool):
        """Test get chat members succeeds."""
        # Mock successful response with empty list
        mock_response = Mock()
        mock_response.code = 0
        mock_response.data = Mock()
        mock_response.data.items = []
        mock_response.data.has_more = False
        mock_response.data.page_token = None

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.im.v1.chat_members.get.return_value = mock_response

        members, next_token = client.get_chat_members(
            app_id="cli_test1234567890ab",
            chat_id="oc_xxx",
            page_size=50,
        )

        assert isinstance(members, list)
        assert next_token is None

    def test_get_chat_members_pagination(self, client, mock_credential_pool):
        """Test get chat members with pagination."""
        # Mock first page response
        mock_response1 = Mock()
        mock_response1.code = 0
        mock_response1.data = Mock()
        mock_response1.data.items = []
        mock_response1.data.has_more = False
        mock_response1.data.page_token = None

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.im.v1.chat_members.get.return_value = mock_response1

        # First page
        members, next_token = client.get_chat_members(
            app_id="cli_test1234567890ab",
            chat_id="oc_xxx",
            page_size=30,
        )

        assert isinstance(members, list)

        # Second page (if next_token exists)
        if next_token:
            members2, next_token2 = client.get_chat_members(
                app_id="cli_test1234567890ab",
                chat_id="oc_xxx",
                page_size=30,
                page_token=next_token,
            )
            assert isinstance(members2, list)

    def test_get_chat_members_max_page_size(self, client, mock_credential_pool):
        """Test get chat members with maximum page size."""
        # Mock successful response
        mock_response = Mock()
        mock_response.code = 0
        mock_response.data = Mock()
        mock_response.data.items = []
        mock_response.data.has_more = False
        mock_response.data.page_token = None

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.im.v1.chat_members.get.return_value = mock_response

        members, _ = client.get_chat_members(
            app_id="cli_test1234567890ab",
            chat_id="oc_xxx",
            page_size=100,
        )

        assert isinstance(members, list)
