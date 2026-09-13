from django.urls import path

from agent.views import AgentMeView, AgentVerificationStatusView, BecomeAgentView

app_name = "agent"

urlpatterns = [
    path("v1/become-agent/", BecomeAgentView.as_view(), name="become_agent"),
    path("v1/me/", AgentMeView.as_view(), name="agent_me"),
    path(
        "v1/me/verification-status/",
        AgentVerificationStatusView.as_view(),
        name="agent_verification_status",
    ),
]
