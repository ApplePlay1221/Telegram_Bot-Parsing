# 🤖 Telegram Bot для автопостинга с Хабра (Python хаб)

## 📌 Описание
Бот автоматически собирает новые статьи из хаба **Python** на Хабре и публикует их в Telegram-канал с кратким содержанием.

## ⚙️ Функционал
- Парсинг статей с `https://habr.com/ru/hubs/python/articles/`
- Извлечение: заголовок, автор, дата, теги, краткое содержание
- Автопостинг в Telegram канал
- База данных SQLite (без дубликатов)
- Проверка новых статей каждый час
- Команды для управления

## 📋 Команды
| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/check` | Проверить новые статьи |
| `/last` | Последние 5 статей |
| `/post_all` | Опубликовать все |
| `/today` | Статьи за сегодня |
| `/random` | Случайная статья |
| `/stats` | Статистика |
| `/search <текст>` | Поиск |
| `/authors` | Топ авторов |

## 🛠 Технологии
- Python 3.7+
- python-telegram-bot
- BeautifulSoup4
- SQLite3
- Requests
- Schedule

## 📦 Установка
```bash
pip install -r requirements.txt
```

Создать `.env`:
```
TELEGRAM_BOT_TOKEN=ваш_токен
TELEGRAM_CHANNEL_ID=@канал
```

Запуск:
```bash
python bot.py
```

## 📁 Структура
- `bot.py` - основной код бота
- `parser.py` - парсер Хабра
- `database.py` - работа с SQLite
- `config.py` - настройки
- `requirements.txt` - зависимости

## 🔧 Настройка
Интервал проверки и URL в `config.py`:
```python
CHECK_INTERVAL = 3600  # 1 час
HABR_URL = 'https://habr.com/ru/hubs/python/articles/'
```
