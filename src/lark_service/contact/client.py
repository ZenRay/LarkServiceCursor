"""
Contact client for Lark Contact API.

This module provides a high-level client for contact query operations
via Lark Contact API, including user queries, department queries, and chat group queries.
"""

from datetime import timedelta

from lark_service.contact.cache import ContactCacheManager
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
    via Lark Contact API, with automatic error handling, retry, and optional caching.

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        retry_strategy : RetryStrategy
            Retry strategy for API calls
        cache_manager : ContactCacheManager | None
            Cache manager for user information (optional)
        enable_cache : bool
            Whether caching is enabled

    Examples
    --------
        >>> # Without cache
        >>> client = ContactClient(credential_pool)

        >>> # With cache (recommended for production)
        >>> cache_manager = ContactCacheManager(db_url="postgresql://...")
        >>> client = ContactClient(
        ...     credential_pool,
        ...     cache_manager=cache_manager,
        ...     enable_cache=True
        ... )
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
        cache_manager: ContactCacheManager | None = None,
        enable_cache: bool = False,
        cache_ttl: timedelta | None = None,
    ) -> None:
        """
        Initialize ContactClient.

        Parameters
        ----------
            credential_pool : CredentialPool
                Credential pool for token management
            retry_strategy : RetryStrategy | None
                Retry strategy (default: creates new instance)
            cache_manager : ContactCacheManager | None
                Cache manager for user information (optional)
            enable_cache : bool
                Whether to enable caching (default: False)
            cache_ttl : timedelta | None
                Cache TTL (default: 24 hours if not specified)

        Notes
        -----
            - If enable_cache=True but cache_manager is None, caching will be disabled
            - Cache is app_id isolated (different apps have different open_ids)
            - Cache uses union_id as primary key (consistent across apps)
        """
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()
        self.cache_manager = cache_manager
        self.enable_cache = enable_cache and cache_manager is not None
        self.cache_ttl = cache_ttl or timedelta(hours=24)

        if enable_cache and cache_manager is None:
            logger.warning(
                "Cache is enabled but cache_manager is None. "
                "Caching will be disabled. Please provide a ContactCacheManager instance."
            )

    def get_user_by_email(
        self,
        app_id: str,
        email: str,
    ) -> User:
        """
        Get user information by email.

        If caching is enabled, checks cache first before making API call.
        Cache is keyed by (app_id, email) and uses union_id for consistency.

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

        # Check cache first if enabled
        if self.enable_cache and self.cache_manager:
            cached_user = self.cache_manager.get_user_by_email(app_id, email)
            if cached_user:
                logger.debug(f"Cache hit for user email: {email}")
                return cached_user
            logger.debug(f"Cache miss for user email: {email}")

        logger.info(f"Getting user by email from API: {email}")

        def _get() -> User:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder for now

            # TODO: Implement actual API call when SDK supports it
            # For now, raise NotFoundError to maintain existing behavior
            raise NotFoundError(f"User not found: {email}")

        user = self.retry_strategy.execute(_get)

        # Store in cache if enabled
        if self.enable_cache and self.cache_manager:
            self.cache_manager.cache_user(app_id, user)
            logger.debug(f"Cached user: {user.union_id}")

        return user

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

        # Check cache first if enabled
        if self.enable_cache and self.cache_manager:
            cached_user = self.cache_manager.get_user_by_mobile(app_id, mobile)
            if cached_user:
                logger.debug(f"Cache hit for user mobile: {mobile}")
                return cached_user
            logger.debug(f"Cache miss for user mobile: {mobile}")

        logger.info(f"Getting user by mobile from API: {mobile}")

        def _get() -> User:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder for now

            # TODO: Implement actual API call when SDK supports it
            raise NotFoundError(f"User not found: {mobile}")

        user = self.retry_strategy.execute(_get)

        # Store in cache if enabled
        if self.enable_cache and self.cache_manager:
            self.cache_manager.cache_user(app_id, user)
            logger.debug(f"Cached user: {user.union_id}")

        return user

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

        # Check cache first if enabled
        if self.enable_cache and self.cache_manager:
            cached_user = self.cache_manager.get_user_by_user_id(app_id, user_id)
            if cached_user:
                logger.debug(f"Cache hit for user_id: {user_id}")
                return cached_user
            logger.debug(f"Cache miss for user_id: {user_id}")

        logger.info(f"Getting user by user_id from API: {user_id}")

        def _get() -> User:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder for now

            # TODO: Implement actual API call when SDK supports it
            raise NotFoundError(f"User not found: {user_id}")

        user = self.retry_strategy.execute(_get)

        # Store in cache if enabled
        if self.enable_cache and self.cache_manager:
            self.cache_manager.cache_user(app_id, user)
            logger.debug(f"Cached user: {user.union_id}")

        return user

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

        # Check cache first if enabled
        found_users: list[User] = []
        remaining_queries: list[BatchUserQuery] = []
        not_found_identifiers: list[str] = []

        if self.enable_cache and self.cache_manager:
            for query in queries:
                # Try to find users from cache for each identifier in the query
                query_found = False

                if query.emails:
                    for email in query.emails:
                        cached_user = self.cache_manager.get_user_by_email(app_id, email)
                        if cached_user:
                            found_users.append(cached_user)
                            query_found = True
                            logger.debug(f"Cache hit for email: {email}")
                        else:
                            not_found_identifiers.append(email)

                if query.mobiles:
                    for mobile in query.mobiles:
                        cached_user = self.cache_manager.get_user_by_mobile(app_id, mobile)
                        if cached_user:
                            found_users.append(cached_user)
                            query_found = True
                            logger.debug(f"Cache hit for mobile: {mobile}")
                        else:
                            not_found_identifiers.append(mobile)

                if query.user_ids:
                    for user_id in query.user_ids:
                        cached_user = self.cache_manager.get_user_by_user_id(app_id, user_id)
                        if cached_user:
                            found_users.append(cached_user)
                            query_found = True
                            logger.debug(f"Cache hit for user_id: {user_id}")
                        else:
                            not_found_identifiers.append(user_id)

                if not query_found:
                    remaining_queries.append(query)
        else:
            remaining_queries = queries

        # If all queries were satisfied by cache, return immediately
        if not remaining_queries:
            logger.info(f"All {len(queries)} users found in cache")
            return BatchUserResponse(
                users=found_users,
                not_found=not_found_identifiers if not_found_identifiers else None,
                total=len(found_users),
            )

        logger.info(
            f"Fetching {len(remaining_queries)} users from API (cache hits: {len(found_users)})"
        )

        def _batch_get() -> BatchUserResponse:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder for now

            # TODO: Implement actual API call when SDK supports it
            # For now, return empty response for remaining queries
            # Extract identifiers from remaining queries for not_found list
            api_not_found: list[str] = []
            for q in remaining_queries:
                if q.emails:
                    api_not_found.extend(q.emails)
                if q.mobiles:
                    api_not_found.extend(q.mobiles)
                if q.user_ids:
                    api_not_found.extend(q.user_ids)

            return BatchUserResponse(
                users=[],
                not_found=api_not_found if api_not_found else None,
                total=0,
            )

        api_response = self.retry_strategy.execute(_batch_get)

        # Store API results in cache if enabled
        if self.enable_cache and self.cache_manager and api_response.users:
            for user in api_response.users:
                self.cache_manager.cache_user(app_id, user)
                logger.debug(f"Cached user from batch: {user.union_id}")

        # Combine cached and API results
        all_users = found_users + api_response.users

        # Combine not_found lists
        all_not_found = not_found_identifiers.copy()
        if api_response.not_found:
            all_not_found.extend(api_response.not_found)

        return BatchUserResponse(
            users=all_users,
            not_found=all_not_found if all_not_found else None,
            total=len(all_users),
        )

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
