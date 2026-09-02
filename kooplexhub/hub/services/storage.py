import os
from dataclasses import dataclass

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
    user_has_folder_access,
)


@dataclass(
    frozen=True,
    slots=True,
)
class UserStoragePathStatus:
    name: str
    path: str

    exists: bool
    is_directory: bool
    access_ready: bool

    @property
    def ready(self):
        return (
            self.exists
            and self.is_directory
            and self.access_ready
        )


@dataclass(
    frozen=True,
    slots=True,
)
class UserStorageStatus:
    paths: tuple[
        UserStoragePathStatus,
        ...
    ]

    @property
    def ready(self):
        return all(
            item.ready
            for item in self.paths
        )

    @property
    def problems(self):
        problems = []

        for item in self.paths:
            if not item.exists:
                problems.append(
                    f"{item.name}: missing "
                    f"{item.path}"
                )

            elif not item.is_directory:
                problems.append(
                    f"{item.name}: not a "
                    f"directory: {item.path}"
                )

            elif not item.access_ready:
                problems.append(
                    f"{item.name}: user ACL "
                    "is missing or incomplete"
                )

        return tuple(problems)


def _inspect_storage_path(
    *,
    name,
    path,
    user,
):
    exists = os.path.exists(path)
    is_directory = os.path.isdir(path)

    access_ready = (
        is_directory
        and user_has_folder_access(
            user,
            path,
            writable=True,
        )
    )

    return UserStoragePathStatus(
        name=name,
        path=path,
        exists=exists,
        is_directory=is_directory,
        access_ready=access_ready,
    )


def _required_user_storage(
    *,
    profile,
):
    user = profile.user

    paths = [
        (
            "home",
            user_home(user),
        ),
    ]

    garbage = user_garbage(user)

    if garbage is not None:
        paths.append(
            (
                "garbage",
                garbage,
            )
        )

    scratch = user_scratch(user)

    if (
        scratch is not None
        and profile.has_scratch
    ):
        paths.append(
            (
                "scratch",
                scratch,
            )
        )

    return tuple(paths)


def inspect_user_storage(
    *,
    profile,
):
    user = profile.user

    statuses = [
        _inspect_storage_path(
            name=name,
            path=path,
            user=user,
        )

        for name, path in (
            _required_user_storage(
                profile=profile
            )
        )
    ]

    return UserStorageStatus(
        paths=tuple(statuses),
    )


def ensure_user_storage(
    *,
    profile,
):
    user = profile.user

    for _name, path in (
        _required_user_storage(
            profile=profile
        )
    ):
        _mkdir(path)

        _grantaccess(
            user,
            path,
            readonly=False,
            recursive=True,
        )

    return inspect_user_storage(
        profile=profile
    )


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
        #TODO: consider to move user's garbage in final garbage naxt to user's home archoved
        _rmdir(garbage)



