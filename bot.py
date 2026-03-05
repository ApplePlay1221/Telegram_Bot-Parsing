import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config
from database import Database
from parser import HabrParser
import schedule
import time
import threading

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HabrPythonBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.channel_id = Config.TELEGRAM_CHANNEL_ID
        self.bot = Bot(token=self.token)
        self.db = Database('habr_python.db')  # SQLite база данных
        self.parser = HabrParser()
        self.application = Application.builder().token(self.token).build()
        
    async def start_command(self, update, context):
        """Обработка команды /start"""
        await update.message.reply_text(
            "👋 Привет! Я бот для автопостинга новостей с Хабра (хаб Python).\n\n"
            "📌 Команды:\n"
            "/start - Показать это сообщение\n"
            "/check - Проверить новые статьи\n"
            "/last - Показать последние статьи\n"
            "/post_all - Опубликовать все непрочитанные\n"
            "/today - Статьи за сегодня\n"
            "/stats - Статистика\n"
            "/search <запрос> - Поиск статей\n"
            "/authors - Топ авторов"
        )
    
    async def check_command(self, update, context):
        """Ручная проверка новых статей"""
        await update.message.reply_text("🔍 Проверяю новые статьи в хабе Python...")
        
        articles = self.parser.fetch_articles(pages=1)
        if articles:
            added = self.db.add_posts_bulk(articles)
            
            if added > 0:
                await update.message.reply_text(f"✅ Найдено {added} новых статей!")
                await self.post_new_articles()
            else:
                await update.message.reply_text("📭 Новых статей не найдено")
        else:
            await update.message.reply_text("❌ Не удалось получить статьи")
    
    async def last_command(self, update, context):
        """Показать последние статьи"""
        posts = self.db.get_last_posts(5)
        
        if posts:
            message = "📰 Последние статьи из хаба Python:\n\n"
            for i, post in enumerate(posts, 1):
                status = "✅" if post['posted_to_telegram'] else "⏳"
                date_str = datetime.fromisoformat(post['published_date']).strftime('%d.%m.%Y')
                message += f"{i}. {status} <b>{post['title']}</b>\n"
                message += f"   📅 {date_str} | 👤 {post['author']}\n"
                message += f"   🔗 {post['url']}\n\n"
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text("📭 В базе нет статей")
    
    async def post_all_command(self, update, context):
        """Опубликовать все непрочитанные статьи"""
        unposted = self.db.get_unposted_posts()
        if not unposted:
            await update.message.reply_text("📭 Нет непрочитанных статей")
            return
            
        await update.message.reply_text(f"🔄 Начинаю публикацию {len(unposted)} статей...")
        await self.post_new_articles()
        await update.message.reply_text("✅ Публикация завершена!")
    
    async def today_command(self, update, context):
        """Показать статьи за сегодня"""
        today = datetime.now().date().isoformat()
        posts = self.db.get_posts_by_date(today)
        
        if posts:
            message = f"📰 Статьи за сегодня ({len(posts)}):\n\n"
            for post in posts:
                status = "✅" if post['posted_to_telegram'] else "⏳"
                message += f"{status} <b>{post['title']}</b>\n"
                message += f"   👤 {post['author']}\n\n"
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text("📭 За сегодня статей нет")
    
    async def stats_command(self, update, context):
        """Показать статистику"""
        stats = self.db.get_stats()
        
        message = f"📊 Статистика бота (хаб Python):\n\n"
        message += f"Всего статей: {stats['total']}\n"
        message += f"Опубликовано: {stats['posted']}\n"
        message += f"Ожидают: {stats['unposted']}\n\n"
        
        if stats['top_authors']:
            message += f"🏆 Топ авторов:\n"
            for author in stats['top_authors']:
                message += f"   • {author['author']}: {author['count']} ст.\n"
        
        await update.message.reply_text(message)
    
    async def search_command(self, update, context):
        """Поиск статей"""
        if not context.args:
            await update.message.reply_text("❌ Укажите поисковый запрос. Пример: /search Python")
            return
        
        query = ' '.join(context.args)
        posts = self.db.search_posts(query)
        
        if posts:
            message = f"🔍 Результаты поиска по запросу '{query}':\n\n"
            for post in posts[:5]:  # Показываем первые 5 результатов
                date_str = datetime.fromisoformat(post['published_date']).strftime('%d.%m.%Y')
                message += f"• <b>{post['title']}</b>\n"
                message += f"  {date_str} | {post['author']}\n"
                message += f"  {post['url']}\n\n"
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ Ничего не найдено по запросу '{query}'")
    
    async def authors_command(self, update, context):
        """Показать топ авторов"""
        stats = self.db.get_stats()
        
        if stats['top_authors']:
            message = "🏆 Топ авторов хаба Python:\n\n"
            for i, author in enumerate(stats['top_authors'], 1):
                message += f"{i}. <b>{author['author']}</b> — {author['count']} статей\n"
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text("📭 Нет данных об авторах")
    
    async def post_article(self, post):
        """Публикация статьи в Telegram"""
        try:
            published_date = datetime.fromisoformat(post['published_date'])
            date_str = published_date.strftime('%d.%m.%Y %H:%M')
            
            message = f"🐍 <b>{post['title']}</b>\n\n"
            message += f"👤 Автор: {post['author']}\n"
            message += f"📅 Дата: {date_str}\n"
            
            if post['tags']:
                message += f"🏷 Теги: {post['tags']}\n"
            
            if post['preview_text']:
                preview = post['preview_text'][:300] + "..." if len(post['preview_text']) > 300 else post['preview_text']
                message += f"\n📝 {preview}\n"
            
            message += f"\n🔗 <a href='{post['url']}'>Читать на Хабре</a>"
            message += f"\n\n#python #habr"
            
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            
            logger.info(f"Опубликована статья: {post['title']}")
            return True
            
        except TelegramError as e:
            logger.error(f"Ошибка при отправке: {e}")
            return False
    
    async def post_new_articles(self):
        """Публикация всех новых статей"""
        unposted = self.db.get_unposted_posts()
        
        if not unposted:
            logger.info("Нет новых статей для публикации")
            return
        
        logger.info(f"Начинаю публикацию {len(unposted)} статей")
        
        posted_ids = []
        for post in unposted:
            success = await self.post_article(post)
            if success:
                posted_ids.append(post['id'])
                await asyncio.sleep(3)  # Задержка 3 секунды
        
        if posted_ids:
            self.db.mark_multiple_as_posted(posted_ids)
            logger.info(f"Опубликовано {len(posted_ids)} статей")
    
    async def scheduled_check(self):
        """Периодическая проверка"""
        logger.info("Плановая проверка хаба Python...")
        
        articles = self.parser.fetch_articles(pages=1)
        if articles:
            added = self.db.add_posts_bulk(articles)
            if added > 0:
                logger.info(f"Найдено {added} новых статей")
                await self.post_new_articles()
    
    def run_scheduler(self):
        """Запуск планировщика"""
        schedule.every(Config.CHECK_INTERVAL).seconds.do(
            lambda: asyncio.run_coroutine_threadsafe(self.scheduled_check(), self.application.loop)
        )
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def run(self):
        """Запуск бота"""
        # Добавляем обработчики
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("check", self.check_command))
        self.application.add_handler(CommandHandler("last", self.last_command))
        self.application.add_handler(CommandHandler("post_all", self.post_all_command))
        self.application.add_handler(CommandHandler("today", self.today_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("authors", self.authors_command))
        
        # Запуск планировщика
        scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Запуск бота
        print("🤖 Бот запущен и готов к работе!")
        self.application.run_polling()

if __name__ == '__main__':
    bot = HabrPythonBot()
    bot.run()