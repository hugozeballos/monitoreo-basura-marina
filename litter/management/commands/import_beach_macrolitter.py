import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.utils import timezone
from litter.models import (
    Beach,
    SamplingEvent,
    SamplingUnit,
    UnitLitterCount,
    LitterType,
    Organization,
)

CATEGORY_COLUMNS = [
    "Papers",
    "Cigarette butts",
    "Plastics",
    "Metals",
    "Glass",
    "Face masks",
    "Worked wood",
    "Others",
]

def parse_number(value):
    if value in (None, "", "NA"):
        return None
    value = value.replace(",", ".")
    return Decimal(value)

def normalize_text(value):
    if not value:
        return None
    return value.strip()

class Command(BaseCommand):
    """Import a macrolitter CSV into Beach/SamplingEvent/SamplingUnit/UnitLitterCount (no beach metadata updates)."""

    help = "Import Beach Macrolitter dataset"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    def handle(self, *args, **options):
        path = options["csv_path"]

        with open(path, encoding="latin-1") as f:
            reader = csv.DictReader(f, delimiter=";")
            from litter.models import SamplingMethod


            sampling_method = SamplingMethod.objects.get(
                name="Grid Quadrats (Transect x Station)"
            )

            if not sampling_method:
                raise Exception("No SamplingMethod exists. Create one in admin first.")
            
            processed_events = set()

            for row in reader:

                # -------------------------
                # 1️⃣ Basic row data
                # -------------------------
                beach_name = normalize_text(row.get("Beach"))
                date_str = normalize_text(row.get("Date"))

                if not beach_name or not date_str:
                    continue

                date = timezone.datetime.strptime(date_str, "%d-%m-%Y").date()

                lat = parse_number(row.get("Latitude"))
                lon = parse_number(row.get("Longitude"))

                # -------------------------
                # 2️⃣ Metadata fields
                # -------------------------
                country = normalize_text(row.get("Country"))
                city = normalize_text(row.get("City"))
                international_zone = normalize_text(row.get("Zone International"))
                chile_zone = normalize_text(row.get("Zone Chile"))
                region_chile = normalize_text(row.get("Region Chile"))
                organization_name = normalize_text(row.get("Organization"))

                # -------------------------
                # 3️⃣ Organization
                # -------------------------
                organization = None
                if organization_name:
                    organization, _ = Organization.objects.get_or_create(
                        name=organization_name,
                        defaults={"country": country},
                    )

                # -------------------------
                # 4️⃣ Beach (create or update)
                # -------------------------
                beach, created = Beach.objects.get_or_create(
                    name=beach_name,
                    defaults={
                        "latitude": lat,
                        "longitude": lon,
                        "country": country or "",
                        "city": city,
                        "international_zone": international_zone,
                        "chile_zone": chile_zone,
                        "region_chile": region_chile,
                    },
                )

                # 🔵 Si ya existía, actualizar metadata si está vacía
                if not created:
                    updated = False

                    if not beach.country and country:
                        beach.country = country
                        updated = True

                    if not beach.city and city:
                        beach.city = city
                        updated = True

                    if not beach.international_zone and international_zone:
                        beach.international_zone = international_zone
                        updated = True

                    if not beach.chile_zone and chile_zone:
                        beach.chile_zone = chile_zone
                        updated = True

                    if not beach.region_chile and region_chile:
                        beach.region_chile = region_chile
                        updated = True

                    if updated:
                        beach.save()

                # -------------------------
                # 5️⃣ SamplingEvent
                # -------------------------
                event, created_event = SamplingEvent.objects.get_or_create(
                    beach=beach,
                    date=date,
                    sampling_method=sampling_method,
                    defaults={
                        "status": "validated",
                        "organization": organization,
                    },
                )

                # 🔵 If event already existed, ensure organization is set
                if not created_event and organization and not event.organization:
                    event.organization = organization
                    event.save(update_fields=["organization"])

                # -------------------------
                # 6️⃣ Units and litter counts
                # -------------------------
                transect = int(row.get("Transect"))
                station = int(row.get("Station"))

                values = [parse_number(row.get(col)) for col in CATEGORY_COLUMNS]

                if not any(v is not None for v in values):
                    continue

                unit, _ = SamplingUnit.objects.get_or_create(
                    sampling_event=event,
                    transect_no=transect,
                    station_no=station,
                    defaults={"area_m2": 9.0},
                )

                for col in CATEGORY_COLUMNS:
                    value = parse_number(row.get(col))
                    if value is None:
                        continue

                    litter_type, _ = LitterType.objects.get_or_create(
                        label=col,
                        defaults={
                            "code": col.lower().replace(" ", "_"),
                            "is_active": True,
                        },
                    )

                    UnitLitterCount.objects.update_or_create(
                        sampling_unit=unit,
                        litter_type=litter_type,
                        defaults={"count": int(value)},
                    )
                    
            for event_id in processed_events:
                event = SamplingEvent.objects.get(id=event_id)
                event.update_event_metrics()

        self.stdout.write(self.style.SUCCESS("Import completed"))
