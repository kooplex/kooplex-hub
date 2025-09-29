from hub.confutils import make_app_settings  # or get_app_settings

DEFAULTS = {
    "wss": {
        'config': 'wss://localhost/hub/ws/volume/config/{user.id}/',
        },
    "mounts": {
        "attachment": {
                "claim": 'attachment',
                "subpath": '{volume.folder}',
                "mountpoint": '/attachment/{volume.folder}',
                "mountpoint_hub": '/mnt/attachments',
            },
        "volume": {
                "claim": "{volume.claim}",
                "mountpoint": '/volume/{volume.folder}',
            },
        },
}

VOLUME_SETTINGS = make_app_settings(defaults=DEFAULTS, section="volume")


