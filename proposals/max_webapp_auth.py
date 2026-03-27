"""Валидация WebAppData MAX и выдача токена сессии mini app."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache


REPLAY_PREFIX = "max_initdata_qid_"
APP_TOKEN_SALT = "max-app-auth-v1"


def _parse_webapp_data(raw: str) -> list[tuple[str, str]]:
    # keep_blank_values важно для корректной подписи
    return parse_qsl(raw or "", keep_blank_values=True)


def validate_max_init_data(init_data: str) -> dict[str, Any] | None:
    """
    Проверить initData MAX по алгоритму HMAC-SHA256 из документации.
    Возвращает распарсенные параметры (dict) или None.
    """
    if not init_data or not isinstance(init_data, str):
        return None
    bot_token = (getattr(settings, "MAX_BOT_TOKEN", "") or "").strip()
    if not bot_token:
        return None

    pairs = _parse_webapp_data(init_data)
    if not pairs:
        return None

    # Каждый ключ должен встречаться ровно один раз
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        return None

    params: dict[str, str] = dict(pairs)
    original_hash = params.pop("hash", None)
    if not original_hash:
        return None

    sorted_items = sorted(params.items(), key=lambda kv: kv[0])
    launch_params = "\n".join(f"{k}={v}" for k, v in sorted_items)

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    signature = hmac.new(secret_key, launch_params.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, original_hash):
        return None

    result: dict[str, Any] = dict(params)
    if "user" in result:
        try:
            result["user"] = json.loads(result["user"])
        except Exception:
            pass
    if "chat" in result:
        try:
            result["chat"] = json.loads(result["chat"])
        except Exception:
            pass
    return result


def validate_ttl_and_replay(validated: dict[str, Any]) -> tuple[bool, str | None]:
    """Проверить auth_date и защиту от повторного query_id."""
    now = int(time.time())
    ttl = int(getattr(settings, "MAX_INITDATA_TTL_SECONDS", 86400))
    auth_date = validated.get("auth_date")
    try:
        auth_ts = int(auth_date)
    except Exception:
        return False, "auth_date отсутствует или некорректен"

    if auth_ts > now + 120:
        return False, "auth_date из будущего"
    if now - auth_ts > ttl:
        return False, "initData просрочен"

    query_id = (validated.get("query_id") or "").strip()
    if query_id:
        cache_key = REPLAY_PREFIX + query_id
        if cache.get(cache_key):
            return False, "повторный query_id"
        cache.set(cache_key, "1", timeout=max(ttl, 60))
    return True, None


def get_or_create_max_user(validated: dict[str, Any]):
    """Связать MAX user.id с локальным пользователем Django."""
    user_data = validated.get("user") if isinstance(validated.get("user"), dict) else {}
    max_user_id = user_data.get("id")
    if not max_user_id:
        raise ValueError("MAX user.id отсутствует")

    User = get_user_model()
    username = f"max_{max_user_id}"
    defaults = {
        "first_name": (user_data.get("first_name") or "")[:150],
        "last_name": (user_data.get("last_name") or "")[:150],
        "email": "",
        "is_active": True,
    }
    user, created = User.objects.get_or_create(username=username, defaults=defaults)
    changed = False
    first_name = (user_data.get("first_name") or "")[:150]
    last_name = (user_data.get("last_name") or "")[:150]
    if first_name and user.first_name != first_name:
        user.first_name = first_name
        changed = True
    if last_name and user.last_name != last_name:
        user.last_name = last_name
        changed = True
    if created:
        user.set_unusable_password()
        changed = True
    if changed:
        user.save()
    return user


def issue_app_token(*, user_id: int, max_user_id: str, chat_id: str | None = None) -> str:
    payload = {"u": int(user_id), "m": str(max_user_id), "c": str(chat_id or "")}
    return signing.dumps(payload, salt=APP_TOKEN_SALT)


def verify_app_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        data = signing.loads(token, salt=APP_TOKEN_SALT, max_age=int(getattr(settings, "MAX_INITDATA_TTL_SECONDS", 86400)))
        if not isinstance(data, dict) or "u" not in data or "m" not in data:
            return None
        return data
    except Exception:
        return None
