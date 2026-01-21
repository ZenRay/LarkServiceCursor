"""
Contact client for Lark Contact API.

This module provides a high-level client for contact query operations
via Lark Contact API, including user queries, department queries, and chat group queries.
"""

from datetime import timedelta

from lark_oapi.api.contact.v3 import (
    BatchGetIdUserRequest,
    BatchGetIdUserRequestBody,
    FindByDepartmentUserRequest,
    GetDepartmentRequest,
    GetUserRequest,
)
from lark_oapi.api.im.v1 import GetChatMembersRequest, GetChatRequest

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
from lark_service.core.base_service_client import BaseServiceClient
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    InvalidParameterError,
    NotFoundError,
)
from lark_service.core.retry import RetryStrategy
from lark_service.utils.logger import get_logger

logger = get_logger()


def _convert_lark_user_status(lark_status: object | None) -> int | None:
    """Convert Lark UserStatus to our status code.

    Args:
        lark_status: Lark UserStatus object

    Returns:
        Status code: 1 (active), 2 (inactive), 4 (resigned), or None
    """
    if not lark_status:
        return None

    # Check status flags (using hasattr for dynamic attributes)
    if hasattr(lark_status, "is_resigned") and lark_status.is_resigned:
        return 4  # Resigned
    if hasattr(lark_status, "is_frozen") and lark_status.is_frozen:
        return 2  # Inactive/Frozen
    if hasattr(lark_status, "is_activated") and lark_status.is_activated:
        return 1  # Active

    # Default to active if no clear status
    return 1


class ContactClient(BaseServiceClient):
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
        app_id: str | None = None,
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
            app_id : str | None
                Optional default app_id for this client (layer 3 in priority)
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
        # Initialize base class
        super().__init__(credential_pool, app_id)

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
        email: str,
        app_id: str | None = None,
    ) -> User:
        """
        Get user information by email.

        If caching is enabled, checks cache first before making API call.
        Cache is keyed by (app_id, email) and uses union_id for consistency.

        Parameters
        ----------
            email : str
                User email address
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

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
            ...     email="user@example.com"
            ... )
            >>> print(f"{user.name} ({user.open_id})")
        """
        if not email or "@" not in email:
            raise InvalidParameterError(f"Invalid email: {email}")

        # Resolve app_id
        resolved_app_id = self._resolve_app_id(app_id)

        # Check cache first if enabled
        if self.enable_cache and self.cache_manager:
            cached_user = self.cache_manager.get_user_by_email(resolved_app_id, email)
            if cached_user:
                logger.debug(f"Cache hit for user email: {email}")
                return cached_user
            logger.debug(f"Cache miss for user email: {email}")

        logger.info(f"Getting user by email from API: {email}")

        def _get() -> User:
            # Get SDK client (handles token management internally)
            client = self.credential_pool._get_sdk_client(resolved_app_id)

            # Step 1: Get user_id from email using BatchGetId
            batch_request = (
                BatchGetIdUserRequest.builder()
                .user_id_type("user_id")
                .request_body(BatchGetIdUserRequestBody.builder().emails([email]).build())
                .build()
            )

            batch_response = client.contact.v3.user.batch_get_id(batch_request)

            # Check response
            if not batch_response.success():
                logger.error(
                    f"Failed to get user_id by email: {batch_response.code} - {batch_response.msg}",
                    extra={"email": email, "code": batch_response.code},
                )
                if batch_response.code == 99991663:  # User not found
                    raise NotFoundError(f"User not found: {email}")
                raise APIError(
                    f"API error: {batch_response.msg}",
                    status_code=batch_response.code,
                    details={"email": email},
                )

            # Parse response to get user_id
            if not batch_response.data or not batch_response.data.user_list:
                raise NotFoundError(f"User not found: {email}")

            user_contact_info = batch_response.data.user_list[0]
            if not user_contact_info.user_id:
                raise NotFoundError(f"User not found: {email}")

            # Step 2: Get full user info using GetUser API
            get_request = (
                GetUserRequest.builder()
                .user_id_type("user_id")
                .user_id(user_contact_info.user_id)
                .build()
            )

            get_response = client.contact.v3.user.get(get_request)

            if not get_response.success():
                logger.error(
                    f"Failed to get user details: {get_response.code} - {get_response.msg}",
                    extra={"user_id": user_contact_info.user_id, "code": get_response.code},
                )
                raise APIError(
                    f"API error: {get_response.msg}",
                    status_code=get_response.code,
                    details={"user_id": user_contact_info.user_id},
                )

            if not get_response.data or not get_response.data.user:
                raise NotFoundError(f"User not found: {email}")

            # Get full user object
            lark_user = get_response.data.user

            # Convert to our User model
            user = User(
                open_id=lark_user.open_id or "",
                user_id=lark_user.user_id or "",
                union_id=lark_user.union_id or "",
                name=lark_user.name or "",
                avatar=lark_user.avatar.avatar_origin if lark_user.avatar else None,
                email=lark_user.email or None,
                mobile=lark_user.mobile or None,
                department_ids=lark_user.department_ids or None,
                employee_no=lark_user.employee_no or None,
                job_title=lark_user.job_title or None,
                status=_convert_lark_user_status(lark_user.status),
            )

            logger.info(f"Successfully retrieved user: {user.name} ({user.open_id})")
            return user

        user = self.retry_strategy.execute(_get)

        # Store in cache if enabled
        if self.enable_cache and self.cache_manager:
            self.cache_manager.cache_user(resolved_app_id, user)
            logger.debug(f"Cached user: {user.union_id}")

        return user

    def get_user_by_mobile(
        self,
        mobile: str,
        app_id: str | None = None,
    ) -> User:
        """
        Get user information by mobile number.

        Parameters
        ----------
            mobile : str
                User mobile number (with country code, e.g., +86-13800138000)
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

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
            ...     mobile="+86-13800138000"
            ... )
            >>> print(f"{user.name} ({user.open_id})")
        """
        if not mobile:
            raise InvalidParameterError("Mobile cannot be empty")

        # Resolve app_id
        resolved_app_id = self._resolve_app_id(app_id)

        # Check cache first if enabled
        if self.enable_cache and self.cache_manager:
            cached_user = self.cache_manager.get_user_by_mobile(resolved_app_id, mobile)
            if cached_user:
                logger.debug(f"Cache hit for user mobile: {mobile}")
                return cached_user
            logger.debug(f"Cache miss for user mobile: {mobile}")

        logger.info(f"Getting user by mobile from API: {mobile}")

        def _get() -> User:
            # Get SDK client (handles token management internally)
            client = self.credential_pool._get_sdk_client(resolved_app_id)

            # Step 1: Get user_id from mobile using BatchGetId
            batch_request = (
                BatchGetIdUserRequest.builder()
                .user_id_type("user_id")
                .request_body(BatchGetIdUserRequestBody.builder().mobiles([mobile]).build())
                .build()
            )

            batch_response = client.contact.v3.user.batch_get_id(batch_request)

            # Check response
            if not batch_response.success():
                logger.error(
                    f"Failed to get user_id by mobile: {batch_response.code} - {batch_response.msg}",
                    extra={"mobile": mobile, "code": batch_response.code},
                )
                if batch_response.code == 99991663:  # User not found
                    raise NotFoundError(f"User not found: {mobile}")
                raise APIError(
                    f"API error: {batch_response.msg}",
                    status_code=batch_response.code,
                    details={"mobile": mobile},
                )

            # Parse response to get user_id
            if not batch_response.data or not batch_response.data.user_list:
                raise NotFoundError(f"User not found: {mobile}")

            user_contact_info = batch_response.data.user_list[0]
            if not user_contact_info.user_id:
                raise NotFoundError(f"User not found: {mobile}")

            # Step 2: Get full user info using GetUser API
            get_request = (
                GetUserRequest.builder()
                .user_id_type("user_id")
                .user_id(user_contact_info.user_id)
                .build()
            )

            get_response = client.contact.v3.user.get(get_request)

            if not get_response.success():
                logger.error(
                    f"Failed to get user details: {get_response.code} - {get_response.msg}",
                    extra={"user_id": user_contact_info.user_id, "code": get_response.code},
                )
                raise APIError(
                    f"API error: {get_response.msg}",
                    status_code=get_response.code,
                    details={"user_id": user_contact_info.user_id},
                )

            if not get_response.data or not get_response.data.user:
                raise NotFoundError(f"User not found: {mobile}")

            # Get full user object
            lark_user = get_response.data.user

            # Convert to our User model
            user = User(
                open_id=lark_user.open_id or "",
                user_id=lark_user.user_id or "",
                union_id=lark_user.union_id or "",
                name=lark_user.name or "",
                avatar=lark_user.avatar.avatar_origin if lark_user.avatar else None,
                email=lark_user.email or None,
                mobile=lark_user.mobile or None,
                department_ids=lark_user.department_ids or None,
                employee_no=lark_user.employee_no or None,
                job_title=lark_user.job_title or None,
                status=_convert_lark_user_status(lark_user.status),
            )

            logger.info(f"Successfully retrieved user: {user.name} ({user.open_id})")
            return user

        user = self.retry_strategy.execute(_get)

        # Store in cache if enabled
        if self.enable_cache and self.cache_manager:
            self.cache_manager.cache_user(resolved_app_id, user)
            logger.debug(f"Cached user: {user.union_id}")

        return user

    def get_user_by_user_id(
        self,
        user_id: str,
        app_id: str | None = None,
    ) -> User:
        """
        Get user information by user_id.

        Parameters
        ----------
            user_id : str
                User ID (tenant-scoped)
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

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
            ...     user_id="4d7a3c6g"
            ... )
            >>> print(f"{user.name} ({user.open_id})")
        """
        if not user_id:
            raise InvalidParameterError("User ID cannot be empty")

        # Resolve app_id
        resolved_app_id = self._resolve_app_id(app_id)

        # Check cache first if enabled
        if self.enable_cache and self.cache_manager:
            cached_user = self.cache_manager.get_user_by_user_id(resolved_app_id, user_id)
            if cached_user:
                logger.debug(f"Cache hit for user_id: {user_id}")
                return cached_user
            logger.debug(f"Cache miss for user_id: {user_id}")

        logger.info(f"Getting user by user_id from API: {user_id}")

        def _get() -> User:
            # Get SDK client (handles token management internally)
            client = self.credential_pool._get_sdk_client(resolved_app_id)

            # Build request - use GetUser API with user_id
            request = GetUserRequest.builder().user_id_type("user_id").user_id(user_id).build()

            # Make API call
            response = client.contact.v3.user.get(request)

            # Check response
            if not response.success():
                logger.error(
                    f"Failed to get user by user_id: {response.code} - {response.msg}",
                    extra={"user_id": user_id, "code": response.code},
                )
                if response.code == 99991663:  # User not found
                    raise NotFoundError(f"User not found: {user_id}")
                raise APIError(
                    f"API error: {response.msg}",
                    status_code=response.code,
                    details={"user_id": user_id},
                )

            # Parse response
            if not response.data or not response.data.user:
                raise NotFoundError(f"User not found: {user_id}")

            # Get user
            lark_user = response.data.user

            # Convert to our User model
            user = User(
                open_id=lark_user.open_id or "",
                user_id=lark_user.user_id or "",
                union_id=lark_user.union_id or "",
                name=lark_user.name or "",
                avatar=lark_user.avatar.avatar_origin if lark_user.avatar else None,
                email=lark_user.email or None,
                mobile=lark_user.mobile or None,
                department_ids=lark_user.department_ids or None,
                employee_no=lark_user.employee_no or None,
                job_title=lark_user.job_title or None,
                status=_convert_lark_user_status(lark_user.status),
            )

            logger.info(f"Successfully retrieved user: {user.name} ({user.open_id})")
            return user

        user = self.retry_strategy.execute(_get)

        # Store in cache if enabled
        if self.enable_cache and self.cache_manager:
            self.cache_manager.cache_user(resolved_app_id, user)
            logger.debug(f"Cached user: {user.union_id}")

        return user

    def batch_get_users(
        self,
        queries: list[BatchUserQuery],
        app_id: str | None = None,
    ) -> BatchUserResponse:
        """
        Batch get users by email, mobile, or user_id.

        Parameters
        ----------
            queries : list[BatchUserQuery]
                List of query conditions (max 50)
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

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

        # Resolve app_id
        resolved_app_id = self._resolve_app_id(app_id)

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
                        cached_user = self.cache_manager.get_user_by_email(resolved_app_id, email)
                        if cached_user:
                            found_users.append(cached_user)
                            query_found = True
                            logger.debug(f"Cache hit for email: {email}")
                        else:
                            not_found_identifiers.append(email)

                if query.mobiles:
                    for mobile in query.mobiles:
                        cached_user = self.cache_manager.get_user_by_mobile(resolved_app_id, mobile)
                        if cached_user:
                            found_users.append(cached_user)
                            query_found = True
                            logger.debug(f"Cache hit for mobile: {mobile}")
                        else:
                            not_found_identifiers.append(mobile)

                if query.user_ids:
                    for user_id in query.user_ids:
                        cached_user = self.cache_manager.get_user_by_user_id(
                            resolved_app_id, user_id
                        )
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
            # Get SDK client (handles token management internally)
            client = self.credential_pool._get_sdk_client(resolved_app_id)

            # Collect all identifiers from remaining queries
            all_emails: list[str] = []
            all_mobiles: list[str] = []

            for q in remaining_queries:
                if q.emails:
                    all_emails.extend(q.emails)
                if q.mobiles:
                    all_mobiles.extend(q.mobiles)
                # Note: user_ids need to be queried individually via GetUser API
                # For now, we'll handle emails and mobiles via BatchGetId

            api_users: list[User] = []
            api_not_found: list[str] = []
            user_id_map: dict[str, str] = {}  # Maps user_id to email/mobile for tracking

            # Query by email/mobile if any
            if all_emails or all_mobiles:
                # Step 1: Get user_ids using BatchGetId
                body_builder = BatchGetIdUserRequestBody.builder()
                if all_emails:
                    body_builder.emails(all_emails)
                if all_mobiles:
                    body_builder.mobiles(all_mobiles)

                batch_request = (
                    BatchGetIdUserRequest.builder()
                    .user_id_type("user_id")
                    .request_body(body_builder.build())
                    .build()
                )

                # Make API call
                batch_response = client.contact.v3.user.batch_get_id(batch_request)

                # Check response
                if not batch_response.success():
                    logger.error(
                        f"Failed to batch get user_ids: {batch_response.code} - {batch_response.msg}",
                        extra={"code": batch_response.code},
                    )
                    # Don't raise error for batch queries, just log
                    # Mark all as not found
                    api_not_found.extend(all_emails)
                    api_not_found.extend(all_mobiles)
                else:
                    # Parse response to get user_ids
                    user_ids_to_fetch: list[str] = []
                    if batch_response.data and batch_response.data.user_list:
                        for user_contact_info in batch_response.data.user_list:
                            if user_contact_info.user_id:
                                user_ids_to_fetch.append(user_contact_info.user_id)
                                # Track which identifier this user_id corresponds to
                                if user_contact_info.email:
                                    user_id_map[user_contact_info.user_id] = user_contact_info.email
                                elif user_contact_info.mobile:
                                    user_id_map[user_contact_info.user_id] = (
                                        user_contact_info.mobile
                                    )

                    # Step 2: Get full user info for each user_id
                    for uid in user_ids_to_fetch:
                        try:
                            get_request = (
                                GetUserRequest.builder()
                                .user_id_type("user_id")
                                .user_id(uid)
                                .build()
                            )

                            get_response = client.contact.v3.user.get(get_request)

                            if (
                                get_response.success()
                                and get_response.data
                                and get_response.data.user
                            ):
                                lark_user = get_response.data.user
                                user = User(
                                    open_id=lark_user.open_id or "",
                                    user_id=lark_user.user_id or "",
                                    union_id=lark_user.union_id or "",
                                    name=lark_user.name or "",
                                    avatar=lark_user.avatar.avatar_origin
                                    if lark_user.avatar
                                    else None,
                                    email=lark_user.email or None,
                                    mobile=lark_user.mobile or None,
                                    department_ids=lark_user.department_ids or None,
                                    employee_no=lark_user.employee_no or None,
                                    job_title=lark_user.job_title or None,
                                    status=_convert_lark_user_status(lark_user.status),
                                )
                                api_users.append(user)
                            else:
                                # Mark the original identifier as not found
                                if uid in user_id_map:
                                    api_not_found.append(user_id_map[uid])
                        except Exception as e:
                            logger.warning(f"Failed to get user {uid}: {e}")
                            if uid in user_id_map:
                                api_not_found.append(user_id_map[uid])

                    # Determine which identifiers were not found in Step 1
                    found_emails = {u.email for u in api_users if u.email}
                    found_mobiles = {u.mobile for u in api_users if u.mobile}

                    api_not_found.extend(
                        [e for e in all_emails if e not in found_emails and e not in api_not_found]
                    )
                    api_not_found.extend(
                        [
                            m
                            for m in all_mobiles
                            if m not in found_mobiles and m not in api_not_found
                        ]
                    )

            # Handle user_ids separately (need individual GetUser calls)
            for q in remaining_queries:
                if q.user_ids:
                    for uid in q.user_ids:
                        try:
                            # Use GetUser API for user_id
                            request = (
                                GetUserRequest.builder()
                                .user_id_type("user_id")
                                .user_id(uid)
                                .build()
                            )

                            response = client.contact.v3.user.get(request)

                            if response.success() and response.data and response.data.user:
                                lark_user = response.data.user
                                user = User(
                                    open_id=lark_user.open_id or "",
                                    user_id=lark_user.user_id or "",
                                    union_id=lark_user.union_id or "",
                                    name=lark_user.name or "",
                                    avatar=lark_user.avatar.avatar_origin
                                    if lark_user.avatar
                                    else None,
                                    email=lark_user.email or None,
                                    mobile=lark_user.mobile or None,
                                    department_ids=lark_user.department_ids or None,
                                    employee_no=lark_user.employee_no or None,
                                    job_title=lark_user.job_title or None,
                                    status=_convert_lark_user_status(lark_user.status),
                                )
                                api_users.append(user)
                            else:
                                api_not_found.append(uid)
                        except Exception as e:
                            logger.warning(f"Failed to get user by user_id {uid}: {e}")
                            api_not_found.append(uid)

            logger.info(
                f"Batch query completed: {len(api_users)} found, {len(api_not_found)} not found"
            )

            return BatchUserResponse(
                users=api_users,
                not_found=api_not_found if api_not_found else None,
                total=len(api_users),
            )

        api_response = self.retry_strategy.execute(_batch_get)

        # Store API results in cache if enabled
        if self.enable_cache and self.cache_manager and api_response.users:
            for user in api_response.users:
                self.cache_manager.cache_user(resolved_app_id, user)
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
        department_id: str,
        app_id: str | None = None,
    ) -> Department:
        """
        Get department information.

        Parameters
        ----------
            department_id : str
                Department ID (open_department_id)
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

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
            ...     department_id="od-xxx"
            ... )
            >>> print(f"{dept.name} (members: {dept.member_count})")
        """
        if not department_id:
            raise InvalidParameterError("Department ID cannot be empty")

        # Resolve app_id
        resolved_app_id = self._resolve_app_id(app_id)

        logger.info(f"Getting department: {department_id}")

        def _get() -> Department:
            # Get SDK client (handles token management internally)
            client = self.credential_pool._get_sdk_client(resolved_app_id)

            # Build request
            request = (
                GetDepartmentRequest.builder()
                .department_id(department_id)
                .department_id_type("open_department_id")
                .user_id_type("user_id")
                .build()
            )

            # Make API call
            response = client.contact.v3.department.get(request)

            # Check response
            if not response.success():
                logger.error(
                    f"Failed to get department: {response.code} - {response.msg}",
                    extra={"code": response.code, "department_id": department_id},
                )

                # Map error codes
                if response.code == 230002:  # Department not found
                    raise NotFoundError(f"Department not found: {department_id}")
                elif response.code in [99991668, 230011]:  # Permission denied
                    from lark_service.core.exceptions import PermissionDeniedError

                    raise PermissionDeniedError(
                        f"No permission to access department: {department_id}"
                    )
                else:
                    raise APIError(
                        f"Failed to get department: {response.msg}",
                        code=response.code,
                    )

            # Parse response
            if not response.data or not response.data.department:
                raise NotFoundError(f"Department not found: {department_id}")

            lark_dept = response.data.department

            # Convert to our Department model
            department = Department(
                department_id=lark_dept.open_department_id or lark_dept.department_id or "",
                name=lark_dept.name or "",
                parent_department_id=lark_dept.parent_department_id or None,
                department_path=None,  # Not provided by API
                leader_user_id=lark_dept.leader_user_id or None,
                member_count=lark_dept.member_count or None,
                status=1 if not hasattr(lark_dept, "status") or not lark_dept.status else 0,
                order=lark_dept.order or None,
            )

            logger.info(f"Successfully retrieved department: {department.name}")
            return department

        return self.retry_strategy.execute(_get)

    def get_department_members(
        self,
        department_id: str,
        page_size: int = 50,
        page_token: str | None = None,
        app_id: str | None = None,
    ) -> tuple[list[DepartmentUser], str | None]:
        """
        Get department members with pagination.

        Parameters
        ----------
            department_id : str
                Department ID (open_department_id)
            page_size : int
                Page size (default: 50, max: 100)
            page_token : str | None
                Page token for pagination
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

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

        # Resolve app_id
        resolved_app_id = self._resolve_app_id(app_id)

        logger.info(f"Getting members of department {department_id}, page_size={page_size}")

        def _get_members() -> tuple[list[DepartmentUser], str | None]:
            # Get SDK client (handles token management internally)
            client = self.credential_pool._get_sdk_client(resolved_app_id)

            # Build request
            request_builder = (
                FindByDepartmentUserRequest.builder()
                .department_id(department_id)
                .department_id_type("open_department_id")
                .user_id_type("user_id")
                .page_size(page_size)
            )

            if page_token:
                request_builder.page_token(page_token)

            request = request_builder.build()

            # Make API call
            response = client.contact.v3.user.find_by_department(request)

            # Check response
            if not response.success():
                logger.error(
                    f"Failed to get department members: {response.code} - {response.msg}",
                    extra={"code": response.code, "department_id": department_id},
                )

                # Map error codes
                if response.code == 230002:  # Department not found
                    raise NotFoundError(f"Department not found: {department_id}")
                elif response.code in [99991668, 230011]:  # Permission denied
                    from lark_service.core.exceptions import PermissionDeniedError

                    raise PermissionDeniedError(
                        f"No permission to access department members: {department_id}"
                    )
                else:
                    raise APIError(
                        f"Failed to get department members: {response.msg}",
                        code=response.code,
                    )

            # Parse response
            members: list[DepartmentUser] = []
            next_page_token: str | None = None

            if response.data:
                if response.data.items:
                    for lark_user in response.data.items:
                        member = DepartmentUser(
                            department_id=department_id,
                            user_id=lark_user.user_id or "",
                            is_leader=False,  # Not provided by find_by_department API
                            order=None,
                        )
                        members.append(member)

                next_page_token = response.data.page_token or None

            logger.info(
                f"Retrieved {len(members)} department members"
                + (f", has_more: {bool(next_page_token)}" if next_page_token else "")
            )

            return members, next_page_token

        return self.retry_strategy.execute(_get_members)

    def get_chat_group(
        self,
        chat_id: str,
        app_id: str | None = None,
    ) -> ChatGroup:
        """
        Get chat group information.

        Parameters
        ----------
            chat_id : str
                Chat ID
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

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
            ...     chat_id="oc_xxx"
            ... )
            >>> print(f"{group.name} (members: {group.member_count})")
        """
        if not chat_id:
            raise InvalidParameterError("Chat ID cannot be empty")

        # Resolve app_id
        resolved_app_id = self._resolve_app_id(app_id)

        logger.info(f"Getting chat group: {chat_id}")

        def _get() -> ChatGroup:
            # Get SDK client (handles token management internally)
            client = self.credential_pool._get_sdk_client(resolved_app_id)

            # Build request
            request = GetChatRequest.builder().chat_id(chat_id).build()

            # Make API call
            response = client.im.v1.chat.get(request)

            # Check response
            if not response.success():
                logger.error(
                    f"Failed to get chat group: {response.code} - {response.msg}",
                    extra={"code": response.code, "chat_id": chat_id},
                )

                # Map error codes
                if response.code == 230008:  # Chat not found
                    raise NotFoundError(f"Chat group not found: {chat_id}")
                elif response.code in [99991668]:  # Permission denied
                    from lark_service.core.exceptions import PermissionDeniedError

                    raise PermissionDeniedError(f"No permission to access chat: {chat_id}")
                else:
                    raise APIError(
                        f"Failed to get chat group: {response.msg}",
                        code=response.code,
                    )

            # Parse response
            if not response.data:
                raise NotFoundError(f"Chat group not found: {chat_id}")

            lark_chat = response.data

            # Convert to our ChatGroup model
            chat_group = ChatGroup(
                chat_id=lark_chat.chat_id or chat_id,
                name=lark_chat.name or "",
                description=lark_chat.description or None,
                owner_id=lark_chat.owner_id or None,
                member_count=None,  # Not provided by get chat API
                chat_mode=lark_chat.chat_mode or None,
                chat_type=lark_chat.chat_type or None,
                avatar=lark_chat.avatar or None,
                create_time=None,  # Not provided by get chat API
                update_time=None,  # Not provided by get chat API
            )

            logger.info(f"Successfully retrieved chat group: {chat_group.name}")
            return chat_group

        return self.retry_strategy.execute(_get)

    def get_chat_members(
        self,
        chat_id: str,
        page_size: int = 50,
        page_token: str | None = None,
        app_id: str | None = None,
    ) -> tuple[list[ChatMember], str | None]:
        """
        Get chat group members with pagination.

        Parameters
        ----------
            chat_id : str
                Chat ID
            page_size : int
                Page size (default: 50, max: 100)
            page_token : str | None
                Page token for pagination
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

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

        # Resolve app_id
        resolved_app_id = self._resolve_app_id(app_id)

        logger.info(f"Getting members of chat {chat_id}, page_size={page_size}")

        def _get_members() -> tuple[list[ChatMember], str | None]:
            # Get SDK client (handles token management internally)
            client = self.credential_pool._get_sdk_client(resolved_app_id)

            # Build request
            request_builder = (
                GetChatMembersRequest.builder()
                .chat_id(chat_id)
                .member_id_type("open_id")
                .page_size(page_size)
            )

            if page_token:
                request_builder.page_token(page_token)

            request = request_builder.build()

            # Make API call
            response = client.im.v1.chat_members.get(request)

            # Check response
            if not response.success():
                logger.error(
                    f"Failed to get chat members: {response.code} - {response.msg}",
                    extra={"code": response.code, "chat_id": chat_id},
                )

                # Map error codes
                if response.code == 230008:  # Chat not found
                    raise NotFoundError(f"Chat group not found: {chat_id}")
                elif response.code in [99991668]:  # Permission denied
                    from lark_service.core.exceptions import PermissionDeniedError

                    raise PermissionDeniedError(f"No permission to access chat members: {chat_id}")
                else:
                    raise APIError(
                        f"Failed to get chat members: {response.msg}",
                        code=response.code,
                    )

            # Parse response
            members: list[ChatMember] = []
            next_page_token: str | None = None

            if response.data:
                if response.data.items:
                    for lark_member in response.data.items:
                        member = ChatMember(
                            chat_id=chat_id,
                            user_id=lark_member.member_id or "",
                            member_role=None,  # Not provided by get_chat_members API
                            join_time=None,  # Not provided by get_chat_members API
                        )
                        members.append(member)

                next_page_token = response.data.page_token or None

            logger.info(
                f"Retrieved {len(members)} chat members"
                + (f", has_more: {bool(next_page_token)}" if next_page_token else "")
            )

            return members, next_page_token

        return self.retry_strategy.execute(_get_members)
