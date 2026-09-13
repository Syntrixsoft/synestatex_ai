from django.urls import path

from organization.views import (
    CompanyBranchListCreateView,
    CompanyCreateView,
    CompanyMemberDetailView,
    CompanyMemberInviteView,
    CompanyMemberListView,
    CompanyVerificationStatusView,
    CompanyVerificationView,
    InviteAcceptView,
    InvitePreviewView,
)

app_name = "organization"

urlpatterns = [
    path("v1/companies/", CompanyCreateView.as_view(), name="company_create"),
    path(
        "v1/companies/<uuid:company_id>/verification/",
        CompanyVerificationView.as_view(),
        name="company_verification",
    ),
    path(
        "v1/companies/<uuid:company_id>/verification-status/",
        CompanyVerificationStatusView.as_view(),
        name="company_verification_status",
    ),
    path(
        "v1/companies/<uuid:company_id>/branches/",
        CompanyBranchListCreateView.as_view(),
        name="company_branches",
    ),
    path(
        "v1/companies/<uuid:company_id>/members/invite/",
        CompanyMemberInviteView.as_view(),
        name="company_member_invite",
    ),
    path(
        "v1/companies/<uuid:company_id>/members/",
        CompanyMemberListView.as_view(),
        name="company_members",
    ),
    path(
        "v1/companies/<uuid:company_id>/members/<uuid:member_id>/",
        CompanyMemberDetailView.as_view(),
        name="company_member_detail",
    ),
    path("v1/invites/<str:token>/", InvitePreviewView.as_view(), name="invite_preview"),
    path(
        "v1/invites/<str:token>/accept/",
        InviteAcceptView.as_view(),
        name="invite_accept",
    ),
]
