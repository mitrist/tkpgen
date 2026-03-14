"""
Telegram Mini App для ТКП: веб-форма в WebView, валидация initData, отправка и скачивание файла.
"""

import hashlib
import hmac
import json
import logging
import secrets
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .tkp_reference import get_tkp_reference_data
from .tkp_draft_service import get_or_create_draft, set_field, submit_final
from .models import TkpTelegramDraft

logger = logging.getLogger(__name__)

DOWNLOAD_TOKEN_PREFIX = 'tkp_miniapp_download_'
DOWNLOAD_TOKEN_TTL = 600  # 10 минут


def validate_init_data(init_data_str):
    """
    Проверка подписи initData от Telegram Mini App.
    Возвращает dict с полями (user, auth_date, ...) или None при неверной подписи.
    """
    if not init_data_str or not isinstance(init_data_str, str):
        return None
    token = (getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or '').strip()
    if not token:
        return None
    try:
        params = dict(parse_qsl(init_data_str, keep_blank_values=True))
        received_hash = params.pop('hash', None)
        if not received_hash:
            return None
        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(params.items()))
        secret_key = hmac.new(
            token.encode(),
            b'WebAppData',
            hashlib.sha256,
        ).digest()
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        if computed_hash != received_hash:
            return None
        # Парсим user из JSON если есть
        if 'user' in params:
            try:
                params['user'] = json.loads(params['user'])
            except json.JSONDecodeError:
                pass
        return params
    except Exception as e:
        logger.debug('initData validation failed: %s', e)
        return None


def _draft_from_form_data(telegram_user_id, telegram_chat_id, data):
    """
    Создать черновик и заполнить из словаря data (поля как в форме).
    Возвращает (draft, error).
    """
    draft = get_or_create_draft(telegram_user_id, telegram_chat_id)
    draft.payload = draft.payload or {}
    draft.payload['internal_choice_set'] = True
    draft.save(update_fields=['payload', 'updated_at'])

    is_internal = data.get('is_internal')
    if is_internal is not None:
        draft.is_internal = bool(is_internal)
        draft.save(update_fields=['is_internal', 'updated_at'])
        if draft.is_internal:
            set_field(draft, 'region_id', None)
            set_field(draft, 'client', '')
            set_field(draft, 's', '')
        else:
            set_field(draft, 'internal_client', '')
            set_field(draft, 'internal_price', '')

    fields = [
        ('date', 'date'),
        ('service_id', 'service_id'),
        ('region_id', 'region_id'),
        ('internal_client', 'internal_client'),
        ('internal_price', 'internal_price'),
        ('client', 'client'),
        ('room', 'room'),
        ('s', 's'),
        ('srok', 'srok'),
        ('text', 'text'),
    ]
    for form_key, field_name in fields:
        val = data.get(form_key)
        if val is None or val == '':
            if field_name in ('internal_price', 'internal_client', 'client', 'room', 's', 'srok', 'text'):
                ok, err = set_field(draft, field_name, '')
                if not ok:
                    return None, err
            elif field_name == 'date':
                draft.date = None
                draft.save(update_fields=['date', 'updated_at'])
            elif field_name in ('service_id', 'region_id'):
                setattr(draft, field_name, None)
                draft.save(update_fields=[field_name, 'updated_at'])
            continue
        if field_name == 'internal_price' and val != '':
            try:
                val = float(val)
            except (TypeError, ValueError):
                val = str(val)
        ok, err = set_field(draft, field_name, val)
        if not ok:
            return None, err
    return draft, None


@require_http_methods(['GET'])
def miniapp_page_view(request):
    """Страница Mini App: форма ТКП. GET /tkp-app/"""
    return render(request, 'proposals/tkp_miniapp.html', {})


@require_http_methods(['GET'])
@csrf_exempt
def miniapp_reference_view(request):
    """GET /tkp-app/reference/ — справочники для формы (без авторизации, только для Mini App)."""
    data = get_tkp_reference_data()
    # Добавляем value для internal_clients и srok (для option value)
    from .choices import INTERNAL_CLIENT_CHOICES, SROK_CHOICES
    data['internal_clients'] = [{'value': v, 'label': l} for v, l in INTERNAL_CLIENT_CHOICES if v]
    data['srok_choices'] = [{'value': v, 'label': l} for v, l in SROK_CHOICES if v]
    return JsonResponse(data)


@require_http_methods(['POST'])
@csrf_exempt
def miniapp_submit_view(request):
    """
    POST /tkp-app/submit/ — принять данные формы, сформировать ТКП, вернуть download_url.
    Тело: JSON { "initData": "<строка из Telegram.WebApp.initData>", "start_param": "<опционально chat_id>", ...поля формы }.
    """
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    init_data_str = body.get('initData')
    parsed = validate_init_data(init_data_str)
    if not parsed:
        return JsonResponse({'error': 'Invalid or missing initData'}, status=401)
    user_obj = parsed.get('user')
    if not user_obj or not isinstance(user_obj, dict):
        return JsonResponse({'error': 'User not found in initData'}, status=401)
    telegram_user_id = str(user_obj.get('id', ''))
    if not telegram_user_id:
        return JsonResponse({'error': 'User id not found'}, status=401)
    start_param = (body.get('start_param') or '').strip()
    telegram_chat_id = start_param if start_param else telegram_user_id

    draft, err = _draft_from_form_data(telegram_user_id, telegram_chat_id, body)
    if err:
        return JsonResponse({'error': err}, status=400)
    from .api_views import _get_telegram_bot_user
    base_name, err = submit_final(draft, user=_get_telegram_bot_user())
    if err:
        return JsonResponse({'error': err}, status=400)
    out_dir = Path(getattr(settings, 'TKP_OUTPUT_DIR', Path(settings.BASE_DIR) / 'TKP_output'))
    pdf_path = out_dir / f'{base_name}.pdf'
    if not pdf_path.exists():
        docx_path = out_dir / f'{base_name}.docx'
        file_path = docx_path if docx_path.exists() else None
    else:
        file_path = pdf_path
    if not file_path or not file_path.exists():
        return JsonResponse({'error': 'Файл не найден после генерации'}, status=500)
    token = DOWNLOAD_TOKEN_PREFIX + secrets.token_urlsafe(24)
    cache.set(token, str(file_path), timeout=DOWNLOAD_TOKEN_TTL)
    # URL для скачивания (относительный путь; фронт подставит свой origin при необходимости)
    download_url = f'/tkp-app/download/{token}/'
    return JsonResponse({'download_url': download_url, 'base_name': base_name})


@require_http_methods(['GET'])
def miniapp_download_view(request, token):
    """GET /tkp-app/download/<token>/ — отдать файл по одноразовому токену."""
    if not token or not token.startswith(DOWNLOAD_TOKEN_PREFIX):
        return HttpResponse('Invalid token', status=404)
    file_path = cache.get(token)
    if not file_path:
        return HttpResponse('Link expired', status=404)
    cache.delete(token)
    path = Path(file_path)
    if not path.exists():
        return HttpResponse('File not found', status=404)
    content_type = 'application/pdf' if path.suffix.lower() == '.pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    try:
        content = path.read_bytes()
    except OSError:
        return HttpResponse('File not found', status=404)
    response = HttpResponse(content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{path.name}"'
    response['Content-Length'] = len(content)
    return response
