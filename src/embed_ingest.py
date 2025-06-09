"""
Embedding ingestion to Supabase pgvector
Generates embeddings for Markdown documents and stores them in vector database
"""
import json
import os
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import openai
import numpy as np
from supabase import create_client, Client
from config import Config, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DOCS_DIR, OUTPUT_DIR

class EmbeddingIngestor:
    """Handles embedding generation and vector database operations"""
    
    def __init__(self):
        self.config = Config()
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Initialize Supabase client
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        
        # Ensure database tables exist
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure required database tables exist"""
        try:
            # Create articles table if not exists
            self.supabase.rpc('create_articles_table_if_not_exists').execute()
            
            # Create embeddings table if not exists
            self.supabase.rpc('create_embeddings_table_if_not_exists').execute()
            
        except Exception as e:
            print(f"Warning: Could not verify/create tables: {e}")
            # Tables might already exist or RPC functions not available
            pass
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []
    
    def extract_text_from_markdown(self, filepath: str) -> Dict[str, Any]:
        """Extract text content from Markdown file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split front matter and content
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    front_matter = parts[1]
                    body = parts[2]
                else:
                    front_matter = ""
                    body = content
            else:
                front_matter = ""
                body = content
            
            # Extract title from front matter
            title = ""
            for line in front_matter.split('\n'):
                if line.strip().startswith('title:'):
                    title = line.split(':', 1)[1].strip().strip('"\'')
                    break
            
            # Clean body text for embedding
            clean_text = self._clean_text_for_embedding(body)
            
            return {
                'title': title,
                'content': clean_text,
                'full_content': content,
                'filepath': filepath,
                'file_hash': self._calculate_file_hash(content)
            }
            
        except Exception as e:
            print(f"Error extracting text from {filepath}: {e}")
            return {}
    
    def _clean_text_for_embedding(self, text: str) -> str:
        """Clean text for better embedding quality"""
        import re
        
        # Remove markdown syntax
        text = re.sub(r'```[\s\S]*?```', '', text)  # Code blocks
        text = re.sub(r'`[^`]*`', '', text)  # Inline code
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # Images
        text = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', text)  # Links
        text = re.sub(r'#{1,6}\s*', '', text)  # Headers
        text = re.sub(r'\*{1,2}([^\*]*)\*{1,2}', r'\1', text)  # Bold/italic
        text = re.sub(r':::.*?:::', '', text, flags=re.DOTALL)  # Admonitions
        text = re.sub(r'<[^>]*>', '', text)  # HTML tags
        
        # Clean whitespace
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _calculate_file_hash(self, content: str) -> str:
        """Calculate hash of file content for change detection"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_existing_article(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Check if article already exists in database"""
        try:
            result = self.supabase.table('articles').select('*').eq('filepath', filepath).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            print(f"Error checking existing article: {e}")
        return None
    
    def upsert_article(self, article_data: Dict[str, Any]) -> Optional[str]:
        """Insert or update article in database"""
        try:
            # Prepare article record
            article_record = {
                'filepath': article_data['filepath'],
                'title': article_data['title'],
                'file_hash': article_data['file_hash'],
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Upsert article
            result = self.supabase.table('articles').upsert(article_record).execute()
            
            if result.data:
                return result.data[0]['id']
            
        except Exception as e:
            print(f"Error upserting article: {e}")
        
        return None
    
    def upsert_embedding(self, article_id: str, embedding: List[float], text: str) -> bool:
        """Insert or update embedding in database"""
        try:
            embedding_record = {
                'article_id': article_id,
                'embedding': embedding,
                'text_content': text[:2000],  # Truncate for storage
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Upsert embedding
            result = self.supabase.table('embeddings').upsert(embedding_record).execute()
            return bool(result.data)
            
        except Exception as e:
            print(f"Error upserting embedding: {e}")
            return False
    
    def process_markdown_file(self, filepath: str) -> bool:
        """Process a single Markdown file"""
        try:
            # Extract text content
            article_data = self.extract_text_from_markdown(filepath)
            if not article_data:
                return False
            
            # Check if file has changed
            existing_article = self.get_existing_article(filepath)
            if existing_article and existing_article.get('file_hash') == article_data['file_hash']:
                print(f"Skipping unchanged file: {filepath}")
                return True
            
            # Generate embedding
            embedding_text = f"{article_data['title']} {article_data['content']}"
            embedding = self.generate_embedding(embedding_text)
            
            if not embedding:
                print(f"Failed to generate embedding for: {filepath}")
                return False
            
            # Upsert article
            article_id = self.upsert_article(article_data)
            if not article_id:
                print(f"Failed to upsert article: {filepath}")
                return False
            
            # Upsert embedding
            success = self.upsert_embedding(article_id, embedding, embedding_text)
            if success:
                print(f"Successfully processed: {filepath}")
            else:
                print(f"Failed to upsert embedding: {filepath}")
            
            return success
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return False
    
    def process_all_markdown_files(self) -> Dict[str, Any]:
        """Process all Markdown files in docs directory"""
        markdown_files = list(DOCS_DIR.glob("**/*.md"))
        
        results = {
            'total_files': len(markdown_files),
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'files': []
        }
        
        print(f"Processing {len(markdown_files)} Markdown files...")
        
        for i, filepath in enumerate(markdown_files, 1):
            print(f"[{i}/{len(markdown_files)}] Processing: {filepath.name}")
            
            success = self.process_markdown_file(str(filepath))
            
            file_result = {
                'filepath': str(filepath),
                'success': success,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            if success:
                results['processed'] += 1
            else:
                results['failed'] += 1
            
            results['files'].append(file_result)
        
        return results
    
    def save_results(self, results: Dict[str, Any]) -> str:
        """Save processing results to JSON file"""
        output_file = OUTPUT_DIR / f"embedding_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Embedding results saved to: {output_file}")
        return str(output_file)

def main():
    """Main embedding ingestion execution"""
    try:
        ingestor = EmbeddingIngestor()
        results = ingestor.process_all_markdown_files()
        output_file = ingestor.save_results(results)
        
        print(f"\nEmbedding ingestion completed!")
        print(f"Total files: {results['total_files']}")
        print(f"Processed: {results['processed']}")
        print(f"Skipped: {results['skipped']}")
        print(f"Failed: {results['failed']}")
        print(f"Results: {output_file}")
        
    except Exception as e:
        print(f"Embedding ingestion failed: {e}")
        raise

if __name__ == "__main__":
    main()