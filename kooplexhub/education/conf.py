from hub.confutils import make_app_settings  # or get_app_settings

DEFAULTS = {
    "wss": {
        "containers": 'wss://localhost/hub/ws/education/container/{user.id}/',
        'handin': 'wss://localhost/hub/ws/education/handin/{user.id}/',
        'config': 'wss://localhost/hub/ws/course/config/{user.id}/',
        'users': 'wss://localhost/hub/ws/course/userhandler/{user.id}/',
        'assignments': 'wss://localhost/hub/ws/assignment/config/{user.id}/',
        'score': 'wss://localhost/hub/ws/assignment/score/{user.id}/',
        },
    "mounts": {
        "public": {
                "claim": 'education',
                "subpath": 'public',
                "folder": '{course.folder}/public',
                "mountpoint": '/course/{course.folder}.public',
                "mountpoint_hub": '/mnt/course_public',
            },
        "assignment_prepare": {
                "claim": 'education',
                "subpath": 'assignment_prepare',
                "folder": '{course.folder}',
                "mountpoint": '/course/{course.folder}.assignment_prepare',
                "mountpoint_hub": '/mnt/assignment_prepare',
            },
        "assignment_snapshot": {
                "claim": 'education',
                "subpath": 'assignment_snapshot',
                "folder": '{course.folder}',
                "mountpoint": '/course/{course.folder}.assignment_snapshot',
                "mountpoint_hub": '/mnt/assignment_snapshot',
            },
        "workdir": {
                "claim": 'education',
                "subpath": 'workdir',
                "folder_top": '{course.folder}',
                "folder": '{course.folder}/{user.username}',
                "mountpoint": '/course/{course.folder}',
                "mountpoint_hub": '/mnt/course_workdir',
            },
        "assignment": {
                "claim": 'education',
                "subpath": 'assignment',
                "folder_top": '{course.folder}',
                "folder": '{course.folder}/{user.username}',
                "mountpoint": '/assignment/{course.folder}.assignment',
                "mountpoint_hub": '/mnt/course_assignment',
            },
        "assignment_correct": {
                "claim": 'education',
                "subpath": 'assignment_correct',
                "folder_top": '{course.folder}',
                "folder": '{course.folder}/{user.username}',
                "mountpoint": '/course/{course.folder}.correct',
                "mountpoint_hub": '/mnt/assignment_correct',
            },
        },
}

EDUCATION_SETTINGS = make_app_settings(defaults=DEFAULTS, section="education")


