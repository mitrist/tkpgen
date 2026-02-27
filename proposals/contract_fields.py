"""
Реквизиты договора для подстановки в шаблоны (docxtpl: {{ переменная }}).

Использование в шаблоне Word: {{ contract_number }}, {{ contract_date }}, и т.д.
"""

# Имена переменных для полей договора (как в форме и в контексте шаблона)
CONTRACT_FIELD_NAMES = (
    'contract_number',       # Номер договора
    'contract_date',         # Дата договора
    'customer_name',        # Наименование заказчика
    'customer_represented_by',  # Заказчик в лице
    'contract_subject',     # Предмет договора
    'delivery_place',       # Место доставки
    'contract_price_and_payment_order',  # Цена договора и порядок расчетов
    'payment_terms',        # Условия оплаты
    'scope_of_services',    # Объем услуг
    'revisions',            # Доработки
    'delivery_period',      # Срок поставки
    'delivery_time',        # Время доставки
    'signature_requisites',  # Реквизиты в подписи
)

# Соответствие: переменная -> русское название (для лейблов формы и отображения)
CONTRACT_FIELD_LABELS = {
    'contract_number': 'Номер договора',
    'contract_date': 'Дата договора',
    'customer_name': 'Наименование заказчика',
    'customer_represented_by': 'Заказчик в лице',
    'contract_subject': 'Предмет договора',
    'delivery_place': 'Место доставки',
    'contract_price_and_payment_order': 'Цена договора и порядок расчетов',
    'payment_terms': 'Условия оплаты',
    'scope_of_services': 'Объем услуг',
    'revisions': 'Доработки',
    'delivery_period': 'Срок поставки',
    'delivery_time': 'Время доставки',
    'signature_requisites': 'Реквизиты в подписи',
}
