#!/usr/bin/env bash
# Команда "Деплой": git add, commit, push
# Запуск: ./deploy-git.sh   или   ./deploy-git.sh "ваше сообщение коммита"
# По умолчанию сообщение: "текст коммита"

set -e
cd "$(dirname "$0")"
MSG="${1:-текст коммита}"

echo "git add ."
git add .

echo "git commit -m \"$MSG\""
git commit -m "$MSG"

echo "git push origin main"
git push origin main

echo "Готово."
