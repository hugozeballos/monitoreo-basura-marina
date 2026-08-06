import csv
import unicodedata
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from litter.models import (
    Beach,
    SamplingEvent,
    SamplingUnit,
    UnitLitterCount,
    LitterType,
    SamplingMethod,
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


def normalize_text(text):
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text.strip())


class Command(BaseCommand):
    help = "Full Macrolitter Import with Beach Metadata"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    def handle(self, *args, **options):

        path = options["csv_path"]

        sampling_method = SamplingMethod.objects.get(
            name="Grid Quadrats (Transect x Station)"
        )

        processed_events = set()

        with open(path, encoding="latin-1") as f:
            reader = csv.DictReader(f, delimiter=";")

            for row in reader:

                beach_name = normalize_text(row.get("Beach"))
                country = normalize_text(row.get("Country"))
                city = normalize_text(row.get("City"))
                region = normalize_text(row.get("Region"))
                international_zone = normalize_text(row.get("Zone International"))
                chile_zone = normalize_text(row.get("Zone Chile"))
                region_chile = normalize_text(row.get("Region Chile"))

                if not beach_name:
                    continue

                date = timezone.datetime.strptime(
                    row["Date"].strip(),
                    "%d-%m-%Y"
                ).date()

                lat = parse_number(row["Latitude"])
                lon = parse_number(row["Longitude"])

                # ------------------------
                # BEACH
                # ------------------------

                beach, created = Beach.objects.get_or_create(
                    name=beach_name,
                    defaults={
                        "country": country,
                        "city": city,
                        "region": region,
                        "international_zone": international_zone,
                        "chile_zone": chile_zone,
                        "region_chile": region_chile,
                        "latitude": lat,
                        "longitude": lon,
                    },
                )

                # Update metadata if empty
                updated = False

                fields_to_update = {
                    "country": country,
                    "city": city,
                    "region": region,
                    "international_zone": international_zone,
                    "chile_zone": chile_zone,
                    "region_chile": region_chile,
                }

                for field, value in fields_to_update.items():
                    if not getattr(beach, field) and value:
                        setattr(beach, field, value)
                        updated = True

                if updated:
                    beach.save()

                # ------------------------
                # EVENT
                # ------------------------

                event, _ = SamplingEvent.objects.get_or_create(
                    beach=beach,
                    date=date,
                    sampling_method=sampling_method,
                    defaults={"status": "validated"},
                )

                processed_events.add(event.id)

                transect = int(row["Transect"])
                station = int(row["Station"])

                values = [parse_number(row[col]) for col in CATEGORY_COLUMNS]
                if not any(v is not None for v in values):
                    continue

                unit, _ = SamplingUnit.objects.get_or_create(
                    sampling_event=event,
                    transect_no=transect,
                    station_no=station,
                    defaults={"area_m2": 9.0},
                )

                for col in CATEGORY_COLUMNS:
                    value = parse_number(row[col])
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

        # Recalculate metrics
        for event_id in processed_events:
            SamplingEvent.objects.get(id=event_id).update_event_metrics()

        self.stdout.write(self.style.SUCCESS("Import completed successfully"))
