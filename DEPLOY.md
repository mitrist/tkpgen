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

# Статика, логотипы и фон страницы «Старт»
# Перед collectstatic убедитесь, что в корне проекта есть папка images/ (или static/) с файлами:
# - logo.png — логотип в шапке и сайдбаре;
# - plk_logo.png — логотип в подвале сайдбара;
# - main.png — фоновое изображение страницы «Старт».
# Если этих файлов нет, после деплоя они не отображаются. Папки images/ и static/ подхватываются через STATICFILES_DIRS и попадают в staticfiles/ при collectstatic.
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

    # Статика (обязательно со слэшем в конце alias, путь — до каталога staticfiles)
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
- Шаблон 1 ДП.docx … Шаблон 5 Навигация_стенды.docx
- Шаблон 6 Фасад.docx, Шаблон 7 ДК Фасад.docx, Шаблон 8 Влагозащита.docx
- Шаблон 9 Комплексное ТКП.docx (для комплексного ТКП)

Имена должны совпадать с настройками в БД (см. `init_services`).

В корне проекта должен быть `region_price.csv` — справочник цен по регионам. Он загружается командой `load_region_prices`.

---

## 9. Проверка

Откройте в браузере: `http://93.77.182.91/`

Админка: `http://93.77.182.91/admin/`

---

## 10. Переход на именной домен (nacpro-web-service.ru)

Если сервис уже работает по IP и нужно перевести его на домен.

### 10.1. DNS

У регистратора домена (или в панели управления DNS) создайте A-записи, указывающие на публичный IP вашей VM (например, 93.77.182.91):

| Тип | Имя (поддомен) | Значение   | TTL (по умолчанию) |
|-----|----------------|------------|---------------------|
| A   | `@`            | 93.77.182.91 | 300–3600          |
| A   | `www`          | 93.77.182.91 | 300–3600          |

- `@` — это сам домен **nacpro-web-service.ru**.
- `www` — поддомен **www.nacpro-web-service.ru**.

Дождитесь обновления DNS (от нескольких минут до 24–48 часов). Проверка с вашего компьютера:

```bash
nslookup nacpro-web-service.ru
nslookup www.nacpro-web-service.ru
```

Оба должны возвращать IP вашей VM.

### 10.2. ALLOWED_HOSTS (Django)

На VM отредактируйте `.env` и добавьте домены в `ALLOWED_HOSTS` (через запятую, без пробелов):

```bash
nano /home/mitrist12/tkp_generator/.env
```

Измените строку, например так:

```
ALLOWED_HOSTS=93.77.182.91,localhost,127.0.0.1,nacpro-web-service.ru,www.nacpro-web-service.ru
```

Сохраните файл.

### 10.3. Nginx — привязка к домену

Откройте конфиг сайта:

```bash
sudo nano /etc/nginx/sites-available/tkp
```

Замените `server_name _;` на ваши домены:

```nginx
server {
    listen 80;
    server_name nacpro-web-service.ru www.nacpro-web-service.ru;

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

Проверьте конфиг и перезагрузите Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Перезапустите приложение, чтобы подхватить новый `ALLOWED_HOSTS`:

```bash
sudo systemctl restart tkp_generator
```

### 10.4. Проверка по домену

Откройте в браузере:

- `http://nacpro-web-service.ru/`
- `http://www.nacpro-web-service.ru/`

Оба адреса должны открывать ваш сервис.

### 10.5. HTTPS (опционально)

Чтобы включить шифрование (рекомендуется для продакшена):

1. Установите certbot и плагин для Nginx:

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

2. Выпустите сертификат (certbot сам подставит параметры в конфиг Nginx):

```bash
sudo certbot --nginx -d nacpro-web-service.ru -d www.nacpro-web-service.ru
```

Следуйте подсказкам (укажите email, согласитесь с условиями). Certbot настроит редирект HTTP → HTTPS и продление сертификата по таймеру.

3. После успешного выпуска откройте:

- `https://nacpro-web-service.ru/`
- `https://www.nacpro-web-service.ru/`

Проверка автообновления сертификата:

```bash
sudo certbot renew --dry-run
```

---

## Обновление приложения с GitHub

### На сервере (Ubuntu / Yandex Cloud VM)

Подключитесь по SSH и выполните:

```bash
cd /home/mitrist12/tkp_generator
git pull origin main
chmod +x deploy.sh
./deploy.sh
```

Если при первом запуске появляется «permission denied», выполните один раз: `chmod +x deploy.sh`. Либо запускайте скрипт так: `bash deploy.sh`.

**Если Git пишет «your local changes would be overwritten by merge»:** на сервере не должны храниться свои правки — берём код только из репозитория. Сбросьте локальные изменения и снова подтяните код:

```bash
cd /home/mitrist12/tkp_generator
git fetch origin
git reset --hard origin/main
./deploy.sh
```

Команда `git reset --hard origin/main` отменяет все локальные изменения в файлах и приводит каталог к состоянию ветки `main` на GitHub. Если нужно было что-то сохранить с сервера — перед этим сделайте копию: `cp -r /home/mitrist12/tkp_generator /home/mitrist12/tkp_generator.backup`.

При необходимости обновить справочник цен по регионам после изменения `region_price.csv`:

```bash
/home/mitrist12/tkp_generator/venv/bin/python manage.py load_region_prices
```

Проверка: откройте в браузере сайт и админку. Логи при ошибках: `sudo journalctl -u tkp_generator -n 50`.

**Если на мобильном не видно изменений (всё ещё боковая панель вместо верхнего меню):**
1. На VM убедитесь, что подтянулся новый код: `grep -l "topbar" /home/mitrist12/tkp_generator/proposals/templates/proposals/base.html` — должна вывести путь к файлу.
2. На телефоне: закройте вкладку с сайтом, откройте заново или откройте в режиме «Инкогнито» / «Приватный режим», чтобы не использовать кэш.

**Если после деплоя на VM не отображаются логотипы или фоновое изображение страницы «Старт»:**
1. В корне проекта должны быть файлы в папке `images/` (или `static/`): `logo.png`, `plk_logo.png`, `main.png` (фон страницы Старт). Закоммитьте их в репозиторий или скопируйте на VM вручную (например через `scp`). Лучше хранить их только в `images/`, чтобы не было дубликатов и сообщения collectstatic «4 skipped due to conflict».
2. В `settings.py` задано `STATIC_URL = '/static/'` (с начальным слэшем), чтобы ссылки на статику были вида `/static/logo.png`.
3. После добавления файлов выполните на VM: `cd /home/mitrist12/tkp_generator && source venv/bin/activate && python manage.py collectstatic --noinput`.
4. В конфиге Nginx в `location /static/` директива `alias` должна указывать на каталог `staticfiles` со слэшем в конце: `alias /home/mitrist12/tkp_generator/staticfiles/`.
5. Проверьте в браузере прямые запросы: `https://ваш-домен/static/logo.png`, `https://ваш-домен/static/main.png` — должны отдаваться файлы (код 200). Если 404 — статика не собрана или Nginx смотрит не в тот каталог.

**Если при открытии статики (логотипы, фон) в браузере — «Ошибка 403» (Forbidden):**  
Nginx работает от пользователя `www-data` и должен иметь право читать каталог `staticfiles` и все каталоги по пути к нему. Выполните на VM:

```bash
# Права на обход пути до staticfiles (без этого www-data не «дойдёт» до каталога)
sudo chmod o+x /home/mitrist12
sudo chmod o+x /home/mitrist12/tkp_generator

# Права на чтение собранной статики (каталоги: execute, файлы: read)
sudo chmod -R o+rX /home/mitrist12/tkp_generator/staticfiles
```

Проверка: снова откройте в браузере `https://ваш-домен/static/logo.png` — должен отдаваться файл (код 200), а не 403.

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

## Как обновить репозиторий на Git (отправить изменения с компьютера)

Когда вы изменили код, шаблоны или конфиги и хотите отправить изменения в GitHub:

### 1. Проверить статус

В папке проекта (PowerShell или командная строка):

```powershell
cd c:\Py_proj\dash_test
git status
```

Будут показаны изменённые и неотслеживаемые файлы.

### 2. Добавить файлы в коммит

Добавить конкретные файлы:

```powershell
git add путь/к/файлу
```

Или добавить все изменения (кроме тех, что в `.gitignore`):

```powershell
git add .
```

**Не добавляйте** в репозиторий: `db.sqlite3`, папки `__pycache__`, `.env`, папки `TKP_output`, `ТКП_pdf` — они уже в `.gitignore`.

### 3. Создать коммит

```powershell
git commit -m "Краткое описание изменений"
```

Например: `git commit -m "Обновление инструкции пользователя"`.

### 4. Отправить в удалённый репозиторий

```powershell
git push origin main
```

Если репозиторий ещё не привязан или ветка другая, первый раз может понадобиться:

```powershell
git remote add origin https://github.com/ВАШ_ЛОГИН/ИМЯ_РЕПОЗИТОРИЯ.git
git push -u origin main
```

После успешного `git push` изменения появятся на GitHub. На сервере (VM) их можно подтянуть командой `git pull origin main` и затем выполнить `./deploy.sh` (см. раздел «Обновление приложения с GitHub» выше).

---

## Полезные команды

| Действие | Команда |
|----------|---------|
| Логи Gunicorn | `sudo journalctl -u tkp_generator -f` |
| Логи Nginx | `sudo tail -f /var/log/nginx/error.log` |
| Перезапуск приложения | `sudo systemctl restart tkp_generator` |
