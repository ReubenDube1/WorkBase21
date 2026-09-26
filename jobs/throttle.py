"""Tiny rate limiter for forms that send email (password reset,
contact). Protects the free Gmail sending quota and stops the forms
being used to spam people. Uses Django's default in-memory cache,
which is fine for this site's single Render instance."""
from django.core.cache import cache


def client_ip(request):
    # Render sits behind a proxy; the visitor's IP is the first entry.
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def over_limit(key, limit, window_seconds=3600):
    """Counts one hit for `key`; True once more than `limit` hits
    happen within the window."""
    cache.add(key, 0, window_seconds)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window_seconds)
        count = 1
    return count > limit
