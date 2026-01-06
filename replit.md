# Lingualeo Bot

## Overview

A Telegram bot and CLI toolkit for learning English vocabulary using the Lingualeo language learning platform. The project provides multiple interfaces for interacting with Lingualeo's API: a Telegram bot for mobile training sessions, command-line tools for bulk word management, vocabulary export, and local spaced-repetition training.

Key capabilities:
- Telegram bot for vocabulary training with English-Russian word exercises
- Bulk word import from CSV files to Lingualeo
- Vocabulary export/parsing from Lingualeo to local CSV
- Local trainer with spaced repetition algorithm
- Cookie-based authentication with Lingualeo API

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Project Structure
The project lives in the `Lingualeo Bot/` directory with this organization:

```
Lingualeo Bot/
├── api_client.py          # Core API client for Lingualeo
├── config.py              # Configuration, cookies, API URLs
├── launcher.py            # Main menu launcher
├── utils.py               # Dependency management
├── lingualeo_pyth/        # Telegram bot
│   ├── tg_bot.py          # Main bot logic
│   └── keys.py            # Bot token
├── lingua_leo_RU_EN/      # Parser and trainer
│   ├── lingualeo_ultimate_parser.py
│   └── trainer.py
├── bulk add/              # Bulk word import
│   └── bot.py
└── User_Cookies/          # Per-user cookie storage
```

### Core Components

**API Client (`api_client.py`)**
- Centralized HTTP client for all Lingualeo API interactions
- Supports both sync (requests) and async (httpx) operations
- Handles authentication via cookies
- Key methods: `add_words_bulk`, `export_all_words`, `process_training_answer_batch`, `get_training_words`

**Configuration (`config.py`)**
- API endpoint URLs
- Default HTTP headers
- Cookie file paths (global and per-user)
- Payload templates for API requests

**Telegram Bot (`lingualeo_pyth/tg_bot.py`)**
- Built with aiogram 3.x
- FSM (Finite State Machine) for conversation flow
- Training session management with word-by-word exercises
- Results submission to Lingualeo server

**Authentication Pattern**
- Cookie-based auth extracted from browser sessions
- Cookies stored in text files (`cookies_current.txt` for global, `User_Cookies/<user_id>_cookies.txt` for per-user)
- Bot token stored in `keys.py` or environment variable `TELEGRAM_BOT_TOKEN`

### Data Flow

1. **Training Flow**: Bot fetches words → presents to user → collects answers → submits results to API
2. **Export Flow**: API client fetches all words → saves to `vocabulary.csv`
3. **Import Flow**: Read CSV → batch API calls to add words

### Key Design Decisions

**Centralized API Client**
- Problem: Multiple scripts needed API access
- Solution: Single `LingualeoAPIClient` class used everywhere
- Benefit: Consistent headers, cookie management, error handling

**Cookie-based Authentication**
- Problem: Lingualeo uses session cookies, no simple API keys
- Solution: Users extract cookies from browser DevTools
- Trade-off: Requires manual cookie refresh when expired

**Fix for Training Results**
- Problem: API expected specific data types (string keys, int values)
- Solution: `fix_process_training_answer_batch` function normalizes data before submission

## External Dependencies

### Python Packages (requirements.txt)
- `aiogram>=3.0.0` - Telegram bot framework
- `httpx>=0.24.0` - Async HTTP client
- `requests>=2.31.0` - Sync HTTP client
- `pandas>=2.0.0` - Data manipulation for CSV
- `aiofiles>=23.0.0` - Async file operations
- `selenium>=4.15.0` - Browser automation (for some utilities)
- `webdriver-manager>=4.0.0` - Chrome driver management

### External Services

**Lingualeo API**
- Base URL: `https://api.lingualeo.com`
- Endpoints: `/SetWords`, `/ProcessTraining`, `/GetLearningMain`
- Auth: Cookie header with `remember` JWT token and `userid`

**Telegram Bot API**
- Bot token required in `keys.py` or `TELEGRAM_BOT_TOKEN` env var
- Create via @BotFather

### File Storage
- Cookies: Plain text files in project root and `User_Cookies/`
- Vocabulary: CSV files (`vocabulary.csv`, `vocabulary_{user_id}.csv`)
- Training results: JSON files (`training_results_{user_id}.json`, `ruseng_results_{user_id}.json`)

## Training Types

### ENG-RUS Training (`/rep_engrus`)
- Shows English word, user selects Russian translation
- **Syncs with Lingualeo server**: Results are sent to API with status codes (1=correct, 2=error)
- Server manages spaced repetition intervals

### RUS-ENG Training (`/rep_ruseng`)
- Shows Russian word, user selects English translation
- **PURELY LOCAL**: Results are NOT sent to Lingualeo server (API doesn't support this training type)
- Spaced repetition managed locally in `vocabulary_{user_id}.csv`
- Intervals stored in local CSV file

## Crash Recovery (RUS-ENG)

The RUS-ENG training includes crash recovery to prevent data loss:

1. **Auto-save**: After each answer, results are saved to `ruseng_results_{user_id}.json`
2. **Session recovery**: On training start, loads saved results and resumes from first unanswered word
3. **Stale callback protection**: Old inline buttons from previous sessions are safely ignored
4. **Safe cleanup**: Cache only deleted after successful vocabulary CSV update

Key implementation files:
- `save_ruseng_results()` / `load_ruseng_results()` - Cache management
- `send_next_ruseng_word()` - Skips already-answered words
- `handle_training_answer()` - Early duplicate detection using callback_word_id

## Vocabulary Management Commands

### `/dictionary` Command
- Displays user's vocabulary with pagination (10 words per page)
- Navigation buttons for browsing (◀️ Назад / ▶️ Далее)
- Sorting options:
  - 🔤 А-Я: Alphabetical by English word
  - 📅 Дата: By next repetition date
  - 🔴 Готовы: Only words due for review
- Status indicators: 🔴 (due), 🟢 (not due), ⚪ (unknown)

### `/wordstatus <word>` Command
- Searches for word in both English and Russian columns
- Displays word statistics:
  - Translation
  - Number of repetitions
  - Current interval (hours)
  - Ease factor
  - Next review date with status
- Shows up to 5 matching words for partial matches

## Recent Changes

**2026-01-06**
- Added PostgreSQL database support for data persistence across redeployments
- Created new `db.py` module with async database functions (asyncpg)
- Dual storage mode: PostgreSQL in production (when DATABASE_URL set), CSV files in development
- Migrated commands to database: /update_vocab, /rep_ruseng, /dictionary, /wordstatus
- Fixed deployment type to VM (required for Telegram bots, not Autoscale)
- Database schema: user_vocabulary (user_id + english unique key), user_cookies, training_results
- Updated API client to store/load cookies from database (multi-user support)

**2026-01-05**
- Added `/dictionary` command with pagination and sorting
- Added `/wordstatus` command for individual word lookup
- Changed RUS-ENG word selection to random sampling (was sequential)
- Updated `/start` menu with categorized command list
- Fixed keyboard construction to avoid empty rows (Telegram BadRequest)