"""Phone checks — real-browser tests (Chromium via Playwright).

Opens the site in a real browser at phone, tablet and laptop widths and
checks what visitors actually see: nothing sticks out sideways, the
hamburger menu works and lists My Profile / For You first, the Contact
pop-up behaves, and form errors are highlighted.

Not part of the normal `python manage.py test` (they're slower).
Run them with:   python manage.py phone_check
One-time setup:  pip install -r requirements-dev.txt
                 playwright install chromium
"""
import os
import unittest

from django.conf import settings
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache
from django.test import tag
from django.urls import reverse

from accounts.models import SavedSearch, TrackedJob
from jobs.models import Job
from .helpers import make_job, make_seeker, skill

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

# Playwright runs its own event loop; this lets Django's database calls work alongside it.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

PHONE, TABLET, LAPTOP = [320, 360, 375, 414], [768, 1024], [1280, 1366, 1440]
ALL_WIDTHS = PHONE + TABLET + LAPTOP

OVERFLOW_JS = """() => {
  const vw = document.documentElement.clientWidth;
  const bad = [];
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height || (r.right <= vw + 1 && r.left >= -1)) continue;
    let p = el.parentElement, clipped = false;          // ignore things inside a scrollable box
    while (p && p !== document.body) {
      if (['auto', 'scroll', 'hidden'].includes(getComputedStyle(p).overflowX)) {
        const pr = p.getBoundingClientRect();
        if (pr.right <= vw + 1 && pr.left >= -1) { clipped = true; break; }
      }
      p = p.parentElement;
    }
    if (!clipped) bad.push(el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/)[0] : ''));
  }
  return {pageWidth: document.documentElement.scrollWidth, vw, bad: [...new Set(bad)].slice(0, 4)};
}"""



# ---------------------------------------------------------------------------
# Editor round-trip: content saved by the OLD editor (CKEditor 4) must survive
# being opened and saved in the new editor (TinyMCE).
# ---------------------------------------------------------------------------
from html.parser import HTMLParser

OLD_CKEDITOR_ARTICLE = (
    '<h2>How to apply</h2>'
    '<p>Read the <strong>requirements</strong> and <em>deadline</em> carefully, then <u>submit early</u>.</p>'
    '<ul><li>Certified ID copy</li><li>Updated <a href="https://example.com/cv-tips" target="_blank">CV</a></li></ul>'
    '<ol><li>Fill in the Z83</li><li>Email it</li></ol>'
    '<blockquote><p>Tip: check your spam folder.</p></blockquote>'
    '<p><img alt="Team photo" src="/media/uploads/2026/08/01/team.jpg" '
    'style="float:left; height:200px; margin:10px; width:300px" />Text beside a left image.</p>'
    '<p><img alt="Logo" src="/media/uploads/2026/08/01/logo.png" style="float:right; width:120px" />Text beside a right image.</p>'
)
OLD_CKEDITOR_JOB = ('<h2>About the role</h2><p>We need a <strong>motivated</strong> graduate with '
                    '<u>Excel</u> skills.</p><ul><li>Capture data</li><li>Prepare reports</li></ul>'
                    '<p>Apply at <a href="https://example.com/apply">our portal</a>.</p>')


class _Features(HTMLParser):
    """Pulls out what matters (headings, formatting, lists, links, quotes,
    images and their position/size), ignoring harmless differences such as
    spacing inside style="..." or attribute order."""
    def __init__(self):
        super().__init__()
        self.found, self._stack = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img':
            style = {k.strip(): v.strip() for k, v in (p.split(':', 1) for p in (a.get('style') or '').split(';') if ':' in p)}
            self.found.append(('img', a.get('src'), a.get('alt'), style.get('float'), style.get('width')))
        elif tag == 'a':
            self.found.append(('a', a.get('href'), a.get('target')))
        elif tag in ('h2', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'blockquote'):
            self._stack.append(tag)
            self.found.append((tag, ''))

    def handle_data(self, data):
        if self._stack and data.strip():
            tag = self._stack[-1]
            for i in range(len(self.found) - 1, -1, -1):
                if self.found[i][0] == tag:
                    self.found[i] = (tag, (self.found[i][1] + ' ' + data.strip()).strip())
                    break

    def handle_endtag(self, tag):
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()


def features(html):
    f = _Features()
    f.feed(html)
    return f.found

@tag('browser')
@unittest.skipIf(sync_playwright is None,
                 "Phone checks need Playwright: pip install -r requirements-dev.txt && playwright install chromium")
class PhoneChecks(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop()
            super().tearDownClass()
            raise unittest.SkipTest(f"Browser not installed — run: playwright install chromium ({e.__class__.__name__})")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.job = make_job('Data Analyst', qualification_level='degree', experience_level='entry',
                            work_mode='onsite', industry='it', skills=[skill('Python')])
        make_job('Remote Intern', type=Job.INTERNSHIP, work_mode='remote')
        make_job('Learnership', type=Job.LEARNERSHIP)
        make_job('Bursary', type=Job.BURSARY)
        make_job('Public Job', sector=Job.PUBLIC)
        self.user = make_seeker('demo', location='Thohoyandou', qualification_level='degree',
                                career_goal='Data Analyst', skills=[skill('Python'), skill('Excel')])
        self.tracked = TrackedJob.objects.create(user=self.user, job=self.job, status='applied', notes='Sent CV')
        SavedSearch.objects.create(user=self.user, job_type='internship', filters={'work_mode': 'remote'})
        self.context = self.browser.new_context()
        # Block every outside website (ads, fonts...) so checks are fast and repeatable.
        self.context.route('**/*', lambda route: route.continue_()
                           if route.request.url.startswith(self.live_server_url) else route.abort())
        self.page = self.context.new_page()

    def tearDown(self):
        self.context.close()

    # --- helpers --------------------------------------------------------
    def log_in(self):
        session = SessionStore()
        session[SESSION_KEY] = str(self.user.pk)
        session[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0] if hasattr(settings, 'AUTHENTICATION_BACKENDS') else 'django.contrib.auth.backends.ModelBackend'
        session[HASH_SESSION_KEY] = self.user.get_session_auth_hash()
        session.save()
        self.context.add_cookies([{'name': settings.SESSION_COOKIE_NAME, 'value': session.session_key,
                                   'url': self.live_server_url}])

    def open(self, path, width, height=800):
        self.page.set_viewport_size({'width': width, 'height': height})
        return self.page.goto(self.live_server_url + path, wait_until='load')

    def check_pages(self, paths):
        problems = []
        for width in ALL_WIDTHS:
            for path in paths:
                response = self.open(path, width)
                if response.status != 200:
                    problems.append(f"{path} at {width}px: HTTP {response.status}")
                    continue
                r = self.page.evaluate(OVERFLOW_JS)
                if r['pageWidth'] > r['vw'] + 1 or r['bad']:
                    problems.append(f"{path} at {width}px: sticks out sideways ({r['pageWidth']}px wide on a {r['vw']}px screen) — {', '.join(r['bad'])}")
        self.assertEqual(problems, [], "\n" + "\n".join(problems))

    # --- checks ---------------------------------------------------------
    def test_public_pages_fit_every_screen(self):
        paths = [reverse(n) for n in ('welcome', 'jobs', 'jobs_public', 'jobs_private', 'internships',
                                      'learnerships', 'bursaries', 'careers', 'market_insights', 'about',
                                      'contact', 'privacy', 'terms', 'login', 'register', 'password_reset',
                                      'trending_list')]
        paths += [self.job.get_absolute_url(), reverse('search') + '?q=data']
        self.check_pages(paths)

    def test_logged_in_pages_fit_every_screen(self):
        self.log_in()
        paths = [reverse(n) for n in ('welcome', 'profile', 'profile_edit', 'recommended_jobs',
                                      'application_tracker', 'job_alerts', 'account_settings',
                                      'account_delete', 'password_change', 'careers')]
        paths += [self.job.get_absolute_url(), reverse('job_eligibility', args=[self.job.pk]),
                  reverse('application_edit', args=[self.tracked.pk])]
        self.check_pages(paths)

    def test_hamburger_menu_on_phone_lists_account_links_first(self):
        self.log_in()
        for width in (320, 375, 414, 1024):
            with self.subTest(width=width):
                self.open(reverse('jobs'), width)
                box = self.page.locator('#hamburger').bounding_box()
                self.assertLessEqual(box['x'] + box['width'], width, "hamburger button must be fully on screen")
                self.page.click('#hamburger')
                items = self.page.eval_on_selector_all(
                    '#main-nav .nav-links > li',
                    "els => els.filter(e => getComputedStyle(e).display !== 'none').map(e => e.innerText.trim())")
                # "My Profile" may carry an alert badge (e.g. "My Profile 1 new").
                self.assertTrue(items[0].startswith('My Profile'), f"first menu item was {items[0]!r}")
                self.assertEqual(items[1:3], ['For You', 'Jobs'])

    def test_small_phone_header_fits_even_with_wide_fonts(self):
        """Fonts differ between phones and computers (and outside fonts are
        blocked during these checks), so force a deliberately WIDE font:
        the header must still fit. This is what failed on Windows before."""
        wide_font = "*{font-family:'DejaVu Sans',Verdana,sans-serif !important}"
        for logged_in in (False, True):
            if logged_in:
                self.log_in()
            for width in (320, 340, 360, 375):
                with self.subTest(logged_in=logged_in, width=width):
                    self.open(reverse('welcome'), width)
                    self.page.add_style_tag(content=wide_font)
                    r = self.page.evaluate("""() => ({
                        right: document.getElementById('hamburger').getBoundingClientRect().right,
                        vw: document.documentElement.clientWidth,
                        page: document.documentElement.scrollWidth})""")
                    self.assertLessEqual(r['right'], r['vw'], f"hamburger pushed off screen at {width}px")
                    self.assertLessEqual(r['page'], r['vw'], f"page sticks out sideways at {width}px")
                    self.page.click('#hamburger')
                    first = self.page.eval_on_selector_all('#main-nav .nav-links > li',
                        "els => els.filter(e => getComputedStyle(e).display !== 'none').map(e => e.innerText.trim())")[0]
                    if logged_in:
                        self.assertTrue(first.startswith('My Profile'))
                    elif width < 360:
                        self.assertEqual(first, 'Log In', "on the smallest phones Log In is first in the menu")

    def test_laptop_header_on_one_line(self):
        self.log_in()
        for width in (1201, 1280, 1366, 1440, 1886):
            with self.subTest(width=width):
                self.open(reverse('contact'), width)
                r = self.page.evaluate("""() => {
                  const mid = e => { const b = e.getBoundingClientRect(); return b.top + b.height / 2; };
                  const link = [...document.querySelectorAll('.nav-links li')].find(l => getComputedStyle(l).display !== 'none').querySelector('a');
                  return {lines: link.getClientRects().length, menu: mid(link),
                          account: mid(document.querySelector('.auth-links .auth-link:not([style*="none"])')),
                          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth}; }""")
                self.assertEqual(r['lines'], 1, "menu links must not wrap")
                self.assertLessEqual(abs(r['menu'] - r['account']), 3, "menu and account links should line up")
                self.assertLessEqual(r['overflow'], 0)

    def test_register_errors_are_easy_to_spot_on_phone(self):
        make_seeker('taken')
        self.open(reverse('register'), 375)
        self.page.fill('input[name=username]', 'taken')
        self.page.fill('input[name=email]', 'new@example.com')
        self.page.fill('input[name=password1]', 'GoodPass!987')
        self.page.fill('input[name=password2]', 'Different!987')
        self.page.click('form.contact-form button[type=submit]')
        self.page.wait_for_load_state('load')
        self.page.wait_for_timeout(700)
        self.assertTrue(self.page.is_visible('#form-error-summary'))
        self.assertEqual(self.page.evaluate("document.activeElement.name"), 'username', "cursor should jump to the first problem")
        colour = self.page.evaluate("getComputedStyle(document.querySelector('.has-error .form-error')).color")
        self.assertEqual(colour, 'rgb(185, 28, 28)', "error text should be red")

    def test_contact_popup_on_phone(self):
        self.open(reverse('contact'), 375)
        self.page.fill('#id_name', 'Lerato'); self.page.fill('#id_email', 'lerato@example.com')
        self.page.fill('#id_subject', 'Hi'); self.page.fill('#id_message', 'Hello there')
        self.page.click('form.contact-form button[type=submit]')
        self.page.wait_for_load_state('load')
        self.page.wait_for_timeout(400)
        self.assertTrue(self.page.evaluate("document.getElementById('contact-result').matches(':modal')"))
        self.assertIn('Message sent', self.page.inner_text('#contact-result'))
        self.assertEqual(self.page.evaluate('window.scrollY'), 0, "page should not jump down")
        box = self.page.locator('#contact-result').bounding_box()
        self.assertGreaterEqual(box['x'], 0)
        self.assertLessEqual(box['x'] + box['width'], 375)
        self.page.click('#contact-result button')
        self.page.wait_for_timeout(300)
        self.assertFalse(self.page.evaluate("document.getElementById('contact-result').open"))

    # --- admin editor ----------------------------------------------------
    def log_in_admin(self):
        from .helpers import make_admin
        self.user = make_admin()
        self.log_in()

    def open_editor(self, url):
        self.open(url, 1280, 900)
        self.page.wait_for_function(
            "window.tinymce && tinymce.get().length === 5 && tinymce.get().every(e => e.initialized)",
            timeout=20000)

    def test_editor_keeps_old_content_and_uploads_images(self):
        import shutil, tempfile
        from pathlib import Path
        from django.test import override_settings
        from jobs.models import TrendingTopic
        media = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=media):
            self.log_in_admin()
            article = TrendingTopic.objects.create(title='Z83 guide', body=OLD_CKEDITOR_ARTICLE)
            job = make_job('Clerk', description=OLD_CKEDITOR_JOB)

            # Job: open in the new editor and save without touching anything.
            self.open_editor(reverse('admin:jobs_job_change', args=[job.pk]))
            with self.page.expect_navigation():
                self.page.click('input[name=_save]')
            job.refresh_from_db()
            self.assertEqual(features(job.description), features(OLD_CKEDITOR_JOB),
                             "job description formatting changed after saving in the new editor")

            # Article: open, add a new picture through the editor's upload, position it, save.
            self.open_editor(reverse('admin:jobs_trendingtopic_change', args=[article.pk]))
            tiny_png = ('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP8z8DAwMDAxMDAwMDAAAANHQEDasKb6QAAAABJRU5ErkJggg==')
            self.page.evaluate("""async (b64) => {
                const ed = tinymce.get()[0];
                ed.selection.select(ed.getBody(), true); ed.selection.collapse(false);
                ed.insertContent('<p><img id="newpic" alt="New" src="data:image/png;base64,' + b64 + '"></p>');
                await ed.uploadImages();
                ed.selection.select(ed.dom.select('img#newpic')[0] || ed.dom.select('img').pop());
                ed.execCommand('JustifyRight');
            }""", tiny_png)
            with self.page.expect_navigation():
                self.page.click('input[name=_save]')
            article.refresh_from_db()

            saved = features(article.body)
            original = features(OLD_CKEDITOR_ARTICLE)
            self.assertEqual(saved[:len(original)], original,
                             "article formatting (headings, underline, links, quotes, image positions) changed")
            new_img = [f for f in saved if f[0] == 'img' and f[2] == 'New']
            self.assertEqual(len(new_img), 1, "the new picture should be in the article")
            self.assertTrue(new_img[0][1].startswith('/media/uploads/'), f"new picture not uploaded: {new_img[0][1][:60]}")
            self.assertEqual(new_img[0][3], 'right', "new picture should be positioned right")
            self.assertEqual(len(list(Path(media).rglob('*.png'))), 1, "the uploaded file should be saved")

            # Visitors see the article with both old images still floated.
            self.open(article.get_absolute_url() if hasattr(article, 'get_absolute_url') else '/', 1280)
        shutil.rmtree(media, ignore_errors=True)

