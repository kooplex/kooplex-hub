import logging
import pwgen
import json
import datetime

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete, post_delete
from django_celery_beat.models import ClockedSchedule, PeriodicTask

from ..models import Profile

logger = logging.getLogger(__name__)

code = lambda x: json.dumps([ i.id for i in x ])


@receiver(post_save, sender = User)
def user_creation(sender, instance, created, **kwargs):
    if instance.is_superuser:
        logger.debug("Admin user %s" % instance)
        return
    if created or not hasattr(instance, 'profile'):
        logger.info("New user %s" % instance)
        token = pwgen.pwgen(64)
        Profile.objects.create(user = instance, token = token)
        schedule_now = ClockedSchedule.objects.create(clocked_time = datetime.datetime.now())
        PeriodicTask.objects.create(
            name = f"create_home_{instance.username}",
            task = "hub.tasks.create_home",
            clocked = schedule_now,
            one_off = True,
            kwargs = json.dumps({
                'user_id': instance.id,
            })
        )
    

@receiver(pre_delete, sender = User)
def garbage_user_home(sender, instance, **kwargs):
    schedule_now = ClockedSchedule.objects.create(clocked_time = datetime.datetime.now())
    PeriodicTask.objects.create(
        name = f"garbage_home_{instance.username}",
        task = "hub.tasks.garbage_home",
        clocked = schedule_now,
        one_off = True,
        kwargs = json.dumps({
            'user_id': instance.id,
        })
    )


