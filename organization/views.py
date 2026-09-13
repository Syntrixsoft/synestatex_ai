from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import map_service_error
from organization.models import CompanyBranch, CompanyMember
from organization.serializers import (
    BranchSerializer,
    CompanyCreateSerializer,
    CompanyMemberSerializer,
    CompanyMemberUpdateSerializer,
    CompanyVerificationSerializer,
    InviteAcceptSerializer,
    InviteMemberSerializer,
)
from organization.services import companies as company_service
from organization.services import invites as invite_service
from user.permissions import HasCompanyPermission


class CompanyCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CompanyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = company_service.register_company(
            user=request.user,
            legal_name=serializer.validated_data["legal_name"],
            company_type=serializer.validated_data["company_type"],
            brand_name=serializer.validated_data.get("brand_name", ""),
        )
        return Response(
            {
                "id": str(company.id),
                "legal_name": company.legal_name,
                "brand_name": company.brand_name,
                "company_type": company.company_type,
            },
            status=status.HTTP_201_CREATED,
        )


class CompanyVerificationView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyPermission]
    required_permission_code = "company.verify"

    def post(self, request, company_id):
        company = company_service.get_company(company_id)
        serializer = CompanyVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = company_service.submit_company_verification(
            company,
            rera_number=serializer.validated_data.get("rera_number", ""),
            gst_number=serializer.validated_data.get("gst_number", ""),
            documents=serializer.validated_data.get("documents", []),
        )
        return Response(result, status=status.HTTP_200_OK)


class CompanyVerificationStatusView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyPermission]
    required_permission_code = "company.view"

    def get(self, request, company_id):
        company = company_service.get_company(company_id)
        return Response(
            company_service.get_company_verification_status(company),
            status=status.HTTP_200_OK,
        )


class CompanyBranchListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyPermission]
    required_permission_code = "company.branch.manage"

    def get(self, request, company_id):
        company = company_service.get_company(company_id)
        branches = company_service.list_branches(company)
        return Response(
            BranchSerializer(branches, many=True).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, company_id):
        company = company_service.get_company(company_id)
        serializer = BranchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branch = company_service.create_branch(
            company=company,
            name=serializer.validated_data["name"],
            city=serializer.validated_data["city"],
            branch_type=serializer.validated_data.get("branch_type"),
            floor_number=serializer.validated_data.get("floor_number", ""),
        )
        return Response(BranchSerializer(branch).data, status=status.HTTP_201_CREATED)


class CompanyMemberInviteView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyPermission]
    required_permission_code = "company.member.invite"

    def post(self, request, company_id):
        company = company_service.get_company(company_id)
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branch = None
        branch_id = serializer.validated_data.get("branch_id")
        if branch_id:
            branch = CompanyBranch.objects.filter(
                pk=branch_id,
                company=company,
            ).first()
            if branch is None:
                raise ValidationError({"branch_id": "Invalid branch"})
        try:
            invite = invite_service.create_invite(
                company=company,
                invited_by=request.user,
                designation=serializer.validated_data["designation"],
                role_code=serializer.validated_data["role_code"],
                phone=serializer.validated_data.get("phone"),
                email=serializer.validated_data.get("email"),
                branch=branch,
            )
        except ValidationError as exc:
            map_service_error(exc)
        return Response(
            {
                "id": str(invite.id),
                "token": invite.token,
                "expires_at": invite.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class CompanyMemberListView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyPermission]
    required_permission_code = "company.member.view"

    def get(self, request, company_id):
        company = company_service.get_company(company_id)
        members = CompanyMember.objects.filter(
            company=company,
            is_active=True,
        ).select_related("agent__user", "branch")
        return Response(
            CompanyMemberSerializer(members, many=True).data,
            status=status.HTTP_200_OK,
        )


class CompanyMemberDetailView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyPermission]
    required_permission_code = "company.member.manage"

    def patch(self, request, company_id, member_id):
        company = company_service.get_company(company_id)
        member = CompanyMember.objects.filter(pk=member_id, company=company).first()
        if member is None:
            raise NotFound({"detail": "Member not found"})
        serializer = CompanyMemberUpdateSerializer(member, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            CompanyMemberSerializer(member).data,
            status=status.HTTP_200_OK,
        )


class InvitePreviewView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            invite = invite_service.get_invite_preview(token)
        except ValidationError as exc:
            map_service_error(exc)
        company = invite.company
        return Response(
            {
                "company_name": company.brand_name or company.legal_name,
                "designation": invite.designation,
                "expires_at": invite.expires_at,
            },
            status=status.HTTP_200_OK,
        )


class InviteAcceptView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, token):
        serializer = InviteAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = invite_service.accept_invite(
                token=token,
                identifier=serializer.validated_data.get("identifier"),
                otp=serializer.validated_data.get("otp"),
                id_token=serializer.validated_data.get("id_token"),
            )
        except ValidationError as exc:
            map_service_error(exc)
        return Response(result, status=status.HTTP_200_OK)
