from django.db import models

from core import choices
from core import models as core_models


class AgentProfile(core_models.BaseModel):
    user = models.OneToOneField(
        "user.User", on_delete=models.CASCADE, related_name="agent_profile"
    )
    specialization = models.CharField(
        max_length=20,
        choices=choices.AgentSpecializationChoices.choices,
        default=choices.AgentSpecializationChoices.BOTH,
    )
    rera_agent_id = models.CharField(max_length=100, blank=True)
    service_cities = models.JSONField(default=list)
    is_independent = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def sync_independence(self):
        has_company = self.company_memberships.filter(is_active=True).exists()
        independent = not has_company
        if self.is_independent != independent:
            AgentProfile.objects.filter(pk=self.pk).update(is_independent=independent)
            self.is_independent = independent

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sync_independence()

    def __str__(self):
        return "{}".format(self.user)
