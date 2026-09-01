import logging

from django_huey import db_task

from .services.provisioning import (
    provision_user,
)

logger = logging.getLogger(__name__)


@db_task(queue="hub")
def provision_user_task(
    profile_id,
):
    logger.info(
        "Provisioning user profile=%s",
        profile_id,
    )

    return provision_user(
        profile_id=profile_id,
    )


@db_task(queue="hub")
def continue_user_delete(
    user_id,
):
    logger.info(
        "Deleting user profile=%s",
        profile_id,
    )

    try:
        complete = progress_user_delete(
            user_id=user_id
        )

    except Exception as error:
        mark_user_delete_failed(
            user_id=user_id,
            error=error,
        )
        raise

    if not complete:
        raise RetryTask(delay=2)


