from __future__ import annotations

from typing import Any, Dict

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from formtools.wizard.views import SessionWizardView

from litter.forms_wizard import Step1BaseInfoForm, Step2MethodForm, Step3ConfirmForm
from litter.models import SamplingEvent
from litter.services.sampling_preview import compute_preview


FORMS = [
    ("base", Step1BaseInfoForm),
    ("method", Step2MethodForm),
    ("confirm", Step3ConfirmForm),
]


TEMPLATES = {
    "base": "litter/wizard/sampling_wizard_base.html",
    "method": "litter/wizard/sampling_wizard_method.html",
    "confirm": "litter/wizard/sampling_wizard_confirm.html",
}


class SamplingEventWizardView(SessionWizardView):
    """
    3-step wizard (base info -> method -> confirm) that only creates the
    SamplingEvent and its units at the final 'confirm' step, not before.
    """

    form_list = FORMS

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def get_context_data(self, form, **kwargs):
        ctx = super().get_context_data(form=form, **kwargs)

        # Preview solo en confirm
        if self.steps.current == "confirm":
            base = self.get_cleaned_data_for_step("base") or {}
            method_step = self.get_cleaned_data_for_step("method") or {}

            sampling_method = method_step.get("sampling_method")
            method_params: Dict[str, Any] = {}

            # Reconstruir params dinámicos (solo si hay método)
            if sampling_method and sampling_method.default_params_schema:
                for k in sampling_method.default_params_schema.keys():
                    if k in method_step and method_step[k] is not None:
                        method_params[k] = method_step[k]

            try:
                preview = compute_preview(sampling_method, method_params) if sampling_method else None
            except ValidationError as e:
                preview = None
                ctx["preview_error"] = str(e)

            ctx["base_data"] = base
            ctx["method_data"] = method_step
            ctx["preview"] = preview

        return ctx

    def done(self, form_list, **kwargs):
        base = self.get_cleaned_data_for_step("base") or {}
        method_step = self.get_cleaned_data_for_step("method") or {}

        sampling_method = method_step["sampling_method"]

        # Construir method_params respetando default_params_schema (no asumir nombres)
        method_params: Dict[str, Any] = {}
        schema = sampling_method.default_params_schema or {}
        for k in schema.keys():
            if k in method_step and method_step[k] is not None:
                method_params[k] = method_step[k]

        # Crear evento SOLO al final
        event = SamplingEvent.objects.create(
            beach=base["beach"],
            date=base["date"],
            organization=base.get("organization"),
            notes=base.get("notes", ""),
            sampling_method=sampling_method,
            method_params=method_params or None,
            status="draft",  # coherente con tu workflow
        )

        # Generar unidades SOLO al final
        try:
            event.generate_units_from_method()
        except ValidationError as e:
            # rollback funcional: si falla, eliminar evento para no dejar basura
            event.delete()
            messages.error(self.request, f"No se pudo crear el monitoreo: {e}")
            return redirect("sampling_create")

        messages.success(self.request, "Monitoreo creado en estado DRAFT y unidades generadas.")
        return redirect("sampling_event_units", pk=event.pk)

    def get_next_step(self, step=None):
        """
        Si el POST viene del auto-reload del método,
        no avanzar de step.
        """
        if self.request.POST.get("reload_step") == "1":
            return self.steps.current

        return super().get_next_step(step)