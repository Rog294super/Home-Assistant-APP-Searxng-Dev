from urllib.parse import urlsplit


def validate_base_url(value):
    """Validate a SearXNG base_url and reject obvious misconfigurations."""
    if value is None:
        raise ValueError("base_url is empty")

    candidate = str(value).strip()
    if not candidate:
        raise ValueError("base_url is empty")

    if not candidate.startswith(("http://", "https://")):
        raise ValueError("base_url must start with http:// or https://")

    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base_url scheme must be http or https")

    if not parsed.netloc:
        raise ValueError("base_url must include a host, for example http://searxng.local/")

    if parsed.path.startswith("//"):
        raise ValueError("base_url must not contain a double slash after the hostname")

    return candidate
