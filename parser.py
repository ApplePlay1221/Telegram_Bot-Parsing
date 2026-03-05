import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from config import Config

class HabrParser:
    def __init__(self):
        self.headers = {
            'User-Agent': Config.USER_AGENT
        }
        self.base_url = 'https://habr.com'
    
    def fetch_articles(self, pages=1):
        """Получение списка статей с хаба Python"""
        all_articles = []
        
        for page in range(1, pages + 1):
            try:
                if page == 1:
                    url = Config.HABR_URL
                else:
                    url = f"{Config.HABR_URL}page{page}/"
                
                print(f"Парсинг страницы: {url}")
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.find_all('article', class_='tm-articles-list__item')
                
                for article in articles:
                    article_data = self._parse_article(article)
                    if article_data:
                        all_articles.append(article_data)
                
                if pages > 1:
                    import time
                    time.sleep(2)
                    
            except Exception as e:
                print(f"Ошибка при парсинге страницы {page}: {e}")
                continue
        
        return all_articles
    
    def _parse_article(self, article):
        """Парсинг отдельной статьи"""
        try:
            # Заголовок
            title_element = article.find('h2', class_='tm-title')
            if not title_element:
                return None
                
            title_link = title_element.find('a')
            title = title_link.text.strip()
            url_suffix = title_link.get('href', '')
            url = f"{self.base_url}{url_suffix}"
            
            # Автор
            author_element = article.find('a', class_='tm-user-info__username')
            author = author_element.text.strip() if author_element else "Неизвестный автор"
            
            # Дата
            date_element = article.find('time')
            if date_element and date_element.get('datetime'):
                published_date = datetime.fromisoformat(date_element['datetime'].replace('Z', '+00:00'))
            else:
                published_date = datetime.now()
            
            # Извлечение краткого содержания (улучшенная версия)
            summary = self._extract_summary(article)
            
            # Теги
            tags = self._extract_tags(article)
            
            # Количество просмотров (если есть)
            views = self._extract_views(article)
            
            # Время чтения (если есть)
            reading_time = self._extract_reading_time(article)
            
            return {
                'title': title,
                'url': url,
                'author': author,
                'published_date': published_date,
                'summary': summary,  # Краткое содержание
                'tags': ', '.join(tags[:5]) if tags else "Python",
                'views': views,
                'reading_time': reading_time
            }
            
        except Exception as e:
            print(f"Ошибка при парсинге статьи: {e}")
            return None
    
    def _extract_summary(self, article):
        """Извлечение краткого содержания статьи"""
        summary = ""
        
        # Способ 1: Ищем первый параграф в теле статьи
        body = article.find('div', class_='tm-article-body')
        if body:
            # Ищем первый параграф с текстом
            first_paragraph = body.find('p')
            if first_paragraph:
                summary = first_paragraph.text.strip()
            else:
                # Если нет параграфа, берем весь текст
                summary = body.text.strip()
        
        # Способ 2: Если не нашли, ищем в сниппете
        if not summary:
            snippet = article.find('div', class_='tm-article-snippet')
            if snippet:
                summary = snippet.text.strip()
        
        # Способ 3: Ищем в заголовке превью
        if not summary:
            preview = article.find('div', class_='tm-article__preview')
            if preview:
                summary = preview.text.strip()
        
        # Очистка текста
        if summary:
            # Удаляем лишние пробелы и переносы строк
            summary = re.sub(r'\s+', ' ', summary)
            summary = re.sub(r'\n+', ' ', summary)
            
            # Ограничиваем длину до 300 символов
            if len(summary) > 300:
                # Ищем последнее предложение в пределах лимита
                truncated = summary[:300]
                last_sentence = truncated.rfind('. ')
                if last_sentence > 200:  # Если нашли предложение
                    summary = truncated[:last_sentence + 1]
                else:
                    summary = truncated + '...'
        
        return summary
    
    def _extract_tags(self, article):
        """Извлечение тегов статьи"""
        tags = []
        
        # Ищем теги в разных местах
        tags_container = article.find('div', class_='tm-article__tags')
        if tags_container:
            tag_links = tags_container.find_all('a', class_='tm-article__tag')
            tags = [tag.text.strip() for tag in tag_links]
        
        if not tags:
            # Пробуем найти в хабах
            hubs = article.find_all('a', class_='tm-publication-hub__link')
            tags = [hub.text.strip() for hub in hubs]
        
        return tags
    
    def _extract_views(self, article):
        """Извлечение количества просмотров"""
        views_element = article.find('span', class_='tm-article-views')
        if views_element:
            views_text = views_element.text.strip()
            # Извлекаем число
            views = re.sub(r'[^0-9]', '', views_text)
            return views if views else None
        return None
    
    def _extract_reading_time(self, article):
        """Извлечение времени чтения"""
        time_element = article.find('span', class_='tm-article-reading-time')
        if time_element:
            return time_element.text.strip()
        return None
    
    def get_full_article(self, article_url):
        """Получение полного текста статьи (для расширенного содержания)"""
        try:
            response = requests.get(article_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Находим тело статьи
            article_body = soup.find('div', class_='tm-article__body')
            if not article_body:
                return None
            
            # Удаляем ненужные элементы
            for element in article_body.find_all(['script', 'style', 'aside']):
                element.decompose()
            
            # Извлекаем все параграфы
            paragraphs = article_body.find_all('p')
            
            # Формируем краткое содержание из первых 3-4 параграфов
            content = []
            for p in paragraphs[:4]:
                text = p.text.strip()
                if text and len(text) > 20:  # Игнорируем слишком короткие параграфы
                    content.append(text)
            
            return ' '.join(content)
            
        except Exception as e:
            print(f"Ошибка при получении полной статьи: {e}")
            return None