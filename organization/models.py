from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core import choices
from core import models as core_models


class Company(core_models.BaseModel):
    parent_company = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sub_companies",
    )
    company_type = models.CharField(
        max_length=20, choices=choices.CompanyTypeChoices.choices
    )
    legal_name = models.CharField(max_length=255)
    brand_name = models.CharField(max_length=150, blank=True)
    rera_number = models.CharField(max_length=100, blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    addresses = GenericRelation("core.Address")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["rera_number"],
                condition=~models.Q(rera_number="")
                & models.Q(object_status=choices.ObjectStatusChoices.ACTIVE),
                name="unique_rera_number",
            )
        ]

    def clean(self):
        node = self.parent_company
        seen = {self.id}
        while node is not None:
            if node.id in seen:
                raise ValidationError("Circular company hierarchy is not allowed")
            seen.add(node.id)
            node = node.parent_company

    def save(self, *args, **kwargs):
        orig = Company.objects.filter(pk=self.pk).first() if self.pk else None
        super().save(*args, **kwargs)
        if orig and orig.is_active and not self.is_active:
            self.branches.update(is_active=False)
            now = timezone.now()
            for member in self.members.filter(is_active=True):
                member.is_active = False
                member.left_at = now
                member.save()

    def __str__(self):
        return self.brand_name or self.legal_name


class CompanyBranch(core_models.BaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="branches"
    )
    name = models.CharField(max_length=150)
    branch_type = models.CharField(
        max_length=20,
        choices=choices.BranchTypeChoices.choices,
        default=choices.BranchTypeChoices.SALES_OFFICE,
    )
    floor_number = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    addresses = GenericRelation("core.Address")

    def __str__(self):
        return "{} - {}".format(self.company, self.name)


class CompanyMember(core_models.BaseModel):
    agent = models.ForeignKey(
        "agent.AgentProfile",
        on_delete=models.CASCADE,
        related_name="company_memberships",
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="members"
    )
    branch = models.ForeignKey(
        CompanyBranch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    designation = models.CharField(
        max_length=30,
        choices=choices.DesignationChoices.choices,
        default=choices.DesignationChoices.SALES_AGENT,
    )
    employment_type = models.CharField(
        max_length=20,
        choices=choices.EmploymentTypeChoices.choices,
        default=choices.EmploymentTypeChoices.EMPLOYEE,
    )
    reports_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reportees",
    )
    is_primary = models.BooleanField(default=False)
    commission_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "company", "branch"],
                condition=models.Q(object_status=choices.ObjectStatusChoices.ACTIVE),
                name="unique_membership",
                nulls_distinct=False,
            ),
            models.UniqueConstraint(
                fields=["agent"],
                condition=models.Q(
                    is_primary=True,
                    is_active=True,
                    object_status=choices.ObjectStatusChoices.ACTIVE,
                ),
                name="one_primary_active_company_per_agent",
            ),
        ]

    def clean(self):
        if self.reports_to and self.reports_to.company_id != self.company_id:
            raise ValidationError("reports_to must be in the same company")

    def save(self, *args, **kwargs):
        if not self.is_active and self.left_at is None:
            self.left_at = timezone.now()
        super().save(*args, **kwargs)
        self.agent.sync_independence()

    def __str__(self):
        return "{} @ {}".format(self.agent, self.company)


class CompanyInvite(core_models.BaseModel):
    token = models.CharField(max_length=64, unique=True)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="invites"
    )
    branch = models.ForeignKey(
        CompanyBranch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invites",
    )
    invited_phone = models.CharField(max_length=20, null=True, blank=True)
    invited_email = models.EmailField(null=True, blank=True)
    designation = models.CharField(max_length=30)
    role_code = models.CharField(max_length=50)
    invited_by = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, related_name="sent_invites"
    )
    status = models.CharField(
        max_length=20,
        choices=choices.InviteStatusChoices.choices,
        default=choices.InviteStatusChoices.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(invited_phone__isnull=False)
                | models.Q(invited_email__isnull=False),
                name="invite_must_have_phone_or_email",
            )
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return "{} invite ({})".format(self.company, self.status)
