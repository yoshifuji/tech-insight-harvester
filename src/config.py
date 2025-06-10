"""
Configuration management for tech-insight-harvester
"""
import os
import yaml
from typing import Dict, List, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Central configuration management"""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            # Default to parent directory of src/
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)
        self.keywords = self._load_keywords()
        self.tags = self._load_tags()
        
    def _load_keywords(self) -> Dict[str, Any]:
        """Load keywords configuration"""
        keywords_file = self.base_path / "keywords.yaml"
        if not keywords_file.exists():
            raise FileNotFoundError(f"Keywords file not found: {keywords_file}")
        
        with open(keywords_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_tags(self) -> Dict[str, Any]:
        """Load tags taxonomy"""
        tags_file = self.base_path / "tags.yaml"
        if not tags_file.exists():
            raise FileNotFoundError(f"Tags file not found: {tags_file}")
        
        with open(tags_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @property
    def keyword_list(self) -> List[str]:
        """Get list of keywords to search for"""
        return self.keywords.get('keywords', [])
    
    @property
    def search_config(self) -> Dict[str, Any]:
        """Get search configuration"""
        return self.keywords.get('search_config', {})
    
    @property
    def tag_hierarchy(self) -> Dict[str, List[str]]:
        """Get tag hierarchy for LLM classification"""
        tags = dict(self.tags)
        tags.pop('tag_rules', None)  # Remove rules from hierarchy
        return tags
    
    @property
    def tag_rules(self) -> Dict[str, Any]:
        """Get tag selection rules"""
        return self.tags.get('tag_rules', {})
    
    @property
    def all_tags(self) -> List[str]:
        """Get flattened list of all available tags"""
        all_tags = []
        for category, tags in self.tag_hierarchy.items():
            all_tags.append(category)
            all_tags.extend(tags)
        return list(set(all_tags))

# Environment variables with defaults
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CX_ID = os.getenv('GOOGLE_CX_ID')
MERCURY_API_KEY = os.getenv('MERCURY_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# File paths
DOCS_DIR = Path("docs/auto")
TEMPLATES_DIR = Path("templates")
OUTPUT_DIR = Path("output")

# Ensure directories exist
DOCS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)