"""Gunicorn settings — loaded automatically, because gunicorn reads
./gunicorn.conf.py from the folder it starts in. Nothing to change on
Render; the Start Command stays the same.

Why: by default gunicorn handles ONE request at a time per process and
kills any request that takes longer than 30 seconds. A large download
(Admin -> Backups -> Download everything, ~70 MB) on a slow connection
would be cut off, and would block every other visitor while it ran.
Threads let one process serve several visitors at once (and long
downloads no longer trip the 30-second limit), without using noticeably
more memory.
"""
import os

workers = int(os.environ.get('WEB_CONCURRENCY', 1))
worker_class = 'gthread'
threads = int(os.environ.get('GUNICORN_THREADS', 4))
timeout = 120
