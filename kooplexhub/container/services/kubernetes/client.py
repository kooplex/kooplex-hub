from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


@dataclass(frozen=True)
class KubernetesClients:
    namespace: str
    core: client.CoreV1Api
    apps: client.AppsV1Api
    custom: client.CustomObjectsApi


def load_configuration() -> None:
    config.load_kube_config()
   # """Prefer the service-account configuration, then fall back to kubeconfig."""
   # try:
   #     config.load_incluster_config()
   # except ConfigException:
   #     config.load_kube_config()


@lru_cache(maxsize=8)
def get_kubernetes_clients(namespace: str) -> KubernetesClients:
    load_configuration()
    return KubernetesClients(
        namespace=namespace,
        core=client.CoreV1Api(),
        apps=client.AppsV1Api(),
        custom=client.CustomObjectsApi(),
    )
