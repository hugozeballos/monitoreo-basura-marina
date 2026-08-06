from django.db import models

from .litter_type import LitterType
from .sampling_unit import SamplingUnit


class UnitLitterCount(models.Model):
    """
    Litter count at the unit level (granularity).
    For each (sampling_unit, litter_type) there should be one row.
    """

    sampling_unit = models.ForeignKey(
        SamplingUnit, on_delete=models.CASCADE, related_name="counts", db_index=True
    )
    litter_type = models.ForeignKey(
        LitterType, on_delete=models.PROTECT, related_name="unit_counts"
    )
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sampling_unit", "litter_type"],
                name="uq_unitlittercount_unit_type",
            )
        ]

    def __str__(self) -> str:
        return f"{self.sampling_unit_id} - {self.litter_type.label}: {self.count}"
