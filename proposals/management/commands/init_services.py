"""
Management-команда для инициализации услуг.
Шаблоны уже есть в папке templates_docx/ проекта.
"""
from django.core.management.base import BaseCommand
from proposals.models import Service


SERVICES = [
    (1, 'ДП', 'Шаблон 1 ДП.docx', Service.UNIT_M2),
    (2, 'ДКП', 'Шаблон 2 ДКП.docx', Service.UNIT_M2),
    (3, 'Навигация', 'Шаблон 3 Навигация.docx', Service.UNIT_PIECE),
    (4, 'Контент', 'Шаблон 4 Контент.docx', Service.UNIT_PIECE),
    (5, 'Навигация_стенды', 'Шаблон 5 Навигация_стенды.docx', Service.UNIT_M2),
    (6, 'Фасад', 'Шаблон 6 Фасад.docx', Service.UNIT_M2),
    (7, 'ДК Фасад', 'Шаблон 7 ДК Фасад.docx', Service.UNIT_M2),
    (8, 'Благоустройство', 'Шаблон 8 Благоустройство.docx', Service.UNIT_M2),
]


class Command(BaseCommand):
    help = 'Создать услуги: ДП, ДКП, Навигация, Контент, Навигация_стенды, Фасад, ДК Фасад, Благоустройство'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить существующие услуги перед созданием',
        )

    def handle(self, *args, **options):
        if options['clear']:
            Service.objects.all().delete()
            self.stdout.write('Существующие услуги удалены.')

        for order, name, template_file, unit_type in SERVICES:
            obj, created = Service.objects.update_or_create(
                template_file=template_file,
                defaults={'name': name, 'order': order, 'unit_type': unit_type}
            )
            status = 'создана' if created else 'обновлена'
            self.stdout.write(f'Услуга "{name}" ({template_file}) — {status}.')

        self.stdout.write(self.style.SUCCESS('Готово.'))
