import hashlib
import hmac

from django.conf import settings
from django.core.cache import cache


def _allow_attempt(action, identity):
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{action}:{identity}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    key = f"auth-rate:{digest}"
    if cache.add(key, 1, timeout=settings.ACCOUNT_RATE_LIMIT_WINDOW_SECONDS):
        return True
    try:
        return cache.incr(key) <= settings.ACCOUNT_RATE_LIMIT_ATTEMPTS
    except ValueError:
        return cache.add(key, 1, timeout=settings.ACCOUNT_RATE_LIMIT_WINDOW_SECONDS)


def allow_sensitive_action(action, email="", remote_addr=""):
    checks = []
    if email:
        checks.append((action, email.strip().casefold()))
    if remote_addr:
        checks.append((f"{action}-ip", remote_addr.strip()))
    return all(_allow_attempt(name, identity) for name, identity in checks)
