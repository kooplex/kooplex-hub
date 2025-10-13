from hub.confutils import make_app_settings  # or get_app_settings

DEFAULTS = {
    "wss": {
        'config': 'wss://localhost/hub/ws/volume/config/{user.id}/',
        },
    "mounts": {
        "attachment": {
                "claim": 'attachments',
                "subpath": '{volume.folder}',
                "folder": '{volume.folder}',  # Ez mire van?
                "mountpoint": '/attachment/{volume.folder}',
                "mountpoint_hub": '/mnt/attachments',
            },
        "volume": {
                "mountpoint": '/volume/{volume.folder}',
            },
        },
}

VOLUME_SETTINGS = make_app_settings(defaults=DEFAULTS, section="volume")


