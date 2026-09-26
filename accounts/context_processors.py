import time

ALERT_COUNT_SESSION_KEY = 'job_alert_count_cache'
CACHE_SECONDS = 600


def job_alert_count(request):
    """Number of new listings across the logged-in user's saved
    searches, for the small badge in the header. Cached in the session
    for 10 minutes so it doesn't add database work to every page."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    cached = request.session.get(ALERT_COUNT_SESSION_KEY)
    now = time.time()
    if cached and now - cached.get('t', 0) < CACHE_SECONDS:
        return {'job_alert_count': cached.get('n', 0)}

    from .models import SavedSearch
    total = sum(s.new_jobs().count() for s in SavedSearch.objects.filter(user=user))
    request.session[ALERT_COUNT_SESSION_KEY] = {'t': now, 'n': total}
    return {'job_alert_count': total}
