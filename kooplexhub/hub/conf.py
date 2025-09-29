from hub.confutils import make_app_settings  # or get_app_settings

DEFAULTS = {
    'ldap': {
        'host': 'localhost',
        'port': 389,
        'base_dn': 'dn=localhost',
        'bind_dn': 'cn=admin,dn=localhost',
        'bind_password': False,
        'userdn': 'uid={user.username},ou=users,dn=localhost',
        'groupdn': 'uid={group.name},ou=users,dn=localhost',
        'usersearch': 'ou=users,dn=localhost',
        'groupsearch': 'ou=groups,dn=localhost',
        'managegroup': False,
        'offset': {
            'project': 10000, 
            'course': 20000, 
            'volume': 30000, 
            },
        },
    'archive_home': False,
    'wss': {
        'token': 'wss://localhost/hub/ws/tokens/{user.id}/',
        'resources': 'wss://localhost/hub/ws/resources/', #FIXME: authorize?
        },
    "mounts": {
        "home": {
                "claim": 'userdata',
                "subpath": 'home/{user.username}',
                "mountpoint": '/home/{user.username}',
                "mountpoint_hub": '/mnt/home',
            },
        "garbage": {
                "claim": 'userdata',
                "subpath": 'garbage/{user.username}',
                "mountpoint": '/garbage/{user.username}',
                "mountpoint_hub": '/mnt/garbage',
            },
        "scratch": {
                "claim": 'userdata',
                "subpath": 'scratch/{user.username}',
                "mountpoint": '/scratch/{user.username}',
                "mountpoint_hub": '/mnt/scratch',
            },
        },
}

HUB_SETTINGS = make_app_settings(defaults=DEFAULTS, section="hub")

