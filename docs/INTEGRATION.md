# External Tools Integration Guide

Connect Metabase, Grafana, DreamFactory, or any REST client to your Reddit scraper data.

---

## Quick Start

```powershell
# Install dependencies
uv sync

# Start the API server
uv run python main.py --api
```

The API will be available at `http://localhost:8000`

---

## Python Embedding

Use the package API when another Python project needs to run scrapes directly instead of shelling out to `main.py`:

```python
from reddit_universal_scraper import RedditScraper

scraper = RedditScraper(data_dir="data")
result = scraper.scrape("delhi", mode="full", limit=100)

print(result.posts_count)
print(result.output_paths.posts)
```

Common CLI-equivalent calls:

```python
scraper.scrape("delhi", mode="history", limit=500)
scraper.scrape("spez", is_user=True, mode="full", limit=50)
scraper.scrape("delhi", mode="full", limit=200, download_media=False)
scraper.scrape("delhi", mode="full", limit=200, scrape_comments=False)

for result in scraper.monitor("delhi", interval_seconds=300, max_iterations=1):
    print(result.posts_count)
```

The monitor iterator also accepts a `stop_event` for long-running embedded workers.

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /posts` | List posts with filters (q, subreddit, author, min_score) |
| `GET /posts/{id}` | Get single post |
| `GET /comments` | List comments with filters |
| `GET /subreddits` | List all scraped subreddits |
| `GET /subreddits/{name}/stats` | Get subreddit statistics |
| `GET /jobs` | View job history |
| `GET /jobs/stats` | Job statistics |
| `GET /query?sql=...` | Raw SQL SELECT queries |
| `GET /docs` | Interactive API documentation |

---

## Metabase Setup

1. Start API: `uv run python main.py --api`
2. In Metabase, add a new "HTTP" question
3. Use `http://localhost:8000/posts?limit=1000` 
4. Or use `/query?sql=SELECT * FROM posts` for custom queries

---

## Grafana Setup

1. Install "JSON API" or "Infinity" datasource plugin
2. Add datasource with URL: `http://localhost:8000`
3. Use `/grafana/query` for time-series data
4. Or use `/query?sql=...` for custom queries

Example Grafana query:
```sql
SELECT date(created_utc) as time, COUNT(*) as posts 
FROM posts 
GROUP BY date(created_utc)
```

---

## DreamFactory / REST Clients

The API includes full CORS support. Connect any tool that speaks REST:

```bash
# Get posts
curl http://localhost:8000/posts?subreddit=python&limit=10

# Custom SQL query
curl "http://localhost:8000/query?sql=SELECT title, score FROM posts ORDER BY score DESC LIMIT 5"
```

---

## Docker Compose (All-in-One)

```yaml
services:
  scraper-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    command: ["--api"]

  metabase:
    image: metabase/metabase
    ports:
      - "3000:3000"
```
