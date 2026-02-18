# Развёртывание на Yandex Cloud VM (Ubuntu)

## Важно: Linux vs Windows

На Ubuntu **нет MS Word**, поэтому `docx2pdf` не работает. Используется **LibreOffice** для конвертации docx → PDF.

---

## 1. Подготовка проекта (на локальном ПК)

Перед деплоем нужно заменить docx2pdf на LibreOffice:

**proposals/views.py** — заменить строку:
```python
docx2pdf_convert(str(docx_path), str(pdf_path))
```
на:
```python
import subprocess
subprocess.run(
    ['libreoffice', '--headless', '--convert-to', 'pdf',
     '--outdir', str(pdf_path.parent), str(docx_path)],
    check=True
)
```

Добавить `import subprocess` в начало файла, удалить `from docx2pdf import ...`.

**requirements.txt** — убрать `docx2pdf`, добавить `gunicorn`:
```
Django>=5.0
docxtpl>=0.16.0
gunicorn>=21.0
```

---

## 2. Создание VM в Yandex Cloud

1. Откройте [консоль Yandex Cloud](https://console.cloud.yandex.ru/).
2. **Compute Cloud** → **Виртуальные машины** → **Создать ВМ**.
3. Параметры:
   - **Имя**: tkp-generator
   - **Зона**: ближайшая (ru-central1-a)
   - **Платформа**: Intel Ice Lake
   - **Ядра**: 2
   - **Память**: 2 ГБ (для LibreOffice)
   - **Диск**: 10 ГБ SSD
   - **Образ**: Ubuntu 22.04 LTS
   - **Сеть**: стандартная, назначить публичный IP
4. В **Безопасность** → **Доступ** укажите SSH-ключ.
5. Создайте ВМ.

### Открытие портов

**VPC** → **Группы безопасности** → ваша группа → добавить правила:
- Входящий: порт 80, CIDR 0.0.0.0/0
- Входящий: порт 22, CIDR 0.0.0.0/0

---

## 3. Подключение к VM

```bash
ssh ubuntu@ВНЕШНИЙ_IP_ВМ
```

(или `ubuntu@` заменить на ваше имя пользователя)

---

## 4. Установка зависимостей на VM

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Python, venv, Git
sudo apt install -y python3-pip python3-venv git

# LibreOffice для конвертации docx → PDF
sudo apt install -y libreoffice-writer

# Nginx (обратный прокси)
sudo apt install -y nginx
```

---

## 5. Клонирование и настройка проекта

```bash
# Клонирование
cd /opt
sudo git clone https://github.com/mitrist/tkpgen.git tkp_generator
sudo chown -R $USER:$USER /opt/tkp_generator
cd /opt/tkp_generator

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Статика
python manage.py collectstatic --noinput

# Миграции
python manage.py migrate

# Инициализация услуг
python manage.py init_services --clear

# Суперпользователь (для админки)
python manage.py createsuperuser
```

---

## 6. Конфигурация для production

Создайте файл переменных окружения:

```bash
nano /opt/tkp_generator/.env
```

Содержимое:
```
SECRET_KEY=сгенерируйте-длинную-случайную-строку
DEBUG=False
ALLOWED_HOSTS=IP_ВМ,localhost,127.0.0.1
```

Для `SECRET_KEY` сгенерируйте строку:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

В **tkp_generator/settings.py** добавьте в начало (после импортов):
```python
import os
from pathlib import Path

# Загрузка .env (упрощённо, без python-dotenv)
def _env(key, default=None):
    return os.environ.get(key, default)

SECRET_KEY = _env('SECRET_KEY', 'change-me-in-production')
DEBUG = _env('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = _env('ALLOWED_HOSTS', 'localhost').split(',')
```

(Либо установите `pip install python-dotenv` и используйте `load_dotenv()`.)

---

## 7. systemd-сервис (Gunicorn)

Создайте `/etc/systemd/system/tkp_generator.service`:

```bash
sudo nano /etc/systemd/system/tkp_generator.service
```

Содержимое (подставьте свой путь и IP):

```ini
[Unit]
Description=TKP Generator Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/tkp_generator

# Переменные окружения
EnvironmentFile=/opt/tkp_generator/.env

ExecStart=/opt/tkp_generator/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    --workers 2 \
    tkp_generator.wsgi:application

Restart=always

[Install]
WantedBy=multi-user.target
```

Настройка прав:
```bash
sudo chown -R www-data:www-data /opt/tkp_generator
sudo chmod 600 /opt/tkp_generator/.env
sudo systemctl daemon-reload
sudo systemctl enable tkp_generator
sudo systemctl start tkp_generator
```

---

## 8. Nginx

Создайте `/etc/nginx/sites-available/tkp`:

```bash
sudo nano /etc/nginx/sites-available/tkp
```

```nginx
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /opt/tkp_generator/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активация:
```bash
sudo ln -s /etc/nginx/sites-available/tkp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 9. Шаблоны .docx

Убедитесь, что в `/opt/tkp_generator/templates_docx/` лежат файлы:
- Шаблон 1 ДП.docx
- Шаблон 2 ДКП.docx
- Шаблон 3 Навигация.docx
- Шаблон 4 Контент.docx
- Шаблон 5 Навигация_стенды.docx

Имена должны совпадать с настройками в БД (см. `init_services`).

---

## 10. Проверка

Откройте в браузере: `http://ВНЕШНИЙ_IP_ВМ/`

Админка: `http://ВНЕШНИЙ_IP_ВМ/admin/`

---

## Обновление приложения

```bash
cd /opt/tkp_generator
sudo -u www-data git pull
sudo -u www-data /opt/tkp_generator/venv/bin/pip install -r requirements.txt
sudo -u www-data /opt/tkp_generator/venv/bin/python manage.py migrate
sudo -u www-data /opt/tkp_generator/venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart tkp_generator
```

---

## Полезные команды

| Действие | Команда |
|----------|---------|
| Логи Gunicorn | `sudo journalctl -u tkp_generator -f` |
| Логи Nginx | `sudo tail -f /var/log/nginx/error.log` |
| Перезапуск приложения | `sudo systemctl restart tkp_generator` |
