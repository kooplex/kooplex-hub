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

# Task scheduler message queue 
# set password like
# CELERY_BROKER_URL = "redis://:THEPASSWORD@localhost:6379"
# CELERY_RESULT_BACKEND = "redis://:THEPASSWORD@localhost:6379"
CELERY_BROKER_URL = "redis://localhost:6379"
CELERY_RESULT_BACKEND = "redis://localhost:6379"

# teleport redis
REDIS_PASSWORD=""

KUBERNETES_SERVICE_NAMESPACE=""

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
SESSION_COOKIE_NAME = "kooplexhub_sessionid"
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

PREFIX = os.getenv('PREFIX', 'kooplex')
DOMAIN = os.getenv('DOMAIN', 'localhost')

ALLOWED_HOSTS = [
    DOMAIN,
        ]

SERVERNAME=""
FQDN="https://"+SERVERNAME
FQDN_AUTH=""
URL_MANUAL="https://xwiki.vo.elte.hu/en/kooplex-manual"
manual_mapping = {
    'volume': 'folderstructure#volume',
}


URL_PROFILE = f'https://{FQDN_AUTH}/oauth/profile'
URL_ACCOUNTS_PROFILE = f'https://{FQDN_AUTH}/oauth/accounts/profile'
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
        #python -m pip install -U channels["daphne"]
    'daphne', #web socket framework
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'social_django',
    'django_tables2',
    'django_bootstrap5',
    'hub',
    'container',
    'project',
    'report',
    'education',
    'volume',
    'api',
    'taggit',
]

ASGI_APPLICATION = "kooplexhub.asgi.application"   #websocket

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.TokenAuthenticationMiddleware',
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
            'volume/templates', 
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
                'container.context_processors.warnings',
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
STATIC_ROOT = '/kooplexhub/static'
STATICFILES_DIRS = (
        f'{BASE_DIR}/hub/templates/static',
        f'{BASE_DIR}/project/templates/static',
        f'{BASE_DIR}/container/templates/static',
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
        #'console': {
        #    'level': 'DEBUG',
        #    'class': 'logging.StreamHandler',
        #    'formatter': 'simple'
        #},
        'dfile': {
            'level': 'DEBUG',
            #'class': 'logging.FileHandler',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024,  # 1 mb
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
        'celery': {
            #'handlers': ['celery', 'console'],
            'handlers': ['dfile'],
            'level': 'INFO',
            'propagate': False,
        },
   }
}

KOOPLEX = {
    'fs_backend': 'nfs4',
    'uid_lookup': 'ldap',
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
        'wss_project': 'wss://localhost/hub/ws/project/{userid}/',
        'wss_container': 'wss://localhost/hub/ws/container_environment/{userid}/',
        'wss_monitor': 'wss://localhost/hub/ws/node_monitor/',
        'wss_assignment': 'wss://localhost/hub/ws/education/{userid}/',
        'wss_assignment_summary': 'wss://localhost/hub/ws/assignment_summary/{userid}/',
    },
    'ldap': {
        'host': '',
        'base_dn': 'dc=',
        'bind_dn': 'cn=admin,ou=',
        'bind_password': '',
        'userdn': 'uid={user.username},ou=users,dc=',
        'usersearch': 'ou=users,dc=',
        'manageuser': False,
        'groupdn': 'cn={group.name},ou=groups,dc=',
        'groupsearch': 'ou=groups,dc=',
        'managegroup': True,
        'offset': {
            'project': 300000,
            'course': 200000,
            'volume': 100000,
        },
    },
    'proxy': {
        'url_api': 'http://proxy:8001/api',
        'auth_token': '',
        'url_internal': 'http://{container.label}:{proxy.port}',
        'notebook_path': 'notebook/{container.label}',
        'url_notebook': os.path.join(FQDN,'notebook/{container.label}'),
        'report_path': 'notebook/report/{container.label}',
        'report_path_open': '/notebook/report/{container.label}/',
        'static_report_path': '/report/{report.id}/{report.indexfile}',
        'static_report_path_open': '/report/{report.id}/{report.indexfile}',
        'check_container': 'http://proxy:8001/api/routes/notebook/{container.label}',
    },
    'kubernetes': {
        'namespace': '',
        'jobsnamespace': '',
        'nslcd': { 'mountPath_nslcd': '/etc/mnt' },
        'kubeconfig_job': 'kubejobsconfig', 
        'imagePullPolicy': 'Always',
        'resources': {
            "requests": {
              "cpu": 0.2,
              "nvidia.com/gpu": 0,
              "memory": 0.4
            },
            "limits": {
              "cpu": 5,
              "nvidia.com/gpu": 0,
              "memory": 28
            },
            "maxrequests": {
              "cpu": 4,
              "nvidia.com/gpu": 0,
              "memory": 28,
              "idletime": 48,
            },
        },
        'nodeSelector_k8s': { "kubernetes.io/hostname": "kubelet1-onco2" },
        #'nodeSelector_k8s': { "kubernetes.io/hostname": "veo1" },
        'userdata': {
            'claim': 'userdata',
            #USER
            'claim-home': 'home',
            'claim-garbage': 'garbage',
            'subPath_home': '{user.username}',
            'mountPath_home': '/v/{user.username}',
            'subPath_garbage': '{user.username}',
            'mountPath_garbage': '/v/garbage',
            'claim-scratch': 'scratch',
            'mountPath_scratch': '/v/scratch',
            'subPath_scratch': '{user.username}',
            #PROJECT
            'claim-project': 'project',
            'subPath_project': 'projects/{project.subpath}',
            'mountPath_project': '/v/projects/{project.subpath}',
            'subPath_report_prepare': 'report_prepare/{project.subpath}',
            'mountPath_report_prepare': '/v/report_prepare/{project.subpath}',
            #REPORT
            'claim-report': 'report',
            'subPath_report': '{report.id}',
            'mountPath_report': '/v/reports/{report.project.subpath}-{report.folder}',
            #ATTACHMENT
            'claim-attachment': 'attachments',
            'mountPath_attachment': '/v/attachments/{volume.folder}',
            # VOLUME
            'mountPath_volume': '/v/volumes/{volume.folder}',
            # EDU
            'claim-edu': 'edu',
            'mountPath_course_workdir': '/v/courses/{course.folder}',
            'subPath_course_workdir': 'course_workdir/{course.folder}/{user.username}',
            'mountPath_course_public': '/v/courses/{course.folder}.public',
            'subPath_course_public': 'course/{course.folder}/public',
            'mountPath_course_assignment_prepare': '/v/courses/{course.folder}.assignment_prepare',
            'subPath_course_assignment_prepare': 'course/{course.folder}/assignment_prepare',
            'mountPath_course_assignment': '/v/courses/{course.folder}.assignments',
            'subPath_course_assignment': 'course_assignment/{course.folder}/workdir/{user.username}',
            'subPath_course_assignment_all': 'course_assignment/{course.folder}/workdir',
            'mountPath_course_assignment_correct': '/v/courses/{course.folder}.correct',
            'subPath_course_assignment_correct': 'course_assignment/{course.folder}/correctdir/{user.username}',
            'subPath_course_assignment_correct_all': 'course_assignment/{course.folder}/correctdir',
            # KUBE JOBS
            'mountPath_kubejobsconfig': '/etc/kubejobsconfig',
            'claim-jobtools': 'job-tools',
            'jobtools_ro': False,
        },
        'cache': {
            'claim': 'pvc-cache',
            'subPath_reportprepare': 'report_prepare',
            'mountPath_reportprepare': '/v/report_prepare',
        },
    },
    # Inside docker containers
    'environmental_variables': {
            'LANG' : 'en_US.UTF-8',
            'SSH_AUTH_SOCK': '/tmp/{container.user.username}', #FIXME: move to db
            'SERVERNAME': SERVERNAME,
            'NB_USER' : '{container.user.username}',
            'NB_TOKEN' : '{container.user.profile.token}',            
            'REPORT_USER' : '{container.user.username}',
            'REPORT_FOLDER' : '/srv/report',
            'REPORT_FILE' : 'main.py',
            # FIXME could be cleaner
            # These needs to be the same as in proxy
            'NB_URL' : 'notebook/{container.label}', # same es KOOPLEX['proxy']['url_notebook']
            'NB_PORT' : '8000', # same es proxy.port
            'REPORT_URL' : 'notebook/report/{container.label}/', # same es KOOPLEX['proxy']['report_path']
            'REPORT_PORT' : '9000', # same es proxy.port
            },
}

