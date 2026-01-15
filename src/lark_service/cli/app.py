"""CLI commands for application management.

Provides commands to manage Feishu application configurations.
"""

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from lark_service.core.exceptions import StorageError, ValidationError
from lark_service.core.storage.sqlite_storage import ApplicationManager

console = Console()


def get_app_manager() -> ApplicationManager:
    """Get ApplicationManager instance.

    Returns:
        ApplicationManager instance

    Raises:
        click.ClickException: If initialization fails
    """
    try:
        # Get encryption key from environment
        import os
        encryption_key_str = os.getenv("LARK_CONFIG_ENCRYPTION_KEY")
        if not encryption_key_str:
            raise click.ClickException(
                "LARK_CONFIG_ENCRYPTION_KEY environment variable not set"
            )

        encryption_key = encryption_key_str.encode()

        # Get database path
        db_path = os.getenv("LARK_CONFIG_DB_PATH", "data/lark_config.db")

        return ApplicationManager(db_path, encryption_key)

    except Exception as e:
        raise click.ClickException(f"Failed to initialize ApplicationManager: {e}") from e


@click.group()
def app() -> None:
    """Manage Feishu application configurations."""
    pass


@app.command()
@click.option("--app-id", required=True, help="Application ID (e.g., cli_abc123)")
@click.option("--app-name", required=True, help="Application name")
@click.option("--app-secret", required=True, help="Application secret")
@click.option("--description", help="Application description")
@click.option("--permissions", help="Application permissions (JSON string)")
@click.option("--created-by", help="Creator identifier")
def add(
    app_id: str,
    app_name: str,
    app_secret: str,
    description: str | None,
    permissions: str | None,
    created_by: str | None,
) -> None:
    """Add a new application configuration.

    Example:
        lark-service-cli app add \\
            --app-id cli_abc123 \\
            --app-name "My App" \\
            --app-secret "secret123" \\
            --description "Test application"
    """
    manager = get_app_manager()

    try:
        app = manager.add_application(
            app_id=app_id,
            app_name=app_name,
            app_secret=app_secret,
            description=description,
            permissions=permissions,
            created_by=created_by,
        )

        console.print("[green]✓[/green] Application added successfully!")
        console.print(f"  App ID: {app.app_id}")
        console.print(f"  App Name: {app.app_name}")
        console.print(f"  Status: {app.status}")

    except (ValidationError, StorageError) as e:
        console.print(f"[red]✗[/red] Error: {e}", style="red")
        sys.exit(1)
    finally:
        manager.close()


@app.command()
@click.option("--status", type=click.Choice(["active", "inactive", "deleted"]), help="Filter by status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def list(status: str | None, output_json: bool) -> None:
    """List all application configurations.

    Example:
        lark-service-cli app list
        lark-service-cli app list --status active
        lark-service-cli app list --json
    """
    manager = get_app_manager()

    try:
        apps = manager.list_applications(status=status)

        if output_json:
            # JSON output
            apps_data = [
                {
                    "app_id": app.app_id,
                    "app_name": app.app_name,
                    "description": app.description,
                    "status": app.status,
                    "permissions": app.permissions,
                    "created_at": app.created_at.isoformat() if app.created_at else None,
                    "created_by": app.created_by,
                }
                for app in apps
            ]
            console.print(json.dumps(apps_data, indent=2, ensure_ascii=False))
        else:
            # Rich table output
            if not apps:
                console.print("[yellow]No applications found.[/yellow]")
                return

            table = Table(title="Feishu Applications")
            table.add_column("App ID", style="cyan")
            table.add_column("App Name", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Description")
            table.add_column("Created At")

            for app in apps:
                status_emoji = "✓" if app.status == "active" else "✗"
                created_at_str = app.created_at.strftime("%Y-%m-%d %H:%M") if app.created_at else "N/A"

                table.add_row(
                    app.app_id,
                    app.app_name,
                    f"{status_emoji} {app.status}",
                    app.description or "",
                    created_at_str,
                )

            console.print(table)
            console.print(f"\nTotal: {len(apps)} application(s)")

    except (ValidationError, StorageError) as e:
        console.print(f"[red]✗[/red] Error: {e}", style="red")
        sys.exit(1)
    finally:
        manager.close()


@app.command()
@click.argument("app_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def show(app_id: str, output_json: bool) -> None:
    """Show application configuration details.

    The app_secret will be masked for security.

    Example:
        lark-service-cli app show cli_abc123
        lark-service-cli app show cli_abc123 --json
    """
    manager = get_app_manager()

    try:
        app = manager.get_application(app_id)

        if not app:
            console.print(f"[red]✗[/red] Application not found: {app_id}", style="red")
            sys.exit(1)

        # Mask secret
        masked_secret = "secret_****"

        if output_json:
            # JSON output
            app_data = {
                "app_id": app.app_id,
                "app_name": app.app_name,
                "app_secret": masked_secret,
                "description": app.description,
                "status": app.status,
                "permissions": app.permissions,
                "created_at": app.created_at.isoformat() if app.created_at else None,
                "updated_at": app.updated_at.isoformat() if app.updated_at else None,
                "created_by": app.created_by,
            }
            console.print(json.dumps(app_data, indent=2, ensure_ascii=False))
        else:
            # Rich formatted output
            console.print("\n[bold cyan]Application Details[/bold cyan]")
            console.print(f"  App ID:       {app.app_id}")
            console.print(f"  App Name:     {app.app_name}")
            console.print(f"  App Secret:   {masked_secret}")
            console.print(f"  Status:       {app.status}")
            console.print(f"  Description:  {app.description or 'N/A'}")
            console.print(f"  Permissions:  {app.permissions or 'N/A'}")
            console.print(f"  Created At:   {app.created_at.strftime('%Y-%m-%d %H:%M:%S') if app.created_at else 'N/A'}")
            console.print(f"  Updated At:   {app.updated_at.strftime('%Y-%m-%d %H:%M:%S') if app.updated_at else 'N/A'}")
            console.print(f"  Created By:   {app.created_by or 'N/A'}\n")

    except (ValidationError, StorageError) as e:
        console.print(f"[red]✗[/red] Error: {e}", style="red")
        sys.exit(1)
    finally:
        manager.close()


@app.command()
@click.argument("app_id")
@click.option("--app-name", help="New application name")
@click.option("--app-secret", help="New application secret")
@click.option("--description", help="New description")
@click.option("--status", type=click.Choice(["active", "inactive", "deleted"]), help="New status")
@click.option("--permissions", help="New permissions (JSON string)")
def update(
    app_id: str,
    app_name: str | None,
    app_secret: str | None,
    description: str | None,
    status: str | None,
    permissions: str | None,
) -> None:
    """Update application configuration.

    Example:
        lark-service-cli app update cli_abc123 --app-name "New Name"
        lark-service-cli app update cli_abc123 --status inactive
        lark-service-cli app update cli_abc123 --app-secret "new_secret"
    """
    manager = get_app_manager()

    try:
        # Check if any update is provided
        if not any([app_name, app_secret, description, status, permissions]):
            console.print("[yellow]No updates provided. Use --help to see available options.[/yellow]")
            sys.exit(0)

        app = manager.update_application(
            app_id=app_id,
            app_name=app_name,
            app_secret=app_secret,
            description=description,
            status=status,
            permissions=permissions,
        )

        console.print("[green]✓[/green] Application updated successfully!")
        console.print(f"  App ID: {app.app_id}")
        console.print(f"  App Name: {app.app_name}")
        console.print(f"  Status: {app.status}")

    except (ValidationError, StorageError) as e:
        console.print(f"[red]✗[/red] Error: {e}", style="red")
        sys.exit(1)
    finally:
        manager.close()


@app.command()
@click.argument("app_id")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--hard", is_flag=True, help="Permanently delete (default is soft delete)")
def delete(app_id: str, force: bool, hard: bool) -> None:
    """Delete application configuration.

    By default, performs soft delete (marks as deleted).
    Use --hard for permanent deletion.

    Example:
        lark-service-cli app delete cli_abc123
        lark-service-cli app delete cli_abc123 --force
        lark-service-cli app delete cli_abc123 --hard --force
    """
    manager = get_app_manager()

    try:
        # Check if app exists
        app = manager.get_application(app_id)
        if not app:
            console.print(f"[red]✗[/red] Application not found: {app_id}", style="red")
            sys.exit(1)

        # Confirmation prompt
        if not force:
            delete_type = "permanently delete" if hard else "soft delete"
            confirm = click.confirm(
                f"Are you sure you want to {delete_type} application '{app.app_name}' ({app_id})?",
                default=False,
            )
            if not confirm:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                sys.exit(0)

        # Delete application
        manager.delete_application(app_id, soft_delete=not hard)

        delete_type = "permanently deleted" if hard else "soft deleted"
        console.print(f"[green]✓[/green] Application {delete_type} successfully!")
        console.print(f"  App ID: {app_id}")

    except (ValidationError, StorageError) as e:
        console.print(f"[red]✗[/red] Error: {e}", style="red")
        sys.exit(1)
    finally:
        manager.close()


@app.command()
@click.argument("app_id")
def enable(app_id: str) -> None:
    """Enable an application (set status to active).

    Example:
        lark-service-cli app enable cli_abc123
    """
    manager = get_app_manager()

    try:
        app = manager.update_application(app_id=app_id, status="active")

        console.print("[green]✓[/green] Application enabled successfully!")
        console.print(f"  App ID: {app.app_id}")
        console.print(f"  Status: {app.status}")

    except (ValidationError, StorageError) as e:
        console.print(f"[red]✗[/red] Error: {e}", style="red")
        sys.exit(1)
    finally:
        manager.close()


@app.command()
@click.argument("app_id")
def disable(app_id: str) -> None:
    """Disable an application (set status to inactive).

    Example:
        lark-service-cli app disable cli_abc123
    """
    manager = get_app_manager()

    try:
        app = manager.update_application(app_id=app_id, status="inactive")

        console.print("[green]✓[/green] Application disabled successfully!")
        console.print(f"  App ID: {app.app_id}")
        console.print(f"  Status: {app.status}")

    except (ValidationError, StorageError) as e:
        console.print(f"[red]✗[/red] Error: {e}", style="red")
        sys.exit(1)
    finally:
        manager.close()
