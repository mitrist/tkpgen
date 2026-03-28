"""Варианты условий оплаты для договора (п. 2.2); значение для шаблона — {{ usl }} и {{ payment_terms }}."""

PAYMENT_TERMS_CHOICE_1 = "1"
PAYMENT_TERMS_CHOICE_2 = "2"

PAYMENT_TERMS_VARIANT_TEXT = {
    PAYMENT_TERMS_CHOICE_1: (
        "2.2. Расчеты по Договору производятся на основании выставленного Исполнителем счета "
        "не позднее 10 рабочих дней с даты подписания Заказчиком товарной накладной/"
        "универсального передаточного документа (УПД)."
    ),
    PAYMENT_TERMS_CHOICE_2: (
        "2.2. Оплата по договору производится в следующем порядке: "
        "2.2.1. В течение 5 рабочих дней на основании выставленного Исполнителем счета "
        "Заказчик выплачивает Исполнителю аванс в размере 30% от цены Договора; "
        "2.2.2. В течение 5 рабочих дней с даты подписания товарной накладной/"
        "универсального передаточного документа (УПД) Заказчик выплачивает Исполнителю "
        "оставшиеся 70% цены Договора."
    ),
}

# Прежний текст по умолчанию (до вариантов) — относим ко 2-му варианту по смыслу
LEGACY_DEFAULT_PAYMENT_TERMS = """2.2.1. В течение 5 (пяти) рабочих дней на основании выставленного Исполнителем счета Заказчик выплачивает Исполнителю аванс в размере 30% от цены Договора;
2.2.2. В течение 5 (пяти) рабочих дней после приемки/утверждения результатов работ Заказчик выплачивает Исполнителю оставшиеся 70% цены Договора."""

# Для обратной совместимости импортов: полный текст варианта 2
DEFAULT_PAYMENT_TERMS = PAYMENT_TERMS_VARIANT_TEXT[PAYMENT_TERMS_CHOICE_2]


def normalize_payment_terms_choice(value) -> str:
    """Принимает '1'/'2' или сохранённый полный текст / старый default."""
    v = (value or "").strip()
    if v in (PAYMENT_TERMS_CHOICE_1, PAYMENT_TERMS_CHOICE_2):
        return v
    if not v:
        return PAYMENT_TERMS_CHOICE_2
    t = v.replace("\r\n", "\n").strip()
    if t == PAYMENT_TERMS_VARIANT_TEXT[PAYMENT_TERMS_CHOICE_1]:
        return PAYMENT_TERMS_CHOICE_1
    if t == PAYMENT_TERMS_VARIANT_TEXT[PAYMENT_TERMS_CHOICE_2]:
        return PAYMENT_TERMS_CHOICE_2
    if t == LEGACY_DEFAULT_PAYMENT_TERMS.strip():
        return PAYMENT_TERMS_CHOICE_2
    low = t.lower()
    if "30%" in t and "70%" in t and "аванс" in low:
        return PAYMENT_TERMS_CHOICE_2
    if "10 рабочих" in t and "упд" in low and "не позднее" in low:
        return PAYMENT_TERMS_CHOICE_1
    return PAYMENT_TERMS_CHOICE_2


def payment_terms_text_for_doc(value) -> str:
    """Текст для подстановки в Word ({{ usl }}, {{ payment_terms }})."""
    key = normalize_payment_terms_choice(value)
    return PAYMENT_TERMS_VARIANT_TEXT[key]
