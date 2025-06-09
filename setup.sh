#!/bin/bash
# =============================================================================
# Tech Insight Harvester - Quick Setup Script
# =============================================================================

set -e

echo "🤖 Tech Insight Harvester - Quick Setup"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "keywords.yaml" ]; then
    echo "❌ Error: Please run this script from the tech-insight-harvester directory"
    exit 1
fi

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers (optional)
echo "🎭 Installing Playwright browsers (optional)..."
playwright install chromium || echo "⚠️  Playwright install failed - this is optional"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file - please edit it with your API keys"
else
    echo "✅ .env file already exists"
fi

# Test configuration loading
echo "🔧 Testing configuration..."
cd src
python -c "from config import Config; c = Config(); print(f'✅ Config loaded: {len(c.keyword_list)} keywords, {len(c.all_tags)} tags')" || {
    echo "❌ Configuration test failed"
    exit 1
}
cd ..

# Build Docusaurus site
echo "🏗️  Building Docusaurus site..."
npm run build

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys:"
echo "   - GOOGLE_API_KEY (required for crawling)"
echo "   - OPENAI_API_KEY (required for LLM processing)"
echo "   - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (required for search)"
echo ""
echo "2. Edit keywords.yaml to add your topics of interest"
echo ""
echo "3. Test the pipeline:"
echo "   cd src && python run_pipeline.py"
echo ""
echo "4. Start development server:"
echo "   npm start"
echo ""
echo "5. Deploy to GitHub Pages by pushing to main branch"
echo ""
echo "📚 Documentation: https://github.com/your-username/tech-insight-harvester"