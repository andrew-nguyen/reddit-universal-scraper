# Extract Scraper Library API Implementation Plan

date: 2026-05-21 16:56 America/Los_Angeles
git_commit: 453009a2550377bf3e6b5d1a56694e32f3ce7140
branch: main
repository: reddit-universal-scraper
topic: extract-scraper-library-api
tags: [python, packaging, scraper, api, refactor]
status: implemented

## Overview

Extract the scraping behavior behind the documented CLI examples into an importable Python package that another project can install and call directly:

```python
from reddit_universal_scraper import RedditScraper

scraper = RedditScraper(data_dir="data")

scraper.scrape("delhi", mode="full", limit=100)
scraper.scrape("delhi", mode="history", limit=500)
scraper.monitor("delhi", interval_seconds=300)
scraper.scrape("spez", is_user=True, mode="full", limit=50)
scraper.scrape("delhi", mode="full", limit=200, download_media=False)
scraper.scrape("delhi", mode="full", limit=200, scrape_comments=False)
```

The current CLI should keep working:

```bash
python main.py delhi --mode full --limit 100
python main.py delhi --mode history --limit 500
python main.py delhi --mode monitor
python main.py spez --user --mode full --limit 50
python main.py delhi --no-media --limit 200
python main.py delhi --no-comments --limit 200
```

The implementation should preserve behavior first, then improve module boundaries. Do not change Reddit source URLs, output CSV schemas, media naming, plugin behavior, or job tracking semantics unless tests expose a bug that must be fixed to make extraction possible.

## Current State Analysis

- The package is not currently installable. `pyproject.toml` has project metadata but explicitly sets `[tool.uv] package = false` at `pyproject.toml:37`.
- The documented scrape commands in `README.md:64` through `README.md:79` all route through `main.py`.
- `main.py` mixes configuration, global HTTP/session state, file storage, extraction, media download, comment parsing, monitor mode, job tracking, plugin handling, and CLI argument parsing in one script.
- `main.py:20` through `main.py:34` define scraper configuration, `SEEN_URLS`, and a module-level `requests.Session`; these globals make the scraper hard to use safely as an imported API.
- `main.py:37` through `main.py:108` define the current data directory layout and CSV persistence:
  - `data/{r|u}_{target}/posts.csv`
  - `data/{r|u}_{target}/comments.csv`
  - `data/{r|u}_{target}/media/images`
  - `data/{r|u}_{target}/media/videos`
- `main.py:394` through `main.py:600` implement full/history scraping, including mirror retry, pagination, media download, comment scraping, plugin processing, dry-run behavior, CSV writes, and job history updates.
- `main.py:604` through `main.py:652` implement one monitor check using Reddit RSS, with fallback to a history-only JSON scrape when RSS is blocked.
- `main.py:654` through `main.py:879` define the entire CLI. The scrape-relevant mapping is:
  - CLI args at `main.py:694` through `main.py:700`.
  - monitor loop every 300 seconds at `main.py:860` through `main.py:867`.
  - history mode forcing no media and no comments at `main.py:868` through `main.py:871`.
  - full mode with `--no-media` and `--no-comments` overrides at `main.py:872` through `main.py:876`.
- `scraper/async_scraper.py` is an existing importable package entry, but it is separate from `main.py` and duplicates parsing/media/path logic. Its primary API is `scrape_async` at `scraper/async_scraper.py:292` and `run_async_scraper` at `scraper/async_scraper.py:467`.
- `scraper/async_scraper.py:216` through `scraper/async_scraper.py:289` duplicate the media URL and post extraction logic from `main.py`.
- `scheduler/cron.py` imports from `main` in two places (`scheduler/cron.py:86` and `scheduler/cron.py:188`), so a clean extraction should update scheduler imports to the new package rather than preserving script imports internally.
- `export/database.py` already has job-history helpers (`start_job_record`, `complete_job_record`) and batch SQLite save helpers. Current scrape flow only uses job tracking, not database batch post/comment persistence.
- There is no existing test suite. The only automated verification script is `scripts/verify-uv-migration.sh`, which checks dependency sync and smoke imports but not scraper behavior.

## Desired End State

- The repository contains an installable import package named `reddit_universal_scraper`.
- Another project can install the repository and import:
  - `RedditScraper`
  - `ScrapeOptions`
  - `ScrapeResult`
  - `ScrapeMode`
  - pure helper functions only where intentionally public
- The public Python API exposes the same behavior as the scrape CLI:
  - full scrape: posts, media, comments
  - history scrape: posts only
  - monitor mode: one-shot check and controlled recurring loop
  - subreddit vs user targets
  - skip media and skip comments controls
- The CLI remains backward compatible and delegates scrape work to the new library instead of owning scraper logic.
- Scheduler code delegates to the new library instead of importing from `main`.
- Existing CSV output layout stays compatible.
- API results are useful to callers, not only printed:
  - counts for posts/comments/images/videos
  - duration in seconds
  - output directory paths
  - job id when job tracking is enabled
  - scraped post/comment records for the current run unless explicitly disabled
  - warnings/errors captured as structured fields where practical
- Scraper state is instance-scoped. No public API should depend on module-level `SEEN_URLS` or a shared global session.
- Network and filesystem behavior is dependency-injectable enough for tests to avoid real Reddit calls.

## What We're NOT Doing

- Not switching to Reddit's authenticated API or requiring API keys.
- Not changing the mirror list, Reddit URL shapes, pagination policy, media limits, or CSV columns as part of the extraction.
- Not rewriting the REST API in `api/server.py`; that API reads stored data and is separate from the requested scrape API.
- Not redesigning the dashboard, analytics, search, cloud export, or plugin system.
- Not making the async scraper the primary public API in the first pass.
- Not adding a database-first storage backend unless a later task explicitly asks for it.
- Not guaranteeing stable behavior for all undocumented `main.py` imports beyond compatibility wrappers for the scrape functions.

## Design Options

### Option A: Thin Wrapper Around `main.py`

Expose a small module that imports `main.run_full_history` and `main.run_monitor`.

Trade-offs:
- Lowest implementation effort.
- Leaves global `SEEN_URLS`, global `SESSION`, print-heavy behavior, and filesystem assumptions intact.
- Does not create a clean API for another project.
- Hard to test without real network and filesystem side effects.

### Option B: Extract a Sync Package and Keep CLI as a Wrapper

Move sync scrape behavior into `reddit_universal_scraper`, add typed options/results, inject filesystem/session dependencies, and make `main.py` delegate to the package.

Trade-offs:
- Best match for the requested CLI-equivalent Python API.
- Preserves behavior while creating a usable library boundary.
- Requires focused tests and careful compatibility wrappers.
- Leaves the existing async scraper mostly intact except for shared pure helpers.

### Option C: Async-First Redesign

Promote `scraper/async_scraper.py` into the public API and refactor CLI to call it.

Trade-offs:
- Potentially faster and more modern.
- Larger behavior change because current CLI uses the sync implementation for the requested commands.
- Existing async implementation does not yet support dry-run, plugins, job tracking, or monitor RSS parity.
- Higher regression risk for a library extraction task.

## Preferred Approach

Use Option B.

Create a real package named `reddit_universal_scraper`, extract the sync CLI behavior into instance-scoped services, and keep `main.py` as a CLI compatibility layer. Consolidate duplicated pure parsing helpers with the async scraper only after the sync API is covered by tests.

Assumptions:
- Import name should be `reddit_universal_scraper`, matching the project name in Python identifier form.
- The public API should be synchronous first because the examples being replicated are synchronous CLI commands.
- Monitor API should include both a one-shot check and a recurring loop with stop controls; a library should not force callers into an uninterruptible infinite loop.
- Existing print output may remain for CLI compatibility, but the library should support a quiet/default logger path so callers can consume structured results.

## Proposed Public API Contract

Add the following public API in `reddit_universal_scraper/__init__.py`:

```python
from reddit_universal_scraper import RedditScraper, ScrapeMode, ScrapeOptions

scraper = RedditScraper(data_dir="data")

result = scraper.scrape(
    target="delhi",
    mode=ScrapeMode.FULL,
    limit=100,
    is_user=False,
)

history = scraper.scrape("delhi", mode="history", limit=500)

for result in scraper.monitor("delhi", interval_seconds=300):
    handle(result)
```

Minimum method surface:

- `RedditScraper.scrape(target, mode="full", limit=100, is_user=False, download_media=None, scrape_comments=None, dry_run=False, use_plugins=False, collect_records=True) -> ScrapeResult`
- `RedditScraper.scrape_full(target, limit=100, is_user=False, **overrides) -> ScrapeResult`
- `RedditScraper.scrape_history(target, limit=500, is_user=False) -> ScrapeResult`
- `RedditScraper.check_monitor_once(target, is_user=False) -> ScrapeResult`
- `RedditScraper.monitor(target, is_user=False, interval_seconds=300, max_iterations=None, stop_event=None) -> Iterator[ScrapeResult]`

Mode resolution rules:

- `mode="history"` always means `download_media=False` and `scrape_comments=False`.
- `mode="full"` defaults to `download_media=True` and `scrape_comments=True`.
- Explicit `download_media=False` mirrors `--no-media`.
- Explicit `scrape_comments=False` mirrors `--no-comments`.
- `mode="monitor"` is exposed through `check_monitor_once` and `monitor`; `scrape(..., mode="monitor")` may delegate to one monitor check, but the CLI should keep the recurring 300-second loop.

## Implementation Approach

Use test-backed extraction. Start by pinning behavior with focused tests around pure helpers and CLI option mapping, then move logic into package modules in small steps. Preserve old `main.py` scrape function names as thin compatibility wrappers until all internal callers have moved.

Recommended package layout:

```text
reddit_universal_scraper/
  __init__.py
  models.py
  settings.py
  client.py
  extractors.py
  storage.py
  media.py
  comments.py
  service.py
  monitor.py
  job_tracking.py
```

Recommended tests:

```text
tests/
  test_extractors.py
  test_storage.py
  test_scraper_service.py
  test_monitor.py
  test_cli_mapping.py
  test_package_import.py
```

## Phase 1: Add Test Harness and Lock Current Behavior

### Files

- `pyproject.toml`
- `tests/test_extractors.py`
- `tests/test_storage.py`
- `tests/test_cli_mapping.py`
- `tests/conftest.py` if shared fakes are needed
- `main.py` only if required to make CLI parsing testable through `main(argv=None)` or `build_parser()`

### Required Changes

- Add `pytest` as a dev dependency, preferably through a `dev` dependency group.
- Add tests for current pure behavior before moving code:
  - `extract_post_data` detects text, image, gallery, video, and link posts.
  - `get_media_urls` extracts direct images, `i.redd.it`, preview images, gallery images, Reddit video fallback URLs, and YouTube URLs.
  - `parse_comments` preserves recursive depth and fields.
  - storage path behavior matches `data/{prefix}_{target}` and current CSV filenames.
- Add a focused CLI mapping test that proves:
  - `mode=history` maps to media off and comments off.
  - `mode=full` maps to media/comments on by default.
  - `--no-media` and `--no-comments` override full mode independently.
  - `--user` maps to user target mode.
  - monitor CLI uses a 300-second interval.
- Avoid real network calls in tests by monkeypatching the scrape function called by CLI mapping.

### Automated Verification

- `uv sync --locked`
- `uv run pytest tests/test_extractors.py tests/test_storage.py tests/test_cli_mapping.py`
- `uv run python main.py --help`
- `uv run pytest tests/test_cli_mapping.py -k documented_examples`
  - This test should encode the README scrape examples and assert the same option mapping the CLI uses.
- `uv run pytest tests/test_cli_mapping.py -k help_flags`
  - This test should parse `main.py --help` output in a subprocess and assert existing scrape flags still appear: `--mode`, `--user`, `--limit`, `--no-media`, `--no-comments`.

### Manual Verification

- None required for this phase after the CLI mapping and help-output checks pass.

## Phase 2: Make the Project Installable and Add Public Models

### Files

- `pyproject.toml`
- `reddit_universal_scraper/__init__.py`
- `reddit_universal_scraper/models.py`
- `reddit_universal_scraper/settings.py`
- `tests/test_package_import.py`

### Required Changes

- Remove or replace `[tool.uv] package = false` so the project can be installed as a package.
- Add build metadata if needed:
  - `[build-system]`
  - Hatchling or another simple build backend
  - package include configuration for `reddit_universal_scraper`
- Add `ScrapeMode`, `ScrapeOptions`, `ScrapeResult`, and media count/path result models.
- Keep models simple:
  - dataclasses or typed dictionaries are enough.
  - Avoid requiring Pydantic unless there is a clear runtime need.
- Export the intended public names from `reddit_universal_scraper/__init__.py`.
- Add import smoke tests that work after `uv sync`.

### Automated Verification

- `uv lock`
- `uv sync --locked`
- `uv run python -c "from reddit_universal_scraper import ScrapeOptions, ScrapeResult, ScrapeMode; print(ScrapeMode.FULL.value)"`
- `uv run pytest tests/test_package_import.py`
- `uv build`
- `uv run pytest tests/test_package_import.py -k wheel_contents`
  - This test should inspect the built wheel with `zipfile` and assert it contains `reddit_universal_scraper/` modules and does not unexpectedly package `data/`, `thoughts/`, or runtime output directories.

### Manual Verification

- User input is only required if the public import name should change from the planned default `reddit_universal_scraper`.

## Phase 3: Extract Pure Parsing, Paths, and Storage

### Files

- `reddit_universal_scraper/extractors.py`
- `reddit_universal_scraper/storage.py`
- `reddit_universal_scraper/settings.py`
- `main.py`
- `scraper/async_scraper.py`
- `tests/test_extractors.py`
- `tests/test_storage.py`

### Required Changes

- Move `extract_post_data`, media URL extraction, and comment parsing into `reddit_universal_scraper/extractors.py`.
- Move directory and CSV persistence behavior into `reddit_universal_scraper/storage.py`.
- Replace `SEEN_URLS` global behavior with a per-storage or per-scraper instance set loaded from the target posts CSV.
- Preserve CSV columns and append behavior.
- Keep `main.py` compatibility functions (`extract_post_data`, `get_media_urls`, `parse_comments`, `setup_directories`, `save_posts_csv`, `save_comments_csv`) as thin wrappers or imports during migration if any internal code still imports them.
- Update `scraper/async_scraper.py` to import shared pure helpers for post/comment/media parsing where doing so does not change behavior.
- Do not change media limits or source labels unless tests explicitly document the current difference between sync and async source labels.

### Automated Verification

- `uv run pytest tests/test_extractors.py tests/test_storage.py`
- `uv run python -c "from reddit_universal_scraper.extractors import extract_post_data, extract_media_urls, parse_comments; print(extract_post_data({'id':'x'}).get('id'))"`
- `uv run python main.py --help`
- `uv run python -c "from scraper.async_scraper import run_async_scraper; print(run_async_scraper.__name__)"`
- `uv run pytest tests/test_storage.py -k csv_schema_compatibility`
  - This test should write mocked pre-refactor and post-refactor rows and compare the generated `posts.csv` and `comments.csv` column order.
- `uv run pytest tests/test_cli_mapping.py -k main_compatibility_wrappers`
  - This test should assert the legacy `main.py` scrape helper exports delegate to the new package functions instead of carrying duplicate scraper logic.

### Manual Verification

- None required for this phase after schema-compatibility and wrapper-delegation tests pass.

## Phase 4: Extract HTTP Client, Media Downloader, and Comment Fetching

### Files

- `reddit_universal_scraper/client.py`
- `reddit_universal_scraper/media.py`
- `reddit_universal_scraper/comments.py`
- `reddit_universal_scraper/settings.py`
- `main.py`
- `tests/test_scraper_service.py`
- `tests/test_monitor.py` if shared client fakes are useful

### Required Changes

- Add an instance-scoped HTTP client around `requests.Session` with:
  - user agent configuration
  - mirror list
  - timeout settings
  - `fetch_posts_page(target, after, is_user, batch_size)`
  - `fetch_comments(permalink)`
  - `fetch_monitor_rss(target, is_user)`
- Move media download behavior into `media.py`:
  - direct media download
  - Reddit video/audio temp-file download and ffmpeg merge fallback
  - image/video/gallery per-post download orchestration
- Move comment JSON fetching into `comments.py`, using the shared parser from `extractors.py`.
- Inject client/downloader/sleep/logger dependencies into later service code so unit tests can fake network, media download, and cooldowns.
- Preserve current fallback behavior when ffmpeg is unavailable.

### Automated Verification

- `uv run pytest tests/test_scraper_service.py tests/test_monitor.py`
- `uv run python -c "from reddit_universal_scraper.client import RedditClient; print(RedditClient.__name__)"`
- `uv run python -c "from reddit_universal_scraper.media import MediaDownloader; print(MediaDownloader.__name__)"`
- `uv run pytest tests/test_scraper_service.py -k dry_run_writes_no_media`
  - This test should use fake client/downloader objects and a temporary data directory to assert dry-run mode creates no media files.
- `uv run pytest tests/test_scraper_service.py -k reddit_video_audio_fallback`
  - This test should cover ffmpeg success, ffmpeg missing, and merge-failure fallback paths with faked downloads or local temp files, not real Reddit media.

### Manual Verification

- None required for this phase after dry-run media and video fallback tests pass.

## Phase 5: Extract the Sync Scrape Service and Public API

### Files

- `reddit_universal_scraper/service.py`
- `reddit_universal_scraper/job_tracking.py`
- `reddit_universal_scraper/__init__.py`
- `main.py`
- `tests/test_scraper_service.py`

### Required Changes

- Implement `RedditScraper` around the extracted client, storage, media, comments, and job tracking adapters.
- Move the core loop from `run_full_history` into `RedditScraper.scrape`.
- Preserve pagination behavior:
  - shuffle mirrors for each page
  - batch size is `min(100, limit - total_posts)`
  - stop when `after` is missing
  - wait 30 seconds when all sources fail
  - wait 3 seconds between successful pages in CLI-equivalent runs
- Preserve dry-run behavior:
  - no CSV writes
  - no media download
  - comments may still be counted if enabled, matching current behavior
- Preserve plugin behavior:
  - run plugins after collection when `use_plugins=True`
  - capture plugin exceptions as warnings without failing the scrape unless current behavior changes are explicitly approved
- Preserve job tracking:
  - use `export.database.start_job_record` and `complete_job_record` behind an adapter
  - continue gracefully when job tracking is unavailable
- Return a structured `ScrapeResult` with counts, duration, output paths, optional records, job id, warnings, and errors.
- Keep `main.run_full_history` as a wrapper around `RedditScraper().scrape(...)` so any external script imports do not break immediately.

### Automated Verification

- `uv run pytest tests/test_scraper_service.py`
- `uv run python -c "from reddit_universal_scraper import RedditScraper; print(RedditScraper().scrape_history.__name__)"`
- `uv run python main.py --help`
- `uv run python main.py --list-plugins`
- `uv run python -c "from main import run_full_history; print(run_full_history.__name__)"`
- `uv run pytest tests/test_scraper_service.py -k cli_api_history_equivalence`
  - This test should run the CLI delegation path and the Python API path against the same fake Reddit page data in separate temporary data directories, then compare output directory structure and CSV columns.
- `RUN_NETWORK=1 uv run pytest tests/test_network_smoke.py -k history_low_limit`
  - Optional, non-blocking integration check for maintainers who want a real Reddit/mirror smoke test.

### Manual Verification

- None required for this phase. Real Reddit/mirror checks should be opt-in automated integration tests.

## Phase 6: Extract Monitor API and Update Scheduler

### Files

- `reddit_universal_scraper/monitor.py`
- `reddit_universal_scraper/service.py`
- `main.py`
- `scheduler/cron.py`
- `tests/test_monitor.py`
- `tests/test_cli_mapping.py`

### Required Changes

- Implement `RedditScraper.check_monitor_once(target, is_user=False)` using the current RSS behavior.
- Implement `RedditScraper.monitor(...)` as a generator or iterator that:
  - calls one monitor check per iteration
  - sleeps `interval_seconds` between checks
  - supports `max_iterations` for tests and bounded callers
  - supports `stop_event` for integration callers
- Keep CLI monitor behavior equivalent:
  - `python main.py delhi --mode monitor` checks every 300 seconds until interrupted.
- Preserve current fallback when RSS returns non-200:
  - run a history-only scrape with limit 25.
- Update `scheduler/cron.py` to import and use `RedditScraper` instead of `from main import run_full_history`.
- Keep `main.run_monitor` as a compatibility wrapper around `RedditScraper().check_monitor_once(...)`.

### Automated Verification

- `uv run pytest tests/test_monitor.py tests/test_cli_mapping.py`
- `uv run python -c "from scheduler.cron import CronScheduler, run_scheduled; print(CronScheduler.__name__, run_scheduled.__name__)"`
- `uv run python -c "from main import run_monitor; print(run_monitor.__name__)"`
- `uv run pytest tests/test_monitor.py -k bounded_monitor`
  - This test should use `max_iterations=1`, a fake client, and monkeypatched sleep to verify one bounded monitor cycle without waiting five minutes.
- `uv run pytest tests/test_monitor.py -k cli_monitor_interrupt`
  - This test should verify the CLI monitor loop delegates correctly and exits cleanly when the injected monitor path raises `KeyboardInterrupt`.

### Manual Verification

- None required for this phase after bounded monitor and interrupt-path tests pass.

## Phase 7: Documentation and Compatibility Cleanup

### Files

- `README.md`
- `docs/INTEGRATION.md`
- `docs/BLOG.md` if it mentions embedding or scraper usage
- `scraper/__init__.py`
- `main.py`
- `pyproject.toml`
- `scripts/verify-uv-migration.sh`
- Optional: `docs/PYTHON_API.md`

### Required Changes

- Add a Python API usage section showing the six requested CLI-equivalent workflows.
- Document install/import usage from another project.
- Document return values and output paths.
- Document monitor stop controls for embedded use.
- Decide whether `scraper/__init__.py` should remain as a legacy async import package or re-export from `reddit_universal_scraper`.
- Remove duplicated scrape logic from `main.py` after wrappers are confirmed.
- Update `scripts/verify-uv-migration.sh` or add a new script to include package import and unit tests.

### Automated Verification

- `uv run pytest`
- `uv run python main.py --help`
- `uv run python main.py --list-plugins`
- `uv run python -c "from reddit_universal_scraper import RedditScraper, ScrapeOptions, ScrapeResult; print(RedditScraper.__name__)"`
- `uv build`
- `./scripts/verify-uv-migration.sh` after updating it, if the script remains the main smoke check
- `rg "from main import run_full_history|from main import run_monitor" .`
  - Expected: no internal runtime imports from `main`; compatibility imports in docs/tests only if intentional.
- `uv run pytest tests/test_docs_examples.py`
  - This test should execute or parse the documented Python API examples and assert the README CLI examples still map to supported CLI arguments.

### Manual Verification

- None required for this phase after docs-example tests and CLI argument checks pass.

## Testing Strategy

- Use unit tests for pure extraction functions, path/storage behavior, and option resolution.
- Use fake HTTP/client/downloader objects for service tests. Do not require real Reddit or mirror network access in CI.
- Use temporary directories for CSV/media tests.
- Use monkeypatched sleep functions for cooldown and monitor loop tests.
- Keep real scrape verification as opt-in automated integration coverage because Reddit/mirror availability is outside the repo's control.
- Add package import and build checks because the core deliverable is an importable library.

Recommended full automated verification after implementation:

```bash
uv lock --locked
uv sync --locked
uv run pytest
uv run python main.py --help
uv run python main.py --list-plugins
uv run python -c "from reddit_universal_scraper import RedditScraper; print(RedditScraper.__name__)"
uv build
```

Recommended opt-in real-runtime checks:

```bash
RUN_NETWORK=1 uv run pytest tests/test_network_smoke.py
```

These checks should use temporary data directories and should be skipped by default because Reddit and mirror availability are outside the repository's control.

## Scope Boundaries and Risks

- Packaging risk: converting from `[tool.uv] package = false` to an installable package can affect `uv sync` behavior. Keep CLI smoke checks in every phase.
- Import risk: existing modules sometimes assume repo-root imports and mutate `sys.path`; package imports should not copy that pattern.
- Behavior risk: `main.py` and `scraper/async_scraper.py` duplicate logic with small differences, so tests should define which behavior is canonical before consolidation.
- Runtime risk: Reddit and mirror availability are unstable. Automated tests must not depend on external network.
- Monitor risk: the existing CLI loop is infinite. The library API must add bounded and stoppable controls while preserving CLI behavior.
- State risk: module-level `SEEN_URLS` currently deduplicates across one process. The extracted API should make this instance-scoped and loaded from the selected storage path.

## Decisions

- Public import name defaults to `reddit_universal_scraper`, matching the normalized project name. Change it only if the user explicitly requests a different public import name before Phase 2.
- `ScrapeResult` should include post/comment records by default for API usefulness, with `collect_records=False` available for large scrapes.
- The legacy `scraper` package remains available for the existing async entrypoint during this extraction and should be documented as legacy/compatibility until async support is formalized under `reddit_universal_scraper`.

## Implementation Progress

- [x] Phase 1 automated verification
  - [x] `uv lock`
  - [x] `uv sync --locked`
  - [x] `uv run pytest tests/test_extractors.py tests/test_storage.py tests/test_cli_mapping.py`
  - [x] `uv run python main.py --help`
  - [x] `uv run pytest tests/test_cli_mapping.py -k documented_examples`
  - [x] `uv run pytest tests/test_cli_mapping.py -k help_flags`
- [x] Phase 2 automated verification
  - [x] `uv lock`
  - [x] `uv sync --locked`
  - [x] `uv run python -c "from reddit_universal_scraper import ScrapeOptions, ScrapeResult, ScrapeMode; print(ScrapeMode.FULL.value)"`
  - [x] `uv run pytest tests/test_package_import.py`
  - [x] `uv build`
  - [x] `uv run pytest tests/test_package_import.py -k wheel_contents`
- [x] Phase 3 automated verification
  - [x] `uv run pytest tests/test_extractors.py tests/test_storage.py`
  - [x] `uv run python -c "from reddit_universal_scraper.extractors import extract_post_data, extract_media_urls, parse_comments; print(extract_post_data({'id':'x'}).get('id'))"`
  - [x] `uv run python main.py --help`
  - [x] `uv run python -c "from scraper.async_scraper import run_async_scraper; print(run_async_scraper.__name__)"`
  - [x] `uv run pytest tests/test_storage.py -k csv_schema_compatibility`
  - [x] `uv run pytest tests/test_cli_mapping.py -k main_compatibility_wrappers`
- [x] Phase 4 automated verification
  - [x] `uv run pytest tests/test_scraper_service.py tests/test_monitor.py`
  - [x] `uv run python -c "from reddit_universal_scraper.client import RedditClient; print(RedditClient.__name__)"`
  - [x] `uv run python -c "from reddit_universal_scraper.media import MediaDownloader; print(MediaDownloader.__name__)"`
  - [x] `uv run pytest tests/test_scraper_service.py -k dry_run_writes_no_media`
  - [x] `uv run pytest tests/test_scraper_service.py -k reddit_video_audio_fallback`
- [x] Phase 5 automated verification
  - [x] `uv run pytest tests/test_scraper_service.py`
  - [x] `uv run python -c "from reddit_universal_scraper import RedditScraper; print(RedditScraper().scrape_history.__name__)"`
  - [x] `uv run python main.py --help`
  - [x] `uv run python main.py --list-plugins`
  - [x] `uv run python -c "from main import run_full_history; print(run_full_history.__name__)"`
  - [x] `uv run pytest tests/test_scraper_service.py -k cli_api_history_equivalence`
  - [ ] Optional: `RUN_NETWORK=1 uv run pytest tests/test_network_smoke.py -k history_low_limit`
- [x] Phase 6 automated verification
  - [x] `uv run pytest tests/test_monitor.py tests/test_cli_mapping.py`
  - [x] `uv run python -c "from scheduler.cron import CronScheduler, run_scheduled; print(CronScheduler.__name__, run_scheduled.__name__)"`
  - [x] `uv run python -c "from main import run_monitor; print(run_monitor.__name__)"`
  - [x] `uv run pytest tests/test_monitor.py -k bounded_monitor`
  - [x] `uv run pytest tests/test_monitor.py -k cli_monitor_interrupt`
- [x] Phase 7 automated verification
  - [x] `uv run pytest`
  - [x] `uv run python main.py --help`
  - [x] `uv run python main.py --list-plugins`
  - [x] `uv run python -c "from reddit_universal_scraper import RedditScraper, ScrapeOptions, ScrapeResult; print(RedditScraper.__name__)"`
  - [x] `uv build`
  - [x] `./scripts/verify-uv-migration.sh`
  - [x] `rg "from main import run_full_history|from main import run_monitor" . --glob '!thoughts/**'`
  - [x] `uv run pytest tests/test_docs_examples.py`
