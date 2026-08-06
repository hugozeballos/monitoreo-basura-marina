from django import forms
from litter.models import SamplingEvent, SamplingMethod


class SamplingEventForm(forms.ModelForm):
    """
    Non-wizard form to create/edit a SamplingEvent, with dynamic fields
    injected from the selected SamplingMethod.default_params_schema.
    """

    class Meta:
        model = SamplingEvent
        fields = [
            "beach",
            "date",
            "sampling_method",
            "organization",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        method = None

        # 1️⃣ If POST
        if "sampling_method" in self.data:
            try:
                method = SamplingMethod.objects.get(
                    pk=self.data.get("sampling_method")
                )
            except SamplingMethod.DoesNotExist:
                pass

        # 2️⃣ If instance (edit case)
        elif self.instance.pk and self.instance.sampling_method:
            method = self.instance.sampling_method

        # 3️⃣ If no POST yet, but only ONE method exists → auto-load it
        elif SamplingMethod.objects.count() == 1:
            method = SamplingMethod.objects.first()

        if method and method.default_params_schema:
            for param_name, config in method.default_params_schema.items():
                default_value = config.get("default")

                self.fields[param_name] = forms.IntegerField(
                    required=False,
                    initial=default_value,
                    label=param_name.replace("_", " ").title(),
                )

    def clean(self):
        cleaned_data = super().clean()

        method = cleaned_data.get("sampling_method")
        event_params = {}

        if method and method.default_params_schema:
            for param_name in method.default_params_schema.keys():
                value = cleaned_data.get(param_name)
                if value is not None:
                    event_params[param_name] = value

        cleaned_data["event_params"] = event_params
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.event_params = self.cleaned_data.get("event_params", {})
        if commit:
            instance.save()
        return instance