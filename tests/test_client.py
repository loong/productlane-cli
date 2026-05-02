from __future__ import annotations

import httpx
import pytest
import respx

from productlane_cli.client import ProductlaneAPIError, ProductlaneClient


@respx.mock
def test_list_threads_builds_expected_request() -> None:
    route = respx.get("https://productlane.com/api/v1/threads").mock(
        return_value=httpx.Response(200, json={"threads": [], "count": 0, "hasMore": False})
    )
    client = ProductlaneClient(token="test-token")

    data = client.list_threads(take=10, skip=5, state="NEW", issue_id="lin-1")

    assert data["threads"] == []
    assert route.called
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer test-token"
    assert dict(request.url.params) == {
        "take": "10",
        "skip": "5",
        "state": "NEW",
        "issueId": "lin-1",
    }


@respx.mock
def test_get_thread_can_include_conversation() -> None:
    route = respx.get("https://productlane.com/api/v1/threads/thread-1").mock(
        return_value=httpx.Response(200, json={"id": "thread-1"})
    )
    client = ProductlaneClient(token="test-token")

    data = client.get_thread("thread-1", include_conversation=True)

    assert data == {"id": "thread-1"}
    assert dict(route.calls.last.request.url.params) == {"includeConversation": "true"}


@respx.mock
def test_send_message_posts_content() -> None:
    route = respx.post("https://productlane.com/api/v1/threads/thread-1/messages").mock(
        return_value=httpx.Response(200, json={"messageId": "msg-1", "threadId": "thread-1"})
    )
    client = ProductlaneClient(token="test-token")

    data = client.send_message("thread-1", "hello")

    assert data["messageId"] == "msg-1"
    assert route.calls.last.request.content == b'{"content":"hello"}'


@respx.mock
def test_update_thread_patches_fields() -> None:
    route = respx.patch("https://productlane.com/api/v1/threads/thread-1").mock(
        return_value=httpx.Response(200, json={"id": "thread-1", "state": "PROCESSED"})
    )
    client = ProductlaneClient(token="test-token")

    data = client.update_thread("thread-1", {"state": "PROCESSED"})

    assert data["state"] == "PROCESSED"
    assert route.calls.last.request.content == b'{"state":"PROCESSED"}'


@respx.mock
def test_api_error_extracts_message() -> None:
    respx.get("https://productlane.com/api/v1/threads").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized", "code": "unauthorized"})
    )
    client = ProductlaneClient(token="bad-token")

    with pytest.raises(ProductlaneAPIError) as exc_info:
        client.list_threads()

    assert exc_info.value.status_code == 401
    assert "Unauthorized" in str(exc_info.value)
