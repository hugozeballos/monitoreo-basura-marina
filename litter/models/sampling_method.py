from django.db import models


class SamplingMethod(models.Model):
    """
    Catalog of sampling methods.
    `default_params_schema` and `unit_template` are JSON descriptors (no logic here yet).
    """

    code = models.SlugField(blank=True, null=True, max_length=64, unique=True)
    name = models.CharField(max_length=255,blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    default_params_schema = models.JSONField(blank=True, null=True)
    unit_template = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
