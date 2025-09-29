from hub.confutils import make_app_settings  # or get_app_settings

DEFAULTS = {
    "wss": {
        "courses": 'wss://localhost/hub/ws/canvas/fetchcourses/{userid}/',
        'assignments': 'wss://localhost/hub/ws/canvas/fetchcourseassignments/', #FIXME
        },
    'filter': lambda x: x,
}

CANVAS_SETTINGS = make_app_settings(defaults=DEFAULTS, section="canvas")



