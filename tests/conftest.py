"""
Pytest configuration for all tests.

This file automatically loads environment variables from .env.test
for integration tests.
"""

from pathlib import Path

from dotenv import load_dotenv

# Load .env.test file if it exists
env_test_path = Path(__file__).parent.parent / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path)
    print(f"\n✅ Loaded environment variables from {env_test_path}")
else:
    print(f"\n⚠️  .env.test not found at {env_test_path}")
    print("   Integration tests may be skipped without proper configuration")


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (requires real API credentials)",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test (uses mocks, no real API calls)",
    )
