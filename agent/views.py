from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agent.models import AgentProfile
from agent.serializers import AgentProfileSerializer, BecomeAgentSerializer


class BecomeAgentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if hasattr(request.user, "agent_profile"):
            raise ValidationError({"detail": "Agent profile already exists"})

        serializer = BecomeAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = AgentProfile.objects.create(
            user=request.user,
            specialization=serializer.validated_data["specialization"],
            is_independent=True,
        )
        return Response(
            AgentProfileSerializer(profile).data,
            status=status.HTTP_201_CREATED,
        )


class AgentMeView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        profile = getattr(request.user, "agent_profile", None)
        if profile is None:
            raise ValidationError({"detail": "Agent profile not found"})
        serializer = AgentProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class AgentVerificationStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, "agent_profile", None)
        if profile is None:
            raise ValidationError({"detail": "Agent profile not found"})

        pending = []
        if not profile.rera_agent_id:
            pending.append("rera_agent_id")
        if not profile.service_cities:
            pending.append("service_cities")

        return Response(
            {
                "is_verified": profile.is_verified,
                "pending": pending,
            },
            status=status.HTTP_200_OK,
        )
