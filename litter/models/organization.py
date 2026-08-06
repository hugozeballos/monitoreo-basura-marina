from django.db import models

class Organization(models.Model):
    """
    Entity (institution, school, NGO) responsible for one or more sampling events.
    """

    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100, blank=True, null=True)

    contact_name = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.name