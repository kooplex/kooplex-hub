from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .labels import dns_label
from .types import BuiltWorkload, RouteSpec


class RouteConfigurationError(ValueError):
    """Raised when a Kooplex proxy cannot be translated into a CHP route."""


@dataclass(frozen=True)
class RouteBuilderSettings:
    """Configuration for :class:`KooplexRouteBuilder`.

    Templates are formatted with these values:

    ``container``
        The Kooplex ``Container`` model instance.
    ``proxy``
        One item from ``container.proxies``.
    ``workload``
        The built Kubernetes workload.
    ``service`` / ``namespace`` / ``port`` / ``proxy_name``
        Convenient scalar aliases.
    """

    endpoint_template: str = "http://{service}.{namespace}.svc.cluster.local:{port}"
    base_path_template: str | None = None


class KooplexRouteBuilder:
    """Build Configurable HTTP Proxy routes from ``container.proxies``.

    The public path is deliberately read from the proxy/domain model instead of
    being derived from the Kubernetes service name. Supported attribute names
    are ``base_path``, ``basepath``, ``route``, ``path`` and ``url`` (the latter
    only when it is a path beginning with ``/``). A project-wide
    ``base_path_template`` may be configured as a fallback.

    The target defaults to the stable Kubernetes Service FQDN. A proxy may
    override it with an ``endpoint`` or ``target`` attribute.
    """

    _BASE_PATH_ATTRIBUTES = ("base_path", "basepath", "route", "path")
    _ENDPOINT_ATTRIBUTES = ("endpoint", "target")

    def __init__(self, settings: RouteBuilderSettings | None = None):
        self.settings = settings or RouteBuilderSettings()

    def build(self, container: Any, workload: BuiltWorkload) -> list[RouteSpec]:
        routes: list[RouteSpec] = []
        seen_paths: set[str] = set()

        for proxy in self._iter_proxies(container):
            port = int(self._required_value(proxy, "svc_port"))
            proxy_name = str(self._required_value(proxy, "name"))
            self._validate_service_port(workload, proxy_name, port)

            context = {
                "container": container,
                "proxy": proxy,
                "workload": workload,
                "service": workload.name,
                "namespace": workload.namespace,
                "port": port,
                "proxy_name": proxy_name,
            }
            base_path = self._base_path(proxy, context)
            endpoint = self._endpoint(proxy, context)

            if base_path in seen_paths:
                raise RouteConfigurationError(
                    f"Duplicate proxy base path {base_path!r} for {workload.name}"
                )
            seen_paths.add(base_path)
            routes.append(RouteSpec(base_path=base_path, endpoint=endpoint))

        return routes

    @staticmethod
    def _iter_proxies(container: Any) -> list[Any]:
        proxies = getattr(container, "proxies", [])
        all_method = getattr(proxies, "all", None)
        if callable(all_method):
            proxies = all_method()
        return list(proxies or [])

    def _base_path(self, proxy: Any, context: dict[str, Any]) -> str:
        value = self._first_value(proxy, self._BASE_PATH_ATTRIBUTES)

        # Some older models expose a URL-looking property for the path.
        if value is None:
            maybe_url = self._value(proxy, "url")
            if isinstance(maybe_url, str) and maybe_url.startswith("/"):
                value = maybe_url

        if value is None and self.settings.base_path_template:
            value = self.settings.base_path_template

        if value is None:
            available = ", ".join(self._BASE_PATH_ATTRIBUTES)
            raise RouteConfigurationError(
                "Proxy route has no public base path. Add one of "
                f"[{available}] to the proxy object or configure "
                "CONTAINER_SETTINGS.proxy.base_path_template."
            )

        rendered = self._render(value, context)
        return self._normalize_base_path(rendered)

    def _endpoint(self, proxy: Any, context: dict[str, Any]) -> str:
        value = self._first_value(proxy, self._ENDPOINT_ATTRIBUTES)
        if value is None:
            value = self.settings.endpoint_template
        rendered = self._render(value, context).strip()
        if not rendered:
            raise RouteConfigurationError("Proxy endpoint rendered to an empty string")
        return rendered.rstrip("/")

    @staticmethod
    def _render(value: Any, context: dict[str, Any]) -> str:
        if callable(value):
            # Bound properties/methods in older Kooplex code are typically
            # zero-argument callables. Keeping this narrow avoids guessing an
            # arbitrary method signature.
            value = value()
        try:
            return str(value).format(**context)
        except (AttributeError, KeyError, IndexError) as exc:
            raise RouteConfigurationError(
                f"Could not format proxy route value {value!r}: {exc}"
            ) from exc

    @staticmethod
    def _normalize_base_path(value: str) -> str:
        path = value.strip()
        if not path:
            raise RouteConfigurationError("Proxy base path rendered to an empty string")
        if "://" in path:
            raise RouteConfigurationError(
                f"Proxy base path must be a path, not an absolute URL: {path!r}"
            )
        if not path.startswith("/"):
            path = f"/{path}"
        # CHP stores route keys without a trailing slash, except for root.
        return path if path == "/" else path.rstrip("/")

    @staticmethod
    def _required_value(obj: Any, name: str) -> Any:
        value = KooplexRouteBuilder._value(obj, name)
        if value is None:
            raise RouteConfigurationError(
                f"Proxy object {obj!r} is missing required attribute {name!r}"
            )
        return value

    @staticmethod
    def _first_value(obj: Any, names: Iterable[str]) -> Any | None:
        for name in names:
            value = KooplexRouteBuilder._value(obj, name)
            if value is not None:
                return value
        return None

    @staticmethod
    def _value(obj: Any, name: str) -> Any | None:
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    @staticmethod
    def _validate_service_port(
        workload: BuiltWorkload, proxy_name: str, expected_port: int
    ) -> None:
        expected_name = dns_label(proxy_name, max_length=15)
        for port in workload.service_ports:
            if port.get("name") == expected_name and int(port.get("port")) == expected_port:
                return
        raise RouteConfigurationError(
            f"Proxy {proxy_name!r}:{expected_port} has no matching Service port "
            f"in workload {workload.name!r}"
        )
