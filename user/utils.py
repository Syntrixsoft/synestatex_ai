from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken

from core import choices
from core.utils import get_unique_filename


class AccountInactive(PermissionDenied):
    default_detail = "Account no longer active"
    default_code = "account_inactive"


def ensure_account_active(user):
    if user.object_status != choices.ObjectStatusChoices.ACTIVE:
        raise AccountInactive()
    if user.status in (
        choices.AccountStatusChoices.SUSPENDED,
        choices.AccountStatusChoices.BLOCKED,
    ):
        raise AccountInactive()
    if not user.is_active:
        raise AccountInactive()


def issue_tokens(user):
    ensure_account_active(user)
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def build_auth_response(user, is_new_user=False):
    return {
        **issue_tokens(user),
        "is_new_user": is_new_user,
        "user": serialize_user(user),
    }


def get_active_login_methods(user):
    return {
        "otp": bool(user.phone_verified or user.email_verified),
        "password": user.has_usable_password(),
        "google": bool(user.google_id),
    }


def serialize_user(user):
    """Serialize the authenticated user for API responses.

    ``signup_source`` is the original signup method (historical only) and does
    not reflect which login methods are currently active. Use
    ``active_login_methods`` for that.
    """
    profile = getattr(user, "profile", None)
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "name": user.name,
        "status": user.status,
        # Original signup method (historical only — not the current login method).
        "signup_source": user.signup_source,
        "active_login_methods": get_active_login_methods(user),
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "profile": {
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "display_name": profile.display_name if profile else "",
            "avatar": profile.avatar.url if profile and profile.avatar else None,
            "bio": profile.bio if profile else "",
        },
    }


def touch_last_login(user):
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])


def profile_image_directory(instance, filename):
    filename = get_unique_filename(instance.pk, filename)
    return "user/profile_image/{}".format(filename)
