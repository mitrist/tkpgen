"""API для OpenClaw/Telegram: справочники ТКП и операции с черновиком."""

import json
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .tkp_draft_service import (
    build_proposal_data_from_draft,
    get_draft_state_for_prompt,
    get_or_create_draft,
    set_field,
    submit_draft,
    submit_final,
)
from .tkp_reference import get_tkp_reference_data


def _get_api_key(request):
    """Извлечь API-ключ из заголовка X-API-Key или Authorization: Bearer."""
    key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '')
    if key.lower().startswith('bearer '):
        key = key[7:].strip()
    return key


def _api_key_required(view_func):
    """Декоратор: требовать валидный TKP_TELEGRAM_API_KEY."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        expected = getattr(settings, 'TKP_TELEGRAM_API_KEY', None)
        if not expected:
            return JsonResponse({'error': 'API key not configured'}, status=500)
        key = _get_api_key(request)
        if key != expected:
            return JsonResponse({'error': 'Invalid or missing API key'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapped


@require_http_methods(['GET'])
@csrf_exempt
@_api_key_required
def tkp_reference_view(request):
    """GET api/tkp/reference/ — JSON справочников для контекста OpenClaw."""
    data = get_tkp_reference_data()
    return JsonResponse(data)


@require_http_methods(['POST'])
@csrf_exempt
@_api_key_required
def tkp_draft_create_view(request):
    """POST api/tkp/draft/ — создать/получить черновик. Тело: {"telegram_user_id", "telegram_chat_id"}."""
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    user_id = body.get('telegram_user_id')
    chat_id = body.get('telegram_chat_id')
    if not user_id or not chat_id:
        return JsonResponse({'error': 'telegram_user_id and telegram_chat_id required'}, status=400)
    draft = get_or_create_draft(str(user_id), str(chat_id))
    state_text = get_draft_state_for_prompt(draft)
    filled = []
    if draft.date:
        filled.append('date')
    if draft.service_id:
        filled.append('service_id')
    if draft.region_id:
        filled.append('region_id')
    if draft.is_internal:
        if draft.internal_client:
            filled.append('internal_client')
        if draft.internal_price is not None:
            filled.append('internal_price')
    else:
        if draft.client:
            filled.append('client')
        if draft.s:
            filled.append('s')
    if draft.srok:
        filled.append('srok')
    if draft.room:
        filled.append('room')
    if draft.text:
        filled.append('text')
    return JsonResponse({
        'draft_id': draft.pk,
        'state_summary': state_text,
        'filled_fields': filled,
    })


@require_http_methods(['POST'])
@csrf_exempt
@_api_key_required
def tkp_draft_set_field_view(request, draft_id):
    """POST api/tkp/draft/<id>/set-field/ — установить поле. Тело: {"field", "value"}."""
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    field = body.get('field')
    value = body.get('value')
    if not field:
        return JsonResponse({'error': 'field required'}, status=400)
    from .models import TkpTelegramDraft
    try:
        draft = TkpTelegramDraft.objects.get(pk=draft_id)
    except TkpTelegramDraft.DoesNotExist:
        return JsonResponse({'error': 'Draft not found'}, status=404)
    ok, err = set_field(draft, field, value)
    if not ok:
        return JsonResponse({'error': err}, status=400)
    return JsonResponse({
        'draft_id': draft.pk,
        'state_summary': get_draft_state_for_prompt(draft),
    })


def _get_telegram_bot_user():
    """Опционально вернуть User для created_by по настройке TKP_TELEGRAM_BOT_USER_ID."""
    user_id = getattr(settings, 'TKP_TELEGRAM_BOT_USER_ID', None)
    if user_id is None or user_id == '':
        return None
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        return User.objects.get(pk=int(user_id))
    except (ValueError, User.DoesNotExist):
        return None


@require_http_methods(['POST'])
@csrf_exempt
@_api_key_required
def tkp_draft_submit_draft_view(request, draft_id):
    """POST api/tkp/draft/<id>/submit-draft/ — сохранить как черновик в перечне ТКП."""
    from .models import TkpTelegramDraft
    try:
        draft = TkpTelegramDraft.objects.get(pk=draft_id)
    except TkpTelegramDraft.DoesNotExist:
        return JsonResponse({'error': 'Draft not found'}, status=404)
    user = _get_telegram_bot_user()
    number, err = submit_draft(draft, user=user)
    if err:
        return JsonResponse({'error': err}, status=400)
    return JsonResponse({'number': number, 'status': 'draft'})


@require_http_methods(['POST'])
@csrf_exempt
@_api_key_required
def tkp_draft_submit_final_view(request, draft_id):
    """POST api/tkp/draft/<id>/submit-final/ — сформировать итоговое ТКП (файлы + запись)."""
    from .models import TkpTelegramDraft
    try:
        draft = TkpTelegramDraft.objects.get(pk=draft_id)
    except TkpTelegramDraft.DoesNotExist:
        return JsonResponse({'error': 'Draft not found'}, status=404)
    user = _get_telegram_bot_user()
    base_name, err = submit_final(draft, user=user)
    if err:
        return JsonResponse({'error': err}, status=400)
    return JsonResponse({'base_name': base_name, 'status': 'final'})
