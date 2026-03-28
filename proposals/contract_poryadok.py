"""Порядок, сроки и условия поставки для шаблона 03 (Навигация + контент) → {{ poryadok }}."""

PORYADOK_CHOICE_1 = "1"
PORYADOK_CHOICE_2 = "2"

PORYADOK_TEXT = {
    PORYADOK_CHOICE_1: (
        "не позднее 20 рабочих дней с даты заключения Договора и внесения предоплаты Заказчиком"
    ),
    PORYADOK_CHOICE_2: "с даты заключения Договора",
}


def normalize_poryadok_choice(value) -> str:
    v = (value or "").strip()
    if v in (PORYADOK_CHOICE_1, PORYADOK_CHOICE_2):
        return v
    t = (value or "").strip()
    if t == PORYADOK_TEXT[PORYADOK_CHOICE_1]:
        return PORYADOK_CHOICE_1
    if t == PORYADOK_TEXT[PORYADOK_CHOICE_2]:
        return PORYADOK_CHOICE_2
    return PORYADOK_CHOICE_1


def poryadok_text_for_doc(value) -> str:
    key = normalize_poryadok_choice(value)
    return PORYADOK_TEXT[key]
