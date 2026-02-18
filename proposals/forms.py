from django import forms
from .models import Service


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
    city = forms.CharField(label='Город', max_length=255)
    client = forms.CharField(
        label='Наименование клиента',
        max_length=255,
        required=False
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
        label='Общая площадь',
        max_digits=15,
        decimal_places=2,
        min_value=0,
        help_text='Стоимость в ТКП = единица измерения × площадь'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = Service.objects.all()
