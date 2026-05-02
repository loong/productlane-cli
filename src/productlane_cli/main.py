from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from productlane_cli import __version__
from productlane_cli.client import MissingTokenError, ProductlaneAPIError, ProductlaneClient

app = typer.Typer(
    help="A small command-line client for the Productlane REST API.",
    no_args_is_help=True,
)
threads_app = typer.Typer(help="Work with Productlane threads/tickets.", no_args_is_help=True)
raw_app = typer.Typer(help="Make raw authenticated Productlane API requests.", no_args_is_help=True)
app.add_typer(threads_app, name="threads")
app.add_typer(raw_app, name="raw")
console = Console()

STATE_VALUES = ["NEW", "PROCESSED", "COMPLETED", "SNOOZED", "UNSNOOZED"]
PAIN_VALUES = ["UNKNOWN", "LOW", "MEDIUM", "HIGH"]


def version_callback(value: bool) -> None:
    if value:
        console.print(f"productlane-cli {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, help="Show version and exit."),
    ] = False,
) -> None:
    _ = version


@threads_app.command("list")
def list_threads(
    state: Annotated[str | None, typer.Option(help="Filter by thread state.")] = None,
    issue_id: Annotated[
        str | None,
        typer.Option("--issue-id", help="Filter by Linear issue ID."),
    ] = None,
    project_id: Annotated[
        str | None,
        typer.Option("--project-id", help="Filter by project ID."),
    ] = None,
    take: Annotated[int, typer.Option(min=1, max=100, help="Number of threads to fetch.")] = 20,
    skip: Annotated[int, typer.Option(min=0, help="Number of threads to skip.")] = 0,
    json_output: Annotated[bool, typer.Option("--json", help="Print raw JSON response.")] = False,
) -> None:
    """List Productlane threads/tickets."""
    validate_choice("state", state, STATE_VALUES)
    client = get_client()
    data = run_api_call(
        lambda: client.list_threads(
            take=take,
            skip=skip,
            state=state,
            issue_id=issue_id,
            project_id=project_id,
        )
    )
    if json_output:
        print_json(data)
        return
    print_threads_table(data)


@threads_app.command("get")
def get_thread(
    thread_id: Annotated[str, typer.Argument(help="Productlane thread ID.")],
    conversation: Annotated[
        bool,
        typer.Option("--conversation", "-c", help="Include conversation messages."),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print raw JSON response.")] = False,
) -> None:
    """Fetch one Productlane thread."""
    client = get_client()
    data = run_api_call(lambda: client.get_thread(thread_id, include_conversation=conversation))
    if json_output:
        print_json(data)
        return
    print_thread_detail(data)


@threads_app.command("reply")
def reply_thread(
    thread_id: Annotated[str, typer.Argument(help="Productlane thread ID.")],
    content: Annotated[str, typer.Argument(help="Message content to send.")],
    channel_id: Annotated[
        str | None,
        typer.Option("--channel-id", help="Slack channel ID override."),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation for potentially customer-visible reply.",
        ),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print raw JSON response.")] = False,
) -> None:
    """Send a message to a Productlane thread.

    Productlane documents this endpoint as sending an email or Slack message to a thread,
    so treat it as customer-visible unless your workspace confirms otherwise.
    """
    if not yes:
        console.print(
            "[yellow]Warning:[/yellow] Productlane documents this as sending an email or Slack "
            "message to the thread. It may be customer-visible."
        )
        typer.confirm("Send this message?", abort=True)

    client = get_client()
    data = run_api_call(lambda: client.send_message(thread_id, content, channel_id=channel_id))
    if json_output:
        print_json(data)
        return
    console.print("[green]Message sent.[/green]")
    print_json(data)


@threads_app.command("update")
def update_thread(
    thread_id: Annotated[str, typer.Argument(help="Productlane thread ID.")],
    title: Annotated[str | None, typer.Option(help="Set thread title.")] = None,
    text: Annotated[str | None, typer.Option(help="Set thread text/content.")] = None,
    state: Annotated[str | None, typer.Option(help="Set thread state.")] = None,
    pain_level: Annotated[str | None, typer.Option("--pain-level", help="Set pain level.")] = None,
    assignee_id: Annotated[
        str | None,
        typer.Option("--assignee-id", help="Set assignee ID. Use empty string to unassign."),
    ] = None,
    project_id: Annotated[str | None, typer.Option("--project-id", help="Set project ID.")] = None,
    contact_id: Annotated[str | None, typer.Option("--contact-id", help="Set contact ID.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print raw JSON response.")] = False,
) -> None:
    """Patch selected fields on a Productlane thread."""
    validate_choice("state", state, STATE_VALUES)
    validate_choice("pain-level", pain_level, PAIN_VALUES)

    fields: dict[str, Any] = {}
    for key, value in {
        "title": title,
        "text": text,
        "state": state,
        "painLevel": pain_level,
        "projectId": project_id,
        "contactId": contact_id,
    }.items():
        if value is not None:
            fields[key] = value
    if assignee_id is not None:
        fields["assigneeId"] = assignee_id or None

    if not fields:
        console.print("[red]No fields to update. Pass at least one update option.[/red]")
        raise typer.Exit(2)

    client = get_client()
    data = run_api_call(lambda: client.update_thread(thread_id, fields))
    if json_output:
        print_json(data)
        return
    console.print("[green]Thread updated.[/green]")
    print_thread_detail(data)


@raw_app.command("get")
def raw_get(
    path: Annotated[str, typer.Argument(help="API path, e.g. /threads?take=5")],
) -> None:
    """Make an authenticated raw GET request."""
    client = get_client()
    print_json(run_api_call(lambda: client.get(path)))


@raw_app.command("post")
def raw_post(
    path: Annotated[str, typer.Argument(help="API path, e.g. /threads")],
    body: Annotated[str, typer.Argument(help="JSON request body.")],
) -> None:
    """Make an authenticated raw POST request."""
    payload = parse_json_body(body)
    client = get_client()
    print_json(run_api_call(lambda: client.post(path, json_body=payload)))


@raw_app.command("patch")
def raw_patch(
    path: Annotated[str, typer.Argument(help="API path, e.g. /threads/<id>")],
    body: Annotated[str, typer.Argument(help="JSON request body.")],
) -> None:
    """Make an authenticated raw PATCH request."""
    payload = parse_json_body(body)
    client = get_client()
    print_json(run_api_call(lambda: client.patch(path, json_body=payload)))


def get_client() -> ProductlaneClient:
    try:
        return ProductlaneClient.from_env()
    except MissingTokenError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc


def run_api_call(callback):  # type: ignore[no-untyped-def]
    try:
        return callback()
    except ProductlaneAPIError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


def validate_choice(name: str, value: str | None, choices: list[str]) -> None:
    if value is not None and value not in choices:
        console.print(f"[red]Invalid {name}: {value}. Expected one of: {', '.join(choices)}[/red]")
        raise typer.Exit(2)


def parse_json_body(body: str) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON body: {exc}[/red]")
        raise typer.Exit(2) from exc
    if not isinstance(payload, dict):
        console.print("[red]JSON body must be an object.[/red]")
        raise typer.Exit(2)
    return payload


def print_json(data: Any) -> None:
    console.print_json(json.dumps(data, indent=2, sort_keys=True, default=str))


def print_threads_table(data: Any) -> None:
    threads = data.get("threads", []) if isinstance(data, dict) else []
    table = Table(title="Productlane Threads")
    table.add_column("ID", overflow="fold")
    table.add_column("State")
    table.add_column("Pain")
    table.add_column("Title", overflow="fold")
    table.add_column("Contact")
    table.add_column("Updated")

    for thread in threads:
        contact = thread.get("contact") or {}
        contact_label = contact.get("email") or contact.get("name") or ""
        table.add_row(
            str(thread.get("id", "")),
            str(thread.get("state", "")),
            str(thread.get("painLevel", "")),
            str(thread.get("title") or thread.get("text", ""))[:120],
            str(contact_label),
            str(thread.get("updatedAt") or ""),
        )
    console.print(table)
    if isinstance(data, dict):
        console.print(
            f"count={data.get('count', len(threads))} hasMore={data.get('hasMore', False)} "
            f"nextPage={data.get('nextPage')}"
        )


def print_thread_detail(thread: Any) -> None:
    if not isinstance(thread, dict):
        print_json(thread)
        return
    console.print(f"[bold]{thread.get('title') or '(untitled)'}[/bold]")
    console.print(f"ID: {thread.get('id')}")
    console.print(f"State: {thread.get('state')}  Pain: {thread.get('painLevel')}")
    console.print(f"Origin: {thread.get('origin')}  Updated: {thread.get('updatedAt')}")
    contact = thread.get("contact") or {}
    if contact:
        console.print(f"Contact: {contact.get('name') or ''} <{contact.get('email') or ''}>")
    company = thread.get("company") or {}
    if company:
        console.print(f"Company: {company.get('name') or company.get('id')}")
    console.print("\n[bold]Text[/bold]")
    console.print(thread.get("text") or "")

    conversation = thread.get("conversation")
    if conversation:
        console.print("\n[bold]Conversation[/bold]")
        for item in conversation:
            if not isinstance(item, dict):
                console.print(str(item))
                continue
            author = (
                item.get("author")
                or item.get("from")
                or item.get("sender")
                or item.get("type")
                or "message"
            )
            created = item.get("createdAt") or item.get("timestamp") or ""
            content = item.get("content") or item.get("text") or item.get("body") or ""
            console.rule(f"{author} {created}")
            console.print(content)


if __name__ == "__main__":
    app()
