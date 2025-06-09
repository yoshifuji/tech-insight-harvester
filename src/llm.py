"""
LLM processing using OpenAI GPT-4o
Generates SEO titles, summaries, tags, and JSON-LD metadata
"""
import json
import openai
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import Config, OPENAI_API_KEY, OUTPUT_DIR

class LLMProcessor:
    """Processes articles using OpenAI GPT-4o"""
    
    def __init__(self):
        self.config = Config()
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set")
    
    def process_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single article with LLM"""
        try:
            # Prepare content for LLM
            content = self._prepare_content(article)
            
            # Generate LLM response
            llm_response = self._call_llm(content)
            
            # Parse and validate response
            processed_data = self._parse_llm_response(llm_response, article)
            
            return processed_data
            
        except Exception as e:
            print(f"Error processing article {article.get('url', 'unknown')}: {e}")
            return self._create_fallback_response(article, str(e))
    
    def _prepare_content(self, article: Dict[str, Any]) -> str:
        """Prepare article content for LLM processing"""
        title = article.get('title', '')
        content = article.get('content', '')
        snippet = article.get('snippet', '')
        
        # Truncate content if too long (GPT-4o context limit)
        max_content_length = 8000  # Leave room for prompt and response
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        return f"""
Title: {title}

Snippet: {snippet}

Content:
{content}
""".strip()
    
    def _call_llm(self, content: str) -> str:
        """Call OpenAI GPT-4o with structured prompt"""
        # Get available tags for the prompt
        all_tags = self.config.all_tags
        tag_hierarchy = self.config.tag_hierarchy
        tag_rules = self.config.tag_rules
        
        system_prompt = f"""You are an expert technical content analyst. Your task is to analyze technology articles and generate structured metadata.

Available tags (choose ONE that best fits):
{json.dumps(tag_hierarchy, indent=2)}

Tag selection rules:
- Choose exactly {tag_rules.get('max_tags_per_article', 1)} tag
- Prefer specific tags over general categories when applicable
- If no tag fits well, use "{tag_rules.get('fallback_tag', 'development')}"

You must respond with a valid JSON object containing:
1. "seo_title": An engaging, SEO-optimized title (50-60 characters)
2. "summary": A compelling 3-sentence summary highlighting key insights
3. "tag": Single most relevant tag from the provided taxonomy
4. "json_ld": TechArticle JSON-LD structured data

Example response format:
{{
  "seo_title": "Revolutionary AI Framework Transforms Enterprise Development",
  "summary": "A new AI framework promises to revolutionize how enterprises approach software development. The technology combines machine learning with traditional coding practices to automate routine tasks. Early adopters report 40% faster development cycles and improved code quality.",
  "tag": "ai",
  "json_ld": {{
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "headline": "Revolutionary AI Framework Transforms Enterprise Development",
    "description": "A new AI framework promises to revolutionize...",
    "author": {{"@type": "Person", "name": "Author Name"}},
    "datePublished": "2024-01-01T00:00:00Z",
    "publisher": {{"@type": "Organization", "name": "Publisher Name"}},
    "mainEntityOfPage": "https://example.com/article"
  }}
}}"""

        user_prompt = f"""Analyze this technology article and generate the required metadata:

{content}

Respond with valid JSON only."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")
    
    def _parse_llm_response(self, llm_response: str, original_article: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate LLM response"""
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in LLM response")
            
            json_str = llm_response[json_start:json_end]
            parsed_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['seo_title', 'summary', 'tag', 'json_ld']
            for field in required_fields:
                if field not in parsed_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate tag is in allowed list
            if parsed_data['tag'] not in self.config.all_tags:
                print(f"Warning: Invalid tag '{parsed_data['tag']}', using fallback")
                parsed_data['tag'] = self.config.tag_rules.get('fallback_tag', 'development')
            
            # Merge with original article data
            result = {
                **original_article,
                'seo_title': parsed_data['seo_title'],
                'summary': parsed_data['summary'],
                'tag': parsed_data['tag'],
                'json_ld': parsed_data['json_ld'],
                'llm_processed_at': datetime.utcnow().isoformat(),
                'llm_model': 'gpt-4o'
            }
            
            return result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse LLM response: {e}")
    
    def _create_fallback_response(self, article: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create fallback response when LLM processing fails"""
        title = article.get('title', 'Technology Article')
        
        return {
            **article,
            'seo_title': title[:60] if len(title) > 60 else title,
            'summary': article.get('snippet', 'Technology article summary not available.'),
            'tag': self.config.tag_rules.get('fallback_tag', 'development'),
            'json_ld': {
                "@context": "https://schema.org",
                "@type": "TechArticle",
                "headline": title,
                "description": article.get('snippet', ''),
                "datePublished": article.get('published_date', datetime.utcnow().isoformat()),
                "mainEntityOfPage": article.get('url', '')
            },
            'llm_error': error,
            'llm_processed_at': datetime.utcnow().isoformat(),
            'llm_model': 'fallback'
        }
    
    def process_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple articles"""
        processed_articles = []
        
        print(f"Processing {len(articles)} articles with LLM...")
        
        for i, article in enumerate(articles, 1):
            print(f"[{i}/{len(articles)}] Processing: {article.get('title', 'Unknown')[:50]}...")
            
            processed_article = self.process_article(article)
            processed_articles.append(processed_article)
        
        return processed_articles
    
    def save_results(self, articles: List[Dict[str, Any]]) -> str:
        """Save LLM processed articles to JSON file"""
        output_file = OUTPUT_DIR / f"llm_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'processed_at': datetime.utcnow().isoformat(),
                'total_articles': len(articles),
                'articles': articles
            }, f, indent=2, ensure_ascii=False)
        
        print(f"LLM processed articles saved to: {output_file}")
        return str(output_file)

def main():
    """Main LLM processing execution"""
    try:
        processor = LLMProcessor()
        
        # Look for latest cleaned text
        input_file = OUTPUT_DIR / "cleaned_text.json"
        if not input_file.exists():
            raise FileNotFoundError(f"Cleaned text not found: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = data.get('articles', [])
        processed_articles = processor.process_articles(articles)
        output_file = processor.save_results(processed_articles)
        
        # Also save as latest for pipeline consumption
        latest_file = OUTPUT_DIR / "llm_processed.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump({
                'processed_at': datetime.utcnow().isoformat(),
                'total_articles': len(processed_articles),
                'articles': processed_articles
            }, f, indent=2, ensure_ascii=False)
        
        print(f"LLM processing completed successfully!")
        print(f"Latest results: {latest_file}")
        
    except Exception as e:
        print(f"LLM processing failed: {e}")
        raise

if __name__ == "__main__":
    main()