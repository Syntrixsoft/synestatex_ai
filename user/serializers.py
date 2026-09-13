from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from core import choices
from core.models import Address
from user.models import Profile, User
from user.utils import AccountInactive, ensure_account_active


class IdentifierSerializer(serializers.Serializer):
    identifier = serializers.CharField()


class OtpVerifySerializer(serializers.Serializer):
    identifier = serializers.CharField()
    otp = serializers.CharField()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)


class EmailTokenSerializer(serializers.Serializer):
    token = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)


class GoogleTokenSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class SetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)


class ActiveUserTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = self.token_class(attrs["refresh"])
        user_id = refresh.payload.get("user_id")
        user = User.objects.complete().filter(pk=user_id).first()
        if user is None:
            raise AccountInactive()
        ensure_account_active(user)
        return data


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            "first_name",
            "last_name",
            "display_name",
            "bio",
            "profile_completion",
        )
        read_only_fields = ("profile_completion",)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "id",
            "address_type",
            "line1",
            "line2",
            "city",
            "state",
            "pincode",
            "latitude",
            "longitude",
            "is_default",
        )
        read_only_fields = ("id",)

    def validate_address_type(self, value):
        if value not in choices.AddressTypeChoices.values:
            raise serializers.ValidationError("Invalid address type")
        return value
