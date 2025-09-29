from hub.confutils import make_app_settings  # or get_app_settings

DEFAULTS = {
    "kubernetes": {
            "namespace": "default",
            "nodeSelector_k8s": {},
            'imagePullPolicy': 'IfNotPresent',
            "resources": {
                #FIXME
                    "min_cpu": .1,
                    "min_gpu": 0,
                    "min_memory": .1,
                    "min_idletime": 1,
                    "max_cpu": 4,
                    "max_gpu": 0,
                    "max_memory": 2,
                    "max_idletime": 24,
                    "limit_cpu": 5,
                    "limit_gpu": 0,
                    "limit_memory": 28,
                },
            'secrets': {
                'name' : 'main-secrets',
                'mount_dir' :'/.secrets',
                },
            'jobs': {
                'namespace': 'jobs', 
                'jobpy': '/etc/jobtool',
                'token_name': 'job_token'
                },
            'nslcd': { 
                'mountPath_nslcd': '/etc/mnt' 
                },
            'initscripts': { 'mountPath_initscripts': '/.init_scripts' },
        },
    "proxy": {
            "proto": "https",
            "url": 'http://localhost:8001/api',
            "check_container": 'routes/notebook/{container.label}',
            "auth_token": "",
        },
    "wss": {
            "fetchlog": 'wss://localhost/hub/ws/container/fetchlog/{user.id}/',
            "config": 'wss://localhost/hub/ws/container/config/{user.id}/',
            "control": 'wss://localhost/hub/ws/container/control/{user.id}/',
            "monitor_node": 'wss://localhost/hub/ws/monitor/node/{user.id}/',
        },
}

CONTAINER_SETTINGS = make_app_settings(defaults=DEFAULTS, section="container")

