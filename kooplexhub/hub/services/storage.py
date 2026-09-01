import os

from ..conf import HUB_SETTINGS
from ..filesystem import (
    user_home,
    user_garbage,
    user_scratch,
    user_home_archive,
)
from ..lib.filesystem import (
    _mkdir,
    _rmdir,
    _archivedir,
    _grantaccess,
)


def ensure_user_storage(
    *,
    profile,
):
    user = profile.user

    paths = [
        user_home(user),
    ]

    garbage = user_garbage(user)

    if garbage is not None:
        paths.append(garbage)

    scratch = user_scratch(user)

    if (
        scratch is not None
        and profile.has_scratch
    ):
        paths.append(scratch)

    for path in paths:
        _mkdir(path)

        _grantaccess(
            user,
            path,
            readonly=False,
            recursive=True,
        )

    return tuple(paths)


def remove_user_storage(
    *,
    user,
):
    home = user_home(user)

    if (
        HUB_SETTINGS.archive_home
        and os.path.isdir(home)
    ):
        target = user_home_archive(user)

        if target is None:
            raise RuntimeError(
                "archive_home=True but no "
                "garbage mount is configured."
            )

        _archivedir(
            home,
            target,
            remove=True,
        )

    else:
        _rmdir(home)

    scratch = user_scratch(user)

    if scratch is not None:
        _rmdir(scratch)

    garbage = user_garbage(user)

    if garbage is not None:
        _rmdir(garbage)



