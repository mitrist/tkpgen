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
    """Запись о сформированном ТКП."""
    date = models.DateField('Дата')
    number = models.CharField('Номер документа', max_length=150, unique=True)
    client = models.CharField('Клиент', max_length=255, blank=True)
    service = models.CharField('Услуга', max_length=255)
    sum_total = models.DecimalField('Сумма', max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Запись ТКП'
        verbose_name_plural = 'Записи ТКП'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.number} — {self.client}'
