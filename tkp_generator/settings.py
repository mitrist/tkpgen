"""
Django settings for tkp_generator project.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(key, default=None):
    """Значение из переменных окружения."""
    return os.environ.get(key, default)


def _path_from_env(key: str, default: Path) -> Path:
    """
    Абсолютный путь из окружения или default.
    Относительный путь в переменной считается от BASE_DIR (удобно для локальной разработки).
    """
    raw = _env(key)
    if not raw or not str(raw).strip():
        return default
    p = Path(str(raw).strip()).expanduser()
    if not p.is_absolute():
        p = (BASE_DIR / p).resolve()
    return p


SECRET_KEY = _env('SECRET_KEY', 'django-insecure-tkp-gen-dev-key-change-in-production')
DEBUG = _env('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = _env('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'proposals',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tkp_generator.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tkp_generator.wsgi.application'

# БД и сгенерированные PDF/DOCX можно вынести в постоянный каталог вне дерева git (см. DEPLOY.md)
SQLITE_DB_PATH = _path_from_env('SQLITE_DB_PATH', BASE_DIR / 'db.sqlite3')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': SQLITE_DB_PATH,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    *([] if not (BASE_DIR / 'static').exists() else [BASE_DIR / 'static']),
    *([] if not (BASE_DIR / 'images').exists() else [BASE_DIR / 'images']),
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Вход по паролю: до авторизации доступ закрыт
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Папка с шаблонами .docx
TEMPLATES_DOCX_DIR = BASE_DIR / 'templates_docx'
# Папка для сформированных PDF и DOCX (ТКП и договоры); переопределяется TKP_OUTPUT_DIR в .env
TKP_OUTPUT_DIR = _path_from_env('TKP_OUTPUT_DIR', BASE_DIR / 'TKP_output')

# Гарантируем наличие каталогов (удобно при первом запуске с путями в /var/lib/...)
Path(SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
Path(TKP_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yandex.ru'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = '...'
EMAIL_HOST_PASSWORD = '...'
DEFAULT_FROM_EMAIL = 'mitrist12@yandex.com'

# API для Telegram/OpenClaw: ключ в заголовке X-API-Key или Authorization: Bearer
TKP_TELEGRAM_API_KEY = _env('TKP_TELEGRAM_API_KEY', '')
# Опционально: id пользователя Django для created_by при создании ТКП из бота
TKP_TELEGRAM_BOT_USER_ID = _env('TKP_TELEGRAM_BOT_USER_ID', '') or None

# Telegram бот и OpenClaw для моста ТКП
TELEGRAM_BOT_TOKEN = _env('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_WEBHOOK_SECRET = _env('TELEGRAM_WEBHOOK_SECRET', '') or None
# URL сайта для Mini App (HTTPS в проде): например https://nacpro-web-service.ru
TKP_MINIAPP_BASE_URL = (_env('TKP_MINIAPP_BASE_URL', '') or '').rstrip('/')
OPENCLAW_GATEWAY_URL = _env('OPENCLAW_GATEWAY_URL', '')
OPENCLAW_API_KEY = _env('OPENCLAW_API_KEY', '')

# MAX bot + Mini App
MAX_ENABLED = _env('MAX_ENABLED', 'False').lower() in ('true', '1', 'yes')
MAX_BOT_TOKEN = _env('MAX_BOT_TOKEN', '')
MAX_WEBHOOK_SECRET = _env('MAX_WEBHOOK_SECRET', '') or None
MAX_MINIAPP_BASE_URL = (_env('MAX_MINIAPP_BASE_URL', '') or '').rstrip('/')
MAX_API_BASE_URL = (_env('MAX_API_BASE_URL', 'https://platform-api.max.ru') or 'https://platform-api.max.ru').rstrip('/')
MAX_INITDATA_TTL_SECONDS = int(_env('MAX_INITDATA_TTL_SECONDS', '86400'))
# Временный режим: разрешить вход в mini app без валидного initData.
# Использовать только для диагностики/временного обхода.
MAX_ALLOW_INSECURE_INITDATA = _env('MAX_ALLOW_INSECURE_INITDATA', 'False').lower() in ('true', '1', 'yes')