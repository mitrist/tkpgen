from django.db import models


class Region(models.Model):
    """Регион для справочника цен."""
    name = models.CharField('Название региона', max_length=255, unique=True)

    class Meta:
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'
        ordering = ['name']

    def __str__(self):
        return self.name


class Service(models.Model):
    """Услуга с привязкой к шаблону ТКП."""
    UNIT_M2 = 'm2'
    UNIT_PIECE = 'piece'
    UNIT_CHOICES = [
        (UNIT_M2, 'м²'),
        (UNIT_PIECE, 'шт'),
    ]

    name = models.CharField('Наименование услуги', max_length=255)
    description = models.TextField(
        'Описание услуги (подставляется в Комментарий в Комплексном ТКП)',
        blank=True,
        default='',
    )
    template_file = models.CharField(
        'Файл шаблона',
        max_length=255,
        help_text='Имя .docx файла в папке templates_docx/'
    )
    unit_type = models.CharField(
        'Единица измерения',
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_M2,
    )
    order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class RegionServicePrice(models.Model):
    """Цена за единицу (м² или шт) по региону и услуге."""
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name='Регион')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name='Услуга')
    unit_price = models.DecimalField(
        'Цена за единицу',
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    class Meta:
        verbose_name = 'Цена по региону'
        verbose_name_plural = 'Цены по регионам'
        unique_together = [['region', 'service']]

    def __str__(self):
        return f'{self.region.name} — {self.service.name}: {self.unit_price}'


class TKPRecord(models.Model):
    """Запись о сформированном ТКП (карточка ТКП для договора)."""
    STATUS_DRAFT = 'draft'
    STATUS_FINAL = 'final'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_FINAL, 'Итоговый'),
    ]
    date = models.DateField('Дата')
    number = models.CharField('Номер документа', max_length=150, unique=True)
    client = models.CharField('Клиент', max_length=255, blank=True)
    service = models.CharField('Услуга', max_length=255)
    sum_total = models.DecimalField('Сумма', max_digits=15, decimal_places=2, default=0)
    room = models.TextField('Параметры объекта / помещение', blank=True)
    s = models.CharField('Площадь / количество', max_length=100, blank=True)
    text = models.TextField('Произвольный текст из ТКП', blank=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_FINAL,
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Запись ТКП'
        verbose_name_plural = 'Записи ТКП'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.number} — {self.client}'


class Counterparty(models.Model):
    """Контрагент: реквизиты из карточки «Добавление реквизитов»."""
    name = models.CharField('Наименование', max_length=500, blank=True)
    inn = models.CharField('ИНН', max_length=12, blank=True)
    address = models.TextField('Адрес', blank=True)
    director = models.CharField('Генеральный директор', max_length=255, blank=True)
    ogrn = models.CharField('ОГРН', max_length=15, blank=True)
    account = models.CharField('Расчетный счет', max_length=64, blank=True)
    bank = models.CharField('Наименование банка', max_length=500, blank=True)
    bik = models.CharField('БИК', max_length=9, blank=True)
    kor_account = models.CharField('Корр. счет', max_length=64, blank=True)
    phone = models.CharField('Телефон', max_length=64, blank=True)
    email = models.CharField('Эл. почта', max_length=255, blank=True)
    kpp = models.CharField('КПП', max_length=9, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Контрагент'
        verbose_name_plural = 'Контрагенты'
        ordering = ['-created_at']

    def __str__(self):
        return self.name or self.inn or f'Контрагент #{self.pk}'


class ContractRecord(models.Model):
    """Запись о сформированном договоре или черновике."""
    STATUS_DRAFT = 'draft'
    STATUS_FINAL = 'final'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_FINAL, 'Итоговый'),
    ]
    date = models.DateField('Дата договора')
    number = models.CharField('Номер договора', max_length=50, unique=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=STATUS_FINAL)
    tkp = models.ForeignKey(
        TKPRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ТКП',
        related_name='contracts',
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Контрагент',
    )
    client = models.CharField('Клиент', max_length=500, blank=True)
    service = models.CharField('Услуга', max_length=255, blank=True)
    sum_total = models.DecimalField('Сумма', max_digits=15, decimal_places=2, default=0)
    docx_file = models.CharField('Файл DOCX', max_length=255, blank=True)
    pdf_file = models.CharField('Файл PDF', max_length=255, blank=True)
    contract_snapshot = models.JSONField('Снимок реквизитов', null=True, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Запись договора'
        verbose_name_plural = 'Записи договоров'
        ordering = ['-created_at']

    def __str__(self):
        return self.number
