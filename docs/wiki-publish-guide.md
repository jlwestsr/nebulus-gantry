# Wiki Publishing Guide

Guide to publishing the Nebulus Gantry wiki pages from `docs/wiki/` to GitHub Wiki.

---

## Overview

We have 20 wiki pages ready to publish:

**Status:**

- ✅ Home - Already published
- ⏳ 19 remaining pages to publish

**Location:**

- Source files: `docs/wiki/*.md`
- Destination: <https://github.com/jlwestsr/nebulus-gantry/wiki>

---

## Quick Publishing Checklist

### Pages to Publish

- [ ] Installation
- [ ] Quick-Start-Guide
- [ ] Configuration
- [ ] Chat-Interface
- [ ] Long-Term-Memory
- [ ] Knowledge-Vault
- [ ] Admin-Dashboard
- [ ] Model-Switching
- [ ] Docker-Deployment
- [ ] Production-Checklist
- [ ] Reverse-Proxy-Setup
- [ ] Scaling-Performance
- [ ] Architecture
- [ ] API-Reference
- [ ] Development-Setup
- [ ] Testing
- [ ] Contributing
- [ ] Common-Issues
- [ ] Debugging-Guide

---

## Publishing Methods

### Method 1: GitHub Web Interface (Manual)

**For each page:**

1. Navigate to <https://github.com/jlwestsr/nebulus-gantry/wiki>
2. Click **"New Page"**
3. Enter page title (e.g., "Installation")
4. Copy content from `docs/wiki/Installation.md`
5. Paste into editor
6. Click **"Save Page"**
7. Repeat for next page

**Pros:** Simple, no setup required
**Cons:** Tedious for 19 pages (~15-20 minutes)

### Method 2: Git Clone Wiki (Recommended)

GitHub wikis are actually Git repositories. You can clone and push.

**Setup:**

```bash
# Clone the wiki repository
cd /tmp
git clone https://github.com/jlwestsr/nebulus-gantry.wiki.git
cd nebulus-gantry.wiki

# Copy all wiki pages
cp /home/jlwestsr/projects/west_ai_labs/nebulus-gantry/docs/wiki/*.md .

# Commit and push
git add *.md
git commit -m "docs: publish all wiki pages"
git push origin master
```

**Pros:** Bulk publish all pages at once
**Cons:** Requires wiki to exist (create Home page first via web)

### Method 3: Automated Script

Use the provided script to copy files to wiki clone:

```bash
# From project root
bash docs/sync-wiki.sh
```

See script below.

---

## Sync Script

Create `docs/sync-wiki.sh`:

```bash
#!/bin/bash
# Sync docs/wiki/ to GitHub wiki repository

set -e

WIKI_DIR="/tmp/nebulus-gantry.wiki"
SOURCE_DIR="$(pwd)/docs/wiki"

echo "📚 Nebulus Gantry Wiki Sync"
echo "=========================="

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Clone wiki if needed
if [ ! -d "$WIKI_DIR" ]; then
    echo "📥 Cloning wiki repository..."
    git clone https://github.com/jlwestsr/nebulus-gantry.wiki.git "$WIKI_DIR"
else
    echo "📂 Wiki repository already cloned"
    cd "$WIKI_DIR"
    git pull origin master
fi

cd "$WIKI_DIR"

# Copy all markdown files
echo "📋 Copying wiki pages..."
cp "$SOURCE_DIR"/*.md .

# Show changes
echo ""
echo "📊 Changes:"
git status --short

# Commit and push
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    read -p "Push changes to GitHub? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add *.md
        git commit -m "docs: sync wiki pages from main repository"
        git push origin master
        echo "✅ Wiki pages published!"
        echo "🔗 View at: https://github.com/jlwestsr/nebulus-gantry/wiki"
    else
        echo "⏸️  Changes staged but not pushed"
    fi
else
    echo "✅ Wiki already up to date"
fi
```

**Make executable:**

```bash
chmod +x docs/sync-wiki.sh
```

**Usage:**

```bash
./docs/sync-wiki.sh
```

---

## Page Order

GitHub Wiki displays pages alphabetically by default. To create a logical reading order, use the sidebar.

**Edit `_Sidebar.md` in wiki repository:**

```markdown
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
```

---

## Verification

After publishing, verify:

**1. All pages exist:**

Navigate to: <https://github.com/jlwestsr/nebulus-gantry/wiki/_pages>

**Expected:** 20 pages listed

**2. Links work:**

Click through navigation in sidebar and footer links.

**3. Formatting correct:**

- Code blocks have syntax highlighting
- Tables render properly
- Images load (if any)
- Markdown renders correctly

**4. Search works:**

Use GitHub wiki search to find content.

---

## Maintenance

### Updating Pages

**Option 1 - Edit on GitHub:**

- Navigate to page on wiki
- Click "Edit" button
- Make changes
- Save

**Option 2 - Edit locally and sync:**

```bash
# Edit files in docs/wiki/
vim docs/wiki/Installation.md

# Commit changes
git add docs/wiki/Installation.md
git commit -m "docs: update Installation wiki page"
git push origin main

# Sync to wiki
./docs/sync-wiki.sh
```

### Keeping in Sync

The wiki repository and `docs/wiki/` are separate. Changes in one don't auto-update the other.

**Best practice:**

1. Edit in `docs/wiki/` (main repo)
2. Commit and push to main
3. Run sync script to update wiki
4. Or edit on wiki and manually copy back to `docs/wiki/`

**Why keep both?**

- `docs/wiki/` - Version controlled with code
- Wiki repository - Easy web editing, better search

---

## Troubleshooting

### Wiki Clone Fails

**Error:** `repository not found`

**Cause:** Wiki doesn't exist yet

**Fix:** Create the first page (Home) via web interface first

### Push Permission Denied

**Error:** `Permission denied (publickey)`

**Fix:** Ensure your SSH key is added to GitHub or use HTTPS:

```bash
git clone https://github.com/jlwestsr/nebulus-gantry.wiki.git
```

### Markdown Not Rendering

**Issue:** Code blocks showing raw markdown

**Fix:** Ensure code fences use triple backticks and language:

````markdown
```python
def hello():
    print("Hello")
```
````

### Images Not Loading

**Issue:** Images referenced don't show

**Fix:** GitHub wikis don't support relative paths well. Upload images to main repo:

```markdown
![Screenshot](https://raw.githubusercontent.com/jlwestsr/nebulus-gantry/main/docs/images/screenshot.png)
```

---

## Alternative: Keep Wiki in Main Repo

Instead of using GitHub's wiki feature, you could:

**1. Create docs site with MkDocs:**

```bash
pip install mkdocs mkdocs-material
mkdocs new .
# Edit mkdocs.yml
mkdocs serve  # Preview locally
mkdocs gh-deploy  # Deploy to GitHub Pages
```

**2. Use GitHub Pages:**

Configure GitHub Pages to serve from `/docs` folder.

**3. Use README navigation:**

Add comprehensive navigation in README linking to `docs/wiki/` files.

**Pros:**

- Version controlled with code
- Easier maintenance
- Automated deployments
- Better theme control

**Cons:**

- No wiki search feature
- Requires setup
- Separate deployment step

---

## Next Steps

1. **Choose publishing method** (recommend Method 2: Git Clone)
2. **Run sync script** or manually copy pages
3. **Create sidebar** for navigation
4. **Verify all pages** published correctly
5. **Test links** between pages
6. **Share wiki URL** with users

---

## Resources

- [GitHub Wiki Documentation](https://docs.github.com/en/communities/documenting-your-project-with-wikis)
- [Markdown Guide](https://www.markdownguide.org/)
- [MkDocs](https://www.mkdocs.org/) (alternative)
- [GitHub Pages](https://pages.github.com/) (alternative)

---

**Ready to publish?** Run: `./docs/sync-wiki.sh`
