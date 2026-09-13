from rest_framework import serializers

from organization.models import Company, CompanyBranch, CompanyMember


class CompanyCreateSerializer(serializers.Serializer):
    legal_name = serializers.CharField(max_length=255)
    company_type = serializers.ChoiceField(choices=Company._meta.get_field("company_type").choices)
    brand_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")


class CompanyVerificationSerializer(serializers.Serializer):
    rera_number = serializers.CharField(required=False, allow_blank=True, default="")
    gst_number = serializers.CharField(required=False, allow_blank=True, default="")
    documents = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBranch
        fields = (
            "id",
            "name",
            "branch_type",
            "floor_number",
            "city",
            "is_active",
        )
        read_only_fields = ("id", "is_active")


class InviteMemberSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    designation = serializers.ChoiceField(
        choices=CompanyMember._meta.get_field("designation").choices
    )
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    role_code = serializers.CharField(max_length=50)


class CompanyMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()

    class Meta:
        model = CompanyMember
        fields = (
            "id",
            "user_id",
            "user_email",
            "user_phone",
            "designation",
            "branch",
            "is_primary",
            "is_active",
            "joined_at",
        )
        read_only_fields = ("id", "joined_at")

    def get_user_id(self, obj):
        return str(obj.agent.user_id)

    def get_user_email(self, obj):
        return obj.agent.user.email

    def get_user_phone(self, obj):
        return obj.agent.user.phone


class CompanyMemberUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyMember
        fields = ("designation", "branch", "is_primary", "is_active")


class InviteAcceptSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=False, allow_blank=True)
    otp = serializers.CharField(required=False, allow_blank=True)
    id_token = serializers.CharField(required=False, allow_blank=True)
