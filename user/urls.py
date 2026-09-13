from django.urls import path

from user.views import (
    AddressDetailView,
    AddressListCreateView,
    ForgotPasswordView,
    GoogleLoginView,
    LinkGoogleView,
    LoginView,
    LogoutView,
    MeView,
    OtpRequestView,
    OtpVerifyView,
    ProfileUpdateView,
    RegisterView,
    SetPasswordView,
    ResetPasswordView,
    TokenRefreshView,
    VerifyEmailView,
)

app_name = "user"

urlpatterns = [
    path("v1/auth/otp/request/", OtpRequestView.as_view(), name="otp_request"),
    path("v1/auth/otp/verify/", OtpVerifyView.as_view(), name="otp_verify"),
    path("v1/auth/register/", RegisterView.as_view(), name="register"),
    path("v1/auth/verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path("v1/auth/login/", LoginView.as_view(), name="login"),
    path("v1/auth/password/forgot/", ForgotPasswordView.as_view(), name="password_forgot"),
    path("v1/auth/password/reset/", ResetPasswordView.as_view(), name="password_reset"),
    path("v1/auth/google/", GoogleLoginView.as_view(), name="google"),
    path("v1/auth/link-google/", LinkGoogleView.as_view(), name="link_google"),
    path("v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("v1/auth/logout/", LogoutView.as_view(), name="logout"),
    path("v1/me/", MeView.as_view(), name="me"),
    path("v1/me/set-password/", SetPasswordView.as_view(), name="set_password"),
    path("v1/me/profile/", ProfileUpdateView.as_view(), name="profile"),
    path("v1/me/addresses/", AddressListCreateView.as_view(), name="addresses"),
    path(
        "v1/me/addresses/<uuid:address_id>/",
        AddressDetailView.as_view(),
        name="address_detail",
    ),
]
