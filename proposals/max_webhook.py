"""Webhook MAX: обработка входящих событий и ответы бота."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .max_api_client import MaxApiError, answer_callback, build_open_app_attachment, send_message

logger = logging.getLogger(__name__)


def _mini_app_url(start_param: str | None = None) -> str:
    base = (getattr(settings, "MAX_MINIAPP_BASE_URL", "") or "").rstrip("/")
    if not base:
        return ""
    url = f"{base}/max-app/"
    if start_param:
        url = f"{url}?startapp={start_param}"
    return url


def _extract_message_payload(update: dict[str, Any]) -> tuple[int | None, int | None, str]:
    """Возвращает (chat_id, user_id, text) из update_type=message_created."""
    message = update.get("message") or {}
    body = message.get("body") or {}
    text = (body.get("text") or "").strip()
    sender = message.get("sender") or {}
    recipient = message.get("recipient") or {}
    user_id = sender.get("user_id")
    chat_id = recipient.get("chat_id") or recipient.get("id")
    return chat_id, user_id, text


def _send_open_app(chat_id: int | None, user_id: int | None, text: str = "") -> None:
    app_url = _mini_app_url(str(chat_id or user_id or ""))
    if not app_url:
        raise MaxApiError("MAX_MINIAPP_BASE_URL не задан")
    attachment = build_open_app_attachment(app_url=app_url, button_text="Открыть")
    send_message(
        user_id=user_id if user_id and not chat_id else None,
        chat_id=chat_id if chat_id else None,
        text=text or "Откройте мини-приложение по кнопке ниже.",
        attachments=[attachment],
    )


def _handle_message_created(update: dict[str, Any]) -> None:
    chat_id, user_id, text = _extract_message_payload(update)
    if not (chat_id or user_id):
        return
    low = (text or "").lower()
    if low in ("/start", "start", "/menu", "меню", "miniapp", "миниприложение"):
        _send_open_app(chat_id, user_id)
        return
    help_text = (
        "Доступные действия:\n"
        "• Открыть мини-приложение\n"
        "• Сформировать ТКП и договор\n\n"
        "Нажмите кнопку ниже."
    )
    _send_open_app(chat_id, user_id, text=help_text)


def _handle_callback(update: dict[str, Any]) -> None:
    callback = update.get("callback") or {}
    callback_id = callback.get("callback_id")
    payload = (callback.get("payload") or "").strip()
    chat_id = callback.get("chat_id")
    user_id = callback.get("user_id")
    if not callback_id:
        return
    if payload == "open_app":
        _send_open_app(chat_id, user_id)
        answer_callback(callback_id, notification="Открываю приложение")
        return
    answer_callback(callback_id, notification="Действие обработано")


@require_http_methods(["POST"])
@csrf_exempt
def max_webhook_view(request):
    """POST /max/webhook/ — webhook-only endpoint для MAX."""
    if not getattr(settings, "MAX_ENABLED", False):
        return HttpResponse(status=404)

    expected = getattr(settings, "MAX_WEBHOOK_SECRET", None)
    got = request.GET.get("secret") or request.headers.get("X-Webhook-Secret")
    if expected and got != expected:
        return HttpResponse(status=403)

    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    updates: list[dict[str, Any]]
    if isinstance(body, dict) and "updates" in body and isinstance(body["updates"], list):
        updates = [u for u in body["updates"] if isinstance(u, dict)]
    elif isinstance(body, dict):
        updates = [body]
    else:
        updates = []

    for update in updates:
        update_type = (update.get("update_type") or "").strip()
        try:
            if update_type == "message_created":
                _handle_message_created(update)
            elif update_type in ("message_callback", "callback"):
                _handle_callback(update)
        except Exception as exc:
            logger.exception("MAX webhook handling failed: %s", exc)

    return HttpResponse("ok")
