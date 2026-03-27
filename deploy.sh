#!/bin/bash
# Обновление приложения на VM после git pull
# Запуск из корня проекта: ./deploy.sh

set -e
cd "$(dirname "$0")"
VENV="${VENV:-./venv}"
PY="${VENV}/bin/python"
PIP="${VENV}/bin/pip"

echo "=== Установка зависимостей ==="
"$PIP" install -r requirements.txt -q

if [ -f "frontend/max-app/package.json" ]; then
  echo "=== Сборка MAX mini app ==="
  if command -v npm >/dev/null 2>&1; then
    (
      cd frontend/max-app
      npm install
      npm run build
    )
  else
    echo "WARNING: npm не найден, пропускаю сборку frontend/max-app"
  fi
fi

echo "=== Миграции ==="
"$PY" manage.py migrate --noinput

echo "=== Сбор статики ==="
"$PY" manage.py collectstatic --noinput

echo "=== Перезапуск Gunicorn ==="
sudo systemctl restart tkp_generator

echo "=== Готово ==="
sudo systemctl status tkp_generator --no-pager
