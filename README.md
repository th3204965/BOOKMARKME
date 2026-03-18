# 🔖 BookmarkMe

**AI-powered bookmark organizer** — beautify and reorganize your browser bookmarks using Google Gemini.

BookmarkMe takes your messy HTML bookmark export (from Chrome, Firefox, Edge, etc.), sends it to Gemini for intelligent reorganization, and generates a clean, categorized bookmark file ready to re-import.

## ✨ Features

- 🧠 **AI-powered categorization** — Gemini groups bookmarks into logical folders
- 🧹 **Deduplication** — Removes duplicate bookmarks automatically
- ✏️ **Title cleanup** — Fixes garbled or unhelpful bookmark titles
- 🔤 **Alphabetical sorting** — Bookmarks sorted within each folder
- 📂 **Browser-compatible output** — Generates standard Netscape Bookmark HTML

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- A [Google AI API key](https://aistudio.google.com)

### Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd bookmarkme

# Install dependencies
uv sync

# Set your API key
export GEMINI_API_KEY="your-api-key-here"
```

### Usage

```bash
# Organize bookmarks
uv run bookmarkme organize --input bookmarks.html --output organized.html

# Use a different model
uv run bookmarkme organize --input bookmarks.html --model gemini-3-flash

# Pass API key directly
uv run bookmarkme organize --input bookmarks.html --api-key "your-key"

# Get help
uv run bookmarkme --help
```

### How to Export Bookmarks

1. **Chrome**: `chrome://bookmarks` → ⋮ → Export bookmarks
2. **Firefox**: Bookmarks → Manage Bookmarks → Import and Backup → Export Bookmarks to HTML
3. **Edge**: `edge://favorites` → ⋮ → Export favorites

## 🛠️ Development

```bash
# Install dev dependencies
uv sync --group dev

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

## 📦 Project Structure

```
bookmarkme/
├── src/bookmarkme/
│   ├── __init__.py      # Package metadata
│   ├── cli.py           # Typer CLI entry point
│   ├── organizer.py     # Gemini API integration
│   └── parser.py        # HTML ↔ JSON bookmark parsing
├── tests/
│   └── sample_bookmarks.html
├── pyproject.toml       # Project config (uv, ruff)
└── README.md
```

## 📄 License

MIT
