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

### Создание .env на сервере

1. Подключитесь по SSH и перейдите в каталог проекта:
   ```bash
   cd /home/mitrist12/tkp_generator
   ```

2. Создайте `.env` из примера (или пустой файл, если примера нет):
   ```bash
   cp .env.example .env
   ```
   Если файла `.env.example` нет:
   ```bash
   touch .env
   ```

3. Откройте файл для редактирования:
   ```bash
   nano .env
   ```

4. Заполните переменные (по одной на строку, без пробелов вокруг `=`):
   ```env
   SECRET_KEY=сгенерируйте-длинную-случайную-строку
   DEBUG=False
   ALLOWED_HOSTS=93.77.182.91,localhost,127.0.0.1,nacpro-web-service.ru,www.nacpro-web-service.ru
   ```
   Для генерации `SECRET_KEY` на сервере выполните:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   ```
   Скопируйте вывод в значение `SECRET_KEY=`.

5. Если используется ТКП через Telegram, добавьте в тот же `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=токен_от_BotFather
   TELEGRAM_WEBHOOK_SECRET=ваша_случайная_строка_секрета
   OPENCLAW_GATEWAY_URL=https://ваш-openclaw:порт
   OPENCLAW_API_KEY=ключ_OpenClaw
   TKP_TELEGRAM_API_KEY=ключ_для_api_при_нужности
   TKP_TELEGRAM_BOT_USER_ID=
   ```
   Необязательные переменные можно не указывать или оставить пустыми.

6. Сохраните файл в nano: `Ctrl+O`, Enter, затем выход: `Ctrl+X`.

7. Ограничьте доступ к `.env` (только владелец может читать):
   ```bash
   chmod 600 .env
   ```
   Если приложение запускается от другого пользователя (например, через systemd от `mitrist12`), владельцем должен быть этот пользователь:
   ```bash
   sudo chmod 600 /home/mitrist12/tkp_generator/.env
   ```

8. Убедитесь, что в unit-файле systemd указан путь к `.env`:
   ```bash
   sudo grep EnvironmentFile /etc/systemd/system/tkp_generator.service
   ```
   Должна быть строка: `EnvironmentFile=/home/mitrist12/tkp_generator/.env`.

9. После изменения `.env` перезапустите приложение:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart tkp_generator
   ```

Приложение читает переменные из окружения (Django не использует python-dotenv); systemd подставляет их из `EnvironmentFile` при старте сервиса.

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

## ТКП через Telegram

Сбор ТКП через бота в Telegram с использованием OpenClaw (DeepSeek) как «мозга» диалога. Справочники (услуги, регионы, сроки) берутся из приложения; пользователь вводит произвольный текст там, где нужно.

### 1. Создание бота и токен

1. В Telegram найдите [@BotFather](https://t.me/BotFather), отправьте `/newbot` и следуйте подсказкам.
2. Скопируйте выданный токен (например `123456789:AAH...`).
3. Добавьте в `.env` на сервере (и при необходимости локально):

```
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
TELEGRAM_WEBHOOK_SECRET=случайная_строка_для_защиты_вебхука
OPENCLAW_GATEWAY_URL=https://ваш-openclaw-или-127.0.0.1:18789
OPENCLAW_API_KEY=ваш_ключ_OpenClaw
TKP_TELEGRAM_API_KEY=ключ_для_вызова_api_из_моста_при_нужности
```

Опционально: чтобы в перечне ТКП запись создавалась от имени конкретного пользователя Django, задайте `TKP_TELEGRAM_BOT_USER_ID=id` (числовой id из таблицы auth_user).

### 2. Установка вебхука

После деплоя приложения один раз зарегистрируйте вебхук (подставьте свой домен и токен):

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://ваш-домен/telegram/webhook/\"}"
```

Если используете `TELEGRAM_WEBHOOK_SECRET`, добавьте его в URL: `https://ваш-домен/telegram/webhook/?secret=ваш_секрет`.

### 3. OpenClaw: URL шлюза и API-ключ

Ошибка «OpenClaw not configured (OPENCLAW_GATEWAY_URL, OPENCLAW_API_KEY)» означает, что в `.env` приложения не заданы или пустые переменные `OPENCLAW_GATEWAY_URL` и `OPENCLAW_API_KEY`. Их нужно взять из настройки **шлюза OpenClaw** на той же VM (или другом сервере), где запущен OpenClaw Gateway.

#### 3.1. Где лежит конфиг OpenClaw

Обычно конфиг: `~/.openclaw/openclaw.json` (на сервере под пользователем, от которого запущен OpenClaw). Полный путь может быть, например: `/home/mitrist12/.openclaw/openclaw.json`.

#### 3.2. Включить эндпоинт /v1/responses

В конфиге должен быть включён HTTP-эндпоинт для API ответов:

```json
{
  "gateway": {
    "http": {
      "endpoints": {
        "responses": {
          "enabled": true
        }
      }
    }
  }
}
```

Если секции `gateway.http` или `gateway.http.endpoints.responses` нет — добавьте их и установите `responses.enabled: true`.

#### 3.3. Задать токен доступа к шлюзу (это и есть OPENCLAW_API_KEY)

Клиенты вызывают API шлюза с заголовком `Authorization: Bearer <токен>`. Этот токен задаётся в конфиге OpenClaw в блоке `gateway.auth`:

**Вариант A — задать токен вручную**

1. Придумайте длинную случайную строку (например сгенерируйте: `openssl rand -hex 32`).
2. В `~/.openclaw/openclaw.json` добавьте или измените секцию `gateway.auth`:

```json
{
  "gateway": {
    "auth": {
      "mode": "token",
      "token": "ваша_случайная_строка_токена"
    }
  }
}
```

Вместо строки можно использовать переменную окружения, например: `"token": "${OPENCLAW_GATEWAY_TOKEN}"`, и задать `OPENCLAW_GATEWAY_TOKEN` в окружении процесса OpenClaw (systemd, .env и т.п.).

3. **Этот же токен** скопируйте в `.env` приложения ТКП как значение `OPENCLAW_API_KEY`:

```env
OPENCLAW_API_KEY=ваша_случайная_строка_токена
```

**Вариант B — токен при первой настройке (onboarding)**

Если OpenClaw при первой настройке запускали через `openclaw onboard` или мастер настройки, он мог сгенерировать токен и записать его в конфиг. Тогда:

1. Откройте `~/.openclaw/openclaw.json` и найдите `gateway.auth.token` (или `gateway.auth.password` при режиме password).
2. Скопируйте это значение в `.env` приложения в переменную `OPENCLAW_API_KEY`.

Если в конфиге указано `"token": "${OPENCLAW_GATEWAY_TOKEN}"`, то значение берётся из переменной окружения на хосте OpenClaw — задайте такой же токен в `.env` приложения ТКП для `OPENCLAW_API_KEY`.

#### 3.4. URL шлюза (OPENCLAW_GATEWAY_URL)

- Если OpenClaw и приложение ТКП на **одной VM**, шлюз по умолчанию слушает порт **18789** на loopback. Укажите в `.env`:
  ```env
  OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789
  ```
- Если OpenClaw на **другом сервере**, укажите полный URL до шлюза (с протоколом и портом), например:
  ```env
  OPENCLAW_GATEWAY_URL=http://192.168.1.10:18789
  ```
  или
  ```env
  OPENCLAW_GATEWAY_URL=https://openclaw.ваш-домен.ru
  ```
  (если перед шлюзом стоит Nginx/прокси с TLS).

Проверка с сервера приложения: `curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ВАШ_ТОКЕН" http://127.0.0.1:18789/v1/responses` — без тела может вернуть 400, но не 401 (401 = неверный или отсутствующий токен).

#### 3.5. Итог в .env приложения

В итоге в `.env` должны быть непустые строки:

```env
OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789
OPENCLAW_API_KEY=тот_же_токен_что_в_gateway.auth.token
```

После изменения `.env` перезапустите приложение: `sudo systemctl restart tkp_generator`.

Модель DeepSeek подключается в конфигурации OpenClaw отдельно (провайдер и ключ для DeepSeek в OpenClaw).

#### 3.6. Как поправить на сервере (ошибки 401, 400)

Если бот в Telegram отвечает ошибкой или в логах видно «401 Unauthorized» или «400 Bad Request» при вызове OpenClaw, выполните по шагам на сервере.

**1. Конфиг OpenClaw**

- Подключитесь по SSH к VM, где запущен OpenClaw.
- Откройте конфиг (часто `~/.openclaw/openclaw.json` или `~/.openclaw/conf.json` у пользователя, под которым крутится OpenClaw):

  ```bash
  nano ~/.openclaw/openclaw.json
  ```

- Убедитесь, что в блоке `gateway` есть:
  - **Токен:** `gateway.auth.mode` = `"token"` и `gateway.auth.token` = строка (например сгенерируйте: `openssl rand -hex 24`).
  - **Эндпоинт /v1/responses:** внутри `gateway` на одном уровне с `auth` должен быть блок `http`:

  ```json
  "gateway": {
    "port": 18789,
    "auth": {
      "mode": "token",
      "token": "ВАШ_ТОКЕН_СЮДА"
    },
    "http": {
      "endpoints": {
        "responses": {
          "enabled": true
        }
      }
    }
  }
  ```

  Сохраните файл (в nano: Ctrl+O, Enter, Ctrl+X). Перезапустите OpenClaw (например `sudo systemctl restart openclaw` или как у вас настроен сервис).

**2. Переменные окружения приложения ТКП**

- На той же VM откройте `.env` приложения (путь из systemd, обычно `/home/mitrist12/tkp_generator/.env`):

  ```bash
  sudo nano /home/mitrist12/tkp_generator/.env
  ```

- Задайте (или исправьте) две переменные — **значения должны совпадать с конфигом OpenClaw**:
  - `OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789` — для одной VM используйте **http** (не https), если шлюз без TLS.
  - `OPENCLAW_API_KEY=` **тот же токен**, что в `gateway.auth.token` в конфиге OpenClaw (см. шаг 1).

- Сохраните файл.

**3. Код приложения**

- Убедитесь, что на сервере подтянут актуальный код (в запрос к `/v1/responses` добавлено поле `model: "openclaw"` и улучшена обработка ошибок):

  ```bash
  cd /home/mitrist12/tkp_generator
  git fetch origin
  git pull origin main
  ./deploy.sh
  ```

  Если не используете Git с этого сервера — скопируйте обновлённый `proposals/telegram_webhook.py` (в нём в `payload` и `payload2` должно быть `'model': 'openclaw'`).

**4. Перезапуск**

- Перезапустите приложение ТКП, чтобы подхватить новый `.env`:

  ```bash
  sudo systemctl restart tkp_generator
  ```

- При необходимости перезапустите OpenClaw (если меняли его конфиг).

**Проверка:** отправьте боту сообщение в Telegram. В логах приложения не должно быть 401/400: `sudo journalctl -u tkp_generator -n 30`. Если 400 остаётся — в логе теперь будет тело ответа от OpenClaw (поле `error.message`), по нему можно уточнить причину.

### 4. Проверка

1. Отправьте боту в Telegram сообщение (например «Привет» или «Хочу ТКП»).
2. Бот должен ответить вопросом по сбору ТКП (например про тип заказчика).
3. После заполнения полей и выбора «Сформировать ТКП» запись и файлы должны появиться в перечне ТКП и в каталоге вывода (если настроен доступ к приложению).

При ошибках смотрите логи: `sudo journalctl -u tkp_generator -n 100`.

---

## ТКП Telegram: режим long polling

Вебхук и long polling — **альтернативные** способы получения обновлений от Telegram для одного бота. При использовании режима long polling вебхук **не задавайте** или сбросьте его (вызов `setWebhook` с пустым `url`), иначе обновления могут уходить в вебхук, а не в getUpdates.

**Когда выбирать вебхук:** есть публичный HTTPS для бота, нужна масштабируемость (несколько воркеров, балансировка).  
**Когда выбирать polling:** нет HTTPS для приёма вебхука от Telegram, проще поднять один процесс без настройки Nginx/домена для бота.

### Переменные окружения

В `.env` (или в `EnvironmentFile` systemd для сервиса polling) задайте:

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от BotFather |
| `TELEGRAM_PROCESS_URL` | URL внутреннего endpoint обработки, например `http://127.0.0.1:8000/api/telegram-process/` |
| `TKP_TELEGRAM_API_KEY` | Ключ для заголовка `X-API-Key` при вызове Django (тот же, что для API) |

### Запуск скрипта

Из каталога проекта с активированным venv:

```bash
cd /home/mitrist12/tkp_generator
source venv/bin/activate
python scripts/telegram_polling_bot.py
```

Либо напрямую через интерпретатор venv:

```bash
/home/mitrist12/tkp_generator/venv/bin/python /home/mitrist12/tkp_generator/scripts/telegram_polling_bot.py
```

### systemd: сервис tkp_telegram_polling

Создайте unit-файл `/etc/systemd/system/tkp_telegram_polling.service`:

```bash
sudo nano /etc/systemd/system/tkp_telegram_polling.service
```

Содержимое:

```ini
[Unit]
Description=TKP Telegram bot (long polling)
After=network.target tkp_generator.service

[Service]
User=mitrist12
Group=mitrist12
WorkingDirectory=/home/mitrist12/tkp_generator

EnvironmentFile=/home/mitrist12/tkp_generator/.env

ExecStart=/home/mitrist12/tkp_generator/venv/bin/python /home/mitrist12/tkp_generator/scripts/telegram_polling_bot.py

Restart=always

[Install]
WantedBy=multi-user.target
```

Включение и запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tkp_telegram_polling
sudo systemctl start tkp_telegram_polling
```

Логи: `sudo journalctl -u tkp_telegram_polling -f`.

### Сброс вебхука (если переходите с вебхука на polling)

Чтобы Telegram перестал слать обновления на вебхук и скрипт polling мог получать их через getUpdates:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": ""}'
```

Подставьте свой токен вместо `<TELEGRAM_BOT_TOKEN>`.

### Проверка

1. Убедитесь, что Django и (при необходимости) сервис `tkp_telegram_polling` запущены.
2. Отправьте боту в Telegram любое сообщение (например «Привет» или `/start`).
3. Бот должен ответить (приветствием или следующим вопросом по ТКП).

Если ответа нет — проверьте логи: `sudo journalctl -u tkp_telegram_polling -n 50` и `sudo journalctl -u tkp_generator -n 50`.

---

## ТКП Telegram: Mini App (форма в WebView)

Форма ТКП может открываться как **Telegram Mini App** (веб-страница внутри Telegram). Пользователь заполняет поля в браузере и после отправки получает ссылку на скачивание сформированного файла (PDF/DOCX).

### Как открыть Mini App из бота

1. В `.env` задайте URL сайта с **HTTPS** (Mini App в Telegram требуют HTTPS):
   ```env
   TKP_MINIAPP_BASE_URL=https://ваш-домен.ru
   ```
2. Перезапустите приложение: `sudo systemctl restart tkp_generator`.
3. В Telegram отправьте боту команду **`/app`** или **`/tkp`**. Бот пришлёт сообщение с кнопкой **«Открыть форму ТКП»** — по нажатию откроется форма в WebView.

### Маршруты

- **GET /tkp-app/** — страница формы (Mini App).
- **GET /tkp-app/reference/** — справочники (услуги, регионы, сроки) в JSON, без авторизации.
- **POST /tkp-app/submit/** — приём данных формы и initData от Telegram; проверка подписи; формирование ТКП; ответ с полем `download_url` (одноразовая ссылка на скачивание).
- **GET /tkp-app/download/&lt;token&gt;/** — скачивание файла по токену из `download_url`.

### Безопасность

Сервер проверяет подпись **initData** (Telegram.WebApp.initData) с помощью секретного ключа бота. Без валидной initData запрос к `/tkp-app/submit/` отклоняется (401).

### Проверка

Откройте в браузере `https://ваш-домен/tkp-app/` — должна загрузиться форма (справочники подтянутся по API). Полный сценарий: отправьте боту `/app`, нажмите кнопку, заполните форму и нажмите «Сформировать ТКП» — должен появиться переход по ссылке скачивания или открытие файла.

---

## Полезные команды

| Действие | Команда |
|----------|---------|
| Логи Gunicorn | `sudo journalctl -u tkp_generator -f` |
| Логи Nginx | `sudo tail -f /var/log/nginx/error.log` |
| Перезапуск приложения | `sudo systemctl restart tkp_generator` |
