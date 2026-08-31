import logging

from django_huey import db_task
from huey.exceptions import RetryTask

from .services.lifecycle import (
    mark_project_delete_failed,
    progress_project_delete,
)
from .services.live import (
    broadcast_project_changed,
    project_member_user_ids,
)
from .models import Project


logger = logging.getLogger(__name__)


@db_task(queue="project")
def continue_project_delete(
    project_id,
    archive=True,
):
    try:
        complete = progress_project_delete(
            project_id=project_id,
            archive=archive,
        )

    except Exception as error:
        mark_project_delete_failed(
            project_id=project_id,
            error=error,
        )

        project = (
            Project.objects
            .filter(pk=project_id)
            .first()
        )

        if project is not None:
            user_ids = (
                project_member_user_ids(
                    project
                )
            )

            broadcast_project_changed(
                project_id=project_id,
                user_ids=user_ids,
                reason=(
                    "project.deletion.failed"
                ),
            )

        logger.exception(
            "Project deletion failed "
            "project=%s",
            project_id,
        )

        raise

    if not complete:
        raise RetryTask(delay=2)


