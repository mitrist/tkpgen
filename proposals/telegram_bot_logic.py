"""
Логика Telegram-бота ТКП без OpenClaw: пошаговое заполнение черновика,
выбор из списков — инлайн-кнопками, текстовые поля — вводом. В конце — отправка файла.
"""

from datetime import date
from pathlib import Path

from django.conf import settings

from .choices import INTERNAL_CLIENT_CHOICES, SROK_CHOICES
from .models import Region, Service, TkpTelegramDraft
from .tkp_draft_service import get_or_create_draft, set_field, submit_draft, submit_final


# Префиксы callback_data (до 64 байт в Telegram)
CB_DATE = 'd'
CB_INTERNAL = 'i'
CB_INTERNAL_CLIENT = 'ic'
CB_SERVICE = 's'
CB_REGION = 'r'
CB_SROK = 'sr'
CB_ACTION_DRAFT = 'ad'
CB_ACTION_FINAL = 'af'


def _get_telegram_bot_user():
    from .api_views import _get_telegram_bot_user as get_user
    return get_user()


def _next_empty_field(draft):
    """Возвращает имя следующего незаполненного поля или None если всё готово к действиям."""
    if not draft.date:
        return 'date'
    # Тип заказчика: различаем «ещё не выбран» через payload (BooleanField default False)
    if not (draft.payload or {}).get('internal_choice_set'):
        return 'is_internal'
    if draft.is_internal:
        if not (draft.internal_client or '').strip():
            return 'internal_client'
        if draft.internal_price is None:
            return 'internal_price'
    if not draft.service_id:
        return 'service_id'
    if not draft.is_internal:
        if not draft.region_id:
            return 'region_id'
        if not (draft.client or '').strip():
            return 'client'
    if (draft.s or '').strip() == '' and not draft.is_internal:
        return 's'
    if not (draft.srok or '').strip():
        return 'srok'
    # room, text — опциональны, можно пропустить кнопкой "Далее" или считать заполненными
    return 'actions'


def get_next_step(draft):
    """
    Определить следующий шаг: текст подсказки и (опционально) ряды кнопок.
    Возвращает (prompt_text, keyboard_rows).
    keyboard_rows: list of list of (button_text, callback_data).
    """
    field = _next_empty_field(draft)
    if not field:
        field = 'actions'

    if field == 'date':
        from django.utils import timezone
        today = timezone.now().date().isoformat()
        return (
            'Укажите дату ТКП (ГГГГ-ММ-ДД) или нажмите кнопку:',
            [[('Сегодня', f'{CB_DATE}:{today}')]],
        )

    if field == 'is_internal':
        return (
            'Тип заказчика:',
            [
                [('Внутренний', f'{CB_INTERNAL}:1'), ('Внешний', f'{CB_INTERNAL}:0')],
            ],
        )

    if field == 'internal_client':
        # Индексы 1..len-1 (0 — пустой выбор)
        choices = INTERNAL_CLIENT_CHOICES[1:]
        row = [(label, f'{CB_INTERNAL_CLIENT}:{i+1}') for i, (val, label) in enumerate(choices)]
        # По 2 кнопки в ряд
        rows = [row[i:i+2] for i in range(0, len(row), 2)]
        return ('Выберите внутреннего клиента:', rows)

    if field == 'internal_price':
        return ('Введите стоимость для внутреннего заказчика (число):', None)

    if field == 'service_id':
        services = list(Service.objects.order_by('order', 'name').values_list('pk', 'name'))
        rows = [[(name, f'{CB_SERVICE}:{pk}')] for pk, name in services]
        return ('Выберите услугу:', rows)

    if field == 'region_id':
        regions = list(Region.objects.order_by('name').values_list('pk', 'name'))
        rows = [[(name, f'{CB_REGION}:{pk}')] for pk, name in regions]
        return ('Выберите регион:', rows)

    if field == 'client':
        return ('Введите наименование клиента:', None)

    if field == 's':
        return ('Введите площадь (м²) или количество:', None)

    if field == 'srok':
        # SROK_CHOICES[0] — пустой
        choices = SROK_CHOICES[1:]
        row = [(label, f'{CB_SROK}:{i+1}') for i, (val, label) in enumerate(choices)]
        rows = [row[i:i+2] for i in range(0, len(row), 2)]
        return ('Выберите срок разработки:', rows)

    if field == 'actions':
        return (
            'Все обязательные поля заполнены. Сохранить черновик или сформировать ТКП?',
            [
                [('Сохранить черновик', CB_ACTION_DRAFT), ('Сформировать ТКП', CB_ACTION_FINAL)],
            ],
        )

    return ('Продолжите заполнение.', None)


def _apply_callback(draft, callback_data):
    """
    Применить выбор из callback_data к черновику. Возвращает (reply_text, error, document_path).
    document_path — путь к файлу для отправки в Telegram (после submit_final).
    """
    if not callback_data or ':' not in callback_data:
        if callback_data == CB_ACTION_DRAFT:
            user = _get_telegram_bot_user()
            number, err = submit_draft(draft, user=user)
            if err:
                return None, err, None
            return f'Черновик сохранён. Номер: {number}', None, None
        if callback_data == CB_ACTION_FINAL:
            user = _get_telegram_bot_user()
            base_name, err = submit_final(draft, user=user)
            if err:
                return None, err, None
            out_dir = Path(getattr(settings, 'TKP_OUTPUT_DIR', Path(settings.BASE_DIR) / 'TKP_output'))
            pdf_path = out_dir / f'{base_name}.pdf'
            if not pdf_path.exists():
                docx_path = out_dir / f'{base_name}.docx'
                return f'ТКП сформировано: {base_name}. Файл: {base_name}.docx', None, str(docx_path) if docx_path.exists() else None
            return f'ТКП сформировано: {base_name}. Во вложении — документ.', None, str(pdf_path)
        return None, 'Неизвестная команда', None

    prefix, value = callback_data.split(':', 1)

    if prefix == CB_DATE:
        try:
            from django.utils import timezone
            draft.date = date.fromisoformat(value[:10]) if value and value != 'today' else timezone.now().date()
            draft.save(update_fields=['date', 'updated_at'])
            return 'Дата сохранена.', None, None
        except Exception:
            return None, 'Некорректная дата.', None

    if prefix == CB_INTERNAL:
        draft.is_internal = value == '1'
        payload = draft.payload or {}
        payload['internal_choice_set'] = True
        draft.payload = payload
        draft.save(update_fields=['is_internal', 'payload', 'updated_at'])
        return 'Тип заказчика сохранён.', None, None

    if prefix == CB_INTERNAL_CLIENT:
        idx = int(value)
        if 1 <= idx <= len(INTERNAL_CLIENT_CHOICES) - 1:
            val = INTERNAL_CLIENT_CHOICES[idx][0]
            ok, err = set_field(draft, 'internal_client', val)
            if not ok:
                return None, err, None
            return 'Клиент выбран.', None, None
        return None, 'Неверный выбор.', None

    if prefix == CB_SERVICE:
        try:
            pk = int(value)
            ok, err = set_field(draft, 'service_id', pk)
            if not ok:
                return None, err, None
            return 'Услуга выбрана.', None, None
        except ValueError:
            return None, 'Неверный выбор.', None

    if prefix == CB_REGION:
        try:
            pk = int(value)
            ok, err = set_field(draft, 'region_id', pk)
            if not ok:
                return None, err, None
            return 'Регион выбран.', None, None
        except ValueError:
            return None, 'Неверный выбор.', None

    if prefix == CB_SROK:
        idx = int(value)
        if 1 <= idx <= len(SROK_CHOICES) - 1:
            val = SROK_CHOICES[idx][0]
            ok, err = set_field(draft, 'srok', val)
            if not ok:
                return None, err, None
            return 'Срок выбран.', None, None
        return None, 'Неверный выбор.', None

    return None, 'Неизвестная команда', None


def process_text_message(chat_id, user_id, text):
    """
    Обработка текстового сообщения от пользователя.
    Возвращает dict: reply_text, error, inline_keyboard (list of rows), document_path.
    """
    if text == '/start':
        draft = get_or_create_draft(user_id, chat_id)
        prompt, rows = get_next_step(draft)
        return {
            'reply_text': 'Здравствуйте. Я помогу сформировать ТКП. ' + prompt,
            'error': None,
            'inline_keyboard': rows,
            'document_path': None,
        }
    if not (text or '').strip():
        return {'reply_text': '', 'error': None, 'inline_keyboard': None, 'document_path': None}

    draft = get_or_create_draft(user_id, chat_id)
    field = _next_empty_field(draft)

    # Текстовые поля
    if field == 'date':
        ok, err = set_field(draft, 'date', text.strip())
        if not ok:
            return {'reply_text': None, 'error': err, 'inline_keyboard': None, 'document_path': None}
    elif field == 'internal_price':
        ok, err = set_field(draft, 'internal_price', text.strip())
        if not ok:
            return {'reply_text': None, 'error': err, 'inline_keyboard': None, 'document_path': None}
    elif field == 'client':
        ok, err = set_field(draft, 'client', text.strip())
        if not ok:
            return {'reply_text': None, 'error': err, 'inline_keyboard': None, 'document_path': None}
    elif field == 's':
        ok, err = set_field(draft, 's', text.strip())
        if not ok:
            return {'reply_text': None, 'error': err, 'inline_keyboard': None, 'document_path': None}
    elif field in ('room', 'text'):
        ok, err = set_field(draft, field, text.strip())
        if not ok:
            return {'reply_text': None, 'error': err, 'inline_keyboard': None, 'document_path': None}
    else:
        # Сейчас ожидался выбор кнопкой — подскажем
        prompt, rows = get_next_step(draft)
        return {'reply_text': prompt, 'error': None, 'inline_keyboard': rows, 'document_path': None}

    prompt, rows = get_next_step(draft)
    return {'reply_text': prompt, 'error': None, 'inline_keyboard': rows, 'document_path': None}


def process_callback(chat_id, user_id, callback_data):
    """
    Обработка нажатия инлайн-кнопки.
    Возвращает dict: reply_text, error, inline_keyboard, document_path.
    """
    draft = get_or_create_draft(user_id, chat_id)
    reply_text, error, document_path = _apply_callback(draft, callback_data)
    if error:
        return {'reply_text': None, 'error': error, 'inline_keyboard': None, 'document_path': None}
    if document_path:
        return {'reply_text': reply_text, 'error': None, 'inline_keyboard': None, 'document_path': document_path}
    # После применения выбора — следующий шаг (черновик мог быть удалён при submit)
    try:
        draft.refresh_from_db()
    except TkpTelegramDraft.DoesNotExist:
        return {'reply_text': reply_text or 'Готово.', 'error': None, 'inline_keyboard': None, 'document_path': None}
    prompt, rows = get_next_step(draft)
    return {'reply_text': prompt, 'error': None, 'inline_keyboard': rows, 'document_path': None}
