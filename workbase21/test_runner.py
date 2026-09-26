"""Test runner that leaves out the slower real-browser "phone checks"
(tagged 'browser') from a normal `python manage.py test`, so the everyday
run stays quick. Run them on their own with:  python manage.py phone_check
"""
import logging
import warnings

from django.test.runner import DiscoverRunner


class WorkBaseTestRunner(DiscoverRunner):
    def __init__(self, *args, tags=None, exclude_tags=None, **kwargs):
        exclude_tags = set(exclude_tags or [])
        if not tags or 'browser' not in tags:
            exclude_tags.add('browser')
        super().__init__(*args, tags=tags, exclude_tags=exclude_tags, **kwargs)

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        # Harmless during tests (static files aren't collected locally).
        warnings.filterwarnings('ignore', message='No directory at', category=UserWarning)
        # Keep test output readable: the site's own log lines (e.g. "backup
        # emailed", or errors from tests that simulate Gmail being down) are
        # expected during tests, so they aren't printed. Tests that check
        # logging still see them.
        for name in ('jobs', 'accounts', 'django.contrib.auth', 'django.request'):
            logger = logging.getLogger(name)
            logger.handlers = [logging.NullHandler()]
            logger.propagate = False
