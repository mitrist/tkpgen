#!/usr/bin/env python3
"""
Long polling Telegram bot: getUpdates → POST to Django telegram-process → sendMessage.
No Django dependency; runs as standalone process. Requires TELEGRAM_BOT_TOKEN,
TELEGRAM_PROCESS_URL, TKP_TELEGRAM_API_KEY (optional: .env in cwd or parent).
"""

import logging
import os
import sys

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"
GET_UPDATES_TIMEOUT = 30


def load_dotenv() -> None:
    """Load .env from current directory or parent (simple KEY=value per line)."""
    for base in (os.getcwd(), os.path.dirname(os.getcwd())):
        path = os.path.join(base, ".env")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key:
                                os.environ.setdefault(key, value)
                logger.info("Loaded .env from %s", path)
            except OSError as e:
                logger.warning("Could not read .env from %s: %s", path, e)
            break


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.error("Missing required env: %s", name)
        sys.exit(1)
    return value


def get_updates(client: httpx.Client, token: str, offset: int) -> list[dict]:
    url = f"{TELEGRAM_API_BASE}{token}/getUpdates"
    params = {"offset": offset, "timeout": GET_UPDATES_TIMEOUT}
    try:
        r = client.get(url, params=params, timeout=GET_UPDATES_TIMEOUT + 10)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            logger.warning("getUpdates not ok: %s", data)
            return []
        return data.get("result") or []
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("getUpdates failed: %s", e)
        return []


def send_message(client: httpx.Client, token: str, chat_id: int, text: str) -> bool:
    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"
    try:
        r = client.post(url, json={"chat_id": chat_id, "text": text}, timeout=30)
        r.raise_for_status()
        return True
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("sendMessage failed for chat_id=%s: %s", chat_id, e)
        return False


def send_message_with_keyboard(
    client: httpx.Client, token: str, chat_id: int, text: str, inline_keyboard: list
) -> bool:
    """Send message with InlineKeyboardMarkup. inline_keyboard: [[(text, callback_data), ...], ...]."""
    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"
    try:
        markup = {
            "inline_keyboard": [
                [{"text": t, "callback_data": cb} for t, cb in row]
                for row in inline_keyboard
            ]
        }
        r = client.post(
            url,
            json={"chat_id": chat_id, "text": text or " ", "reply_markup": markup},
            timeout=30,
        )
        r.raise_for_status()
        return True
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("sendMessage with keyboard failed for chat_id=%s: %s", chat_id, e)
        return False


def send_document(client: httpx.Client, token: str, chat_id: int, file_path: str) -> bool:
    """Send file via sendDocument. file_path must be readable on this machine."""
    url = f"{TELEGRAM_API_BASE}{token}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": (os.path.basename(file_path), f, "application/octet-stream")}
            r = client.post(url, data={"chat_id": chat_id}, files=files, timeout=30)
        r.raise_for_status()
        return True
    except (httpx.HTTPError, ValueError, OSError) as e:
        logger.warning("sendDocument failed for chat_id=%s: %s", chat_id, e)
        return False


def send_webapp_button(
    client: httpx.Client, token: str, chat_id: int, text: str, button_text: str, web_app_url: str
) -> bool:
    """Send message with button that opens a Web App (Mini App)."""
    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"
    try:
        markup = {
            "inline_keyboard": [[{"text": button_text, "web_app": {"url": web_app_url}}]],
        }
        r = client.post(
            url,
            json={"chat_id": chat_id, "text": text or " ", "reply_markup": markup},
            timeout=30,
        )
        r.raise_for_status()
        return True
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("sendMessage with web_app failed for chat_id=%s: %s", chat_id, e)
        return False


def answer_callback_query(client: httpx.Client, token: str, callback_query_id: str) -> None:
    try:
        url = f"{TELEGRAM_API_BASE}{token}/answerCallbackQuery"
        client.post(url, json={"callback_query_id": callback_query_id}, timeout=5)
    except (httpx.HTTPError, ValueError):
        pass


def process_updates(
    client: httpx.Client,
    token: str,
    process_url: str,
    api_key: str,
    offset: int,
) -> int:
    updates = get_updates(client, token, offset)
    new_offset = offset
    for upd in updates:
        new_offset = max(new_offset, upd.get("update_id", 0) + 1)
        cq = upd.get("callback_query")
        if cq:
            answer_callback_query(client, token, cq.get("id", ""))
            msg = cq.get("message") or {}
            chat_id = msg.get("chat", {}).get("id")
            user_id = (cq.get("from") or {}).get("id")
            callback_data = (cq.get("data") or "").strip()
            if chat_id is None or user_id is None:
                continue
            payload = {"chat_id": chat_id, "user_id": user_id, "callback_data": callback_data}
            headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
            try:
                r = client.post(process_url, json=payload, headers=headers, timeout=60)
                r.raise_for_status()
                data = r.json()
                _send_response(client, token, chat_id, data)
            except (httpx.HTTPError, ValueError) as e:
                logger.warning("POST %s failed: %s", process_url, e)
                send_message(client, token, chat_id, "Не удалось получить ответ.")
            continue

        msg = upd.get("message") or upd.get("edited_message")
        if not msg or "text" not in msg:
            continue
        text = msg.get("text") or ""
        chat_id = msg.get("chat", {}).get("id")
        user_id = (msg.get("from") or {}).get("id")
        if chat_id is None or user_id is None:
            logger.warning("Skip update: missing chat_id or user_id")
            continue
        payload = {"chat_id": chat_id, "user_id": user_id, "text": text}
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        try:
            r = client.post(process_url, json=payload, headers=headers, timeout=60)
            r.raise_for_status()
            data = r.json()
            _send_response(client, token, chat_id, data)
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("POST %s failed: %s", process_url, e)
            send_message(client, token, chat_id, "Не удалось получить ответ.")
    return new_offset


def _send_response(client: httpx.Client, token: str, chat_id: int, data: dict) -> None:
    reply_text = data.get("reply_text")
    error_msg = data.get("error")
    inline_keyboard = data.get("inline_keyboard")
    document_path = data.get("document_path")
    web_app_url = data.get("web_app_url")
    web_app_button_text = data.get("web_app_button_text")
    if error_msg:
        send_message(client, token, chat_id, f"Ошибка: {error_msg[:500]}")
        return
    if document_path:
        send_document(client, token, chat_id, document_path)
    if web_app_url and web_app_button_text:
        send_webapp_button(client, token, chat_id, reply_text or " ", web_app_button_text, web_app_url)
    elif reply_text:
        if inline_keyboard:
            send_message_with_keyboard(client, token, chat_id, reply_text, inline_keyboard)
        else:
            send_message(client, token, chat_id, reply_text)
    elif not document_path:
        send_message(client, token, chat_id, "Не удалось получить ответ.")


def main() -> None:
    load_dotenv()
    token = get_env("TELEGRAM_BOT_TOKEN")
    process_url = get_env("TELEGRAM_PROCESS_URL")
    api_key = get_env("TKP_TELEGRAM_API_KEY")

    offset = 0
    logger.info("Starting polling; process_url=%s", process_url)
    with httpx.Client() as client:
        while True:
            try:
                offset = process_updates(client, token, process_url, api_key, offset)
            except Exception as e:
                logger.exception("Iteration error (continuing): %s", e)


if __name__ == "__main__":
    main()
