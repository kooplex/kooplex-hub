import logging
import time

from channels.layers import get_channel_layer
from django_huey import task
from asgiref.sync import async_to_sync

from django.contrib.auth.models import User

from kooplexhub.settings import KOOPLEX
from hub.lib import archivedir, extracttarbal, grantaccess_user
from hub.lib import filename, dirname
from hub.lib import mkdir, archivedir, rmdir

logger = logging.getLogger(__name__)

@task(queue = 'hub')
def delete_folder(folder):
    logging.warning(f'Deleting folder {folder}')
    rmdir( folder )


@task(queue = 'hub')
def garbage_home(user_id):
    user = User.objects.get(id = user_id)
    rmdir( dirname.usergarbage(user) )
    if KOOPLEX.get('mountpoint_hub', {}).get('scratch') is not None:
        rmdir( dirname.userscratch(user) )
    if KOOPLEX.get('archive_home'):
        archivedir( dirname.userhome(user), filename.userhome_garbage(user), remove = True)
    else:
        rmdir( dirname.userhome(user) )


@task(queue = 'hub')
def archive(folder, tarbal, remove=False):
    from .lib import archivedir
    archivedir(folder, tarbal, remove = remove_folder)
