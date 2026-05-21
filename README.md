# 🤖 Universal Reddit Scraper Suite

[![Docker Build & Publish](https://github.com/ksanjeev284/reddit-universal-scraper/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/ksanjeev284/reddit-universal-scraper/actions/workflows/docker-publish.yml)

A **full-featured** Reddit scraper with analytics dashboard, REST API, scheduled scraping, plugins, and more. **No API keys required!**

<img width="2558" height="1331" alt="image" src="https://github.com/user-attachments/assets/180b89ce-db02-4cd2-922d-aa3d1b8eeda7" />

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Full Scraping** | Posts, comments, images, videos, galleries |
| 📈 **Web Dashboard** | Beautiful Streamlit UI with 7 tabs |
| 🚀 **REST API** | Connect Metabase, Grafana, DuckDB |
| 🔌 **Plugin System** | Extensible post-processing (sentiment, dedupe, keywords) |
| 📋 **Job Tracking** | Full history with status, duration, errors |
| 🧪 **Dry Run Mode** | Test scrape rules without saving data |
| 📦 **Parquet Export** | Analytics-ready format for DuckDB/warehouses |
| 😀 **Sentiment Analysis** | Analyze post/comment sentiment |
| 📅 **Scheduled Scraping** | Cron-style job scheduling |
| 📧 **Notifications** | Discord & Telegram alerts |
| 🗄️ **SQLite Database** | Structured storage with auto-backup |

---

## 🚀 Quick Start

```bash
# Install dependencies
uv sync

# Scrape a subreddit
uv run python main.py python --mode full --limit 100

# Launch dashboard
uv run python main.py --dashboard
# Opens at http://localhost:8501
```

### 📋 Requirements

- **Python 3.10+**
- **uv**
- **ffmpeg** (optional, for video with audio)

```bash
# Windows (via chocolatey)
choco install ffmpeg

# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

---

## 📖 All Commands

### 🔄 Scraping

```bash
# Full scrape (posts + media + comments)
uv run python main.py delhi --mode full --limit 100

# Fast history-only (no media/comments)
uv run python main.py delhi --mode history --limit 500

# Live monitor (checks every 5 min)
uv run python main.py delhi --mode monitor

# Scrape a user's posts
uv run python main.py spez --user --mode full --limit 50

# Skip media or comments
uv run python main.py delhi --no-media --limit 200
uv run python main.py delhi --no-comments --limit 200
```

### 🧪 Dry Run Mode

Test scrape rules without saving any data:

```bash
uv run python main.py python --mode full --limit 50 --dry-run
```

Output:
```
🧪 DRY RUN MODE - No data will be saved
🧪 DRY RUN COMPLETE!
   📊 Would scrape: 100 posts
   💬 Would scrape: 245 comments
```

### 🔌 Plugins

Enable post-processing plugins:

```bash
# List available plugins
uv run python main.py --list-plugins

# Run with plugins enabled
uv run python main.py python --mode full --plugins
```

**Built-in Plugins:**
| Plugin | Description |
|--------|-------------|
| `sentiment_tagger` | Adds sentiment scores to posts |
| `deduplicator` | Removes duplicate posts |
| `keyword_extractor` | Extracts top keywords |

Create custom plugins in `plugins/` folder.

### 📊 Dashboard

```bash
uv run python main.py --dashboard
# Opens at http://localhost:8501
```

**Dashboard Tabs:**
- 📊 Overview - Stats & charts
- 📈 Analytics - Sentiment & keywords
- 🔍 Search - Query scraped data
- 💬 Comments - Comment analysis
- ⚙️ Scraper - Start new scrapes
- 📋 Job History - View all jobs
- 🔌 Integrations - API, export, plugins

### 🚀 REST API

```bash
uv run python main.py --api
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

**Endpoints:**
| Endpoint | Description |
|----------|-------------|
| `GET /posts` | List posts with filters |
| `GET /comments` | List comments |
| `GET /subreddits` | All scraped subreddits |
| `GET /jobs` | Job history |
| `GET /query?sql=...` | Raw SQL queries |
| `GET /grafana/query` | Grafana time-series |

### 📦 Export & Maintenance

```bash
# Export to Parquet (for DuckDB/warehouses)
uv run python main.py --export-parquet python

# View job history
uv run python main.py --job-history

# Backup database
uv run python main.py --backup

# Optimize database
uv run python main.py --vacuum
```

Optional cloud upload dependencies:

```bash
# S3 uploads
uv sync --extra s3

# Google Drive uploads
uv sync --extra gdrive

# Both S3 and Google Drive
uv sync --extra cloud
```

### 📅 Scheduled Scraping

```bash
# Scrape every 60 minutes
uv run python main.py --schedule delhi --every 60

# With options
uv run python main.py --schedule delhi --every 30 --mode full --limit 50
```

### 🔍 Search & Analytics

```bash
# Search scraped data
uv run python main.py --search "credit card" --min-score 100

# Run sentiment analysis
uv run python main.py --analyze delhi --sentiment

# Extract keywords
uv run python main.py --analyze delhi --keywords
```

---

## 🐳 Docker

### Quick Start

```bash
# Build
docker build -t reddit-scraper .

# Run scrape
docker run -v ./data:/app/data reddit-scraper python --limit 100

# Run with plugins
docker run -v ./data:/app/data reddit-scraper python --plugins
```

### Docker Compose (Full Stack)

```bash
# Start API + Dashboard
docker-compose up -d

# Access:
# Dashboard: http://localhost:8501
# API: http://localhost:8000/docs
```

### Deploy to AWS/VPS

```bash
# SSH into your server
ssh user@your-server-ip

# Clone repo
git clone https://github.com/ksanjeev284/reddit-universal-scraper.git
cd reddit-universal-scraper

# Start services
docker-compose up -d

# Open firewall ports
sudo ufw allow 8000
sudo ufw allow 8501
```

Access:
- `http://your-server-ip:8501` → Dashboard
- `http://your-server-ip:8000/docs` → API

---

## 🔗 External Integrations

### Metabase

1. Start API: `uv run python main.py --api`
2. Add HTTP datasource: `http://localhost:8000`
3. Query: `/posts?subreddit=python&limit=100`

### Grafana

1. Install "JSON API" or "Infinity" plugin
2. Add datasource: `http://localhost:8000`
3. Use `/grafana/query` for time-series

### DuckDB

```python
import duckdb

# Export to Parquet first
# uv run python main.py --export-parquet python

# Query directly
duckdb.query("SELECT * FROM 'data/parquet/*.parquet'").df()
```

---

## 📁 Project Structure

```
reddit-scraper/
├── main.py              # CLI entry point
├── config.py            # Settings
├── analytics/           # Sentiment & keywords
├── alerts/              # Discord/Telegram
├── api/                 # REST API server
├── dashboard/           # Streamlit UI
├── export/              # Database & exports
├── plugins/             # Post-processing plugins
├── scheduler/           # Cron scheduling
├── search/              # Search engine
└── data/
    ├── r_subreddit/     # Scraped data
    ├── backups/         # DB backups
    └── parquet/         # Parquet exports
```

---

## 📊 Data Output

### posts.csv
| Column | Description |
|--------|-------------|
| id | Reddit post ID |
| title | Post title |
| author | Username |
| score | Net upvotes |
| num_comments | Comment count |
| post_type | text/image/video/gallery |
| selftext | Post body |
| sentiment_score | -1.0 to 1.0 (with plugins) |

### comments.csv
| Column | Description |
|--------|-------------|
| comment_id | Comment ID |
| post_permalink | Parent post |
| author | Username |
| body | Comment text |
| score | Upvotes |

---

## ⚙️ Environment Variables

```bash
# Notifications
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="987654321"
```

---

## 📜 License

MIT License - Feel free to use, modify, and distribute.

## 🤝 Contributing

Pull requests welcome! For major changes, please open an issue first.
