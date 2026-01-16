#!/usr/bin/env python3
"""
Integration test configuration verification script.

This script verifies that the integration test environment is properly configured.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def check_env_file() -> bool:
    """Check if .env.test file exists."""
    env_test = project_root / ".env.test"
    if not env_test.exists():
        print("❌ .env.test file not found")
        print(f"   Expected location: {env_test}")
        print("   Please create it from .env.example")
        return False
    print(f"✅ .env.test file found: {env_test}")
    return True


def load_env_vars() -> dict[str, str]:
    """Load environment variables from .env.test."""
    from dotenv import load_dotenv

    env_test = project_root / ".env.test"
    load_dotenv(env_test)

    return {
        "TEST_APP_ID": os.getenv("TEST_APP_ID", ""),
        "TEST_APP_SECRET": os.getenv("TEST_APP_SECRET", ""),
        "TEST_USER_EMAIL": os.getenv("TEST_USER_EMAIL", ""),
        "TEST_USER_MOBILE": os.getenv("TEST_USER_MOBILE", ""),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB", "lark_service_test"),
        "POSTGRES_USER": os.getenv("POSTGRES_USER", "lark"),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "LARK_CONFIG_ENCRYPTION_KEY": os.getenv("LARK_CONFIG_ENCRYPTION_KEY", ""),
    }


def check_required_vars(env_vars: dict[str, str]) -> bool:
    """Check if required environment variables are set."""
    required = {
        "TEST_APP_ID": "Lark application ID",
        "TEST_APP_SECRET": "Lark application secret",
        "TEST_USER_EMAIL": "Test user email",
        "POSTGRES_HOST": "PostgreSQL host",
        "POSTGRES_DB": "PostgreSQL database",
        "POSTGRES_USER": "PostgreSQL user",
        "POSTGRES_PASSWORD": "PostgreSQL password",
        "LARK_CONFIG_ENCRYPTION_KEY": "Encryption key",
    }

    all_ok = True
    for var, description in required.items():
        value = env_vars.get(var, "")
        if not value or value.startswith("xxx") or value.startswith("test_key"):
            print(f"❌ {var} not configured ({description})")
            all_ok = False
        else:
            # Mask sensitive values
            if "SECRET" in var or "PASSWORD" in var or "KEY" in var:
                masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                print(f"✅ {var} = {masked}")
            else:
                print(f"✅ {var} = {value}")

    return all_ok


def check_optional_vars(env_vars: dict[str, str]) -> None:
    """Check optional environment variables."""
    optional = {
        "TEST_USER_MOBILE": "Test user mobile",
        "TEST_USER_OPEN_ID": "Test user open_id",
        "TEST_DOC_TOKEN": "Test document token",
        "TEST_BITABLE_APP_TOKEN": "Test bitable app token",
    }

    print("\n📋 Optional configuration:")
    for var, description in optional.items():
        value = os.getenv(var, "")
        if value and not value.startswith("xxx"):
            print(f"✅ {var} = {value} ({description})")
        else:
            print(f"⚠️  {var} not configured ({description}) - will be auto-created")


def check_postgres_connection(env_vars: dict[str, str]) -> bool:
    """Check PostgreSQL connection."""
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=env_vars["POSTGRES_HOST"],
            port=int(env_vars["POSTGRES_PORT"]),
            database=env_vars["POSTGRES_DB"],
            user=env_vars["POSTGRES_USER"],
            password=env_vars["POSTGRES_PASSWORD"],
            connect_timeout=5,
        )
        conn.close()
        print(f"✅ PostgreSQL connection successful ({env_vars['POSTGRES_HOST']}:{env_vars['POSTGRES_PORT']})")
        return True
    except ImportError:
        print("⚠️  psycopg2 not installed - skipping PostgreSQL check")
        print("   Install: pip install psycopg2-binary")
        return True  # Not a failure, just can't check
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print(f"   Host: {env_vars['POSTGRES_HOST']}:{env_vars['POSTGRES_PORT']}")
        print(f"   Database: {env_vars['POSTGRES_DB']}")
        print("   Please ensure PostgreSQL is running:")
        print("   docker-compose up -d postgres")
        return False


def check_lark_credentials(env_vars: dict[str, str]) -> bool:
    """Check Lark application credentials."""
    app_id = env_vars.get("TEST_APP_ID", "")
    app_secret = env_vars.get("TEST_APP_SECRET", "")

    # Basic format validation
    if not app_id.startswith("cli_"):
        print(f"❌ TEST_APP_ID format invalid: should start with 'cli_' (got: {app_id})")
        return False

    if len(app_secret) < 20:
        print(f"❌ TEST_APP_SECRET too short: should be at least 20 characters")
        return False

    print("✅ Lark credentials format valid")

    # Try to get tenant access token
    try:
        import lark_oapi as lark
        from lark_oapi.api.auth.v3 import InternalTenantAccessTokenRequest

        client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()

        request = InternalTenantAccessTokenRequest.builder().build()
        response = client.auth.v3.tenant_access_token.internal(request)

        if response.success():
            print("✅ Lark API authentication successful")
            print(f"   Tenant access token obtained (expires in {response.data.expire} seconds)")
            return True
        else:
            print(f"❌ Lark API authentication failed: {response.code} - {response.msg}")
            print("   Please check your APP_ID and APP_SECRET")
            return False

    except ImportError:
        print("⚠️  lark-oapi-sdk not installed - skipping API check")
        print("   Install: pip install lark-oapi")
        return True  # Not a failure, just can't check
    except Exception as e:
        print(f"❌ Lark API check failed: {e}")
        return False


def check_test_user(env_vars: dict[str, str]) -> bool:
    """Check test user configuration."""
    email = env_vars.get("TEST_USER_EMAIL", "")

    if not email or "@" not in email:
        print(f"❌ TEST_USER_EMAIL invalid: {email}")
        return False

    print(f"✅ Test user email valid: {email}")
    return True


def print_summary(checks: dict[str, bool]) -> None:
    """Print summary of all checks."""
    print("\n" + "=" * 60)
    print("📊 Configuration Verification Summary")
    print("=" * 60)

    passed = sum(checks.values())
    total = len(checks)

    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")

    print("=" * 60)
    print(f"Result: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! You can run integration tests:")
        print("   pytest tests/integration/ -v")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("   See docs/integration-test-setup.md for detailed instructions")


def main() -> int:
    """Main entry point."""
    print("🔍 Verifying integration test configuration...\n")

    checks = {}

    # Check 1: .env.test file exists
    checks["Environment file"] = check_env_file()
    if not checks["Environment file"]:
        print_summary(checks)
        return 1

    # Load environment variables
    env_vars = load_env_vars()

    # Check 2: Required variables
    print("\n📋 Required configuration:")
    checks["Required variables"] = check_required_vars(env_vars)

    # Check 3: Optional variables
    check_optional_vars(env_vars)

    # Check 4: PostgreSQL connection
    print("\n🗄️  Database connection:")
    checks["PostgreSQL connection"] = check_postgres_connection(env_vars)

    # Check 5: Lark credentials
    print("\n🔑 Lark API credentials:")
    checks["Lark credentials"] = check_lark_credentials(env_vars)

    # Check 6: Test user
    print("\n👤 Test user:")
    checks["Test user"] = check_test_user(env_vars)

    # Print summary
    print_summary(checks)

    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
