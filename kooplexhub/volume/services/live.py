"""Notify active Storage grids of committed volume lifecycle changes."""

from hub.services.live import broadcast_global_live_event


def broadcast_volume_list_changed(*, reason):
    # No private volume identifiers are exposed. Each grid is rendered
    # using its requesting user's access policy.
    broadcast_global_live_event(
        keys=["volume-list"],
        payload={"model": "volume-list", "reason": reason},
    )
