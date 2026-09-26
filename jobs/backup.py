"""Backups for WorkBase21 (free, no external services).

Render already snapshots the whole disk daily and keeps 7 days (Render
dashboard -> Disk -> Snapshots). This module covers what that doesn't:
  * copies kept OUTSIDE Render (download to your laptop / weekly email),
  * copies older than 7 days,
  * restoring the database from an older copy.

Database copies use SQLite's own "online backup", which makes a correct
copy even while people are using the site (a plain file copy taken at
the wrong moment can be corrupt). Every copy is integrity-checked.
"""
import gzip
import logging
import os
import sqlite3
import tempfile
import threading
import time
import zipfile
import zlib
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)

WEEK_SECONDS = 7 * 24 * 60 * 60
KEEP_SAFETY_COPIES = 3


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def db_path():
    # The database Django is ACTUALLY using right now. During tests this is
    # the temporary test database, never the real one.
    from django.db import connections
    return Path(connections['default'].settings_dict['NAME'])


def media_root():
    return Path(settings.MEDIA_ROOT)


def backup_dir():
    """Small folder next to the database for backup bookkeeping and the
    safety copy made before a restore (on Render: /var/data/backups)."""
    d = Path(getattr(settings, 'BACKUP_DIR', None) or (db_path().parent / 'backups'))
    d.mkdir(parents=True, exist_ok=True)
    return d


def stamp():
    return timezone.localtime().strftime('%Y-%m-%d-%H%M')


def human_size(n):
    for unit in ('bytes', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f"{n:.0f} {unit}" if unit == 'bytes' else f"{n:.1f} {unit}"
        n /= 1024


def media_size():
    root = media_root()
    if not root.exists():
        return 0, 0
    total = count = 0
    for p in root.rglob('*'):
        if p.is_file():
            total += p.stat().st_size
            count += 1
    return total, count


# ---------------------------------------------------------------------------
# Making copies
# ---------------------------------------------------------------------------

def copy_database_to(dest):
    """Safe, consistent copy of the live database, integrity-checked."""
    src = sqlite3.connect(str(db_path()))
    dst = sqlite3.connect(str(dest))
    try:
        with dst:
            src.backup(dst)
        result = dst.execute('PRAGMA integrity_check').fetchone()[0]
    finally:
        src.close()
        dst.close()
    if result != 'ok':
        raise RuntimeError(f"Backup copy failed its integrity check: {result}")
    return Path(dest)


def gzipped_database():
    """Returns (gzipped bytes, uncompressed size)."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = copy_database_to(Path(tmp) / 'db.sqlite3')
        raw = copy.read_bytes()
    return gzip.compress(raw, compresslevel=6), len(raw)


RESTORE_NOTES = """WorkBase21 backup
=================
db.sqlite3  - the database (jobs, articles, companies, reviews, user accounts,
              profiles, saved jobs, job alerts...)
media/      - uploaded files (company logos, job images, Z83 forms, article images)

To restore the database: Django admin -> Backups -> "Restore database from a
backup file", and choose this zip (or the db.sqlite3 inside it).
Uploaded files are rarely lost; if needed, Render's daily disk snapshots
(Render -> Disk -> Snapshots) restore them.

This file contains personal information of job seekers. Keep it private.
"""


def write_full_backup_zip(fileobj):
    """Database + every uploaded file, as one zip. Images/PDFs are already
    compressed, so they're stored as-is (fast); the database is compressed."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = copy_database_to(Path(tmp) / 'db.sqlite3')
        with zipfile.ZipFile(fileobj, 'w') as zf:
            zf.write(copy, 'db.sqlite3', compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr('HOW-TO-RESTORE.txt', RESTORE_NOTES, compress_type=zipfile.ZIP_DEFLATED)
            root = media_root()
            if root.exists():
                for p in sorted(root.rglob('*')):
                    if p.is_file():
                        zf.write(p, f"media/{p.relative_to(root).as_posix()}", compress_type=zipfile.ZIP_STORED)


# ---------------------------------------------------------------------------
# Weekly email
# ---------------------------------------------------------------------------

def _state_file():
    return backup_dir() / 'last_emailed.txt'


def last_emailed():
    """Unix time of the last emailed backup, or None."""
    try:
        return float(_state_file().read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def email_is_configured():
    return settings.EMAIL_BACKEND.endswith('smtp.EmailBackend')


def email_database_backup(reason='weekly'):
    data, raw_size = gzipped_database()
    name = f"workbase21-database-{stamp()}.sqlite3.gz"
    when = timezone.localtime().strftime('%d %B %Y, %H:%M')
    msg = EmailMessage(
        subject=f"WorkBase21 {'weekly ' if reason == 'weekly' else ''}backup — {when}",
        body=(
            f"Attached is a backup of the WorkBase21 database, taken {when}.\n\n"
            f"File: {name} ({human_size(len(data))}, {human_size(raw_size)} unpacked)\n"
            "Contains: jobs, articles, companies, reviews, user accounts, profiles,\n"
            "saved jobs and job alerts. (Uploaded images/files are not included —\n"
            "use Admin -> Backups -> Download everything for those.)\n\n"
            "To restore it: Django admin -> Backups -> Restore database from a\n"
            "backup file, and choose this attachment.\n\n"
            "This file contains job seekers' personal information: keep this\n"
            "email private, and delete backups older than about 3 months.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.SITE_EMAIL],
    )
    msg.attach(name, data, 'application/gzip')
    msg.send()
    _state_file().write_text(str(time.time()))
    logger.info("Database backup emailed to %s (%s, reason: %s).", settings.SITE_EMAIL, human_size(len(data)), reason)
    return len(data)


_check_lock = threading.Lock()
_next_check = 0.0


def maybe_send_weekly_backup():
    """Called on normal page requests (see middleware). At most once an
    hour per server process it checks whether a week has passed since the
    last emailed backup; if so it emails one in the background, so the
    visitor's page isn't slowed down. A lock file stops two server
    processes sending at the same time."""
    global _next_check
    if not getattr(settings, 'BACKUP_EMAIL_WEEKLY', True) or not email_is_configured():
        return
    now = time.time()
    with _check_lock:
        if now < _next_check:
            return
        _next_check = now + 3600

    last = last_emailed()
    if last is not None and now - last < WEEK_SECONDS:
        return

    lock = backup_dir() / 'weekly.lock'
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            if now - lock.stat().st_mtime > 3600:  # left behind by a crash
                lock.unlink()
        except FileNotFoundError:
            pass
        return
    os.close(fd)

    def run():
        try:
            email_database_backup('weekly')
        except Exception:
            logger.exception("Weekly backup email failed — will retry within the hour.")
        finally:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass

    threading.Thread(target=run, name='weekly-backup', daemon=True).start()


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

class RestoreError(Exception):
    pass


def _extract_sqlite(uploaded, workdir):
    """Accepts .sqlite3, .sqlite3.gz or the full-backup .zip; returns the
    path of a plain SQLite file in workdir."""
    raw = uploaded.read()
    if raw[:2] == b'\x1f\x8b':
        try:
            raw = gzip.decompress(raw)
        except (OSError, EOFError, zlib.error):
            # EOFError = file cut short (e.g. a download that didn't finish)
            raise RestoreError("That .gz file is damaged or incomplete (maybe the download didn't finish).")
    elif raw[:4] == b'PK\x03\x04':
        import io
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                raw = zf.read('db.sqlite3')
        except KeyError:
            raise RestoreError("That zip doesn't contain a db.sqlite3 — is it a WorkBase21 backup?")
        except (zipfile.BadZipFile, OSError, EOFError, zlib.error):
            raise RestoreError("That zip file is damaged or incomplete (maybe the download didn't finish).")
    if not raw.startswith(b'SQLite format 3\x00'):
        raise RestoreError("That file isn't a database backup. Choose a WorkBase21 backup "
                           "(.sqlite3.gz from the email, or the downloaded .zip).")
    path = Path(workdir) / 'restore.sqlite3'
    path.write_bytes(raw)
    return path


def _validate(path):
    con = sqlite3.connect(str(path))
    try:
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RestoreError("That backup file is damaged (failed its integrity check).")
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for needed in ('django_migrations', 'jobs_job', 'auth_user'):
            if needed not in tables:
                raise RestoreError("That database isn't a WorkBase21 backup.")
        return {
            'jobs': con.execute('SELECT COUNT(*) FROM jobs_job').fetchone()[0],
            'users': con.execute('SELECT COUNT(*) FROM auth_user').fetchone()[0],
        }
    finally:
        con.close()


def restore_database(uploaded):
    """Replace the live database with an uploaded backup.
    1. unpack + integrity-check + confirm it's a WorkBase21 database
    2. save a safety copy of the CURRENT database (so this can be undone)
    3. copy the backup into the live database (SQLite online backup)
    4. run migrations, in case the backup is from an older version
    Returns (safety_copy_path, counts)."""
    from django.core.management import call_command
    from django.db import connections

    with tempfile.TemporaryDirectory() as tmp:
        backup_file = _extract_sqlite(uploaded, tmp)
        counts = _validate(backup_file)

        safety = backup_dir() / f"db-before-restore-{stamp()}.sqlite3"
        copy_database_to(safety)
        olds = sorted(backup_dir().glob('db-before-restore-*.sqlite3'))
        for old in olds[:-KEEP_SAFETY_COPIES]:
            old.unlink()

        connections.close_all()
        src = sqlite3.connect(str(backup_file))
        dst = sqlite3.connect(str(db_path()), timeout=30)
        try:
            with dst:
                src.backup(dst)
        finally:
            src.close()
            dst.close()

    call_command('migrate', interactive=False, verbosity=0)
    logger.warning("Database RESTORED from an uploaded backup (%s jobs, %s users). "
                   "Previous database saved as %s.", counts['jobs'], counts['users'], safety)
    return safety, counts
