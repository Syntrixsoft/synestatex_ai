import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from agent.models import AgentProfile
from communication.service import CommunicationService
from core import choices
from core.utils import parse_identifier
from organization.models import CompanyInvite, CompanyMember
from organization.services.companies import create_company_member
from organization.utils import build_invite_link, existing_member_for_contact
from user.models import Role, UserRole
from user.services import auth as auth_service
from user.services import google as google_service
from user.utils import build_auth_response, ensure_account_active


INVITE_EXPIRY_DAYS = 7


def create_invite(company, invited_by, designation, role_code, phone=None, email=None, branch=None):
    phone = (phone or "").strip() or None
    email = (email or "").strip().lower() or None
    if not phone and not email:
        raise ValidationError({"detail": "Phone or email is required"})

    if existing_member_for_contact(company, phone=phone, email=email):
        raise ValidationError(
            {"detail": "User is already a member of this company"},
            code="conflict",
        )

    token = secrets.token_urlsafe(32)
    invite = CompanyInvite.objects.create(
        token=token,
        company=company,
        branch=branch,
        invited_phone=phone,
        invited_email=email,
        designation=designation,
        role_code=role_code,
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=INVITE_EXPIRY_DAYS),
    )

    link = build_invite_link(token)
    message = "You are invited to join {}. Open: {}".format(
        company.brand_name or company.legal_name,
        link,
    )
    if phone:
        CommunicationService.send(
            channel=choices.CommunicationChannelChoices.SMS,
            recipient=phone,
            message=message,
        )
    if email:
        invited_by_name = ""
        if invited_by:
            invited_by_name = invited_by.name or invited_by.email or ""
        CommunicationService.send(
            channel=choices.CommunicationChannelChoices.EMAIL,
            recipient=email,
            subject="Invitation to join {}".format(
                company.brand_name or company.legal_name
            ),
            template="communication/emails/company_invite.html",
            context={
                "company_name": company.brand_name or company.legal_name,
                "designation": designation,
                "invite_link": link,
                "invited_by_name": invited_by_name,
                "expires_at": invite.expires_at,
            },
        )
    return invite


def _assert_invite_identity_match(invite, identifier=None, id_token=None):
    if identifier:
        try:
            channel, normalized = parse_identifier(identifier)
        except ValueError as exc:
            raise ValidationError({"identifier": str(exc)})

        if channel == choices.OtpChannelChoices.EMAIL:
            invited_email = (invite.invited_email or "").lower()
            if not invited_email or normalized != invited_email:
                raise PermissionDenied(
                    "This invite was not issued to this phone/email"
                )
        else:
            if not invite.invited_phone or normalized != invite.invited_phone:
                raise PermissionDenied(
                    "This invite was not issued to this phone/email"
                )
        return

    if id_token:
        if not invite.invited_email:
            raise PermissionDenied(
                "This invite was not issued to this Google account's email"
            )
        payload = google_service.verify_google_token(id_token)
        google_email = (payload.get("email") or "").lower()
        if google_email != invite.invited_email.lower():
            raise PermissionDenied(
                "This invite was not issued to this Google account's email"
            )


def get_invite_preview(token):
    invite = CompanyInvite.objects.filter(token=token).select_related("company").first()
    if invite is None:
        raise ValidationError({"detail": "Invite not found"}, code="not_found")
    if invite.status != choices.InviteStatusChoices.PENDING:
        raise ValidationError({"detail": "Invite already used"}, code="gone")
    if invite.is_expired():
        invite.status = choices.InviteStatusChoices.EXPIRED
        invite.save(update_fields=["status"])
        raise ValidationError({"detail": "Invite expired"}, code="gone")
    return invite


@transaction.atomic
def accept_invite(token, identifier=None, otp=None, id_token=None):
    invite = (
        CompanyInvite.objects.select_for_update()
        .select_related("company", "branch")
        .filter(token=token)
        .first()
    )
    if invite is None:
        raise ValidationError({"detail": "Invite not found"}, code="not_found")
    if invite.status != choices.InviteStatusChoices.PENDING:
        raise ValidationError({"detail": "Invite already used"}, code="gone")
    if invite.is_expired():
        invite.status = choices.InviteStatusChoices.EXPIRED
        invite.save(update_fields=["status"])
        raise ValidationError({"detail": "Invite expired"}, code="gone")

    _assert_invite_identity_match(
        invite,
        identifier=identifier,
        id_token=id_token,
    )

    if id_token:
        user, _ = google_service.login_or_register_with_google(id_token)
    elif identifier and otp:
        user, _ = auth_service.verify_otp_and_login(identifier, otp)
    else:
        raise ValidationError({"detail": "OTP or Google token is required"})

    ensure_account_active(user)

    agent_profile, _ = AgentProfile.objects.get_or_create(
        user=user,
        defaults={"is_independent": False},
    )
    if agent_profile.is_independent:
        agent_profile.is_independent = False
        agent_profile.save(update_fields=["is_independent"])

    if CompanyMember.objects.filter(
        company=invite.company,
        agent=agent_profile,
        is_active=True,
    ).exists():
        raise ValidationError(
            {"detail": "User is already a member of this company"},
            code="conflict",
        )

    create_company_member(
        agent_profile,
        invite.company,
        branch=invite.branch,
        designation=invite.designation,
    )

    role = Role.objects.filter(code=invite.role_code).first()
    if role:
        scope_type = (
            choices.RoleScopeTypeChoices.BRANCH
            if invite.branch_id
            else choices.RoleScopeTypeChoices.COMPANY
        )
        scope_id = invite.branch_id or invite.company_id
        UserRole.objects.get_or_create(
            user=user,
            role=role,
            scope_type=scope_type,
            scope_id=scope_id,
            defaults={"granted_by": invite.invited_by},
        )

    invite.status = choices.InviteStatusChoices.ACCEPTED
    invite.save(update_fields=["status"])

    response = build_auth_response(user)
    response["company_id"] = str(invite.company_id)
    response["designation"] = invite.designation
    return response
