import logging

import pwgen
from django.utils import timezone

from django.db import transaction
from django.contrib.auth import (
    get_user_model,
)

from ..models import Profile


logger = logging.getLogger(__name__)


@transaction.atomic
def register_user(
    *,
    user,
):
    from hub.tasks import provision_user_task

    if user.is_superuser:
        return None

    profile = (
        Profile.objects
        .select_for_update()
        .filter(user=user)
        .first()
    )

    if profile is not None:
        return profile

    profile = Profile.objects.create(
        user=user,
        token=pwgen.pwgen(64),
        state=Profile.State.PREPARING,
    )

    profile_id = profile.pk

    def enqueue():
        logger.debug(
            "Enqueueing user provisioning "
            "profile=%s user=%s",
            profile_id,
            user.username,
        )

        provision_user_task(
            profile_id
        )

    transaction.on_commit(enqueue)
    
    return profile


def create_user(
    *,
    username,
    email="",
    first_name="",
    last_name="",
):
    User = get_user_model()

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        register_user(
            user=user
        )

    return user


def request_user_delete(
    *,
    user,
):
    from hub.tasks import (
        continue_user_delete,
    )

    with transaction.atomic():
        profile = (
            Profile.objects
            .select_for_update()
            .get(user=user)
        )

        if profile.state == Profile.State.DELETING:
            return False

        profile.state = Profile.State.DELETING
        profile.deletion_requested_at = (
            timezone.now()
        )
        profile.last_operation_error = ""
        profile.last_operation_failed_at = None

        profile.save(
            update_fields=[
                "state",
                "deletion_requested_at",
                "last_operation_error",
                "last_operation_failed_at",
            ]
        )

        User.objects.filter(
            pk=user.pk
        ).update(
            is_active=False
        )

        user_id = user.pk

        transaction.on_commit(
            lambda: continue_user_delete(
                user_id
            )
        )

    return True



