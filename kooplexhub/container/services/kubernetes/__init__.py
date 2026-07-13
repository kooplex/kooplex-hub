"""Kubernetes runtime and resource services for Kooplex containers.

Keep this initializer lightweight: importing a pure helper such as quantities or
labels must not initialize Django settings or load a Kubernetes configuration.
Runtime factories live in :mod:`container.services.kubernetes.wiring`.
"""

__all__: list[str] = []
