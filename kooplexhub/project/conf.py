from hub.confutils import make_app_settings  # or get_app_settings

DEFAULTS = {
    "wss": {
        'join': 'wss://localhost/hub/ws/project/join/{user.id}/',
        'config': 'wss://localhost/hub/ws/project/config/{user.id}/',
        'containers': 'wss://localhost/hub/ws/project/container/{user.id}/',
        'users': 'wss://localhost/hub/ws/project/userhandler/{user.id}/',
        },
    "mounts": {
        "project": {
                "claim": 'project',
                "subpath": 'projects/{project.subpath}',
                "mountpoint": '/project/{project.subpath}',
                "mountpoint_hub": '/mnt/projects',
            },
        },
}

PROJECT_SETTINGS = make_app_settings(defaults=DEFAULTS, section="project")

