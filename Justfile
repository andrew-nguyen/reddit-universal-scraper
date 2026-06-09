set shell := ["bash", "-uc"]

default:
    @just --list

version:
    @awk -F'"' '/^version = / { print $2; exit }' pyproject.toml

lock:
    uv lock

test:
    uv run pytest

build: lock
    uv build --wheel --sdist

smoke: build
    @version="$(awk -F'"' '/^version = / { print $2; exit }' pyproject.toml)"; \
    uv run --isolated --no-project --with "dist/reddit_universal_scraper-${version}-py3-none-any.whl" python -c "from reddit_universal_scraper import RedditScraper; print(RedditScraper.__name__)"

_check-testpypi-token:
    @test -n "${UV_PUBLISH_TOKEN:-}" || (echo "Set UV_PUBLISH_TOKEN to a TestPyPI API token" >&2; exit 1)

_publish-testpypi:
    @version="$(awk -F'"' '/^version = / { print $2; exit }' pyproject.toml)"; \
    uv publish --index testpypi "dist/reddit_universal_scraper-${version}.tar.gz" "dist/reddit_universal_scraper-${version}-py3-none-any.whl"

publish-testpypi: _check-testpypi-token smoke _publish-testpypi

release-testpypi: _check-testpypi-token test smoke _publish-testpypi
