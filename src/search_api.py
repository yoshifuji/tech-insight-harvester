"""
FastAPI semantic search API
Provides /search endpoint for cosine similarity search in pgvector
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import create_client, Client
from config import OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Initialize FastAPI app
app = FastAPI(
    title="Tech Insight Harvester Search API",
    description="Semantic search API for technology articles",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

class SearchResult(BaseModel):
    """Search result model"""
    id: str
    title: str
    filepath: str
    similarity: float
    text_preview: str
    url: Optional[str] = None

class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float

class SearchAPI:
    """Semantic search functionality"""
    
    def __init__(self):
        self.openai_client = openai_client
        self.supabase = supabase_client
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=query,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {e}")
    
    def search_similar_articles(self, query_embedding: List[float], limit: int = 10, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar articles using cosine similarity"""
        try:
            # Use Supabase RPC function for vector similarity search
            result = self.supabase.rpc(
                'search_articles',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': threshold,
                    'match_count': limit
                }
            ).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            # Fallback to manual similarity calculation if RPC not available
            return self._manual_similarity_search(query_embedding, limit, threshold)
    
    def _manual_similarity_search(self, query_embedding: List[float], limit: int, threshold: float) -> List[Dict[str, Any]]:
        """Manual similarity search fallback"""
        try:
            # Get all embeddings
            result = self.supabase.table('embeddings').select('*, articles(*)').execute()
            
            if not result.data:
                return []
            
            import numpy as np
            
            query_vec = np.array(query_embedding)
            similarities = []
            
            for row in result.data:
                if row['embedding']:
                    doc_vec = np.array(row['embedding'])
                    similarity = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec))
                    
                    if similarity >= threshold:
                        similarities.append({
                            'id': row['article_id'],
                            'title': row['articles']['title'] if row['articles'] else '',
                            'filepath': row['articles']['filepath'] if row['articles'] else '',
                            'similarity': float(similarity),
                            'text_content': row['text_content']
                        })
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search failed: {e}")
    
    def format_search_results(self, results: List[Dict[str, Any]], query: str) -> List[SearchResult]:
        """Format search results for API response"""
        formatted_results = []
        
        for result in results:
            # Generate preview text
            text_preview = result.get('text_content', '')[:200]
            if len(text_preview) == 200:
                text_preview += "..."
            
            # Generate URL from filepath
            filepath = result.get('filepath', '')
            url = None
            if filepath:
                # Convert filepath to URL (adjust based on your deployment)
                filename = filepath.split('/')[-1].replace('.md', '')
                url = f"/docs/{filename}"
            
            formatted_results.append(SearchResult(
                id=result.get('id', ''),
                title=result.get('title', 'Untitled'),
                filepath=filepath,
                similarity=result.get('similarity', 0.0),
                text_preview=text_preview,
                url=url
            ))
        
        return formatted_results

# Initialize search API
search_api = SearchAPI()

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Tech Insight Harvester Search API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/search?q=your_query",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        result = search_api.supabase.table('articles').select('count').execute()
        db_status = "healthy" if result else "unhealthy"
    except:
        db_status = "unhealthy"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status
    }

@app.get("/search", response_model=SearchResponse)
async def search_articles(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="Similarity threshold")
):
    """
    Semantic search for technology articles
    
    - **q**: Search query (required)
    - **limit**: Maximum number of results (1-50, default: 10)
    - **threshold**: Similarity threshold (0.0-1.0, default: 0.7)
    """
    start_time = datetime.now()
    
    try:
        # Generate query embedding
        query_embedding = search_api.generate_query_embedding(q)
        
        # Search for similar articles
        raw_results = search_api.search_similar_articles(query_embedding, limit, threshold)
        
        # Format results
        formatted_results = search_api.format_search_results(raw_results, q)
        
        # Calculate search time
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            query=q,
            results=formatted_results,
            total_results=len(formatted_results),
            search_time_ms=round(search_time, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    try:
        # Get article count
        articles_result = search_api.supabase.table('articles').select('count').execute()
        article_count = len(articles_result.data) if articles_result.data else 0
        
        # Get embedding count
        embeddings_result = search_api.supabase.table('embeddings').select('count').execute()
        embedding_count = len(embeddings_result.data) if embeddings_result.data else 0
        
        return {
            "total_articles": article_count,
            "total_embeddings": embedding_count,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "search_api:app",
        host="0.0.0.0",
        port=12001,
        reload=True,
        access_log=True
    )