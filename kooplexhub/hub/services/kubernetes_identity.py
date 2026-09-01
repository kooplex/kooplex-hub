import base64
from dataclasses import dataclass

from kubernetes import client
from kubernetes.client.exceptions import (
    ApiException,
)

from container.services.kubernetes.client import (
    get_kubernetes_clients,
)

from ..conf import HUB_SETTINGS


class KubernetesIdentityError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class KubernetesIdentityStatus:
    namespace: str
    secret_present: bool
    token_present: bool
    token_matches: bool

    @property
    def ready(self):
        return (
            self.secret_present
            and self.token_present
            and self.token_matches
        )


def _namespaces():
    settings = (
        HUB_SETTINGS.kubernetes_identity
    )

    if not settings.enabled:
        return ()

    namespaces = tuple(
        dict.fromkeys(
            str(namespace).strip()
            for namespace
            in settings.secret_namespaces
            if str(namespace).strip()
        )
    )

    if not namespaces:
        raise KubernetesIdentityError(
            "Kubernetes identity provisioning "
            "is enabled, but no secret "
            "namespaces are configured."
        )

    return namespaces


def ensure_user_kubernetes_identity(
    *,
    profile,
):
    settings = (
        HUB_SETTINGS.kubernetes_identity
    )

    if not settings.enabled:
        return ()

    if not profile.token:
        raise KubernetesIdentityError(
            "Profile has no job token."
        )

    user = profile.user
    key = settings.job_token_key

    touched = []

    for namespace in _namespaces():
        core = (
            get_kubernetes_clients(
                namespace
            ).core
        )

        body = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=user.username,
            ),
            type="Opaque",
            string_data={
                key: profile.token,
            },
        )

        try:
            core.read_namespaced_secret(
                name=user.username,
                namespace=namespace,
            )

        except ApiException as error:
            if error.status != 404:
                raise KubernetesIdentityError(
                    "Could not inspect Kubernetes "
                    f"secret {namespace}/"
                    f"{user.username}: {error}"
                ) from error

            core.create_namespaced_secret(
                namespace=namespace,
                body=body,
            )

        else:
            core.patch_namespaced_secret(
                name=user.username,
                namespace=namespace,
                body=body,
            )

        touched.append(namespace)

    return tuple(touched)


def inspect_user_kubernetes_identity(
    *,
    profile,
):
    settings = (
        HUB_SETTINGS.kubernetes_identity
    )

    if not settings.enabled:
        return ()

    result = []

    for namespace in _namespaces():
        core = (
            get_kubernetes_clients(
                namespace
            ).core
        )

        try:
            secret = (
                core.read_namespaced_secret(
                    name=profile.user.username,
                    namespace=namespace,
                )
            )

        except ApiException as error:
            if error.status == 404:
                result.append(
                    KubernetesIdentityStatus(
                        namespace=namespace,
                        secret_present=False,
                        token_present=False,
                        token_matches=False,
                    )
                )
                continue

            raise

        encoded = (
            (secret.data or {}).get(
                settings.job_token_key
            )
        )

        token = None

        if encoded:
            token = (
                base64.b64decode(encoded)
                .decode("utf-8")
            )

        result.append(
            KubernetesIdentityStatus(
                namespace=namespace,
                secret_present=True,
                token_present=(
                    token is not None
                ),
                token_matches=(
                    token == profile.token
                ),
            )
        )

    return tuple(result)


