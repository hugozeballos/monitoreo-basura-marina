from django.test import TestCase
from django.urls import reverse

from litter.models import Beach, SamplingMethod, SamplingEvent


class SamplingWizardTests(TestCase):
    def setUp(self):
        self.beach = Beach.objects.create(name="Test Beach", country="CL", region="RM", city="Santiago", is_active=True)
        self.method = SamplingMethod.objects.create(
            code="m1",
            name="Transect Grid",
            is_active=True,
            default_params_schema={
                "n_transects": {"default": 2},
                "n_stations": {"default": 3},
            },
            unit_template={
                "layout": "transect_station_grid",
                "unit_kind": "transect_station",
                "transects": {"param": "n_transects", "default": 2},
                "stations_per_transect": {"param": "n_stations", "default": 3},
                "area_m2": {"default": 9},
                "label_format": "T{transect}-S{station}",
            },
        )

    def test_wizard_creates_event_only_at_end_and_generates_units(self):
        url = reverse("sampling_create")

        # Step 1
        r1 = self.client.get(url)
        self.assertEqual(r1.status_code, 200)

        post1 = {
            "sampling_event_wizard_view-current_step": "base",
            "base-beach": str(self.beach.pk),
            "base-date": "2026-02-01",
            "base-notes": "test",
        }
        r2 = self.client.post(url, data=post1)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(SamplingEvent.objects.count(), 0)

        # Step 2
        post2 = {
            "sampling_event_wizard_view-current_step": "method",
            "method-sampling_method": str(self.method.pk),
            "method-n_transects": "2",
            "method-n_stations": "3",
        }
        r3 = self.client.post(url, data=post2)
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(SamplingEvent.objects.count(), 0)

        # Step 3 (done)
        post3 = {
            "sampling_event_wizard_view-current_step": "confirm",
            "confirm-confirm": "on",
        }
        r4 = self.client.post(url, data=post3, follow=True)
        self.assertEqual(r4.status_code, 200)

        self.assertEqual(SamplingEvent.objects.count(), 1)
        event = SamplingEvent.objects.first()
        self.assertEqual(event.status, "draft")
        self.assertEqual(event.units_expected, 6)
        self.assertEqual(event.units.count(), 6)