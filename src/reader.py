"""
Article content reader and extractor
Fetches HTML and extracts main content using multiple strategies
"""
import json
import requests
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from config import OUTPUT_DIR, MERCURY_API_KEY

class ArticleReader:
    """Extracts clean article content from URLs"""
    
    def __init__(self):
        self.mercury_api_key = MERCURY_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def read_article(self, url: str) -> Dict[str, Any]:
        """Extract article content from URL"""
        try:
            # Try Mercury Parser API first if available
            if self.mercury_api_key:
                content = self._extract_with_mercury(url)
                if content:
                    return content
            
            # Fallback to custom extraction
            return self._extract_with_beautifulsoup(url)
            
        except Exception as e:
            print(f"Error reading article {url}: {e}")
            return {
                'url': url,
                'title': '',
                'content': '',
                'author': '',
                'published_date': '',
                'error': str(e),
                'extracted_at': datetime.utcnow().isoformat()
            }
    
    def _extract_with_mercury(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract content using Mercury Parser API"""
        try:
            api_url = "https://mercury.postlight.com/parser"
            headers = {
                'x-api-key': self.mercury_api_key,
                'Content-Type': 'application/json'
            }
            params = {'url': url}
            
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'url': url,
                    'title': data.get('title', ''),
                    'content': data.get('content', ''),
                    'author': data.get('author', ''),
                    'published_date': data.get('date_published', ''),
                    'word_count': data.get('word_count', 0),
                    'excerpt': data.get('excerpt', ''),
                    'lead_image_url': data.get('lead_image_url', ''),
                    'domain': data.get('domain', ''),
                    'extraction_method': 'mercury',
                    'extracted_at': datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            print(f"Mercury API failed for {url}: {e}")
        
        return None
    
    def _extract_with_beautifulsoup(self, url: str) -> Dict[str, Any]:
        """Extract content using BeautifulSoup with heuristics"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup)
            
            # Extract main content
            content = self._extract_content(soup)
            
            # Extract metadata
            author = self._extract_author(soup)
            published_date = self._extract_published_date(soup)
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'author': author,
                'published_date': published_date,
                'word_count': len(content.split()) if content else 0,
                'extraction_method': 'beautifulsoup',
                'extracted_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"BeautifulSoup extraction failed: {e}")
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title"""
        # Try various title selectors
        selectors = [
            'h1',
            '[property="og:title"]',
            '[name="twitter:title"]',
            'title',
            '.article-title',
            '.post-title',
            '.entry-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') or element.get_text(strip=True)
                if title and len(title) > 10:
                    return title
        
        return ''
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content"""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
            element.decompose()
        
        # Try content selectors in order of preference
        content_selectors = [
            'article',
            '[role="main"]',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            'main',
            '#content',
            '.article-body'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                # Clean up the content
                content = self._clean_content(element)
                if content and len(content) > 200:  # Minimum content length
                    return content
        
        # Fallback: try to find the largest text block
        paragraphs = soup.find_all('p')
        if paragraphs:
            content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
            if content:
                return content
        
        return ''
    
    def _clean_content(self, element) -> str:
        """Clean extracted content"""
        # Remove unwanted nested elements
        for unwanted in element(['script', 'style', 'nav', 'aside', 'footer', 'header', '.advertisement', '.social-share']):
            unwanted.decompose()
        
        # Get text with some formatting preserved
        text = element.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n\n'.join(lines)
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract article author"""
        selectors = [
            '[property="article:author"]',
            '[name="author"]',
            '.author',
            '.byline',
            '[rel="author"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get('content') or element.get_text(strip=True)
                if author:
                    return author
        
        return ''
    
    def _extract_published_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date"""
        selectors = [
            '[property="article:published_time"]',
            '[property="og:published_time"]',
            '[name="publish_date"]',
            'time[datetime]',
            '.published',
            '.date'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                date = element.get('content') or element.get('datetime') or element.get_text(strip=True)
                if date:
                    return date
        
        return ''
    
    def process_url_list(self, url_list_file: str) -> List[Dict[str, Any]]:
        """Process all URLs from crawler output"""
        with open(url_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = data.get('articles', [])
        processed_articles = []
        
        print(f"Processing {len(articles)} articles...")
        
        for i, article in enumerate(articles, 1):
            url = article['url']
            print(f"[{i}/{len(articles)}] Reading: {url}")
            
            content_data = self.read_article(url)
            
            # Merge with original crawler data
            merged_data = {**article, **content_data}
            processed_articles.append(merged_data)
            
            # Rate limiting
            time.sleep(0.5)
        
        return processed_articles
    
    def save_results(self, articles: List[Dict[str, Any]]) -> str:
        """Save processed articles to JSON file"""
        output_file = OUTPUT_DIR / f"cleaned_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'processed_at': datetime.utcnow().isoformat(),
                'total_articles': len(articles),
                'articles': articles
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Processed articles saved to: {output_file}")
        return str(output_file)

def main():
    """Main reader execution"""
    try:
        reader = ArticleReader()
        
        # Look for latest URL list
        url_list_file = OUTPUT_DIR / "url_list.json"
        if not url_list_file.exists():
            raise FileNotFoundError(f"URL list not found: {url_list_file}")
        
        articles = reader.process_url_list(str(url_list_file))
        output_file = reader.save_results(articles)
        
        # Also save as latest for pipeline consumption
        latest_file = OUTPUT_DIR / "cleaned_text.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump({
                'processed_at': datetime.utcnow().isoformat(),
                'total_articles': len(articles),
                'articles': articles
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Article reading completed successfully!")
        print(f"Latest results: {latest_file}")
        
    except Exception as e:
        print(f"Reader failed: {e}")
        raise

if __name__ == "__main__":
    main()