from django.conf import settings
from django.db import models

from .beach import Beach
from .sampling_method import SamplingMethod
from django.db import models, transaction
from django.core.exceptions import ValidationError


class SamplingEvent(models.Model):
    """
    A sampling campaign/event at a given beach and date.
    Uses workflow status: draft -> submitted -> validated/rejected.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("validated", "Validated"),
        ("rejected", "Rejected"),
    ]

    beach = models.ForeignKey(
        Beach, on_delete=models.PROTECT, related_name="events", db_index=True
    )
    date = models.DateField(db_index=True)

    sampling_method = models.ForeignKey(
        SamplingMethod, on_delete=models.PROTECT, related_name="events"
    )
    method_params = models.JSONField(blank=True, null=True)

    notes = models.TextField(blank=True)

    # Workflow / audit
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="draft", db_index=True
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_sampling_events",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_sampling_events",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    # Optional persisted caches (system-owned; may be null until computed later)
    event_total_items = models.IntegerField(null=True, blank=True)
    event_area_m2 = models.FloatField(null=True, blank=True)
    event_density_items_per_m2 = models.FloatField(null=True, blank=True)

    units_expected = models.IntegerField(null=True, blank=True)
    units_completed = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    organization = models.ForeignKey(
        "litter.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events"
    )


    def _resolve_param(self, spec: dict, params: dict):
        """
        spec: {"param": "n_transects", "default": 2}  OR {"default": 2}
        params: event.method_params merged with method defaults
        """
        if not spec:
            return None
        if "param" in spec:
            key = spec["param"]
            if key in params and params[key] is not None:
                return params[key]
        return spec.get("default")

    def _build_effective_params(self) -> dict:
        """
        Merge defaults from SamplingMethod.default_params_schema with event.method_params overrides.
        """
        method = self.sampling_method
        if not method:
            return {}

        defaults = {}
        schema = method.default_params_schema or {}
        for k, v in schema.items():
            if isinstance(v, dict) and "default" in v:
                defaults[k] = v["default"]

        overrides = self.method_params or {}
        # overrides wins
        return {**defaults, **overrides}

    @transaction.atomic
    def generate_units_from_method(self, *, overwrite_area=False) -> int:
        """
        Create SamplingUnit rows based on sampling_method.unit_template.
        Returns number of units created.
        Idempotent: uses get_or_create (won't duplicate).
        """
        if not self.sampling_method:
            raise ValidationError("SamplingEvent has no sampling_method.")

        tpl = self.sampling_method.unit_template or {}
        if not tpl:
            raise ValidationError("SamplingMethod has no unit_template configured.")

        params = self._build_effective_params()

        unit_kind = tpl.get("unit_kind", "quadrat")
        layout = tpl.get("layout")

        # Only implement the MVP layout now: transect_station_grid
        if layout != "transect_station_grid":
            raise ValidationError(f"Unsupported layout: {layout}")

        transects_spec = tpl.get("transects", {"default": 1})
        stations_spec = tpl.get("stations_per_transect", {"default": 1})
        area_spec = tpl.get("area_m2", {"default": 1.0})
        label_fmt = tpl.get("label_format", "T{transect}-S{station}")

        n_transects = int(self._resolve_param(transects_spec, params) or 0)
        n_stations = int(self._resolve_param(stations_spec, params) or 0)
        area_m2 = float(self._resolve_param(area_spec, params) or 0.0)

        if n_transects <= 0 or n_stations <= 0:
            raise ValidationError("Invalid template params: n_transects/n_stations must be > 0.")
        if area_m2 <= 0:
            raise ValidationError("Invalid template params: area_m2 must be > 0.")

        from .sampling_unit import SamplingUnit  # local import to avoid circulars

        created_count = 0
        for t in range(1, n_transects + 1):
            for s in range(1, n_stations + 1):
                label = label_fmt.format(transect=t, station=s)

                obj, created = SamplingUnit.objects.get_or_create(
                    sampling_event=self,
                    unit_kind=unit_kind,
                    transect_no=t,
                    station_no=s,
                    defaults={
                        "zone": "unknown",
                        "area_m2": area_m2,
                        "label": label,
                    },
                )
                if created:
                    created_count += 1
                else:
                    # optionally update area if template changes
                    if overwrite_area and obj.area_m2 != area_m2:
                        obj.area_m2 = area_m2
                        obj.save(update_fields=["area_m2"])

        # Optional persisted cache (si lo estás usando)
        # units_expected: total de unidades esperadas por método
        try:
            self.units_expected = n_transects * n_stations
            self.save(update_fields=["units_expected"])
        except Exception:
            # no rompemos si el campo no existe
            pass

        return created_count
    
    def update_event_metrics(self):
        """
        Calculate and persist event-level metrics
        based on SamplingUnits and UnitLitterCount.
        Only applies if event is VALIDATED.
        """

        if self.status != "validated":
            # Clear caches if not validated
            self.event_total_items = None
            self.event_area_m2 = None
            self.event_density_items_per_m2 = None
            self.save(update_fields=[
                "event_total_items",
                "event_area_m2",
                "event_density_items_per_m2",
            ])
            return

        # Import here to avoid circular imports
        from .sampling_unit import SamplingUnit
        from .unit_litter_count import UnitLitterCount

        # Get all units of this event
        units = SamplingUnit.objects.filter(sampling_event=self)

        total_area = units.aggregate(
            total=models.Sum("area_m2")
        )["total"] or 0

        # Sum all counts for this event
        total_items = UnitLitterCount.objects.filter(
            sampling_unit__sampling_event=self
        ).aggregate(
            total=models.Sum("count")
        )["total"] or 0

        density = 0
        if total_area > 0:
            density = total_items / total_area

        # Persist values
        self.event_total_items = total_items
        self.event_area_m2 = total_area
        self.event_density_items_per_m2 = density

        self.save(update_fields=[
            "event_total_items",
            "event_area_m2",
            "event_density_items_per_m2",
        ])

    def save(self, *args, **kwargs):
        """
        Override save to detect status transitions.
        """

        # Detect previous status (if updating existing instance)
        if self.pk:
            old = SamplingEvent.objects.get(pk=self.pk)
            old_status = old.status
        else:
            old_status = None

        super().save(*args, **kwargs)

        # If just validated → calculate metrics
        if old_status != "validated" and self.status == "validated":
            self.update_event_metrics()

        # If leaving validated → clear metrics
        if old_status == "validated" and self.status != "validated":
            self.update_event_metrics()



    class Meta:
        ordering = ["-date", "beach__name"]
        indexes = [
            models.Index(fields=["status", "date"]),
            models.Index(fields=["beach", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.beach.name} - {self.date} ({self.get_status_display()})"

    from django.core.exceptions import ValidationError

    def submit(self):
        """Move a draft event into 'submitted' so it can be reviewed."""
        if self.status != "draft":
            raise ValidationError("Solo se puede enviar un evento en draft.")
        self.status = "submitted"
        self.save()

    def validate_event(self):
        """Accept a submitted event as scientifically valid; triggers metric recalculation via save()."""
        if self.status != "submitted":
            raise ValidationError("Solo se puede validar un evento enviado.")
        self.status = "validated"
        self.save()

    def reject(self):
        """Reject a submitted event; it will not count toward public/validated data."""
        if self.status != "submitted":
            raise ValidationError("Solo se puede rechazar un evento enviado.")
        self.status = "rejected"
        self.save()