# litter/models/__init__.py

from .beach import Beach
from .litter_type import LitterType
from .sampling_method import SamplingMethod
from .sampling_event import SamplingEvent
from .sampling_unit import SamplingUnit
from .unit_litter_count import UnitLitterCount
from .sampling_photo import SamplingPhoto
from .organization import Organization


# Backward-compatible alias: old code imports LitterCount
LitterCount = UnitLitterCount

__all__ = [
    "Beach",
    "LitterType",
    "SamplingMethod",
    "SamplingEvent",
    "SamplingUnit",
    "UnitLitterCount",
    "SamplingPhoto",
    "LitterCount",
    "Organization",
]
