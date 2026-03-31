import logging
import time
from tqdm import tqdm
from kubernetes import client, config, watch
from django.db import connection, connections, close_old_connections
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from kubernetes import client, config, watch

from django.utils import timezone
from ...conf import CONTAINER_SETTINGS

logger = logging.getLogger(__name__)


from container.models import Container
from hub.models import User
from pathlib import Path
import os

class Command(BaseCommand):
    help = "Start test containers, inject code and run them"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subcommand", required=True)

        # subcommand clean up
        p_cleanup = subparsers.add_parser("stop", help="Remove any pods starting with label 'test-'")

        # subcommand create
        p_create = subparsers.add_parser("start", help="Create n pods starting with label 'test-' for a given user")
        p_create.add_argument('--user', help = "Run containers for user", required = True)
        p_create.add_argument('--max', help = "Number of containers to launch", default = 1, type=int)
        p_create.add_argument('--cpurequest', help = "Change requested cpu resource", default = 1, type=float)
        p_create.add_argument('--memoryrequest', help = "Change requested memory resource", default = 1, type=float)
        p_create.add_argument('--image', help = "Use image to test", default = 32, type=int)

        # subcommand propagate scripts
        p_script = subparsers.add_parser("prepare", help="Copy script in the home folder for a given user")
        p_script.add_argument('--user', help = "Run containers for user", required = True)
        p_script.add_argument('--script', help = "Inject code", required = True)
        p_script.add_argument('--folder', help = "Create subfolder for the script", default = "stress")

        # subcommand run scripts in background
        p_launch = subparsers.add_parser("launch", help="Start script in the home folder in already running containers")
        p_launch.add_argument('--user', help = "Impersonate user", required = True)
        p_launch.add_argument('--script', help = "Inject code", required = True)
        p_launch.add_argument('--folder', help = "Create subfolder for the script", default = "stress")


    def cleanup(self):
        containers = Container.objects.filter(label__startswith=f"test-")
        fnd = 0
        for c in containers:
            self.stdout.write(self.style.SUCCESS(f"Removing container {c.label}"))
            c.delete()
            fnd += 1
        return fnd

    def create_containers(self, username, image_id, cpureq, memreq, n):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            msg = f"user {username} does not exist"
            self.stderr.write(msg)
            raise CommandError(msg)

        for i in range(n):
            c = Container.objects.create(user=user, image_id = image_id, label=f"test-{i}")
            c.memoryrequest = memreq
            c.cpurequest = cpureq
            c.save()
            c.start()
            self.stdout.write(self.style.SUCCESS(f"Created and starting container {c.label}"))


    def start_command_in_pod(self, container, command, user):
        from test.utils import kube_api
        from test.utils import get_container_state
        from kubernetes.stream import stream
        import shlex
        pod, container_label, namespace = get_container_state(container)
        k_api = kube_api()

        sfx = str(command)
        pidfile = "/tmp/sfx.pid"
        logfile = "/tmp/sfx.log"
        
        launch = (
            f"rm -f {shlex.quote(pidfile)}; "
            f"nohup {shlex.quote(sfx)} </dev/null >{shlex.quote(logfile)} 2>&1 "
            f"& echo $! > {shlex.quote(pidfile)}"
        )
        
        # If you need to run as another user, prefer a login env:
        cmd = ["sh", "-lc", f"su -l {shlex.quote(user.username)} -s /bin/sh -c {shlex.quote(launch)}"]

        
        resp = stream(k_api.connect_get_namespaced_pod_exec,
                        pod.metadata.name,
                        namespace,
                        command=cmd,
                        container=container_label,
                        stderr=False, stdin=False,
                        stdout=True, tty=False,
                        _preload_content=True,
                      )
    


    def run_code(self, username, folder, script):
        from test.utils import check_container_running, exec_command_in_pod
        script_path = Path('/v') / username / folder / script
        containers = Container.objects.filter(label__startswith=f"test-", user__username = username)
        c_ok = []
        while len(c_ok) < len(containers):
            containers_left = set(containers).difference(c_ok)
            for c in containers_left:
                if not check_container_running(c):
                    continue
                self.start_command_in_pod(c, script_path, c.user)
                c_ok.append(c)
                self.stdout.write(self.style.SUCCESS(f"Issued script {script_path} in container {c.label}"))

    def prepare_script(self, username, folder, code_src):
        import stat
        import pwd, grp
        try:
            uid = pwd.getpwnam(username).pw_uid
            gid = grp.getgrnam('users').gr_gid
        except:
            msg = f"Name resolution error: user {username} does not exist"
            self.stderr.write(msg)
            raise CommandError(msg)
        script = Path(code_src).name
        wd = Path("/mnt/home") / username / folder
        wd.mkdir(parents=True, exist_ok=True)
        os.chown(wd, uid, gid)
        self.stdout.write(self.style.SUCCESS(f"Created or found folder {wd}"))
        script_path= wd / script
        with open(code_src) as fin, open(script_path, 'w') as fon:
            sc = fin.read()
            fon.write(sc)

        st = os.stat(script_path)
        os.chmod(script_path, st.st_mode | stat.S_IXUSR)
        os.chown(script_path, uid, gid)
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(sc)} bytes to file {script_path}"))


    def handle(self, *args, **opts):
        cmd = opts["subcommand"]
        if cmd == "stop":
            self.cleanup()
        elif cmd == "start":
            username = opts['user']
            n = opts['max']
            cpureq = opts['cpurequest']
            memreq = opts['memoryrequest']
            image = opts['image']
            self.create_containers(username, image, cpureq, memreq, n)
        elif cmd == "prepare":
            username = opts['user']
            folder = opts['folder']
            script = opts['script']
            self.prepare_script(username, folder, script)
        elif cmd == "launch":
            username = opts['user']
            folder = opts['folder']
            script = opts['script']
            self.run_code(username, folder, script)
        else:
            raise CommandError(f"Unknown subcommand: {cmd}")
        return

