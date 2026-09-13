from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from agent.models import AgentProfile
from core import choices
from organization.models import Company, CompanyInvite, CompanyMember
from organization.services.companies import create_company_member, register_company
from organization.services.invites import accept_invite
from user.models import User


class InviteAcceptIdentityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(
            email="admin@example.com",
            status=choices.AccountStatusChoices.ACTIVE,
        )
        self.company = Company.objects.create(
            legal_name="Test Co",
            company_type=choices.CompanyTypeChoices.AGENCY,
        )
        self.invite = CompanyInvite.objects.create(
            token="phone-invite-token",
            company=self.company,
            invited_phone="+911111111111",
            designation=choices.DesignationChoices.SALES_AGENT,
            role_code="SALES_AGENT",
            invited_by=self.admin,
            expires_at=timezone.now() + timedelta(days=7),
        )

    @patch("verification.service.OtpService.verify")
    def test_accept_invite_rejects_mismatched_phone(self, mock_verify):
        response = self.client.post(
            "/organization/v1/invites/{}/accept/".format(self.invite.token),
            {"identifier": "+912222222222", "otp": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        mock_verify.assert_not_called()

    @patch("verification.service.OtpService.verify")
    def test_accept_invite_allows_matching_phone(self, mock_verify):
        from verification.service import OtpVerifyResult

        mock_verify.return_value = OtpVerifyResult(success=True)
        response = self.client.post(
            "/organization/v1/invites/{}/accept/".format(self.invite.token),
            {"identifier": "+911111111111", "otp": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)


class CompanyMemberPrimaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="agent@example.com",
            status=choices.AccountStatusChoices.ACTIVE,
        )
        self.agent_profile = AgentProfile.objects.create(user=self.user)
        self.company_a = Company.objects.create(
            legal_name="Company A",
            company_type=choices.CompanyTypeChoices.AGENCY,
        )
        self.company_b = Company.objects.create(
            legal_name="Company B",
            company_type=choices.CompanyTypeChoices.AGENCY,
        )

    def test_first_membership_is_primary(self):
        member = create_company_member(
            self.agent_profile,
            self.company_a,
            designation=choices.DesignationChoices.SALES_AGENT,
        )
        self.assertTrue(member.is_primary)

    def test_second_membership_is_not_primary(self):
        create_company_member(
            self.agent_profile,
            self.company_a,
            designation=choices.DesignationChoices.SALES_AGENT,
        )
        member_b = create_company_member(
            self.agent_profile,
            self.company_b,
            designation=choices.DesignationChoices.SALES_AGENT,
        )
        self.assertFalse(member_b.is_primary)

    def test_new_membership_is_primary_after_leaving_previous(self):
        old_member = create_company_member(
            self.agent_profile,
            self.company_a,
            designation=choices.DesignationChoices.SALES_AGENT,
        )
        old_member.is_active = False
        old_member.is_primary = False
        old_member.save(update_fields=["is_active", "is_primary"])

        new_member = create_company_member(
            self.agent_profile,
            self.company_b,
            designation=choices.DesignationChoices.SALES_AGENT,
        )
        self.assertTrue(new_member.is_primary)

    @patch("verification.service.OtpService.verify")
    def test_invite_accept_sets_is_primary_false_when_agent_has_primary(
        self, mock_verify
    ):
        from verification.service import OtpVerifyResult

        mock_verify.return_value = OtpVerifyResult(success=True)
        user = User.objects.create(
            phone="+919999999999",
            status=choices.AccountStatusChoices.ACTIVE,
            phone_verified=True,
        )
        agent = AgentProfile.objects.create(user=user)
        create_company_member(
            agent,
            self.company_a,
            designation=choices.DesignationChoices.SALES_AGENT,
        )
        admin = User.objects.create(
            email="admin@example.com",
            status=choices.AccountStatusChoices.ACTIVE,
        )
        invite = CompanyInvite.objects.create(
            token="join-company-b",
            company=self.company_b,
            invited_phone="+919999999999",
            designation=choices.DesignationChoices.SALES_AGENT,
            role_code="SALES_AGENT",
            invited_by=admin,
            expires_at=timezone.now() + timedelta(days=7),
        )

        accept_invite(
            invite.token,
            identifier="+919999999999",
            otp="123456",
        )

        member = CompanyMember.objects.get(agent=agent, company=self.company_b)
        self.assertFalse(member.is_primary)

    def test_company_registration_creates_primary_membership(self):
        owner = User.objects.create(
            email="owner@example.com",
            status=choices.AccountStatusChoices.ACTIVE,
        )
        company = register_company(
            owner,
            legal_name="New Co",
            company_type=choices.CompanyTypeChoices.AGENCY,
        )
        member = CompanyMember.objects.get(
            agent__user=owner,
            company=company,
        )
        self.assertTrue(member.is_primary)
