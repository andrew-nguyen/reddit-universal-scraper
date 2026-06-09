import tomllib


def test_uv_main_delegates_to_package_cli():
    import uv_main
    from reddit_universal_scraper import cli

    assert uv_main.main is cli.main


def test_package_defines_console_script():
    with open("pyproject.toml", "rb") as fh:
        project = tomllib.load(fh)["project"]

    assert project["scripts"]["reddit-universal-scraper"] == "reddit_universal_scraper.cli:main"
