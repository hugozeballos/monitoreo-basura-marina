from multiprocessing import context

from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from urllib3 import request
from litter.models import Beach, SamplingEvent, Organization
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from django.urls import reverse
from django.core.exceptions import ValidationError
from litter.models import Beach, SamplingEvent, Organization
from litter.models.sampling_unit import SamplingUnit  # o import relativo según tu estructura
from litter.forms import SamplingEventForm
import json
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from litter.models import SamplingEvent, SamplingUnit, LitterType, UnitLitterCount
from django.views.generic import DetailView
from django.db import models


def map_view(request):
    return render(request, "litter/map.html")

## version 2 of the map view, which will use the new API endpoint with filters
def map_view_v2(request):
    return render(request, "litter/map_v2.html")


def beaches_geojson(request):
    """Lightweight beach list (id/name/lat/lng) for placing markers on the base map."""
    beaches = Beach.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        is_active=True
    )

    data = [
        {
            "id": beach.id,
            "name": beach.name,
            "lat": beach.latitude,
            "lng": beach.longitude,
        }
        for beach in beaches
    ]

    return JsonResponse(data, safe=False)

class BeachCreateView(CreateView):
    model = Beach
    fields = [
        "name",
        "country",
        "region",
        "city",
        "latitude",
        "longitude",
        "beach_type",
        "access_type",
        "is_active",
        "description",
        "cover_image",
    ]
    template_name = "litter/beach_form.html"
    success_url = reverse_lazy("litter_map_v2")

class SamplingEventCreateView(CreateView):
    """Non-wizard event creation: creates the event, then immediately generates its units from the chosen method."""

    model = SamplingEvent
    form_class = SamplingEventForm
    template_name = "litter/sampling_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # When method changes (GET request)
        if self.request.method == "GET" and "sampling_method" in self.request.GET:
            kwargs["data"] = self.request.GET

        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)

        try:
            self.object.generate_units_from_method()
        except ValidationError as e:
            form.add_error(None, e.message)
            return self.form_invalid(form)

        return response

    def get_success_url(self):
        return reverse("sampling_event_units", kwargs={"pk": self.object.pk})
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from litter.models import SamplingMethod

        methods = SamplingMethod.objects.all()

        context["methods_schema_json"] = json.dumps({
            str(m.id): m.default_params_schema
            for m in methods
            if m.default_params_schema
        })

        return context



class SamplingEventUnitsView(ListView):
    model = SamplingUnit
    template_name = "litter/event_units.html"
    context_object_name = "units"

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(SamplingEvent, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            SamplingUnit.objects
            .filter(sampling_event=self.event)
            .order_by("transect_no", "station_no", "id")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["event"] = self.event
        return ctx
    
# litter/views/views.py



class OrganizationCreateView(CreateView):
    model = Organization
    fields = ["name", "contact_email", "contact_phone"]
    template_name = "litter/organization_form.html"
    success_url = reverse_lazy("sampling_create")


class SamplingEventEntryView(View):
    """Data-entry grid (unit x litter type) for filling in counts of a non-validated event."""

    template_name = "litter/event_entry.html"

    def get(self, request, pk):
        event = get_object_or_404(SamplingEvent, pk=pk)
        units = SamplingUnit.objects.filter(sampling_event=event).order_by("transect_no", "station_no")
        litter_types = LitterType.objects.all()

        # Load existing counts
        existing_counts = UnitLitterCount.objects.filter(sampling_unit__in=units)

        # Build a safe matrix structure

        units_data = []

        for unit in units:
            row = {
                "unit": unit,
                "counts": []
            }

            for lt in litter_types:
                existing = existing_counts.filter(
                    sampling_unit=unit,
                    litter_type=lt
                ).first()

                row["counts"].append({
                    "litter_type": lt,
                    "value": existing.count if existing else ""
                })

            units_data.append(row)

        return render(request, self.template_name, {
            "event": event,
            "units_data": units_data,
            "litter_types": litter_types,   # ← IMPORTANTE
        })

    def post(self, request, pk):
        event = get_object_or_404(SamplingEvent, pk=pk)
        units = SamplingUnit.objects.filter(sampling_event=event)
        litter_types = LitterType.objects.all()

        for unit in units:
            for lt in litter_types:
                field_name = f"count_{unit.id}_{lt.id}"
                value = request.POST.get(field_name)

                if value is not None and value != "":
                    count_value = int(value)

                    obj, created = UnitLitterCount.objects.update_or_create(
                        sampling_unit=unit,
                        litter_type=lt,
                        defaults={"count": count_value}
                    )

        return redirect("sampling_event_units", pk=event.pk)
    
    def get_event(self):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(SamplingEvent, pk=self.kwargs["pk"])
    
    def dispatch(self, request, *args, **kwargs):
        event = self.get_event()

        if event.status == "validated":
            messages.warning(
                request,
                "Este monitoreo ya fue VALIDADO. No puede ser editado."
            )
            return redirect("sampling_event_detail", pk=event.pk)            

        return super().dispatch(request, *args, **kwargs)
        
class SamplingEventListView(ListView):
    model = SamplingEvent
    template_name = "litter/event_list.html"
    context_object_name = "events"
    ordering = ["-date"]


class BeachListView(View):
    template_name = "litter/beach_list.html"

    def get(self, request):
        from django.db.models import Count, Avg, Q

        beaches_qs = (
            Beach.objects
            .filter(is_active=True)
            .annotate(
                n_events=Count(
                    "events", distinct=True,
                    filter=Q(events__status="validated")
                ),
                avg_density=Avg(
                    "events__event_density_items_per_m2",
                    filter=Q(events__status="validated")
                ),
                last_event_org_id=models.Subquery(
                    SamplingEvent.objects
                    .filter(beach=models.OuterRef("pk"), status="validated")
                    .order_by("-date")
                    .values("organization_id")[:1]
                )
            )
            .order_by("country", "name")
        )

        countries = (
            Beach.objects.filter(is_active=True)
            .values_list("country", flat=True)
            .distinct().order_by("country")
        )

        organizations = (
            Organization.objects.filter(
                events__status="validated"
            ).distinct().order_by("name")
        )

        return render(request, self.template_name, {
            "beaches":       beaches_qs,
            "countries":     countries,
            "organizations": organizations,
        })
    

class SamplingEventDetailView(DetailView):
    model = SamplingEvent
    template_name = "litter/event_detail.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        units = self.object.units.all()
        total_units = units.count()

        context["total_units"] = total_units
        context["units"] = units

        return context
    
    
# --- FUNCTION BASED VIEWS (transiciones de estado) ---
from django.shortcuts import redirect, get_object_or_404
from litter.models import SamplingEvent

def submit_event(request, pk):
    event = get_object_or_404(SamplingEvent, pk=pk)
    event.submit()
    return redirect("sampling_event_detail", pk=pk)

def validate_event(request, pk):
    event = get_object_or_404(SamplingEvent, pk=pk)
    event.validate_event()
    return redirect("sampling_event_detail", pk=pk)

def reject_event(request, pk):
    event = get_object_or_404(SamplingEvent, pk=pk)
    event.reject()
    return redirect("sampling_event_detail", pk=pk)




# Ampliar BeachDetailView.get_context_data — reemplazar el método completo:

class BeachDetailView(DetailView):
    model = Beach
    template_name = "litter/beach_detail.html"
    context_object_name = "beach"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        events = self.object.events.filter(status="validated").order_by("-date")
        all_events = self.object.events.all().order_by("-date")

        # ── Métricas históricas ──────────────────────────────────────────
        total_items = events.aggregate(total=Sum("event_total_items"))["total"] or 0
        total_area  = events.aggregate(total=Sum("event_area_m2"))["total"] or 0

        context["events"]      = all_events
        context["total_items"] = total_items
        context["total_area"]  = total_area
        context["avg_density"] = total_items / total_area if total_area else 0

        # ── Doughnut: composición global por litter_type ─────────────────
        composition_qs = (
            UnitLitterCount.objects
            .filter(sampling_unit__sampling_event__in=events)
            .values("litter_type__label")
            .annotate(total=Sum("count"))
            .order_by("-total")
        )
        composition = {
            row["litter_type__label"]: row["total"]
            for row in composition_qs
            if row["total"] and row["total"] > 0
        }
        context["chart_labels"]   = list(composition.keys())
        context["chart_values"]   = list(composition.values())

        # ── Stacked bar: por transecto Y por estación ─────────────────────
        from collections import defaultdict

        unit_qs = (
            UnitLitterCount.objects
            .filter(sampling_unit__sampling_event__in=events)
            .values(
                "sampling_unit__transect_no",
                "sampling_unit__station_no",
                "sampling_unit__area_m2",
                "litter_type__label",
            )
            .annotate(total=Sum("count"))
        )

        litter_labels = list(composition.keys())

        # Matrices por transecto (densidad)
        transect_data = defaultdict(lambda: defaultdict(float))
        transect_area = defaultdict(float)
        # Matrices por estacion (densidad)
        station_data  = defaultdict(lambda: defaultdict(float))
        station_area  = defaultdict(float)

        for row in unit_qs:
            t    = row["sampling_unit__transect_no"]
            s    = row["sampling_unit__station_no"]
            area = row["sampling_unit__area_m2"] or 1
            lt   = row["litter_type__label"]
            cnt  = row["total"] or 0

            if t is not None:
                transect_data[t][lt] += cnt
                transect_area[t]     += area
            if s is not None:
                station_data[s][lt]  += cnt
                station_area[s]      += area

        transects_set = sorted(transect_data.keys())
        stations_set  = sorted(station_data.keys())

        # Densidad por transecto
        transect_matrix = [
            {
                "litter_type": lt,
                "data": [
                    round(transect_data[t][lt] / transect_area[t], 4) if transect_area[t] else 0
                    for t in transects_set
                ]
            }
            for lt in litter_labels
        ]

        # Densidad por estación
        station_matrix = [
            {
                "litter_type": lt,
                "data": [
                    round(station_data[s][lt] / station_area[s], 4) if station_area[s] else 0
                    for s in stations_set
                ]
            }
            for lt in litter_labels
        ]

        context["chart_labels"]        = list(composition.keys())
        context["chart_values"]        = list(composition.values())
        context["transect_labels"]     = [f"T{t}" for t in transects_set]
        context["transect_matrix"]     = transect_matrix
        context["station_labels"]      = [f"S{s}" for s in stations_set]
        context["station_matrix"]      = station_matrix
        context["has_transect_data"]   = len(transects_set) > 0

        context["chart_labels_json"]       = json.dumps(context["chart_labels"])
        context["chart_values_json"]       = json.dumps(context["chart_values"])
        context["transect_labels_json"]    = json.dumps(context["transect_labels"])
        context["transect_matrix_json"]    = json.dumps(context["transect_matrix"])
        context["station_labels_json"]     = json.dumps(context["station_labels"])
        context["station_matrix_json"]     = json.dumps(context["station_matrix"])


        # ── Lista de playas para el comparador ───────────────────────────
        context["all_beaches"] = (
            Beach.objects
            .filter(is_active=True)
            .exclude(pk=self.object.pk)
            .order_by("country", "name")
            .values("id", "name", "country")
        )

        return context


# ── API JSON para el comparador ──────────────────────────────────────────
def beach_chart_api(request, pk):
    from collections import defaultdict
    beach  = get_object_or_404(Beach, pk=pk, is_active=True)
    events = SamplingEvent.objects.filter(beach=beach, status="validated")

    # ── Doughnut ────────────────────────────────────────────────────────
    composition_qs = (
        UnitLitterCount.objects
        .filter(sampling_unit__sampling_event__in=events)
        .values("litter_type__label")
        .annotate(total=Sum("count"))
        .order_by("-total")
    )
    composition = {
        row["litter_type__label"]: row["total"]
        for row in composition_qs
        if row["total"] and row["total"] > 0
    }

    # ── Barras por transecto y estación (densidad) ───────────────────────
    unit_qs = (
        UnitLitterCount.objects
        .filter(sampling_unit__sampling_event__in=events)
        .values(
            "sampling_unit__transect_no",
            "sampling_unit__station_no",
            "sampling_unit__area_m2",
            "litter_type__label",
        )
        .annotate(total=Sum("count"))
    )

    litter_labels = list(composition.keys())
    transect_data = defaultdict(lambda: defaultdict(float))
    transect_area = defaultdict(float)
    station_data  = defaultdict(lambda: defaultdict(float))
    station_area  = defaultdict(float)

    for row in unit_qs:
        t    = row["sampling_unit__transect_no"]
        s    = row["sampling_unit__station_no"]
        area = row["sampling_unit__area_m2"] or 1
        lt   = row["litter_type__label"]
        cnt  = row["total"] or 0
        if t is not None:
            transect_data[t][lt] += cnt
            transect_area[t]     += area
        if s is not None:
            station_data[s][lt]  += cnt
            station_area[s]      += area

    transects_set = sorted(transect_data.keys())
    stations_set  = sorted(station_data.keys())

    return JsonResponse({
        "beach_name":      beach.name,
        "country":         beach.country,
        "labels":          list(composition.keys()),
        "values":          list(composition.values()),
        "transect_labels": [f"T{t}" for t in transects_set],
        "transect_matrix": [
            {"litter_type": lt, "data": [
                round(transect_data[t][lt] / transect_area[t], 4) if transect_area[t] else 0
                for t in transects_set
            ]} for lt in litter_labels
        ],
        "station_labels":  [f"S{s}" for s in stations_set],
        "station_matrix":  [
            {"litter_type": lt, "data": [
                round(station_data[s][lt] / station_area[s], 4) if station_area[s] else 0
                for s in stations_set
            ]} for lt in litter_labels
        ],
    })
class CountryDetailView(View):
    template_name = "litter/country_detail.html"

    def get(self, request, country):
        beaches = (
            Beach.objects
            .filter(country=country, is_active=True)
            .order_by("name")
        )
        if not beaches.exists():
            from django.http import Http404
            raise Http404

        # ── Stacked bar: densidad por playa, apilada por litter_type ──
        validated_events = SamplingEvent.objects.filter(
            beach__country=country,
            status="validated"
        )

                # Para cada playa: promedio de densidad por litter_type entre todos sus eventos validados
        beach_events = {}
        for event in validated_events.select_related("beach"):
            b = event.beach.name
            if b not in beach_events:
                beach_events[b] = []
            beach_events[b].append(event)

        beach_names = sorted(beach_events.keys())

        composition_qs = (
            UnitLitterCount.objects
            .filter(sampling_unit__sampling_event__in=validated_events)
            .values(
                "sampling_unit__sampling_event__beach__name",
                "sampling_unit__sampling_event__id",
                "sampling_unit__sampling_event__event_area_m2",
                "litter_type__label",
            )
            .annotate(total=Sum("count"))
        )

        # Agrupar por playa → evento → litter_type
        # estructura: {beach: {event_id: {lt: count, _area: m2}}}
        from collections import defaultdict
        event_data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        event_area = {}

        for row in composition_qs:
            b       = row["sampling_unit__sampling_event__beach__name"]
            eid     = row["sampling_unit__sampling_event__id"]
            lt      = row["litter_type__label"]
            total   = row["total"] or 0
            area    = row["sampling_unit__sampling_event__event_area_m2"] or 1
            event_data[b][eid][lt] = total
            event_area[(b, eid)]   = area

        litter_types = sorted({row["litter_type__label"] for row in composition_qs})

        # Para cada playa: promedio de densidad por litter_type entre sus eventos
        matrix = {}
        for b in beach_names:
            matrix[b] = {}
            for lt in litter_types:
                densities = []
                for eid, lt_counts in event_data[b].items():
                    area = event_area.get((b, eid), 1)
                    count = lt_counts.get(lt, 0)
                    densities.append(count / area if area > 0 else 0)
                matrix[b][lt] = round(sum(densities) / len(densities), 4) if densities else 0

        bar_datasets = [
            {"litter_type": lt, "data": [matrix[b][lt] for b in beach_names]}
            for lt in litter_types
        ]
        # ── Tabla de instituciones ────────────────────────────────────
        from django.db.models import Count
        institutions = (
            SamplingEvent.objects
            .filter(beach__country=country, status="validated", organization__isnull=False)
            .values("organization__name")
            .annotate(
                n_events=Count("id"),
                n_beaches=Count("beach", distinct=True)
            )
            .order_by("-n_beaches")
        )

        import json
        context = {
            "country":        country,
            "beaches":        beaches,
            "institutions":   institutions,
            "bar_beach_names_json":  json.dumps(beach_names),
            "bar_datasets_json":     json.dumps(bar_datasets),
            "litter_types_json":     json.dumps(litter_types),
            "has_data":              len(beach_names) > 0,

        }
        return render(request, self.template_name, context)
    
def country_chart_api(request, country):
    from collections import defaultdict

    validated_events = SamplingEvent.objects.filter(
        beach__country=country, status="validated"
    )
    if not validated_events.exists():
        from django.http import Http404
        raise Http404

    composition_qs = (
        UnitLitterCount.objects
        .filter(sampling_unit__sampling_event__in=validated_events)
        .values(
            "sampling_unit__sampling_event__beach__name",
            "sampling_unit__sampling_event__id",
            "sampling_unit__sampling_event__event_area_m2",
            "litter_type__label",
        )
        .annotate(total=Sum("count"))
    )

    event_data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    event_area = {}
    for row in composition_qs:
        b     = row["sampling_unit__sampling_event__beach__name"]
        eid   = row["sampling_unit__sampling_event__id"]
        lt    = row["litter_type__label"]
        area  = row["sampling_unit__sampling_event__event_area_m2"] or 1
        event_data[b][eid][lt] = row["total"] or 0
        event_area[(b, eid)]   = area

    beach_names  = sorted(event_data.keys())
    litter_types = sorted({row["litter_type__label"] for row in composition_qs})

    matrix = {}
    for b in beach_names:
        matrix[b] = {}
        for lt in litter_types:
            densities = []
            for eid, lt_counts in event_data[b].items():
                area  = event_area.get((b, eid), 1)
                count = lt_counts.get(lt, 0)
                densities.append(count / area if area > 0 else 0)
            matrix[b][lt] = round(sum(densities) / len(densities), 4) if densities else 0

    return JsonResponse({
        "country":     country,
        "beach_names": beach_names,
        "datasets": [
            {"litter_type": lt, "data": [matrix[b][lt] for b in beach_names]}
            for lt in litter_types
        ],
    })

COUNTRY_FLAGS = {
    "Chile": "🇨🇱", "Colombia": "🇨🇴", "Costa Rica": "🇨🇷",
    "Ecuador": "🇪🇨", "El Salvador": "🇸🇻", "Guatemala": "🇬🇹",
    "México": "🇲🇽", "Nicaragua": "🇳🇮", "Panamá": "🇵🇦",
    "Perú": "🇵🇪", "Honduras": "🇭🇳", "Bolivia": "🇧🇴",
    "Brasil": "🇧🇷", "Argentina": "🇦🇷", "Uruguay": "🇺🇾",
    "Venezuela": "🇻🇪", "Paraguay": "🇵🇾",
}

class CountryListView(View):
    def get(self, request):
        from django.db.models import Count

        country_data = (
            Beach.objects
            .filter(is_active=True)
            .values("country")
            .annotate(n_beaches=Count("id", distinct=True))
            .order_by("country")
        )

        event_counts = {
            row["beach__country"]: row["total"]
            for row in SamplingEvent.objects
                .filter(status="validated")
                .values("beach__country")
                .annotate(total=Count("id"))
        }

        max_events = max((event_counts.get(c["country"], 0) for c in country_data), default=1)

        countries = []
        for row in country_data:
            name     = row["country"]
            n_events = event_counts.get(name, 0)
            pct      = round(n_events / max_events * 100) if max_events else 0
            # Activity level relative to the busiest country: top third = Alto, bottom third = Bajo.
            if pct >= 66:   level = "Alto"
            elif pct >= 33: level = "Medio"
            else:           level = "Bajo"
            countries.append({
                "name":         name,
                "flag":         COUNTRY_FLAGS.get(name, "🌍"),
                "n_beaches":    row["n_beaches"],
                "n_events":     n_events,
                "activity_pct": pct,
                "activity_level": level,
            })

        return render(request, "litter/country_list.html", {"countries": countries})


from django.views.generic import DeleteView    

class SamplingEventDeleteView(DeleteView):
    model = SamplingEvent
    template_name = "litter/event_confirm_delete.html"
    context_object_name = "event"

    def get_success_url(self):
        return reverse_lazy("beach_detail", kwargs={"pk": self.object.beach.pk})