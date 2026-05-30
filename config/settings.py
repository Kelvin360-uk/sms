"""
Django settings for School Management System.
Single-server MVP configuration.
"""
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-CHANGE-ME-IN-PRODUCTION')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0,192.168.79.128,192.168.79.1').split(',')

# ----------------------------------------------------------------------------
# Applications
# ----------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Local apps
    'apps.users',
    'apps.students',
    'apps.teachers',
    'apps.classes',
    'apps.exams',
    'apps.payments',
    'apps.audit',
    'apps.notifications',
    'apps.messaging',
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
    # Custom middleware
    'middleware.session_timeout.SessionTimeoutMiddleware',
    'middleware.audit_context.AuditContextMiddleware',
    
]

ROOT_URLCONF = 'config.urls'

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
                'apps.notifications.context_processors.unread_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ----------------------------------------------------------------------------
# Database - PostgreSQL
# ----------------------------------------------------------------------------

import dj_database_url

DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=60)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='sms_db'),
            'USER': config('DB_USER', default='sms_user'),
            'PASSWORD': config('DB_PASSWORD', default='educational123'),
            'HOST': config('DB_HOST', default='192.168.79.128'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }

# ----------------------------------------------------------------------------
# Custom User Model
# ----------------------------------------------------------------------------
AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# ----------------------------------------------------------------------------
# Internationalization
# ----------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ----------------------------------------------------------------------------
# Static & Media
# ----------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ----------------------------------------------------------------------------
# Security
# ----------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 4  # 4 hours global hard limit
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
X_FRAME_OPTIONS = 'DENY'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ----------------------------------------------------------------------------
# Session timeout (custom)
# ----------------------------------------------------------------------------
TEACHER_SESSION_MINUTES = config('TEACHER_SESSION_MINUTES', default=120, cast=int)
ADMIN_SESSION_MINUTES = config('ADMIN_SESSION_MINUTES', default=240, cast=int)

# ----------------------------------------------------------------------------
# Cloud sync
# ----------------------------------------------------------------------------
CLOUD_SYNC_ENABLED = config('CLOUD_SYNC_ENABLED', default=False, cast=bool)
CLOUD_SYNC_URL = config('CLOUD_SYNC_URL', default='')
CLOUD_SYNC_API_KEY = config('CLOUD_SYNC_API_KEY', default='')

# ----------------------------------------------------------------------------
# School info
# ----------------------------------------------------------------------------
SCHOOL_NAME = config('SCHOOL_NAME', default='Your School')
ACADEMIC_YEAR = config('ACADEMIC_YEAR', default='2025-2026')

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'sms': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
