from core import choices
from agent.models import AgentProfile


def ensure_agent_profile(user):
    profile, _ = AgentProfile.objects.get_or_create(
        user=user,
        defaults={
            "specialization": choices.AgentSpecializationChoices.BOTH,
            "is_independent": True,
        },
    )
    return profile
