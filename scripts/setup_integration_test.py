#!/usr/bin/env python3
"""
Interactive setup wizard for integration test configuration.

This script guides you through the process of configuring integration tests.
"""

import os
import sys
from pathlib import Path


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_step(step_num: int, text: str) -> None:
    """Print a step header."""
    print(f"\n📍 Step {step_num}: {text}")
    print("-" * 60)


def get_input(prompt: str, default: str = "", required: bool = True) -> str:
    """Get user input with optional default value."""
    if default:
        prompt = f"{prompt} [{default}]"

    while True:
        value = input(f"{prompt}: ").strip()
        if not value and default:
            return default
        if not value and required:
            print("❌ This field is required. Please enter a value.")
            continue
        return value


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ["y", "yes"]:
            return True
        if response in ["n", "no"]:
            return False
        print("❌ Please enter 'y' or 'n'")


def main() -> int:
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    env_test_path = project_root / ".env.test"

    print_header("🚀 Integration Test Setup Wizard")
    print("\nThis wizard will help you configure integration tests for Lark Service.")
    print("You'll need:")
    print("  1. A Lark application (App ID and App Secret)")
    print("  2. A test user's email address")
    print("  3. PostgreSQL database access")

    if not get_yes_no("\nReady to begin?", default=True):
        print("\n👋 Setup cancelled.")
        return 0

    # Step 1: Lark Application
    print_step(1, "Lark Application Configuration")
    print("\n📖 To get your App ID and App Secret:")
    print("   1. Visit: https://open.feishu.cn/app")
    print("   2. Select your application")
    print("   3. Go to: 凭证与基础信息 (Credentials & Basic Info)")
    print("   4. Copy App ID and App Secret")

    app_id = get_input("\nEnter your App ID (starts with 'cli_')", required=True)
    while not app_id.startswith("cli_"):
        print("❌ App ID should start with 'cli_'")
        app_id = get_input("Enter your App ID", required=True)

    app_secret = get_input("Enter your App Secret", required=True)
    while len(app_secret) < 20:
        print("❌ App Secret seems too short (should be at least 20 characters)")
        app_secret = get_input("Enter your App Secret", required=True)

    # Step 2: Test User
    print_step(2, "Test User Configuration")
    print("\n📖 Provide a test user from your organization:")
    print("   - This user should be in the application's scope")
    print("   - We'll use this user for Contact API tests")

    test_email = get_input("\nEnter test user's email", required=True)
    while "@" not in test_email:
        print("❌ Invalid email format")
        test_email = get_input("Enter test user's email", required=True)

    test_mobile = get_input(
        "Enter test user's mobile (optional, format: +8613800138000)",
        required=False,
    )

    # Step 3: Database Configuration
    print_step(3, "Database Configuration")
    print("\n📖 PostgreSQL is required for caching tests.")

    use_docker = get_yes_no("\nAre you using Docker/docker-compose?", default=True)

    if use_docker:
        print("\n✅ Great! Using default Docker configuration:")
        postgres_host = "localhost"
        postgres_port = "5432"
        postgres_db = "lark_service_test"
        postgres_user = "lark"
        postgres_password = "test_password_123"
        print(f"   Host: {postgres_host}:{postgres_port}")
        print(f"   Database: {postgres_db}")
        print(f"   User: {postgres_user}")
    else:
        postgres_host = get_input("PostgreSQL host", default="localhost")
        postgres_port = get_input("PostgreSQL port", default="5432")
        postgres_db = get_input("PostgreSQL database", default="lark_service_test")
        postgres_user = get_input("PostgreSQL user", default="lark")
        postgres_password = get_input("PostgreSQL password", required=True)

    # Step 4: Encryption Key
    print_step(4, "Encryption Key")
    print("\n📖 An encryption key is needed for securing app secrets.")

    generate_key = get_yes_no("Generate a random encryption key?", default=True)

    if generate_key:
        import base64
        import secrets

        encryption_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        print(f"\n✅ Generated encryption key: {encryption_key[:20]}...")
    else:
        encryption_key = get_input(
            "Enter your encryption key (base64, 32 bytes)",
            default="test_key_for_integration_tests_only_32bytes_base64==",
        )

    # Step 5: Optional Test Data
    print_step(5, "Optional Test Data")
    print("\n📖 You can provide existing test documents, or we'll create them automatically.")

    configure_docs = get_yes_no("Configure test document tokens?", default=False)

    doc_token = ""
    bitable_app_token = ""
    bitable_table_id = ""

    if configure_docs:
        doc_token = get_input("Document token (starts with 'doxcn')", required=False)
        bitable_app_token = get_input("Bitable app token (starts with 'bascn')", required=False)
        if bitable_app_token:
            bitable_table_id = get_input("Bitable table ID (starts with 'tbl')", required=False)

    # Step 6: Generate .env.test file
    print_step(6, "Generating Configuration File")

    config_content = f"""# ============================================
# 集成测试环境变量配置
# ============================================
# 
# 自动生成于: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 
# ⚠️ 警告: 此文件包含真实凭证,请勿提交到 Git!

# ============================================
# PostgreSQL 配置
# ============================================
POSTGRES_HOST={postgres_host}
POSTGRES_PORT={postgres_port}
POSTGRES_DB={postgres_db}
POSTGRES_USER={postgres_user}
POSTGRES_PASSWORD={postgres_password}

# ============================================
# RabbitMQ 配置 (可选)
# ============================================
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=lark
RABBITMQ_PASSWORD=test_password_123

# ============================================
# 加密密钥配置
# ============================================
LARK_CONFIG_ENCRYPTION_KEY={encryption_key}

# ============================================
# 飞书应用凭证
# ============================================
TEST_APP_ID={app_id}
TEST_APP_SECRET={app_secret}

# ============================================
# 测试数据配置
# ============================================
TEST_USER_EMAIL={test_email}
"""

    if test_mobile:
        config_content += f"TEST_USER_MOBILE={test_mobile}\n"

    if doc_token:
        config_content += f"\n# 测试文档\nTEST_DOC_TOKEN={doc_token}\n"

    if bitable_app_token:
        config_content += f"TEST_BITABLE_APP_TOKEN={bitable_app_token}\n"
        if bitable_table_id:
            config_content += f"TEST_BITABLE_TABLE_ID={bitable_table_id}\n"

    config_content += """
# ============================================
# 日志配置
# ============================================
LOG_LEVEL=DEBUG
"""

    # Check if file exists
    if env_test_path.exists():
        print(f"\n⚠️  File already exists: {env_test_path}")
        if not get_yes_no("Overwrite existing file?", default=False):
            backup_path = env_test_path.with_suffix(".test.backup")
            print(f"\n💾 Saving configuration to: {backup_path}")
            env_test_path = backup_path

    # Write file
    with open(env_test_path, "w") as f:
        f.write(config_content)

    print(f"\n✅ Configuration saved to: {env_test_path}")

    # Step 7: Verification
    print_step(7, "Verification")
    print("\n📖 Let's verify your configuration...")

    if get_yes_no("Run configuration verification now?", default=True):
        print("\n" + "=" * 60)
        verify_script = project_root / "scripts" / "verify_integration_config.py"
        if verify_script.exists():
            os.system(f"python {verify_script}")
        else:
            print("⚠️  Verification script not found")
            print(f"   Expected: {verify_script}")

    # Final instructions
    print_header("🎉 Setup Complete!")
    print("\n✅ Your integration test environment is configured!")
    print("\n📝 Next steps:")
    print("\n1. Start PostgreSQL (if using Docker):")
    print("   docker-compose up -d postgres")
    print("\n2. Verify configuration:")
    print("   python scripts/verify_integration_config.py")
    print("\n3. Run integration tests:")
    print("   pytest tests/integration/ -v")
    print("\n4. View detailed setup guide:")
    print("   cat docs/integration-test-setup.md")
    print("\n" + "=" * 60)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
