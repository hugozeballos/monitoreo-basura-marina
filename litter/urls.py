from django.urls import path
from .views import map_view, map_view_v2, beaches_geojson
from .views.api import beaches_summary_api
from .views.api import beaches_summary_api_v2
from .views.views import BeachCreateView, SamplingEventUnitsView
from .views.views import SamplingEventCreateView
from .views.views import OrganizationCreateView
from .views.views import SamplingEventEntryView
from .views.views import SamplingEventListView
from .views.views import BeachListView
from .views.views import BeachDetailView
from .views.views import SamplingEventDetailView
from .views.views import submit_event, validate_event, reject_event
from .views.wizard import SamplingEventWizardView
from .views.views import beach_chart_api
from .views.views import CountryDetailView
from .views.views import country_chart_api
from .views.views import CountryListView
from .views.views import SamplingEventDeleteView



urlpatterns = [
    path("", map_view_v2, name="litter_map"),
    path("v2/", map_view_v2, name="litter_map_v2"), # new URL for the version 2 of the map view with filters
    path("api/beaches/", beaches_geojson, name="beaches_geojson"),
    path("api/beaches-summary/", beaches_summary_api, name="beaches-summary"),
    path("api/beaches-summary-v2/", beaches_summary_api_v2, name="beaches-summary-v2"),
    path("beach/create/", BeachCreateView.as_view(), name="beach_create"),
    path("sampling/create/", SamplingEventCreateView.as_view(), name="sampling_create"),
    path("organization/create/", OrganizationCreateView.as_view(), name="organization_create"),
    path("event/<int:pk>/units/", SamplingEventUnitsView.as_view(), name="sampling_event_units"),
    path("event/<int:pk>/entry/", SamplingEventEntryView.as_view(), name="sampling_event_entry"),
    path("events/", SamplingEventListView.as_view(), name="sampling_event_list"),
    path("beaches/", BeachListView.as_view(), name="beach_list"),
    path("beaches/<int:pk>/", BeachDetailView.as_view(), name="beach_detail"),
    path("event/<int:pk>/", SamplingEventDetailView.as_view(), name="sampling_event_detail"),
    path("event/<int:pk>/submit/", submit_event, name="sampling_event_submit"),
    path("event/<int:pk>/validate/", validate_event, name="sampling_event_validate"),
    path("event/<int:pk>/reject/", reject_event, name="sampling_event_reject"),
    path("sampling/create/wizard/", SamplingEventWizardView.as_view(), name="sampling_create_wizard"),
    path("api/beaches/<int:pk>/chart/", beach_chart_api, name="beach_chart_api"),
    path("country/<str:country>/", CountryDetailView.as_view(), name="country_detail"),
    path("api/country/<str:country>/chart/", country_chart_api, name="country_chart_api"),
    path("countries/", CountryListView.as_view(), name="country_list"),
    path("event/<int:pk>/delete/", SamplingEventDeleteView.as_view(), name="sampling_event_delete"),

]
