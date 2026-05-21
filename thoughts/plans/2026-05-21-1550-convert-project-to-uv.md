# Convert Project to uv Implementation Plan

date: 2026-05-21 15:50 America/Los_Angeles
git_commit: c416fef6aae0b4ed889edcf5ce77c6407a1662a4
branch: main
repository: reddit-universal-scraper
research: thoughts/research/2026-05-21-1547-convert-to-uv.md
topic: convert-project-to-uv
tags: [python, packaging, uv, docker]
status: complete

## Overview

Convert the repository from an unpinned `requirements.txt`/`pip` workflow to a `uv` project workflow with `pyproject.toml`, `uv.lock`, updated Docker installation, and documentation that uses `uv sync` and `uv run`.

The plan intentionally keeps the application architecture unchanged. The existing CLI remains `python main.py ...`, just run through `uv` for local development. Docker keeps the current command argument behavior so `docker run ... reddit-scraper python --limit 100` and Compose service commands continue to work from the user's perspective.

## Current State Analysis

- `requirements.txt` is the only dependency declaration and contains unpinned dependencies:
  - `pandas`
  - `requests`
  - `aiohttp`
  - `aiofiles`
  - `streamlit`
  - `openpyxl`
  - `pyarrow`
  - `fastapi`
  - `uvicorn`
  - `psutil`
  - `duckdb`
- There is no `pyproject.toml`, `uv.lock`, package metadata, console script, test config, or CI Python install step.
- `README.md`, `docs/BLOG.md`, and `docs/INTEGRATION.md` document `pip install ...` and direct `python main.py ...` usage.
- `Dockerfile` copies `requirements.txt` and runs `pip install --no-cache-dir -r requirements.txt`.
- `.github/workflows/docker-publish.yml` only builds/publishes Docker images, so Docker build verification is the main CI-relevant path.
- Python support is inconsistent:
  - `README.md` says Python 3.8+.
  - `docs/BLOG.md` says Python 3.10+.
  - `Dockerfile` uses Python 3.11.
- `export/cloud.py` contains optional cloud upload imports for `boto3`, `botocore`, `google-api-python-client`, and `google-auth-oauthlib`; these are not currently installed by `requirements.txt`.

## Desired End State

- `pyproject.toml` declares project metadata, supported Python version, runtime dependencies, and optional cloud dependencies.
- `uv.lock` is generated and committed for reproducible installs.
- Local install/run docs use:
  - `uv sync`
  - `uv run python main.py ...`
- Docker uses `uv sync --locked` and benefits from dependency-layer caching by copying `pyproject.toml` and `uv.lock` before the application source.
- Existing app behavior remains intact:
  - CLI entry remains `main.py`.
  - Dashboard launches through `main.py --dashboard`.
  - REST API launches through `main.py --api`.
  - Docker Compose commands continue to pass arguments to the same CLI.
- Verification is mostly automated with lock, sync, import, CLI, API, dashboard import, and Docker build checks.

## What We're NOT Doing

- Not refactoring the repository into a `src/` package layout.
- Not renaming modules or moving application files.
- Not replacing `argparse` with a new CLI framework.
- Not adding a console script such as `reddit-scraper` in this migration.
- Not changing scraper behavior, API behavior, dashboard UI, or database schema.
- Not adding a full test suite beyond focused smoke checks unless implementation discovers an existing test harness.
- Not installing optional cloud upload dependencies by default.

## Design Options

### Option A: Minimal uv Installer Wrapper

Keep `requirements.txt` and change Docker/local docs to use `uv pip install -r requirements.txt`.

Trade-offs:
- Lowest code churn.
- Does not create project metadata.
- Does not meaningfully improve reproducibility unless a generated requirements lock is also added.
- Leaves the repo halfway between old and new workflows.

### Option B: uv Project Mode, Script-Style App

Add `pyproject.toml` and `uv.lock`, keep runtime commands as `uv run python main.py ...`, and update Docker to `uv sync --locked`.

Trade-offs:
- Adds modern project metadata and lockfile without changing app structure.
- Keeps migration risk low because imports and entrypoints stay the same.
- Requires docs and Docker updates.
- Recommended for this repository.

### Option C: uv Project Mode plus Installable CLI

Do Option B and also add a console script such as `reddit-scraper = "main:main"`.

Trade-offs:
- More polished CLI after install.
- Slightly larger behavioral surface because package execution/import assumptions change.
- May require resolving top-level module/package naming conventions.
- Better as a follow-up after the uv migration is stable.

## Preferred Approach

Use Option B: uv project mode while keeping the existing script-style application.

Assumptions:
- Canonical Python support should be `>=3.10`, because docs already mention Python 3.10+ and current dependency versions are more likely to support 3.10+ cleanly than 3.8 in 2026.
- Docker should remain on Python 3.11 unless dependency resolution or runtime smoke checks indicate a reason to move.
- Optional S3 and Google Drive dependencies should be represented as extras, not installed by default.

## Phase 1: Add uv Project Metadata

### Files

- `pyproject.toml`
- `requirements.txt`

### Required Changes

- [x] Add `pyproject.toml` with project metadata:
   - `[project]`
   - `name = "reddit-universal-scraper"`
   - `version = "0.1.0"` unless another project version exists.
   - `description` matching the README summary.
   - `readme = "README.md"`
   - `requires-python = ">=3.10"`
   - `license` using the project license.
   - `dependencies` copied from current `requirements.txt`.
- [x] Add optional dependencies:
   - `[project.optional-dependencies]`
   - `s3 = ["boto3"]`
   - `gdrive = ["google-api-python-client", "google-auth-oauthlib"]`
   - `cloud = ["boto3", "google-api-python-client", "google-auth-oauthlib"]`
- [x] Do not add a `[project.scripts]` entry in this phase.
- [x] Decide whether to keep `requirements.txt`:
   - Preferred: keep it temporarily as a compatibility note with comments directing users to `pyproject.toml` and `uv sync`, or remove it only if every docs path is updated.
   - If kept, do not maintain two conflicting dependency sources. Either leave it as legacy compatibility generated from the project or clearly mark `pyproject.toml` as authoritative.

### Automated Verification

- [x] `uv lock`
- [x] `test -f pyproject.toml`
- [x] `test -f uv.lock`
- [x] `uv sync --locked`
- [x] `uv run python -c "import pandas, requests, aiohttp, aiofiles, streamlit, openpyxl, pyarrow, fastapi, uvicorn, psutil, duckdb"`
- [x] `uv run python main.py --help`
- [x] `uv run python main.py --list-plugins`

### Manual Verification

- [x] Review `pyproject.toml` metadata for acceptable project name, version, description, and Python support range.

## Phase 2: Update Runtime Hints and Optional Dependency Messages

### Files

- `main.py`
- `api/server.py`
- `dashboard/app.py`
- `export/cloud.py`
- `export/parquet.py`

### Required Changes

- [x] Update user-facing install hints from `pip install ...` to `uv add ...` or `uv sync`.
- [x] In `main.py`, update the REST API missing dependency message:
   - From `pip install fastapi uvicorn`
   - To a `uv`-appropriate message such as `Run uv sync` or `uv add fastapi uvicorn`.
- [x] In `export/cloud.py`, update optional dependency error messages:
   - S3: recommend `uv sync --extra s3` or `uv sync --extra cloud`.
   - Google Drive: recommend `uv sync --extra gdrive` or `uv sync --extra cloud`.
- [x] In `export/parquet.py`, update `pyarrow` missing dependency messages to recommend `uv sync`.
- [x] Keep runtime behavior unchanged.

### Automated Verification

- [x] `rg "pip install" main.py api dashboard export docs README.md`
- Expected result after this phase:
  - No `pip install` references in runtime code.
  - Any remaining docs references should be intentional legacy/migration notes only.
- [x] `uv run python main.py --help`
- [x] `uv run python main.py --list-plugins`
- [x] `uv run python -c "from api.server import app; print(app.title)"`
- [x] `uv run python -c "import dashboard.app"`
- [x] `uv run python -c "from export.parquet import export_to_parquet; print(export_to_parquet.__name__)"`
- [x] `uv run python -c "from export.cloud import S3Uploader, GDriveUploader; print(S3Uploader.__name__, GDriveUploader.__name__)"`

### Manual Verification

- [x] Confirm any remaining install guidance reads naturally for users unfamiliar with `uv`.

## Phase 3: Convert Docker to uv

### Files

- `Dockerfile`
- `.dockerignore` if needed
- `docker-compose.yml`

### Required Changes

- [x] Update Docker dependency installation to use `uv`.
- [x] Prefer the official uv image copy pattern or installer pattern:
   - Example shape:
     - `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/`
     - `ENV UV_COMPILE_BYTECODE=1`
     - `ENV UV_LINK_MODE=copy`
     - `ENV UV_NO_DEV=1`
- [x] Copy dependency metadata before source for Docker layer caching:
   - `COPY pyproject.toml uv.lock ./`
   - `RUN uv sync --locked --no-install-project`
   - Copy application source.
   - `RUN uv sync --locked --no-dev`
- [x] Preserve existing system packages:
   - `curl`
   - `ffmpeg`
- [x] Preserve exposed ports:
   - `8501`
   - `8000`
- [x] Preserve the current CLI-facing entry behavior:
   - Use the uv-managed environment when running `main.py`.
   - Example: `ENTRYPOINT ["uv", "run", "python", "main.py"]`
   - Validate Docker Compose `command: ["--api"]` and dashboard/scraper commands still append correctly.
- [x] Add `.dockerignore` if Docker build context currently sends avoidable local artifacts:
   - `.git`
   - `.venv`
   - `__pycache__/`
   - `.pytest_cache/`
   - `data/`
   - `thoughts/`

### Automated Verification

- [x] `docker build -t reddit-scraper-uv .`
- [x] `docker run --rm reddit-scraper-uv --help`
- [x] `docker run --rm reddit-scraper-uv --list-plugins`
- [x] API smoke:
  - Start container in detached mode:
    - `docker run --rm -d --name reddit-scraper-api-test -p 18000:8000 reddit-scraper-uv --api`
  - Poll health endpoint:
    - `curl -fsS http://localhost:18000/health`
  - Stop container:
    - `docker stop reddit-scraper-api-test`
- [x] Compose config validation:
  - `docker compose config`

### Manual Verification

- N/A: Docker was available locally, and automated Docker build/runtime smoke checks passed.

## Phase 4: Update Documentation

### Files

- `README.md`
- `docs/BLOG.md`
- `docs/INTEGRATION.md`
- `api/server.py`
- `dashboard/app.py`
- `docker-compose.yml`

### Required Changes

- [x] Replace install commands:
   - From `pip install -r requirements.txt`
   - To `uv sync`
- [x] Replace local run commands in user-facing docs:
   - From `python main.py ...`
   - To `uv run python main.py ...`
- [x] Keep Docker commands unchanged unless the image behavior changes.
- [x] Update requirements section:
   - Python 3.10+
   - uv
   - ffmpeg optional for video with audio
- [x] Update API integration quick start:
   - `uv sync`
   - `uv run python main.py --api`
- [x] Update dashboard comments:
   - `uv run streamlit run dashboard/app.py` where direct Streamlit invocation is documented.
- [x] Update optional cloud dependency instructions:
   - `uv sync --extra s3`
   - `uv sync --extra gdrive`
   - `uv sync --extra cloud`

### Automated Verification

- [x] `rg "pip install|python main\\.py|streamlit run|uvicorn api\\.server" README.md docs api dashboard docker-compose.yml`
- Expected result:
  - `pip install` should be absent unless in a legacy migration note.
  - `python main.py` should either be prefixed with `uv run` in local docs or remain only in Docker-internal examples where appropriate.
- [x] `uv run python main.py --help`

### Manual Verification

- [x] Read the Quick Start and Docker sections in `README.md` to confirm a new user can follow them without knowing the old `pip` workflow.

## Phase 5: Add Automated Smoke Verification Script

### Files

- `scripts/verify-uv-migration.sh`
- `.gitignore` if script outputs artifacts

### Required Changes

- [x] Add a shell script that runs local non-network app smoke checks after dependencies are installed:
   - `uv lock --locked`
   - `uv sync --locked`
   - import check for all default dependencies
   - `uv run python main.py --help`
   - `uv run python main.py --list-plugins`
   - `uv run python -c "from api.server import app; print(app.title)"`
   - `uv run python -c "from export.parquet import export_to_parquet; print(export_to_parquet.__name__)"`
- [x] Include optional Docker checks behind an environment flag so local verification can run without Docker:
   - `RUN_DOCKER=1 scripts/verify-uv-migration.sh`
- [x] Make the script fail fast:
   - `set -euo pipefail`
- [x] Keep the script POSIX-ish or explicitly use Bash with a shebang.

### Automated Verification

- [x] `chmod +x scripts/verify-uv-migration.sh`
- [x] `scripts/verify-uv-migration.sh`
- If Docker is available:
  - [x] `RUN_DOCKER=1 scripts/verify-uv-migration.sh`

### Manual Verification

- [x] Confirm the script output is readable enough for migration review/debugging.

## Phase 6: Final Consistency and Git Review

### Files

- All touched files.

### Required Changes

- [x] Review changed files for duplicate dependency declarations or stale commands.
- [x] Ensure `uv.lock` is present and unignored so the final commit can include it.
- [x] Ensure generated/local environment directories are not committed:
   - `.venv/`
   - `.pytest_cache/`
   - `__pycache__/`
- [x] Ensure `data/` remains ignored.

### Automated Verification

- [x] `git diff --check`
- [x] `git status --short`
- [x] `uv lock --locked`
- [x] `uv sync --locked`
- [x] `scripts/verify-uv-migration.sh`
- [x] `rg "pip install -r requirements\\.txt|pip install fastapi uvicorn|pip install pyarrow|pip install boto3|pip install google-api-python-client" .`
  - Matches were limited to historical references in `thoughts/`; the same check excluding `thoughts/**` found no stale user-facing docs or runtime messages.
- If Docker is available:
  - [x] `RUN_DOCKER=1 scripts/verify-uv-migration.sh`

### Manual Verification

- [x] Review final diff to confirm the migration did not alter scraper, dashboard, API, or persistence behavior.

## Testing Strategy

Automate the following as the primary confidence checks:

- Dependency resolution:
  - `uv lock`
  - `uv lock --locked`
- Environment reproducibility:
  - `uv sync --locked`
- Runtime dependency imports:
  - import every default dependency from `pyproject.toml`
- Application import checks:
  - API app import
  - dashboard module import
  - parquet export import
  - cloud module import without optional extras
- CLI checks:
  - `uv run python main.py --help`
  - `uv run python main.py --list-plugins`
- Docker checks:
  - image build
  - `--help`
  - `--list-plugins`
  - API `/health`
- Static consistency checks:
  - grep for stale `pip install` commands
  - grep for unprefixed local `python main.py` commands in docs
  - `git diff --check`

Manual verification should be limited to:

- Confirming the chosen Python support range.
- Reading updated docs for user clarity.
- Confirming Docker runtime behavior manually if Docker is unavailable in the implementation environment.

## Implementation Notes

- Do not run networked scraper commands as part of automated verification. They depend on Reddit/mirror availability and may create unwanted data.
- Avoid using `uv run python main.py --dashboard` in automation because it starts a long-running Streamlit server.
- Use import-level dashboard verification instead of starting Streamlit unless a later acceptance check requires browser validation.
- If `uv sync --locked` fails because the lockfile is stale after edits, regenerate with `uv lock` and rerun `uv sync --locked`.
- If Python 3.10 support fails during dependency resolution, pause and decide whether to raise `requires-python` to `>=3.11` to match Docker.
