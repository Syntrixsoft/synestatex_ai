from rest_framework import serializers

from agent.models import AgentProfile


class BecomeAgentSerializer(serializers.Serializer):
    specialization = serializers.ChoiceField(
        choices=AgentProfile._meta.get_field("specialization").choices
    )


class AgentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentProfile
        fields = (
            "specialization",
            "rera_agent_id",
            "service_cities",
            "is_independent",
            "is_verified",
            "is_active",
        )
        read_only_fields = ("is_independent", "is_verified", "is_active")
