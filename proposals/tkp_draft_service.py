"""Сервис черновиков ТКП для Telegram: получение/создание, установка полей, сбор proposal_data, отправка."""

from datetime import datetime
from decimal import Decimal

from django.utils import timezone

from .models import RegionServicePrice, TkpTelegramDraft, TKPRecord


def get_or_create_draft(telegram_user_id, telegram_chat_id):
    """Получить или создать черновик ТКП для пары user_id/chat_id."""
    draft, _ = TkpTelegramDraft.objects.get_or_create(
        telegram_user_id=str(telegram_user_id),
        defaults={'telegram_chat_id': str(telegram_chat_id)},
    )
    if str(draft.telegram_chat_id) != str(telegram_chat_id):
        draft.telegram_chat_id = str(telegram_chat_id)
        draft.save(update_fields=['telegram_chat_id', 'updated_at'])
    return draft


def set_field(draft, field_name, value):
    """
    Установить поле черновика с базовой валидацией.
    Возвращает (True, None) при успехе или (False, 'сообщение об ошибке').
    """
    if field_name == 'date':
        if value is None or value == '':
            draft.date = None
            draft.save(update_fields=['date', 'updated_at'])
            return True, None
        if isinstance(value, datetime):
            draft.date = value.date()
        elif isinstance(value, str):
            try:
                draft.date = datetime.strptime(value.strip()[:10], '%Y-%m-%d').date()
            except ValueError:
                return False, 'Некорректная дата. Используйте формат ГГГГ-ММ-ДД.'
        else:
            return False, 'Некорректное значение даты.'
        draft.save(update_fields=['date', 'updated_at'])
        return True, None

    if field_name == 'service_id':
        from .models import Service
        if value is None or value == '':
            draft.service_id = None
            draft.save(update_fields=['service_id', 'updated_at'])
            return True, None
        try:
            pk = int(value)
            Service.objects.get(pk=pk)
            draft.service_id = pk
            draft.save(update_fields=['service_id', 'updated_at'])
            return True, None
        except (ValueError, Service.DoesNotExist):
            return False, 'Услуга с таким id не найдена.'

    if field_name == 'region_id':
        from .models import Region
        if value is None or value == '':
            draft.region_id = None
            draft.save(update_fields=['region_id', 'updated_at'])
            return True, None
        try:
            pk = int(value)
            Region.objects.get(pk=pk)
            draft.region_id = pk
            draft.save(update_fields=['region_id', 'updated_at'])
            return True, None
        except (ValueError, Region.DoesNotExist):
            return False, 'Регион с таким id не найден.'

    if field_name == 'is_internal':
        draft.is_internal = bool(value)
        draft.save(update_fields=['is_internal', 'updated_at'])
        return True, None

    if field_name in ('internal_client', 'client', 'room', 'srok', 'text'):
        str_val = '' if value is None else str(value).strip()
        setattr(draft, field_name, str_val[:500] if field_name in ('room', 'text') else str_val[:255])
        draft.save(update_fields=[field_name, 'updated_at'])
        return True, None

    if field_name == 'internal_price':
        if value is None or value == '':
            draft.internal_price = None
            draft.save(update_fields=['internal_price', 'updated_at'])
            return True, None
        try:
            draft.internal_price = Decimal(str(value))
            if draft.internal_price < 0:
                return False, 'Стоимость не может быть отрицательной.'
            draft.save(update_fields=['internal_price', 'updated_at'])
            return True, None
        except Exception:
            return False, 'Введите число для стоимости.'

    if field_name == 's':
        if value is None or value == '':
            draft.s = ''
            draft.save(update_fields=['s', 'updated_at'])
            return True, None
        try:
            v = Decimal(str(value))
            if v < 0:
                return False, 'Площадь/количество не может быть отрицательным.'
            draft.s = str(v)
            draft.save(update_fields=['s', 'updated_at'])
            return True, None
        except Exception:
            return False, 'Введите число для площади/количества.'

    return False, f'Неизвестное поле: {field_name}'


def get_draft_state_for_prompt(draft):
    """Вернуть текст «что заполнено / что пусто» для контекста OpenClaw."""
    filled = []
    missing = []
    if draft.date:
        filled.append(f"дата={draft.date.strftime('%Y-%m-%d')}")
    else:
        missing.append('дата')
    if draft.service_id:
        filled.append(f"услуга_id={draft.service_id} ({getattr(draft.service, 'name', '') or ''})")
    else:
        missing.append('услуга')
    if draft.is_internal:
        filled.append('внутренний заказчик')
        if draft.internal_client:
            filled.append(f"внутренний клиент={draft.internal_client}")
        else:
            missing.append('внутренний клиент')
        if draft.internal_price is not None:
            filled.append(f"стоимость={draft.internal_price}")
        else:
            missing.append('стоимость')
    else:
        if draft.region_id:
            filled.append(f"регион_id={draft.region_id} ({getattr(draft.region, 'name', '') or ''})")
        else:
            missing.append('регион')
        if draft.s:
            filled.append(f"площадь/количество={draft.s}")
        else:
            missing.append('площадь/количество')
        if draft.client:
            filled.append(f"клиент={draft.client[:50]}...")
        else:
            missing.append('наименование клиента')
    if draft.srok:
        filled.append(f"срок={draft.srok}")
    else:
        missing.append('срок разработки')
    if draft.room:
        filled.append('параметры объекта (заполнено)')
    if draft.text:
        filled.append('произвольный текст (заполнено)')
    lines = ['Заполнено: ' + ', '.join(filled) if filled else 'Заполнено: ничего', 'Не заполнено: ' + ', '.join(missing)]
    return '\n'.join(lines)


def build_proposal_data_from_draft(draft):
    """
    Собрать словарь proposal_data из черновика (формат как у _build_proposal_data_from_form_cleaned).
    Возвращает (data, None) при успехе или (None, 'сообщение об ошибке').
    """
    if not draft.date:
        return None, 'Не указана дата ТКП.'
    if not draft.service_id:
        return None, 'Не выбрана услуга.'
    service = draft.service
    if not service:
        return None, 'Услуга не найдена.'

    date_str = draft.date.strftime('%Y-%m-%d')
    if draft.is_internal:
        if not draft.internal_client:
            return None, 'Не выбран внутренний клиент.'
        if draft.internal_price is None or draft.internal_price < 0:
            return None, 'Не указана стоимость для внутреннего заказчика.'
        price_value = float(draft.internal_price)
        region_name = ''
        client_value = draft.internal_client.strip()
        s_str = draft.s or ''
    else:
        if not draft.region_id:
            return None, 'Не выбран регион.'
        region = draft.region
        if not region:
            return None, 'Регион не найден.'
        try:
            rsp = RegionServicePrice.objects.get(region=region, service=service)
        except RegionServicePrice.DoesNotExist:
            return None, f'Не найдена цена для региона "{region.name}" и услуги "{service.name}".'
        s_val = draft.s
        if s_val is None or s_val == '':
            try:
                s_float = 0.0
            except Exception:
                return None, 'Введите площадь/количество для расчёта стоимости.'
        else:
            try:
                s_float = float(s_val)
            except Exception:
                return None, 'Площадь/количество должно быть числом.'
        if s_float < 0:
            return None, 'Площадь/количество не может быть отрицательным.'
        price_value = float(rsp.unit_price) * s_float
        region_name = region.name
        client_value = (draft.client or '').strip()
        s_str = draft.s or str(s_float)

    return {
        'date': date_str,
        'service_id': service.pk,
        'service_name': service.name,
        'city': region_name,
        'price': str(price_value),
        'client': client_value,
        'room': draft.room or '',
        'srok': draft.srok or '',
        'text': draft.text or '',
        's': s_str,
    }, None


def submit_draft(draft, user=None):
    """
    Сохранить черновик в перечне ТКП (статус draft), очистить сессию черновика.
    Возвращает (number, None) при успехе или (None, 'сообщение об ошибке').
    """
    data, err = build_proposal_data_from_draft(draft)
    if err:
        return None, err
    from .views import _save_tkp_record
    _save_tkp_record(data, status=TKPRecord.STATUS_DRAFT, user=user)
    number = TKPRecord.objects.filter(date=data['date'], status=TKPRecord.STATUS_DRAFT).order_by('-id').first()
    number = number.number if number else ''
    draft.delete()
    return number, None


def submit_final(draft, user=None):
    """
    Сформировать итоговое ТКП (файлы + запись), очистить черновик.
    Возвращает (base_name, None) при успехе или (None, 'сообщение об ошибке').
    """
    data, err = build_proposal_data_from_draft(draft)
    if err:
        return None, err
    from .views import _generate_and_save_files, _save_tkp_record
    base_name = _generate_and_save_files(data)
    if not base_name:
        return None, 'Ошибка генерации файлов ТКП (шаблон или сервис не найден).'
    _save_tkp_record(data, status=TKPRecord.STATUS_FINAL, user=user)
    draft.delete()
    return base_name, None
