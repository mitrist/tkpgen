# Генератор ТКП

Web-приложение на Django для автоматической генерации технико-коммерческих предложений (ТКП).

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

1. Шаблоны в папке `templates_docx/`:
   - `Шаблон 1 ДП.docx`, `Шаблон 2 ДКП.docx`, `Шаблон 3 Навигация.docx`, `Шаблон 4 Контент.docx`, `Шаблон 5 Навигация_стенды.docx`

2. Инициализация услуг:
```bash
python manage.py migrate
python manage.py init_services
```

## Запуск

```bash
python manage.py runserver
```

Откройте http://127.0.0.1:8000/

## Требования

- Windows с установленным MS Word (для конвертации в PDF)
