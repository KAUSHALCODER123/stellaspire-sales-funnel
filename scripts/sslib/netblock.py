"""Tell a sandbox that refuses a host apart from a provider that rejects a key."""
import urllib.error


def blocked_host(exc: urllib.error.HTTPError, host: str) -> str | None:
    """`network_blocked:<host>` when the 403 comes from the session's network allowlist, else None."""
    try:
        body = exc.read(400).decode("utf-8", "ignore").lower()
    except Exception:
        body = ""
    if exc.code == 403 and ("not allowed" in body or "blocked" in body or "allowlist" in body):
        return f"network_blocked:{host}"
    return None
