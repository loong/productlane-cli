from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from productlane_cli.main import app

runner = CliRunner()


@respx.mock
def test_threads_list_json(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PRODUCTLANE_API_KEY", "test-token")
    respx.get("https://productlane.com/api/v1/threads").mock(
        return_value=httpx.Response(200, json={"threads": [], "count": 0, "hasMore": False})
    )

    result = runner.invoke(app, ["threads", "list", "--json"])

    assert result.exit_code == 0
    assert '"threads": []' in result.output


def test_threads_reply_requires_confirmation(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PRODUCTLANE_API_KEY", "test-token")

    result = runner.invoke(app, ["threads", "reply", "thread-1", "hello"], input="n\n")

    assert result.exit_code != 0
    assert "may be customer-visible" in result.output


def test_missing_token_exits_cleanly(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("PRODUCTLANE_API_KEY", raising=False)
    monkeypatch.delenv("PRODUCTLANE_TOKEN", raising=False)

    result = runner.invoke(app, ["threads", "list"])

    assert result.exit_code == 2
    assert "Set PRODUCTLANE_API_KEY" in result.output
