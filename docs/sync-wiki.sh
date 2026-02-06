#!/bin/bash
# Sync docs/wiki/ to GitHub wiki repository

set -e

WIKI_DIR="/tmp/nebulus-gantry.wiki"
SOURCE_DIR="$(pwd)/docs/wiki"

echo "📚 Nebulus Gantry Wiki Sync"
echo "=========================="
echo ""

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory not found: $SOURCE_DIR"
    echo "   Run this script from the project root directory"
    exit 1
fi

# Clone wiki if needed
if [ ! -d "$WIKI_DIR" ]; then
    echo "📥 Cloning wiki repository..."
    git clone https://github.com/jlwestsr/nebulus-gantry.wiki.git "$WIKI_DIR"
    echo ""
else
    echo "📂 Wiki repository already exists at: $WIKI_DIR"
    cd "$WIKI_DIR"
    echo "🔄 Pulling latest changes..."
    git pull origin master
    echo ""
fi

cd "$WIKI_DIR"

# Copy all markdown files
echo "📋 Copying wiki pages from $SOURCE_DIR..."
cp "$SOURCE_DIR"/*.md .
echo "   $(ls -1 *.md | wc -l) pages copied"
echo ""

# Create sidebar if it doesn't exist
if [ ! -f "_Sidebar.md" ]; then
    echo "📄 Creating sidebar navigation..."
    cat > _Sidebar.md << 'EOF'
### Getting Started
* [Home](Home)
* [Installation](Installation)
* [Quick Start Guide](Quick-Start-Guide)
* [Configuration](Configuration)

### Features
* [Chat Interface](Chat-Interface)
* [Long-Term Memory](Long-Term-Memory)
* [Knowledge Vault](Knowledge-Vault)
* [Admin Dashboard](Admin-Dashboard)
* [Model Switching](Model-Switching)

### Deployment
* [Docker Deployment](Docker-Deployment)
* [Production Checklist](Production-Checklist)
* [Reverse Proxy Setup](Reverse-Proxy-Setup)
* [Scaling & Performance](Scaling-Performance)

### Developers
* [Architecture](Architecture)
* [API Reference](API-Reference)
* [Development Setup](Development-Setup)
* [Testing](Testing)
* [Contributing](Contributing)

### Troubleshooting
* [Common Issues](Common-Issues)
* [Debugging Guide](Debugging-Guide)
EOF
    echo "   ✅ Sidebar created"
    echo ""
fi

# Show changes
echo "📊 Changes detected:"
git status --short
echo ""

# Commit and push
if [ -n "$(git status --porcelain)" ]; then
    read -p "📤 Push changes to GitHub wiki? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add *.md
        git commit -m "docs: sync wiki pages from main repository"
        git push origin master
        echo ""
        echo "✅ Wiki pages published successfully!"
        echo "🔗 View at: https://github.com/jlwestsr/nebulus-gantry/wiki"
    else
        echo ""
        echo "⏸️  Changes staged but not pushed"
        echo "   Run 'cd $WIKI_DIR && git push origin master' to push later"
    fi
else
    echo "✅ Wiki already up to date - no changes detected"
fi
