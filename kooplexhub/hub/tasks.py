from celery import shared_task
#import logging
import time

from django.contrib.auth.models import User

from kooplexhub.settings import KOOPLEX
from hub.lib import archivedir, extracttarbal, grantaccess_user
from hub.lib import filename, dirname
from hub.lib import mkdir, archivedir, rmdir

#logger = logging.getLogger(__name__)

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

@shared_task()
def create_home(user_id):
    user = User.objects.get(id = user_id)
    userdirs = [ dirname.userhome, dirname.usergarbage ]
    if KOOPLEX.get('mountpoint_hub', {}).get('scratch') is not None:
        userdirs.append(dirname.userscratch)
    for userdir in userdirs:
        folder = userdir(user)
        mkdir(folder)
        grantaccess_user(user, folder, readonly = False, recursive = True)


@shared_task()
def garbage_home(user_id):
    user = User.objects.get(id = user_id)
    rmdir( dirname.usergarbage(user) )
    if KOOPLEX.get('mountpoint_hub', {}).get('scratch') is not None:
        rmdir( dirname.userscratch(user) )
    if KOOPLEX.get('archive_home'):
        archivedir( dirname.userhome(user), filename.userhome_garbage(user), remove = True)
    else:
        rmdir( dirname.userhome(user) )
