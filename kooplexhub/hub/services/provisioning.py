from django.utils import timezone

from ..models import Profile
from .directory import (
    DirectoryService,
)
from .storage import (
    ensure_user_storage,
)
from .users_directory import (
    ensure_user_directory_identity,
)
from .kubernetes_identity import (
    ensure_user_kubernetes_identity,
)


MAX_ERROR_LENGTH = 4000


def _operation_error(error):
    return (
        f"{error.__class__.__name__}: {error}"
    )[:MAX_ERROR_LENGTH]


def provision_user(
    *,
    profile_id,
):
    profile = (
        Profile.objects
        .select_related("user")
        .get(pk=profile_id)
    )

    if (
        profile.state
        != Profile.State.PREPARING
    ):
        return False

    try:
        DirectoryService().ensure_structure()

        ensure_user_directory_identity(
            profile=profile,
        )

        ensure_user_storage(
            profile=profile,
        )

        ensure_user_kubernetes_identity(
            profile=profile,
        )

    except Exception as error:
        updated = (
            Profile.objects.filter(
                pk=profile_id,
                state=Profile.State.PREPARING,
            ).update(
                state=(
                    Profile.State.PROVISION_FAILED
                ),
                last_operation_error=(
                    _operation_error(error)
                ),
                last_operation_failed_at=(
                    timezone.now()
                ),
            )
        )
    
        logger.exception(
            "User provisioning failed "
            "profile=%s state_updated=%s",
            profile_id,
            updated == 1,
        )

        raise

    Profile.objects.filter(
        pk=profile_id,
        state=Profile.State.PREPARING,
    ).update(
        state=Profile.State.READY,
        last_operation_error="",
        last_operation_failed_at=None,
        provisioned_at=timezone.now(),
    )

    return True


