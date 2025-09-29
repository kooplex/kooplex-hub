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
        "workdir": {
                "claim": 'education',
                "subpath": 'course/{course.folder}/{user.username}',
                "mountpoint": '/course/{course.folder}',
                "mountpoint_hub": '/mnt/course_workdir',
            },
        "public": {
                "claim": 'education',
                "subpath": 'course/{course.folder}/public',
                "mountpoint": '/course/{course.folder}.public',
                "mountpoint_hub": '/mnt/course_public',
            },
        "assignment": {
                "claim": 'education',
                "subpath_teacher": 'assignment/{course.folder}/',
                "subpath_student": 'assignment/{course.folder}/{user.username}',
                "mountpoint": '/assignment/{course.folder}.assignment',
                "mountpoint_hub": '/mnt/course_assignment',
            },
        "assignment_prepare": {
                "claim": 'education',
                "subpath": 'assignment_prepare/{course.folder}',
                "mountpoint": '/course/{course.folder}.assignment_prepare',
                "mountpoint_hub": '/mnt/assignment_prepare',
            },
        "assignment_correct": {
                "claim": 'education',
                "subpath_teacher": 'assignment_prepare/{course.folder}/',
                "subpath_student": 'assignment_prepare/{course.folder}/{user.username}',
                "mountpoint": '/course/{course.folder}.correct',
                "mountpoint_hub": '/mnt/assignment_correct',
            },
        },
}

EDUCATION_SETTINGS = make_app_settings(defaults=DEFAULTS, section="education")


