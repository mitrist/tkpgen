# Публикация на VM — что обновить

## 0. Выгрузка приложения в Git

Команды выполняются **на локальной машине** в каталоге проекта (например, `c:\Py_proj\dash_test` или `~/dash_test`).

### Первый раз (репозиторий ещё не создан)

```bash
# Инициализация репозитория (если папка ещё не под git)
git init

# Добавить удалённый репозиторий (подставьте свой URL)
git remote add origin https://github.com/USER/REPO.git
# или по SSH:
# git remote add origin git@github.com:USER/REPO.git

# Добавить все файлы (учитывается .gitignore: venv, db.sqlite3, TKP_output и т.д.)
git add .

# Первый коммит
git commit -m "Initial commit: TKP generator + договоры"

# Отправить в ветку main (или master)
git branch -M main
git push -u origin main
```

### Обычное обновление (код уже под git)

```bash
# Посмотреть изменённые файлы
git status

# Добавить все изменения
git add .

# Или добавить выборочно:
# git add proposals/ tkp_generator/ requirements.txt

# Коммит с сообщением
git commit -m "Описание изменений: договоры, поиск контрагентов, ..."

# Выгрузить на сервер (GitHub / GitLab / свой git)
git push origin main
```

### Если репозиторий уже есть и нужно только подключить папку

```bash
git init
git remote add origin https://github.com/USER/REPO.git
git fetch origin
git checkout -b main origin/main
# либо сразу клонировать в пустую папку: git clone https://github.com/USER/REPO.git .
```

**Важно:** В репозиторий не попадают (благодаря `.gitignore`): `db.sqlite3`, `venv/`, `TKP_output/`, `.env`. Шаблоны из `templates_docx/` и код миграций — попадают; при необходимости добавьте в `.gitignore` пути к файлам, которые не должны храниться в git.

---

## 1. Код и зависимости

- Выкатить актуальный код (git pull или копирование файлов).
- Обновить зависимости:
  ```bash
  pip install -r requirements.txt
  ```
  При необходимости: `pip install -r requirements.txt --upgrade`

## 2. Миграции БД

- Применить миграции (новые модели/поля: ContractRecord, изменения TKPRecord и т.д.):
  ```bash
  python manage.py migrate
  ```

## 3. Статика (если используется)

- Собрать статику для раздачи веб-сервером:
  ```bash
  python manage.py collectstatic --noinput
  ```

## 4. Файлы и каталоги на VM

- **templates_docx/** — скопировать/обновить шаблоны, в т.ч.:
  - `Шаблон договора_Дизайн_проект.docx` (договор по ТКП ДП).
- **TKP_output/** — каталог для сгенерированных ТКП/договоров (создаётся автоматически при первой генерации; при необходимости создать вручную и выставить права).
- **data/** — при наличии (например, complex_service_comments.json) — скопировать.

## 5. Переменные окружения (production)

- `SECRET_KEY` — задать свой ключ.
- `DEBUG=False`.
- `ALLOWED_HOSTS` — через запятую домен/IP VM, например: `ALLOWED_HOSTS=your-domain.ru,127.0.0.1`.

## 6. Перезапуск приложения

- Перезапустить gunicorn (или другой WSGI-сервер) и при необходимости веб-сервер (nginx/apache):
  ```bash
  sudo systemctl restart gunicorn
  # или
  sudo systemctl restart nginx
  ```

## 7. Опционально: LibreOffice / PDF

- Для генерации PDF из договоров/ТКП на VM должен быть установлен **LibreOffice** (или docx2pdf + MS Word на Windows). Иначе будет доступна только выдача DOCX.

---

**Итого минимум на VM:**  
`git pull` → `pip install -r requirements.txt` → `python manage.py migrate` → `python manage.py collectstatic --noinput` (если нужно) → обновить `templates_docx/` и при необходимости `data/` → перезапуск gunicorn.
