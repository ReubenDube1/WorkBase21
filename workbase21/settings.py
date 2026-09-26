"""
Django settings for WorkBase21 project.
A premium job portal for Jobs, Internships, Learnerships,
In-Service Trainee positions and Bursaries.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# In production, set this via an environment variable instead.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-CHANGE-THIS-KEY-BEFORE-DEPLOYING-workbase21'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS',
    'localhost,127.0.0.1,workbase21.co.za,www.workbase21.co.za'
).split(',')

# Add your Render URL here once deployed, e.g. 'workbase21.onrender.com'
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Required so Django trusts POST requests (e.g. the contact form) coming
# in over HTTPS on the custom domain — without this you'll get a
# "CSRF verification failed" error once workbase21.co.za is live.
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'https://workbase21.co.za,https://www.workbase21.co.za'
).split(',')

# Render sits behind a proxy that terminates HTTPS, so Django needs this
# to know a request was actually made over HTTPS (affects request.is_secure(),
# the share-link URLs on the job detail page, and CSRF checks).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # Third-party apps
    'ckeditor',
    'ckeditor_uploader',

    # Local apps
    'jobs',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Logs page visits for the admin's Site Analytics dashboard. Must
    # come after SessionMiddleware (needs request.session).
    'jobs.middleware.VisitTrackingMiddleware',

    # Emails a database backup to SITE_EMAIL once a week (jobs/backup.py).
    'jobs.middleware.WeeklyBackupMiddleware',
]

ROOT_URLCONF = 'workbase21.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Custom context processor so job type nav links are
                # available on every single page (used in base.html)
                'jobs.context_processors.job_types',
                'jobs.context_processors.filter_choices',
                'accounts.context_processors.job_alert_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'workbase21.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# Only use the persistent disk when it is actually available (runtime).
# During the build stage the disk is not mounted yet.

if os.environ.get('RENDER') and os.path.exists('/var/data'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/var/data/db.sqlite3',
        }
    }
else:
    # Local development + Render build stage
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Tests (python manage.py test) use their own temporary database file,
# created and deleted automatically — never the real database.
DATABASES['default']['TEST'] = {'NAME': str(BASE_DIR / 'test_db.sqlite3')}

# Default test run skips the slower real-browser "phone checks";
# run those with:  python manage.py phone_check
TEST_RUNNER = 'workbase21.test_runner.WorkBaseTestRunner'


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Job-seeker accounts (Phase 3) — where to send people for/after login.
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'profile'
LOGOUT_REDIRECT_URL = 'welcome'


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (job/company logo uploads, CKEditor uploads)
MEDIA_URL = '/media/'

if os.environ.get('RENDER') and os.path.exists('/var/data'):
    MEDIA_ROOT = '/var/data/media'
else:
    MEDIA_ROOT = BASE_DIR / 'media'


# CKEditor configuration
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList'],
            ['Link', 'Unlink'],
            ['Format'],
            ['RemoveFormat', 'Source'],
        ],
        'height': 300,
        'width': '100%',
    },
    # Used for TrendingTopic article body fields — adds image insertion
    # so pictures can be dropped in and positioned anywhere in the text,
    # not just as a single banner image.
    'article': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList'],
            ['Blockquote'],
            ['Link', 'Unlink'],
            ['Image'],
            ['Format'],
            ['RemoveFormat', 'Source'],
        ],
        'height': 350,
        'width': '100%',
        'filebrowserUploadMethod': 'form',
    },
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Site info used in templates (SEO meta tags, footer, etc.)
SITE_NAME = 'WorkBase21'
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'workbase21.co.za')
SITE_EMAIL = os.environ.get('SITE_EMAIL', 'contact.workbase21@gmail.com')
SITE_DESCRIPTION = (
    'WorkBase21 connects South African job seekers with jobs, internships, '
    'learnerships and bursaries.'
)


# ---------------------------------------------------------------------------
# Email (free): sent through a Gmail account using a Google "App password".
# Used for password reset emails and Contact-page messages.
#
# On Render, set these environment variables:
#   EMAIL_HOST_USER      = the Gmail address, e.g. contact.workbase21@gmail.com
#   EMAIL_HOST_PASSWORD  = the 16-character App password (NOT the normal
#                          Gmail password)
# If they're missing (e.g. on your laptop), emails are printed in the
# terminal instead of being sent — handy for testing, nothing breaks.
# ---------------------------------------------------------------------------
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').replace(' ', '')
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_TIMEOUT = 20
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = f"WorkBase21 <{EMAIL_HOST_USER or SITE_EMAIL}>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Password reset links stay valid for 1 hour.
PASSWORD_RESET_TIMEOUT = 60 * 60


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Our own apps: password reset / contact email diagnostics show up
        # in the Render logs.
        'accounts': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'jobs': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}