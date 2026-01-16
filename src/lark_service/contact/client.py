"""
Contact client for Lark Contact API.

This module provides a high-level client for contact query operations
via Lark Contact API, including user queries, department queries, and chat group queries.
"""

from lark_service.contact.models import (
    BatchUserQuery,
    BatchUserResponse,
    ChatGroup,
    ChatMember,
    Department,
    DepartmentUser,
    User,
)
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError, NotFoundError
from lark_service.core.retry import RetryStrategy
from lark_service.utils.logger import get_logger

logger = get_logger()


class ContactClient:
    """
    High-level client for Lark Contact operations.

    Provides convenient methods for querying users, departments, and chat groups
    via Lark Contact API, with automatic error handling and retry.

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        retry_strategy : RetryStrategy
            Retry strategy for API calls

    Examples
    --------
        >>> client = ContactClient(credential_pool)
        >>> user = client.get_user_by_email(
        ...     app_id="cli_xxx",
        ...     email="user@example.com"
        ... )
        >>> print(user.name)
    """

    def __init__(
        self,
        credential_pool: CredentialPool,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        """
        Initialize ContactClient.

        Parameters
        ----------
            credential_pool : CredentialPool
                Credential pool for token management
            retry_strategy : RetryStrategy | None
                Retry strategy (default: creates new instance)
        """
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()

    def get_user_by_email(
        self,
        app_id: str,
        email: str,
    ) -> User:
        """
        Get user information by email.

        Parameters
        ----------
            app_id : str
                Lark application ID
            email : str
                User email address

        Returns
        -------
            User
                User information

        Raises
        ------
            InvalidParameterError
                If email is invalid
            NotFoundError
                If user not found

        Examples
        --------
            >>> user = client.get_user_by_email(
            ...     app_id="cli_xxx",
            ...     email="user@example.com"
            ... )
            >>> print(f"{user.name} ({user.open_id})")
        """
        if not email or "@" not in email:
            raise InvalidParameterError(f"Invalid email: {email}")

        logger.info(f"Getting user by email: {email}")

        def _get() -> User:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            # Should also check cache first
            raise NotFoundError(f"User not found: {email}")

        return self.retry_strategy.execute(_get)

    def get_user_by_mobile(
        self,
        app_id: str,
        mobile: str,
    ) -> User:
        """
        Get user information by mobile number.

        Parameters
        ----------
            app_id : str
                Lark application ID
            mobile : str
                User mobile number (with country code, e.g., +86-13800138000)

        Returns
        -------
            User
                User information

        Raises
        ------
            InvalidParameterError
                If mobile is invalid
            NotFoundError
                If user not found

        Examples
        --------
            >>> user = client.get_user_by_mobile(
            ...     app_id="cli_xxx",
            ...     mobile="+86-13800138000"
            ... )
            >>> print(f"{user.name} ({user.open_id})")
        """
        if not mobile:
            raise InvalidParameterError("Mobile cannot be empty")

        logger.info(f"Getting user by mobile: {mobile}")

        def _get() -> User:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            # Should also check cache first
            raise NotFoundError(f"User not found: {mobile}")

        return self.retry_strategy.execute(_get)

    def get_user_by_user_id(
        self,
        app_id: str,
        user_id: str,
    ) -> User:
        """
        Get user information by user_id.

        Parameters
        ----------
            app_id : str
                Lark application ID
            user_id : str
                User ID (tenant-scoped)

        Returns
        -------
            User
                User information

        Raises
        ------
            InvalidParameterError
                If user_id is invalid
            NotFoundError
                If user not found

        Examples
        --------
            >>> user = client.get_user_by_user_id(
            ...     app_id="cli_xxx",
            ...     user_id="4d7a3c6g"
            ... )
            >>> print(f"{user.name} ({user.open_id})")
        """
        if not user_id:
            raise InvalidParameterError("User ID cannot be empty")

        logger.info(f"Getting user by user_id: {user_id}")

        def _get() -> User:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            # Should also check cache first
            raise NotFoundError(f"User not found: {user_id}")

        return self.retry_strategy.execute(_get)

    def batch_get_users(
        self,
        app_id: str,
        queries: list[BatchUserQuery],
    ) -> BatchUserResponse:
        """
        Batch get users by email, mobile, or user_id.

        Parameters
        ----------
            app_id : str
                Lark application ID
            queries : list[BatchUserQuery]
                List of query conditions (max 50)

        Returns
        -------
            BatchUserResponse
                Batch query response with found users and not found queries

        Raises
        ------
            InvalidParameterError
                If queries are invalid

        Examples
        --------
            >>> queries = [
            ...     BatchUserQuery(email="user1@example.com"),
            ...     BatchUserQuery(mobile="+86-13800138000"),
            ...     BatchUserQuery(user_id="4d7a3c6g")
            ... ]
            >>> response = client.batch_get_users(
            ...     app_id="cli_xxx",
            ...     queries=queries
            ... )
            >>> print(f"Found {response.total} users")
            >>> if response.not_found:
            ...     print(f"Not found: {response.not_found}")
        """
        if not queries:
            raise InvalidParameterError("Queries cannot be empty")

        if len(queries) > 50:
            raise InvalidParameterError(f"Too many queries: {len(queries)} (max 50)")

        logger.info(f"Batch getting {len(queries)} users")

        def _batch_get() -> BatchUserResponse:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            # Should also check cache first
            return BatchUserResponse(
                users=[],
                not_found=[],
                total=0,
            )

        return self.retry_strategy.execute(_batch_get)

    def get_department(
        self,
        app_id: str,
        department_id: str,
    ) -> Department:
        """
        Get department information.

        Parameters
        ----------
            app_id : str
                Lark application ID
            department_id : str
                Department ID (open_department_id)

        Returns
        -------
            Department
                Department information

        Raises
        ------
            InvalidParameterError
                If department_id is invalid
            NotFoundError
                If department not found

        Examples
        --------
            >>> dept = client.get_department(
            ...     app_id="cli_xxx",
            ...     department_id="od-xxx"
            ... )
            >>> print(f"{dept.name} (members: {dept.member_count})")
        """
        if not department_id:
            raise InvalidParameterError("Department ID cannot be empty")

        logger.info(f"Getting department: {department_id}")

        def _get() -> Department:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            raise NotFoundError(f"Department not found: {department_id}")

        return self.retry_strategy.execute(_get)

    def get_department_members(
        self,
        app_id: str,
        department_id: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> tuple[list[DepartmentUser], str | None]:
        """
        Get department members with pagination.

        Parameters
        ----------
            app_id : str
                Lark application ID
            department_id : str
                Department ID (open_department_id)
            page_size : int
                Page size (default: 50, max: 100)
            page_token : str | None
                Page token for pagination

        Returns
        -------
            tuple[list[DepartmentUser], str | None]
                (members, next_page_token)

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If department not found

        Examples
        --------
            >>> members, next_token = client.get_department_members(
            ...     app_id="cli_xxx",
            ...     department_id="od-xxx",
            ...     page_size=20
            ... )
            >>> for member in members:
            ...     print(f"{member.name} - {member.job_title}")
        """
        if not department_id:
            raise InvalidParameterError("Department ID cannot be empty")

        if page_size < 1 or page_size > 100:
            raise InvalidParameterError(f"Invalid page_size: {page_size} (1-100)")

        logger.info(f"Getting members of department {department_id}, page_size={page_size}")

        def _get_members() -> tuple[list[DepartmentUser], str | None]:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return [], None

        return self.retry_strategy.execute(_get_members)

    def get_chat_group(
        self,
        app_id: str,
        chat_id: str,
    ) -> ChatGroup:
        """
        Get chat group information.

        Parameters
        ----------
            app_id : str
                Lark application ID
            chat_id : str
                Chat ID

        Returns
        -------
            ChatGroup
                Chat group information

        Raises
        ------
            InvalidParameterError
                If chat_id is invalid
            NotFoundError
                If chat group not found

        Examples
        --------
            >>> group = client.get_chat_group(
            ...     app_id="cli_xxx",
            ...     chat_id="oc_xxx"
            ... )
            >>> print(f"{group.name} (members: {group.member_count})")
        """
        if not chat_id:
            raise InvalidParameterError("Chat ID cannot be empty")

        logger.info(f"Getting chat group: {chat_id}")

        def _get() -> ChatGroup:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            raise NotFoundError(f"Chat group not found: {chat_id}")

        return self.retry_strategy.execute(_get)

    def get_chat_members(
        self,
        app_id: str,
        chat_id: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> tuple[list[ChatMember], str | None]:
        """
        Get chat group members with pagination.

        Parameters
        ----------
            app_id : str
                Lark application ID
            chat_id : str
                Chat ID
            page_size : int
                Page size (default: 50, max: 100)
            page_token : str | None
                Page token for pagination

        Returns
        -------
            tuple[list[ChatMember], str | None]
                (members, next_page_token)

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If chat group not found

        Examples
        --------
            >>> members, next_token = client.get_chat_members(
            ...     app_id="cli_xxx",
            ...     chat_id="oc_xxx",
            ...     page_size=20
            ... )
            >>> for member in members:
            ...     print(f"{member.name} ({member.member_role})")
        """
        if not chat_id:
            raise InvalidParameterError("Chat ID cannot be empty")

        if page_size < 1 or page_size > 100:
            raise InvalidParameterError(f"Invalid page_size: {page_size} (1-100)")

        logger.info(f"Getting members of chat {chat_id}, page_size={page_size}")

        def _get_members() -> tuple[list[ChatMember], str | None]:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return [], None

        return self.retry_strategy.execute(_get_members)
