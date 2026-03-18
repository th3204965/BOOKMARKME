# 🔖 BookmarkMe

AI-powered bookmark organizer — beautify and reorganize your browser bookmarks with Google Gemini.

## What It Does

BookmarkMe takes your exported browser bookmarks (a Netscape HTML file) and uses the Gemini API to intelligently categorize them into clean, organized folders — ready to re-import into any browser or bookmark manager like [Raindrop.io](https://raindrop.io).

### Features

- **AI Categorization** — Gemini classifies each bookmark into one of 11 strict categories (Development, Design, Entertainment, etc.)
- **Strict Deduplication** — Removes duplicate bookmarks by normalizing URLs (strips `www.`, trailing slashes, `utm_` tracking params, and matches `http`/`https`)
- **Concurrent Processing** — Splits bookmarks into batches and sends them to Gemini in parallel for fast processing
- **Structured Outputs** — Uses Pydantic schemas with Gemini's structured output mode to guarantee valid, parseable responses every time
- **Progress Bar** — Real-time CLI progress tracking with Rich
- **Clean Output** — Strips bloat (favicons, timestamps, metadata) and outputs a minimal, importable HTML file

## Installation

Requires **Python 3.12+** and [uv](https://docs.astral.sh/uv/).

```bash
# Clone the repository
git clone https://github.com/TahyrHussayn/bookmarkme.git
cd bookmarkme

# Install dependencies
uv sync
```

## Setup

1. Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com)
2. Create a `.env` file:

```bash
cp .env.example .env
# Edit .env and add your key
```

```env
GEMINI_API_KEY=your_api_key_here
```

## Usage

1. Export your bookmarks from Chrome/Firefox/Safari as an HTML file.
2. Place the exported file in the `bookmarks/` directory (as `bookmarks.html`).
3. Run:

```bash
uv run bookmarkme
```

The organized output will be written to `bookmarks/bookmarks_organized.html` — ready to re-import.

You can also specify custom paths:

```bash
uv run bookmarkme -i bookmarks/my_export.html -o bookmarks/my_organized.html
```

### Options

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--input` | `-i` | Path to the HTML bookmark file | `bookmarks/bookmarks.html` |
| `--output` | `-o` | Path for the organized output | `bookmarks/bookmarks_organized.html` |
| `--model` | `-m` | Gemini model to use | `gemini-2.5-pro` |
| `--api-key` | `-k` | API key (overrides `.env`) | `GEMINI_API_KEY` env var |

### Example Output

```
📂 Reading bookmarks from: bookmarks/bookmarks.html
✅ Found 2148 bookmarks

📚 Deduplicated: 2148 → 2117 unique bookmarks.
🚀 Sending 22 batches of 100 bookmarks to gemini-2.5-pro concurrently...
  Categorizing bookmarks... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
✅ Reorganized completely! Final count: 2117 bookmarks
╭──────────────────────────────── 🎉 Done! ──────────────────────────────────╮
│ Bookmarks organized successfully!                                          │
│                                                                            │
│ 📥 Input:  bookmarks/bookmarks.html (5.6 MB, 2148 bookmarks)                    │
│ 📤 Output: bookmarks/bookmarks_organized.html (198.3 KB, 2117 bookmarks)        │
│                                                                            │
│ Import the output file into your browser to use the organized bookmarks.   │
╰────────────────────────────────────────────────────────────────────────────╯
```

## Categories

Bookmarks are organized into these strict categories:

| Category | Examples |
|----------|----------|
| **Development** | GitHub, Stack Overflow, API docs |
| **Design** | Figma, Dribbble, UI kits |
| **Social Media** | Twitter, LinkedIn, Reddit |
| **News & Media** | CNN, TechCrunch, The Verge |
| **Entertainment** | YouTube, Spotify, Steam |
| **Education & Learning** | Coursera, MDN, tutorials |
| **Shopping & Finance** | Amazon, banking, crypto |
| **Productivity & Tools** | Notion, Trello, Gmail |
| **Reference & Research** | Wikipedia, papers, docs |
| **Personal** | Personal blogs, portfolios |
| **Other** | Everything else |

## Project Structure

```
bookmarkme/
├── bookmarks/                 # ← Drop your bookmarks.html here
│   └── .gitkeep
├── src/bookmarkme/
│   ├── __init__.py       # Package metadata
│   ├── cli.py            # Typer CLI entry point
│   ├── organizer.py      # Gemini API integration & batching
│   └── parser.py         # HTML parsing, dedup & generation
├── .env.example          # API key template
├── .gitignore
├── pyproject.toml        # Project config & dependencies
└── README.md
```

## Tech Stack

- **[uv](https://docs.astral.sh/uv/)** — Package management
- **[Typer](https://typer.tiangolo.com/)** — CLI framework
- **[Rich](https://rich.readthedocs.io/)** — Terminal UI & progress bars
- **[Google GenAI](https://ai.google.dev/)** — Gemini API client
- **[Pydantic](https://docs.pydantic.dev/)** — Structured output schemas
- **[Ruff](https://docs.astral.sh/ruff/)** — Linting & formatting

## License

MIT
