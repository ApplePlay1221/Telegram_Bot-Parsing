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
import random
import re

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
        self.db = Database('habr_python.db')
        self.parser = HabrParser()
        self.application = Application.builder().token(self.token).build()
        
        # Эмодзи для разных тем
        self.topic_emojis = {
            'python': '🐍',
            'ai': '🤖',
            'ml': '🧠',
            'data': '📊',
            'web': '🌐',
            'devops': '⚙️',
            'testing': '🧪',
            'security': '🔒',
            'default': '📰'
        }
    
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
            "/random - Случайная статья\n"
            "/stats - Статистика\n"
            "/search <запрос> - Поиск статей\n"
            "/authors - Топ авторов"
        )
    
    def _get_emoji_for_tags(self, tags):
        """Определение эмодзи по тегам"""
        tags_lower = tags.lower()
        
        if 'python' in tags_lower:
            return '🐍'
        elif any(word in tags_lower for word in ['ai', 'ии', 'нейросет', 'gpt']):
            return '🤖'
        elif any(word in tags_lower for word in ['ml', 'machine', 'обучен']):
            return '🧠'
        elif any(word in tags_lower for word in ['data', 'анализ', 'дата']):
            return '📊'
        elif any(word in tags_lower for word in ['web', 'django', 'flask']):
            return '🌐'
        elif any(word in tags_lower for word in ['devops', 'docker', 'kubernetes']):
            return '⚙️'
        elif any(word in tags_lower for word in ['test', 'тестирован']):
            return '🧪'
        elif any(word in tags_lower for word in ['security', 'безопасн']):
            return '🔒'
        else:
            return '📰'
    
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
                
                # Добавляем краткое содержание
                summary = post.get('summary', '')
                if summary:
                    # Обрезаем summary для списка
                    short_summary = summary[:100] + "..." if len(summary) > 100 else summary
                else:
                    short_summary = "Нет описания"
                
                message += f"{i}. {status} <b>{post['title']}</b>\n"
                message += f"   📅 {date_str} | 👤 {post['author']}\n"
                message += f"   📝 {short_summary}\n"
                message += f"   🔗 {post['url']}\n\n"
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text("📭 В базе нет статей")
    
    async def random_command(self, update, context):
        """Показать случайную статью"""
        posts = self.db.get_last_posts(100)
        
        if posts:
            post = random.choice(posts)
            
            # Формируем сообщение со случайной статьей
            emoji = self._get_emoji_for_tags(post['tags'])
            date_str = datetime.fromisoformat(post['published_date']).strftime('%d.%m.%Y %H:%M')
            
            message = f"{emoji} <b>{post['title']}</b>\n\n"
            message += f"👤 Автор: {post['author']}\n"
            message += f"📅 Дата: {date_str}\n"
            message += f"🏷 Теги: {post['tags']}\n\n"
            
            if post.get('summary'):
                message += f"📝 <b>Кратко:</b>\n{post['summary']}\n\n"
            
            message += f"🔗 <a href='{post['url']}'>Читать полностью</a>"
            
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text("📭 В базе нет статей")
    
    async def today_command(self, update, context):
        """Показать статьи за сегодня"""
        today = datetime.now().date().isoformat()
        posts = self.db.get_posts_by_date(today)
        
        if posts:
            message = f"📰 Статьи за сегодня ({len(posts)}):\n\n"
            for post in posts:
                status = "✅" if post['posted_to_telegram'] else "⏳"
                emoji = self._get_emoji_for_tags(post['tags'])
                message += f"{status} {emoji} <b>{post['title']}</b>\n"
                message += f"   👤 {post['author']}\n"
                if post.get('summary'):
                    short_summary = post['summary'][:100] + "..." if len(post['summary']) > 100 else post['summary']
                    message += f"   📝 {short_summary}\n"
                message += "\n"
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text("📭 За сегодня статей нет")
    
    async def post_article(self, post):
        """Публикация статьи в Telegram с кратким содержанием"""
        try:
            published_date = datetime.fromisoformat(post['published_date'])
            date_str = published_date.strftime('%d.%m.%Y %H:%M')
            
            # Выбираем эмодзи по тегам
            emoji = self._get_emoji_for_tags(post['tags'])
            
            # Формируем заголовок
            message = f"{emoji} <b>{post['title']}</b>\n\n"
            
            # Мета-информация
            message += f"👤 <b>Автор:</b> {post['author']}\n"
            message += f"📅 <b>Дата:</b> {date_str}\n"
            
            if post['tags']:
                message += f"🏷 <b>Теги:</b> {post['tags']}\n"
            
            # Краткое содержание (самое важное!)
            if post.get('summary'):
                message += f"\n📝 <b>О чем статья:</b>\n"
                message += f"<i>{post['summary']}</i>\n"
            
            # Время чтения (если есть)
            if post.get('reading_time'):
                message += f"\n⏱ <b>Время чтения:</b> {post['reading_time']}\n"
            
            # Ссылка на статью
            message += f"\n🔗 <a href='{post['url']}'>Читать полную версию на Хабре</a>\n"
            
            # Хештеги
            message += f"\n#python #habr #программирование"
            
            # Добавляем хештеги из тегов (первые 3)
            if post['tags']:
                tag_list = post['tags'].split(', ')[:3]
                for tag in tag_list:
                    # Очищаем тег для хештега
                    clean_tag = re.sub(r'[^a-zA-Z0-9а-яА-Я]', '', tag)
                    if clean_tag:
                        message += f" #{clean_tag}"
            
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
                await asyncio.sleep(3)  # Задержка 3 секунды между постами
        
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
    
    async def search_command(self, update, context):
        """Поиск статей"""
        if not context.args:
            await update.message.reply_text("❌ Укажите поисковый запрос. Пример: /search Python")
            return
        
        query = ' '.join(context.args)
        posts = self.db.search_posts(query)
        
        if posts:
            message = f"🔍 Результаты поиска по запросу '{query}':\n\n"
            for post in posts[:5]:
                date_str = datetime.fromisoformat(post['published_date']).strftime('%d.%m.%Y')
                emoji = self._get_emoji_for_tags(post['tags'])
                
                message += f"{emoji} <b>{post['title']}</b>\n"
                message += f"   📅 {date_str} | 👤 {post['author']}\n"
                if post.get('summary'):
                    short_summary = post['summary'][:80] + "..." if len(post['summary']) > 80 else post['summary']
                    message += f"   📝 {short_summary}\n"
                message += f"   🔗 {post['url']}\n\n"
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
            
            # Добавляем последнюю активность
            message += "\n📊 Последние публикации:\n"
            last_posts = self.db.get_last_posts(3)
            for post in last_posts:
                date_str = datetime.fromisoformat(post['published_date']).strftime('%d.%m')
                message += f"   • {date_str} - {post['title'][:50]}...\n"
            
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text("📭 Нет данных об авторах")
    
    async def stats_command(self, update, context):
        """Показать статистику"""
        stats = self.db.get_stats()
        
        message = f"📊 Статистика бота (хаб Python):\n\n"
        message += f"📚 Всего статей: {stats['total']}\n"
        message += f"✅ Опубликовано: {stats['posted']}\n"
        message += f"⏳ Ожидают: {stats['unposted']}\n\n"
        
        if stats['top_authors']:
            message += f"🏆 Топ авторов:\n"
            for author in stats['top_authors']:
                message += f"   • {author['author']}: {author['count']} ст.\n"
        
        if stats['daily_stats']:
            message += f"\n📅 Статистика за последние 7 дней:\n"
            for day in stats['daily_stats']:
                date = datetime.strptime(day['date'], '%Y-%m-%d').strftime('%d.%m')
                message += f"   • {date}: {day['count']} ст.\n"
        
        await update.message.reply_text(message)
    
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
        self.application.add_handler(CommandHandler("post_all", self.check_command))
        self.application.add_handler(CommandHandler("today", self.today_command))
        self.application.add_handler(CommandHandler("random", self.random_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("authors", self.authors_command))
        
        # Запуск планировщика
        scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Запуск бота
        print("🤖 Бот запущен и готов к работе!")
        print(f"📊 База данных: habr_python.db")
        print(f"📰 Отслеживаемый хаб: Python")
        print(f"⏱ Проверка каждые {Config.CHECK_INTERVAL} секунд")
        self.application.run_polling()

if __name__ == '__main__':
    bot = HabrPythonBot()
    bot.run()