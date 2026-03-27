"""Клиент API MAX для отправки/чтения сообщений бота."""

from __future__ import annotations

import time
from typing import Any

import httpx
from django.conf import settings


class MaxApiError(RuntimeError):
    """Ошибка работы с API MAX."""


_REQUEST_TIMESTAMPS: list[float] = []


def _rate_limit(max_rps: int = 30) -> None:
    """Простое ограничение до max_rps запросов/сек в рамках процесса."""
    now = time.time()
    window_start = now - 1.0
    while _REQUEST_TIMESTAMPS and _REQUEST_TIMESTAMPS[0] < window_start:
        _REQUEST_TIMESTAMPS.pop(0)
    if len(_REQUEST_TIMESTAMPS) >= max_rps:
        sleep_for = 1.0 - (now - _REQUEST_TIMESTAMPS[0])
        if sleep_for > 0:
            time.sleep(sleep_for)
    _REQUEST_TIMESTAMPS.append(time.time())


def _base_url() -> str:
    return (getattr(settings, "MAX_API_BASE_URL", "") or "https://platform-api.max.ru").rstrip("/")


def _token() -> str:
    token = (getattr(settings, "MAX_BOT_TOKEN", "") or "").strip()
    if not token:
        raise MaxApiError("MAX_BOT_TOKEN не задан")
    return token


def _request(method: str, path: str, *, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
    _rate_limit(30)
    url = f"{_base_url()}{path}"
    headers = {
        "Authorization": _token(),
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    with httpx.Client(timeout=20.0) as client:
        response = client.request(method, url, params=params, json=json_body, headers=headers)
    if response.status_code >= 400:
        raise MaxApiError(f"MAX API {method} {path} failed: {response.status_code} {response.text[:500]}")
    if not response.content:
        return {}
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
    except Exception:
        return {"raw": response.text}


def send_message(*, user_id: int | None = None, chat_id: int | None = None, text: str = "", attachments: list[dict[str, Any]] | None = None, fmt: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if user_id is not None:
        params["user_id"] = user_id
    if chat_id is not None:
        params["chat_id"] = chat_id
    body: dict[str, Any] = {"text": (text or "")[:4000]}
    if attachments:
        body["attachments"] = attachments
    if fmt in ("markdown", "html"):
        body["format"] = fmt
    return _request("POST", "/messages", params=params, json_body=body)


def answer_callback(callback_id: str, *, notification: str | None = None, message: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if notification:
        body["notification"] = notification[:200]
    if message:
        body["message"] = message
    return _request("POST", "/answers", params={"callback_id": callback_id}, json_body=body)


def build_open_app_attachment(*, app_url: str, button_text: str = "Открыть") -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "open_app",
                        "text": button_text,
                        "url": app_url,
                    }
                ]
            ]
        },
    }


def get_message(message_id: str) -> dict[str, Any]:
    return _request("GET", f"/messages/{message_id}")


def list_messages(*, chat_id: int | None = None, message_ids: str | None = None, count: int = 50) -> dict[str, Any]:
    params: dict[str, Any] = {"count": max(1, min(int(count), 100))}
    if chat_id is not None:
        params["chat_id"] = chat_id
    if message_ids:
        params["message_ids"] = message_ids
    return _request("GET", "/messages", params=params)


def edit_message(*, message_id: str, text: str, attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"text": (text or "")[:4000]}
    if attachments is not None:
        body["attachments"] = attachments
    return _request("PUT", "/messages", params={"message_id": message_id}, json_body=body)


def delete_message(message_id: str) -> dict[str, Any]:
    return _request("DELETE", "/messages", params={"message_id": message_id})
