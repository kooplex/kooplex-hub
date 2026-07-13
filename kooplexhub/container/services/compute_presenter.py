from dataclasses import dataclass
from decimal import Decimal

from ..conf import CONTAINER_SETTINGS
from .compute_limits import ComputeLimits, compute_limits_provider


@dataclass
class ResourceMetric:
    requested: float
    used: float | None
    unit: str
    percentage: float | None
    width_percentage: float
    level: str
    usage_label: str


@dataclass
class ContainerComputePresenter:
    container: object
    limits: ComputeLimits | None = None

    def __post_init__(self):
        if self.limits is None:
            self.limits = compute_limits_provider.for_container(self.container)

    @property
    def is_running(self):
        return self.container.is_running

    @property
    def is_transitioning(self):
        return self.container.state in {
            self.container.State.STARTING,
            self.container.State.STOPPING,
        }

    @property
    def is_editable(self):
        return not self.is_transitioning

    @property
    def requested_cpu(self):
        return self._number(self.container.requested_cpu_m)

    @property
    def requested_memory(self):
        return self._number(self.container.requested_memory_mib)

    @property
    def requested_gpu(self):
        return int(self.container.requested_gpu or 0)

    @property
    def cpu_setting_percent(self):
        return self._setting_percentage(
            self.requested_cpu,
            self.limits.cpu_min,
            self.limits.cpu_max,
        )

    @property
    def memory_setting_percent(self):
        return self._setting_percentage(
            self.requested_memory,
            self.limits.memory_min,
            self.limits.memory_max,
        )

    @property
    def gpu_setting_percent(self):
        return self._setting_percentage(
            self.requested_gpu,
            self.limits.gpu_min,
            self.limits.gpu_max,
        )

    @property
    def cpu(self):
        return self._metric(
            requested=self.requested_cpu,
            used=self._optional_number(self.container.cpu_usage_m),
            unit="CPU",
        )

    @property
    def memory(self):
        return self._metric(
            requested=self.requested_memory,
            used=self._optional_number(self.container.memory_usage_mib),
            unit="GiB",
        )

    @property
    def gpu_label(self):
        return str(self.requested_gpu)

    def _metric(self, requested, used, unit):
        if used is None or requested <= 0:
            return ResourceMetric(
                requested=requested,
                used=used,
                unit=unit,
                percentage=None,
                width_percentage=0,
                level="unavailable",
                usage_label="No metric available",
            )

        percentage = used / requested * 100
        level = self._usage_level(percentage / 100)

        return ResourceMetric(
            requested=requested,
            used=used,
            unit=unit,
            percentage=percentage,
            width_percentage=min(100, max(0, percentage)),
            level=level,
            usage_label=(
                f"{self._format(used)} / "
                f"{self._format(requested)} {unit} "
                f"({percentage:.0f}%)"
            ),
        )

    def _usage_level(self, ratio):
        settings = CONTAINER_SETTINGS.compute_widget

        if ratio > settings.critical_ratio:
            return "critical"

        if ratio >= settings.warning_ratio:
            return "warning"

        return "normal"

    @staticmethod
    def _setting_percentage(value, minimum, maximum):
        if maximum <= minimum:
            return 0

        percentage = (value - minimum) / (maximum - minimum) * 100
        return min(100, max(0, percentage))

    @staticmethod
    def _number(value):
        if value is None:
            return 0.0
        return float(value)

    @classmethod
    def _optional_number(cls, value):
        if value is None:
            return None
        return cls._number(value)

    @staticmethod
    def _format(value):
        if isinstance(value, Decimal):
            value = float(value)

        if float(value).is_integer():
            return str(int(value))

        return f"{float(value):.1f}"

