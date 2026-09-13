from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from communication.service import CommunicationService
from core import choices
from core.utils import build_site_url, parse_identifier
from user.models import Profile, User
from user.utils import ensure_account_active, touch_last_login
from verification.service import OtpResendTooSoon, OtpService


MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
EMAIL_VERIFY_MAX_AGE = 24 * 60 * 60
PASSWORD_RESET_MAX_AGE = 24 * 60 * 60


def request_otp(identifier):
    channel, normalized = parse_identifier(identifier)
    purpose = choices.OtpPurposeChoices.LOGIN
    try:
        OtpService.send(purpose=purpose, sent_to=normalized, channel=channel)
    except OtpResendTooSoon as exc:
        raise ValidationError(
            {"retry_after": exc.retry_after},
            code="resend_too_soon",
        )
    return {"channel": channel, "sent_to": normalized}


def verify_otp_and_login(identifier, otp):
    channel, normalized = parse_identifier(identifier)
    purpose = choices.OtpPurposeChoices.LOGIN
    result = OtpService.verify(
        purpose=purpose,
        sent_to=normalized,
        code=otp,
        channel=channel,
    )
    if not result.success:
        raise ValidationError({"otp": result.error})

    user, is_new = _get_or_create_user_from_identifier(channel, normalized)
    ensure_account_active(user)
    touch_last_login(user)
    return user, is_new


def _get_or_create_user_from_identifier(channel, normalized):
    is_new = False
    if channel == choices.OtpChannelChoices.EMAIL:
        user = User.objects.complete().filter(email=normalized).first()
        if user:
            ensure_account_active(user)
            if not user.email_verified:
                user.email_verified = True
                user.save(update_fields=["email_verified"])
            return user, False

        user = User(
            email=normalized,
            signup_source=choices.SignupSourceChoices.EMAIL_OTP,
            status=choices.AccountStatusChoices.ACTIVE,
            email_verified=True,
        )
        user.set_unusable_password()
        user.save()
        Profile.objects.get_or_create(user=user)
        return user, True

    user = User.objects.complete().filter(phone=normalized).first()
    if user:
        ensure_account_active(user)
        if not user.phone_verified:
            user.phone_verified = True
            user.save(update_fields=["phone_verified"])
        return user, False

    user = User(
        phone=normalized,
        signup_source=choices.SignupSourceChoices.PHONE_OTP,
        status=choices.AccountStatusChoices.ACTIVE,
        phone_verified=True,
    )
    user.set_unusable_password()
    user.save()
    Profile.objects.get_or_create(user=user)
    return user, True


@transaction.atomic
def register_with_password(email, password):
    email = email.strip().lower()
    if User.objects.complete().filter(email=email).exists():
        raise ValidationError({"email": "Email already registered"})

    try:
        validate_password(password)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)})

    user = User(
        email=email,
        signup_source=choices.SignupSourceChoices.EMAIL_PASSWORD,
        status=choices.AccountStatusChoices.PENDING_VERIFICATION,
    )
    user.set_password(password)
    user.save()
    Profile.objects.get_or_create(user=user)
    _send_verification_email(user)
    return user


def _send_verification_email(user):
    signer = TimestampSigner()
    token = signer.sign(str(user.id))
    verify_url = build_site_url("user/v1/auth/verify-email")
    CommunicationService.send(
        channel=choices.CommunicationChannelChoices.EMAIL,
        recipient=user.email,
        subject="Verify your email",
        template="communication/emails/verify_email.html",
        context={
            "name": user.name,
            "token": token,
            "verify_url": verify_url,
            "expiry_hours": EMAIL_VERIFY_MAX_AGE // 3600,
        },
    )


def verify_email_token(token):
    signer = TimestampSigner()
    try:
        user_id = signer.unsign(token, max_age=EMAIL_VERIFY_MAX_AGE)
    except SignatureExpired:
        raise ValidationError({"token": "expired"})
    except BadSignature:
        raise ValidationError({"token": "invalid"})

    user = User.objects.complete().filter(pk=user_id).first()
    if user is None:
        raise ValidationError({"token": "invalid"})
    ensure_account_active(user)

    user.email_verified = True
    user.status = choices.AccountStatusChoices.ACTIVE
    user.save(update_fields=["email_verified", "status"])
    touch_last_login(user)
    return user


def login_with_password(email, password):
    email = email.strip().lower()
    user = User.objects.complete().filter(email=email).first()
    if user is None:
        raise ValidationError({"detail": "Invalid credentials"})

    ensure_account_active(user)

    if user.locked_until and user.locked_until > timezone.now():
        raise ValidationError({"detail": "Account temporarily locked"})

    if not user.has_usable_password():
        raise ValidationError(
            {
                "detail": (
                    "No password is set for this account. Try Google or OTP login, "
                    "or set a password from your profile."
                )
            }
        )

    if not user.check_password(password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = timezone.now() + timezone.timedelta(
                minutes=LOCKOUT_MINUTES
            )
            user.failed_login_attempts = 0
        user.save(update_fields=["failed_login_attempts", "locked_until"])
        raise ValidationError({"detail": "Invalid credentials"})

    user.failed_login_attempts = 0
    user.locked_until = None
    user.save(update_fields=["failed_login_attempts", "locked_until"])
    touch_last_login(user)
    return user


def request_password_reset(email):
    email = email.strip().lower()
    user = User.objects.filter(email=email).first()
    if user and user.has_usable_password():
        signer = TimestampSigner()
        token = signer.sign("{}:{}".format(user.id, user.password))
        reset_url = build_site_url("user/v1/auth/password/reset")
        CommunicationService.send(
            channel=choices.CommunicationChannelChoices.EMAIL,
            recipient=user.email,
            subject="Reset your password",
            template="communication/emails/password_reset.html",
            context={
                "token": token,
                "reset_url": reset_url,
                "expiry_hours": PASSWORD_RESET_MAX_AGE // 3600,
            },
        )
    return {
        "detail": "If an account exists with this email, a reset link has been sent."
    }


def reset_password(token, new_password):
    signer = TimestampSigner()
    try:
        value = signer.unsign(token, max_age=PASSWORD_RESET_MAX_AGE)
    except SignatureExpired:
        raise ValidationError({"token": "expired"})
    except BadSignature:
        raise ValidationError({"token": "invalid"})

    user_id, password_hash = value.split(":", 1)
    user = User.objects.complete().filter(pk=user_id).first()
    if user is None:
        raise ValidationError({"token": "invalid"})
    ensure_account_active(user)

    if user.password != password_hash:
        raise ValidationError({"token": "already_used"})

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)})

    user.set_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save(update_fields=["password", "failed_login_attempts", "locked_until"])
    touch_last_login(user)
    return user


def set_password(user, new_password):
    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"new_password": list(exc.messages)})

    user.set_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save(update_fields=["password", "failed_login_attempts", "locked_until"])
    return user
