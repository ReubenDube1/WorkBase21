"""Run the real-browser "phone checks" (jobs/tests/test_phone.py).

    python manage.py phone_check

One-time setup on your computer:
    pip install -r requirements-dev.txt
    playwright install chromium
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Open the site in a real browser at phone, tablet and laptop sizes and check the layout."

    def handle(self, *args, **options):
        try:
            import playwright  # noqa: F401
        except ImportError:
            self.stdout.write(self.style.ERROR("Phone checks need Playwright, which isn't installed yet."))
            self.stdout.write("Run these two commands once, then try again:\n"
                              "    pip install -r requirements-dev.txt\n"
                              "    playwright install chromium")
            return
        self.stdout.write("Opening the site in a real browser at phone, tablet and laptop sizes "
                          "(takes a few minutes)...")
        call_command('test', 'jobs.tests.test_phone', tags=['browser'])
