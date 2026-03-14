"""
Вебхук Telegram-бота ТКП: приём сообщений и callback от кнопок,
пошаговое заполнение черновика (инлайн-кнопки + текст), отправка сформированного файла.
Без OpenClaw; логика в telegram_bot_logic.
"""

import json
import logging
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import telegram_bot_logic as bot_logic

logger = logging.getLogger(__name__)


def _telegram_send_message(chat_id, text, token=None):
    """Отправить сообщение в Telegram (sendMessage). Текст обрезается до 4096 символов."""
    token = token or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token:
        logger.warning('TELEGRAM_BOT_TOKEN not set')
        return False
    if not text or not text.strip():
        return True
    text = text.strip()[:4096]
    try:
        import httpx
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        r = httpx.post(url, json={'chat_id': chat_id, 'text': text}, timeout=15.0)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.exception('Telegram sendMessage failed: %s', e)
        return False


def _telegram_send_message_with_keyboard(chat_id, text, inline_keyboard, token=None):
    """Отправить сообщение с инлайн-кнопками (reply_markup: InlineKeyboardMarkup)."""
    token = token or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token:
        logger.warning('TELEGRAM_BOT_TOKEN not set')
        return False
    text = (text or '').strip()[:4096] or ' '
    try:
        import httpx
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        # inline_keyboard: list of list of {text, callback_data}
        markup = {
            'inline_keyboard': [
                [{'text': btn_text, 'callback_data': cb_data} for btn_text, cb_data in row]
                for row in (inline_keyboard or [])
            ],
        }
        payload = {'chat_id': chat_id, 'text': text, 'reply_markup': markup}
        r = httpx.post(url, json=payload, timeout=15.0)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.exception('Telegram sendMessage with keyboard failed: %s', e)
        return False


def _telegram_send_document(chat_id, file_path, token=None, caption=None):
    """Отправить файл в Telegram (sendDocument). file_path — путь к файлу на диске."""
    token = token or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token:
        logger.warning('TELEGRAM_BOT_TOKEN not set')
        return False
    path = __import__('pathlib').Path(file_path)
    if not path.exists():
        logger.warning('Document file not found: %s', file_path)
        return False
    try:
        import httpx
        url = f'https://api.telegram.org/bot{token}/sendDocument'
        data = {'chat_id': chat_id}
        if caption:
            data['caption'] = caption[:1024]
        with open(path, 'rb') as f:
            files = {'document': (path.name, f, 'application/octet-stream')}
            r = httpx.post(url, data=data, files=files, timeout=30.0)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.exception('Telegram sendDocument failed: %s', e)
        return False


def _telegram_answer_callback_query(callback_query_id, token=None, text=None):
    """Ответить на callback_query (убрать «часики» у кнопки)."""
    token = token or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token:
        return
    try:
        import httpx
        url = f'https://api.telegram.org/bot{token}/answerCallbackQuery'
        payload = {'callback_query_id': callback_query_id}
        if text:
            payload['text'] = str(text)[:200]
        httpx.post(url, json=payload, timeout=5.0)
    except Exception as e:
        logger.debug('answerCallbackQuery failed: %s', e)


def process_telegram_message(chat_id, user_id, text=None, callback_data=None):
    """
    Обработка сообщения или нажатия кнопки. Возвращает (reply_text, error, inline_keyboard, document_path).
    Для совместимости с api telegram_process_view: вызывающий код может отправлять reply сам.
    """
    if callback_data is not None:
        result = bot_logic.process_callback(chat_id, user_id, callback_data)
    else:
        result = bot_logic.process_text_message(chat_id, user_id, text or '')
    return (
        result.get('reply_text'),
        result.get('error'),
        result.get('inline_keyboard'),
        result.get('document_path'),
    )


@require_http_methods(['POST'])
@csrf_exempt
def telegram_webhook_view(request):
    """
    POST /telegram/webhook/ — приём обновлений от Telegram (message и callback_query).
    """
    secret = request.GET.get('secret') or request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    expected_secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', None)
    if expected_secret and secret != expected_secret:
        return HttpResponse(status=403)

    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    # Обработка нажатия инлайн-кнопки
    callback_query = body.get('callback_query')
    if callback_query:
        cq_id = callback_query.get('id')
        from_user = callback_query.get('from') or {}
        user_id = from_user.get('id')
        message = callback_query.get('message') or {}
        chat_id = message.get('chat', {}).get('id')
        data = (callback_query.get('data') or '').strip()
        if not chat_id or not user_id:
            return HttpResponse('ok')
        _telegram_answer_callback_query(cq_id)
        reply_text, err, keyboard, document_path = process_telegram_message(
            chat_id, user_id, callback_data=data,
        )
        if err:
            _telegram_send_message(chat_id, f'Ошибка: {err[:500]}')
        elif document_path:
            _telegram_send_document(chat_id, document_path)
            if reply_text:
                _telegram_send_message(chat_id, reply_text)
        elif reply_text:
            if keyboard:
                _telegram_send_message_with_keyboard(chat_id, reply_text, keyboard)
            else:
                _telegram_send_message(chat_id, reply_text)
        return HttpResponse('ok')

    # Обычное сообщение с текстом
    message = body.get('message') or body.get('edited_message')
    if not message:
        return HttpResponse('ok')

    chat_id = message.get('chat', {}).get('id')
    from_user = message.get('from') or {}
    user_id = from_user.get('id')
    text = (message.get('text') or '').strip()

    if not chat_id or not user_id:
        return HttpResponse('ok')

    reply_text, err, keyboard, document_path = process_telegram_message(chat_id, user_id, text=text)
    if err:
        _telegram_send_message(chat_id, f'Ошибка: {err[:500]}')
    elif document_path:
        _telegram_send_document(chat_id, document_path)
        if reply_text:
            _telegram_send_message(chat_id, reply_text)
    elif reply_text:
        if keyboard:
            _telegram_send_message_with_keyboard(chat_id, reply_text, keyboard)
        else:
            _telegram_send_message(chat_id, reply_text)

    return HttpResponse('ok')
