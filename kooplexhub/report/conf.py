from hub.confutils import make_app_settings  # or get_app_settings

DEFAULTS = {
    "mounts": {
        "prepare": {
                "claim": 'report',
                "subpath": 'prepare',
                "folder": '{project.subpath}',
                "mountpoint": '/project/{project.subpath}/report_prepare',
                "mountpoint_hub": '/mnt/report_prepare',
                "garbage": "{project.creator.username}/projectreport-{project.subpath}.{time.time()}.tar.gz",
            },
        "report": {
                "claim": 'report',
                "subpath": 'report',
                "folder": '{report.folder}',
                "mountpoint": '/report',
                "mountpoint_hub": '/mnt/reports',
            },
        },
    "paths": {
        "static": 'http://localhost/report/{report.id}/',
        "proxied": 'http://localhost/report/{container.label}/', #FIXME
        }
}

REPORT_SETTINGS = make_app_settings(defaults=DEFAULTS, section="report")


