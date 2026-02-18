from django import template

register = template.Library()


@register.filter
def format_price(value):
    """Форматирование суммы с разделителями тысяч."""
    if value is None:
        return ''
    try:
        s = str(int(value))
    except (ValueError, TypeError):
        return str(value)
    n = len(s)
    if n <= 3:
        return s
    r = n % 3 or 3
    result = s[:r]
    for i in range(r, n, 3):
        result += ' ' + s[i:i + 3]
    return result
