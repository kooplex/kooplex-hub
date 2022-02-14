import logging
import threading
import json

from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.contrib.auth.models import User

from kooplexhub.settings import KOOPLEX
from kooplexhub.lib import now

from ..lib import mkdir, archivedir, rmdir, extracttarbal
from ..lib import grantaccess_user, grantaccess_group
from ..lib import revokeaccess_user, revokeaccess_group
from ..models import FilesystemTask, Group

logger = logging.getLogger(__name__)

thread_id = 0
semaphore = threading.Semaphore(value = KOOPLEX.get('parallel_fs_tasks', 2))

decode = lambda x: json.loads(x) if x else []

def worker(fstask: FilesystemTask):
    error = None
    try:
        logger.info('starting {}'.format(fstask))
        if fstask.task == FilesystemTask.TSK_CREATE:
            mkdir(fstask.folder)
        elif fstask.task == FilesystemTask.TSK_GRANT:
            if fstask.create_folder:
                mkdir(fstask.folder)
            for u in decode(fstask.users_ro):
                grantaccess_user(User.objects.get(id = u), fstask.folder, acl = 'rXtcy')
            for u in decode(fstask.users_rw):
                grantaccess_user(User.objects.get(id = u), fstask.folder)
            for g in decode(fstask.groups_ro):
                with transaction.atomic():
                    go = Group.objects.select_for_update().get(id = g)
                grantaccess_group(go, fstask.folder, acl = 'rXtcy')
            for g in decode(fstask.groups_rw):
                with transaction.atomic():
                    go = Group.objects.select_for_update().get(id = g)
                grantaccess_group(go, fstask.folder)
        elif fstask.task == FilesystemTask.TSK_TAR:
            archivedir(fstask.folder, fstask.tarbal, remove = fstask.remove_folder)
        elif fstask.task == FilesystemTask.TSK_REMOVE:
            rmdir(fstask.folder)
        elif fstask.task == FilesystemTask.TSK_REVOKE:
            for u in decode(fstask.users_rw):
                revokeaccess_user(User.objects.get(id = u), fstask.folder)
            #for g in decode(fstask.group_rw):
            #    revokeaccess_group(Group.objects.get(id = g), fstask.folder)
        elif fstask.task == FilesystemTask.TSK_UNTAR:
            extracttarbal(fstask.tarbal, fstask.folder)
            for u in decode(fstask.users_ro):
                grantaccess_user(User.objects.get(id = u), fstask.folder, acl = 'rXtcy')
            for u in decode(fstask.users_rw):
                grantaccess_user(User.objects.get(id = u), fstask.folder)
        else:
            raise NotImplementedError(FilesystemTask.TSK_LOOKUP[fstask.task])
    except Exception as e:
        error = e
        logger.error('oppsed with {} -- {}'.format(fstask, e))
    finally:
        logger.info('stopped {}'.format(fstask))
        if error is None and not KOOPLEX.get('keep_fstask_in_db', True):
            fstask.delete()
            return
        elif error:
            fstask.error = str(error)
        fstask.stop_at = now()
        fstask.save()


@receiver(pre_save, sender = FilesystemTask)
def sanity_check(sender, instance, **kwargs):
    logger.critical('not implemented')
#    from kooplexhub.lib import provision_home, provision_scratch
#    #FIXME: exclude admins!
#    if created or not hasattr(instance, 'profile'):
#        logger.info("New user %s" % instance)
#        token = pwgen.pwgen(64)
#        Profile.objects.create(user = instance, token = token)
#    provision_home(instance)
#    provision_scratch(instance)




@receiver(post_save, sender = FilesystemTask)
def process(sender, instance, created, **kwargs):
    global thread_id, semaphore
    if instance.launched_at is None:
        with semaphore:
            thread_id += 1
            instance.launched_at = now()
            p = threading.Thread(target = worker, name = f"FilesystemTask-{thread_id}", args = (instance, ))
            p.start()



#@receiver(pre_delete, sender = User)
#def garbage_user_home(sender, instance, **kwargs):
#    from kooplex.lib.filesystem import garbagedir_home
#    garbagedir_home(instance)


