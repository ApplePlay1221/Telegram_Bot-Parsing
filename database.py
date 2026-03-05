import sqlite3
from datetime import datetime
import json

class Database:
    def __init__(self, db_name='habr_python.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        """Получение соединения с БД"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Инициализация базы данных с новым полем summary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Создание таблицы с полем summary
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    author TEXT,
                    published_date TEXT,
                    summary TEXT,  -- Новое поле для краткого содержания
                    tags TEXT,
                    views TEXT,
                    reading_time TEXT,
                    posted_to_telegram INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создание индексов
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON posts(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posted ON posts(posted_to_telegram)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON posts(published_date)')
            
            conn.commit()
    
    def add_post(self, post_data):
        """Добавление нового поста с кратким содержанием"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже такой пост
            cursor.execute('SELECT id FROM posts WHERE url = ?', (post_data['url'],))
            existing = cursor.fetchone()
            
            if existing:
                return False
            
            # Подготовка данных
            published_date = post_data['published_date']
            if isinstance(published_date, datetime):
                published_date = published_date.isoformat()
            
            # Вставка нового поста со всеми полями
            cursor.execute('''
                INSERT INTO posts 
                (title, url, author, published_date, summary, tags, views, reading_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_data['title'],
                post_data['url'],
                post_data.get('author', 'Неизвестный автор'),
                published_date,
                post_data.get('summary', ''),  # Краткое содержание
                post_data.get('tags', ''),
                post_data.get('views', ''),
                post_data.get('reading_time', '')
            ))
            
            conn.commit()
            return True
    
    def add_posts_bulk(self, posts_data):
        """Добавление нескольких постов за раз"""
        added_count = 0
        for post in posts_data:
            if self.add_post(post):
                added_count += 1
        return added_count
    
    def get_unposted_posts(self):
        """Получение всех неопубликованных постов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM posts 
                WHERE posted_to_telegram = 0 
                ORDER BY published_date ASC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def mark_as_posted(self, post_id):
        """Отметить пост как опубликованный"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE posts 
                SET posted_to_telegram = 1 
                WHERE id = ?
            ''', (post_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def mark_multiple_as_posted(self, post_ids):
        """Отметить несколько постов как опубликованные"""
        if not post_ids:
            return 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(post_ids))
            cursor.execute(f'''
                UPDATE posts 
                SET posted_to_telegram = 1 
                WHERE id IN ({placeholders})
            ''', post_ids)
            conn.commit()
            return cursor.rowcount
    
    def get_last_posts(self, limit=10, include_posted=True):
        """Получение последних постов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if include_posted:
                cursor.execute('''
                    SELECT * FROM posts 
                    ORDER BY published_date DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT * FROM posts 
                    WHERE posted_to_telegram = 0
                    ORDER BY published_date DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_posts_by_date(self, date):
        """Получение постов за конкретную дату"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM posts 
                WHERE DATE(published_date) = DATE(?)
                ORDER BY published_date DESC
            ''', (date,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def search_posts(self, query):
        """Поиск постов по заголовку, автору или содержанию"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM posts 
                WHERE title LIKE ? 
                   OR author LIKE ? 
                   OR summary LIKE ? 
                   OR tags LIKE ?
                ORDER BY published_date DESC 
                LIMIT 20
            ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_stats(self):
        """Получение статистики"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute('SELECT COUNT(*) as total FROM posts')
            total = cursor.fetchone()['total']
            
            cursor.execute('SELECT COUNT(*) as posted FROM posts WHERE posted_to_telegram = 1')
            posted = cursor.fetchone()['posted']
            
            # Статистика по авторам
            cursor.execute('''
                SELECT author, COUNT(*) as count 
                FROM posts 
                WHERE author IS NOT NULL AND author != ''
                GROUP BY author 
                ORDER BY count DESC 
                LIMIT 5
            ''')
            top_authors = [dict(row) for row in cursor.fetchall()]
            
            # Статистика по дням
            cursor.execute('''
                SELECT DATE(published_date) as date, COUNT(*) as count
                FROM posts 
                WHERE published_date >= DATE('now', '-7 days')
                GROUP BY DATE(published_date)
                ORDER BY date DESC
            ''')
            daily_stats = [dict(row) for row in cursor.fetchall()]
            
            return {
                'total': total,
                'posted': posted,
                'unposted': total - posted,
                'top_authors': top_authors,
                'daily_stats': daily_stats
            }