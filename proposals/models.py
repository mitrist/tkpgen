from django.conf import settings
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
    notes = models.TextField('Заметки по сделке', blank=True, default='')
    rows_json = models.JSONField(
        'Строки комплексного ТКП (позиции)',
        null=True,
        blank=True,
        help_text='Список строк: service_name, comment, srok, unit, quantity, price_per_unit, total',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tkp_records',
        verbose_name='Владелец',
    )

    class Meta:
        verbose_name = 'Запись ТКП'
        verbose_name_plural = 'Записи ТКП'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.number} — {self.client}'


class TkpTelegramDraft(models.Model):
    """Черновик ТКП по сессии Telegram (состояние диалога для OpenClaw)."""
    telegram_user_id = models.CharField('Telegram user id', max_length=64, db_index=True)
    telegram_chat_id = models.CharField('Telegram chat id', max_length=64)
    is_internal = models.BooleanField('Внутренний заказчик', default=False, blank=True)
    date = models.DateField('Дата ТКП', null=True, blank=True)
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Услуга',
        related_name='+',
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Регион',
        related_name='+',
    )
    internal_client = models.CharField('Внутренний клиент', max_length=255, blank=True)
    internal_price = models.DecimalField(
        'Стоимость для внутреннего заказчика',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    client = models.CharField('Наименование клиента', max_length=255, blank=True)
    room = models.TextField('Параметры объекта / помещение', blank=True)
    s = models.CharField('Площадь / количество', max_length=100, blank=True)
    srok = models.CharField('Срок разработки', max_length=255, blank=True)
    text = models.TextField('Произвольный текст', blank=True)
    payload = models.JSONField('Сырые значения', default=dict, blank=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Черновик ТКП (Telegram)'
        verbose_name_plural = 'Черновики ТКП (Telegram)'
        ordering = ['-updated_at']

    def __str__(self):
        return f'Draft {self.telegram_user_id}'


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
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_contract_records',
        verbose_name='Владелец',
    )

    class Meta:
        verbose_name = 'Запись договора'
        verbose_name_plural = 'Записи договоров'
        ordering = ['-created_at']

    def __str__(self):
        return self.number


class KanbanColumnTitleOverride(models.Model):
    """Переопределение названия колонки канбана для пользователя."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kanban_column_title_overrides',
    )
    column_key = models.CharField('Ключ колонки', max_length=50)
    title = models.CharField('Название', max_length=255)

    class Meta:
        verbose_name = 'Название колонки канбана'
        verbose_name_plural = 'Названия колонок канбана'
        unique_together = [['user', 'column_key']]

    def __str__(self):
        return f'{self.column_key}: {self.title}'


class KanbanColumnCustom(models.Model):
    """Пользовательская колонка канбана."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kanban_custom_columns',
    )
    title = models.CharField('Название', max_length=255)
    order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Пользовательская колонка канбана'
        verbose_name_plural = 'Пользовательские колонки канбана'
        ordering = ['user', 'order', 'pk']

    def __str__(self):
        return self.title


class KanbanCardPosition(models.Model):
    """Позиция карточки на канбане (в какой колонке показывать)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kanban_card_positions',
    )
    tkp = models.ForeignKey(
        TKPRecord,
        on_delete=models.CASCADE,
        related_name='kanban_positions',
    )
    column_key = models.CharField('Колонка', max_length=64)

    class Meta:
        verbose_name = 'Позиция карточки канбана'
        verbose_name_plural = 'Позиции карточек канбана'
        unique_together = [['user', 'tkp']]

    def __str__(self):
        return f'{self.tkp_id} → {self.column_key}'


class KanbanCardField(models.Model):
    """Пользовательское доп. поле на карточке канбана."""
    VALUE_TEXT = 'text'
    VALUE_NUMBER = 'number'
    VALUE_TYPE_CHOICES = [
        (VALUE_TEXT, 'Текст'),
        (VALUE_NUMBER, 'Число'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kanban_card_fields',
    )
    tkp = models.ForeignKey(
        TKPRecord,
        on_delete=models.CASCADE,
        related_name='kanban_custom_fields',
    )
    name = models.CharField('Название поля', max_length=255)
    value_type = models.CharField('Тип', max_length=20, choices=VALUE_TYPE_CHOICES, default=VALUE_TEXT)
    value = models.TextField('Значение', blank=True)
    order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Доп. поле карточки канбана'
        verbose_name_plural = 'Доп. поля карточек канбана'
        ordering = ['order', 'pk']
        unique_together = [['user', 'tkp', 'name']]

    def __str__(self):
        return f'{self.name}: {self.value[:50] if self.value else "—"}'


class KanbanBoardOrder(models.Model):
    """Порядок колонок на доске канбана для пользователя (список ключей колонок)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kanban_board_order',
    )
    order = models.JSONField(
        'Порядок колонок',
        default=list,
        help_text='Список ключей: draft, final, contract_draft, contract_final, custom_<id>',
    )

    class Meta:
        verbose_name = 'Порядок колонок канбана'
        verbose_name_plural = 'Порядок колонок канбана'

    def __str__(self):
        return f'Order for {self.user}'
