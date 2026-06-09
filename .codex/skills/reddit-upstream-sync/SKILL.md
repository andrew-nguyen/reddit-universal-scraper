---
name: reddit-upstream-sync
description: Use when syncing this reddit-universal-scraper fork with upstream, resolving upstream merge conflicts, reviewing fork-vs-upstream divergence, or changing entrypoints, dependencies, README examples, config, dashboard, or scraper files affected by upstream.
---

# Reddit Upstream Sync

## Core Rule

Treat this repo as a productized fork, not a mirror. Keep upstream-owned files easy to accept from upstream, and keep fork-owned behavior in fork-owned files.

Root `main.py` is upstream-owned. Do not add fork behavior there. The fork CLI lives in:

- `uv_main.py`
- `reddit_universal_scraper/cli.py`
- `pyproject.toml` script: `reddit-universal-scraper = "reddit_universal_scraper.cli:main"`

If `main.py` diverges from `upstream/main`, future merges will reintroduce recurring conflicts.

## Before Syncing

1. Inspect actual repo state before giving advice:
   ```bash
   git status --short --branch
   git remote -v
   git branch -vv
   git fetch upstream
   git rev-list --left-right --count upstream/main...main
   ```

2. Do not sync with dirty work unless the user explicitly wants those changes included. Existing dirty files may be user work.

3. Ensure repeated conflict resolutions can be reused:
   ```bash
   git config rerere.enabled true
   ```

## Merge Process

Use an integration branch. Do not rebase shared `main`.

```bash
git fetch upstream
git switch main
git switch -c sync/upstream-$(date +%Y-%m-%d)
git merge upstream/main
```

Resolve by file ownership:

- `main.py`: upstream-owned. Take upstream if it conflicts.
  ```bash
  git restore --source=upstream/main --worktree main.py
  git add main.py
  ```
- `uv_main.py`, `reddit_universal_scraper/cli.py`, `pyproject.toml`: fork-owned. Preserve fork behavior.
- `requirements.txt`: keep fork compatibility note unless intentionally supporting upstream install flow. Add runtime deps to `pyproject.toml`.
- `.gitignore`: usually take the union.
- `scraper/async_scraper.py`: manually port upstream behavior while preserving package extractor delegation.
- `README.md`, `docs/*`, `dashboard/app.py`: review auto-merges; upstream marketing/proxy content may not belong unchanged.

After resolving:

```bash
.venv/bin/pytest -q
git diff --exit-code upstream/main -- main.py
```

If the test suite invokes `uv build` and sandboxed `uv` panics in macOS SystemConfiguration, rerun the same verification outside the sandbox with approval.

## Porting Upstream Features

Upstream often puts new behavior directly in `main.py`, `config.py`, `dashboard/app.py`, or `scraper/async_scraper.py`. Do not blindly keep those changes in `main.py`.

Port useful behavior into the fork architecture:

- Settings/env/proxy defaults: `reddit_universal_scraper/settings.py`
- HTTP/session/proxy behavior: `reddit_universal_scraper/client.py`
- Sync scrape orchestration: `reddit_universal_scraper/service.py`
- Fork CLI flags/help/docs: `reddit_universal_scraper/cli.py`, `uv_main.py`, README/docs
- Async scraper behavior: `scraper/async_scraper.py` or a package module if refactoring is in scope

Useful inspection commands:

```bash
git diff main...upstream/main -- main.py config.py scraper/async_scraper.py dashboard/app.py requirements.txt README.md
git merge-tree --write-tree --name-only HEAD upstream/main
```

For uncommitted work, create a temporary commit object for merge simulation rather than trusting `HEAD`:

```bash
tmp_index=$(mktemp /tmp/reddit-sync-index.XXXXXX)
GIT_INDEX_FILE="$tmp_index" git read-tree HEAD
git diff --binary | GIT_INDEX_FILE="$tmp_index" git apply --cached --binary
GIT_INDEX_FILE="$tmp_index" git add uv_main.py reddit_universal_scraper/cli.py tests/test_fork_entrypoints.py
tree=$(GIT_INDEX_FILE="$tmp_index" git write-tree)
commit=$(git commit-tree "$tree" -p HEAD -m 'temporary sync test')
git merge-tree --write-tree --name-only "$commit" upstream/main
rm -f "$tmp_index"
```

## Completion Checklist

- `main.py` matches `upstream/main`.
- User-facing fork commands use `uv run python uv_main.py` or the package console script, not `uv run python main.py`.
- Tests import `reddit_universal_scraper.cli` for fork CLI behavior, not root `main.py`.
- Wheel contents include `reddit_universal_scraper/cli.py` and entrypoint metadata.
- Remaining conflicts are understood and documented before merging back to `main`.
