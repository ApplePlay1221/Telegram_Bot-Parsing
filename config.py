import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')  # @channel_username или -1001234567890
    DATABASE_URL = 'sqlite:///habr_python.db'
    CHECK_INTERVAL = 3600  # Проверка новых постов каждый час
    HABR_URL = 'https://habr.com/ru/hubs/python/articles/'  # Ссылка на хаб Python
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'