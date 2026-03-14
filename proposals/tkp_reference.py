"""Справочники ТКП для контекста OpenClaw и API."""

from .choices import INTERNAL_CLIENT_CHOICES, SROK_CHOICES
from .models import Region, Service


def get_tkp_reference_data():
    """
    Возвращает словарь справочников для ТКП: услуги, регионы, внутренние клиенты, сроки.
    Используется для API и для формирования instructions в OpenClaw.
    """
    services = [
        {'id': s.pk, 'name': s.name, 'unit_type': s.unit_type}
        for s in Service.objects.all().order_by('order', 'name')
    ]
    regions = [
        {'id': r.pk, 'name': r.name}
        for r in Region.objects.all().order_by('name')
    ]
    internal_clients = [label for _value, label in INTERNAL_CLIENT_CHOICES if _value]
    srok_choices = [label for _value, label in SROK_CHOICES if _value]
    return {
        'services': services,
        'regions': regions,
        'internal_clients': internal_clients,
        'srok_choices': srok_choices,
    }


def format_tkp_reference_for_prompt(data):
    """
    Форматирует словарь справочников в текст для вставки в instructions OpenClaw.
    Модель должна предлагать пользователю только значения из этих списков.
    """
    lines = [
        '## Справочники ТКП (использовать только эти значения)',
        '',
        '### Услуги (выбор обязателен)',
    ]
    for s in data['services']:
        unit = 'м²' if s['unit_type'] == 'm2' else 'шт'
        lines.append(f"- id={s['id']}: {s['name']} ({unit})")
    lines.extend(['', '### Регионы (выбор для внешнего заказчика)'])
    for r in data['regions']:
        lines.append(f"- id={r['id']}: {r['name']}")
    lines.extend(['', '### Внутренние клиенты (если заказчик внутренний)'])
    lines.append(' | '.join(data['internal_clients']))
    lines.extend(['', '### Срок разработки (выбор из списка)'])
    lines.append(' | '.join(data['srok_choices']))
    return '\n'.join(lines)


# Правила диалога для instructions OpenClaw (сбор ТКП)
TKP_DIALOG_RULES = """
## Правила диалога по сбору ТКП

1. Сначала уточни у пользователя: внутренний или внешний заказчик.
2. Для внешнего заказчика обязательно: дата, услуга (только из списка), регион (из списка), площадь/количество (число), наименование клиента (произвольный текст), срок (из списка). По желанию: параметры объекта, произвольный текст.
3. Для внутреннего заказчика обязательно: дата, услуга, внутренний клиент (из списка), стоимость (число).
4. Не придумывай значения для полей-справочников — предлагай только из переданного списка.
5. После заполнения всех обязательных полей предложи сохранить черновик или сформировать итоговое ТКП и вызови соответствующий инструмент: tkp_submit_draft или tkp_submit_final.
6. Когда пользователь выбирает или вводит значение — зафиксируй его вызовом tkp_set_field (field и value).
"""
