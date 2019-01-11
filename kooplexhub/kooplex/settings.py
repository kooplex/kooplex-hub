"""
Django settings for kooplex project.
"""

import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

DEBUG = True

PREFIX = os.getenv('PREFIX', 'kooplex')
DOMAIN = os.getenv('DOMAIN', 'localhost')
LDAP_DOMAIN = os.getenv('LDAP_DOMAIN', 'dc=%s' % ',dc='.join(DOMAIN.split('.')))
LDAP_ADMIN = os.getenv('HUBLDAP_ADMIN', 'admin')

ALLOWED_HOSTS = (
    DOMAIN,
    '%s-nginx' % PREFIX,
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social_django',
    'django_tables2',
    'bootstrap3',
    'hub',
)

AUTHENTICATION_BACKENDS = (
# TODO: a place for google IDP modul,
#    'kooplex.auth.elte.my_ElteOpenID',
    'kooplex.auth.hydra.HydraOpenID',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_ELTEOIDC_KEY = '%s-hub' % PREFIX
SOCIAL_AUTH_ELTEOIDC_SECRET = os.getenv('ELTEOIDC_SECRET')
SOCIAL_AUTH_HYDRAOIDC_KEY = '%s-hub' % PREFIX
SOCIAL_AUTH_HYDRAOIDC_SECRET = os.getenv('ELTEOIDC_SECRET')
SOCIAL_AUTH_USER_FIELDS = [ 'username', 'email' ]
SOCIAL_AUTH_URL_NAMESPACE = 'social'



MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'kooplex.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ os.path.join(BASE_DIR, 'hub/templates') ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'kooplex.lib.context_processors.form_biography',
                'kooplex.lib.context_processors.form_project',
                'kooplex.lib.context_processors.form_container',
                'kooplex.lib.context_processors.user',
                'kooplex.lib.context_processors.table',
            ],
        },
    },
]

WSGI_APPLICATION = 'kooplex.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('HUBDB', 'kooplexhub'),
        'USER': os.getenv('HUBDB_USER', PREFIX),
        'PASSWORD': os.getenv('HUBDB_PW'),
        'HOST': '%s-hub-mysql' % PREFIX,
        'PORT': '3306',
    }
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.getenv('TIME_ZONE', 'Europe/Budapest')

USE_I18N = True

USE_L10N = True

USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = (
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)


LOGIN_REDIRECT_URL = 'indexpage'

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
            'filename': '/tmp/debug.log',
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
    'base_url': 'https://%s' % DOMAIN,
    'mountpoint': {
        'home': '/mnt/.volumes/home',

        'workdir': '/mnt/.volumes/project',
        'git': '/mnt/.volumes/git',
        'share': '/mnt/.volumes/share',
        'report': '/mnt/.volumes/report',

        'course': '/mnt/.volumes/course',
        'usercourse': '/mnt/.volumes/usercourse',
        'assignment': '/mnt/.volumes/assignment',

        'garbage': '/mnt/.volumes/garbage',
    },
    'volume': {
        'home': '%s-home' % PREFIX,
        'course': '%s-course' % PREFIX,
    },
    'ldap': {
        'host': '%s-ldap' % PREFIX,
        'port': os.getenv('HUBLDAP_PORT', 389),
        'bind_dn': 'cn=%s,%s' % (LDAP_ADMIN, LDAP_DOMAIN),
        'base_dn': LDAP_DOMAIN,
        'bind_username': LDAP_ADMIN,
        'bind_password': os.getenv('HUBLDAP_PW'),
    },
    'docker': {
        'pattern_functionalvolumename_filter': r'^vol-([_\w-]+)$',
        'pattern_storagevolumename_filter': r'^stg-([_\w-]+)$',
        'pattern_homevolumename_filter': r'^%s-(home)$' % PREFIX,
        'pattern_sharevolumename_filter': r'^%s-(share)$' % PREFIX,
        'pattern_gitvolumename_filter': r'^%s-(git)$' % PREFIX,
        'pattern_workdirvolumename_filter': r'^%s-(project)$' % PREFIX,
        'pattern_coursevolumename_filter': r'^%s-(course)$' % PREFIX,
        'pattern_usercoursevolumename_filter': r'^%s-(usercourse)$' % PREFIX,
        'pattern_assignmentvolumename_filter': r'^%s-(assignment)$' % PREFIX,
        'pattern_imagename_filter': r'^%s-notebook-(\w+):\w+$' % PREFIX,
        'pattern_imagename': '%s-notebook-%%(imagename)s' % PREFIX,
        'network': '%s-net' % PREFIX,
        'default_image': os.getenv('DEFAULT_IMAGE', '%s-notebook-basic' % PREFIX),
        'mountconf': '/tmp/mount.conf',
    },
    'spawner': {
        'pattern_proxypath': 'notebook/%(containername)s',
        'pattern_courseproject_containername': 'course-%(projectname)s-%(username)s',
        'port': 8000,
    },
    'proxy': {
        'base_url': 'http://%s-proxy:8001' % PREFIX,
        'auth_token': os.getenv('HUBPROXY_PW'),
    },
}

