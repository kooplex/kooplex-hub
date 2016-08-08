from docker.client import Client
from kooplex.lib import LibBase, get_settings
from kooplex.hub.models.container import Container

class Docker(LibBase):

    def __init__(self, host=None, port=None, network=None, socket=False):
        if socket:
            self.host = None
            self.port = None
            self.network = None
        else:
            self.host = get_settings('docker', 'host', host)
            self.port = get_settings('docker', 'port', port)
            self.network = get_settings('docker', 'network', network, 'kooplex')

        self.docli = self.make_docker_client()

    def get_docker_url(self):
        if self.host is None or self.port is None:
            url = 'unix:///var/run/docker.sock'
        else:
            url = 'tcp://%s:%d' % (self.host, self.port)
        return url

    def make_docker_client(self):
        url = self.get_docker_url()
        cli = Client(base_url=url)
        return cli

    def get_network(self):
        nets = self.docli.networks(names = (self.network,))
        if nets and len(nets) == 1:
            return nets[0]
        else:
            return None

    def get_image_name(self, image):
        if type(image) is str:
            name = image
        elif type(image) is Container:
            name = image.image
        return name

    def get_image(self, image):
        name = self.get_image_name(image)
        imgs = self.docli.images(name=name)
        if imgs and len(imgs) == 1:
            return imgs[0]
        else:
            return None

    def pull_image(self, name):
        self.docli.pull(name)
        img = self.get_image(name)
        return img

    def build_image(self):
        raise NotImplementedError

    def ensure_image_exists(self, image):
        img = self.get_image(image)
        if img is None:
            img = self.pull_image(image)
        return img

    def remove_image(self, image):
        self.docli.remove_image(image)

    def ensure_network_configured(self, container):
        if not container.network:
            container.network = self.network

    def create_container(self, container):
        self.ensure_image_exists(container.image)
        self.ensure_network_configured(container)
        volumes = container.get_volumes()
        binds = container.get_binds()
        host_config = self.docli.create_host_config(
            binds=binds,
            privileged=container.privileged
            )
        networking_config = container.get_networking_config()
        environment = container.get_environment()
        ports = container.get_ports()
        c = self.docli.create_container(
            name=container.name,
            image=container.image,
            detach=True,
            hostname=container.name,
            host_config=host_config,
            networking_config=networking_config,
            command=container.command,
            environment=environment,
            volumes=volumes,
            ports=ports
        )
        #TODO: convey UID to container so that permissions on NFS are correct
        return self.get_container(container)

    def get_container_name(self, container):
        if type(container) is str:
            name = container
        else:
            name = container.name
        return name

    def get_container(self, container):
        name = self.get_container_name(container)
        conts = self.docli.containers(all=True, filters={'name': name})
        if conts and len(conts) == 1:
            return Container.from_docker_dict(self, conts[0])
        else:
            return None

    def ensure_container_exists(self, container):
        c = self.get_container(container)
        if c is None:
            c = self.create_container(container)
        return c

    def list_containers(self):
        containers = docli.containers(all=True)
        # TODO: modify to return user's containers only
        #containers = [ c for c in docli.containers() if
        #Spawner.container_prefix in c['Names'][0] ]
        return containers

    def start_container(self, container):
        name = self.get_container_name(container)
        self.docli.start(name)
        return self.get_container(container)

    def ensure_container_running(self, container):
        container = self.ensure_container_exists(container)
        if container.state in ('created', 'exited') :
            container = self.start_container(container)
        return container

    def stop_container(self, container):
        name = self.get_container_name(container)
        self.docli.stop(name)

    def kill_container(self, container):
        name = self.get_container_name(container)
        self.docli.kill(name)

    def ensure_container_stopped(self, container):
        container = self.get_container(container)
        if container and container.state not in ('created', 'exited'):
            self.stop_container(container)
        # TODO: kill if stop isn't working

    def remove_container(self, container):
        name = self.get_container_name(container)
        self.docli.remove_container(container=name)

    def ensure_container_removed(self, container):
        container = self.get_container(container)
        if container:
            self.ensure_container_stopped(container)
            self.remove_container(container)

    def exec_container(self, container, command):
        exec = self.docli.exec_create(
            container=container.name, 
            cmd=command, 
            #user=self.username,
        )
        # TODO: use real user once LDAP and PAM are set up inside image
        res = self.docli.exec_start(exec, detach=True)
        return res