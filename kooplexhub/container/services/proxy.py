from __future__ import annotations

import logging
import requests
from datetime import datetime, timezone as datetime_timezone
from typing import Any
from urllib.parse import quote, urljoin


logger = logging.getLogger(__name__)


class ProxyActivityError(RuntimeError):
    """Raised when proxy activity information cannot be retrieved."""


class ProxyActivityClient:
    """Client for Kooplex's custom container-activity endpoint."""

    def __init__(
        self,
        base_url: str,
        check_container_path: str,
        *,
        auth_token: str | None = None,
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
    ):
        if not base_url:
            raise ValueError("Proxy activity base URL is required")

        if not check_container_path:
            raise ValueError("Proxy check_container path is required")

        self.base_url = base_url.rstrip("/") + "/"
        self.check_container_path = check_container_path
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

        if auth_token:
            self.session.headers.update(
                {"Authorization": f"token {auth_token}"}
            )

    def get_last_activity(self, container: Any) -> datetime:
        url = self._activity_url(container)

        try:
            response = self.session.get(
                url,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ProxyActivityError(
                f"Activity request failed for {container}: {exc}"
            ) from exc
        except ValueError as exc:
            raise ProxyActivityError(
                f"Activity endpoint returned invalid JSON for {container}"
            ) from exc

        raw_last_activity = payload.get("last_activity")
        if not raw_last_activity:
            raise ProxyActivityError(
                f"Activity response for {container} has no "
                "'last_activity' value"
            )

        return self._parse_timestamp(str(raw_last_activity))

    def _activity_url(self, container: Any) -> str:
        try:
            rendered_path = self.check_container_path.format(
                container=container
            )
        except (AttributeError, KeyError, IndexError) as exc:
            raise ProxyActivityError(
                "Could not format proxy check_container path "
                f"{self.check_container_path!r}: {exc}"
            ) from exc

        # Preserve a possible path component in base_url.
        return urljoin(
            self.base_url,
            rendered_path.lstrip("/"),
        )

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        normalized = value.strip()

        # datetime.fromisoformat() understands +00:00 consistently.
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        try:
            result = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ProxyActivityError(
                f"Invalid last_activity timestamp: {value!r}"
            ) from exc

        # Older proxy implementations may omit the timezone. Their timestamps
        # were intended as UTC, so handle that explicitly.
        if result.tzinfo is None:
            result = result.replace(tzinfo=datetime_timezone.utc)

        return result.astimezone(datetime_timezone.utc)


class ConfigurableHttpProxyClient:
    def __init__(
        self,
        routes_url: str,
        auth_token: str,
        *,
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
    ):
        self.routes_url = routes_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"token {auth_token}"})

    def list_routes(self) -> dict:
        response = self.session.get(self.routes_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def add_route(self, base_path: str, endpoint: str) -> None:
        response = self.session.post(
            self._route_url(base_path),
            json={"target": endpoint},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        logger.debug("Added proxy route %s -> %s", base_path, endpoint)

    def remove_route(self, base_path: str) -> None:
        response = self.session.delete(
            self._route_url(base_path),
            timeout=self.timeout_seconds,
        )
        if response.status_code not in (200, 204, 404):
            response.raise_for_status()
        logger.debug("Removed proxy route %s", base_path)

    def drop_all_routes(self) -> None:
        for base_path in self.list_routes():
            self.remove_route(base_path)

    def _route_url(self, base_path: str) -> str:
        normalized = quote(base_path.lstrip("/"), safe="/")
        return f"{self.routes_url}/{normalized}"
