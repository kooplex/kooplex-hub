from docker.client import Client
from kooplex.lib import LibBase, get_settings

class Docker(LibBase):

    def __init__(self, host=None, port=None, network=None, socket=False):
        if socket:
            self.host = None
            self.port = None
            self.network = None
        else:
            self.host = get_settings('KOOPLEX_DOCKER', 'host', host)
            self.port = get_settings('KOOPLEX_DOCKER', 'port', port)
            self.network = get_settings('KOOPLEX_DOCKER', 'network', network, 'kooplex')

        self.docli = self.make_docker_client()

    def make_docker_client(self):
        if self.host is None or self.port is None:
            url = 'unix:///var/run/docker.sock'
        else:
            url = 'tcp://%s:%d' % (self.host, self.port)
        cli = Client(base_url=url)
        return cli

    def get_network(self):
        nets = self.docli.networks(names = (self.network,))
        if nets and len(nets) == 1:
            return nets[0]
        else:
            return None

    def get_image(self, name):
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

    def ensure_image_exists(self, name):
        img = self.get_image(name)
        if img is None:
            img = self.pull_image(name)
        return img

    def remove_image(self, name):
        self.docli.remove_image(name)

    def create_container(self, name, image, command=None, ip=None, environment=None, ports=None, volumes=None):
        self.ensure_image_exists(image)
        host_config = {}
        networking_config = {
            'EndpointsConfig': {
                self.network: {
                    'IPAMConfig': {
                        'IPv4Address': ip,
                        #'IPv6Address': '...',
                    }
                }
            }
        }
        container = self.docli.create_container(
            name=name,
            image=image,
            detach=True,
            hostname=name,
            host_config=host_config,
            networking_config=networking_config,
            environment=environment,
            ports=ports,
            volumes=volumes,
            command=command
        )
        #TODO: convey UID to container so that permissions on NFS are correct
        return self.get_container(name)

    def get_container(self, name):
        conts = self.docli.containers(all=True, filters={'name': name})
        if conts and len(conts) == 1:
            return conts[0]
        else:
            return None

    def get_container_ip(self, name):
        container = self.get_container(name)
        ip = container['NetworkSettings']['Networks'][self.network]['IPAMConfig']['IPv4Address']
        return ip

    def ensure_container_exists(self, name, image, command=None, ip=None, environment=None, ports=None, volumes=None):
        container = self.get_container(name)
        if container is None:
            container = self.create_container(name, image, command, ip, environment, ports, volumes)
        return container

    def list_containers(self):
        containers = docli.containers(all=True)
        # TODO: modify to return user's containers only
        #containers = [ c for c in docli.containers() if
        #Spawner.container_prefix in c['Names'][0] ]
        return containers

    def start_container(self, name):
        container = self.get_container(name)
        self.docli.start(container)
        return self.get_container(name)

    def ensure_container_running(self, name, image=None, command=None, ip=None, environment=None, ports=None, volumes=None):
        if image:
            container = self.ensure_container_exists(name, image, command, ip, environment, ports, volumes)
        else:
            container = self.get_container(name)
        # created|restarting|running|paused|exited|dead
        if container['State'] in ('created', 'exited') :
            container = self.start_container(name)
        return container

    def stop_container(self, id):
        self.docli.stop(container=id)

    def kill_container(self, id):
        self.docli.kill(container=id)

    def ensure_container_stopped(self, name):
        container = self.get_container(name)
        if container and container['State'] not in ('created', 'exited'):
            self.stop_container(container['Id'])
        # TODO: kill if stop isn't working

    def remove_container(self, id):
        self.docli.remove_container(id)

    def ensure_container_removed(self, name):
        container = self.get_container(name)
        if container:
            self.ensure_container_stopped(name)
            self.remove_container(container['Id'])

    def exec_container(self, name, command):
        exec = self.docli.exec_create(
            container=name, 
            cmd=command, 
            #user=self.username,
        )
        # TODO: use real user once LDAP and PAM are set up inside image
        res = self.docli.exec_start(exec, detach=True)
        return res