"""Every page loads; hidden listings stay hidden; expired listings stay
visible (on purpose); login-only and admin-only pages are protected."""
from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from jobs.models import Job
from .helpers import WBTestCase, make_admin, make_job, make_seeker


class PublicPagesTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.job = make_job('Data Capturer')

    def test_every_public_page_loads(self):
        names = ['welcome', 'jobs', 'jobs_public', 'jobs_private', 'internships', 'learnerships',
                 'bursaries', 'careers', 'search', 'market_insights', 'trending_list', 'about',
                 'contact', 'privacy', 'terms', 'login', 'register', 'password_reset', 'sitemap',
                 'robots_txt', 'ads_txt']
        for name in names:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_job_detail_page_loads(self):
        r = self.client.get(self.job.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertPageHas(r, 'Data Capturer')

    def test_old_style_job_link_redirects_to_current_one(self):
        r = self.client.get(reverse('job_detail_legacy', args=[self.job.pk]))
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], self.job.get_absolute_url())

    def test_unknown_page_gives_404(self):
        self.assertEqual(self.client.get('/this-page-does-not-exist/').status_code, 404)

    def test_footer_shows_site_contact_email(self):
        self.assertPageHas(self.client.get(reverse('welcome')), settings.SITE_EMAIL)


class HiddenAndExpiredListingsTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.hidden = make_job('Secret Draft Job', is_active=False)
        self.expired = make_job('Closed Job', deadline=timezone.localdate() - timedelta(days=3))

    def test_hidden_listing_is_404_for_public_and_job_seekers(self):
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse('job_detail_legacy', args=[self.hidden.pk])).status_code, 404)
        self.login(make_seeker())
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)

    def test_admin_can_preview_hidden_listing_with_banner(self):
        self.login(make_admin())
        r = self.client.get(self.hidden.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertPageHas(r, 'Admin preview')

    def test_hidden_listing_not_in_lists_search_or_sitemap(self):
        for url in [reverse('jobs_private'), reverse('search') + '?q=Secret', reverse('sitemap')]:
            with self.subTest(url=url):
                self.assertPageLacks(self.client.get(url), 'Secret Draft Job')
        self.assertPageLacks(self.client.get(reverse('sitemap')), self.hidden.get_absolute_url())

    def test_expired_listing_still_visible_with_label(self):
        r = self.client.get(self.expired.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertPageHas(r, 'Expired')


class AccessControlTest(WBTestCase):
    LOGIN_ONLY = ['profile', 'profile_edit', 'recommended_jobs', 'application_tracker', 'job_alerts',
                  'account_settings', 'account_delete', 'password_change', 'account_download']
    ADMIN_ONLY = ['admin_listing_insights', 'admin_analytics', 'admin_backups',
                  'admin_backup_download_db', 'admin_backup_download_full']

    def test_login_only_pages_send_visitors_to_login(self):
        for name in self.LOGIN_ONLY:
            with self.subTest(page=name):
                r = self.client.get(reverse(name))
                self.assertEqual(r.status_code, 302)
                self.assertIn(reverse('login'), r['Location'])

    def test_login_only_pages_work_when_logged_in(self):
        self.login(make_seeker())
        for name in self.LOGIN_ONLY:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_admin_pages_blocked_for_visitors_and_job_seekers(self):
        for who in (None, make_seeker()):
            if who:
                self.login(who)
            for name in self.ADMIN_ONLY:
                with self.subTest(page=name, logged_in=bool(who)):
                    self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_admin_pages_open_for_admin(self):
        make_job()
        self.login(make_admin())
        for name in self.ADMIN_ONLY + ['admin:index', 'admin:jobs_job_changelist']:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
