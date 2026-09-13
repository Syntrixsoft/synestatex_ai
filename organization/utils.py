from core.utils import build_site_url
from organization.models import CompanyMember
from user.models import User


def build_invite_link(token):
    return build_site_url("organization/v1/invites", token)


def existing_member_for_contact(company, phone=None, email=None):
    qs = CompanyMember.objects.filter(company=company, is_active=True)
    if phone:
        user = User.objects.filter(phone=phone).first()
        if user and hasattr(user, "agent_profile"):
            if qs.filter(agent=user.agent_profile).exists():
                return True
    if email:
        user = User.objects.filter(email=email).first()
        if user and hasattr(user, "agent_profile"):
            if qs.filter(agent=user.agent_profile).exists():
                return True
    return False
