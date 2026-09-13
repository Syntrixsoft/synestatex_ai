from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core import choices
from organization.models import Company, CompanyInvite, CompanyMember
from user.models import Profile, User
from user.services.google import GoogleAccountConflict, login_or_register_with_google
from user.utils import issue_tokens


@override_settings(GOOGLE_CLIENT_ID="test-client-id")
class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("verification.service.OtpService.send")
    def test_otp_request_delegates_to_existing_service(self, mock_send):
        response = self.client.post(
            "/user/v1/auth/otp/request/",
            {"identifier": "user@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        mock_send.assert_called_once()

    @patch("verification.service.OtpService.verify")
    def test_otp_verify_creates_user_and_returns_tokens(self, mock_verify):
        from verification.service import OtpVerifyResult

        mock_verify.return_value = OtpVerifyResult(success=True)
        response = self.client.post(
            "/user/v1/auth/otp/verify/",
            {"identifier": "new@example.com", "otp": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertTrue(response.data["is_new_user"])
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_password_login_rejects_when_no_password_set(self):
        user = User.objects.create(
            email="otp@example.com",
            signup_source=choices.SignupSourceChoices.EMAIL_OTP,
            status=choices.AccountStatusChoices.ACTIVE,
            email_verified=True,
        )
        user.set_unusable_password()
        user.save()
        response = self.client.post(
            "/user/v1/auth/login/",
            {"email": "otp@example.com", "password": "Password123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No password is set", response.data["detail"])

    def test_me_includes_active_login_methods(self):
        user = User.objects.create(
            email="me@example.com",
            signup_source=choices.SignupSourceChoices.EMAIL_OTP,
            status=choices.AccountStatusChoices.ACTIVE,
            email_verified=True,
            google_id="google-abc",
        )
        user.set_unusable_password()
        user.save()
        self.client.force_authenticate(user=user)
        response = self.client.get("/user/v1/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["active_login_methods"],
            {"otp": True, "password": False, "google": True},
        )
        self.assertEqual(
            response.data["signup_source"],
            choices.SignupSourceChoices.EMAIL_OTP,
        )

    def test_password_login_succeeds_after_otp_user_sets_password(self):
        user = User.objects.create(
            email="otp@example.com",
            signup_source=choices.SignupSourceChoices.EMAIL_OTP,
            status=choices.AccountStatusChoices.ACTIVE,
            email_verified=True,
        )
        user.set_unusable_password()
        user.save()
        self.client.force_authenticate(user=user)
        self.client.post(
            "/user/v1/me/set-password/",
            {"new_password": "Password123!"},
            format="json",
        )
        self.client.logout()
        response = self.client.post(
            "/user/v1/auth/login/",
            {"email": "otp@example.com", "password": "Password123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_soft_deleted_user_cannot_receive_tokens(self):
        user = User.objects.create(
            email="deleted@example.com",
            signup_source=choices.SignupSourceChoices.EMAIL_PASSWORD,
            status=choices.AccountStatusChoices.ACTIVE,
            email_verified=True,
        )
        user.set_password("Password123!")
        user.save()
        user.delete()
        with self.assertRaises(Exception):
            issue_tokens(User.objects.complete().get(pk=user.pk))

    @patch("user.services.google.verify_google_token")
    def test_google_login_links_existing_email_password_account(self, mock_verify):
        user = User.objects.create(
            email="existing@example.com",
            signup_source=choices.SignupSourceChoices.EMAIL_PASSWORD,
            status=choices.AccountStatusChoices.ACTIVE,
            email_verified=True,
        )
        user.set_password("Password123!")
        user.save()
        mock_verify.return_value = {
            "sub": "google-123",
            "email": "existing@example.com",
            "email_verified": True,
            "name": "Existing User",
        }
        linked_user, is_new = login_or_register_with_google("token")
        self.assertFalse(is_new)
        self.assertEqual(linked_user.google_id, "google-123")
        self.assertTrue(linked_user.check_password("Password123!"))

    @patch("user.services.google.verify_google_token")
    def test_link_google_conflict_when_already_linked_elsewhere(self, mock_verify):
        owner = User.objects.create(
            email="owner@example.com",
            google_id="google-owned",
            signup_source=choices.SignupSourceChoices.GOOGLE,
            status=choices.AccountStatusChoices.ACTIVE,
        )
        current = User.objects.create(
            email="current@example.com",
            signup_source=choices.SignupSourceChoices.EMAIL_PASSWORD,
            status=choices.AccountStatusChoices.ACTIVE,
        )
        mock_verify.return_value = {
            "sub": "google-owned",
            "email": "owner@example.com",
            "email_verified": True,
        }
        self.client.force_authenticate(user=current)
        response = self.client.post(
            "/user/v1/auth/link-google/",
            {"id_token": "token"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_become_agent_returns_400_when_profile_exists(self):
        user = User.objects.create(
            email="agent@example.com",
            signup_source=choices.SignupSourceChoices.EMAIL_PASSWORD,
            status=choices.AccountStatusChoices.ACTIVE,
        )
        user.set_password("Password123!")
        user.save()
        Profile.objects.get_or_create(user=user)
        self.client.force_authenticate(user=user)
        self.client.post(
            "/agent/v1/become-agent/",
            {"specialization": "RENT"},
            format="json",
        )
        response = self.client.post(
            "/agent/v1/become-agent/",
            {"specialization": "RENT"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invite_preview_returns_410_when_expired(self):
        from agent.models import AgentProfile
        from organization.models import Company

        admin = User.objects.create(
            email="admin@example.com",
            status=choices.AccountStatusChoices.ACTIVE,
        )
        company = Company.objects.create(
            legal_name="Test Co",
            company_type=choices.CompanyTypeChoices.AGENCY,
        )
        invite = CompanyInvite.objects.create(
            token="expired-token",
            company=company,
            invited_phone="+911111111111",
            designation=choices.DesignationChoices.SALES_AGENT,
            role_code="SALES_AGENT",
            invited_by=admin,
            expires_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.get("/organization/v1/invites/{}/".format(invite.token))
        self.assertEqual(response.status_code, 410)
