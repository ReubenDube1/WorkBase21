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

    # Third-party apps
    'ckeditor',
    'ckeditor_uploader',

    # Local apps
    'jobs',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'workbase21.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# On Render we store the SQLite file on a Persistent Disk so it survives redeploys.

if os.environ.get('RENDER'):
    # Persistent disk path (must match the Mount Path you set in Render)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/var/data/db.sqlite3',
        }
    }
else:
    # Local development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


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

if os.environ.get('RENDER'):
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
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Site info used in templates (SEO meta tags, footer, etc.)
SITE_NAME = 'WorkBase21'
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'workbase21.co.za')
SITE_DESCRIPTION = (
    'WorkBase21 connects South African job seekers with jobs, internships, '
    'learnerships, in-service trainee positions and bursaries.'
)


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
    },
}