"""
Web crawler using Google Programmable Search API
Retrieves fresh URLs for keywords defined in keywords.yaml
"""
import json
import requests
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
from config import Config, GOOGLE_API_KEY, GOOGLE_CX_ID, OUTPUT_DIR

class TechCrawler:
    """Crawls tech articles using Google Custom Search API"""
    
    def __init__(self):
        self.config = Config()
        self.api_key = GOOGLE_API_KEY
        self.cx_id = GOOGLE_CX_ID
        
        if not self.api_key or not self.cx_id:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_CX_ID must be set")
    
    def search_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Search for articles related to a specific keyword"""
        search_config = self.config.search_config
        max_results = search_config.get('max_results_per_keyword', 10)
        date_range = search_config.get('date_range', 'week')
        language = search_config.get('language', 'en')
        
        # Calculate date restriction
        date_restrict = self._get_date_restrict(date_range)
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.api_key,
            'cx': self.cx_id,
            'q': keyword,
            'num': min(max_results, 10),  # API limit is 10 per request
            'lr': f'lang_{language}',
            'dateRestrict': date_restrict,
            'sort': 'date',
            'fileType': '',  # Exclude PDFs, docs, etc.
            'siteSearch': '',  # Could be configured to search specific sites
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('items', []):
                result = {
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'published_date': self._extract_date(item),
                    'keyword': keyword,
                    'source_domain': self._extract_domain(item.get('link', '')),
                    'crawled_at': datetime.utcnow().isoformat()
                }
                results.append(result)
            
            # Rate limiting
            time.sleep(0.1)
            return results
            
        except requests.RequestException as e:
            print(f"Error searching for keyword '{keyword}': {e}")
            return []
    
    def _get_date_restrict(self, date_range: str) -> str:
        """Convert date range to Google API format"""
        mapping = {
            'day': 'd1',
            'week': 'd7',
            'month': 'm1',
            'year': 'y1'
        }
        return mapping.get(date_range, 'd7')
    
    def _extract_date(self, item: Dict[str, Any]) -> str:
        """Extract publication date from search result"""
        # Try to get date from pagemap or other metadata
        pagemap = item.get('pagemap', {})
        
        # Check various date fields
        for date_field in ['metatags', 'article', 'newsarticle']:
            if date_field in pagemap:
                for meta in pagemap[date_field]:
                    for key in ['publishedtime', 'datepublished', 'article:published_time']:
                        if key in meta:
                            return meta[key]
        
        # Fallback to current date
        return datetime.utcnow().isoformat()
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return ''
    
    def crawl_all_keywords(self) -> List[Dict[str, Any]]:
        """Crawl articles for all configured keywords"""
        all_results = []
        keywords = self.config.keyword_list
        
        print(f"Starting crawl for {len(keywords)} keywords...")
        
        for i, keyword in enumerate(keywords, 1):
            print(f"[{i}/{len(keywords)}] Searching: {keyword}")
            results = self.search_keyword(keyword)
            all_results.extend(results)
            print(f"  Found {len(results)} articles")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)
        
        print(f"Total unique articles found: {len(unique_results)}")
        return unique_results
    
    def save_results(self, results: List[Dict[str, Any]]) -> str:
        """Save crawl results to JSON file"""
        output_file = OUTPUT_DIR / f"url_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'crawled_at': datetime.utcnow().isoformat(),
                'total_articles': len(results),
                'articles': results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to: {output_file}")
        return str(output_file)

def main():
    """
    Runs the full crawling workflow, saving results and handling errors to ensure pipeline continuity.
    
    This function instantiates the crawler, retrieves articles for all configured keywords, and saves the results to timestamped and "latest" JSON files. If API credentials are missing or any error occurs, it creates an empty output file with error metadata to allow downstream processes to continue.
    """
    try:
        crawler = TechCrawler()
        results = crawler.crawl_all_keywords()
        output_file = crawler.save_results(results)
        
        # Also save as latest for pipeline consumption
        latest_file = OUTPUT_DIR / "url_list.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump({
                'crawled_at': datetime.utcnow().isoformat(),
                'total_articles': len(results),
                'articles': results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Crawling completed successfully!")
        print(f"Latest results: {latest_file}")
        
    except ValueError as e:
        if "GOOGLE_API_KEY" in str(e):
            print(f"Warning: {e}")
            print("Creating empty output file for pipeline continuation...")
            # Create empty output file so pipeline can continue
            latest_file = OUTPUT_DIR / "url_list.json"
            with open(latest_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'crawled_at': datetime.utcnow().isoformat(),
                    'total_articles': 0,
                    'articles': [],
                    'error': 'Missing API credentials'
                }, f, indent=2, ensure_ascii=False)
            print(f"Empty results file created: {latest_file}")
        else:
            raise
    except Exception as e:
        print(f"Crawler failed: {e}")
        # Create empty output file so pipeline can continue
        latest_file = OUTPUT_DIR / "url_list.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump({
                'crawled_at': datetime.utcnow().isoformat(),
                'total_articles': 0,
                'articles': [],
                'error': str(e)
            }, f, indent=2, ensure_ascii=False)
        print(f"Error output file created: {latest_file}")
        raise

if __name__ == "__main__":
    main()