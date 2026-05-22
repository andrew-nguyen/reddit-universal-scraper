#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-reddit-scraper-uv}"
API_CONTAINER_NAME="${API_CONTAINER_NAME:-reddit-scraper-api-test}"
API_PORT="${API_PORT:-18000}"

log() {
  printf '[verify] %s\n' "$1"
}

cleanup_api_container() {
  if docker ps -a --format '{{.Names}}' | grep -qx "$API_CONTAINER_NAME"; then
    docker stop "$API_CONTAINER_NAME" >/dev/null
  fi
}

log "checking uv lockfile"
uv lock --locked

log "syncing uv environment"
uv sync --locked

log "importing default dependencies"
uv run python -c "import pandas, requests, aiohttp, aiofiles, streamlit, openpyxl, pyarrow, fastapi, uvicorn, psutil, duckdb"

log "importing scraper package"
uv run python -c "from reddit_universal_scraper import RedditScraper, ScrapeOptions, ScrapeResult; print(RedditScraper.__name__)"

log "running unit tests"
uv run pytest

log "checking CLI help"
uv run python main.py --help >/dev/null

log "checking plugin listing"
uv run python main.py --list-plugins >/dev/null

log "checking API app import"
uv run python -c "from api.server import app; print(app.title)"

log "checking parquet export import"
uv run python -c "from export.parquet import export_to_parquet; print(export_to_parquet.__name__)"

log "building package"
uv build

if [[ "${RUN_DOCKER:-0}" == "1" ]]; then
  log "building Docker image"
  docker build -t "$IMAGE_NAME" .

  log "checking Docker CLI help"
  docker run --rm "$IMAGE_NAME" --help >/dev/null

  log "checking Docker plugin listing"
  docker run --rm "$IMAGE_NAME" --list-plugins >/dev/null

  log "checking Docker API health"
  trap cleanup_api_container EXIT
  cleanup_api_container
  docker run --rm -d --name "$API_CONTAINER_NAME" -p "$API_PORT:8000" "$IMAGE_NAME" --api >/dev/null

  for _ in {1..30}; do
    if curl -fsS "http://localhost:${API_PORT}/health" >/dev/null; then
      cleanup_api_container
      trap - EXIT
      log "Docker API health passed"
      log "all checks passed"
      exit 0
    fi
    sleep 1
  done

  docker logs "$API_CONTAINER_NAME"
  cleanup_api_container
  trap - EXIT
  printf '[verify] Docker API health failed\n' >&2
  exit 1
fi

log "Docker checks skipped; set RUN_DOCKER=1 to enable them"
log "all checks passed"
