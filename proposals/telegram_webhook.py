"""
Вебхук Telegram и мост к OpenClaw: приём сообщений, формирование контекста, вызов /v1/responses, отправка ответа.
"""

import json
import logging
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .tkp_draft_service import get_draft_state_for_prompt, get_or_create_draft
from .tkp_reference import (
    TKP_DIALOG_RULES,
    format_tkp_reference_for_prompt,
    get_tkp_reference_data,
)

logger = logging.getLogger(__name__)

HISTORY_CACHE_KEY_PREFIX = 'tkp_telegram_history_'
HISTORY_MAX_MESSAGES = 20


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


def _get_history(user_id):
    return cache.get(HISTORY_CACHE_KEY_PREFIX + str(user_id)) or []


def _append_to_history(user_id, role, content):
    key = HISTORY_CACHE_KEY_PREFIX + str(user_id)
    hist = cache.get(key) or []
    hist.append({'role': role, 'content': content})
    if len(hist) > HISTORY_MAX_MESSAGES:
        hist = hist[-HISTORY_MAX_MESSAGES:]
    cache.set(key, hist, timeout=60 * 60 * 24)  # 24 ч


def _build_instructions(draft):
    ref_data = get_tkp_reference_data()
    ref_text = format_tkp_reference_for_prompt(ref_data)
    state_text = get_draft_state_for_prompt(draft)
    return ref_text + '\n\n## Текущий черновик ТКП\n' + state_text + '\n' + TKP_DIALOG_RULES


def _openresponses_tools():
    return [
        {
            'type': 'function',
            'function': {
                'name': 'tkp_set_field',
                'description': 'Записать значение поля черновика ТКП после ответа пользователя. Вызывать после того, как пользователь выбрал или ввёл значение.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'field': {'type': 'string', 'description': 'Имя поля: date, service_id, region_id, is_internal, internal_client, internal_price, client, room, s, srok, text'},
                        'value': {'type': 'string', 'description': 'Значение (строка или число в строке)'},
                    },
                    'required': ['field', 'value'],
                },
            },
        },
        {
            'type': 'function',
            'function': {
                'name': 'tkp_get_state',
                'description': 'Получить текущее состояние черновика (что заполнено, что пусто).',
                'parameters': {'type': 'object', 'properties': {}},
            },
        },
        {
            'type': 'function',
            'function': {
                'name': 'tkp_submit_draft',
                'description': 'Сохранить ТКП как черновик в перечне. Вызывать, когда пользователь просит сохранить черновик.',
                'parameters': {'type': 'object', 'properties': {}},
            },
        },
        {
            'type': 'function',
            'function': {
                'name': 'tkp_submit_final',
                'description': 'Сформировать итоговое ТКП (файлы + запись). Вызывать, когда пользователь просит сформировать/отправить ТКП.',
                'parameters': {'type': 'object', 'properties': {}},
            },
        },
    ]


def _run_tool(draft_id, tool_name, arguments):
    """Выполнить инструмент и вернуть строку результата для function_call_output."""
    from .tkp_draft_service import set_field, submit_draft, submit_final
    from .models import TkpTelegramDraft

    if tool_name == 'tkp_get_state':
        try:
            draft = TkpTelegramDraft.objects.get(pk=draft_id)
            return get_draft_state_for_prompt(draft)
        except TkpTelegramDraft.DoesNotExist:
            return 'Черновик не найден.'

    if tool_name == 'tkp_set_field':
        if not isinstance(arguments, dict):
            try:
                arguments = json.loads(arguments) if isinstance(arguments, str) else {}
            except json.JSONDecodeError:
                return 'Неверные аргументы.'
        field = arguments.get('field')
        value = arguments.get('value')
        if not field:
            return 'Не указано поле.'
        try:
            draft = TkpTelegramDraft.objects.get(pk=draft_id)
        except TkpTelegramDraft.DoesNotExist:
            return 'Черновик не найден.'
        ok, err = set_field(draft, field, value)
        return err if not ok else get_draft_state_for_prompt(draft)

    if tool_name == 'tkp_submit_draft':
        try:
            draft = TkpTelegramDraft.objects.get(pk=draft_id)
        except TkpTelegramDraft.DoesNotExist:
            return 'Черновик не найден.'
        from .api_views import _get_telegram_bot_user
        number, err = submit_draft(draft, user=_get_telegram_bot_user())
        return err if err else f'Черновик сохранён. Номер: {number}'

    if tool_name == 'tkp_submit_final':
        try:
            draft = TkpTelegramDraft.objects.get(pk=draft_id)
        except TkpTelegramDraft.DoesNotExist:
            return 'Черновик не найден.'
        from .api_views import _get_telegram_bot_user
        base_name, err = submit_final(draft, user=_get_telegram_bot_user())
        return err if err else f'ТКП сформировано. Документ: {base_name}'

    return f'Неизвестный инструмент: {tool_name}'


def _call_openclaw(user_id, instructions, input_messages, tools, draft_id):
    """
    Вызвать OpenClaw POST /v1/responses. Обработать function_call при наличии.
    Возвращает (reply_text, error).
    """
    base_url = (getattr(settings, 'OPENCLAW_GATEWAY_URL', '') or '').rstrip('/')
    api_key = getattr(settings, 'OPENCLAW_API_KEY', None)
    if not base_url or not api_key:
        return None, 'OpenClaw not configured (OPENCLAW_GATEWAY_URL, OPENCLAW_API_KEY)'

    url = f'{base_url}/v1/responses'
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    # input: массив сообщений в формате OpenResponses
    input_items = []
    for m in input_messages:
        input_items.append({
            'type': 'message',
            'role': m.get('role', 'user'),
            'content': m.get('content', ''),
        })

    payload = {
        'model': 'openclaw',
        'user': str(user_id),
        'instructions': instructions,
        'input': input_items,
        'tools': tools,
    }

    try:
        import httpx
    except ImportError:
        return None, 'httpx not installed (pip install httpx)'

    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        body = e.response.text
        try:
            err_obj = e.response.json()
            msg = err_obj.get('error', {}).get('message', body) or body
        except Exception:
            msg = body or str(e)
        logger.exception('OpenClaw request failed %s: %s', e.response.status_code, msg)
        return None, f'{e.response.status_code}: {msg}'
    except Exception as e:
        logger.exception('OpenClaw request failed: %s', e)
        return None, str(e)

    # Разбор ответа: output может содержать message и/или function_call
    output = data.get('output') or []
    reply_text = ''
    function_calls = []

    for item in output:
        if item.get('type') == 'message' and item.get('role') == 'assistant':
            reply_text = (item.get('content') or '').strip()
        if item.get('type') == 'function_call':
            function_calls.append(item)

    # Если есть function_call — выполнить и отправить ещё один запрос
    for fc in function_calls:
        call_id = fc.get('call_id', '')
        name = fc.get('name', '')
        args = fc.get('arguments', {})
        if isinstance(args, str):
            try:
                args = json.loads(args) if args else {}
            except json.JSONDecodeError:
                args = {}
        result = _run_tool(draft_id, name, args)
        # Повторный запрос: предыдущий input + ответ ассистента с function_call + function_call_output
        new_input = list(input_messages)
        new_input.append({'role': 'assistant', 'content': reply_text or '(вызов инструмента)'})
        new_input.append({
            'type': 'function_call_output',
            'call_id': call_id,
            'output': json.dumps({'result': result}),
        })
        new_items = []
        for m in new_input:
            if m.get('type') == 'function_call_output':
                new_items.append(m)
            else:
                new_items.append({'type': 'message', 'role': m.get('role', 'user'), 'content': m.get('content', '')})
        payload2 = {
            'model': 'openclaw',
            'user': str(user_id),
            'instructions': instructions,
            'input': new_items,
            'tools': tools,
        }
        try:
            r2 = httpx.post(url, json=payload2, headers=headers, timeout=60.0)
            r2.raise_for_status()
            data2 = r2.json()
        except Exception as e:
            logger.exception('OpenClaw follow-up failed: %s', e)
            return reply_text or result, None
        out2 = data2.get('output') or []
        reply_text = ''
        for item in out2:
            if item.get('type') == 'message' and item.get('role') == 'assistant':
                reply_text = (item.get('content') or '').strip()
        # Один цикл на один function_call; при нескольких вызовах можно повторить
        break

    return reply_text, None


@require_http_methods(['POST'])
@csrf_exempt
def telegram_webhook_view(request):
    """
    POST /telegram/webhook/ — приём обновлений от Telegram.
    Тело: JSON от Telegram Bot API (update). Извлекаем message.chat.id, message.from.id, message.text.
    """
    secret = request.GET.get('secret') or request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    expected_secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', None)
    if expected_secret and secret != expected_secret:
        return HttpResponse(status=403)

    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    # Только message с text
    message = body.get('message') or body.get('edited_message')
    if not message:
        return HttpResponse('ok')

    chat_id = message.get('chat', {}).get('id')
    from_user = message.get('from') or {}
    user_id = from_user.get('id')
    text = (message.get('text') or '').strip()

    if not chat_id or not user_id:
        return HttpResponse('ok')

    # /start — приветствие
    if text == '/start':
        _telegram_send_message(chat_id, 'Здравствуйте. Я помогу сформировать ТКП. Ответьте на несколько вопросов.')
        return HttpResponse('ok')

    if not text:
        return HttpResponse('ok')

    draft = get_or_create_draft(user_id, chat_id)
    instructions = _build_instructions(draft)
    history = _get_history(user_id)
    history.append({'role': 'user', 'content': text})
    _append_to_history(user_id, 'user', text)

    reply_text, err = _call_openclaw(
        user_id,
        instructions,
        history,
        _openresponses_tools(),
        draft.pk,
    )

    if err:
        _telegram_send_message(chat_id, f'Ошибка: {err[:500]}')
        return HttpResponse('ok')

    if reply_text:
        _append_to_history(user_id, 'assistant', reply_text)
        _telegram_send_message(chat_id, reply_text)

    return HttpResponse('ok')
