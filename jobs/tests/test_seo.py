"""AdSense / search readiness: pages with real content are indexable and may
carry ads; utility pages (login, sign-up, search, contact, account pages,
404) are neither indexed nor shown ads; titles are never empty; robots.txt
and the sitemap list the right things."""
import re

from django.urls import reverse

from accounts.models import CareerPath
from jobs.models import TrendingTopic
from .helpers import WBTestCase, make_job, make_seeker

AD_SCRIPT = 'pagead2.googlesyndication.com'


def robots_meta(html):
    return re.search(r'<meta name="robots" content="([^"]*)"', html).group(1)


def title(html):
    return re.search(r'<title>(.*?)</title>', html, re.S).group(1).strip()


class IndexingAndAdsRulesTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.job = make_job('Data Capturer')
        self.article = TrendingTopic.objects.create(title='How to write a CV', body='<p>Real article.</p>')
        from django.core.management import call_command
        import io
        call_command('seed_career_graph', stdout=io.StringIO())

    def html(self, url, **kw):
        r = self.client.get(url, **kw)
        return r, r.content.decode()

    def test_content_pages_are_indexable_and_may_show_ads(self):
        urls = [reverse('welcome'), reverse('jobs'), reverse('jobs_private'), reverse('internships'),
                reverse('trending_list'), reverse('careers'), reverse('market_insights'),
                reverse('about'), reverse('privacy'), reverse('terms'),
                self.job.get_absolute_url(), self.article.get_absolute_url(),
                CareerPath.objects.first().get_absolute_url()]
        for url in urls:
            with self.subTest(page=url):
                r, h = self.html(url)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(robots_meta(h), 'index, follow')
                self.assertIn(AD_SCRIPT, h)

    def test_utility_pages_are_not_indexed_and_have_no_ads(self):
        urls = [reverse('login'), reverse('register'), reverse('password_reset'),
                reverse('password_reset_done'), reverse('search'), reverse('search') + '?q=clerk']
        for url in urls:
            with self.subTest(page=url):
                r, h = self.html(url)
                self.assertEqual(robots_meta(h), 'noindex, follow')
                self.assertNotIn(AD_SCRIPT, h)

    def test_contact_page_is_indexable_but_has_no_ads(self):
        r, h = self.html(reverse('contact'))
        self.assertEqual(robots_meta(h), 'index, follow')
        self.assertNotIn(AD_SCRIPT, h)

    def test_logged_in_pages_have_no_ads(self):
        self.login(make_seeker())
        for name in ('profile', 'recommended_jobs', 'application_tracker', 'job_alerts', 'account_settings'):
            with self.subTest(page=name):
                r, h = self.html(reverse(name))
                self.assertEqual(r.status_code, 200)
                self.assertNotIn(AD_SCRIPT, h)
        r, h = self.html(reverse('job_eligibility', args=[self.job.pk]))
        self.assertNotIn(AD_SCRIPT, h)

    def test_404_page_is_never_indexed_and_has_no_ads(self):
        r = self.client.get('/this-page-does-not-exist/')   # the real 404 handling, as a visitor gets it
        self.assertEqual(r.status_code, 404)
        h = r.content.decode()
        self.assertEqual(robots_meta(h), 'noindex, nofollow')
        self.assertNotIn(AD_SCRIPT, h)

    def test_no_page_has_an_empty_title(self):
        urls = [reverse(n) for n in ('welcome', 'login', 'register', 'password_reset', 'password_reset_done',
                                    'contact', 'search', 'careers')]
        for url in urls:
            with self.subTest(page=url):
                t = title(self.html(url)[1])
                self.assertFalse(t.startswith('|'), f"empty page title on {url}: {t!r}")
                self.assertGreater(len(t), len(' | WorkBase21'))


class RobotsAndSitemapTest(WBTestCase):
    def test_robots_txt(self):
        text = self.client.get(reverse('robots_txt')).content.decode()
        for line in ('Disallow: /admin/', 'Disallow: /accounts/', 'Disallow: /search/', 'Disallow: /recommended/'):
            self.assertIn(line, text)
        self.assertNotIn('ckeditor', text.lower())
        self.assertIn('Sitemap: https://', text)
        self.assertNotIn('Disallow: /\n', text, "must not block the whole site")

    def test_sitemap_lists_content_pages_but_not_hidden_or_utility_ones(self):
        import io
        from django.core.management import call_command
        call_command('seed_career_graph', stdout=io.StringIO())
        live = make_job('Public Listing')
        hidden = make_job('Hidden Listing', is_active=False)
        card_only = TrendingTopic.objects.create(title='Stat card only', body='')
        article = TrendingTopic.objects.create(title='Real article', body='<p>Body</p>')
        xml = self.client.get(reverse('sitemap')).content.decode()
        for url in (live.get_absolute_url(), article.get_absolute_url(), reverse('careers'),
                    reverse('market_insights'), CareerPath.objects.first().get_absolute_url()):
            self.assertIn(url, xml)
        self.assertNotIn(hidden.get_absolute_url(), xml)
        self.assertNotIn('/accounts/', xml)
        self.assertNotIn('/search/', xml)


class JobsChoicePageContentTest(WBTestCase):
    def test_jobs_page_has_real_guidance_not_just_two_buttons(self):
        h = self.client.get(reverse('jobs')).content.decode()
        text = re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style).*?</\1>', '', h, flags=re.S))
        self.assertGreater(len(text.split()), 250)
        self.assertIn('Z83', h)
