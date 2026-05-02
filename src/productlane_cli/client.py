from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://productlane.com/api/v1"


class ProductlaneError(RuntimeError):
    """Base error raised by productlane-cli."""


class MissingTokenError(ProductlaneError):
    """Raised when no Productlane API token is configured."""


class ProductlaneAPIError(ProductlaneError):
    """Raised when the Productlane API returns an error response."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        response: httpx.Response | None = None,
    ) -> None:
        self.status_code = status_code
        self.response = response
        super().__init__(f"Productlane API returned HTTP {status_code}: {message}")


@dataclass(frozen=True)
class ProductlaneClient:
    token: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> ProductlaneClient:
        token = os.getenv("PRODUCTLANE_API_KEY") or os.getenv("PRODUCTLANE_TOKEN")
        if not token:
            raise MissingTokenError(
                "Set PRODUCTLANE_API_KEY or PRODUCTLANE_TOKEN with your Productlane API key."
            )
        return cls(token=token, base_url=os.getenv("PRODUCTLANE_BASE_URL", DEFAULT_BASE_URL))

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> Any:
        url = self._url(path)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(method, url, headers=headers, params=params, json=json_body)

        if response.status_code >= 400:
            raise ProductlaneAPIError(
                response.status_code,
                _extract_error_message(response),
                response=response,
            )

        if not response.content:
            return None

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    def get(self, path: str, *, params: Mapping[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, json_body: Mapping[str, Any] | None = None) -> Any:
        return self.request("POST", path, json_body=json_body)

    def patch(self, path: str, *, json_body: Mapping[str, Any] | None = None) -> Any:
        return self.request("PATCH", path, json_body=json_body)

    def list_threads(
        self,
        *,
        take: int = 20,
        skip: int = 0,
        state: str | None = None,
        issue_id: str | None = None,
        project_id: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {"take": take, "skip": skip}
        if state:
            params["state"] = state
        if issue_id:
            params["issueId"] = issue_id
        if project_id:
            params["projectId"] = project_id
        return self.get("/threads", params=params)

    def get_thread(self, thread_id: str, *, include_conversation: bool = False) -> Any:
        params = {"includeConversation": "true" if include_conversation else "false"}
        return self.get(f"/threads/{thread_id}", params=params)

    def send_message(self, thread_id: str, content: str, *, channel_id: str | None = None) -> Any:
        body: dict[str, Any] = {"content": content}
        if channel_id:
            body["channelId"] = channel_id
        return self.post(f"/threads/{thread_id}/messages", json_body=body)

    def update_thread(self, thread_id: str, fields: Mapping[str, Any]) -> Any:
        return self.patch(f"/threads/{thread_id}", json_body=dict(fields))

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        base = self.base_url.rstrip("/")
        clean_path = path if path.startswith("/") else f"/{path}"
        return f"{base}{clean_path}"


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return response.text.strip() or response.reason_phrase

    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("error")
        code = payload.get("code")
        if message and code:
            return f"{message} ({code})"
        if message:
            return str(message)
    return json.dumps(payload)
