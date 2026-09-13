from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework.exceptions import APIException, ValidationError


class GoogleAccountConflict(APIException):
    status_code = 409
    default_detail = "This Google account is already linked to another user"

from core import choices
from user.models import Profile, User
from user.utils import ensure_account_active, touch_last_login


def verify_google_token(token_str):
    try:
        return google_id_token.verify_oauth2_token(
            token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise ValidationError({"id_token": "Invalid Google token"})


def login_or_register_with_google(token_str):
    payload = verify_google_token(token_str)
    google_id = payload["sub"]
    email = payload.get("email")
    email_verified = payload.get("email_verified", False)
    name = payload.get("name", "")

    user = User.objects.complete().filter(google_id=google_id).first()
    is_new = False

    if not user and email:
        user = User.objects.complete().filter(email=email).first()
        if user:
            ensure_account_active(user)
            user.google_id = google_id
            user.email_verified = True
            user.save(update_fields=["google_id", "email_verified"])

    if not user:
        user = User(
            email=email,
            google_id=google_id,
            email_verified=email_verified,
            signup_source=choices.SignupSourceChoices.GOOGLE,
            status=choices.AccountStatusChoices.ACTIVE,
            name=name,
        )
        user.set_unusable_password()
        user.save()
        first_name = name.split(" ")[0] if name else ""
        Profile.objects.get_or_create(user=user, defaults={"first_name": first_name})
        is_new = True

    ensure_account_active(user)
    touch_last_login(user)
    return user, is_new


def link_google_account(user, token_str):
    payload = verify_google_token(token_str)
    google_id = payload["sub"]

    existing = User.objects.complete().filter(google_id=google_id).exclude(pk=user.pk).first()
    if existing:
        raise GoogleAccountConflict()

    user.google_id = google_id
    if payload.get("email_verified"):
        user.email_verified = True
    user.save(update_fields=["google_id", "email_verified"])
    return user
