from django.conf import settings
from django.db import models

from .sampling_event import SamplingEvent
from .sampling_unit import SamplingUnit


class SamplingPhoto(models.Model):
    """
    Optional photos for events and/or units.
    Beach cover photo is mandatory (handled in Beach model).
    """

    PHOTO_KIND_CHOICES = [
        ("evidence", "Evidence"),
        ("site", "Site"),
        ("context", "Context"),
    ]

    # A photo can be attached to an event, a unit, or both.
    sampling_event = models.ForeignKey(
        SamplingEvent,
        on_delete=models.CASCADE,
        related_name="photos",
        null=True,
        blank=True,
    )
    sampling_unit = models.ForeignKey(
        SamplingUnit,
        on_delete=models.CASCADE,
        related_name="photos",
        null=True,
        blank=True,
    )

    image = models.ImageField(upload_to="sampling/photos/")
    photo_kind = models.CharField(
        max_length=16, choices=PHOTO_KIND_CHOICES, default="evidence"
    )
    caption = models.CharField(max_length=255, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_sampling_photos",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Photo {self.id} ({self.photo_kind})"
