import logging

from django.core.management.base import BaseCommand

from kubernetes import client, config
from container.models import Image
import time

from kooplexhub.settings import KUBERNETES_SERVICE_NAMESPACE

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Either take a given image_name or list all image of which attribute present=True and pull it on all nodes"

    def add_arguments(self, parser):
        parser.add_argument('imagename', type=str)


    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        imagename = options['imagename']
        if imagename:
            # Check whether the image is present in the database
            if Image.objects.filter(name=imagename).exists():
                pull_image_to_all_nodes(imagename)
            else:
                logger.error(f"Image {imagename} is not present in the database")
        else:
            for im in Image.objects.filter(present=True):
                print(im)
                pull_image_to_all_nodes(im.name)


def pull_image_to_all_nodes(image):
    # Load kube config
    config.load_kube_config("/tmp/config")
    # Create a Kubernetes API client
    v1 = client.CoreV1Api()
    namespace = KUBERNETES_SERVICE_NAMESPACE + '-pods'
    daemonset_name=f"image-puller-{image.split("/")[1]}"  # Name of the DaemonSet
    print(namespace)

    # Get all nodes
    # nodes = v1.list_node().items
    # Create a DaemonSet to pull the image on all nodes
    daemonset = client.V1DaemonSet(
        metadata=client.V1ObjectMeta(name=daemonset_name),
        spec=client.V1DaemonSetSpec(
            selector=client.V1LabelSelector(
                match_labels={"app": daemonset_name}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": daemonset_name}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name=daemonset_name,
                            image=image,
                            command=["sh", "-c", "sleep 10"]
                        )
                    ],
                    # tolerations=[
                    #     client.V1Toleration(
                    #         effect="NoSchedule",
                    #         operator="Exists"
                    #     )
                    # ]
                )
            )
        )
    )
    # Create the DaemonSet in the default namespace
    apps_v1 = client.AppsV1Api()
    print("Creating DaemonSet...")
    apps_v1.create_namespaced_daemon_set(namespace=namespace, body=daemonset)
    print("DaemonSet created.")
    # Wait for the DaemonSet to complete its job
    # (This is a placeholder, you might want to implement a proper wait mechanism)
    time.sleep(900)
    print("Image pulled on all nodes. Stopping the DaemonSet.")
    
    # Delete the DaemonSet after the image has been pulled
    apps_v1.delete_namespaced_daemon_set(name=daemonset_name, namespace=namespace)
    
    return apps_v1