from django import forms
from .choices import INTERNAL_CLIENT_CHOICES, SROK_CHOICES
from .models import Counterparty, Region, Service


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
        choices=INTERNAL_CLIENT_CHOICES,
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
        choices=SROK_CHOICES,
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


class ComplexProposalForm(forms.Form):
    """Форма комплексного ТКП: регион, дата, клиент, срок, параметры объекта, text1. Строки передаются отдельно (JSON)."""
    region = forms.ModelChoiceField(
        label='Регион',
        queryset=Region.objects.none(),
        empty_label='Выберите регион',
        required=True,
        help_text='Регион, для которого формируется ТКП (по нему подставляются цены в таблице)',
    )
    date = forms.DateField(
        label='Дата ТКП',
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d']
    )
    client = forms.CharField(label='Наименование клиента', max_length=255)
    room = forms.CharField(
        label='Параметры объекта',
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text='Описание параметров объекта для подстановки в шаблон ТКП.',
    )
    text1 = forms.CharField(
        label='Доп. текст 1',
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text='По желанию. Если пусто — в ТКП не попадает.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['region'].queryset = Region.objects.all().order_by('name')


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


class RequisitesParseForm(forms.Form):
    """Загрузка файла реквизитов и редактирование извлечённых полей."""
    source_file = forms.FileField(
        label='Файл с реквизитами (.docx/.pdf)',
        required=False,
        help_text='Поддерживаются DOCX и PDF.',
    )
    name = forms.CharField(label='Наименование', max_length=500, required=False)
    inn = forms.CharField(label='ИНН', max_length=12, required=False)
    kpp = forms.CharField(label='КПП', max_length=9, required=False)
    address = forms.CharField(
        label='Адрес',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    director = forms.CharField(label='Генеральный директор', max_length=255, required=False)
    ogrn = forms.CharField(label='ОГРН', max_length=15, required=False)
    account = forms.CharField(label='Расчетный счет (р/сч)', max_length=64, required=False)
    bank = forms.CharField(label='Наименование банка (Банк)', max_length=500, required=False)
    bik = forms.CharField(label='БИК', max_length=9, required=False)
    kor_account = forms.CharField(label='Корр. счет', max_length=64, required=False)
    phone = forms.CharField(label='Телефон', max_length=64, required=False)
    email = forms.CharField(label='Эл. почта', max_length=255, required=False)


class ContractForm(forms.Form):
    """Реквизиты договора: все поля из ТКП и блок подписи заказчика для проверки."""
    counterparty = forms.ModelChoiceField(
        label='Заказчик (контрагент)',
        queryset=Counterparty.objects.none(),
        required=True,
        empty_label='Выберите контрагента',
    )
    contract_number = forms.CharField(
        label='Номер договора',
        max_length=50,
        required=False,
        help_text='Присваивается при формировании: дата_порядковый номер за день',
    )
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d'],
        required=True,
    )
    customer_name = forms.CharField(label='Наименование заказчика', max_length=500, required=False)  # дублирует контрагента, подставляется из выбора
    customer_represented_by = forms.CharField(
        label='В лице (р.п.)',
        max_length=255,
        required=False,
        help_text='ФИО в родительном падеже — первое вхождение в шаблоне',
    )
    customer_represented_by_nominative = forms.CharField(
        label='В лице (им.п.)',
        max_length=255,
        required=False,
        help_text='ФИО в именительном падеже — второе вхождение в шаблоне',
    )
    customer_in_person = forms.ChoiceField(
        label='Заказчик в лице',
        choices=[
            ('', '— выберите —'),
            ('Директора', 'Директора'),
            ('Генерального директора', 'Генерального директора'),
            ('И.О. Директора', 'И.О. Директора'),
            ('Подписанта', 'Подписанта'),
        ],
        required=False,
    )
    acting_on_basis = forms.ChoiceField(
        label='Действующего на основании',
        choices=[
            ('', '— выберите —'),
            ('Устава', 'Устава'),
            ('Приказа', 'Приказа'),
            ('Доверенности', 'Доверенности'),
            ('ОГРНИП', 'ОГРНИП'),
        ],
        required=False,
    )
    work_completion_period = forms.ChoiceField(
        label='Срок выполнения работ',
        choices=[
            ('', '— выберите —'),
            ('10 рабочих дней', '10 рабочих дней'),
            ('20 рабочих дней', '20 рабочих дней'),
            ('25 рабочих дней', '25 рабочих дней'),
            ('35 рабочих дней', '35 рабочих дней'),
        ],
        required=False,
    )
    period_starts_from = forms.ChoiceField(
        label='Срок отсчитывается от',
        choices=[
            ('', '— выберите —'),
            ('внесения предоплаты по Договору Заказчиком', 'внесения предоплаты по Договору Заказчиком'),
            ('с даты согласования макетов Заказчиком', 'с даты согласования макетов Заказчиком'),
        ],
        required=False,
    )
    price = forms.DecimalField(label='Цена договора', max_digits=15, decimal_places=2, required=True)
    payment_terms = forms.CharField(
        label='Условия оплаты',
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    include_ris = forms.BooleanField(
        label='Включить пункт про РИС?',
        required=False,
        initial=False,
    )
    # Реквизиты в подписи Заказчик
    name = forms.CharField(label='Наименование', max_length=500, required=False)
    address = forms.CharField(label='Юридический адрес', required=False, widget=forms.Textarea(attrs={'rows': 2}))
    inn = forms.CharField(label='ИНН', max_length=12, required=False)
    kpp = forms.CharField(label='КПП', max_length=9, required=False)
    ogrn = forms.CharField(label='ОГРН', max_length=15, required=False)
    account = forms.CharField(label='Р/с', max_length=64, required=False)
    bank = forms.CharField(label='Банк', max_length=500, required=False)
    bik = forms.CharField(label='БИК', max_length=9, required=False)
    kor_account = forms.CharField(label='к/с', max_length=64, required=False)
    email = forms.CharField(label='эл.почта', max_length=255, required=False)
    # Из ТКП: границы подготовки документации
    room = forms.CharField(label='Параметры объекта / помещение', required=False, widget=forms.Textarea(attrs={'rows': 2}))
    s = forms.CharField(label='Площадь / количество', max_length=100, required=False)
    # Для комплексного ТКП: выбор типа договора (шаблон 05 или 08)
    complex_contract_type = forms.ChoiceField(
        label='Комплексный договор',
        choices=[
            ('', '— выберите —'),
            ('05_Договор_Контент_Навигация.docx', 'Контент и навигация'),
            ('08_Договор_ДПФ_Благоустройство.docx', 'ДПФ и Благоустройство'),
        ],
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['counterparty'].queryset = Counterparty.objects.all().order_by('name')
