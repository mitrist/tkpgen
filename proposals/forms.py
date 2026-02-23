from django import forms
from .models import Region, Service


class ProposalForm(forms.Form):
    """Форма ввода параметров ТКП."""
    date = forms.DateField(
        label='Дата ТКП',
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d']
    )
    service = forms.ModelChoiceField(
        label='Услуга',
        queryset=Service.objects.none(),
        empty_label='Выберите услугу'
    )
    region = forms.ModelChoiceField(
        label='Регион',
        queryset=Region.objects.none(),
        empty_label='Выберите регион',
        required=False,
    )
    is_internal = forms.BooleanField(
        label='Является внутренним заказчиком?',
        required=False,
        initial=False
    )
    internal_client = forms.ChoiceField(
        label='Внутренний клиент',
        choices=[
            ('', 'Выберите клиента'),
            ('ООО НацПро', 'ООО НацПро'),
            ('ООО Нацпро Северо-Запад', 'ООО Нацпро Северо-Запад'),
            ('ИП Соколова АМ', 'ИП Соколова АМ'),
            ('ООО Северная Столица', 'ООО Северная Столица'),
        ],
        required=False
    )
    internal_price = forms.DecimalField(
        label='Стоимость для внутреннего заказчика',
        max_digits=15,
        decimal_places=2,
        min_value=0,
        required=False
    )
    client = forms.CharField(
        label='Наименование клиента',
        max_length=255,
        required=False,
        help_text='Заполняется, если заказчик не внутренний'
    )
    room = forms.CharField(
        label='Наименование объекта и характеристика помещений',
        max_length=500,
        required=False
    )
    srok = forms.ChoiceField(
        label='Срок разработки',
        choices=[
            ('', 'Выберите срок'),
            ('в течение 10 рабочих дней', 'в течение 10 рабочих дней'),
            ('в течение 15 рабочих дней', 'в течение 15 рабочих дней'),
            ('в течение 20 рабочих дней', 'в течение 20 рабочих дней'),
            ('в течение 35 рабочих дней', 'в течение 35 рабочих дней'),
        ],
        required=False
    )
    text = forms.CharField(
        label='Произвольный текст',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    s = forms.DecimalField(
        label='Площадь / Количество',
        max_digits=15,
        decimal_places=2,
        min_value=0,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = Service.objects.all()
        self.fields['region'].queryset = Region.objects.all()

    def clean(self):
        data = super().clean()
        if data.get('is_internal'):
            if not data.get('internal_client'):
                self.add_error('internal_client', 'Выберите внутреннего клиента')
            if data.get('internal_price') is None or data.get('internal_price', 0) < 0:
                self.add_error('internal_price', 'Введите стоимость')
        else:
            if not data.get('region'):
                self.add_error('region', 'Выберите регион')
            if data.get('s') is None or data.get('s', 0) < 0:
                self.add_error('s', 'Введите значение для расчёта стоимости')
        return data


SROK_CHOICES = [
    ('', 'Выберите срок'),
    ('в течение 10 рабочих дней', 'в течение 10 рабочих дней'),
    ('в течение 15 рабочих дней', 'в течение 15 рабочих дней'),
    ('в течение 20 рабочих дней', 'в течение 20 рабочих дней'),
    ('в течение 35 рабочих дней', 'в течение 35 рабочих дней'),
]


class ComplexProposalForm(forms.Form):
    """Форма комплексного ТКП: дата, клиент, срок, опционально text1/text2. Строки передаются отдельно (JSON)."""
    date = forms.DateField(
        label='Дата ТКП',
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d']
    )
    client = forms.CharField(label='Наименование клиента', max_length=255)
    srok = forms.ChoiceField(label='Срок разработки', choices=SROK_CHOICES, required=False)
    text1 = forms.CharField(
        label='Доп. текст 1',
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text='По желанию. Если пусто — в ТКП не попадает.',
    )
    text2 = forms.CharField(
        label='Доп. текст 2',
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text='По желанию. Если пусто — в ТКП не попадает.',
    )


class TariffForm(forms.Form):
    """Добавление тарифа: услуга + регион + цена. Регион можно выбрать или ввести новый."""
    service = forms.ModelChoiceField(
        label='Услуга',
        queryset=Service.objects.none(),
        empty_label='Выберите услугу'
    )
    region = forms.ModelChoiceField(
        label='Регион',
        queryset=Region.objects.none(),
        empty_label='— или выберите существующий —',
        required=False
    )
    new_region_name = forms.CharField(
        label='Новый регион',
        max_length=255,
        required=False,
        help_text='Заполните, чтобы добавить новый регион'
    )
    unit_price = forms.DecimalField(
        label='Цена за единицу (₽)',
        max_digits=15,
        decimal_places=2,
        min_value=0
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = Service.objects.all()
        self.fields['region'].queryset = Region.objects.all().order_by('name')

    def clean(self):
        data = super().clean()
        region = data.get('region')
        new_name = (data.get('new_region_name') or '').strip()
        if not region and not new_name:
            self.add_error('new_region_name', 'Выберите регион или введите название нового')
        return data
