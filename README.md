# AI News Bot

Telegram-бот для сбора немецких новостей, обработки текстов ML-моделями и отправки персональных дайджестов.

Проект состоит из Python-бэкенда и Rust-модуля `rust_core`. Rust собирает новости и тексты статей, Python очищает данные, определяет категории и тональность, делает краткие выжимки, сохраняет результат в SQLite и отвечает на команды Telegram.

## Возможности

- сбор новостей из DW и Tagesschau через Rust/PyO3;
- сохранение статей, подписчиков и пользовательских предпочтений в SQLite;
- краткие и расширенные дайджесты;
- мультиязычные выжимки DE/EN/RU;
- категории: `politics`, `economy`, `tech`, `world`, `society`, `other`;
- определение тональности;
- персональные рекомендации по избранным категориям, тональности и истории кликов;
- авторассылка подписчикам каждые 2 часа.

## Технологии

- Python 3.12;
- Poetry для виртуального окружения и Python-зависимостей;
- aiogram 3 для Telegram-бота;
- APScheduler для фоновой рассылки;
- SQLAlchemy + SQLite;
- transformers, torch, sentencepiece для ML-пайплайнов;
- Rust + PyO3 + maturin для Python-расширения `rust_core`.

## Структура

```text
backend/
  ai_module/        # очистка, категории, sentiment, summary/translation pipeline
  db/               # SQLAlchemy engine, session, ORM-модели
  telegram/         # aiogram handlers
  rust_core/        # Rust/PyO3 модуль для сбора новостей
  main.py           # точка входа бота
news.db             # локальная SQLite база, создается/обновляется при запуске
pyproject.toml      # Poetry окружение
poetry.toml         # локальная настройка .venv внутри проекта
```

## Подготовка

Установите системные инструменты:

- Python 3.12;
- Poetry;
- Rust toolchain с сайта `https://rustup.rs`;
- Microsoft C++ Build Tools, если Rust/PyO3 сборка на Windows попросит компилятор.

Проверьте:

```powershell
python --version
poetry --version
cargo --version
```

## Установка окружения

В корне проекта:

```powershell
poetry install
```

Poetry настроен создавать виртуальное окружение в `.venv` внутри проекта.

Далее соберите Rust-модуль в это окружение:

```powershell
poetry run maturin develop --manifest-path backend/rust_core/Cargo.toml --release
```

Проверьте импорт:

```powershell
poetry run python -c "from rust_core import fetch_news, fetch_full_articles; print('rust_core OK')"
```

## Настройка Telegram-токена

Создайте файл `.env` рядом с `pyproject.toml`:

```env
BOT_TOKEN=123456:telegram_bot_token
```

Можно начать с шаблона:

```powershell
Copy-Item .env.example .env
```

## Запуск

```powershell
poetry run python -m backend.main
```

При первом запуске SQLAlchemy создаст недостающие таблицы в `news.db`.

Первый вызов команд, использующих ML-модели, может быть долгим: `transformers` скачает модели Hugging Face в локальный кеш.

## Команды бота

| Команда | Назначение |
| --- | --- |
| `/start` | справка по командам |
| `/news` | короткая сводка |
| `/smartnews` | расширенная выжимка по полным текстам |
| `/multilangnews` | дайджест DE/EN/RU |
| `/categories` | статистика категорий за 3 дня |
| `/category <name>` | свежие новости выбранной категории |
| `/sentiment` | статистика тональности за 3 дня |
| `/subscribe` | включить авторассылку |
| `/unsubscribe` | отключить авторассылку |
| `/setfav <cats>` | сохранить любимые категории |
| `/setlang de\|en\|ru` | сохранить язык дайджеста |
| `/setsentiment positive\|neutral\|negative` | сохранить желаемую тональность |
| `/recommend` | персональная подборка |

## База данных

По умолчанию используется SQLite:

```python
DATABASE_URL = "sqlite:///news.db"
```

Основные таблицы:

- `news` - старая таблица для совместимости с короткими дайджестами;
- `articles` - полные статьи, категории, summary и sentiment;
- `subscribers` - подписчики авторассылки;
- `user_preferences` - настройки пользователя;
- `user_category_stats` - история интереса к категориям.

## Частые проблемы

### `poetry` не найден

Установите Poetry:

```powershell
python -m pip install --user pipx
python -m pipx ensurepath
pipx install poetry
```

Откройте новый терминал и повторите `poetry --version`.

Если Poetry установлен через `pip --user`, но команда все еще не находится, добавьте в `PATH`:

```text
C:\Users\Dmitriy\AppData\Roaming\Python\Python312\Scripts
```

До обновления `PATH` можно запускать Poetry по полному пути:

```powershell
C:\Users\Dmitriy\AppData\Roaming\Python\Python312\Scripts\poetry.exe install
C:\Users\Dmitriy\AppData\Roaming\Python\Python312\Scripts\poetry.exe run python -m backend.main
```

### `ModuleNotFoundError: No module named 'rust_core'`

Rust-модуль еще не установлен в Poetry-окружение. Выполните:

```powershell
poetry run maturin develop --manifest-path backend/rust_core/Cargo.toml --release
```

### Ошибка компиляции Rust на Windows

Установите Rust через `rustup` и Microsoft C++ Build Tools. После установки откройте новый терминал и повторите сборку.

### Долгий старт или загрузка моделей

Это ожидаемо при первом запуске. Модели `sshleifer/distilbart-cnn-12-6`, `Helsinki-NLP/opus-mt-de-en` и `facebook/nllb-200-distilled-600M` скачиваются один раз в кеш Hugging Face.

## Разработка

Полезные проверки:

```powershell
poetry run python -m compileall backend
cargo check --manifest-path backend/rust_core/Cargo.toml
```

Собранные файлы Rust, `.venv`, `.env`, `__pycache__` и локальная база исключены из Git через `.gitignore`.
