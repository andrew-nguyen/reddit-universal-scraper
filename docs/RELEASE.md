# Release Process

This project uses `uv` for locking, building, and publishing Python package
artifacts. Releases are intentionally local and explicit for now: bump the
version manually, verify the package, publish to TestPyPI, then test it from a
consumer project before publishing anywhere else.

## Prerequisites

- Python 3.10 or newer
- `uv`
- `just`
- A TestPyPI API token exported as `UV_PUBLISH_TOKEN` before publishing

## Local Release Checklist

1. Update the package version in `pyproject.toml`.
2. Refresh the lockfile:

   ```bash
   just lock
   ```

3. Run the test suite:

   ```bash
   just test
   ```

4. Build the wheel and source distribution:

   ```bash
   just build
   ```

5. Smoke test the built wheel:

   ```bash
   just smoke
   ```

6. Publish to TestPyPI:

   ```bash
   export UV_PUBLISH_TOKEN="pypi-..."
   just publish-testpypi
   ```

For the full local flow, run:

```bash
export UV_PUBLISH_TOKEN="pypi-..."
just release-testpypi
```

`just publish-testpypi` publishes only the current version's wheel and source
distribution, so older files in `dist/` are not uploaded by accident.

## Testing From Another Project

In a consumer project, pin this package to TestPyPI while keeping normal PyPI
available for dependencies:

```toml
[tool.uv.sources]
reddit-universal-scraper = { index = "testpypi" }

[[tool.uv.index]]
name = "testpypi"
url = "https://test.pypi.org/simple/"
explicit = true
```

Then install the release candidate:

```bash
uv add reddit-universal-scraper==<version>
uv run python -c "from reddit_universal_scraper import RedditScraper; print(RedditScraper)"
```

## Publishing Notes

- Do not set TestPyPI as the default index in consumer projects. Use
  `[tool.uv.sources]` so dependencies continue resolving from PyPI.
- Create a git tag only after the TestPyPI artifact has been installed and
  smoke tested from another project.
- If the project later publishes to PyPI from GitHub Actions, prefer PyPI
  trusted publishing over long-lived tokens.
