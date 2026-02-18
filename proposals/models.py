from django.db import models


class Service(models.Model):
    """Услуга с привязкой к шаблону ТКП."""
    name = models.CharField('Наименование услуги', max_length=255)
    template_file = models.CharField(
        'Файл шаблона',
        max_length=255,
        help_text='Имя .docx файла в папке templates_docx/'
    )
    unit = models.DecimalField(
        'Единица измерения',
        max_digits=15,
        decimal_places=2,
        default=1,
        help_text='Цена в шаблоне = единица_измерения × площадь'
    )
    order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


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
