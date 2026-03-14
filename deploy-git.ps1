# Команда "Деплой": git add, commit, push
# Запуск: .\deploy-git.ps1   или   .\deploy-git.ps1 "ваше сообщение коммита"
# По умолчанию сообщение: "текст коммита"

param(
    [string]$Message = "текст коммита"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "git add ."
git add .

Write-Host "git commit -m `"$Message`""
git commit -m "$Message"

Write-Host "git push origin main"
git push origin main

Write-Host "Готово."
