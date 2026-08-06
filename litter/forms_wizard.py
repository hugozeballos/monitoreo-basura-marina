from __future__ import annotations

from typing import Any, Dict, Optional

from django import forms

from litter.models import Beach, Organization, SamplingMethod


class Step1BaseInfoForm(forms.Form):
    beach = forms.ModelChoiceField(queryset=Beach.objects.all(), required=True, label="Playa")
    date = forms.DateField(required=True, label="Fecha", widget=forms.DateInput(attrs={"type": "date"}))
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        required=False,
        label="Organización (opcional)",
    )
    notes = forms.CharField(required=False, label="Notas (opcional)", widget=forms.Textarea(attrs={"rows": 3}))


class Step2MethodForm(forms.Form):
    """Wizard step 2: pick a sampling method, plus its dynamic params (transects, stations, etc.)."""

    sampling_method = forms.ModelChoiceField(
        queryset=SamplingMethod.objects.filter(is_active=True),
        required=True,
        label="Método de muestreo",
        empty_label="Seleccione un método"
    )

    def __init__(self, *args, **kwargs):
        """
        Agrega campos dinámicos a partir de SamplingMethod.default_params_schema.
        - No asumimos tipos complejos: por ahora IntegerField como en tu CreateView actual.
        - Queda preparado para extender (float, choice, etc.) leyendo schema.
        """
        super().__init__(*args, **kwargs)

        # Detect selected method using wizard prefix-aware access
        method: Optional[SamplingMethod] = None


        # En wizard, el nombre real del campo es algo como "method-sampling_method"
        for key in self.data.keys():
            if key.endswith("sampling_method") and self.data.get(key):
                try:
                    method = SamplingMethod.objects.get(pk=self.data.get(key))
                except SamplingMethod.DoesNotExist:
                    method = None
                break

        # Fallback cuando se navega hacia atrás
        if method is None:
            initial_method = self.initial.get("sampling_method")
            if isinstance(initial_method, SamplingMethod):
                method = initial_method
            elif initial_method:
                try:
                    method = SamplingMethod.objects.get(pk=initial_method)
                except SamplingMethod.DoesNotExist:
                    method = None

        if method and method.default_params_schema:
            for param_name, config in method.default_params_schema.items():
                default_value = None
                if isinstance(config, dict):
                    default_value = config.get("default")

                self.fields[param_name] = forms.IntegerField(
                    required=False,
                    initial=default_value,
                    label=param_name.replace("_", " ").title(),
                )

    def cleaned_method_params(self) -> Dict[str, Any]:
        """
        Devuelve solo los params dinámicos presentes en default_params_schema.
        """
        method: SamplingMethod = self.cleaned_data["sampling_method"]
        out: Dict[str, Any] = {}

        schema = method.default_params_schema or {}
        for param_name in schema.keys():
            value = self.cleaned_data.get(param_name)
            if value is not None:
                out[param_name] = value
        return out


class Step3ConfirmForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label="Confirmo que la información es correcta",
    )