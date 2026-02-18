"""
Загрузка справочника цен по регионам из CSV.
Формат: service_name;ед. изм;region_name;unit_price
Сопоставление: Контент-система -> Контент
"""
import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from proposals.models import Region, RegionServicePrice, Service

CSV_SERVICE_TO_SERVICE = {
    'Контент-система': 'Контент',
}


class Command(BaseCommand):
    help = 'Загрузить цены по регионам из region_price.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            nargs='?',
            default=None,
            help='Путь к CSV (по умолчанию region_price.csv в корне проекта)',
        )

    def handle(self, *args, **options):
        path = options['file']
        if not path:
            path = Path(settings.BASE_DIR) / 'region_price.csv'
        else:
            path = Path(path)
        if not path.exists():
            self.stdout.write(self.style.ERROR(f'Файл не найден: {path}'))
            return
        count = 0
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                service_name = (row.get('service_name') or '').strip()
                region_name = (row.get('region_name') or '').strip()
                try:
                    unit_price = float((row.get('unit_price') or '0').replace(',', '.'))
                except ValueError:
                    self.stdout.write(self.style.WARNING(f'Пропуск: неверная цена {row}'))
                    continue
                if not service_name or not region_name:
                    continue
                service_name = CSV_SERVICE_TO_SERVICE.get(service_name, service_name)
                try:
                    service = Service.objects.get(name=service_name)
                except Service.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Услуга не найдена: {service_name}'))
                    continue
                region, _ = Region.objects.get_or_create(name=region_name, defaults={})
                obj, created = RegionServicePrice.objects.update_or_create(
                    region=region,
                    service=service,
                    defaults={'unit_price': unit_price},
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Загружено записей: {count}'))
