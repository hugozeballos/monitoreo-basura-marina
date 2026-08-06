from django.db import models


class LitterType(models.Model):
    """
    Admin-manageable list of litter categories.
    Initial set will be seeded later; admin can add more.
    """

    code = models.SlugField(max_length=64, unique=True)
    label = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    # Optional: control ordering in forms/charts.
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "label"]

    def __str__(self) -> str:
        return self.label
