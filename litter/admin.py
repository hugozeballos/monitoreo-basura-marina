from django.contrib import admin, messages
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    Beach,
    LitterType,
    SamplingMethod,
    SamplingEvent,
    SamplingUnit,
    UnitLitterCount,
    SamplingPhoto,
)
from django.contrib import admin





# -------------------------
# Inlines
# -------------------------

class SamplingPhotoInline(admin.TabularInline):
    model = SamplingPhoto
    extra = 0
    fields = ("image", "photo_kind", "caption", "uploaded_by", "created_at")
    readonly_fields = ("created_at",)


class UnitLitterCountInline(admin.TabularInline):
    model = UnitLitterCount
    extra = 0
    fields = ("litter_type", "count")
    autocomplete_fields = ("litter_type",)
    ordering = ("litter_type",)


class SamplingUnitInline(admin.TabularInline):
    model = SamplingUnit
    extra = 0
    fields = (
        "unit_kind",
        "transect_no",
        "station_no",
        "zone",
        "area_m2",
        "label",
        "notes",
        "created_at",
    )
    readonly_fields = ("created_at",)
    ordering = ("transect_no", "station_no", "id")


# -------------------------
# Admin actions (workflow)
# -------------------------

# -------------------------
# Additional Admin Actions
# generate SamplingUnits from method
# -------------------------


@admin.action(description="Generate SamplingUnits from method (selected events)")
def generate_units_for_events(modeladmin, request, queryset):
    total_created = 0
    failed = 0

    for ev in queryset:
        try:
            created = ev.generate_units_from_method(overwrite_area=False)
            total_created += created
        except ValidationError as e:
            failed += 1
            modeladmin.message_user(
                request,
                f"Event {ev.id} failed: {e}",
                level=messages.ERROR,
            )

    if failed == 0:
        modeladmin.message_user(
            request,
            f"OK: created {total_created} units across {queryset.count()} events.",
            level=messages.SUCCESS,
        )
    else:
        modeladmin.message_user(
            request,
            f"Partial: created {total_created} units; {failed} events failed (see errors).",
            level=messages.WARNING,
        )

@admin.action(description="Mark selected events as SUBMITTED")
def mark_events_submitted(modeladmin, request, queryset):
    for ev in queryset:
        ev.status = "submitted"
        ev.submitted_by = request.user
        ev.submitted_at = timezone.now()
        ev.save(update_fields=["status", "submitted_by", "submitted_at"])


@admin.action(description="Mark selected events as VALIDATED")
def mark_events_validated(modeladmin, request, queryset):
    for ev in queryset:
        ev.status = "validated"
        ev.reviewed_by = request.user
        ev.reviewed_at = timezone.now()
        ev.save()


@admin.action(description="Mark selected events as REJECTED")
def mark_events_rejected(modeladmin, request, queryset):
    for ev in queryset:
        ev.status = "rejected"
        ev.reviewed_by = request.user
        ev.reviewed_at = timezone.now()
        ev.save()


# -------------------------
# ModelAdmins
# -------------------------

@admin.register(Beach)
class BeachAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "region",
        "city",
        "is_active",
        "beach_type",
        "access_type",
        "created_at",
        "updated_at",
    )
    list_filter = ("country", "region", "is_active", "beach_type", "access_type")
    search_fields = ("name", "city", "region", "country")
    ordering = ("country", "region", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LitterType)
class LitterTypeAdmin(admin.ModelAdmin):
    list_display = ("label", "code", "is_active", "sort_order", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("label", "code")
    ordering = ("sort_order", "label")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SamplingMethod)
class SamplingMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(SamplingEvent)
class SamplingEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "date",
        "beach",
        "status",
        "sampling_method",
        "units_expected",
        "units_completed",
        "event_total_items",
        "event_density_items_per_m2",
        "submitted_at",
        "reviewed_at",
    )
    list_filter = ("status", "sampling_method", "date", "beach")
    search_fields = ("beach__name", "sampling_method__name")
    date_hierarchy = "date"
    autocomplete_fields = ("beach", "sampling_method")
    readonly_fields = ("created_at", "updated_at")

    inlines = (SamplingPhotoInline, SamplingUnitInline)

    actions = (mark_events_submitted, mark_events_validated, mark_events_rejected, generate_units_for_events)

    fieldsets = (
        ("Core", {
            "fields": ("beach", "date", "sampling_method", "method_params", "notes")
        }),
        ("Workflow", {
            "fields": (
                "status",
                "submitted_by",
                "submitted_at",
                "reviewed_by",
                "reviewed_at",
                "review_notes",
            )
        }),
        ("Optional persisted caches", {
            "fields": (
                "units_expected",
                "units_completed",
                "event_total_items",
                "event_area_m2",
                "event_density_items_per_m2",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(SamplingUnit)
class SamplingUnitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sampling_event",
        "unit_kind",
        "transect_no",
        "station_no",
        "zone",
        "area_m2",
        "label",
        "created_at",
    )
    list_filter = ("unit_kind", "zone")
    search_fields = ("sampling_event__beach__name", "label")
    autocomplete_fields = ("sampling_event",)
    readonly_fields = ("created_at",)
    inlines = (UnitLitterCountInline, SamplingPhotoInline)


@admin.register(UnitLitterCount)
class UnitLitterCountAdmin(admin.ModelAdmin):
    list_display = ("id", "sampling_unit", "litter_type", "count")
    list_filter = ("litter_type",)
    search_fields = ("sampling_unit__sampling_event__beach__name", "litter_type__label")
    autocomplete_fields = ("sampling_unit", "litter_type")


@admin.register(SamplingPhoto)
class SamplingPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "sampling_event", "sampling_unit", "photo_kind", "uploaded_by", "created_at")
    list_filter = ("photo_kind",)
    search_fields = ("caption",)
    autocomplete_fields = ("sampling_event", "sampling_unit", "uploaded_by")
    readonly_fields = ("created_at",)
