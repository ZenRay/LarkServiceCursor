"""CLI entry point for lark-service.

Provides command-line interface for managing Feishu applications and tokens.
"""

import click

from lark_service.cli.app import app


@click.group()
@click.version_option(version="0.1.0", prog_name="lark-service-cli")
def main() -> None:
    """Lark Service CLI - Manage Feishu applications and tokens.

    A command-line tool for managing Feishu application configurations,
    tokens, and performing system diagnostics.

    Examples:
        # Add a new application
        lark-service-cli app add --app-id cli_abc123 --app-name "My App" --app-secret "secret"

        # List all applications
        lark-service-cli app list

        # Show application details
        lark-service-cli app show cli_abc123

        # Update application
        lark-service-cli app update cli_abc123 --status inactive

        # Delete application
        lark-service-cli app delete cli_abc123

    For more information on each command, use:
        lark-service-cli COMMAND --help
    """
    pass


# Register command groups
main.add_command(app)


if __name__ == "__main__":
    main()
