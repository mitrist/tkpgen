# Развёртывание на Yandex Cloud VM (Ubuntu)

## Важно: Linux vs Windows

На Ubuntu **нет MS Word**, поэтому используется **LibreOffice** для конвертации docx → PDF. Проект подготовлен для деплоя: `requirements.txt` содержит gunicorn, docx2pdf убран.

Для локальной разработки на Windows: `pip install docx2pdf` и замените в `views.py` subprocess LibreOffice на `docx2pdf_convert`.

---

## 1. Создание VM в Yandex Cloud

1. Откройте [консоль Yandex Cloud](https://console.cloud.yandex.ru/).
2. **Compute Cloud** → **Виртуальные машины** → **Создать ВМ**.
3. Параметры:
   - **Имя**: tkp
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

## 2. Подключение к VM

```bash
ssh mitrist12@93.77.182.91
```

---

## 3. Установка зависимостей на VM

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

## 4. Клонирование и настройка проекта

```bash
# Клонирование
cd /home/mitrist12
git clone https://github.com/mitrist/tkpgen.git tkp_generator
cd /home/mitrist12/tkp_generator

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

# Загрузка справочника цен по регионам
python manage.py load_region_prices

# Суперпользователь (для админки)
python manage.py createsuperuser
```

---

## 5. Конфигурация для production

Создайте файл переменных окружения (скопируйте пример и отредактируйте):

```bash
cp /home/mitrist12/tkp_generator/.env.example /home/mitrist12/tkp_generator/.env
nano /home/mitrist12/tkp_generator/.env
```

Содержимое `.env`:
```
SECRET_KEY=сгенерируйте-длинную-случайную-строку
DEBUG=False
ALLOWED_HOSTS=93.77.182.91,localhost,127.0.0.1
```

Для `SECRET_KEY` сгенерируйте строку:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Settings уже читают переменные из окружения. Убедитесь, что `EnvironmentFile` в systemd указывает на `.env`.

---

## 6. systemd-сервис (Gunicorn)

Создайте `/etc/systemd/system/tkp_generator.service`:

```bash
sudo nano /etc/systemd/system/tkp_generator.service
```

Содержимое:

```ini
[Unit]
Description=TKP Generator Gunicorn
After=network.target

[Service]
User=mitrist12
Group=mitrist12
WorkingDirectory=/home/mitrist12/tkp_generator

# Переменные окружения
EnvironmentFile=/home/mitrist12/tkp_generator/.env

ExecStart=/home/mitrist12/tkp_generator/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    --workers 2 \
    tkp_generator.wsgi:application

Restart=always

[Install]
WantedBy=multi-user.target
```

Настройка прав:
```bash
sudo chmod 600 /home/mitrist12/tkp_generator/.env
sudo systemctl daemon-reload
sudo systemctl enable tkp_generator
sudo systemctl start tkp_generator
```

---

## 7. Nginx

Создайте `/etc/nginx/sites-available/tkp`:

```bash
sudo nano /etc/nginx/sites-available/tkp
```

```nginx
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /home/mitrist12/tkp_generator/staticfiles/;
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

## 8. Шаблоны .docx и справочник регионов

Убедитесь, что в `/home/mitrist12/tkp_generator/templates_docx/` лежат файлы:
- Шаблон 1 ДП.docx
- Шаблон 2 ДКП.docx
- Шаблон 3 Навигация.docx
- Шаблон 4 Контент.docx
- Шаблон 5 Навигация_стенды.docx

Имена должны совпадать с настройками в БД (см. `init_services`).

В корне проекта должен быть `region_price.csv` — справочник цен по регионам. Он загружается командой `load_region_prices`.

---

## 9. Проверка

Откройте в браузере: `http://93.77.182.91/`

Админка: `http://93.77.182.91/admin/`

---

## Обновление приложения с GitHub

### На сервере (Ubuntu / Yandex Cloud VM)

Подключитесь по SSH и выполните по порядку:

```bash
# 1. Перейти в каталог проекта
cd /home/mitrist12/tkp_generator

# 2. Скачать изменения с GitHub
git pull origin main

# 3. Обновить зависимости Python
/home/mitrist12/tkp_generator/venv/bin/pip install -r requirements.txt

# 4. Применить миграции БД (если были изменения моделей)
/home/mitrist12/tkp_generator/venv/bin/python manage.py migrate

# 4a. Обновить справочник цен (если менялся region_price.csv)
/home/mitrist12/tkp_generator/venv/bin/python manage.py load_region_prices

# 5. Собрать статику
/home/mitrist12/tkp_generator/venv/bin/python manage.py collectstatic --noinput

# 6. Перезапустить приложение
sudo systemctl restart tkp_generator
```

Проверка: откройте в браузере сайт и админку. Логи при ошибках: `sudo journalctl -u tkp_generator -n 50`.

### Локально (Windows)

В папке проекта в PowerShell или командной строке:

```powershell
cd c:\Py_proj\dash_test
git pull origin main
pip install -r requirements.txt
python manage.py migrate
```

После этого перезапустите сервер разработки (`python manage.py runserver`), если он был запущен.

---

## Полезные команды

| Действие | Команда |
|----------|---------|
| Логи Gunicorn | `sudo journalctl -u tkp_generator -f` |
| Логи Nginx | `sudo tail -f /var/log/nginx/error.log` |
| Перезапуск приложения | `sudo systemctl restart tkp_generator` |
