"""Backups: downloads are valid, restore brings data back, bad files are
refused without changing anything, only superusers can restore, and the
weekly email sends once a week (never twice at once)."""
import gzip
import io
import shutil
import sqlite3
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from jobs import backup
from jobs.models import Job
from .helpers import PASSWORD, make_admin, make_job, make_seeker


class BackupTestBase(TransactionTestCase):
    """Restore replaces the database file, so these tests use real
    transactions (TransactionTestCase). Backup files and uploads go to a
    temporary folder that's deleted afterwards."""

    def setUp(self):
        cache.clear()
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / 'media' / 'job_images').mkdir(parents=True)
        (self.tmp / 'media' / 'job_images' / 'photo.jpg').write_bytes(b'\xff\xd8 fake image ' * 500)
        self.settings_override = override_settings(BACKUP_DIR=str(self.tmp / 'backups'), MEDIA_ROOT=str(self.tmp / 'media'))
        self.settings_override.enable()
        self.boss = make_admin()
        self.client.force_login(self.boss)
        for i in range(4):
            make_job(f'Listing {i}')

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def download_db(self):
        return self.client.get(reverse('admin_backup_download_db')).content

    def restore(self, content, name='backup.sqlite3.gz', confirm='RESTORE'):
        return self.client.post(reverse('admin_backup_restore'),
                                {'confirm': confirm, 'backup_file': SimpleUploadedFile(name, content)}, follow=True)


class DownloadTest(BackupTestBase):
    def test_database_download_is_a_valid_complete_copy(self):
        data = self.download_db()
        self.assertEqual(data[:2], b'\x1f\x8b', "download should be gzip-compressed")
        path = self.tmp / 'check.sqlite3'
        path.write_bytes(gzip.decompress(data))
        con = sqlite3.connect(path)
        self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(con.execute('SELECT COUNT(*) FROM jobs_job').fetchone()[0], 4)
        con.close()

    def test_full_download_contains_database_and_uploads(self):
        r = self.client.get(reverse('admin_backup_download_full'))
        zf = zipfile.ZipFile(io.BytesIO(b''.join(r.streaming_content)))
        self.assertIn('db.sqlite3', zf.namelist())
        self.assertIn('HOW-TO-RESTORE.txt', zf.namelist())
        self.assertEqual(zf.read('media/job_images/photo.jpg'),
                         (self.tmp / 'media' / 'job_images' / 'photo.jpg').read_bytes())
        self.assertIsNone(zf.testzip(), "every file in the zip should be intact")

    def test_backups_page_loads(self):
        self.assertEqual(self.client.get(reverse('admin_backups')).status_code, 200)


class RestoreTest(BackupTestBase):
    def test_practice_restore_brings_everything_back(self):
        good = self.download_db()
        titles = sorted(Job.objects.values_list('title', flat=True))
        Job.objects.filter(title='Listing 0').delete()
        Job.objects.update(title='DAMAGED')
        r = self.restore(good)
        self.assertIn('Database restored', r.content.decode())
        self.assertEqual(sorted(Job.objects.values_list('title', flat=True)), titles)
        safety = sorted((self.tmp / 'backups').glob('db-before-restore-*.sqlite3'))
        self.assertEqual(len(safety), 1, "a safety copy should be saved before restoring")
        con = sqlite3.connect(safety[0])
        self.assertGreater(con.execute("SELECT COUNT(*) FROM jobs_job WHERE title='DAMAGED'").fetchone()[0], 0)
        con.close()

    def test_restore_from_full_zip(self):
        blob = b''.join(self.client.get(reverse('admin_backup_download_full')).streaming_content)
        Job.objects.all().delete()
        self.restore(blob, name='full.zip')
        self.assertEqual(Job.objects.count(), 4)

    def assert_refused(self, response, message):
        self.assertIn(message, response.content.decode())
        self.assertEqual(Job.objects.filter(title='CHANGED').count(), 4, "nothing should have changed")

    def test_bad_files_refused_without_changing_anything(self):
        good = self.download_db()
        Job.objects.update(title='CHANGED')
        other = self.tmp / 'other.sqlite3'
        con = sqlite3.connect(other); con.execute('create table x(a)'); con.commit(); con.close()
        cases = [
            ('wrong confirmation word', good, 'restore', 'type RESTORE'),
            ('not a database', b'hello, just some text', 'RESTORE', "isn&#x27;t a database backup"),
            ('half-downloaded .gz', good[:len(good) // 2], 'RESTORE', 'damaged or incomplete'),
            ("someone else's database", other.read_bytes(), 'RESTORE', "isn&#x27;t a WorkBase21 backup"),
        ]
        for label, content, confirm, message in cases:
            with self.subTest(case=label):
                self.assert_refused(self.restore(content, confirm=confirm), message)

    def test_only_superusers_can_restore(self):
        good = self.download_db()
        staff = make_admin('staffer', superuser=False)
        self.client.force_login(staff)
        r = self.client.post(reverse('admin_backup_restore'), {'confirm': 'RESTORE', 'backup_file': SimpleUploadedFile('b.gz', good)})
        self.assertEqual(r.status_code, 403)

    def test_job_seekers_cannot_download(self):
        self.client.force_login(make_seeker())
        self.assertEqual(self.client.get(reverse('admin_backup_download_db')).status_code, 302)


class WeeklyEmailTest(BackupTestBase):
    def setUp(self):
        super().setUp()
        backup._next_check = 0.0
        mail.outbox = []
        self.configured = mock.patch.object(backup, 'email_is_configured', return_value=True)
        self.configured.start()

    def tearDown(self):
        self.configured.stop()
        super().tearDown()

    def visit(self):
        backup._next_check = 0.0          # skip the "once an hour" wait
        self.client.get(reverse('welcome'))
        for t in threading.enumerate():
            if t.name == 'weekly-backup':
                t.join(10)

    def test_first_visit_sends_a_valid_backup_to_site_inbox(self):
        self.visit()
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        name, content, _ = m.attachments[0]
        self.assertTrue(name.endswith('.sqlite3.gz'))
        path = self.tmp / 'w.sqlite3'; path.write_bytes(gzip.decompress(content))
        con = sqlite3.connect(path)
        self.assertEqual(con.execute('SELECT COUNT(*) FROM jobs_job').fetchone()[0], 4)
        con.close()

    def test_not_sent_twice_in_a_week_but_sent_again_after(self):
        self.visit(); self.visit(); self.visit()
        self.assertEqual(len(mail.outbox), 1)
        backup._state_file().write_text(str(time.time() - 8 * 24 * 3600))
        self.visit()
        self.assertEqual(len(mail.outbox), 2)

    def test_lock_prevents_two_at_once(self):
        (backup.backup_dir() / 'weekly.lock').write_text('busy')
        self.visit()
        self.assertEqual(len(mail.outbox), 0)

    def test_gmail_failure_does_not_break_site_and_retries(self):
        with mock.patch.object(backup, 'email_database_backup', side_effect=OSError('down')), \
             mock.patch('jobs.backup.logger'):
            self.visit()
        self.assertFalse((backup.backup_dir() / 'weekly.lock').exists(), "lock must be released for a retry")
        self.assertEqual(self.client.get(reverse('welcome')).status_code, 200)

    def test_email_now_button(self):
        r = self.client.post(reverse('admin_backup_email_now'), follow=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Backup emailed to', r.content.decode())


class WeeklyEmailOffTest(BackupTestBase):
    def test_nothing_sent_when_email_not_set_up(self):
        backup._next_check = 0.0
        self.client.get(reverse('welcome'))
        time.sleep(0.2)
        self.assertEqual(len(mail.outbox), 0)
