"""Shared project/course environment compatibility presentation.

Only explicit preferred volumes are required; additional container mounts are OK.
"""
from dataclasses import dataclass

from volume.conf import VOLUME_SETTINGS


@dataclass(frozen=True)
class EnvironmentCompatibility:
    container: object
    compatible: bool
    tooltip: str


def check_environments(containers, *, preferred_image_id, preferred_volumes):
    """Return comparison rows for a collection of existing containers.

    preferred_volumes is an iterable of Volume objects, not just IDs, so the
    tooltip can show a user-readable configured mount location.
    """
    preferred = {volume.pk: volume for volume in preferred_volumes}
    results = []
    for container in containers:
        current_ids = set(container.volumebindings.values_list("volume_id", flat=True))
        missing = [volume for id_, volume in preferred.items() if id_ not in current_ids]
        reasons = []
        if container.image_id != preferred_image_id:
            reasons.append("Image differs from preferred image.")
        if missing:
            reasons.append("Missing preferred mounts:")
            reasons.extend(
                "• " + VOLUME_SETTINGS.mountpoint.format(volume=volume)
                for volume in missing
            )
        results.append(EnvironmentCompatibility(
            container=container,
            compatible=not reasons,
            tooltip="\n".join(reasons) if reasons else "Image and preferred mounts match.",
        ))
    return results
