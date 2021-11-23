"""
Django settings for kooplexhub project.

Generated by 'django-admin startproject' using Django 3.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
SESSION_COOKIE_NAME = "kooplexhub_sessionid"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

PREFIX = os.getenv('PREFIX', 'kooplex')
DOMAIN = os.getenv('DOMAIN', 'localhost')

ALLOWED_HOSTS = [
    DOMAIN,
        ]


LOGIN_URL = ''
LOGOUT_URL = ''
SOCIAL_AUTH_KOOPLEX_KEY = ''
SOCIAL_AUTH_KOOPLEX_SECRET = ''
SOCIAL_AUTH_USER_FIELDS = [ 'username', 'email' ]
SOCIAL_AUTH_URL_NAMESPACE = 'social'
KOOPLEX_OID_AUTHORIZATION_URL = ''
KOOPLEX_OID_ACCESS_TOKEN_URL = ''
LOGIN_REDIRECT_URL = 'indexpage'
LOGOUT_REDIRECT_URL = 'indexpage'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social_django',
    'django_tables2',
    'django_bootstrap5',
    'hub',
    'container',
    'project',
    'education',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kooplexhub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ 
            'hub/templates', 
            'container/templates', 
            'project/templates', 
            'education/templates', 
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'hub.context_processors.next_page',
                'hub.context_processors.user',
                'hub.context_processors.notes',
                'hub.context_processors.installed_apps',
                'container.context_processors.form_container',
                'container.context_processors.warnings',
                'container.context_processors.form_attachment',
                'project.context_processors.form_project',
                'project.context_processors.warnings',
                'education.context_processors.assignment_warnings',
                'education.context_processors.warnings',
                'education.context_processors.group_warnings',
                'education.context_processors.active_tab',
            ],
        },
    },
]

WSGI_APPLICATION = 'kooplexhub.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('HUBDB', 'kooplexhub'),
        'USER': os.getenv('HUBDB_USER', PREFIX),
        'PASSWORD': os.getenv('HUBDB_PW'),
        'HOST': os.getenv('HUBDB_HOSTNAME', '%s-hub-mysql' % PREFIX),
        'PORT': '3306',
    }
}

AUTHENTICATION_BACKENDS = (
    'hub.k8plex-oauth.KooplexOpenID',
    'django.contrib.auth.backends.ModelBackend',
)

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.getenv('TIME_ZONE', 'Europe/Budapest')

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
        f'{BASE_DIR}/hub/templates/static',
)

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
       'verbose': {
            'format': '%(levelname)s[%(asctime)s]\t%(module)s:%(funcName)s:%(lineno)s -- %(message)s'
        },
    },
    'handlers': {
        'dfile': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/hub/hub.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'handlers': ['dfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
   }
}

KOOPLEX = {
    'fs_backend': 'nfs4',
    'mountpoint_hub': {
        'home': '/mnt/home',
        'garbage': '/mnt/garbage',
        'scratch': None,

        'project': '/mnt/project',
        
        'report': '/mnt/report',
        'report_prepare': '/mnt/report_prepare',

        'course': '/mnt/course',
        'course_workdir': '/mnt/course_workdir',
        'course_assignment': '/mnt/course_assignment',

    },
    'hub': {
        'adminemail': '',
        'smtpserver': '',
    },
    'proxy': {
        'url_api': 'http://proxy:8001/api',
        'auth_token': '',
        'url_internal': 'http://{container.label}:{proxy.port}',
        'url_public': 'https://%s/{proxy.path_open}' % DOMAIN,
        'path': 'notebook/{container.name}',
    },
    'kubernetes': {
        'namespace': '',
        'imagePullPolicy': 'Always',
        'nslcd': {
            'mountPath_nslcd': '/etc/mnt'
            },
        'nodeSelector_k8s': { "kubernetes.io/hostname": "" },
#        'nodeSelector_k8s': { "nodetype": "worker" },
        'userdata': {
            'claim': 'pvc-userdata',
            # USERDATA
            'claim-home': 'pvc-home',
            'claim-garbage': 'pvc-garbage',
            'subPath_home': '{user.username}',
            'mountPath_home': '/v/{user.username}',
            'subPath_garbage': '{user.username}',
            'mountPath_garbage': '/v/garbage',
            'claim-scratch': 'pvc-scratch',
            'mountPath_scratch': '/v/scratch/',
            'subPath_scratch': '{user.username}',
            # PROJECT
            'claim-project': 'pvc-project',
            'claim-report': 'pvc-report',
            'mountPath_project': '/v/projects/{project.uniquename}',
            'subPath_project': 'projects',
            'mountPath_report_prepare': '/v/report_prepare/{project.uniquename}',
            'subPath_report_prepare': 'report_prepare/{project.uniquename}',
            'mountPath_report': '/v/reports/{report.uniquename}',
            'subPath_report': 'reports',
            # EDU
            'claim-edu': 'pvc-edu',
            'mountPath_course_workdir': '/v/courses/{course.folder}',
            'subPath_course_workdir': 'course_workdir/{course.folder}/{user.username}',
            'mountPath_course_public': '/v/courses/{course.folder}.public',
            'subPath_course_public': 'courses/{course.folder}/public',
            'mountPath_course_assignment_prepare': '/v/courses/{course.folder}.assignment_prepare',
            'subPath_course_assignment_prepare': 'courses/{course.folder}/assignment_prepare',
            'mountPath_course_assignment': '/v/courses/{course.folder}.assignments',
            'subPath_course_assignment': 'course_assignments/{course.folder}/workdir/{user.username}',
            'subPath_course_assignment_all': 'course_assignments/{course.folder}/workdir',
            'mountPath_course_assignment_correct': '/v/courses/{course.folder}.correct',
            'subPath_course_assignment_correct': 'course_assignments/{course.folder}/correctdir/{user.username}',
            'subPath_course_assignment_correct_all': 'course_assignments/{course.folder}/correctdir',
        },
        'cache': {
            'claim': 'pvc-cache',
            'subPath_reportprepare': 'report_prepare',
            'mountPath_reportprepare': '/v/report_prepare',
        },
    },
}

