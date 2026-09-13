from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from core.models import Address
from organization.models import CompanyMember
from user.serializers import (
    ActiveUserTokenRefreshSerializer,
    AddressSerializer,
    EmailTokenSerializer,
    GoogleTokenSerializer,
    IdentifierSerializer,
    LoginSerializer,
    OtpVerifySerializer,
    PasswordResetRequestSerializer,
    PasswordResetSerializer,
    ProfileSerializer,
    RegisterSerializer,
    SetPasswordSerializer,
)
from user.services import auth as auth_service
from user.services import google as google_service
from user.utils import build_auth_response, serialize_user


class OtpRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = IdentifierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = auth_service.request_otp(serializer.validated_data["identifier"])
        return Response(result, status=status.HTTP_200_OK)


class OtpVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, is_new = auth_service.verify_otp_and_login(
            serializer.validated_data["identifier"],
            serializer.validated_data["otp"],
        )
        return Response(
            build_auth_response(user, is_new_user=is_new),
            status=status.HTTP_201_CREATED if is_new else status.HTTP_200_OK,
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service.register_with_password(
            serializer.validated_data["email"],
            serializer.validated_data["password"],
        )
        return Response(
            {"detail": "Registration successful. Please verify your email."},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = auth_service.verify_email_token(serializer.validated_data["token"])
        return Response(build_auth_response(user), status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = auth_service.login_with_password(
            serializer.validated_data["email"],
            serializer.validated_data["password"],
        )
        return Response(build_auth_response(user), status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = auth_service.request_password_reset(serializer.validated_data["email"])
        return Response(result, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = auth_service.reset_password(
            serializer.validated_data["token"],
            serializer.validated_data["password"],
        )
        return Response(build_auth_response(user), status=status.HTTP_200_OK)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, is_new = google_service.login_or_register_with_google(
            serializer.validated_data["id_token"]
        )
        return Response(
            build_auth_response(user, is_new_user=is_new),
            status=status.HTTP_201_CREATED if is_new else status.HTTP_200_OK,
        )


class LinkGoogleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GoogleTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        google_service.link_google_account(
            request.user,
            serializer.validated_data["id_token"],
        )
        return Response(
            {"detail": "Google account linked successfully"},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {
                "detail": (
                    "Logged out successfully. "
                    "Discard tokens on the client. "
                    "Server-side token blacklist is not configured."
                )
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(BaseTokenRefreshView):
    serializer_class = ActiveUserTokenRefreshSerializer


class MeView(APIView):
    """Return the authenticated user's profile.

    ``signup_source`` in the response is the original signup method
    (historical only). Use ``active_login_methods`` to see which login
    methods are currently enabled on the account.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = serialize_user(user)
        data["has_agent_profile"] = hasattr(user, "agent_profile")
        data["company_memberships"] = [
            {
                "company_id": str(member.company_id),
                "company_name": member.company.brand_name or member.company.legal_name,
                "designation": member.designation,
                "branch_id": str(member.branch_id) if member.branch_id else None,
                "is_primary": member.is_primary,
            }
            for member in CompanyMember.objects.filter(
                agent__user=user,
                is_active=True,
            ).select_related("company", "branch")
        ]
        return Response(data, status=status.HTTP_200_OK)


class SetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service.set_password(
            request.user,
            serializer.validated_data["new_password"],
        )
        return Response(
            {"message": "Password set successfully"},
            status=status.HTTP_200_OK,
        )


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(
            content_type=ContentType.objects.get_for_model(request.user),
            object_id=request.user.id,
        )
        return Response(
            AddressSerializer(addresses, many=True).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = serializer.save(
            content_type=ContentType.objects.get_for_model(request.user),
            object_id=request.user.id,
        )
        return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, address_id):
        try:
            return Address.objects.get(
                pk=address_id,
                content_type=ContentType.objects.get_for_model(request.user),
                object_id=request.user.id,
            )
        except Address.DoesNotExist:
            raise NotFound({"detail": "Address not found"})

    def patch(self, request, address_id):
        address = self.get_object(request, address_id)
        serializer = AddressSerializer(address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, address_id):
        address = self.get_object(request, address_id)
        address.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
