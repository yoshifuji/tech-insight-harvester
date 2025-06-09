"""
Markdown writer for Docusaurus
Converts processed articles to Markdown files with front-matter
"""
import json
import re
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from slugify import slugify
from config import Config, DOCS_DIR, TEMPLATES_DIR, OUTPUT_DIR

class MarkdownWriter:
    """Converts processed articles to Docusaurus-compatible Markdown"""
    
    def __init__(self):
        self.config = Config()
        self.docs_dir = DOCS_DIR
        self.templates_dir = TEMPLATES_DIR
        
        # Ensure directories exist
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.jinja_env.filters['tojson'] = self._tojson_filter
    
    def _tojson_filter(self, value, indent=None):
        """Custom JSON filter for Jinja2"""
        return json.dumps(value, indent=indent, ensure_ascii=False)
    
    def create_markdown_file(self, article: Dict[str, Any]) -> str:
        """Create a Markdown file for a single article"""
        try:
            # Generate slug and filename
            slug = self._generate_slug(article)
            filename = f"{datetime.now().strftime('%Y%m%d')}-{slug}.md"
            filepath = self.docs_dir / filename
            
            # Prepare template context
            context = self._prepare_context(article, slug)
            
            # Load and render template
            template = self.jinja_env.get_template('article.md')
            content = template.render(**context)
            
            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Created: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"Error creating markdown for article: {e}")
            return ""
    
    def _generate_slug(self, article: Dict[str, Any]) -> str:
        """Generate URL-friendly slug from article title"""
        title = article.get('seo_title') or article.get('title', 'untitled')
        
        # Create base slug
        base_slug = slugify(title, max_length=50)
        
        # Ensure uniqueness by checking existing files
        slug = base_slug
        counter = 1
        
        while True:
            test_filename = f"{datetime.now().strftime('%Y%m%d')}-{slug}.md"
            test_filepath = self.docs_dir / test_filename
            
            if not test_filepath.exists():
                break
            
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def _prepare_context(self, article: Dict[str, Any], slug: str) -> Dict[str, Any]:
        """Prepare template context with cleaned data"""
        context = dict(article)
        context['slug'] = slug
        
        # Clean and format content
        content = article.get('content', '')
        context['content'] = self._clean_markdown_content(content)
        
        # Ensure required fields have defaults
        context.setdefault('seo_title', article.get('title', 'Untitled Article'))
        context.setdefault('summary', 'Article summary not available.')
        context.setdefault('tag', 'development')
        context.setdefault('author', '')
        context.setdefault('published_date', '')
        context.setdefault('source_domain', '')
        context.setdefault('word_count', 0)
        context.setdefault('extraction_method', 'unknown')
        context.setdefault('llm_model', 'unknown')
        context.setdefault('json_ld', {})
        
        # Format dates
        for date_field in ['crawled_at', 'llm_processed_at', 'published_date']:
            if context.get(date_field):
                context[date_field] = self._format_date(context[date_field])
        
        return context
    
    def _clean_markdown_content(self, content: str) -> str:
        """Clean content for Markdown output"""
        if not content:
            return "Content not available."
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Escape problematic characters for Markdown
        content = content.replace('---', '\\-\\-\\-')  # Avoid front-matter conflicts
        
        # Limit content length for readability
        max_length = 5000
        if len(content) > max_length:
            content = content[:max_length] + "\n\n*[Content truncated for readability]*"
        
        return content.strip()
    
    def _format_date(self, date_str: str) -> str:
        """Format date string for display"""
        try:
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M UTC')
            return date_str
        except:
            return date_str
    
    def process_articles(self, articles: List[Dict[str, Any]]) -> List[str]:
        """Process multiple articles into Markdown files"""
        created_files = []
        
        print(f"Creating Markdown files for {len(articles)} articles...")
        
        for i, article in enumerate(articles, 1):
            title = article.get('seo_title') or article.get('title', 'Unknown')
            print(f"[{i}/{len(articles)}] Creating: {title[:50]}...")
            
            filepath = self.create_markdown_file(article)
            if filepath:
                created_files.append(filepath)
        
        return created_files
    
    def create_index_file(self, articles: List[Dict[str, Any]]) -> str:
        """Create an index file listing all articles"""
        index_content = """---
title: "Tech Insights - Latest Articles"
description: "Automatically curated technology articles and insights"
---

# Tech Insights

Welcome to our automatically curated collection of technology articles and insights.

## Latest Articles

"""
        
        # Group articles by tag
        articles_by_tag = {}
        for article in articles:
            tag = article.get('tag', 'development')
            if tag not in articles_by_tag:
                articles_by_tag[tag] = []
            articles_by_tag[tag].append(article)
        
        # Generate content by tag
        for tag, tag_articles in sorted(articles_by_tag.items()):
            index_content += f"\n### {tag.title()}\n\n"
            
            for article in tag_articles[:10]:  # Limit to 10 per tag
                title = article.get('seo_title') or article.get('title', 'Untitled')
                summary = article.get('summary', '').split('.')[0] + '.'
                url = article.get('url', '')
                
                index_content += f"- **[{title}]({url})** - {summary}\n"
        
        index_content += f"\n\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*\n"
        
        # Write index file
        index_file = self.docs_dir / "intro.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"Created index file: {index_file}")
        return str(index_file)

def main():
    """Main markdown writer execution"""
    try:
        writer = MarkdownWriter()
        
        # Look for latest LLM processed articles
        input_file = OUTPUT_DIR / "llm_processed.json"
        if not input_file.exists():
            raise FileNotFoundError(f"LLM processed articles not found: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = data.get('articles', [])
        
        # Create Markdown files
        created_files = writer.process_articles(articles)
        
        # Create index file
        index_file = writer.create_index_file(articles)
        
        print(f"Markdown generation completed successfully!")
        print(f"Created {len(created_files)} article files")
        print(f"Index file: {index_file}")
        
        # Save file list for commit
        file_list = created_files + [index_file]
        with open(OUTPUT_DIR / "created_files.json", 'w') as f:
            json.dump({
                'created_at': datetime.utcnow().isoformat(),
                'files': file_list
            }, f, indent=2)
        
    except Exception as e:
        print(f"Markdown writer failed: {e}")
        raise

if __name__ == "__main__":
    main()