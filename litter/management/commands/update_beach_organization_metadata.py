import csv
from django.core.management.base import BaseCommand
from litter.models import Beach

class Command(BaseCommand):
    help = "Update beach metadata fields from CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    def handle(self, *args, **options):
        path = options["csv_path"]

        updated = 0

        with open(path, encoding="latin-1") as f:
            reader = csv.DictReader(f, delimiter=";")

            for row in reader:
                beach_name = row["Beach"].strip()

                try:
                    beach = Beach.objects.get(name=beach_name)
                except Beach.DoesNotExist:
                    continue

                beach.zone_international = row["Organization"]


                beach.save()
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Updated {updated} beaches.")
        )
