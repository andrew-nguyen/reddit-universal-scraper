"""Default scraper settings shared by the public package."""

import os
import random
import string
from pathlib import Path
from urllib.parse import urlparse, urlunparse


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

MIRRORS = [
    "https://old.reddit.com",
    "https://redlib.privadency.com",
    "https://redlib.orangenet.cc",
    "https://red.artemislena.eu",
]

DEFAULT_DATA_DIR = Path("data")


def load_env_file(env_path: str | os.PathLike[str] = ".env") -> None:
    """Load key=value defaults from an env file without overriding shell env."""
    path = Path(env_path)
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()

PROXY_URL = os.getenv("PROXY_URL", "")
PROXY_COUNTRY = os.getenv("PROXY_COUNTRY", "")
PROXY_SESSION_ID = os.getenv("PROXY_SESSION_ID", "")
PROXY_AUTO_ROTATE = os.getenv("PROXY_AUTO_ROTATE", "true").lower() in ("true", "1", "yes")
DIRECT_PROXY_VALUES = {"none", "direct", "disabled", ""}


def is_proxy_disabled(proxy_url: str | None) -> bool:
    """Return True when a proxy value means direct connection."""
    if proxy_url is None:
        return True
    return proxy_url.strip().lower() in DIRECT_PROXY_VALUES


def _random_session_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def get_formatted_proxy_url(
    proxy_url: str,
    country: str | None = None,
    session_id: str | None = None,
    force_rotate: bool = False,
    auto_rotate: bool | None = None,
) -> str:
    """Format ScrapingAnt proxy usernames with optional country/session targeting."""
    if not proxy_url:
        return proxy_url

    try:
        parsed = urlparse(proxy_url)
        username = parsed.username

        if not username or not username.startswith("customer-"):
            return proxy_url

        parts = username.split("-")
        new_username_parts = parts[:2] if len(parts) >= 2 else parts
        original_country = ""
        original_session = ""

        i = 2
        while i < len(parts):
            if parts[i] == "country" and i + 1 < len(parts):
                original_country = parts[i + 1]
                i += 2
            elif parts[i] == "sessionid" and i + 1 < len(parts):
                original_session = parts[i + 1]
                i += 2
            else:
                new_username_parts.append(parts[i])
                i += 1

        configured_country = country if country is not None else PROXY_COUNTRY
        if configured_country and configured_country.lower() != "none":
            final_country = configured_country.lower()
        elif configured_country and configured_country.lower() == "none":
            final_country = ""
        else:
            final_country = original_country

        configured_session = session_id if session_id is not None else PROXY_SESSION_ID
        should_auto_rotate = PROXY_AUTO_ROTATE if auto_rotate is None else auto_rotate
        if configured_session and configured_session.lower() == "auto":
            final_session = _random_session_id()
        elif configured_session and configured_session.lower() == "none":
            final_session = ""
        elif configured_session:
            final_session = configured_session
        elif force_rotate and should_auto_rotate:
            final_session = _random_session_id()
        else:
            final_session = original_session

        if final_country:
            new_username_parts.extend(["country", final_country])
        if final_session:
            new_username_parts.extend(["sessionid", final_session])

        auth = "-".join(new_username_parts)
        if parsed.password is not None:
            auth += f":{parsed.password}"
        netloc = f"{auth}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"

        return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    except Exception:
        return proxy_url
