"""
Django settings for kooplex project.
"""

import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

SESSION_COOKIE_NAME = "kooplexhub_sessionid"


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
SOCIAL_AUTH_HYDRAOIDC_SECRET = os.getenv('HYDRA_OIDC_SECRET_HUB')
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
                'kooplex.lib.context_processors.manual',
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
LOGOUT_URL = 'https://%s.elte.hu/consent/auth/logout' % PREFIX

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

DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap4.html"


KOOPLEX = {
    'base_url': 'https://%s' % DOMAIN,
    'url_manual': 'https://kooplex-test.elte.hu/manual',
    'hydra_oidc_endpoint':  'https://%s/hydra' % DOMAIN,
    'mountpoint': {
        'home': '/mnt/.volumes/home',

        'report': '/mnt/.volumes/report',

        'workdir': '/mnt/.volumes/workdir',
        'git': '/mnt/.volumes/git',
        'filesync': '/mnt/.volumes/cache-seafile',
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
    'volumepattern': {
        'home': r'^%s-(home)$' % PREFIX,
        'garbage': r'^%s-(garbage)$' % PREFIX,
        'report': r'^%s-(report)$' % PREFIX,
        'share': r'^%s-(share)$' % PREFIX,
        'git': r'^%s-(git)$' % PREFIX,
        'filesync': r'^%s-(cache-seafile)$' % PREFIX,
        'workdir': r'^%s-(workdir)$' % PREFIX,
        'functional': r'^vol-([_\w-]+)$',
        'storage': r'^stg-([_\w-]+)$',
        'course': r'^%s-(course)$' % PREFIX,
        'usercourse': r'^%s-(usercourse)$' % PREFIX,
        'assignment': r'^%s-(assignment)$' % PREFIX,
    },
    'docker': {
        'pattern_imagename_filter': r'^%s-notebook-(\w+):\w+$' % PREFIX,
        'pattern_imagename': '%s-notebook-%%(imagename)s' % PREFIX,
        'network': '%s-net' % PREFIX,
        'default_image': os.getenv('DEFAULT_IMAGE', '%s-notebook-basic' % PREFIX),
        'volume_dir': os.getenv('DOCKER_VOLUME_DIR', None),
        'mountconf': '/tmp/mount.conf',
        'gitcommandconf': '/tmp/gitcommand.conf',
        'impersonator': '%s-impersonator' % PREFIX, #FIXME: is it still used?
    },
    'impersonator': {
        'base_url': 'http://%s-impersonator:5000' % PREFIX,
        'username': 'hub',
        'password': 'blabla',
        'seafile_api': 'http://%s-seafile-pw:5000' % PREFIX,
    },
    'spawner': {
        'pattern_proxypath': 'notebook/%(containername)s',
        'pattern_proxypath_test': 'notebook/%(containername)s/report',
        'pattern_courseproject_containername': 'course-%(projectname)s-%(username)s',
        'port': 8000,
        'port_test': 9000,
    },
    'proxy': {
        'base_url': 'http://%s-proxy:8001' % PREFIX,
        'auth_token': os.getenv('HUBPROXY_PW'),
    },
    'reportserver': {
        'base_url': 'http://%s-report-nginx' % PREFIX,
    }
}

