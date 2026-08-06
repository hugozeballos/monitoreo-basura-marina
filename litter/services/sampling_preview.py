from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError

from litter.models import SamplingMethod


@dataclass(frozen=True)
class SamplingPreview:
    """Read-only estimate of how many units/area a method+params combo would produce, before an event is created."""

    units_expected: int
    area_m2_total_estimated: float
    area_m2_per_unit: Optional[float]
    layout: Optional[str]
    unit_kind: Optional[str]


def _resolve_param(spec: dict, params: dict):
    """Resolve one template param: use params[spec['param']] if present, else spec['default']."""
    if not spec:
        return None
    if "param" in spec:
        key = spec["param"]
        if key in params and params[key] is not None:
            return params[key]
    return spec.get("default")


def build_effective_params(method: SamplingMethod, overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge a method's default_params_schema defaults with caller-provided overrides (overrides win)."""
    defaults = {}
    schema = method.default_params_schema or {}
    for k, v in schema.items():
        if isinstance(v, dict) and "default" in v:
            defaults[k] = v["default"]
    overrides = overrides or {}
    return {**defaults, **overrides}


def compute_preview(method: SamplingMethod, method_params: Optional[Dict[str, Any]]) -> SamplingPreview:
    """Estimate units_expected/area for a method+params combo, without creating any SamplingUnit rows."""
    tpl = method.unit_template or {}
    if not tpl:
        raise ValidationError("SamplingMethod has no unit_template configured.")

    params = build_effective_params(method, method_params)

    layout = tpl.get("layout")
    unit_kind = tpl.get("unit_kind", "quadrat")

    # MVP actual: transect_station_grid (mismo layout que ya soporta tu modelo)
    if layout == "transect_station_grid":
        transects_spec = tpl.get("transects", {"default": 1})
        stations_spec = tpl.get("stations_per_transect", {"default": 1})
        area_spec = tpl.get("area_m2", {"default": 1.0})

        n_transects = int(_resolve_param(transects_spec, params) or 0)
        n_stations = int(_resolve_param(stations_spec, params) or 0)
        area_m2_per_unit = float(_resolve_param(area_spec, params) or 0.0)

        if n_transects <= 0 or n_stations <= 0:
            raise ValidationError("Invalid template params: n_transects/n_stations must be > 0.")
        if area_m2_per_unit <= 0:
            raise ValidationError("Invalid template params: area_m2 must be > 0.")

        units_expected = n_transects * n_stations
        return SamplingPreview(
            units_expected=units_expected,
            area_m2_total_estimated=units_expected * area_m2_per_unit,
            area_m2_per_unit=area_m2_per_unit,
            layout=layout,
            unit_kind=unit_kind,
        )

    # Soporte futuro: otros layouts
    raise ValidationError(f"Unsupported layout: {layout}")