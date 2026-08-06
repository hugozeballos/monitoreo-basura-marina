from django.db import models

from .sampling_event import SamplingEvent


class SamplingUnit(models.Model):
    """
    A repeatable sampling unit within an event (e.g., quadrat at transect/station).
    Units are auto-generated from SamplingMethod templates (later iteration).
    """

    UNIT_KIND_CHOICES = [
        ("quadrat", "Quadrat"),
        ("belt_segment", "Belt segment"),
        ("segment", "Segment"),
        ("photo_quadrat", "Photo quadrat"),
        ("other", "Other"),
    ]

    ZONE_CHOICES = [
        ("intertidal", "Intertidal"),
        ("wrack_line", "Wrack line"),
        ("backshore", "Backshore"),
        ("dune", "Dune"),
        ("unknown", "Unknown"),
    ]

    sampling_event = models.ForeignKey(
        SamplingEvent, on_delete=models.CASCADE, related_name="units", db_index=True
    )

    unit_kind = models.CharField(
        max_length=32, choices=UNIT_KIND_CHOICES, default="quadrat"
    )

    # For methods without transects/stations these can be null.
    transect_no = models.PositiveSmallIntegerField(null=True, blank=True)
    station_no = models.PositiveSmallIntegerField(null=True, blank=True)

    zone = models.CharField(max_length=32, choices=ZONE_CHOICES, default="unknown")

    # Auditable area for this unit (the atomic piece for density derivation).
    area_m2 = models.FloatField()

    label = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sampling_event_id", "transect_no", "station_no", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["sampling_event", "unit_kind", "transect_no", "station_no"],
                name="uq_samplingunit_event_kind_transect_station",
            )
        ]

    def __str__(self) -> str:
        if self.label:
            return self.label
        t = self.transect_no if self.transect_no is not None else "-"
        s = self.station_no if self.station_no is not None else "-"
        return f"Event {self.sampling_event_id} | {self.unit_kind} | T{t}-S{s}"
