from django.db.models import Sum
from litter.models import Beach, SamplingEvent, UnitLitterCount


def get_beaches_summary(filters=None):
    """
    Returns scientific summary for all active beaches
    based on the latest validated SamplingEvent.
    Adds contamination_level based on density distribution.
    """

    beaches = Beach.objects.filter(is_active=True)

    result = []

    # -------------------------
    # 1️⃣ Build base data
    # -------------------------
    for beach in beaches:

        event_qs = SamplingEvent.objects.filter(
            beach=beach,
            status="validated"
        )

        if filters:
            if filters.get("year"):
                event_qs = event_qs.filter(date__year=filters["year"])

            if filters.get("method_id"):
                event_qs = event_qs.filter(method_id=filters["method_id"])

            if filters.get("country"):
                event_qs = event_qs.filter(beach__country=filters["country"])

        last_event = event_qs.order_by("-date").first()

        
        if not last_event:
            continue

        composition_qs = (
            UnitLitterCount.objects
            .filter(sampling_unit__sampling_event=last_event)
            .values("litter_type__label")
            .annotate(total=Sum("count"))
        )

        composition = {
            row["litter_type__label"]: row["total"]
            for row in composition_qs
            if row["total"] and row["total"] > 0
        }


        result.append({
            "id": beach.id,
            "name": beach.name,
            "country": beach.country,
            "latitude": beach.latitude,
            "longitude": beach.longitude,
            "last_event_date": last_event.date,
            "organization": last_event.organization_id if last_event.organization else None,
            "total_items": last_event.event_total_items,
            "density": last_event.event_density_items_per_m2 or 0,
            "composition": composition,
        })

    if filters and filters.get("min_density"):
        try:
            min_d = float(filters["min_density"])
            result = [item for item in result if item["density"] >= min_d]
        except ValueError:
            pass


    # -------------------------
    # 2️⃣ Compute contamination levels
    # -------------------------
    densities = [item["density"] for item in result if item["density"] is not None]

    if not densities:
        return {
            "stats": {
                "total_beaches": 0,
                "total_events": total_events,
                "total_countries": total_countries,
                "total_organizations": total_organizations,
            },
            "beaches": [],
        }

    min_density_val = min(densities)
    max_density_val = max(densities)

    if min_density_val == max_density_val:
        # All beaches same density → classify as medium
        for item in result:
            item["contamination_level"] = "medium"

    range_size = (max_density_val - min_density_val) / 3

    low_threshold = min_density_val + range_size
    medium_threshold = min_density_val + (2 * range_size)

    for item in result:
        density = item["density"]

        if density <= low_threshold:
            level = "low"
        elif density <= medium_threshold:
            level = "medium"
        else:
            level = "high"

        item["contamination_level"] = level

    # -------------------------
    # 3️⃣ Global stats (historical, filter-aware)
    # -------------------------

    events_stats_qs = SamplingEvent.objects.filter(status="validated")

    if filters:
        if filters.get("year"):
            events_stats_qs = events_stats_qs.filter(date__year=filters["year"])

        if filters.get("method_id"):
            events_stats_qs = events_stats_qs.filter(method_id=filters["method_id"])

        if filters.get("country"):
            events_stats_qs = events_stats_qs.filter(beach__country=filters["country"])

    total_events = events_stats_qs.count()

    total_countries = (
        events_stats_qs
        .values("beach__country")
        .distinct()
        .count()
    )

    total_organizations = (
        events_stats_qs
        .exclude(organization__isnull=True)
        .values("organization")
        .distinct()
        .count()
    )

    total_beaches = len(result)

    # -------------------------
    # 4️⃣ Available filter values
    # -------------------------

    available_years = (
        SamplingEvent.objects
        .filter(status="validated")
        .dates("date", "year")
    )

    available_years = [d.year for d in available_years]

    available_countries = (
        Beach.objects
        .filter(events__status="validated")
        .values_list("country", flat=True)
        .distinct()
    )

    return {
    "stats": {
        "total_beaches": total_beaches,
        "total_events": total_events,
        "total_countries": total_countries,
        "total_organizations": total_organizations,
    },
    "beaches": result,
        "filters": {
        "years": sorted(available_years, reverse=True),
        "countries": sorted(list(available_countries)),
    }
}

