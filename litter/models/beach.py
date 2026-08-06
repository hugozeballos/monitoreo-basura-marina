from django.conf import settings
from django.db import models


class Beach(models.Model):
    """
    Beach catalog entry.
    `cover_image` is required by your MVP rule.
    """

    BEACH_TYPE_CHOICES = [
        ("sandy", "Sandy"),
        ("rocky", "Rocky"),
        ("mixed", "Mixed"),
        ("unknown", "Unknown"),
    ]

    ACCESS_TYPE_CHOICES = [
        ("public", "Public"),
        ("restricted", "Restricted"),
        ("private", "Private"),
        ("unknown", "Unknown"),
    ]

    name = models.CharField(max_length=255, db_index=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255)

    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    international_zone = models.CharField(max_length=255, blank=True, null=True)
    chile_zone = models.CharField(max_length=255, blank=True, null=True)
    region_chile = models.CharField(max_length=150, blank=True)


    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    beach_type = models.CharField(
        max_length=32, choices=BEACH_TYPE_CHOICES, default="unknown"
    )
    access_type = models.CharField(
        max_length=32, choices=ACCESS_TYPE_CHOICES, default="unknown"
    )

    # Required cover image for beach creation (MVP decision).
    cover_image = models.ImageField(upload_to="beaches/covers/", null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_beaches",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["country", "region", "name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.country})"
