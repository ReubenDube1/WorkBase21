"""Lightweight, privacy-friendly site-visit logging.

Logs one PageVisit row per real page request so the admin can see how
many people are visiting the site (see jobs/admin_analytics.py). No IP
addresses or personal data are recorded — only the path and the
anonymous session key Django already assigns to every visitor.
"""
import re

from .models import PageVisit

# Paths we never want cluttering the analytics — admin, static/media
# assets, CKEditor, and the various SEO/bot-facing endpoints.
_EXCLUDED_PREFIXES = (
    '/admin/', '/ckeditor/', '/static/', '/media/',
)
_EXCLUDED_EXACT = (
    '/robots.txt', '/ads.txt', '/sitemap.xml', '/favicon.ico',
)
_JOB_DETAIL_RE = re.compile(r'^/job/(?P<pk>\d+)/')


class VisitTrackingMiddleware:
    """Records a PageVisit for every real, successful GET page view."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._maybe_log(request, response)
        except Exception:
            # Analytics must never be able to break the site.
            pass
        return response

    def _maybe_log(self, request, response):
        if request.method != 'GET':
            return
        if getattr(response, 'streaming', False):
            return
        if response.status_code >= 400:
            return

        path = request.path
        if path.startswith(_EXCLUDED_PREFIXES) or path in _EXCLUDED_EXACT:
            return

        # Skip requests explicitly flagged as bots isn't reliable without
        # a dependency, so we keep it simple — this still gives an
        # accurate relative picture of traffic and per-job popularity.

        if not request.session.session_key:
            request.session.save()

        job_id = None
        match = _JOB_DETAIL_RE.match(path)
        if match:
            job_id = match.group('pk')

        PageVisit.objects.create(
            path=path[:500],
            session_key=request.session.session_key or '',
            job_id=job_id,
        )


class WeeklyBackupMiddleware:
    """Triggers the weekly emailed database backup (see jobs/backup.py).
    Render has no free scheduler that can reach the disk, so normal site
    traffic is used as the clock: after each response it cheaply checks
    (at most once an hour) whether a backup is due, and if so sends it in
    the background — visitors are never kept waiting."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            from .backup import maybe_send_weekly_backup
            maybe_send_weekly_backup()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Weekly backup check failed")
        return response
