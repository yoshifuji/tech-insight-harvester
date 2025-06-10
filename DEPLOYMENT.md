# 🚀 Deployment Guide

This guide walks you through deploying Tech Insight Harvester to production.

## Prerequisites

- GitHub account
- Google Custom Search API credentials
- OpenAI API key
- Supabase account (for vector search)
- Mercury Parser API key (optional, for better content extraction)

## 1. Repository Setup

### Fork and Clone
```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/tech-insight-harvester.git
cd tech-insight-harvester
```

### Run Setup Script
```bash
./setup.sh
```

## 2. API Keys Configuration

### Required APIs

#### Google Custom Search API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the "Custom Search API"
4. Create credentials (API key)
5. Create a Custom Search Engine at [cse.google.com](https://cse.google.com/)
6. Note your Search Engine ID (CX)

#### OpenAI API
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an API key
3. Ensure you have credits for GPT-4o and text-embedding-3-small

#### Supabase Setup
1. Create account at [Supabase](https://supabase.com/)
2. Create a new project
3. Go to Settings → API to get your URL and service role key
4. Enable the pgvector extension:
   ```sql
   -- In Supabase SQL Editor
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
5. Create required tables:
   ```sql
   -- Articles table
   CREATE TABLE articles (
     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
     filepath TEXT UNIQUE NOT NULL,
     title TEXT,
     file_hash TEXT,
     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );

   -- Embeddings table
   CREATE TABLE embeddings (
     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
     article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
     embedding VECTOR(1536),
     text_content TEXT,
     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );

   -- Create index for vector similarity search
   CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);

   -- RPC function for similarity search
   CREATE OR REPLACE FUNCTION search_articles(
     query_embedding VECTOR(1536),
     match_threshold FLOAT DEFAULT 0.7,
     match_count INT DEFAULT 10
   )
   RETURNS TABLE (
     id UUID,
     title TEXT,
     filepath TEXT,
     similarity FLOAT,
     text_content TEXT
   )
   LANGUAGE plpgsql
   AS $$
   BEGIN
     RETURN QUERY
     SELECT
       a.id,
       a.title,
       a.filepath,
       1 - (e.embedding <=> query_embedding) AS similarity,
       e.text_content
     FROM embeddings e
     JOIN articles a ON e.article_id = a.id
     WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
     ORDER BY e.embedding <=> query_embedding
     LIMIT match_count;
   END;
   $$;
   ```

#### Mercury Parser (Optional)
1. Sign up at [Mercury Web Parser](https://mercury.postlight.com/web-parser/)
2. Get your API key for better content extraction

## 3. GitHub Secrets Configuration

Go to your repository → Settings → Secrets and variables → Actions

Add these secrets:

```
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CX_ID=your_custom_search_engine_id
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
MERCURY_API_KEY=your_mercury_api_key  # Optional
```

## 4. GitHub Pages Setup

1. Go to repository Settings → Pages
2. Source: "Deploy from a branch"
3. Branch: `gh-pages` (will be created automatically)
4. Folder: `/ (root)`

## 5. Customize Configuration

### Update Repository URLs
Edit these files to replace placeholder URLs:

1. `docusaurus.config.js`:
   ```javascript
   url: 'https://YOUR_USERNAME.github.io',
   baseUrl: '/tech-insight-harvester/',
   organizationName: 'YOUR_USERNAME',
   projectName: 'tech-insight-harvester',
   ```

2. `README.md`: Update badge URLs and links

3. `.github/workflows/*.yml`: Update any hardcoded repository references

### Configure Keywords
Edit `keywords.yaml` to add your topics of interest:

```yaml
keywords:
  - "your technology topic"
  - "another interesting keyword"
  # Add more keywords here
```

### Customize Tags
Edit `tags.yaml` to modify the classification taxonomy:

```yaml
your_category:
  - specific-tag-1
  - specific-tag-2
```

## 6. Test Local Setup

```bash
# Test configuration
cd src
python -c "from config import Config; print('✅ Config loaded')"

# Test pipeline (requires API keys in .env)
python run_pipeline.py

# Test Docusaurus build
cd ..
npm run build

# Start development server
npm start
```

## 7. Deploy to Production

### Initial Deployment
```bash
git add .
git commit -m "Configure for production deployment"
git push origin main
```

This will trigger:
1. Build workflow → Deploy to GitHub Pages
2. Vector sync workflow → Index content in Supabase

### Enable Daily Automation
The crawl workflow runs daily at 06:00 JST. To test it manually:

1. Go to Actions tab in GitHub
2. Select "Daily Content Crawl and Processing"
3. Click "Run workflow"

## 8. Monitor and Maintain

### Check Workflow Status
- Monitor GitHub Actions for failures
- Review daily PRs created by the bot
- Merge appropriate content PRs

### API Usage Monitoring
- OpenAI: Monitor token usage in OpenAI dashboard
- Google: Check quota usage in Google Cloud Console
- Supabase: Monitor database usage in Supabase dashboard

### Content Quality
- Review generated articles for accuracy
- Adjust LLM prompts in `src/llm.py` if needed
- Update keywords based on content quality

## 9. Troubleshooting

### Common Issues

**Build Failures**
- Check API keys are correctly set in GitHub Secrets
- Verify Supabase tables are created
- Check for syntax errors in configuration files

**No Content Generated**
- Verify keywords are discoverable via Google Search
- Check API quotas and limits
- Review crawler logs in GitHub Actions

**Search Not Working**
- Ensure pgvector extension is enabled in Supabase
- Verify embedding generation is working
- Check search API logs

### Debug Commands
```bash
# Test individual components
cd src
python crawler.py    # Test crawling
python reader.py     # Test content extraction
python llm.py        # Test LLM processing
python md_writer.py  # Test Markdown generation

# Check configuration
python -c "from config import Config; c = Config(); print(c.keyword_list)"
```

## 10. Advanced Configuration

### Custom Content Sources
Modify `src/crawler.py` to add additional content sources beyond Google Search.

### LLM Prompt Tuning
Edit prompts in `src/llm.py` to improve content quality and categorization.

### Search Improvements
Enhance the search API in `src/search_api.py` with filters, facets, and advanced ranking.

### Monitoring Setup
- Set up alerts for workflow failures
- Monitor API costs and usage
- Track content quality metrics

---

## Support

For issues and questions:
1. Check the [troubleshooting section](#9-troubleshooting)
2. Review GitHub Actions logs
3. Open an issue in the repository

Happy harvesting! 🤖📚