import requests
from bs4 import BeautifulSoup
from datetime import datetime
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
            
            # Превью
            preview_text = ""
            preview_element = article.find('div', class_='tm-article-body')
            if not preview_element:
                preview_element = article.find('div', class_='tm-article-snippet')
            
            if preview_element:
                preview_text = preview_element.text.strip()
                if len(preview_text) > 500:
                    preview_text = preview_text[:500] + "..."
            
            # Теги
            tags = []
            tags_container = article.find('div', class_='tm-article__tags')
            if tags_container:
                tag_links = tags_container.find_all('a', class_='tm-article__tag')
                tags = [tag.text.strip() for tag in tag_links]
            
            if not tags:
                tags = ["Python"]
            
            return {
                'title': title,
                'url': url,
                'author': author,
                'published_date': published_date,
                'preview_text': preview_text,
                'tags': ', '.join(tags[:5])
            }
            
        except Exception as e:
            print(f"Ошибка при парсинге статьи: {e}")
            return None