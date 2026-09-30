"""The admin rich-text editor (TinyMCE 7.9.3) and its image upload.
CKEditor is fully removed; uploads are admin-only, real images only,
no SVG, max 5 MB, and protected against forged requests."""
import io
import json
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from PIL import Image

from jobs.models import TrendingTopic
from .helpers import WBTestCase, make_admin, make_job, make_seeker


def png_bytes(size=(20, 20)):
    buf = io.BytesIO()
    Image.new('RGB', size, (37, 99, 235)).save(buf, 'PNG')
    return buf.getvalue()


class EditorWiringTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.login(make_admin())

    def editor_configs(self, url):
        html = self.client.get(url).content.decode()
        self.assertIn('vendor/tinymce/tinymce', html, "TinyMCE should load on this admin page")
        import re
        return [json.loads(m.replace('&quot;', '"')) for m in re.findall(r'data-editor-config="([^"]+)"', html)]

    def test_job_description_boxes_use_editor_without_images(self):
        job = make_job()
        configs = self.editor_configs(reverse('admin:jobs_job_change', args=[job.pk]))
        self.assertEqual(len(configs), 5, "all 5 description boxes use the editor")
        for c in configs:
            self.assertNotIn('image', c['plugins'])
            self.assertNotIn('upload_url', c)

    def test_article_boxes_use_editor_with_image_upload(self):
        configs = self.editor_configs(reverse('admin:jobs_trendingtopic_add'))
        self.assertEqual(len(configs), 5, "all 5 article body boxes use the editor")
        for c in configs:
            self.assertIn('image', c['plugins'])
            self.assertEqual(c['upload_url'], reverse('admin_editor_upload_image'))

    def test_ckeditor_is_gone(self):
        self.assertNotIn('ckeditor', settings.INSTALLED_APPS)
        self.assertNotIn('ckeditor_uploader', settings.INSTALLED_APPS)
        self.assertEqual(self.client.get('/ckeditor/upload/').status_code, 404)

    def test_bundled_tinymce_is_the_fixed_version(self):
        js = (Path(settings.BASE_DIR) / 'static/vendor/tinymce/tinymce.min.js').read_text(encoding='utf-8')[:200]
        self.assertIn('TinyMCE version 7.9.3', js, "must include the CVE-2026-47759 fix (7.9.3+)")

    def test_saved_html_is_shown_to_visitors_unchanged(self):
        html = '<p><u>Underlined</u> <img style="float: left; width: 200px;" src="/media/uploads/a.jpg" alt="x"></p>'
        job = make_job(description=html)
        self.assertPageHas(self.client.get(job.get_absolute_url()), html)


    def test_article_link_picker_lists_published_articles_only(self):
        TrendingTopic.objects.create(title='Z83 guide', body='<p>Guide</p>')
        TrendingTopic.objects.create(title='Hidden', body='<p>x</p>', is_active=False)
        TrendingTopic.objects.create(title='Stat card only', body='')
        r = self.client.get(reverse('admin:jobs_job_article_links'))
        titles = [a['title'] for a in r.json()]
        self.assertIn('Z83 guide', titles)
        self.assertNotIn('Hidden', titles, "hidden articles must not be offered")
        self.assertNotIn('Stat card only', titles, "cards without an article page must not be offered")
        page = self.client.get(reverse('admin:jobs_job_add')).content.decode()
        self.assertIn('admin_insert_article_link.js', page, "the picker script must load on the job form")


class ImageUploadTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.url = reverse('admin_editor_upload_image')

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def upload(self, content, name='pic.png', client=None):
        return (client or self.client).post(self.url, {'file': SimpleUploadedFile(name, content)})

    def uploaded_files(self):
        return [p for p in Path(self.media).rglob('*') if p.is_file()]

    def test_admin_can_upload_a_real_image(self):
        self.login(make_admin())
        r = self.upload(png_bytes())
        self.assertEqual(r.status_code, 200)
        location = r.json()['location']
        self.assertTrue(location.startswith(settings.MEDIA_URL + 'uploads/'))
        self.assertTrue(location.endswith('.png'))
        self.assertEqual(len(self.uploaded_files()), 1)

    def test_refused_files_are_not_saved(self):
        self.login(make_admin())
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        big = png_bytes() + b'\0' * (5 * 1024 * 1024)
        cases = [
            ('text file pretending to be a picture', b'just some text', 'photo.png'),
            ('SVG (can hide scripts)', svg, 'logo.svg'),
            ('larger than 5 MB', big, 'huge.png'),
        ]
        for label, content, name in cases:
            with self.subTest(case=label):
                r = self.upload(content, name)
                self.assertEqual(r.status_code, 400)
                self.assertIn('error', r.json())
        self.assertEqual(self.uploaded_files(), [], "nothing should be saved")

    def test_only_admins_can_upload(self):
        self.assertEqual(self.upload(png_bytes()).status_code, 302)          # visitor -> login
        self.login(make_seeker())
        self.assertEqual(self.upload(png_bytes()).status_code, 302)          # job seeker -> login
        self.assertEqual(self.uploaded_files(), [])

    def test_get_not_allowed_and_forged_requests_blocked(self):
        admin = make_admin()
        self.login(admin)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(admin)
        self.assertEqual(self.upload(png_bytes(), client=strict).status_code, 403, "needs the security token")
        self.assertEqual(self.uploaded_files(), [])
